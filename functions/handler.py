"""Lambda handler for the NHID Clinical conformance check API."""
import json
import os
import re
import sys

# When SAM packages with CodeUri: ., the repo root is /var/task.
# This insert ensures `src` and `adapters` are importable whether running locally or in Lambda.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nhid_policy_engine_v1 import (  # noqa: E402
    POLICY_ENGINE_VERSION,
    NHID_SPEC_VERSION,
    evaluate_all,
)
from src.nhid_cas import _tier_for_cas  # noqa: E402
from src.nhid_network_resilience import retry_with_backoff  # noqa: E402
from src.dbc01_review_routing import should_route_to_review  # noqa: E402

try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TURNSTILE_SECRET_ENV = "CLOUDFLARE_TURNSTILE_SECRET"

#: Beacon's live ElevenLabs agent (prompt and config maintained privately, outside the public repo).
_BEACON_AGENT_ID = "agent_4001krn32nmwe5t8mqzgee0w84rj"

#: Outbound demo calls cost real Twilio/ElevenLabs minutes, unlike every other
#: demo-suffixed route — these limits exist to cap that cost, not just deter bots.
_DEMO_CALL_RATE_LIMIT_WINDOW_SECONDS = 3600
_DEMO_CALL_IP_LIMIT = 5
_DEMO_CALL_PHONE_LIMIT = 3


def lambda_handler(event: dict, context) -> dict:
    """
    Routes:
      GET  /health                           — liveness probe, no API key required
      POST /v1/conformance/check             — evaluate an NHID event, API key required
      POST /v1/demo/check                    — same as conformance/check, no API key required
      POST /v1/adapters/vapi/check           — accepts native VAPI call payload, no API key
      POST /v1/adapters/twilio/check         — accepts native Twilio call payload, no API key
      POST /v1/adapters/vonage/check         — accepts native Vonage call payload, no API key
      POST /v1/adapters/retell/check         — accepts native Retell AI payload, no API key
      POST /v1/adapters/connect/check        — accepts Amazon Connect Contact Lens payload
      POST /v1/webhooks/call-progress        — turn-by-turn evaluation, no API key required
      GET  /v1/public/vendor/{id}/badge      — public CAS badge SVG, no API key required
      GET  /v1/vendor/metrics/summary        — per-vendor metrics, API key required
      POST /v1/pilot/enroll                  — pilot enrollment, no API key required
      POST /v1/cts/evaluate                  — run conformance test suite, no API key required
      POST /v1/webhooks/twilio-demo/voice    — scripted demo line TwiML, no API key (website demo, not framework)
      GET  /v1/demo/call-status              — live demo call status, no API key (website demo, not framework)
      POST /v1/demo/call                     — trigger Beacon outbound demo call, Turnstile+rate-limited (website demo, not framework)
      POST /v1/demo/sms-opt-in               — web opt-in to text the starter-pack link, consent+Turnstile+rate-limited (website demo, not framework)
      POST /v1/webhooks/elevenlabs/postcall  — ElevenLabs post-call webhook for the Beacon demo, no API key (website demo, not framework)
      POST /v1/identity/verify-passport      — verify an NHID-Auth v2 agent passport (src/agent_identity.py), no API key required
      POST /v1/identity/revoke-passport      — durably revoke a delegation_id, API key required
    """
    method = event.get("httpMethod", "POST")
    path = event.get("path", "")

    if method == "GET":
        if "/public/vendor/" in path and path.endswith("/badge"):
            return _handle_badge(event, path)
        if "/vendor/metrics/summary" in path:
            return _handle_metrics_summary(event)
        if "/demo/call-status" in path:
            return _handle_demo_call_status(event)
        return _ok({
            "status": "healthy",
            "policy_engine_version": POLICY_ENGINE_VERSION,
            "nhid_spec_version": NHID_SPEC_VERSION,
        })

    # Twilio scripted inbound demo line (website demo feature, not the framework)
    if "/webhooks/twilio-demo/voice" in path:
        from functions.twilio_demo_handler import _handle_twilio_demo_voice
        return _handle_twilio_demo_voice(event)

    # Starter-pack SMS web opt-in (website demo feature, not the framework)
    if "/demo/sms-opt-in" in path:
        return _handle_demo_sms_optin(event)

    # Beacon outbound call demo (website demo feature, not the framework)
    if "/demo/call" in path:
        return _handle_demo_call(event)

    # ElevenLabs post-call webhook for the Beacon outbound demo (website demo feature)
    if "/webhooks/elevenlabs/postcall" in path:
        from functions.elevenlabs_postcall_handler import _handle_elevenlabs_postcall_webhook
        return _handle_elevenlabs_postcall_webhook(event)

    # NHID-Auth v2 agent passport verification / revocation
    if "/identity/verify-passport" in path:
        return _handle_verify_passport(event)
    if "/identity/revoke-passport" in path:
        return _handle_revoke_passport(event)

    # Pilot enrollment
    if "/pilot/enroll" in path:
        return _handle_pilot_enroll(event)

    # Hosted CTS evaluation
    if "/cts/evaluate" in path:
        return _handle_cts_evaluate(event)

    # Turn-by-turn call-progress webhook (no DB writes, stateless)
    if "/webhooks/call-progress" in path:
        return _handle_call_progress(event)

    # Vendor adapter routes
    if "/adapters/vapi/" in path:
        return _handle_vendor(event, "vapi")
    if "/adapters/twilio/" in path:
        return _handle_vendor(event, "twilio")
    if "/adapters/vonage/" in path:
        return _handle_vendor(event, "vonage")
    if "/adapters/retell/" in path:
        return _handle_vendor(event, "retell")
    if "/adapters/connect/" in path:
        return _handle_vendor(event, "connect")

    # Generic NHID event routes (/v1/conformance/check and /v1/demo/check)
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    if "event" not in body:
        return _error(400, "Missing required field: 'event'")

    session = body.get("session", {})
    policy_event = body["event"]

    try:
        decision = evaluate_all(session, policy_event)
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Policy evaluation failed: {exc}")

    return _ok(_decision_to_dict(decision, policy_event))


def _handle_vendor(event: dict, vendor: str) -> dict:
    """Parse a vendor-native payload, run the adapter, and evaluate conformance."""
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    try:
        if vendor == "vapi":
            from adapters.vapi_adapter import to_nhid_event
            session, policy_event = to_nhid_event(payload)
        elif vendor == "twilio":
            from adapters.twilio_adapter import to_nhid_event as _twilio_to_nhid
            session, policy_event = _twilio_to_nhid(payload)
        elif vendor == "vonage":
            from adapters.vonage_adapter import to_nhid_event as _vonage_to_nhid
            session, policy_event = _vonage_to_nhid(payload)
        elif vendor == "retell":
            from adapters.retell_adapter import to_nhid_event as _retell_to_nhid
            session, policy_event = _retell_to_nhid(payload)
        elif vendor == "connect":
            from adapters.amazon_connect_adapter import to_nhid_event as _connect_to_nhid
            session, policy_event = _connect_to_nhid(payload)
        else:
            return _error(400, f"Unknown vendor: {vendor}")
    except Exception as exc:  # noqa: BLE001
        return _error(400, f"Adapter conversion failed: {exc}")

    try:
        decision = evaluate_all(session, policy_event)
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Policy evaluation failed: {exc}")

    result = _decision_to_dict(decision, policy_event)
    result["vendor"] = vendor
    return _ok(result)


def _handle_call_progress(event: dict) -> dict:
    """Turn-by-turn conformance evaluation. Stateless — caller maintains session_state."""
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    try:
        from adapters.call_progress_adapter import to_nhid_event
        session, policy_event = to_nhid_event(body)
    except (KeyError, ValueError) as exc:
        return _error(400, f"Invalid call-progress payload: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _error(400, f"Adapter conversion failed: {exc}")

    try:
        decision = evaluate_all(session, policy_event)
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Policy evaluation failed: {exc}")

    result = _decision_to_dict(decision, policy_event)
    result["turn_index"] = body.get("turn_index", 0)
    result["session_id"] = body.get("session_id", "")
    return _ok(result)


def _handle_badge(event: dict, path: str) -> dict:
    """Public CAS badge SVG for a vendor. No auth — read-only, score only."""
    # Path shape: /v1/public/vendor/{vendor_id}/badge
    parts = [p for p in path.split("/") if p]
    try:
        vendor_id = parts[parts.index("vendor") + 1]
    except (ValueError, IndexError):
        return _error(400, "Invalid badge path")

    from src.nhid_badge_generator import generate_badge_svg

    score = 0.0
    tier = "No Data"
    try:
        import nhid_event_store as store
        metrics = store.get_vendor_metrics(vendor_id)
        if metrics["calls_total"] > 0:
            score = metrics["cas_avg"]
            tier = None  # derive from score
    except Exception:  # noqa: BLE001 — read-only FS or no DB: keep "No Data" badge
        pass

    svg = generate_badge_svg(vendor_id, score, tier)
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "image/svg+xml",
            "Cache-Control": "max-age=3600",
            **_CORS,
        },
        "body": svg,
    }


def _handle_metrics_summary(event: dict) -> dict:
    """Per-vendor conformance metrics. vendor_id from query string."""
    params = event.get("queryStringParameters") or {}
    vendor_id = (params.get("vendor_id") or "").strip()
    if not vendor_id:
        return _error(400, "Missing required query parameter: vendor_id")

    days_raw = params.get("days", "30")
    try:
        days = max(1, min(365, int(days_raw)))
    except (TypeError, ValueError):
        return _error(400, "Invalid 'days' parameter")

    try:
        import nhid_event_store as store
        metrics = store.get_vendor_metrics(vendor_id, days)
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Metrics query failed: {exc}")

    return _ok(metrics)


def _verify_turnstile(token: str) -> bool:
    """Verify a Cloudflare Turnstile token server-side. False on any failure
    (missing token, missing secret, network error, or Cloudflare rejection) —
    callers should treat that as "reject the request", not "skip the check"."""
    if not token:
        return False
    secret = os.environ.get(TURNSTILE_SECRET_ENV, "")
    if not secret or not _HTTPX_OK:
        return False

    @retry_with_backoff(max_attempts=3)
    def _post():
        resp = httpx.post(
            TURNSTILE_VERIFY_URL,
            data={"secret": secret, "response": token},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp

    try:
        return bool(_post().json().get("success"))
    except Exception:  # noqa: BLE001
        return False


def _source_ip(event: dict) -> str:
    identity = (event.get("requestContext") or {}).get("identity") or {}
    return identity.get("sourceIp") or "unknown"


#: Starter-pack SMS web opt-in — sends real SMS, so rate-limit per IP/number.
_SMS_OPTIN_IP_LIMIT = 5
_SMS_OPTIN_PHONE_LIMIT = 3


def _handle_demo_sms_optin(event: dict) -> dict:
    """Web opt-in: a visitor submits their number + explicit consent on the
    site's /sms-opt-in.html form to receive the one-time starter-pack link by
    text. CAPTCHA- and rate-limited; sends a real SMS via functions.twilio_sms.
    The submitted consent + this server-side gate are the documented A2P 10DLC
    opt-in for the campaign."""
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    # Explicit opt-in consent is mandatory — never text without it.
    if not body.get("consent"):
        return _error(400, "Consent is required to receive a text message")

    if not _verify_turnstile(str(body.get("turnstile_token", ""))):
        return _error(400, "CAPTCHA verification failed")

    phone = str(body.get("phone", "")).strip()
    if not phone:
        return _error(400, "Missing required field: 'phone'")

    digits = re.sub(r"\D", "", phone)
    if not digits.startswith("1"):
        digits = "1" + digits
    if len(digits) != 11:
        return _error(400, "Phone number must be a valid US number in E.164 format")
    e164 = "+" + digits

    from functions import rate_limiter
    if not rate_limiter.check_and_increment(
        f"smsoptin-ip:{_source_ip(event)}",
        limit=_SMS_OPTIN_IP_LIMIT,
        window_seconds=_DEMO_CALL_RATE_LIMIT_WINDOW_SECONDS,
    ):
        return _error(429, "Rate limit exceeded. Please try again later.")
    if not rate_limiter.check_and_increment(
        f"smsoptin-phone:{e164}",
        limit=_SMS_OPTIN_PHONE_LIMIT,
        window_seconds=_DEMO_CALL_RATE_LIMIT_WINDOW_SECONDS,
    ):
        return _error(429, "This number has requested too many texts recently.")

    from functions import twilio_sms
    if not twilio_sms.sms_enabled() or not _HTTPX_OK:
        return _error(503, "SMS service not configured")

    try:
        sent = twilio_sms.send_sms(e164, twilio_sms.starter_pack_body())
    except Exception as exc:  # noqa: BLE001
        return _error(502, f"SMS send failed: {exc}")
    if not sent:
        return _error(502, "SMS send failed")

    return _ok({"status": "sent"})


def _handle_demo_call(event: dict) -> dict:
    """Trigger an outbound ElevenLabs (Beacon) call to the provided phone
    number. The one demo route with real per-call Twilio/ElevenLabs cost --
    gated by Turnstile CAPTCHA and per-IP/per-number rate limits before any
    network call is made."""
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    if not _verify_turnstile(str(body.get("turnstile_token", ""))):
        return _error(400, "CAPTCHA verification failed")

    phone = str(body.get("phone", "")).strip()
    if not phone:
        return _error(400, "Missing required field: 'phone'")

    digits = re.sub(r"\D", "", phone)
    if not digits.startswith("1"):
        digits = "1" + digits
    if len(digits) != 11:
        return _error(400, "Phone number must be a valid US number in E.164 format")
    e164 = "+" + digits

    from functions import rate_limiter
    if not rate_limiter.check_and_increment(
        f"ip:{_source_ip(event)}", limit=_DEMO_CALL_IP_LIMIT, window_seconds=_DEMO_CALL_RATE_LIMIT_WINDOW_SECONDS
    ):
        return _error(429, "Rate limit exceeded. Please try again later.")
    if not rate_limiter.check_and_increment(
        f"phone:{e164}", limit=_DEMO_CALL_PHONE_LIMIT, window_seconds=_DEMO_CALL_RATE_LIMIT_WINDOW_SECONDS
    ):
        return _error(429, "This phone number has received too many demo calls recently.")

    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    phone_number_id = os.environ.get("ELEVENLABS_PHONE_NUMBER_ID", "")
    if not api_key or not phone_number_id or not _HTTPX_OK:
        return _error(503, "Outbound call service not configured")

    url = f"https://api.elevenlabs.io/v1/convai/phone-numbers/{phone_number_id}/outbound-call"

    @retry_with_backoff(max_attempts=3)
    def _post():
        resp = httpx.post(
            url,
            json={"agent_id": _BEACON_AGENT_ID, "to_number": e164},
            headers={"xi-api-key": api_key},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp

    try:
        resp_body = _post().json()
    except Exception as exc:  # noqa: BLE001
        return _error(502, f"Outbound call failed: {exc}")

    return _ok({
        "status": "dialing",
        "call_id": resp_body.get("call_id", resp_body.get("conversation_id", "")),
    })


def _handle_demo_call_status(event: dict) -> dict:
    """Live status for the Twilio scripted demo line. Polled by the website.

    session_id="latest" looks up whichever demo call is most recently in
    progress — visitors watching the site don't know their own call's
    Twilio CallSid, so this lets anyone watch the live call without typing
    anything in.
    """
    params = event.get("queryStringParameters") or {}
    session_id = (params.get("session_id") or "").strip()
    if not session_id:
        return _error(400, "Missing required query parameter: session_id")

    from functions import demo_status_store
    if session_id == "latest":
        session_id = demo_status_store.LATEST_SESSION_KEY

    try:
        status = demo_status_store.get_status(session_id)
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Status lookup failed: {exc}")

    return _ok(status)


def _handle_pilot_enroll(event: dict) -> dict:
    """Pilot enrollment — validates the request and returns next steps."""
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    org_name = str(body.get("org_name", "")).strip()
    contact_email = str(body.get("contact_email", "")).strip()
    if not org_name:
        return _error(400, "Missing required field: 'org_name'")
    if not contact_email or "@" not in contact_email:
        return _error(400, "Missing or invalid field: 'contact_email'")

    import uuid as _uuid
    pilot_id = f"pilot-{_uuid.uuid4().hex[:12]}"

    return _ok({
        "pilot_id": pilot_id,
        "org_name": org_name,
        "status": "enrolled",
        "next_steps_url": "https://nhid-clinical.org/shadow-evaluation-guide.html",
        "next_steps": [
            "Read the 90-day shadow evaluation guide",
            "Run baseline calls through POST /v1/demo/check or a vendor adapter route",
            "Generate your pilot report with tools/pilot_report_generator.py",
        ],
    })


def _handle_cts_evaluate(event: dict) -> dict:
    """Run the NHID CTS YAML test cases and return structured results."""
    raw_body = event.get("body") or "{}"
    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    test_ids = body.get("test_ids") or None
    if test_ids is not None and not isinstance(test_ids, list):
        return _error(400, "'test_ids' must be a list of strings")

    try:
        from src.cts_runner import run_cts
        report = run_cts(test_ids=test_ids)
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"CTS evaluation failed: {exc}")

    return _ok(report)


def _handle_verify_passport(event: dict) -> dict:
    """Verify an NHID-Auth v2 agent passport (src/agent_identity.py).

    AgentIdentityManager.verify_passport() only checks its own in-memory
    revocation dicts, which are empty on every fresh Lambda invocation — so
    this also checks nhid_event_store's durable revoked_delegations table,
    which is the revocation store of record across invocations.
    """
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    delegation_raw = body.get("delegation")
    signature_b64 = body.get("signature_b64")
    agent_signature_b64 = body.get("agent_signature_b64")
    provider_public_key_b64 = body.get("provider_public_key_b64")
    if not delegation_raw or not signature_b64 or not agent_signature_b64 or not provider_public_key_b64:
        return _error(
            400,
            "Missing required fields: 'delegation', 'signature_b64', "
            "'agent_signature_b64', 'provider_public_key_b64'",
        )

    try:
        from src.agent_identity import AgentIdentityManager, AgentPassport, Delegation
        delegation = Delegation.from_json(json.dumps(delegation_raw))
        passport = AgentPassport(
            delegation=delegation,
            signature_b64=signature_b64,
            agent_signature_b64=agent_signature_b64,
        )
        manager = AgentIdentityManager()
        provider_pub = manager.b64_to_public_key(provider_public_key_b64)
    except Exception as exc:  # noqa: BLE001
        return _error(400, f"Invalid passport payload: {exc}")

    required_scope = body.get("required_scope")
    if required_scope is not None and not isinstance(required_scope, list):
        return _error(400, "'required_scope' must be a list of strings")

    result = manager.verify_passport(
        passport,
        provider_pub,
        call_sid=str(body.get("call_sid", "")),
        required_scope=required_scope,
    )

    if result.valid:
        try:
            import nhid_event_store as store
            if store.is_delegation_revoked(delegation.delegation_id):
                result = type(result)(False, "ERR_REVOKED", delegation_id=delegation.delegation_id)
        except Exception:  # noqa: BLE001 — read-only FS or no DB: fall back to library-only check
            pass

    return _ok({
        "valid": result.valid,
        "reason": result.reason,
        "delegation_id": result.delegation_id,
        "provider_npi": result.provider_npi,
        "agent_id": result.agent_id,
        "scope": result.scope,
    })


def _handle_revoke_passport(event: dict) -> dict:
    """Durably revoke a delegation_id, surviving across stateless invocations."""
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    delegation_id = str(body.get("delegation_id", "")).strip()
    if not delegation_id:
        return _error(400, "Missing required field: 'delegation_id'")

    try:
        import nhid_event_store as store
        store.record_revocation(delegation_id, reason=str(body.get("reason", "")))
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Revocation failed: {exc}")

    return _ok({"delegation_id": delegation_id, "revoked": True})


def _policy_cas(decision, event: dict) -> dict:
    """Disclosure-level CAS derived from policy violations and event audit fields.

    F_IAF: 1.0 if no IDG-01/PDX-01 violations (identity gates clear)
    F_NOCF: approximated from violation severity pattern
    ECF: fraction of core NHID event audit fields present in the event

    Note: this is a disclosure-focused CAS. For the full NOCF telemetry-based
    CAS, use src/nhid_cas.compute_cas() with operational metrics.
    """
    violations = decision.violations
    critical_ids = {v.rule_id for v in violations if v.severity.value == "critical"}

    F_IAF = 0.0 if ("IDG-01" in critical_ids or "PDX-01" in critical_ids) else 1.0

    critical_count = sum(1 for v in violations if v.severity.value == "critical")
    if critical_count == 0:
        F_NOCF = 0.90
    elif critical_count == 1:
        F_NOCF = 0.50
    else:
        F_NOCF = 0.25

    _CORE_FIELDS = ("event_id", "timestamp", "session_id", "event_type")
    present = sum(1 for f in _CORE_FIELDS if event.get(f) is not None)
    ECF = round(present / len(_CORE_FIELDS), 4)

    cas = round(F_IAF * F_NOCF * ECF, 4)
    tier, badge = _tier_for_cas(cas)

    return {
        "score": cas,
        "tier": tier,
        "badge_eligible": badge,
        "F_IAF": F_IAF,
        "F_NOCF": round(F_NOCF, 4),
        "ECF": ECF,
    }


def _route_for_human_review(decision, cas: dict, event: dict) -> dict:
    """Queue the session for human review per docs/dbc01-human-review-sop.md
    if it meets either routing criterion. Never raises — a queueing failure
    (e.g. read-only FS, no DB available) must not break the conformance
    response itself."""
    routing = should_route_to_review(decision, cas)
    if not routing.route:
        return {"queued": False, "trigger_reason": None, "queue_id": None}

    queue_id = None
    try:
        import nhid_event_store as store
        governance = event.get("healthcare_governance") or {}
        row = store.enqueue_dbc01_review(
            session_id=event.get("session_id"),
            event_id=event.get("event_id"),
            request_id=event.get("request_id"),
            trigger_reason=routing.trigger_reason,
            severity=routing.severity,
            identity_assertion_text=governance.get("identity_assertion_text"),
            cas_score=cas.get("score"),
            cas_tier=cas.get("tier"),
        )
        queue_id = row.get("id")
    except Exception:  # noqa: BLE001 — read-only FS or no DB: still report the routing decision
        pass

    return {"queued": queue_id is not None, "trigger_reason": routing.trigger_reason, "queue_id": queue_id}


def _decision_to_dict(decision, event: dict | None = None) -> dict:
    event = event or {}
    cas = _policy_cas(decision, event)
    result = {
        "conformant": len(decision.violations) == 0,
        "action": decision.action.value,
        "reason_code": decision.reason_code,
        "policy_version": decision.policy_version,
        "violations": [
            {
                "rule_id": v.rule_id,
                "description": v.description,
                "severity": v.severity.value,
            }
            for v in decision.violations
        ],
        "next_state": decision.next_state,
        "twiml_fallback": decision.twiml_fallback,
        "gather_speech": decision.gather_speech,
        "cas": cas,
        "human_review": _route_for_human_review(decision, cas, event),
    }
    return result


_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,x-api-key",
    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
}


def _ok(body: dict) -> dict:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps({"error": message}),
    }
