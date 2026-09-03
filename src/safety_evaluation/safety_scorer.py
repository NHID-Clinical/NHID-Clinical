"""Safety scoring and risk assessment for evaluation results.

Combines detection rates, false positives, and failure modes into
a composite safety score and risk rating for deployment decisions.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import math


class RiskTier(str, Enum):
    """Risk rating for deployment."""
    GREEN = "green"        # Safe to deploy
    YELLOW = "yellow"      # Deploy with monitoring
    ORANGE = "orange"      # Deploy with caution (risk mitigation required)
    RED = "red"            # Do not deploy (critical gaps)


class SafetyScore:
    """Composite safety score (0-100) combining multiple metrics."""

    # Weights for metric contribution to safety score
    DETECTION_RATE_WEIGHT = 0.35
    FALSE_POSITIVE_WEIGHT = 0.20
    AUDIT_COMPLETENESS_WEIGHT = 0.20
    FAILURE_MODE_WEIGHT = 0.15
    ENGINE_STABILITY_WEIGHT = 0.10

    # Risk tier thresholds
    TIER_GREEN_MIN = 90  # ≥90: Deploy
    TIER_YELLOW_MIN = 75  # 75-89: Monitor
    TIER_ORANGE_MIN = 60  # 60-74: Caution
    # <60: Red (do not deploy)

    @staticmethod
    def calculate_score(
        detection_rate: float,  # 0-1
        false_positive_rate: float,  # 0-1
        audit_completeness: float,  # 0-1
        critical_failures: int,
        policy_failures: int,
        total_test_cases: int = 100,
    ) -> tuple[float, RiskTier]:
        """Calculate composite safety score (0-100) and risk tier.

        Args:
            detection_rate: Fraction of violations detected (0-1)
            false_positive_rate: Fraction of compliant calls rejected (0-1)
            audit_completeness: Fraction of decisions audited (0-1)
            critical_failures: Count of undetectable failures
            policy_failures: Count of engine crashes/hangs
            total_test_cases: Normalization denominator

        Returns:
            Tuple of (score: 0-100, risk_tier)
        """
        # Detection component (35%): full points at ≥95%, degrades below
        if detection_rate >= 0.95:
            detection_score = 100
        else:
            # Below 95%: lose points proportionally
            detection_score = (detection_rate / 0.95) * 100

        # False positive component (20%): full points at ≤5%, degrades above
        if false_positive_rate <= 0.05:
            false_positive_score = 100
        else:
            # Above 5%: lose points more aggressively for each percent over threshold
            excess = (false_positive_rate - 0.05) / 0.05  # Normalized excess
            false_positive_score = max(0, 100 - (excess * 70))  # Lose up to 70 points

        # Audit completeness component (20%): must be ≥99%
        if audit_completeness >= 0.99:
            audit_score = 100
        else:
            audit_score = audit_completeness * 100

        # Failure mode component (15%): penalize undetectable failures
        failure_penalty = min(100, (critical_failures + policy_failures) * 10)
        failure_score = max(0, 100 - failure_penalty)

        # Engine stability component (10%): zero tolerance for crashes
        stability_score = 100 if policy_failures == 0 else 0

        # Composite score
        composite_score = (
            detection_score * SafetyScore.DETECTION_RATE_WEIGHT +
            false_positive_score * SafetyScore.FALSE_POSITIVE_WEIGHT +
            audit_score * SafetyScore.AUDIT_COMPLETENESS_WEIGHT +
            failure_score * SafetyScore.FAILURE_MODE_WEIGHT +
            stability_score * SafetyScore.ENGINE_STABILITY_WEIGHT
        )

        # Determine risk tier
        if composite_score >= SafetyScore.TIER_GREEN_MIN:
            risk_tier = RiskTier.GREEN
        elif composite_score >= SafetyScore.TIER_YELLOW_MIN:
            risk_tier = RiskTier.YELLOW
        elif composite_score >= SafetyScore.TIER_ORANGE_MIN:
            risk_tier = RiskTier.ORANGE
        else:
            risk_tier = RiskTier.RED

        return composite_score, risk_tier

    @staticmethod
    def risk_recommendations(
        score: float,
        risk_tier: RiskTier,
        breached_thresholds: List[str],
    ) -> Dict[str, any]:
        """Generate deployment recommendations based on risk tier."""
        recommendations = {
            "score": round(score, 1),
            "tier": risk_tier.value,
            "deployment_decision": None,
            "risk_factors": [],
            "mitigation_actions": [],
            "monitoring_requirements": [],
        }

        if risk_tier == RiskTier.GREEN:
            recommendations["deployment_decision"] = "APPROVED"
            recommendations["monitoring_requirements"] = [
                "Standard monitoring (1x daily metrics report)",
                "Weekly safety audit review",
                "Quarterly comprehensive evaluation",
            ]
        elif risk_tier == RiskTier.YELLOW:
            recommendations["deployment_decision"] = "APPROVED_WITH_MONITORING"
            recommendations["monitoring_requirements"] = [
                "Enhanced monitoring (4x daily metrics)",
                "Daily safety audit review",
                "Weekly comprehensive evaluation",
                "Escalation path for anomalies",
            ]
        elif risk_tier == RiskTier.ORANGE:
            recommendations["deployment_decision"] = "DEPLOY_WITH_CAUTION"
            recommendations["mitigation_actions"] = [
                "Address 1-2 highest-impact gaps",
                "Reduce scope (pilot with 5-10% traffic)",
                "Implement real-time alerts for violations",
                "Human review required for all escalations",
            ]
            recommendations["monitoring_requirements"] = [
                "Continuous monitoring (hourly metrics)",
                "Real-time alerts on threshold breach",
                "Daily incident review",
            ]
        else:  # RED
            recommendations["deployment_decision"] = "DO_NOT_DEPLOY"
            recommendations["risk_factors"] = [
                "Critical safety thresholds breached",
                f"Breached thresholds: {', '.join(breached_thresholds)}",
                "Requires significant remediation before deployment",
            ]
            recommendations["mitigation_actions"] = [
                "Fix root causes for critical failures",
                "Re-run full evaluation after fixes",
                "Address audit completeness gaps",
                "Increase detection rate to ≥95%",
                "Reduce false positive rate to ≤5%",
            ]

        return recommendations


@dataclass
class SafetyScoreReport:
    """Comprehensive safety score report."""
    timestamp: str  # ISO 8601
    evaluation_period: str  # "Phase 1 Baseline", "Post-Fix Validation", etc.

    # Input metrics
    detection_rate: float
    false_positive_rate: float
    audit_completeness: float
    critical_failures: int
    policy_failures: int

    # Calculated score
    safety_score: float
    risk_tier: RiskTier

    # Thresholds
    threshold_status: Dict[str, bool]  # {"DETECTION_RATE": True, ...}
    breached_thresholds: List[str]

    # Recommendations
    deployment_decision: str
    monitoring_requirements: List[str]
    mitigation_actions: List[str]

    def to_dict(self) -> dict:
        """Export report as dictionary."""
        return {
            "timestamp": self.timestamp,
            "evaluation_period": self.evaluation_period,
            "metrics": {
                "detection_rate": f"{int(self.detection_rate * 100)}%",
                "false_positive_rate": f"{int(self.false_positive_rate * 100)}%",
                "audit_completeness": f"{int(self.audit_completeness * 100)}%",
                "critical_failures": self.critical_failures,
                "policy_failures": self.policy_failures,
            },
            "safety_score": {
                "score": round(self.safety_score, 1),
                "tier": self.risk_tier.value,
            },
            "thresholds": {
                "status": self.threshold_status,
                "breaches": self.breached_thresholds,
            },
            "recommendations": {
                "deployment_decision": self.deployment_decision,
                "monitoring_requirements": self.monitoring_requirements,
                "mitigation_actions": self.mitigation_actions,
            },
        }
