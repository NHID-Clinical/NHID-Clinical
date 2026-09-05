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

Webhook payload format (ElevenLabs):
  {
    "conversation_id": "conv_abc123",
    "transcript": [
      {"role": "agent", "message": "...", "time_in_call_secs": 0.0},
      {"role": "user", "message": "...", "time_in_call_secs": 4.2},
      ...
    ]
  }

NHID-Clinical is a voluntary open proposal. This module is licensed
Apache-2.0 (see LICENSE); the normative control text it implements is
CC BY 4.0 (see LICENSE-DOCS).
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

from typing import Any, Iterator

_ROLE_TO_SPEAKER = {"agent": "agent", "user": "user"}


def iter_turns(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield one {session_id, turn_index, speaker, text} dict per transcript
    message, in transcript order. Messages with an unrecognized role (e.g.
    ElevenLabs system/tool-call entries) are skipped without breaking the
    turn_index sequence."""
    conversation_id = payload.get("conversation_id")
    if not conversation_id:
        raise ValueError("conversation_id is required")

    turn_index = 0
    for message in payload.get("transcript") or []:
        speaker = _ROLE_TO_SPEAKER.get(message.get("role"))
        if speaker is None:
            continue
        yield {
            "session_id": conversation_id,
            "turn_index": turn_index,
            "speaker": speaker,
            "text": message.get("message", "") or "",
        }
        turn_index += 1
