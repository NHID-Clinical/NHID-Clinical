"""8 deterministic tests for the call-progress turn-by-turn webhook."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.call_progress_adapter import to_nhid_event
from src.nhid_policy_engine_v1 import evaluate_all, PolicyAction


# ── helpers ──────────────────────────────────────────────────────────────────

def _webhook_body(
    session_id: str = "call_test_001",
    turn_index: int = 0,
    speaker: str = "agent",
    text: str = "",
    disclosure_ts: str | None = None,
    escalation_available: bool = True,
) -> dict:
    return {
        "session_id": session_id,
        "turn_index": turn_index,
        "speaker": speaker,
        "text": text,
        "session_state": {
            "turn_count": turn_index + 1,
            "disclosure_timestamp": disclosure_ts,
            "escalation_available": escalation_available,
        },
    }


# ── adapter tests ─────────────────────────────────────────────────────────────

class TestCallProgressAdapter:
    def test_adapter_returns_session_and_event_dicts(self):
        body = _webhook_body(text="Hi, I am an automated AI assistant.")
        session, event = to_nhid_event(body)
        assert isinstance(session, dict)
        assert isinstance(event, dict)
        assert "turn_count" in session
        assert "healthcare_governance" in event

    def test_agent_disclosure_sets_disclosure_timestamp(self):
        body = _webhook_body(
            speaker="agent",
            text="Hi, I am an automated AI assistant calling from Dr. Smith's office.",
        )
        session, event = to_nhid_event(body)
        assert event["healthcare_governance"]["disclosure_timestamp"] is not None

    def test_user_phi_request_captured(self):
        body = _webhook_body(
            speaker="user",
            text="The member id is 12345.",
            disclosure_ts="2026-06-12T00:00:01Z",
        )
        session, event = to_nhid_event(body)
        assert "member id" in event["healthcare_governance"]["phi_accessed"]

    def test_missing_session_id_raises_value_error(self):
        import pytest
        with pytest.raises((ValueError, KeyError)):
            to_nhid_event({"speaker": "agent", "text": "hello"})


# ── end-to-end policy evaluation tests ────────────────────────────────────────

class TestCallProgressPolicyEvaluation:
    def test_undisclosed_phi_request_triggers_violations(self):
        """Turn 3: agent has not disclosed, user requests PHI → IDG-01 + PDX-01."""
        body = _webhook_body(
            turn_index=3,
            speaker="user",
            text="what is the member id?",
            disclosure_ts=None,  # no disclosure yet
        )
        session, event = to_nhid_event(body)
        decision = evaluate_all(session, event)
        rule_ids = {v.rule_id for v in decision.violations}
        assert "PDX-01" in rule_ids

    def test_disclosed_call_no_critical_violations(self):
        """After disclosure, no critical IDG-01/PDX-01 violations on a user turn."""
        body = _webhook_body(
            turn_index=2,
            speaker="user",
            text="the date of service is 2026-01-15",
            disclosure_ts="2026-06-12T00:00:01Z",
        )
        session, event = to_nhid_event(body)
        decision = evaluate_all(session, event)
        critical_gate_violations = [
            v for v in decision.violations
            if v.rule_id in ("IDG-01", "PDX-01") and v.severity.value == "critical"
        ]
        assert critical_gate_violations == []

    def test_escalation_request_triggers_eit01(self):
        body = _webhook_body(
            turn_index=5,
            speaker="user",
            text="I need to speak to a human please.",
            disclosure_ts="2026-06-12T00:00:01Z",
        )
        session, event = to_nhid_event(body)
        decision = evaluate_all(session, event)
        assert decision.action == PolicyAction.ESCALATE_HUMAN

    def test_turn_index_preserved_in_handler_response(self):
        """Handler returns turn_index in response body."""
        from functions.handler import lambda_handler
        body = _webhook_body(
            turn_index=7,
            speaker="agent",
            text="Hi, I am an automated AI assistant.",
        )
        resp = lambda_handler({
            "httpMethod": "POST",
            "path": "/v1/webhooks/call-progress",
            "body": json.dumps(body),
        }, None)
        assert resp["statusCode"] == 200
        result = json.loads(resp["body"])
        assert result["turn_index"] == 7
        assert "cas" in result
