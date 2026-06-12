"""8 deterministic tests for DBC-01 text heuristics (impersonation phrase detection)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.nhid_policy_engine_v1 import (
    evaluate_dbc01,
    _assertion_implies_human,
    PolicyAction,
    ViolationSeverity,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_event(assertion_text: str = "", flags: list | None = None,
                disclosure_ts: str | None = "2026-06-12T00:00:01Z") -> tuple:
    session = {"turn_count": 1, "escalation_path_available": True}
    event = {
        "event_id": "test-dbc-001",
        "timestamp": "2026-06-12T00:00:00Z",
        "session_id": "sess-dbc-001",
        "event_type": "POLICY",
        "state_before": "ACTIVE",
        "counterparty_type": "human_operator",
        "healthcare_governance": {
            "disclosure_timestamp": disclosure_ts,
            "identity_assertion_text": assertion_text,
            "deceptive_artifact_flags": flags or [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": [],
        },
        "input_payload": {"speech_text": "", "raw_form_fields": None},
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
    }
    return session, event


# ── tests ─────────────────────────────────────────────────────────────────────

class TestDBC01Heuristics:
    def test_clean_assertion_no_violation(self):
        session, event = _make_event("Hi, I am an automated AI system.")
        d = evaluate_dbc01(session, event)
        assert d.action == PolicyAction.CONTINUE_AI
        assert d.violations == []

    def test_empty_assertion_no_violation(self):
        session, event = _make_event("")
        d = evaluate_dbc01(session, event)
        assert d.action == PolicyAction.CONTINUE_AI

    def test_iam_a_human_phrase_triggers_major(self):
        session, event = _make_event("Hi there, I am a human calling from a provider's office.")
        d = evaluate_dbc01(session, event)
        assert d.action == PolicyAction.LOG_ONLY
        assert any(v.rule_id == "DBC-01" and v.severity == ViolationSeverity.MAJOR
                   for v in d.violations)

    def test_real_person_calling_triggers_major(self):
        session, event = _make_event("This is a real person calling from Dr. Smith's office.")
        d = evaluate_dbc01(session, event)
        assert d.action == PolicyAction.LOG_ONLY
        majors = [v for v in d.violations if v.severity == ViolationSeverity.MAJOR]
        assert len(majors) == 1

    def test_reason_code_for_text_only_match(self):
        session, event = _make_event("I am a human, I promise.")
        d = evaluate_dbc01(session, event)
        assert d.reason_code == "DBC01_IMPERSONATION_PHRASE_DETECTED"

    def test_artifact_flag_still_triggers_critical(self):
        session, event = _make_event("Automated system.", flags=["synthetic_breathing"])
        d = evaluate_dbc01(session, event)
        criticals = [v for v in d.violations if v.severity == ViolationSeverity.CRITICAL]
        assert len(criticals) == 1
        assert d.reason_code == "DBC01_ARTIFACT_DETECTED"

    def test_both_flag_and_phrase_captured(self):
        session, event = _make_event(
            "I am a human calling you.", flags=["voice_clone_detected"]
        )
        d = evaluate_dbc01(session, event)
        assert len(d.violations) == 2
        severities = {v.severity for v in d.violations}
        assert ViolationSeverity.CRITICAL in severities
        assert ViolationSeverity.MAJOR in severities

    def test_assertion_implies_human_helper_case_insensitive(self):
        assert _assertion_implies_human("I AM A HUMAN") is not None
        assert _assertion_implies_human("totally automated system") is None
