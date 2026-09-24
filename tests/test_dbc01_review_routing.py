"""Unit tests for src/dbc01_review_routing.should_route_to_review().

Pure logic, no DB — verifies the SOP's routing criteria
(docs/dbc01-human-review-sop.md) against PolicyDecision/violations shapes.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.dbc01_review_routing import (
    DBC01_PHRASE_TRIGGER,
    should_route_to_review,
)
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
        result = should_route_to_review(decision)
        assert result.route is True
        assert result.trigger_reason == DBC01_PHRASE_TRIGGER

    def test_critical_artifact_violation_routes(self):
        decision = _decision(
            [BoundaryViolation("DBC-01", "persona phrase", ViolationSeverity.MAJOR)]
        )
        result = should_route_to_review(decision)
        assert result.route is True
        assert result.trigger_reason == DBC01_PHRASE_TRIGGER

    def test_critical_takes_precedence_over_major_when_both_present(self):
        decision = _decision(
            [
                BoundaryViolation("DBC-01", "phrase match", ViolationSeverity.MAJOR),
                BoundaryViolation("DBC-01", "persona phrase", ViolationSeverity.MAJOR),
            ]
        )
        result = should_route_to_review(decision)
        assert result.trigger_reason == DBC01_PHRASE_TRIGGER

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
        result = should_route_to_review(decision)
        assert result.route is True
        assert result.trigger_reason == DBC01_PHRASE_TRIGGER


