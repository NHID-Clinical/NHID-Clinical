"""
NHID-Clinical – Retell AI Adapter
====================================
Converts a Retell AI call webhook payload to an NHID-Clinical v1.3
(session, event) pair for evaluate_all().

Retell input format (call_analyzed webhook):
  {
    "call_id": "call_abc123",
    "start_timestamp": 1718150400000,
    "transcript_object": [
      {"role": "agent", "content": "...", "words": [...]},
      {"role": "user",  "content": "...", "words": [...]}
    ]
  }

Usage:
  from adapters.retell_adapter import to_nhid_event
  session, event = to_nhid_event(retell_payload)
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


def _ms_to_iso(start_ms: int | float, offset_ms: int | float = 0) -> str:
    """Convert epoch milliseconds + offset to ISO 8601 string."""
    try:
        total_ms = float(start_ms) + float(offset_ms)
        dt = datetime.fromtimestamp(total_ms / 1000.0, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def to_nhid_event(retell_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Convert a Retell AI call webhook payload to an NHID-Clinical (session, event) pair.

    Args:
        retell_payload: Dict with call_id, start_timestamp (epoch ms),
                        and transcript_object list.

    Returns:
        (session_dict, event_dict) ready for evaluate_all().
    """
    call_id = retell_payload.get("call_id", str(uuid.uuid4()))
    start_ms = retell_payload.get("start_timestamp", 0)
    transcript = retell_payload.get("transcript_object", [])

    # Fallback ISO start time
    try:
        start_iso = _ms_to_iso(start_ms)
    except Exception:
        start_iso = datetime.now(timezone.utc).isoformat()

    disclosure_ts: str | None = None
    identity_assertion_text = ""
    phi_accessed: list[str] = []
    escalation_ts: str | None = None

    for entry in transcript:
        role = str(entry.get("role", "")).lower()
        content = str(entry.get("content", "") or "")
        words_list = entry.get("words", [])

        # Use first word start_time (ms offset from call start) if available
        entry_offset_ms: float = 0.0
        if words_list and isinstance(words_list, list) and len(words_list) > 0:
            try:
                entry_offset_ms = float(words_list[0].get("start", 0))
            except (TypeError, ValueError):
                entry_offset_ms = 0.0

        if role == "agent":
            if disclosure_ts is None and _detect_disclosure(content):
                disclosure_ts = _ms_to_iso(start_ms, entry_offset_ms)
                identity_assertion_text = content
        elif role == "user":
            phi_accessed.extend(_detect_phi(content))
            if not escalation_ts and _detect_escalation(content):
                escalation_ts = _ms_to_iso(start_ms, entry_offset_ms)

    now = datetime.now(timezone.utc).isoformat()

    session: dict[str, Any] = {
        "turn_count": len(transcript),
        "escalation_path_available": True,
    }

    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": now,
        "session_id": call_id,
        "request_id": f"req-{call_id}",
        "event_type": "POLICY",
        "actor_id": f"retell-{call_id}",
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
            "speech_text": _last_user_content(transcript),
            "raw_form_fields": None,
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
    }

    return session, event


def _last_user_content(transcript: list[dict]) -> str:
    for entry in reversed(transcript):
        if str(entry.get("role", "")).lower() == "user":
            return str(entry.get("content", "") or "")
    return ""
