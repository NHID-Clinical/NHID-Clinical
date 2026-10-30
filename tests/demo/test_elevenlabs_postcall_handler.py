"""
Tests for functions/elevenlabs_postcall_handler.py::_handle_elevenlabs_postcall_webhook()
— evaluates a completed Ida outbound-demo-call transcript turn-by-turn
through the real adapters.call_progress_adapter + src.nhid_policy_engine_v1
pipeline, threading session_state/disclosure_timestamp across turns exactly
like functions/twilio_demo_handler.py does. Website demo feature, NOT the
NHID-Clinical governance framework (lives under tests/demo/, excluded from
the framework's pytest tests/ baseline — see pytest.ini).

Uses the same hand-rolled fake DynamoDB table as tests/demo/test_demo_status_store.py
and tests/demo/test_twilio_demo_handler.py — no moto dependency, no real network calls.

Every request is signed the way ElevenLabs signs it (ElevenLabs-Signature,
t=<unix>,v0=<hmac>) with a test secret, and every payload uses the real
post-call envelope. Signature, timing and vendor-grade tests that the
framework suite runs are in tests/test_elevenlabs_postcall.py.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import pytest

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


_SECRET = "test-webhook-secret"


@pytest.fixture(autouse=True)
def _webhook_secret(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", _SECRET)


def _signed(raw: str) -> dict:
    ts = str(int(time.time()))
    digest = hmac.new(_SECRET.encode(), f"{ts}.{raw}".encode(), hashlib.sha256).hexdigest()
    return {"body": raw, "headers": {"elevenlabs-signature": f"t={ts},v0={digest}"}}


def _envelope(conversation_id, transcript) -> dict:
    data = {"agent_id": "agent_test", "transcript": transcript}
    if conversation_id is not None:
        data["conversation_id"] = conversation_id
    return {"type": "post_call_transcription", "event_timestamp": int(time.time()), "data": data}


def _invoke(payload: dict, table: _FakeTable) -> dict:
    return _handle_elevenlabs_postcall_webhook(_signed(json.dumps(payload)), status_table=table)


def test_missing_body_rejected():
    table = _FakeTable()
    resp = _handle_elevenlabs_postcall_webhook(_signed(""), status_table=table)
    assert resp["statusCode"] == 400


def test_invalid_json_rejected():
    table = _FakeTable()
    resp = _handle_elevenlabs_postcall_webhook(_signed("not json"), status_table=table)
    assert resp["statusCode"] == 400


def test_missing_conversation_id_rejected():
    table = _FakeTable()
    resp = _invoke(_envelope(None, []), table)
    assert resp["statusCode"] == 400


def test_compliant_transcript_evaluates_without_exception():
    table = _FakeTable()
    payload = _envelope("conv_compliant", [
            {"role": "agent", "message": "Hello, this is an automated system calling on behalf of your provider.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Okay, go ahead.", "time_in_call_secs": 3.0},
    ])
    resp = _invoke(payload, table)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["conversation_id"] == "conv_compliant"
    assert body["turns_evaluated"] == 2


def test_noncompliant_transcript_trips_pdx01_critical_violation():
    table = _FakeTable()
    payload = _envelope("conv_noncompliant", [
            {"role": "agent", "message": "Hi there, calling about your claim.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Can you confirm my date of birth?", "time_in_call_secs": 3.0},
    ])
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
    payload = _envelope("conv_disclosure", [
            {"role": "agent", "message": "This is an automated agent calling.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Got it.", "time_in_call_secs": 2.0},
            {"role": "agent", "message": "Let's continue.", "time_in_call_secs": 4.0},
    ])
    _invoke(payload, table)
    stored = table.items["conv_disclosure"]
    assert stored["session_state"]["disclosure_timestamp"] is not None


def test_writes_one_time_summary_turn_after_all_transcript_turns():
    table = _FakeTable()
    payload = _envelope("conv_summary", [
            {"role": "agent", "message": "Hello.", "time_in_call_secs": 0.0},
            {"role": "user", "message": "Hi.", "time_in_call_secs": 1.0},
    ])
    _invoke(payload, table)
    stored = table.items["conv_summary"]
    assert stored["completed"] is True
    assert stored["turns"][-1]["decision"]["type"] == "summary"
    # 2 transcript turns + 1 summary turn
    assert len(stored["turns"]) == 3


def test_mirrors_into_latest_session_key():
    table = _FakeTable()
    payload = _envelope("conv_mirror", [{"role": "agent", "message": "Hello.", "time_in_call_secs": 0.0}])
    _invoke(payload, table)
    from functions.demo_status_store import LATEST_SESSION_KEY
    assert LATEST_SESSION_KEY in table.items
    assert table.items[LATEST_SESSION_KEY]["completed"] is True
