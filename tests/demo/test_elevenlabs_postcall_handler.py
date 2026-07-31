"""
Tests for functions/elevenlabs_postcall_handler.py::_handle_elevenlabs_postcall_webhook()
— evaluates a completed Beacon outbound-demo-call transcript turn-by-turn
through the real adapters.call_progress_adapter + src.nhid_policy_engine_v1
pipeline, threading session_state/disclosure_timestamp across turns exactly
like functions/twilio_demo_handler.py does. Website demo feature, NOT the
NHID-Clinical governance framework (lives under tests/demo/, excluded from
the framework's pytest tests/ baseline — see pytest.ini).

Uses the same hand-rolled fake DynamoDB table as tests/demo/test_demo_status_store.py
and tests/demo/test_twilio_demo_handler.py — no moto dependency, no real network calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from functions.elevenlabs_postcall_handler import _handle_elevenlabs_postcall_webhook  # noqa: E402


class _FakeTable:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def get_item(self, Key: dict) -> dict:
        item = self.items.get(Key["session_id"])
        return {"Item": item} if item is not None else {}

    def put_item(self, Item: dict) -> None:
        self.items[Item["session_id"]] = Item


def _invoke(payload: dict, table: _FakeTable) -> dict:
    event = {"body": json.dumps(payload)}
    return _handle_elevenlabs_postcall_webhook(event, status_table=table)


def test_missing_body_rejected():
    table = _FakeTable()
    resp = _handle_elevenlabs_postcall_webhook({}, status_table=table)
    assert resp["statusCode"] == 400


def test_invalid_json_rejected():
    table = _FakeTable()
    resp = _handle_elevenlabs_postcall_webhook({"body": "not json"}, status_table=table)
    assert resp["statusCode"] == 400


def test_missing_conversation_id_rejected():
    table = _FakeTable()
    resp = _invoke({"transcript": []}, table)
    assert resp["statusCode"] == 400


def test_compliant_transcript_evaluates_without_exception():
    table = _FakeTable()
    payload = {
        "conversation_id": "conv_compliant",
        "transcript": [
            {"role": "agent", "message": "Hello, this is an automated system calling on behalf of your provider.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Okay, go ahead.", "time_in_call_secs": 3.0},
        ],
    }
    resp = _invoke(payload, table)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["conversation_id"] == "conv_compliant"
    assert body["turns_evaluated"] == 2


def test_noncompliant_transcript_trips_pdx01_critical_violation():
    table = _FakeTable()
    payload = {
        "conversation_id": "conv_noncompliant",
        "transcript": [
            {"role": "agent", "message": "Hi there, calling about your claim.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Can you confirm my date of birth?", "time_in_call_secs": 3.0},
        ],
    }
    _invoke(payload, table)
    stored = table.items["conv_noncompliant"]
    rule_ids = {
        v["rule_id"]
        for t in stored["turns"]
        for v in t["decision"].get("violations", [])
        if v["severity"] == "critical"
    }
    assert "PDX-01" in rule_ids


def test_disclosure_timestamp_threads_forward_once_set():
    table = _FakeTable()
    payload = {
        "conversation_id": "conv_disclosure",
        "transcript": [
            {"role": "agent", "message": "This is an automated agent calling.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Got it.", "time_in_call_secs": 2.0},
            {"role": "agent", "message": "Let's continue.", "time_in_call_secs": 4.0},
        ],
    }
    _invoke(payload, table)
    stored = table.items["conv_disclosure"]
    assert stored["session_state"]["disclosure_timestamp"] is not None


def test_writes_one_time_summary_turn_after_all_transcript_turns():
    table = _FakeTable()
    payload = {
        "conversation_id": "conv_summary",
        "transcript": [
            {"role": "agent", "message": "Hello.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Hi.", "time_in_call_secs": 1.0},
        ],
    }
    _invoke(payload, table)
    stored = table.items["conv_summary"]
    assert stored["completed"] is True
    assert stored["turns"][-1]["decision"]["type"] == "summary"
    # 2 transcript turns + 1 summary turn
    assert len(stored["turns"]) == 3


def test_mirrors_into_latest_session_key():
    table = _FakeTable()
    payload = {
        "conversation_id": "conv_mirror",
        "transcript": [{"role": "agent", "message": "Hello.", "time_in_call_secs": 0.0}],
    }
    _invoke(payload, table)
    from functions.demo_status_store import LATEST_SESSION_KEY
    assert LATEST_SESSION_KEY in table.items
    assert table.items[LATEST_SESSION_KEY]["completed"] is True
