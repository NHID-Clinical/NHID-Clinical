"""6 deterministic tests for the Vonage Voice API adapter."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.vonage_adapter import to_nhid_event
from src.nhid_policy_engine_v1 import evaluate_all, PolicyAction


def _make_payload(
    uuid_val: str = "call_vonage_001",
    start_time: str = "2026-06-12T00:00:00Z",
    transcript: list | None = None,
) -> dict:
    return {
        "uuid": uuid_val,
        "start_time": start_time,
        "transcript": transcript or [],
    }


class TestVonageAdapter:
    def test_returns_session_and_event_dicts(self):
        payload = _make_payload(transcript=[
            {"speaker": "bot", "speech": "Hi, I am an automated system.", "start_time": "0.5"},
            {"speaker": "user", "speech": "Okay.", "start_time": "3.0"},
        ])
        session, event = to_nhid_event(payload)
        assert isinstance(session, dict)
        assert isinstance(event, dict)
        assert "turn_count" in session
        assert "healthcare_governance" in event

    def test_bot_disclosure_sets_disclosure_timestamp(self):
        payload = _make_payload(transcript=[
            {"speaker": "bot", "speech": "I am an automated AI agent calling for Acme Health.",
             "start_time": "0.5"},
        ])
        session, event = to_nhid_event(payload)
        assert event["healthcare_governance"]["disclosure_timestamp"] is not None

    def test_no_bot_disclosure_leaves_timestamp_none(self):
        payload = _make_payload(transcript=[
            {"speaker": "bot", "speech": "Good morning, how can I help you?", "start_time": "0.5"},
        ])
        session, event = to_nhid_event(payload)
        assert event["healthcare_governance"]["disclosure_timestamp"] is None

    def test_user_phi_keyword_captured(self):
        payload = _make_payload(transcript=[
            {"speaker": "bot", "speech": "I am an automated system.", "start_time": "0.5"},
            {"speaker": "user", "speech": "The member id is 90210.", "start_time": "3.0"},
        ])
        session, event = to_nhid_event(payload)
        assert "member id" in event["healthcare_governance"]["phi_accessed"]

    def test_turn_count_matches_transcript_length(self):
        transcript = [
            {"speaker": "bot", "speech": "I am an automated system.", "start_time": "0.0"},
            {"speaker": "user", "speech": "Yes.", "start_time": "2.0"},
            {"speaker": "bot", "speech": "Can I get the NPI?", "start_time": "4.0"},
        ]
        payload = _make_payload(transcript=transcript)
        session, _ = to_nhid_event(payload)
        assert session["turn_count"] == 3

    def test_undisclosed_phi_request_produces_pdx01_violation(self):
        payload = _make_payload(transcript=[
            {"speaker": "user", "speech": "My member id is 12345.", "start_time": "1.0"},
        ])
        session, event = to_nhid_event(payload)
        decision = evaluate_all(session, event)
        rule_ids = {v.rule_id for v in decision.violations}
        assert "PDX-01" in rule_ids
