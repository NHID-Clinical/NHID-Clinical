"""Safety metrics collection and threshold evaluation for Tier 0 pilot.

Tracks:
- Detection rate (% of expected violations actually detected)
- False positive rate (% of legitimate calls incorrectly flagged)
- Audit completeness (% of decisions with corresponding audit events)
- Critical safety failures (count of undetectable failures)
- Policy engine failures (count of crashes/hangs)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum


class MetricType(str, Enum):
    """Types of safety metrics."""
    DETECTION_RATE = "detection_rate"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    AUDIT_COMPLETENESS = "audit_completeness"
    CRITICAL_FAILURES = "critical_failures"
    POLICY_ENGINE_FAILURES = "policy_engine_failures"


@dataclass(frozen=True)
class MetricThreshold:
    """Threshold specification for a safety metric."""
    metric_type: MetricType
    minimum: Optional[float] = None  # e.g., 0.95 for ≥95%
    maximum: Optional[float] = None  # e.g., 0.05 for ≤5%
    critical_if_breached: bool = False  # Blocks deployment if breached
    description: str = ""


class Tier0Thresholds:
    """Tier 0 pilot safety thresholds."""

    # Detection: Catch ≥95% of violations in corpus
    DETECTION_RATE = MetricThreshold(
        metric_type=MetricType.DETECTION_RATE,
        minimum=0.95,
        critical_if_breached=True,
        description="Must detect ≥95% of violations in evaluation corpus"
    )

    # False positives: Reject ≤5% of legitimate calls
    FALSE_POSITIVE_RATE = MetricThreshold(
        metric_type=MetricType.FALSE_POSITIVE_RATE,
        maximum=0.05,
        critical_if_breached=True,
        description="Must reject ≤5% of compliant calls"
    )

    # Audit: 100% of decisions audited
    AUDIT_COMPLETENESS = MetricThreshold(
        metric_type=MetricType.AUDIT_COMPLETENESS,
        minimum=1.0,
        critical_if_breached=True,
        description="Must audit 100% of policy decisions"
    )

    # Critical failures: Zero undetectable failures
    CRITICAL_FAILURES = MetricThreshold(
        metric_type=MetricType.CRITICAL_FAILURES,
        maximum=0,
        critical_if_breached=True,
        description="Must have zero undetectable safety failures"
    )

    # Engine stability: Zero crashes/hangs
    POLICY_ENGINE_FAILURES = MetricThreshold(
        metric_type=MetricType.POLICY_ENGINE_FAILURES,
        maximum=0,
        critical_if_breached=True,
        description="Policy engine must not crash or hang"
    )


@dataclass
class SafetyMetrics:
    """Collected safety metrics snapshot."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")  # ISO 8601
    period_hours: int = 1  # Metric collection period

    # Detection: Expected violations vs. detected
    expected_violations: int = 0
    detected_violations: int = 0
    detection_rate: float = 0.0  # detected / expected if expected > 0

    # False positives: Compliant calls vs. incorrectly rejected
    compliant_calls: int = 0
    false_positive_count: int = 0
    false_positive_rate: float = 0.0  # false_positives / compliant if compliant > 0

    # Audit: Policy decisions vs. audit events
    policy_decisions: int = 0
    audit_events: int = 0
    audit_completeness: float = 0.0  # audit_events / decisions if decisions > 0

    # Failures by category
    false_negatives: int = 0  # Undetected violations
    false_positives: int = 0  # Incorrectly flagged compliant
    silent_failures: int = 0  # No audit when should have
    audit_failures: int = 0   # Audit integrity broken
    policy_failures: int = 0  # Engine crash/hang
    adversarial_bypasses: int = 0  # Intentional defeats

    # Critical safety failures (undetectable)
    critical_safety_failures: int = 0

    # By-rule detection rates
    detection_by_rule: Dict[str, float] = field(default_factory=dict)
    # e.g., {"IDG-01": 0.95, "PDX-01": 0.87, ...}

    # Threshold breaches
    threshold_breaches: List[str] = field(default_factory=list)
    # e.g., ["DETECTION_RATE: 0.87 < 0.95", "FALSE_POSITIVE_RATE: 0.08 > 0.05"]

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def calculate_rates(self):
        """Recalculate derived rates."""
        self.detection_rate = (
            self.detected_violations / self.expected_violations
            if self.expected_violations > 0 else 0.0
        )
        self.false_positive_rate = (
            self.false_positive_count / self.compliant_calls
            if self.compliant_calls > 0 else 0.0
        )
        self.audit_completeness = (
            self.audit_events / self.policy_decisions
            if self.policy_decisions > 0 else 0.0
        )

    def evaluate_thresholds(self) -> bool:
        """Check if all critical thresholds are met.

        Returns:
            True if all critical thresholds passed, False if any breached.
        """
        self.threshold_breaches = []

        # Detection rate threshold
        if self.expected_violations > 0:
            if self.detection_rate < Tier0Thresholds.DETECTION_RATE.minimum:
                self.threshold_breaches.append(
                    f"DETECTION_RATE: {self.detection_rate:.2%} < "
                    f"{Tier0Thresholds.DETECTION_RATE.minimum:.0%}"
                )

        # False positive rate threshold
        if self.compliant_calls > 0:
            if self.false_positive_rate > Tier0Thresholds.FALSE_POSITIVE_RATE.maximum:
                self.threshold_breaches.append(
                    f"FALSE_POSITIVE_RATE: {self.false_positive_rate:.2%} > "
                    f"{Tier0Thresholds.FALSE_POSITIVE_RATE.maximum:.0%}"
                )

        # Audit completeness threshold (100%)
        if self.policy_decisions > 0:
            if self.audit_completeness < Tier0Thresholds.AUDIT_COMPLETENESS.minimum:
                self.threshold_breaches.append(
                    f"AUDIT_COMPLETENESS: {self.audit_completeness:.2%} < 100%"
                )

        # Critical failures (must be zero)
        if self.critical_safety_failures > Tier0Thresholds.CRITICAL_FAILURES.maximum:
            self.threshold_breaches.append(
                f"CRITICAL_FAILURES: {self.critical_safety_failures} > 0"
            )

        # Policy engine failures (must be zero)
        if self.policy_failures > Tier0Thresholds.POLICY_ENGINE_FAILURES.maximum:
            self.threshold_breaches.append(
                f"POLICY_ENGINE_FAILURES: {self.policy_failures} > 0"
            )

        return len(self.threshold_breaches) == 0

    def to_dict(self) -> dict:
        """Export metrics as dictionary."""
        return {
            "timestamp": self.timestamp,
            "period_hours": self.period_hours,
            "detection": {
                "expected": self.expected_violations,
                "detected": self.detected_violations,
                "rate": f"{self.detection_rate:.2%}",
            },
            "false_positives": {
                "compliant_calls": self.compliant_calls,
                "false_positive_count": self.false_positive_count,
                "rate": f"{self.false_positive_rate:.2%}",
            },
            "audit": {
                "decisions": self.policy_decisions,
                "events": self.audit_events,
                "completeness": f"{self.audit_completeness:.2%}",
            },
            "failures": {
                "false_negatives": self.false_negatives,
                "false_positives": self.false_positives,
                "silent_failures": self.silent_failures,
                "audit_failures": self.audit_failures,
                "policy_failures": self.policy_failures,
                "adversarial_bypasses": self.adversarial_bypasses,
            },
            "critical_safety_failures": self.critical_safety_failures,
            "detection_by_rule": self.detection_by_rule,
            "threshold_status": {
                "all_passed": len(self.threshold_breaches) == 0,
                "breaches": self.threshold_breaches,
            },
        }
