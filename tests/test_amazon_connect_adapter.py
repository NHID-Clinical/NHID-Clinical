"""6 deterministic tests for the Amazon Connect Contact Lens adapter."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.amazon_connect_adapter import to_nhid_event
from src.nhid_policy_engine_v1 import evaluate_all, PolicyAction


def _make_payload(
    contact_id: str = "connect_contact_001",
    transcript: list | None = None,
) -> dict:
    return {
        "ContactId": contact_id,
        "ConnectedToSystemTimestamp": "2026-06-12T00:00:00Z",
        "Transcript": transcript or [],
    }


class TestAmazonConnectAdapter:
    def test_returns_session_and_event_dicts(self):
        payload = _make_payload(transcript=[
            {"ParticipantRole": "AGENT", "Content": "I am an automated system.", "BeginOffsetMillis": 0},
            {"ParticipantRole": "CUSTOMER", "Content": "OK.", "BeginOffsetMillis": 3000},
        ])
        session, event = to_nhid_event(payload)
        assert isinstance(session, dict)
        assert isinstance(event, dict)
        assert "turn_count" in session
        assert "healthcare_governance" in event

    def test_agent_disclosure_sets_disclosure_timestamp(self):
        payload = _make_payload(transcript=[
            {"ParticipantRole": "AGENT",
             "Content": "Hello, this is an automated AI system calling from Summit Health.",
             "BeginOffsetMillis": 500},
        ])
        session, event = to_nhid_event(payload)
        assert event["healthcare_governance"]["disclosure_timestamp"] is not None

    def test_no_agent_disclosure_leaves_timestamp_none(self):
        payload = _make_payload(transcript=[
            {"ParticipantRole": "AGENT", "Content": "Good morning.", "BeginOffsetMillis": 0},
        ])
        session, event = to_nhid_event(payload)
        assert event["healthcare_governance"]["disclosure_timestamp"] is None

    def test_customer_phi_keyword_captured(self):
        payload = _make_payload(transcript=[
            {"ParticipantRole": "AGENT", "Content": "I am an automated system.", "BeginOffsetMillis": 0},
            {"ParticipantRole": "CUSTOMER", "Content": "The group number is 7721.", "BeginOffsetMillis": 3000},
        ])
        session, event = to_nhid_event(payload)
        assert "group number" in event["healthcare_governance"]["phi_accessed"]

    def test_session_id_set_from_contact_id(self):
        payload = _make_payload(contact_id="connect_contact_XYZ")
        session, event = to_nhid_event(payload)
        assert event["session_id"] == "connect_contact_XYZ"

    def test_undisclosed_phi_request_produces_pdx01_violation(self):
        payload = _make_payload(transcript=[
            {"ParticipantRole": "CUSTOMER", "Content": "My NPI is 1234567890.", "BeginOffsetMillis": 0},
        ])
        session, event = to_nhid_event(payload)
        decision = evaluate_all(session, event)
        rule_ids = {v.rule_id for v in decision.violations}
        assert "PDX-01" in rule_ids
