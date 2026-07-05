"""
ElevenLabs post-call webhook handler for the Beacon outbound demo.

ElevenLabs delivers the full transcript once a call ends (not turn-by-turn
like Twilio), so this handler evaluates every turn in one pass: thread
session_state/disclosure_timestamp across turns exactly like
functions.twilio_demo_handler does, run each turn through the same real
pipeline (adapters.call_progress_adapter.to_nhid_event() +
src.nhid_policy_engine_v1.evaluate_all()), and write the accumulated result
into functions.demo_status_store keyed by ElevenLabs' conversation_id --
the same store, the same shape, the Twilio scripted demo line uses, so the
website's NHIDDemoStatus.render() component works unmodified for both.

This is infrastructure for the demo website feature, NOT the NHID-Clinical
governance framework itself.
"""

from __future__ import annotations

import json
from typing import Any

from adapters.call_progress_adapter import to_nhid_event
from adapters.elevenlabs_postcall_adapter import iter_turns
from functions import demo_status_store
from functions.twilio_demo_handler import _DEMO_GATE_RULE_IDS, _decision_summary
from src.nhid_policy_engine_v1 import evaluate_all

_SCRIPT_LABEL = "Beacon outbound call"


def _critical_violation_count(turns: list[dict[str, Any]]) -> int:
    return sum(
        1
        for t in turns
        for v in t.get("decision", {}).get("violations", [])
        if v.get("severity") == "critical" and v.get("rule_id") in _DEMO_GATE_RULE_IDS
    )


def _handle_elevenlabs_postcall_webhook(event: dict[str, Any], *, status_table=None) -> dict[str, Any]:
    raw_body = event.get("body") or ""
    if not raw_body:
        return _error(400, "Request body is required")

    try:
        payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError as exc:
        return _error(400, f"Invalid JSON: {exc}")

    try:
        turns = list(iter_turns(payload))
    except ValueError as exc:
        return _error(400, str(exc))

    conversation_id = payload.get("conversation_id")
    session_state: dict[str, Any] = {
        "turn_count": 0,
        "disclosure_timestamp": None,
        "escalation_available": True,
    }

    stored: dict[str, Any] = {}
    for turn in turns:
        session, policy_event = to_nhid_event({**turn, "session_state": session_state})
        decision = evaluate_all(session, policy_event)

        session_state = dict(session_state)
        session_state["turn_count"] = turn["turn_index"] + 1
        session_state["disclosure_timestamp"] = policy_event["healthcare_governance"]["disclosure_timestamp"]

        stored = demo_status_store.put_turn(
            conversation_id,
            turn["turn_index"],
            _decision_summary(decision),
            session_state=session_state,
            extra={"script_label": _SCRIPT_LABEL, "completed": False},
            table=status_table,
        )

    accumulated_turns = stored.get("turns", []) if stored else []
    stored = demo_status_store.put_turn(
        conversation_id,
        len(turns),
        {"type": "summary", "critical_violation_count": _critical_violation_count(accumulated_turns)},
        session_state=session_state,
        extra={"script_label": _SCRIPT_LABEL, "completed": True},
        table=status_table,
    )
    demo_status_store.set_latest(stored, table=status_table)

    return _ok({"conversation_id": conversation_id, "turns_evaluated": len(turns)})


_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,x-api-key",
    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
}


def _ok(body: dict) -> dict:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps({"error": message}),
    }
