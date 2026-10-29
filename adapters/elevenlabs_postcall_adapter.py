"""
NHID-Clinical — ElevenLabs Post-Call Webhook Adapter
=======================================================
Translates ElevenLabs' post-call webhook payload (the full conversation
transcript, delivered once a Beacon outbound demo call ends) into the same
per-turn shape adapters.call_progress_adapter.to_nhid_event() expects.

This adapter only reshapes the payload -- it does not evaluate anything.
Session-state threading (turn_count, disclosure_timestamp) and the actual
evaluate_all() calls happen in the caller
(functions/elevenlabs_postcall_handler.py), exactly as they do for the
Twilio scripted demo line in functions/twilio_demo_handler.py.

Un-archived 2026-10-29: the Beacon demo is maintained again, so this adapter
tracks ElevenLabs' current interface (adapters/archive/README.md: "un-archiving
one is a reasonable response to a real integration request").

Webhook payload format (ElevenLabs, documented at
https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks):

  {
    "type": "post_call_transcription",
    "event_timestamp": 1739537297,                  # unix seconds, when sent
    "data": {
      "agent_id": "agent_...",
      "conversation_id": "conv_...",
      "transcript": [
        {"role": "agent", "message": "...", "time_in_call_secs": 0},
        {"role": "user",  "message": "...", "time_in_call_secs": 4,
         "interrupted": false},
        ...
      ],
      "metadata": {"start_time_unix_secs": 1739537200,
                   "call_duration_secs": 97, ...},
      "analysis": {"evaluation_criteria_results": {...},
                   "data_collection_results": {...}, ...}
    }
  }

The other event types (post_call_audio, call_initiation_failure) carry no
transcript; ``parse_postcall`` reports their type so the handler can ignore
them. The earlier flat shape ({"conversation_id", "transcript"} at the top
level) is still accepted, because existing tests and fixtures use it.

NHID-Clinical is a voluntary open proposal. This module is licensed
Apache-2.0 (see LICENSE); the normative control text it implements is
CC BY 4.0 (see LICENSE-DOCS).
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

_ROLE_TO_SPEAKER = {"agent": "agent", "user": "user"}

#: The one event type that carries a transcript.
TRANSCRIPTION_TYPE = "post_call_transcription"


def _number(value: Any) -> Optional[float]:
    """A finite number, or None. Booleans are not numbers here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if value == value and value not in (float("inf"), float("-inf")) else None


def parse_postcall(payload: dict[str, Any]) -> dict[str, Any]:
    """Unwrap a post-call payload into one flat record.

    Returns ``{type, conversation_id, agent_id, event_timestamp,
    start_time_unix_secs, call_duration_secs, analysis, transcript}``. Fields
    the payload does not carry are None (``analysis`` is ``{}``,
    ``transcript`` is ``[]``), never a guessed default.

    Raises ValueError when the payload is not an object, or is a transcription
    event without a conversation_id.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    if "type" in payload or "data" in payload:
        event_type = str(payload.get("type") or "")
        data = payload.get("data")
        if not isinstance(data, dict):
            data = {}
        event_timestamp = _number(payload.get("event_timestamp"))
    else:  # flat shape, pre-envelope
        event_type = TRANSCRIPTION_TYPE
        data = payload
        event_timestamp = _number(payload.get("event_timestamp"))

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    analysis = data.get("analysis") if isinstance(data.get("analysis"), dict) else {}
    transcript = data.get("transcript")
    if not isinstance(transcript, list):
        transcript = []

    record = {
        "type": event_type,
        "conversation_id": data.get("conversation_id"),
        "agent_id": data.get("agent_id"),
        "event_timestamp": event_timestamp,
        "start_time_unix_secs": _number(metadata.get("start_time_unix_secs")),
        "call_duration_secs": _number(metadata.get("call_duration_secs")),
        "analysis": analysis,
        "transcript": transcript,
    }
    if event_type == TRANSCRIPTION_TYPE and not record["conversation_id"]:
        raise ValueError("conversation_id is required")
    return record


def iter_turns(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield one turn dict per transcript message, in transcript order:
    ``{session_id, turn_index, speaker, text, time_in_call_secs, interrupted}``.

    ``time_in_call_secs`` is the message's offset from call start as
    ElevenLabs reports it, or None when absent; never 0 by default, because a
    missing time is not a disclosure at the start of the call.

    Messages with an unrecognized role (e.g. ElevenLabs system/tool-call
    entries) are skipped without breaking the turn_index sequence."""
    record = parse_postcall(payload)
    conversation_id = record["conversation_id"]
    if not conversation_id:
        raise ValueError("conversation_id is required")

    turn_index = 0
    for message in record["transcript"]:
        if not isinstance(message, dict):
            continue
        speaker = _ROLE_TO_SPEAKER.get(message.get("role"))
        if speaker is None:
            continue
        yield {
            "session_id": conversation_id,
            "turn_index": turn_index,
            "speaker": speaker,
            "text": message.get("message", "") or "",
            "time_in_call_secs": _number(message.get("time_in_call_secs")),
            "interrupted": bool(message.get("interrupted")),
        }
        turn_index += 1
