"""
DBC-01 Human-Review Routing
============================
Operationalizes docs/dbc01-human-review-sop.md's routing criteria as a pure,
DB-free function: given a PolicyDecision (from evaluate_all()) and an optional
CAS result dict (from functions/handler.py's _policy_cas()), decide whether
the session must be queued for human review.

Two independent trigger sources, per the SOP:
  1. Any DBC-01 violation in decision.violations (MAJOR == phrase match,
     CRITICAL == artifact flags). The composite PolicyDecision.reason_code
     is NOT used here: evaluate_all() sets reason_code/action from whichever
     of the six rules is highest-priority (see _priority in evaluate_all()),
     so a DBC-01 MAJOR violation can be present in `violations` even when
     reason_code reflects an unrelated DENY_DATA/ESCALATE_HUMAN rule. Scanning
     `violations` directly is the same approach src/cts_runner.py's
     _check_violations() already uses to verify per-rule outcomes.
  2. CAS score below CAS_CONDITIONAL_TRUST (the SOP's "Review Required or
     worse" threshold) — independent of any DBC-01 finding.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.nhid_cas import CAS_CONDITIONAL_TRUST
from src.nhid_policy_engine_v1 import PolicyDecision, ViolationSeverity

DBC01_PHRASE_TRIGGER = "DBC01_IMPERSONATION_PHRASE_DETECTED"
DBC01_ARTIFACT_TRIGGER = "DBC01_ARTIFACT_DETECTED"
CAS_REVIEW_TRIGGER = "CAS_REVIEW_REQUIRED"


@dataclass(frozen=True)
class RoutingResult:
    route: bool
    trigger_reason: str | None = None
    severity: str | None = None


def should_route_to_review(decision: PolicyDecision, cas: dict | None = None) -> RoutingResult:
    """Decide whether `decision` (+ optional `cas` dict with a "score" key)
    must be queued for human review, per the SOP's routing criteria."""
    dbc01_violations = [v for v in decision.violations if v.rule_id == "DBC-01"]
    if dbc01_violations:
        has_critical = any(v.severity == ViolationSeverity.CRITICAL for v in dbc01_violations)
        if has_critical:
            return RoutingResult(True, DBC01_ARTIFACT_TRIGGER, ViolationSeverity.CRITICAL.value)
        return RoutingResult(True, DBC01_PHRASE_TRIGGER, ViolationSeverity.MAJOR.value)

    if cas is not None and cas.get("score") is not None and cas["score"] < CAS_CONDITIONAL_TRUST:
        return RoutingResult(True, CAS_REVIEW_TRIGGER, None)

    return RoutingResult(False)
