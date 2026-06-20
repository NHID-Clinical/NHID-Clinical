"""
Twilio voice webhook handler for the NHID-Clinical scripted inbound demo line.

Stateless per Twilio's webhook model (each request is a fresh Lambda
invocation), but the demo *call* is stateful across requests: progress is
persisted turn-by-turn in functions.demo_status_store, keyed by Twilio's
CallSid. Every turn is evaluated through the exact same real pipeline used
in production — adapters.call_progress_adapter.to_nhid_event() +
src.nhid_policy_engine_v1.evaluate_all() — only the scripted speech in
functions.demo_scripts is fake.

This is infrastructure for the demo website feature, NOT the NHID-Clinical
governance framework itself.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, Optional
from xml.sax.saxutils import escape

from adapters.call_progress_adapter import to_nhid_event
from functions import demo_status_store
from functions.demo_scripts import SCRIPT_LABELS, SCRIPTS
from src.nhid_policy_engine_v1 import evaluate_all

VOICE_WEBHOOK_PATH = "/v1/webhooks/twilio-demo/voice"

_DIGIT_TO_SCRIPT: dict[str, str] = {"1": "compliant", "2": "noncompliant"}
_DEFAULT_SCRIPT = "compliant"

_SAY_PATTERN = re.compile(r"<Say>(.*?)</Say>", re.DOTALL)

_SPEAKER_LABELS = {"agent": "AI agent", "user": "Claims staff"}


def _voice_webhook_url(event: dict[str, Any]) -> str:
    """Best-effort absolute URL back to this same webhook, for <Redirect>."""
    headers = event.get("headers") or {}
    host = headers.get("Host") or headers.get("host") or ""
    if not host:
        return VOICE_WEBHOOK_PATH
    stage = (event.get("requestContext") or {}).get("stage") or ""
    prefix = f"/{stage}" if stage else ""
    return f"https://{host}{prefix}{VOICE_WEBHOOK_PATH}"


def _twiml_response(body: str) -> dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/xml"},
        "body": f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>{body}\n</Response>',
    }


def _say(text: str) -> str:
    return f"\n  <Say>{escape(text)}</Say>"


def _say_and_hangup(text: str) -> str:
    return _say(text) + "\n  <Hangup/>"


def _menu_twiml(action_url: str) -> dict[str, Any]:
    body = (
        f'\n  <Gather numDigits="1" action="{escape(action_url)}" method="POST" timeout="8">'
        + _say(
            "Welcome to the NHID Clinical live demo line. "
            "Press 1 to hear a call that satisfies the disclosure and data "
            "protection controls. Press 2 to hear a call that violates them."
        )
        + "\n  </Gather>"
        + _say("No selection received. Goodbye.")
    )
    return _twiml_response(body)


def _redirect_twiml(say_text: str, action_url: str) -> dict[str, Any]:
    body = _say(say_text) + '\n  <Pause length="1"/>' + f"\n  <Redirect method=\"POST\">{escape(action_url)}</Redirect>"
    return _twiml_response(body)


def _other_script(script_name: str) -> str:
    """The scenario the caller has not heard yet (compliant <-> noncompliant)."""
    return "noncompliant" if script_name == "compliant" else "compliant"


def _end_menu_twiml(summary_text: str, other_script: str, action_url: str) -> dict[str, Any]:
    """End-of-demo menu: speak the scenario summary, then offer to hear the
    other scenario (press 1) or end the demo (press 2). The trailing Hangup
    covers the no-input case."""
    other_label = SCRIPT_LABELS[other_script].lower()
    body = (
        _say(summary_text)
        + f'\n  <Gather numDigits="1" action="{escape(action_url)}" method="POST" timeout="8">'
        + _say(
            f"Press 1 to hear the {other_label}, or press 2 to end the demo."
        )
        + "\n  </Gather>"
        + _say("No selection received. Goodbye.")
        + "\n  <Hangup/>"
    )
    return _twiml_response(body)


def _extract_say_text(twiml_fallback: Optional[str]) -> Optional[str]:
    """Pull the spoken message out of a policy-engine twiml_fallback string."""
    if not twiml_fallback:
        return None
    match = _SAY_PATTERN.search(twiml_fallback)
    return match.group(1) if match else None


def _decision_summary(decision) -> dict[str, Any]:
    return {
        "action": decision.action.value,
        "reason_code": decision.reason_code,
        "violations": [
            {"rule_id": v.rule_id, "severity": v.severity.value, "description": v.description}
            for v in decision.violations
        ],
    }


def _turn_say_text(turn: dict[str, str], decision) -> str:
    """The spoken line for one turn — the canonical gate language if a gate
    fired, otherwise the scripted line read aloud with its speaker labeled."""
    gate_text = _extract_say_text(decision.twiml_fallback)
    if gate_text:
        return gate_text
    label = _SPEAKER_LABELS.get(turn["speaker"], turn["speaker"])
    return f"{label} says: {turn['text']}"


#: Rule IDs the demo's pass/fail narrative is about. ATR-01 is deliberately
#: excluded: call_progress_adapter.py never populates actor_id/replay_mode/
#: external_calls_cached, so it fails CRITICAL on every turn regardless of
#: script content — a structural adapter gap, not a scripted-call outcome.
#: See tests/test_call_progress_webhook.py for the same exclusion convention.
_DEMO_GATE_RULE_IDS = frozenset({"IDG-01", "PDX-01", "DBC-01", "EIT-01"})


def _critical_violation_count(turns: list[dict[str, Any]]) -> int:
    return sum(
        1
        for t in turns
        for v in t.get("decision", {}).get("violations", [])
        if v.get("severity") == "critical" and v.get("rule_id") in _DEMO_GATE_RULE_IDS
    )


def _closing_summary_text(turns: list[dict[str, Any]]) -> str:
    critical_count = _critical_violation_count(turns)
    if critical_count == 0:
        return (
            "That scenario is complete. No critical NHID Clinical control "
            "violations were detected."
        )
    return (
        f"That scenario is complete. {critical_count} critical NHID Clinical "
        "control violations were detected."
    )


def _handle_twilio_demo_voice(event: dict[str, Any], *, status_table=None) -> dict[str, Any]:
    raw_body = event.get("body") or ""
    params = urllib.parse.parse_qs(raw_body)

    def _field(name: str) -> str:
        values = params.get(name)
        return values[0] if values else ""

    call_sid = _field("CallSid")
    digits = _field("Digits")

    if not call_sid:
        return _twiml_response(_say_and_hangup("This demo line requires a valid call session."))

    action_url = _voice_webhook_url(event)
    existing = demo_status_store.get_status(call_sid, table=status_table)
    script_name = existing.get("script")
    existing_turns = list(existing.get("turns", []))
    demo_completed = bool(existing_turns) and existing_turns[-1].get("decision", {}).get("type") == "summary"

    if demo_completed:
        # The scenario finished and the caller is answering the end-of-demo
        # menu: press 1 replays the scenario they didn't choose, anything
        # else (including 2 or no input) ends the demo.
        if digits == "1":
            script_name = _other_script(script_name or _DEFAULT_SCRIPT)
            demo_status_store.reset_session(call_sid, table=status_table)
            turns: list[dict[str, Any]] = []
            session_state: dict[str, Any] = {
                "turn_count": 0,
                "disclosure_timestamp": None,
                "escalation_available": True,
            }
        else:
            return _twiml_response(
                _say_and_hangup("Thanks for exploring the NHID Clinical demo. Goodbye.")
            )
    elif not script_name:
        # No script chosen yet: first request shows the menu, the menu's
        # response (a Digits field with no stored script) picks the scenario.
        if not digits:
            return _menu_twiml(action_url)
        script_name = _DIGIT_TO_SCRIPT.get(digits, _DEFAULT_SCRIPT)
        turns = []
        session_state = {
            "turn_count": 0,
            "disclosure_timestamp": None,
            "escalation_available": True,
        }
    else:
        turns = existing_turns
        session_state = dict(existing.get("session_state", {}))

    script = SCRIPTS[script_name]
    turn_index = len(turns)

    if turn_index >= len(script):
        # Scenario finished: record the summary once, then offer the
        # end-of-demo menu (hear the other scenario / end) instead of
        # hanging up immediately.
        already_closed = bool(turns) and turns[-1].get("decision", {}).get("type") == "summary"
        if not already_closed:
            stored = demo_status_store.put_turn(
                call_sid,
                turn_index,
                {"type": "summary", "critical_violation_count": _critical_violation_count(turns)},
                session_state=session_state,
                extra={"script": script_name, "script_label": SCRIPT_LABELS[script_name], "completed": True},
                table=status_table,
            )
            demo_status_store.set_latest(stored, table=status_table)
        return _end_menu_twiml(_closing_summary_text(turns), _other_script(script_name), action_url)

    turn = script[turn_index]
    body = {
        "session_id": call_sid,
        "turn_index": turn_index,
        "speaker": turn["speaker"],
        "text": turn["text"],
        "session_state": session_state,
    }
    session, policy_event = to_nhid_event(body)
    decision = evaluate_all(session, policy_event)

    new_session_state = dict(session_state)
    new_session_state["turn_count"] = turn_index + 1
    new_session_state["disclosure_timestamp"] = policy_event["healthcare_governance"]["disclosure_timestamp"]

    stored = demo_status_store.put_turn(
        call_sid,
        turn_index,
        _decision_summary(decision),
        session_state=new_session_state,
        extra={"script": script_name, "script_label": SCRIPT_LABELS[script_name], "completed": False},
        table=status_table,
    )
    demo_status_store.set_latest(stored, table=status_table)

    say_text = _turn_say_text(turn, decision)
    return _redirect_twiml(say_text, action_url)
