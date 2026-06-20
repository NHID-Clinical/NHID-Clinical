"""
Tests for functions/twilio_demo_handler.py — the Twilio-only scripted inbound
demo line. Website demo feature, NOT the NHID-Clinical governance framework
(lives under tests/demo/, excluded from the framework's pytest tests/
baseline — see pytest.ini).

Every turn in these scripts is run through the real adapters.call_progress_adapter
+ src.nhid_policy_engine_v1.evaluate_all() pipeline — only the scripted speech
is fake. These tests assert on critical-severity-filtered violations, mirroring
the existing pattern in tests/test_call_progress_webhook.py, since ATR-01
(missing actor_id/replay_mode/external_calls_cached) and the MAJOR
IDG01_ASSERTION_TEXT_MISSING violation are pre-existing, structural quirks of
call_progress_adapter.py's stateless design — not something specific to these
scripts.
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from functions.twilio_demo_handler import _handle_twilio_demo_voice  # noqa: E402
from functions.demo_scripts import SCRIPTS  # noqa: E402
from functions.demo_status_store import LATEST_SESSION_KEY  # noqa: E402


class _FakeTable:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def get_item(self, Key: dict) -> dict:
        item = self.items.get(Key["session_id"])
        return {"Item": item} if item is not None else {}

    def put_item(self, Item: dict) -> None:
        self.items[Item["session_id"]] = Item


def _event(call_sid: str = "CA123", digits: str | None = None) -> dict:
    fields = {"CallSid": call_sid}
    if digits is not None:
        fields["Digits"] = digits
    return {
        "httpMethod": "POST",
        "path": "/v1/webhooks/twilio-demo/voice",
        "headers": {},
        "body": urllib.parse.urlencode(fields),
    }


#: ATR-01 fails CRITICAL on every turn through call_progress_adapter.py
#: regardless of script content (it never populates actor_id/replay_mode/
#: external_calls_cached) — a pre-existing structural adapter gap, not a
#: scripted-call outcome. Excluded here to match the convention already
#: established in tests/test_call_progress_webhook.py.
_DEMO_GATE_RULE_IDS = {"IDG-01", "PDX-01", "DBC-01", "EIT-01"}


def _critical_rule_ids(turn: dict) -> list[str]:
    return [
        v["rule_id"]
        for v in turn.get("decision", {}).get("violations", [])
        if v.get("severity") == "critical" and v["rule_id"] in _DEMO_GATE_RULE_IDS
    ]


def _run_full_call(call_sid: str, digit: str, table: _FakeTable) -> list[str]:
    """Drive a call from the menu to completion. Returns the list of TwiML bodies."""
    bodies = []
    resp = _handle_twilio_demo_voice(_event(call_sid), status_table=table)
    bodies.append(resp["body"])

    resp = _handle_twilio_demo_voice(_event(call_sid, digits=digit), status_table=table)
    bodies.append(resp["body"])

    # Keep advancing (no Digits — auto-redirect turns) until Hangup appears.
    for _ in range(20):
        if "<Hangup/>" in bodies[-1]:
            break
        resp = _handle_twilio_demo_voice(_event(call_sid), status_table=table)
        bodies.append(resp["body"])
    return bodies


def test_no_call_sid_returns_safe_twiml_without_exception():
    table = _FakeTable()
    event = {"httpMethod": "POST", "path": "/v1/webhooks/twilio-demo/voice", "headers": {}, "body": ""}
    resp = _handle_twilio_demo_voice(event, status_table=table)
    assert resp["statusCode"] == 200
    assert "<Response>" in resp["body"]
    assert "<Hangup/>" in resp["body"]


def test_first_request_returns_menu():
    table = _FakeTable()
    resp = _handle_twilio_demo_voice(_event(), status_table=table)
    assert resp["statusCode"] == 200
    assert resp["headers"]["Content-Type"] == "text/xml"
    assert "<Gather" in resp["body"]
    assert "Press 1" in resp["body"]


def test_every_twiml_response_is_well_formed():
    table = _FakeTable()
    bodies = _run_full_call("CA-wellformed", "1", table)
    for body in bodies:
        assert body.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert body.count("<Response>") == 1
        assert body.count("</Response>") == 1


def test_compliant_script_completes_without_critical_violations():
    table = _FakeTable()
    bodies = _run_full_call("CA-compliant", "1", table)
    assert "<Hangup/>" in bodies[-1]
    assert "No critical" in bodies[-1]

    status = table.items["CA-compliant"]
    assert status["script"] == "compliant"
    for turn in status["turns"]:
        assert _critical_rule_ids(turn) == []


def test_noncompliant_script_trips_pdx01_critical_violation():
    table = _FakeTable()
    bodies = _run_full_call("CA-noncompliant", "2", table)
    assert "<Hangup/>" in bodies[-1]
    assert "critical NHID Clinical control" in bodies[-1]

    status = table.items["CA-noncompliant"]
    assert status["script"] == "noncompliant"
    all_critical = [rid for turn in status["turns"] for rid in _critical_rule_ids(turn)]
    assert "PDX-01" in all_critical


def test_invalid_digit_falls_back_to_compliant_script():
    table = _FakeTable()
    _handle_twilio_demo_voice(_event("CA-fallback"), status_table=table)
    _handle_twilio_demo_voice(_event("CA-fallback", digits="9"), status_table=table)
    status = table.items["CA-fallback"]
    assert status["script"] == "compliant"


def test_call_completes_in_exactly_script_length_turns():
    table = _FakeTable()
    bodies = _run_full_call("CA-length", "1", table)
    status = table.items["CA-length"]
    scripted_turns = [t for t in status["turns"] if t["decision"].get("type") != "summary"]
    assert len(scripted_turns) == len(SCRIPTS["compliant"])


def test_completion_offers_end_menu_instead_of_immediate_hangup():
    table = _FakeTable()
    bodies = _run_full_call("CA-endmenu", "1", table)
    final = bodies[-1]
    # The demo now ends on a menu, not a bare goodbye-hangup.
    assert "<Gather" in final
    assert "Press 1 to hear the non-compliant call" in final
    assert "press 2 to end the demo" in final
    # Summary is still spoken and the no-input fallback still hangs up.
    assert "That scenario is complete" in final
    assert "<Hangup/>" in final


def test_end_menu_press_1_replays_the_other_scenario():
    table = _FakeTable()
    _run_full_call("CA-replay", "1", table)  # hear compliant first
    assert table.items["CA-replay"]["script"] == "compliant"

    # Press 1 at the end menu -> restart with the non-compliant scenario.
    _handle_twilio_demo_voice(_event("CA-replay", digits="1"), status_table=table)

    # Drive the replayed scenario to its own completion.
    for _ in range(20):
        resp = _handle_twilio_demo_voice(_event("CA-replay"), status_table=table)
        if "<Gather" in resp["body"] or "Thanks for exploring" in resp["body"]:
            break

    status = table.items["CA-replay"]
    assert status["script"] == "noncompliant"
    scripted_turns = [t for t in status["turns"] if t["decision"].get("type") != "summary"]
    assert len(scripted_turns) == len(SCRIPTS["noncompliant"])


def test_end_menu_press_2_ends_the_demo():
    table = _FakeTable()
    _run_full_call("CA-bye", "1", table)
    resp = _handle_twilio_demo_voice(_event("CA-bye", digits="2"), status_table=table)
    assert "<Hangup/>" in resp["body"]
    assert "<Gather" not in resp["body"]
    assert "Goodbye" in resp["body"]


def test_latest_mirror_tracks_call_progress_for_anonymous_viewers():
    table = _FakeTable()
    _run_full_call("CA-mirrored", "2", table)

    assert LATEST_SESSION_KEY in table.items
    latest = table.items[LATEST_SESSION_KEY]
    real = table.items["CA-mirrored"]
    assert latest["turns"] == real["turns"]
    assert latest["script"] == "noncompliant"
