"""Unit tests for src/dbc01_review_routing.should_route_to_review().

Pure logic, no DB — verifies the SOP's routing criteria
(docs/dbc01-human-review-sop.md) against PolicyDecision/violations shapes.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.dbc01_review_routing import (
    CAS_REVIEW_TRIGGER,
    DBC01_ARTIFACT_TRIGGER,
    DBC01_PHRASE_TRIGGER,
    should_route_to_review,
)
from src.nhid_cas import CAS_CONDITIONAL_TRUST
from src.nhid_policy_engine_v1 import (
    BoundaryViolation,
    PolicyAction,
    PolicyDecision,
    ViolationSeverity,
)


def _decision(violations, action=PolicyAction.LOG_ONLY):
    return PolicyDecision(action=action, reason_code="TEST", violations=violations)


class TestDBC01ViolationRouting:
    def test_major_phrase_violation_routes(self):
        decision = _decision(
            [BoundaryViolation("DBC-01", "phrase match", ViolationSeverity.MAJOR)]
        )
        result = should_route_to_review(decision, cas=None)
        assert result.route is True
        assert result.trigger_reason == DBC01_PHRASE_TRIGGER

    def test_critical_artifact_violation_routes(self):
        decision = _decision(
            [BoundaryViolation("DBC-01", "artifact flag", ViolationSeverity.CRITICAL)]
        )
        result = should_route_to_review(decision, cas=None)
        assert result.route is True
        assert result.trigger_reason == DBC01_ARTIFACT_TRIGGER

    def test_critical_takes_precedence_over_major_when_both_present(self):
        decision = _decision(
            [
                BoundaryViolation("DBC-01", "phrase match", ViolationSeverity.MAJOR),
                BoundaryViolation("DBC-01", "artifact flag", ViolationSeverity.CRITICAL),
            ]
        )
        result = should_route_to_review(decision, cas=None)
        assert result.trigger_reason == DBC01_ARTIFACT_TRIGGER

    def test_dbc01_violation_routes_even_when_composite_action_is_higher_priority(self):
        # Composite action/reason_code can be dominated by an unrelated rule
        # (e.g. ATR-01 DENY_DATA) while DBC-01's own violation is still present
        # in the merged violations list — routing must not depend on the
        # composite reason_code.
        decision = _decision(
            [
                BoundaryViolation("ATR-01", "missing field", ViolationSeverity.CRITICAL),
                BoundaryViolation("DBC-01", "phrase match", ViolationSeverity.MAJOR),
            ],
            action=PolicyAction.DENY_DATA,
        )
        result = should_route_to_review(decision, cas=None)
        assert result.route is True
        assert result.trigger_reason == DBC01_PHRASE_TRIGGER


class TestCASRouting:
    def test_cas_below_conditional_trust_routes(self):
        decision = _decision([], action=PolicyAction.CONTINUE_AI)
        result = should_route_to_review(
            decision,
            cas={"score": CAS_CONDITIONAL_TRUST - 0.01, "tier": "Review Required"},
        )
        assert result.route is True
        assert result.trigger_reason == CAS_REVIEW_TRIGGER

    def test_cas_at_or_above_conditional_trust_does_not_route(self):
        decision = _decision([], action=PolicyAction.CONTINUE_AI)
        result = should_route_to_review(
            decision,
            cas={"score": CAS_CONDITIONAL_TRUST, "tier": "Verified Trust"},
        )
        assert result.route is False

    def test_no_cas_and_no_dbc01_violation_does_not_route(self):
        decision = _decision([], action=PolicyAction.CONTINUE_AI)
        result = should_route_to_review(decision, cas=None)
        assert result.route is False
        assert result.trigger_reason is None

    def test_clean_continue_ai_with_other_violations_does_not_route(self):
        # Non-DBC-01 violations alone are not a review trigger.
        decision = _decision(
            [BoundaryViolation("IDG-01", "minor note", ViolationSeverity.MINOR)],
            action=PolicyAction.CONTINUE_AI,
        )
        result = should_route_to_review(decision, cas={"score": 1.0, "tier": "Verified Trust"})
        assert result.route is False
