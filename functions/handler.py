"""Lambda handler for the NHID Clinical conformance check API."""
import json
import os
import sys

# When SAM packages with CodeUri: ., the repo root is /var/task.
# This insert ensures `src` and `adapters` are importable whether running locally or in Lambda.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nhid_policy_engine_v1 import (  # noqa: E402
    POLICY_ENGINE_VERSION,
    NHID_SPEC_VERSION,
    evaluate_all,
)


def lambda_handler(event: dict, context) -> dict:
    """
    Routes:
      GET  /health                      — liveness probe, no API key required
      POST /v1/conformance/check        — evaluate an NHID event, API key required
      POST /v1/demo/check               — same as conformance/check, no API key required
      POST /v1/adapters/vapi/check      — accepts native VAPI call payload, no API key
      POST /v1/adapters/twilio/check    — accepts native Twilio call payload, no API key
    """
    method = event.get("httpMethod", "POST")
    path = event.get("path", "")

    if method == "GET":
        return _ok({
            "status": "healthy",
            "policy_engine_version": POLICY_ENGINE_VERSION,
            "nhid_spec_version": NHID_SPEC_VERSION,
        })

    # Vendor adapter routes
    if "/adapters/vapi/" in path:
        return _handle_vendor(event, "vapi")
    if "/adapters/twilio/" in path:
        return _handle_vendor(event, "twilio")

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

    return _ok(_decision_to_dict(decision))


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
        else:
            return _error(400, f"Unknown vendor: {vendor}")
    except Exception as exc:  # noqa: BLE001
        return _error(400, f"Adapter conversion failed: {exc}")

    try:
        decision = evaluate_all(session, policy_event)
    except Exception as exc:  # noqa: BLE001
        return _error(500, f"Policy evaluation failed: {exc}")

    result = _decision_to_dict(decision)
    result["vendor"] = vendor
    return _ok(result)


def _decision_to_dict(decision) -> dict:
    return {
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
    }


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
