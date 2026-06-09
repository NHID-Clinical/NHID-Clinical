"""
NHID-Clinical – VAPI Adapter
==============================
Converts a VAPI call payload to an NHID-Clinical v1.3 event trace and to a
(session, event) pair suitable for direct use with evaluate_all().

VAPI input format:
  {
    "call": {"id": "call_abc123", "startedAt": "2026-06-09T10:00:00Z"},
    "messages": [
      {"role": "bot",  "message": "...", "secondsFromStart": 0.0},
      {"role": "user", "message": "...", "secondsFromStart": 4.2}
    ]
  }

Usage:
  from adapters.vapi_adapter import to_nhid_event
  session, event = to_nhid_event(vapi_payload)
  decision = evaluate_all(session, event)

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

DISCLOSURE_KEYWORDS = {"automated", "agent", "system", "virtual", "bot", "ai"}

DATA_REQUEST_KEYWORDS = {
    "npi", "member id", "member number", "claim number",
    "date of birth", "dob", "tax id", "ein", "group number",
}

ESCALATION_KEYWORDS = ("transfer", "human", "representative", "speak to someone", "agent please")


def vapi_to_nhid_trace(vapi_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a VAPI call payload to an NHID-Clinical v1.3 event trace.

    Args:
        vapi_payload: Dict with keys:
            - call.id (str): VAPI call identifier
            - call.startedAt (str): ISO 8601 call start timestamp
            - messages (list): [{role, message, secondsFromStart}, ...]

    Returns:
        NHID-Clinical trace dict with events and compliance summary.
    """
    call = vapi_payload.get("call", {})
    call_id = call.get("id", "unknown")
    start_time = call.get("startedAt", "")
    messages = vapi_payload.get("messages", [])

    events: list[dict[str, Any]] = []
    disclosure_timestamp: float | None = None
    first_data_request_timestamp: float | None = None

    for msg in messages:
        role = msg.get("role", "unknown")
        original_text = msg.get("message", "")
        text = original_text.lower()
        ts = float(msg.get("secondsFromStart", 0.0))

        # VAPI uses "bot" for the AI agent, "user" for the human caller
        speaker = "agent" if role == "bot" else ("human" if role == "user" else "unknown")

        words = set(text.replace(",", " ").replace(".", " ").split())

        if DISCLOSURE_KEYWORDS & words and speaker in ("agent", "unknown"):
            if disclosure_timestamp is None:
                disclosure_timestamp = ts
            events.append({
                "event_type": "DISCLOSURE",
                "timestamp_offset_s": ts,
                "speaker": speaker,
                "text_snippet": original_text[:120],
                "nhid_rule": "IDG-01",
            })

        elif DATA_REQUEST_KEYWORDS & words:
            if first_data_request_timestamp is None:
                first_data_request_timestamp = ts
            events.append({
                "event_type": "DATA_REQUEST",
                "timestamp_offset_s": ts,
                "speaker": speaker,
                "text_snippet": original_text[:120],
                "nhid_rule": "PDX-01",
            })

        elif any(kw in text for kw in ESCALATION_KEYWORDS):
            events.append({
                "event_type": "ESCALATION_REQUEST",
                "timestamp_offset_s": ts,
                "speaker": speaker,
                "text_snippet": original_text[:120],
                "nhid_rule": "EIT-01",
            })

    # IDG-01: disclosure must precede any data request
    if disclosure_timestamp is None:
        idg01 = "FAIL – no disclosure detected"
    elif (
        first_data_request_timestamp is not None
        and disclosure_timestamp > first_data_request_timestamp
    ):
        idg01 = "FAIL – disclosure occurred after data request (impersonation latency)"
    else:
        idg01 = "PASS"

    return {
        "trace_id": f"vapi_{call_id}",
        "source_format": "vapi_call",
        "correlation_id": call_id,
        "call_start_time": start_time,
        "policy_version": "1.3",
        "nhid_schema_version": "1.0",
        "events": events,
        "compliance": {
            "IDG-01": idg01,
            "disclosure_timestamp_offset_s": disclosure_timestamp,
            "first_data_request_offset_s": first_data_request_timestamp,
            "disclosure_made": disclosure_timestamp is not None,
        },
    }


def to_nhid_event(vapi_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Convert a VAPI call payload to a (session, event) pair for evaluate_all().

    Returns:
        (session_dict, event_dict) ready for src.nhid_policy_engine_v1.evaluate_all()
    """
    call = vapi_payload.get("call", {})
    call_id = call.get("id", str(uuid.uuid4()))
    start_time = call.get("startedAt", datetime.now(timezone.utc).isoformat())
    messages = vapi_payload.get("messages", [])

    trace = vapi_to_nhid_trace(vapi_payload)
    compliance = trace["compliance"]

    # Extract disclosure text and latest user speech from messages
    disclosure_text = ""
    latest_user_speech = ""
    escalation_requested = False

    for msg in messages:
        role = msg.get("role", "unknown")
        original_text = msg.get("message", "")
        text = original_text.lower()
        words = set(text.replace(",", " ").replace(".", " ").split())

        if role in ("bot", "unknown") and DISCLOSURE_KEYWORDS & words and not disclosure_text:
            disclosure_text = original_text

        if role == "user":
            latest_user_speech = original_text
            if any(kw in text for kw in ESCALATION_KEYWORDS):
                escalation_requested = True

    session: dict[str, Any] = {
        "turn_count": len(messages),
        "escalation_path_available": True,
    }

    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": start_time,
        "session_id": call_id,
        "request_id": f"req-{call_id}",
        "event_type": "POLICY",
        "actor_id": f"vapi-{call_id}",
        "state_before": "ACTIVE",
        "state_after": "ACTIVE",
        "replay_mode": "live",
        "external_calls_cached": False,
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "counterparty_type": "human_operator",
        "healthcare_governance": {
            "disclosure_timestamp": start_time if compliance["disclosure_made"] else None,
            "identity_assertion_text": disclosure_text,
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": [],
        },
        "input_payload": {
            "speech_text": latest_user_speech,
            "raw_form_fields": None,
        },
        "output_payload": None,
        "error": None,
        "policy_decision": None,
    }

    return session, event


# ---------------------------------------------------------------------------
# Example / smoke test
# ---------------------------------------------------------------------------

SAMPLE_VAPI_COMPLIANT = {
    "call": {"id": "call_vapi_compliant_001", "startedAt": "2026-06-09T10:00:00Z"},
    "messages": [
        {
            "role": "bot",
            "message": "Hello, I am an automated system calling on behalf of ABC Medical Group. I am not a human representative.",
            "secondsFromStart": 0.5,
        },
        {"role": "user", "message": "Okay, understood.", "secondsFromStart": 4.2},
        {
            "role": "bot",
            "message": "Can I get the NPI number for the ordering provider please?",
            "secondsFromStart": 6.1,
        },
        {"role": "user", "message": "Sure, it's 1234567890.", "secondsFromStart": 9.3},
    ],
}

SAMPLE_VAPI_NONCOMPLIANT = {
    "call": {"id": "call_vapi_noncompliant_001", "startedAt": "2026-06-09T10:05:00Z"},
    "messages": [
        {
            "role": "bot",
            "message": "Hi, can I get the member ID and NPI for this authorization request?",
            "secondsFromStart": 0.3,
        },
        {
            "role": "user",
            "message": "Sure — member ID is 789-XX-4421, NPI is 1234567890.",
            "secondsFromStart": 3.1,
        },
        {
            "role": "bot",
            "message": "Thank you. By the way, I am an automated system.",
            "secondsFromStart": 5.8,
        },
    ],
}


if __name__ == "__main__":
    print("=== Compliant VAPI call ===")
    print(json.dumps(vapi_to_nhid_trace(SAMPLE_VAPI_COMPLIANT), indent=2))

    print("\n=== Non-compliant VAPI call (PHI before disclosure) ===")
    print(json.dumps(vapi_to_nhid_trace(SAMPLE_VAPI_NONCOMPLIANT), indent=2))
