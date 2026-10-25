"""Lambda handler for the NHID Clinical conformance check API."""
import json
import os
import re
import sys
from typing import Any, Optional

# When SAM packages with CodeUri: ., the repo root is /var/task.
# This insert ensures `src` and `adapters` are importable whether running locally or in Lambda.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nhid_policy_engine_v1 import (  # noqa: E402
    POLICY_ENGINE_VERSION,
    NHID_SPEC_VERSION,
    evaluate_all,
)
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
      GET  /v1/vendor/metrics/summary        — per-vendor metrics, API key required
      POST /v1/pilot/enroll                  — pilot enrollment, no API key required
      POST /v1/cts/evaluate                  — run conformance test suite, no API key required
      POST /v1/webhooks/twilio-demo/voice    — scripted demo line TwiML, no API key (website demo, not framework)
      GET  /v1/demo/call-status              — live demo call status, no API key (website demo, not framework)
      POST /v1/demo/call                     — trigger Beacon outbound demo call, Turnstile+rate-limited (website demo, not framework)
      POST /v1/demo/sms-opt-in               — web opt-in to text the starter-pack link, consent+Turnstile+rate-limited (website demo, not framework)
      POST /v1/webhooks/elevenlabs/postcall  — ElevenLabs post-call webhook for the Beacon demo, no API key (website demo, not framework)
      POST /v1/identity/verify-passport      — verify an agent passport against a CALLER-SUPPLIED provider key: a consistency check, not a trust decision, no API key required
      POST /v2/identity/verify-passport      — verify against a SERVER-CONFIGURED trust anchor, with durable revocation and optional proof of possession, API key required
      POST /v1/identity/revoke-passport      — durably revoke a delegation_id, API key required
    """
    method = event.get("httpMethod", "POST")
    path = event.get("path", "")

    if method == "GET":
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

    # NHID-Auth v2 agent passport verification / revocation.
    # v2 is matched first: "/identity/verify-passport" is a substring of the
    # v2 path, so testing v1 first would swallow every v2 request.
    if "/v2/identity/verify-passport" in path:
        return _handle_verify_passport_v2(event)
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
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

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
    payload, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

    try:
        if vendor == "vapi":
            from adapters.vapi_adapter import to_nhid_event
            session, policy_event = to_nhid_event(payload)
        elif vendor == "twilio":
            from adapters.twilio_adapter import to_nhid_event as _twilio_to_nhid
            session, policy_event = _twilio_to_nhid(payload)
        elif vendor == "vonage":
            from adapters.archive.vonage_adapter import to_nhid_event as _vonage_to_nhid
            session, policy_event = _vonage_to_nhid(payload)
        elif vendor == "retell":
            from adapters.archive.retell_adapter import to_nhid_event as _retell_to_nhid
            session, policy_event = _retell_to_nhid(payload)
        elif vendor == "connect":
            from adapters.archive.amazon_connect_adapter import to_nhid_event as _connect_to_nhid
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
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

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
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

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
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

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
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

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
    body, parse_error = _parse_json_body(event, allow_empty=True)
    if parse_error:
        return parse_error

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
    """Check an agent passport against a provider key the **caller** supplies.

    **This is a consistency check, not a trust decision**, and the response
    says so in its `trust` field. The route is handed both the passport and
    the key it should verify against, so a `valid: true` means only that those
    two agree. It cannot mean the issuer is trusted: the caller chose the
    issuer. Anyone can mint a keypair, sign a delegation naming any NPI, and
    get `valid: true` from this route.

    For an answer that depends on who the signer is, use
    `/v2/identity/verify-passport`, which resolves the provider key from this
    deployment's configured trust anchors and refuses a caller-supplied one.

    AgentIdentityManager.verify_passport() only checks its own in-memory
    revocation dicts, which are empty on every fresh Lambda invocation — so
    this also checks nhid_event_store's durable revoked_delegations table,
    which is the revocation store of record across invocations. Note that the
    durable check is best-effort here: an unreachable store falls back to the
    library-only check, which on a fresh manager is no revocation check at
    all. v2 returns 503 in that situation instead.
    """
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

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

    # A passport presented on its own is claiming provider authority on its
    # own, so it must name a provider. Without this the route answered
    # `valid: true` with `provider_npi: ""` for a delegation that asserts no
    # authority at all.
    result = manager.verify_passport(
        passport,
        provider_pub,
        call_sid=str(body.get("call_sid", "")),
        required_scope=required_scope,
        require_npi=True,
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
        # Named explicitly so no integrator mistakes this for a trust
        # decision. The provider key came from the request, so a `valid: true`
        # here says the passport is internally consistent with a key the
        # caller chose — it cannot say the issuer is trusted, because the
        # caller supplied both halves of that question.
        "trust": "caller_supplied_key",
    })


#: Server-configured trust anchors for the v2 verify route, as
#: NHID_TRUST_ANCHORS="<npi>:<base64 key>[:<kid>],<npi>:<key>[:<kid>]".
#:
#: The v1 route takes the provider key from the request body, which proves a
#: passport is internally consistent and nothing about whether its issuer is
#: trusted — the caller supplied both halves. v2 resolves the key from this
#: configuration instead, so "valid" means "signed by a provider this
#: deployment decided to trust".
_TRUST_ANCHOR_ENV = "NHID_TRUST_ANCHORS"


def _configured_trust_anchors():
    """Build a resolver from the environment, or None if none is configured.

    Returns None rather than an empty resolver so the route can tell "this
    deployment has not configured trust anchors" (a 503 — it cannot answer the
    question) from "this provider is not trusted" (a verification failure).
    """
    raw = (os.environ.get(_TRUST_ANCHOR_ENV) or "").strip()
    if not raw:
        return None
    from src.trust_anchor import StaticTrustAnchorResolver

    resolver = StaticTrustAnchorResolver()
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) == 2:
            npi, key_b64, kid = parts[0], parts[1], ""
        elif len(parts) == 3:
            npi, key_b64, kid = parts
        else:
            raise ValueError(
                f"{_TRUST_ANCHOR_ENV} entry {entry!r} must be "
                f"'<npi>:<key>' or '<npi>:<key>:<kid>'"
            )
        resolver.add(npi.strip(), key_b64.strip(), kid.strip())
    return resolver


def _handle_verify_passport_v2(event: dict) -> dict:
    """Verify a passport against a trust anchor this deployment configured.

    Differences from v1, all of them the point of the route:
      * the provider key is **resolved by NPI and kid** from server
        configuration, never read from the request body;
      * the durable revocation store is consulted and a failure to reach it is
        a 503, not a silent fallback to the in-memory check;
      * an optional presentation proof can be required, so the caller must
        prove it holds the agent key now rather than merely holding bytes that
        once verified.
    """
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

    try:
        resolver = _configured_trust_anchors()
    except ValueError as exc:
        return _error(500, f"Trust anchor configuration is invalid: {exc}")
    if resolver is None:
        return _error(
            503,
            f"No trust anchors are configured. Set {_TRUST_ANCHOR_ENV} to "
            f"'<npi>:<base64-ed25519-key>[:<kid>]' entries. Without one this "
            f"route cannot establish who signed a delegation, and answering "
            f"would only restate the caller's own assumption.",
        )

    delegation_raw = body.get("delegation")
    signature_b64 = body.get("signature_b64")
    agent_signature_b64 = body.get("agent_signature_b64")
    if not delegation_raw or not signature_b64 or not agent_signature_b64:
        return _error(
            400,
            "Missing required fields: 'delegation', 'signature_b64', "
            "'agent_signature_b64'",
        )
    if body.get("provider_public_key_b64"):
        return _error(
            400,
            "'provider_public_key_b64' is not accepted on this route. The "
            "provider key is resolved from this deployment's configured trust "
            "anchors; a caller-supplied key would make the result a "
            "consistency check rather than a trust decision. Use "
            "/v1/identity/verify-passport if that is what you want.",
        )

    try:
        from src.agent_identity import (
            AgentIdentityManager, AgentPassport, Delegation, PresentationProof,
        )
        delegation = Delegation.from_json(json.dumps(delegation_raw))
        passport = AgentPassport(
            delegation=delegation,
            signature_b64=signature_b64,
            agent_signature_b64=agent_signature_b64,
        )
        manager = AgentIdentityManager()
    except Exception as exc:  # noqa: BLE001
        return _error(400, f"Invalid passport payload: {exc}")

    required_scope = body.get("required_scope")
    if required_scope is not None and not isinstance(required_scope, list):
        return _error(400, "'required_scope' must be a list of strings")

    verifier_nonce = str(body.get("verifier_nonce", ""))
    proof = None
    proof_raw = body.get("presentation_proof")
    if proof_raw is not None:
        if not isinstance(proof_raw, dict):
            return _error(400, "'presentation_proof' must be an object")
        try:
            proof = PresentationProof(**proof_raw)
        except Exception as exc:  # noqa: BLE001
            return _error(400, f"Invalid presentation_proof: {exc}")

    provider_pub = resolver.resolve(delegation.provider_npi, delegation.kid)
    if provider_pub is None:
        return _ok({
            "valid": False,
            "reason": "ERR_TRUST_ANCHOR_UNRESOLVED",
            "delegation_id": delegation.delegation_id,
            "provider_npi": delegation.provider_npi,
            "agent_id": None,
            "scope": None,
            "trust": "configured_trust_anchor",
        })

    result = manager.verify_passport(
        passport,
        provider_pub,
        call_sid=str(body.get("call_sid", "")),
        required_scope=required_scope,
        require_npi=True,
        verifier_nonce=verifier_nonce,
        proof=proof,
    )

    # Revocation is not optional here, and an unreachable store is an answer
    # this route cannot give rather than a pass. v1 swallows the error and
    # falls back to the in-memory check, which on a fresh manager is no check.
    if result.valid:
        try:
            import nhid_event_store as store
            if store.is_delegation_revoked(delegation.delegation_id):
                result = type(result)(
                    False, "ERR_REVOKED", delegation_id=delegation.delegation_id
                )
        except Exception as exc:  # noqa: BLE001
            return _error(
                503,
                f"Revocation store is unreachable, so this passport cannot be "
                f"confirmed live: {exc}",
            )

    return _ok({
        "valid": result.valid,
        "reason": result.reason,
        "delegation_id": result.delegation_id,
        "provider_npi": result.provider_npi,
        "agent_id": result.agent_id,
        "scope": result.scope,
        "trust": "configured_trust_anchor",
        "possession_proved": bool(verifier_nonce) and result.valid,
    })


def _handle_revoke_passport(event: dict) -> dict:
    """Durably revoke a delegation_id, surviving across stateless invocations."""
    body, parse_error = _parse_json_body(event)
    if parse_error:
        return parse_error

    delegation_id = str(body.get("delegation_id", "")).strip()
    if not delegation_id:
        return _error(400, "Missing required field: 'delegation_id'")

    try:
        import nhid_event_store as store
        store.record_revocation(delegation_id, reason=str(body.get("reason", "")))
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Revocation failed: {exc}")

    return _ok({"delegation_id": delegation_id, "revoked": True})


_EVIDENCE_FIELDS = ("event_id", "timestamp", "session_id", "event_type")


def _evidence_completeness(event: dict) -> dict:
    """How much of the core NHID audit record this event actually carries.

    This replaces the former composite CAS score, which blended an identity
    factor, an approximated operational factor and this completeness fraction
    into one number, then mapped it to a "Verified Trust" / "Conditional Trust"
    tier. That score is withdrawn: it mixed heterogeneous denominators, and the
    tier vocabulary read as a certification this project does not issue.

    What survives is the one component with independent meaning and a denominator
    that can be stated out loud: the fraction of core audit fields present. It is
    reported as a fraction with its denominator, never as a grade.
    """
    present = sum(1 for f in _EVIDENCE_FIELDS if event.get(f) is not None)
    return {
        "present": present,
        "expected": len(_EVIDENCE_FIELDS),
        "fraction": round(present / len(_EVIDENCE_FIELDS), 4),
        "fields": list(_EVIDENCE_FIELDS),
    }


def _route_for_human_review(decision, event: dict) -> dict:
    """Queue the session for human review per docs/dbc01-human-review-sop.md
    if it meets the routing criterion. Never raises — a queueing failure
    (e.g. read-only FS, no DB available) must not break the conformance
    response itself."""
    routing = should_route_to_review(decision)
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
            cas_score=None,
            cas_tier=None,
        )
        queue_id = row.get("id")
    except Exception:  # noqa: BLE001 — read-only FS or no DB: still report the routing decision
        pass

    return {"queued": queue_id is not None, "trigger_reason": routing.trigger_reason, "queue_id": queue_id}


def _decision_to_dict(decision, event: dict | None = None) -> dict:
    event = event or {}
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
        "evidence_completeness": _evidence_completeness(event),
        "human_review": _route_for_human_review(decision, event),
    }
    return result


_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,x-api-key",
    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
}


#: Largest request body this function will attempt to parse. API Gateway's own
#: ceiling for a REST API is 10 MB; this is well under it because every payload
#: these routes accept — one NHID event, one passport, one scenario list — is
#: kilobytes. A body larger than this is refused before `json.loads` sees it.
MAX_BODY_BYTES = 2 * 1024 * 1024

#: Deepest JSON nesting a request body may carry. The real events are four or
#: five levels deep; sixty-four is generous. The limit is enforced by counting
#: brackets before parsing, not by catching `RecursionError` from the parser:
#: on Python 3.14 a 5,000-level object no longer raises it, so a guard that
#: relied on it returned 200 to the exact request it existed to refuse.
MAX_JSON_DEPTH = 64


def _json_nesting_depth(raw) -> int:
    """Maximum bracket depth of a JSON text, ignoring brackets inside strings."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    depth = deepest = 0
    in_string = escaped = False
    for ch in raw:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            if depth > deepest:
                deepest = depth
                if deepest > MAX_JSON_DEPTH:
                    return deepest  # no need to read the rest
        elif ch in "]}":
            depth -= 1
    return deepest


def _parse_json_body(
    event: dict, *, require_object: bool = True, allow_empty: bool = False
) -> tuple[Any, Optional[dict]]:
    """Parse a request body into JSON, or return the 400 to send instead.

    Returns `(parsed, None)` on success and `(None, error_response)` on failure,
    so a route reads:

        body, err = _parse_json_body(event)
        if err:
            return err

    Every route used to inline `json.loads` guarded by `json.JSONDecodeError`
    alone. That is not the only way parsing fails: CPython's JSON decoder
    recurses per nesting level, so a body of 60,000 open brackets raises
    `RecursionError`, which no route caught — one trivially-crafted request
    produced an unhandled exception and a 502 on four routes. Depth is the
    attack, not size, so the breadth of this `except` is the actual fix and the
    size cap is a second line.

    `require_object` rejects a body that parses but is not a JSON object, which
    every one of these routes assumes when it calls `.get(...)` on the result.
    """
    raw_body = event.get("body") or ""
    if not raw_body:
        # Some routes treat an absent body as "no options supplied" rather than
        # as a malformed request.
        if allow_empty:
            return ({} if require_object else None), None
        return None, _error(400, "Request body is required")

    if isinstance(raw_body, (str, bytes)) and len(raw_body) > MAX_BODY_BYTES:
        return None, _error(
            413,
            f"Request body is {len(raw_body)} bytes; the limit is "
            f"{MAX_BODY_BYTES}",
        )

    if isinstance(raw_body, (str, bytes)):
        depth = _json_nesting_depth(raw_body)
        if depth > MAX_JSON_DEPTH:
            return None, _error(
                400,
                f"Invalid JSON: nesting depth exceeds {MAX_JSON_DEPTH}",
            )

    try:
        parsed = json.loads(raw_body) if isinstance(raw_body, (str, bytes)) else raw_body
    except (json.JSONDecodeError, RecursionError, ValueError, UnicodeDecodeError) as exc:
        # RecursionError is not a ValueError and JSONDecodeError does not cover
        # it, so it has to be named explicitly.
        return None, _error(400, f"Invalid JSON: {exc}")

    if require_object and not isinstance(parsed, dict):
        return None, _error(
            400,
            f"Request body must be a JSON object, got "
            f"{type(parsed).__name__}",
        )

    return parsed, None


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
