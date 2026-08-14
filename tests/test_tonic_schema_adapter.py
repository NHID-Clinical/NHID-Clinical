"""Regression tests for the Tonic corpus schema adapter.

Each test here pins one of four defects that together produced a 100%
false-positive rate on IDG-01 and 0% detection on EIT-01 against the Tonic
corpus. The policy engine was correct throughout; the adapter was starving it.
"""

import pytest

from scripts.tonic_schema_adapter import TonicschemAdapter
from src.nhid_policy_engine_v1 import evaluate_all


def _turn(idx, event_type, **kw):
    base = {
        "turn_number": idx,
        "timestamp": f"2024-01-01T08:00:{idx:02d}Z",
        "speaker": "VOICE_AGENT",
        "utterance": "",
        "event_type": event_type,
        "contains_phi": False,
        "contains_pii": False,
        "disclosure_status": "N/A",
        "escalation_requested": False,
        "escalation_outcome": "N/A",
        "deception_pattern": "NONE",
    }
    base.update(kw)
    return base


def _disclosed_session():
    """Compliant shape: disclosure at turn 1, PHI afterwards at turn 2."""
    return [
        _turn(0, "SMALL_TALK", speaker="CALLER", utterance="Hi, calling about a visit."),
        _turn(1, "IDENTITY_DISCLOSURE", disclosure_status="DISCLOSED",
              utterance="Before we continue, I want to let you know I am an automated system."),
        _turn(2, "PHI_REQUEST", speaker="CALLER", contains_phi=True,
              utterance="The member id is 12345."),
        _turn(3, "CLOSING", utterance="Thanks, have a good day."),
    ]


class TestDisclosureAssertionCarryForward:
    """IDG-01 requires disclosure_timestamp AND non-empty identity_assertion_text."""

    def test_assertion_text_persists_after_the_disclosure_turn(self):
        adapter = TonicschemAdapter()
        turns = _disclosed_session()
        for idx in (1, 2, 3):
            gov = adapter.build_governance_context("S1", turns, idx)
            assert gov["disclosure_timestamp"] == 1
            assert gov["identity_assertion_text"], (
                f"turn {idx}: assertion text dropped after disclosure — "
                "IDG-01 will re-fire on every subsequent turn"
            )

    def test_no_assertion_text_before_disclosure(self):
        adapter = TonicschemAdapter()
        gov = adapter.build_governance_context("S1", _disclosed_session(), 0)
        assert gov["disclosure_timestamp"] is None
        assert gov["identity_assertion_text"] == ""

    def test_engine_stops_flagging_idg01_on_post_disclosure_turns(self):
        adapter = TonicschemAdapter()
        turns = _disclosed_session()
        for idx in (1, 2, 3):
            decision = evaluate_all(
                adapter.build_session(turns, idx),
                adapter.adapt_turn("S1", turns, idx),
            )
            assert "IDG-01" not in {v.rule_id for v in decision.violations}


class TestEscalationPathDerivation:
    """The corpus encodes an unhonored escalation as an absence, never as DEFLECTED."""

    def test_request_without_transfer_is_not_honored(self):
        turns = _disclosed_session()
        turns.insert(2, _turn(2, "ESCALATION_REQUEST", speaker="CALLER",
                              escalation_requested=True,
                              utterance="Can you transfer me to an actual person?"))
        assert TonicschemAdapter().infer_escalation_path_available(turns) is False

    def test_request_followed_by_transfer_is_honored(self):
        turns = _disclosed_session()
        turns.insert(2, _turn(2, "ESCALATION_REQUEST", speaker="CALLER",
                              escalation_requested=True,
                              utterance="Can you transfer me to an actual person?"))
        turns.insert(3, _turn(3, "ESCALATION_OUTCOME",
                              escalation_outcome="TRANSFERRED_TO_HUMAN",
                              utterance="Connecting you now."))
        assert TonicschemAdapter().infer_escalation_path_available(turns) is True

    def test_session_with_no_request_is_available(self):
        assert TonicschemAdapter().infer_escalation_path_available(_disclosed_session()) is True

    def test_engine_receives_escalation_path_in_session_dict(self):
        adapter = TonicschemAdapter()
        turns = _disclosed_session()
        turns.insert(2, _turn(2, "ESCALATION_REQUEST", speaker="CALLER",
                              escalation_requested=True,
                              utterance="Can you transfer me to an actual person?"))
        session = adapter.build_session(turns, 2)
        assert session["escalation_path_available"] is False, (
            "escalation must reach the engine via the session dict; routing it "
            "into _source metadata made EIT-01 undetectable"
        )


class TestAuditContextCompleteness:
    """ATR-01 fired on every turn because required audit fields were absent."""

    @pytest.mark.parametrize("field", ["event_type", "execution_context", "replay_mode"])
    def test_required_audit_fields_present(self, field):
        assert field in TonicschemAdapter().build_audit_context("S1", 0)

    def test_replay_mode_is_a_valid_enum_value(self):
        assert TonicschemAdapter().build_audit_context("S1", 0)["replay_mode"] in (
            "live", "replay", "test",
        )

    def test_execution_context_carries_all_three_versions(self):
        ctx = TonicschemAdapter().build_audit_context("S1", 0)["execution_context"]
        for key in ("pipeline_version", "policy_engine_version", "nhid_schema_version"):
            assert ctx.get(key)

    def test_compliant_turn_raises_no_atr01_violations(self):
        adapter = TonicschemAdapter()
        turns = _disclosed_session()
        decision = evaluate_all(
            adapter.build_session(turns, 3), adapter.adapt_turn("S1", turns, 3)
        )
        assert "ATR-01" not in {v.rule_id for v in decision.violations}
