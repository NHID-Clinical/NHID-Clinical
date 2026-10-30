"""
Tests for adapters/elevenlabs_postcall_adapter.py::iter_turns() — reshapes
ElevenLabs' post-call webhook transcript into call-progress-adapter-shaped
turns. Website demo feature, NOT the NHID-Clinical governance framework
(lives under tests/demo/, excluded from the framework's pytest tests/
baseline — see pytest.ini). The envelope, timing and signature tests the
framework suite runs are in tests/test_elevenlabs_postcall.py.

Fixtures use the real post-call envelope:
{"type": "post_call_transcription", "event_timestamp": ..., "data": {...}}.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters.elevenlabs_postcall_adapter import iter_turns  # noqa: E402


def _envelope(conversation_id, transcript):
    data = {"agent_id": "agent_test", "transcript": transcript}
    if conversation_id is not None:
        data["conversation_id"] = conversation_id
    return {"type": "post_call_transcription", "event_timestamp": 1_761_700_000, "data": data}


def test_maps_agent_and_user_roles_to_speaker():
    payload = _envelope("conv_123", [
        {"role": "agent", "message": "Hello", "time_in_call_secs": 0},
        {"role": "user", "message": "Hi there", "time_in_call_secs": 2},
    ])
    turns = list(iter_turns(payload))
    assert [t["speaker"] for t in turns] == ["agent", "user"]
    assert [t["text"] for t in turns] == ["Hello", "Hi there"]


def test_turn_index_increments_sequentially_across_turns():
    payload = _envelope("conv_123", [
        {"role": "agent", "message": "a", "time_in_call_secs": 0},
        {"role": "user", "message": "b", "time_in_call_secs": 1},
        {"role": "agent", "message": "c", "time_in_call_secs": 2},
    ])
    turns = list(iter_turns(payload))
    assert [t["turn_index"] for t in turns] == [0, 1, 2]


def test_all_turns_carry_the_conversation_id_as_session_id():
    payload = _envelope("conv_abc", [
        {"role": "agent", "message": "a", "time_in_call_secs": 0},
        {"role": "user", "message": "b", "time_in_call_secs": 1},
    ])
    turns = list(iter_turns(payload))
    assert all(t["session_id"] == "conv_abc" for t in turns)


def test_unrecognized_role_is_skipped_without_breaking_turn_index():
    payload = _envelope("conv_123", [
        {"role": "agent", "message": "a", "time_in_call_secs": 0},
        {"role": "tool_call", "message": "lookup_member", "time_in_call_secs": 1},
        {"role": "user", "message": "b", "time_in_call_secs": 2},
    ])
    turns = list(iter_turns(payload))
    assert [t["speaker"] for t in turns] == ["agent", "user"]
    assert [t["turn_index"] for t in turns] == [0, 1]


def test_missing_conversation_id_raises_value_error():
    with pytest.raises(ValueError):
        list(iter_turns(_envelope(None, [])))


def test_empty_transcript_yields_no_turns():
    assert list(iter_turns(_envelope("conv_123", []))) == []


def test_missing_message_text_defaults_to_empty_string():
    turns = list(iter_turns(_envelope("conv_123", [{"role": "agent", "time_in_call_secs": 0}])))
    assert turns[0]["text"] == ""


def test_time_in_call_secs_and_interrupted_are_carried_through():
    turns = list(iter_turns(_envelope("conv_t", [
        {"role": "agent", "message": "a", "time_in_call_secs": 4, "interrupted": True},
        {"role": "user", "message": "b"},
    ])))
    assert turns[0]["time_in_call_secs"] == 4.0
    assert turns[0]["interrupted"] is True
    # Absent time is unknown, not zero.
    assert turns[1]["time_in_call_secs"] is None
    assert turns[1]["interrupted"] is False


def test_the_flat_pre_envelope_shape_still_works():
    payload = {
        "conversation_id": "conv_flat",
        "transcript": [{"role": "agent", "message": "Hello", "time_in_call_secs": 0}],
    }
    turns = list(iter_turns(payload))
    assert turns[0]["session_id"] == "conv_flat"
