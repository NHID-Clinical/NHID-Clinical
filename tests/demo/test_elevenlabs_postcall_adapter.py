"""
Tests for adapters/elevenlabs_postcall_adapter.py::iter_turns() — reshapes
ElevenLabs' post-call webhook transcript into call-progress-adapter-shaped
turns. Website demo feature, NOT the NHID-Clinical governance framework
(lives under tests/demo/, excluded from the framework's pytest tests/
baseline — see pytest.ini).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapters.elevenlabs_postcall_adapter import iter_turns  # noqa: E402


def test_maps_agent_and_user_roles_to_speaker():
    payload = {
        "conversation_id": "conv_123",
        "transcript": [
            {"role": "agent", "message": "Hello", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Hi there", "time_in_call_secs": 2.5},
        ],
    }
    turns = list(iter_turns(payload))
    assert [t["speaker"] for t in turns] == ["agent", "user"]
    assert [t["text"] for t in turns] == ["Hello", "Hi there"]


def test_turn_index_increments_sequentially_across_turns():
    payload = {
        "conversation_id": "conv_123",
        "transcript": [
            {"role": "agent", "message": "a", "time_in_call_secs": 0.0},
            {"role": "user", "message": "b", "time_in_call_secs": 1.0},
            {"role": "agent", "message": "c", "time_in_call_secs": 2.0},
        ],
    }
    turns = list(iter_turns(payload))
    assert [t["turn_index"] for t in turns] == [0, 1, 2]


def test_all_turns_carry_the_conversation_id_as_session_id():
    payload = {
        "conversation_id": "conv_abc",
        "transcript": [
            {"role": "agent", "message": "a", "time_in_call_secs": 0.0},
            {"role": "user", "message": "b", "time_in_call_secs": 1.0},
        ],
    }
    turns = list(iter_turns(payload))
    assert all(t["session_id"] == "conv_abc" for t in turns)


def test_unrecognized_role_is_skipped_without_breaking_turn_index():
    payload = {
        "conversation_id": "conv_123",
        "transcript": [
            {"role": "agent", "message": "a", "time_in_call_secs": 0.0},
            {"role": "tool_call", "message": "lookup_member", "time_in_call_secs": 1.0},
            {"role": "user", "message": "b", "time_in_call_secs": 2.0},
        ],
    }
    turns = list(iter_turns(payload))
    assert [t["speaker"] for t in turns] == ["agent", "user"]
    assert [t["turn_index"] for t in turns] == [0, 1]


def test_missing_conversation_id_raises_value_error():
    with pytest.raises(ValueError):
        list(iter_turns({"transcript": []}))


def test_empty_transcript_yields_no_turns():
    turns = list(iter_turns({"conversation_id": "conv_123", "transcript": []}))
    assert turns == []


def test_missing_message_text_defaults_to_empty_string():
    payload = {
        "conversation_id": "conv_123",
        "transcript": [{"role": "agent", "time_in_call_secs": 0.0}],
    }
    turns = list(iter_turns(payload))
    assert turns[0]["text"] == ""
