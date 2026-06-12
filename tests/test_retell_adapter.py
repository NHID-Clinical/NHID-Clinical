"""6 deterministic tests for the Retell AI adapter."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.retell_adapter import to_nhid_event
from src.nhid_policy_engine_v1 import evaluate_all, PolicyAction

# Retell uses epoch milliseconds for start_timestamp
_START_MS = 1_718_150_400_000  # 2024-06-12T00:00:00Z


def _make_payload(
    call_id: str = "retell_call_001",
    transcript: list | None = None,
) -> dict:
    return {
        "call_id": call_id,
        "start_timestamp": _START_MS,
        "transcript_object": transcript or [],
    }


class TestRetellAdapter:
    def test_returns_session_and_event_dicts(self):
        payload = _make_payload(transcript=[
            {"role": "agent", "content": "I am an automated system.", "words": []},
            {"role": "user", "content": "Understood.", "words": []},
        ])
        session, event = to_nhid_event(payload)
        assert isinstance(session, dict)
        assert isinstance(event, dict)
        assert "turn_count" in session
        assert "healthcare_governance" in event

    def test_agent_disclosure_sets_disclosure_timestamp(self):
        payload = _make_payload(transcript=[
            {"role": "agent", "content": "Hi, I am an automated AI bot calling for Apex Medical.",
             "words": [{"start": 0}]},
        ])
        session, event = to_nhid_event(payload)
        assert event["healthcare_governance"]["disclosure_timestamp"] is not None

    def test_no_agent_disclosure_leaves_timestamp_none(self):
        payload = _make_payload(transcript=[
            {"role": "agent", "content": "Good morning, how can I help?", "words": []},
        ])
        session, event = to_nhid_event(payload)
        assert event["healthcare_governance"]["disclosure_timestamp"] is None

    def test_user_phi_keyword_captured(self):
        payload = _make_payload(transcript=[
            {"role": "agent", "content": "I am an automated system.", "words": []},
            {"role": "user", "content": "The claim number is 9988.", "words": []},
        ])
        session, event = to_nhid_event(payload)
        assert "claim number" in event["healthcare_governance"]["phi_accessed"]

    def test_session_id_set_from_call_id(self):
        payload = _make_payload(call_id="retell_abc_xyz")
        session, event = to_nhid_event(payload)
        assert event["session_id"] == "retell_abc_xyz"

    def test_undisclosed_phi_request_produces_pdx01_violation(self):
        payload = _make_payload(transcript=[
            {"role": "user", "content": "My date of birth is 1980-01-01.", "words": []},
        ])
        session, event = to_nhid_event(payload)
        decision = evaluate_all(session, event)
        rule_ids = {v.rule_id for v in decision.violations}
        assert "PDX-01" in rule_ids
