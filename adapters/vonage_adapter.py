"""
NHID-Clinical – Vonage Voice API Adapter
==========================================
Converts a Vonage Voice API call transcript payload to an NHID-Clinical
v1.3 event trace and to a (session, event) pair for evaluate_all().

Vonage input format (NLP/ASR call transcript webhook):
  {
    "uuid": "call_abc123",
    "conversation_uuid": "con_abc123",
    "start_time": "2026-06-12T00:00:00Z",
    "transcript": [
      {"start_time": "0.00", "duration": "2.5", "speech": "...", "speaker": "bot"},
      {"start_time": "3.00", "duration": "1.5", "speech": "...", "speaker": "user"}
    ]
  }

Usage:
  from adapters.vonage_adapter import to_nhid_event
  session, event = to_nhid_event(vonage_payload)
  decision = evaluate_all(session, event)

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

DISCLOSURE_KEYWORDS = {"automated", "agent", "system", "virtual", "bot", "ai"}

DATA_REQUEST_KEYWORDS = {
    "npi", "member id", "member number", "claim number",
    "date of birth", "dob", "tax id", "ein", "group number",
}

ESCALATION_KEYWORDS = ("transfer", "human", "representative", "speak to someone", "agent please")


def _detect_disclosure(text: str) -> bool:
    normalized = text.lower()
    return any(kw in normalized for kw in DISCLOSURE_KEYWORDS)


def _detect_phi(text: str) -> list[str]:
    normalized = text.lower()
    return [kw for kw in DATA_REQUEST_KEYWORDS if kw in normalized]


def _detect_escalation(text: str) -> bool:
    normalized = text.lower()
    return any(kw in normalized for kw in ESCALATION_KEYWORDS)


def to_nhid_event(vonage_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Convert a Vonage call transcript payload to an NHID-Clinical (session, event) pair.

    Args:
        vonage_payload: Dict with uuid, start_time, and transcript list.

    Returns:
        (session_dict, event_dict) ready for evaluate_all().
    """
    call_id = vonage_payload.get("uuid") or vonage_payload.get("conversation_uuid", "unknown")
    start_time = vonage_payload.get("start_time", datetime.now(timezone.utc).isoformat())
    transcript = vonage_payload.get("transcript", [])

    disclosure_ts: str | None = None
    identity_assertion_text = ""
    phi_accessed: list[str] = []
    escalation_ts: str | None = None
    turn_count = len(transcript)

    for entry in transcript:
        # Vonage uses "speaker": "bot" or "user"
        speaker = str(entry.get("speaker", "")).lower()
        speech = str(entry.get("speech", entry.get("text", "")) or "")
        entry_time = str(entry.get("start_time", "0"))

        try:
            offset_secs = float(entry_time)
        except (ValueError, TypeError):
            offset_secs = 0.0

        if speaker == "bot":
            if disclosure_ts is None and _detect_disclosure(speech):
                disclosure_ts = _offset_to_iso(start_time, offset_secs)
                identity_assertion_text = speech
        elif speaker == "user":
            phi_accessed.extend(_detect_phi(speech))
            if not escalation_ts and _detect_escalation(speech):
                escalation_ts = _offset_to_iso(start_time, offset_secs)

    now = datetime.now(timezone.utc).isoformat()

    session: dict[str, Any] = {
        "turn_count": turn_count,
        "escalation_path_available": True,
    }

    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": now,
        "session_id": call_id,
        "request_id": f"req-{call_id}",
        "event_type": "POLICY",
        "actor_id": f"vonage-{call_id}",
        "state_before": "ACTIVE",
        "state_after": "ACTIVE",
        "replay_mode": "live",
        "external_calls_cached": False,
        "counterparty_type": "human_operator",
        "healthcare_governance": {
            "disclosure_timestamp": disclosure_ts,
            "identity_assertion_text": identity_assertion_text,
            "deceptive_artifact_flags": [],
            "escalation_timestamp": escalation_ts,
            "escalation_outcome": None,
            "phi_accessed": list(set(phi_accessed)),
        },
        "input_payload": {
            "speech_text": _last_user_speech(transcript),
            "raw_form_fields": None,
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
    }

    return session, event


def _offset_to_iso(start_time: str, offset_secs: float) -> str:
    """Add offset_secs to an ISO 8601 start_time string."""
    try:
        base = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        from datetime import timedelta
        return (base + timedelta(seconds=offset_secs)).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _last_user_speech(transcript: list[dict]) -> str:
    for entry in reversed(transcript):
        if str(entry.get("speaker", "")).lower() == "user":
            return str(entry.get("speech", entry.get("text", "")) or "")
    return ""
