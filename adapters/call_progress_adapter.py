"""
NHID-Clinical – Call-Progress Adapter
=======================================
Converts a turn-by-turn call-progress webhook body to an NHID-Clinical
(session, event) pair for use with evaluate_all().

This enables near-real-time, per-turn conformance evaluation. The caller
is responsible for maintaining session_state across turns and sending it
back on each webhook call. No server-side state is stored.

Webhook body format:
  {
    "session_id": "call_abc123",
    "turn_index": 3,
    "speaker": "agent",          # "agent" or "user"
    "text": "...",
    "session_state": {
      "turn_count": 3,
      "disclosure_timestamp": null,    # ISO 8601 or null
      "escalation_available": true
    }
  }

On each turn, the caller receives back an action + violations.
Update session_state.disclosure_timestamp when the agent discloses.
Send the updated session_state on the next turn.

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

DISCLOSURE_KEYWORDS = frozenset({"automated", "agent", "system", "virtual", "bot", "ai assistant"})
DATA_REQUEST_KEYWORDS = frozenset({
    "npi", "member id", "member number", "claim number",
    "date of birth", "dob", "tax id", "ein", "group number",
})
ESCALATION_KEYWORDS = (
    "transfer", "speak to a human", "real person", "representative",
    "supervisor", "human agent",
)


def _detect_disclosure(text: str) -> bool:
    """Return True if text contains an identity disclosure."""
    normalized = text.lower()
    return any(kw in normalized for kw in DISCLOSURE_KEYWORDS)


def _detect_phi_request(text: str) -> list[str]:
    """Return list of PHI field names detected in text."""
    normalized = text.lower()
    return [kw for kw in DATA_REQUEST_KEYWORDS if kw in normalized]


def _detect_escalation(text: str) -> bool:
    """Return True if text requests human escalation."""
    normalized = text.lower()
    return any(kw in normalized for kw in ESCALATION_KEYWORDS)


def to_nhid_event(body: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Convert a call-progress webhook body to an NHID-Clinical (session, event) pair.

    Args:
        body: Dict with session_id, turn_index, speaker, text, session_state.

    Returns:
        (session_dict, event_dict) ready for evaluate_all().

    Raises:
        ValueError: if required fields are missing or invalid.
        KeyError: if required fields are absent.
    """
    session_id = body.get("session_id")
    if not session_id:
        raise ValueError("session_id is required")

    speaker = body.get("speaker", "user")
    text = body.get("text", "") or ""
    turn_index = int(body.get("turn_index", 0))

    state = body.get("session_state", {}) or {}
    turn_count = int(state.get("turn_count", turn_index + 1))
    disclosure_ts = state.get("disclosure_timestamp")
    escalation_available = bool(state.get("escalation_available", True))

    now = datetime.now(timezone.utc).isoformat()

    # Derive disclosure state from session_state or detect in agent speech
    identity_assertion_text = ""
    if speaker == "agent" and _detect_disclosure(text):
        if not disclosure_ts:
            disclosure_ts = now
        identity_assertion_text = text

    phi_accessed = []
    if speaker == "user":
        phi_accessed = _detect_phi_request(text)

    escalation_ts = None
    if speaker == "user" and _detect_escalation(text):
        escalation_ts = now

    session: dict[str, Any] = {
        "turn_count": turn_count,
        "escalation_path_available": escalation_available,
    }

    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": now,
        "session_id": session_id,
        "request_id": f"req-{session_id}-t{turn_index}",
        "event_type": "POLICY",
        "state_before": "ACTIVE",
        "state_after": "ACTIVE",
        "counterparty_type": "human_operator",
        "healthcare_governance": {
            "disclosure_timestamp": disclosure_ts,
            "identity_assertion_text": identity_assertion_text,
            "deceptive_artifact_flags": [],
            "escalation_timestamp": escalation_ts,
            "escalation_outcome": None,
            "phi_accessed": phi_accessed,
        },
        "input_payload": {
            "speech_text": text if speaker == "user" else "",
            "raw_form_fields": None,
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
    }

    return session, event
