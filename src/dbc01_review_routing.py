"""
DBC-01 Human-Review Routing
============================
Operationalizes docs/dbc01-human-review-sop.md's routing criteria as a pure,
DB-free function: given a PolicyDecision (from evaluate_all()), decide whether
the session must be queued for human review.

Trigger source: any DBC-01 violation in decision.violations. The composite
PolicyDecision.reason_code is NOT used here: evaluate_all() sets
reason_code/action from whichever rule is highest-priority (see _priority in
evaluate_all()), so a DBC-01 violation can be present in `violations` even when
reason_code reflects an unrelated DENY_DATA/ESCALATE_HUMAN rule. Scanning
`violations` directly is the same approach src/cts_runner.py's
_check_violations() already uses to verify per-rule outcomes.

Two triggers were removed rather than retained:

  * The composite-score trigger. It routed on a CAS value below a "Conditional
    Trust" threshold. The composite score, its tiers and its badges have been
    withdrawn (see docs/claim-boundaries.md): a single blended number over
    heterogeneous denominators is not a defensible basis for a review decision,
    and the tier vocabulary read as a certification this project does not issue.

  * The artifact trigger. It fired on `deceptive_artifact_flags` supplied in the
    event payload — i.e. self-reported by the agent being evaluated. A deception
    control that depends on the deceiver declaring the deception establishes
    nothing, so the flag is no longer read and CRITICAL is no longer reachable
    from DBC-01.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.nhid_policy_engine_v1 import PolicyDecision, ViolationSeverity

DBC01_PHRASE_TRIGGER = "DBC01_IMPERSONATION_PHRASE_DETECTED"


@dataclass(frozen=True)
class RoutingResult:
    route: bool
    trigger_reason: str | None = None
    severity: str | None = None


def should_route_to_review(decision: PolicyDecision) -> RoutingResult:
    """Decide whether `decision` must be queued for human review, per the SOP's
    routing criteria.

    A DBC-01 violation is now always a persona/impersonation-phrase finding, so
    the severity reported is MAJOR. The CRITICAL path is retained in the type
    only because ViolationSeverity is shared; DBC-01 no longer produces it.
    """
    dbc01_violations = [v for v in decision.violations if v.rule_id == "DBC-01"]
    if dbc01_violations:
        return RoutingResult(True, DBC01_PHRASE_TRIGGER, ViolationSeverity.MAJOR.value)

    return RoutingResult(False)
