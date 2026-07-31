"""
NHID-Clinical – Amazon Connect Contact Lens Adapter
=====================================================
Converts an Amazon Connect Contact Lens transcript payload to an
NHID-Clinical v1.3 (session, event) pair for evaluate_all().

Amazon Connect Contact Lens input format:
  {
    "ContactId": "abc-123",
    "InstanceId": "instance-456",
    "Transcript": [
      {
        "Id": "turn-001",
        "ParticipantId": "AGENT",
        "ParticipantRole": "AGENT",
        "Content": "...",
        "BeginOffsetMillis": 0,
        "EndOffsetMillis": 2500
      },
      {
        "Id": "turn-002",
        "ParticipantRole": "CUSTOMER",
        "Content": "...",
        "BeginOffsetMillis": 3000,
        "EndOffsetMillis": 4500
      }
    ]
  }

Usage:
  from adapters.amazon_connect_adapter import to_nhid_event
  session, event = to_nhid_event(connect_payload)
  decision = evaluate_all(session, event)

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

DISCLOSURE_KEYWORDS = {"automated", "agent", "system", "virtual", "bot", "ai"}

DATA_REQUEST_KEYWORDS = {
    "npi", "member id", "member number", "claim number",
    "date of birth", "dob", "tax id", "ein", "group number",
}

ESCALATION_KEYWORDS = ("transfer", "human", "representative", "speak to someone", "agent please")


def _detect_disclosure(text: str) -> bool:
    normalized = text.lower()
    words = set(normalized.replace(",", " ").replace(".", " ").split())
    return bool(DISCLOSURE_KEYWORDS & words)


def _detect_phi(text: str) -> list[str]:
    normalized = text.lower()
    return [kw for kw in DATA_REQUEST_KEYWORDS if kw in normalized]


def _detect_escalation(text: str) -> bool:
    normalized = text.lower()
    return any(kw in normalized for kw in ESCALATION_KEYWORDS)


def _ms_offset_to_iso(start_iso: str, offset_ms: int | float) -> str:
    """Add millisecond offset to an ISO 8601 base timestamp."""
    try:
        base = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        return (base + timedelta(milliseconds=float(offset_ms))).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def to_nhid_event(connect_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Convert an Amazon Connect Contact Lens transcript to an NHID-Clinical (session, event) pair.

    Args:
        connect_payload: Dict with ContactId and Transcript list.
                         Each transcript entry has ParticipantRole ("AGENT"/"CUSTOMER"),
                         Content (str), and BeginOffsetMillis (int).

    Returns:
        (session_dict, event_dict) ready for evaluate_all().
    """
    contact_id = connect_payload.get("ContactId") or connect_payload.get("contactId", "")
    if not contact_id:
        contact_id = str(uuid.uuid4())

    transcript = connect_payload.get("Transcript", connect_payload.get("transcript", []))

    # Connect payloads may include a ConnectedToSystemTimestamp; fall back to now
    start_iso = connect_payload.get(
        "ConnectedToSystemTimestamp",
        datetime.now(timezone.utc).isoformat()
    )

    disclosure_ts: str | None = None
    identity_assertion_text = ""
    phi_accessed: list[str] = []
    escalation_ts: str | None = None

    for entry in transcript:
        role = str(entry.get("ParticipantRole", entry.get("participantRole", ""))).upper()
        content = str(entry.get("Content", entry.get("content", "")) or "")
        offset_ms = entry.get("BeginOffsetMillis", entry.get("beginOffsetMillis", 0))

        try:
            offset_ms = float(offset_ms)
        except (TypeError, ValueError):
            offset_ms = 0.0

        if role == "AGENT":
            if disclosure_ts is None and _detect_disclosure(content):
                disclosure_ts = _ms_offset_to_iso(start_iso, offset_ms)
                identity_assertion_text = content
        elif role == "CUSTOMER":
            phi_accessed.extend(_detect_phi(content))
            if not escalation_ts and _detect_escalation(content):
                escalation_ts = _ms_offset_to_iso(start_iso, offset_ms)

    now = datetime.now(timezone.utc).isoformat()

    session: dict[str, Any] = {
        "turn_count": len(transcript),
        "escalation_path_available": True,
    }

    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": now,
        "session_id": contact_id,
        "request_id": f"req-{contact_id}",
        "event_type": "POLICY",
        "actor_id": f"connect-{contact_id}",
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
            "speech_text": _last_customer_content(transcript),
            "raw_form_fields": None,
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
    }

    return session, event


def _last_customer_content(transcript: list[dict]) -> str:
    for entry in reversed(transcript):
        role = str(entry.get("ParticipantRole", entry.get("participantRole", ""))).upper()
        if role == "CUSTOMER":
            return str(entry.get("Content", entry.get("content", "")) or "")
    return ""
