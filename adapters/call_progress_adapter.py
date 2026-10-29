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
    "actor_id": "agent-vendor-7", # optional: stable agent id for the audit trail
    "text": "...",
    "interrupted": false,        # optional: playback cut off by the other party
    "timestamp": null,           # optional: ISO 8601 time this turn happened, when the
                                 # caller knows it (a post-call transcript does); else now
    "heard_text": null,          # optional: the part actually played, if interrupted
    "session_state": {
      "turn_count": 3,
      "disclosure_timestamp": null,    # ISO 8601 or null
      "escalation_available": true
    }
  }

On each turn, the caller receives back an action + violations.
Update session_state.disclosure_timestamp when the agent discloses and the
result is not IDG01_DISCLOSURE_INTERRUPTED: a disclosure the counterparty cut
off before hearing does not count and must be repeated.
Send the updated session_state on the next turn.

NHID-Clinical is a voluntary open proposal. This module is licensed
Apache-2.0 (see LICENSE); the normative control text it implements is
CC BY 4.0 (see LICENSE-DOCS).
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
    # ATR-01 requires an actor. A stable agent identifier when the caller has
    # one; otherwise derived from the session, so the field is never empty.
    actor_id = str(body.get("actor_id") or "").strip() or f"agent-{session_id}"

    speaker = body.get("speaker", "user")
    text = body.get("text", "") or ""
    turn_index = int(body.get("turn_index", 0))

    state = body.get("session_state", {}) or {}
    turn_count = int(state.get("turn_count", turn_index + 1))
    disclosure_ts = state.get("disclosure_timestamp")
    escalation_available = bool(state.get("escalation_available", True))

    # The time this turn happened. A live webhook turn is happening now; a
    # post-call transcript replays turns that happened earlier, and stamping
    # them with processing time made disclosure timing unmeasurable (every turn
    # of a 90-second call landed in the same second). A caller that knows the
    # real time passes it; anything unparseable is an error, not "now".
    supplied_ts = body.get("timestamp")
    if supplied_ts:
        try:
            parsed = datetime.fromisoformat(str(supplied_ts).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"timestamp must be ISO 8601, got {supplied_ts!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        now = parsed.isoformat()
    else:
        now = datetime.now(timezone.utc).isoformat()

    # Derive disclosure state from session_state or detect in agent speech
    identity_assertion_text = ""
    interrupted = bool(body.get("interrupted"))
    heard_text = body.get("heard_text")
    disclosure_interrupted = False
    if speaker == "agent" and _detect_disclosure(text):
        if not disclosure_ts:
            disclosure_ts = now
            # The disclosure is first being made on this turn, so whether it
            # was heard decides IDG-01. The engine credits an interrupted turn
            # only if heard_text itself states a non-human identity.
            disclosure_interrupted = interrupted
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
        # The three envelope fields ATR-01 requires that this adapter used to
        # omit. Without them every turn through the webhook and the gate came
        # back LOG_ONLY / ATR01_AUDIT_FIELDS_MISSING and no signed audit trail
        # was ever built for a live call (found 2026-10-25). A webhook turn is
        # live by definition: nothing is replayed and nothing is cached.
        "actor_id": actor_id,
        "replay_mode": "live",
        "external_calls_cached": False,
        "state_before": "ACTIVE",
        "state_after": "ACTIVE",
        "counterparty_type": "human_operator",
        "healthcare_governance": {
            "disclosure_timestamp": disclosure_ts,
            "identity_assertion_text": identity_assertion_text,
            "disclosure_interrupted": disclosure_interrupted,
            "disclosure_heard_text": heard_text if disclosure_interrupted else None,
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
