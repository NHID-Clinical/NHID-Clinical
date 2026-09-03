"""Adversarial robustness metrics calculation.

Computes attack success rates, control robustness scores,
coverage metrics, and severity-weighted bypass scores.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class SeverityLevel(str, Enum):
    """Attack severity for weighting."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


@dataclass(frozen=True)
class AdversarialMetrics:
    """Calculated robustness metrics from campaign."""
    total_attacks: int
    successful_bypasses: int
    partial_bypasses: int
    total_bypass_attempts: int
    attack_success_rate: float  # successful / total
    control_robustness_score: float  # 1 - ASR
    coverage_ratio: float  # tested scenarios / potential scenarios
    severity_weighted_bypass_score: float  # Weighted by attack severity
    false_negative_rate: float  # Violations missed
    false_positive_rate: float  # Extra violations detected
    test_confidence: float  # Confidence in results (based on coverage)

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary."""
        return {
            "total_attacks": self.total_attacks,
            "successful_bypasses": self.successful_bypasses,
            "partial_bypasses": self.partial_bypasses,
            "total_bypass_attempts": self.total_bypass_attempts,
            "attack_success_rate": round(self.attack_success_rate, 4),
            "control_robustness_score": round(self.control_robustness_score, 4),
            "coverage_ratio": round(self.coverage_ratio, 4),
            "severity_weighted_bypass_score": round(self.severity_weighted_bypass_score, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "test_confidence": round(self.test_confidence, 4),
        }


class MetricsCalculator:
    """Calculate adversarial robustness metrics."""

    # Severity weighting for bypass scoring
    SEVERITY_WEIGHTS = {
        SeverityLevel.CRITICAL: 3.0,
        SeverityLevel.MAJOR: 2.0,
        SeverityLevel.MINOR: 1.0,
    }

    @staticmethod
    def calculate_attack_success_rate(
        successful_bypasses: int,
        total_attacks: int
    ) -> float:
        """Calculate ASR: successful bypasses / total attacks.

        Range: 0.0 (no bypasses) to 1.0 (all bypassed)
        Lower is better.
        """
        if total_attacks == 0:
            return 0.0
        return successful_bypasses / total_attacks

    @staticmethod
    def calculate_control_robustness_score(asr: float) -> float:
        """Calculate control robustness: 1 - ASR.

        Range: 0.0 (no control) to 1.0 (perfect control)
        Higher is better.
        """
        return 1.0 - asr

    @staticmethod
    def calculate_coverage_ratio(
        tested_scenarios: int,
        total_possible_scenarios: int = 100  # Normalized baseline
    ) -> float:
        """Calculate coverage: tested / possible scenarios.

        Uses normalized baseline if not provided.
        Range: 0.0 to 1.0+
        Higher is better (but 1.0+ indicates comprehensive testing).
        """
        if total_possible_scenarios == 0:
            return 0.0
        return tested_scenarios / total_possible_scenarios

    @staticmethod
    def calculate_severity_weighted_bypass_score(
        bypass_results: List[Dict[str, Any]],
        total_attacks: int
    ) -> float:
        """Calculate severity-weighted bypass score.

        Gives more weight to critical/major attack bypasses.

        Args:
            bypass_results: List of bypassed attacks with severity
            total_attacks: Total number of attacks

        Returns:
            Weighted score (0-3.0, normalized to 0-1.0 range)
        """
        if total_attacks == 0:
            return 0.0

        total_weight = 0.0
        for result in bypass_results:
            severity = result.get("severity", "minor")
            weight = MetricsCalculator.SEVERITY_WEIGHTS.get(
                SeverityLevel(severity), 1.0
            )
            total_weight += weight

        # Normalize to 0-1.0 range
        # Max weight = total_attacks * 3.0 (all critical)
        max_weight = total_attacks * 3.0
        return total_weight / max_weight if max_weight > 0 else 0.0

    @staticmethod
    def calculate_false_negative_rate(
        missed_violations: List[str],
        total_expected_violations: int
    ) -> float:
        """Calculate false negative rate: missed violations / total expected.

        Range: 0.0 (none missed) to 1.0 (all missed)
        Lower is better.
        """
        if total_expected_violations == 0:
            return 0.0
        return len(missed_violations) / total_expected_violations

    @staticmethod
    def calculate_false_positive_rate(
        extra_violations: List[str],
        total_detected_violations: int
    ) -> float:
        """Calculate false positive rate: extra violations / total detected.

        Range: 0.0 (none extra) to 1.0 (all false positives)
        Lower is better.
        """
        if total_detected_violations == 0:
            return 0.0
        return len(extra_violations) / total_detected_violations

    @staticmethod
    def calculate_test_confidence(
        coverage: float,
        sample_size: int,
        effectiveness: float = None
    ) -> float:
        """Calculate confidence in test results.

        Factors in coverage, sample size, and tactic effectiveness.

        Range: 0.0 to 1.0
        Higher = more confident in results
        """
        # Base confidence from coverage (up to 0.7)
        coverage_component = min(coverage * 0.7, 0.7)

        # Sample size component (up to 0.2)
        # Assume 50+ samples = high confidence
        sample_component = min(sample_size / 50.0 * 0.2, 0.2)

        # Effectiveness component (up to 0.1)
        # Assumes many different tactics tested
        effectiveness_component = (effectiveness or 0.5) * 0.1

        return coverage_component + sample_component + effectiveness_component

    @staticmethod
    def from_campaign_results(
        campaign_summary: Dict[str, Any],
        baseline_scenario_count: int = 100
    ) -> AdversarialMetrics:
        """Calculate metrics from red team campaign summary.

        Args:
            campaign_summary: Output from RedTeamRunner.campaign_summary()
            baseline_scenario_count: Total possible scenarios for coverage calc

        Returns:
            AdversarialMetrics with all calculated values
        """
        outcomes = campaign_summary.get("outcomes", {})
        total = campaign_summary.get("total_cases", 0)

        detected = outcomes.get("detected", 0)
        bypassed = outcomes.get("bypassed", 0)
        partial = outcomes.get("partial", 0)
        errors = outcomes.get("errors", 0)

        # ASR = bypasses (complete and partial) / total
        successful_bypasses = bypassed
        total_bypass_attempts = bypassed + partial
        asr = MetricsCalculator.calculate_attack_success_rate(
            total_bypass_attempts, total
        )

        # Control robustness
        robustness = MetricsCalculator.calculate_control_robustness_score(asr)

        # Coverage
        coverage = MetricsCalculator.calculate_coverage_ratio(
            total, baseline_scenario_count
        )

        # Severity-weighted bypass score (requires detailed results)
        # Simplified version for campaign summary
        severity_weighted = MetricsCalculator.calculate_severity_weighted_bypass_score(
            [{"severity": "major"}] * total_bypass_attempts,
            total
        )

        # False negative rate (approximate from partial bypasses)
        false_negative = 0.0
        if partial > 0:
            # Partial bypasses indicate ~50% false negative on average
            false_negative = (partial / total) * 0.5

        # False positive rate (from extra detected violations)
        false_positive = 0.0  # Would need detailed results

        # Test confidence
        num_tactics = len(campaign_summary.get("tactic_effectiveness", {}))
        tactic_effectiveness = (num_tactics / 6.0) if num_tactics > 0 else 0.5
        confidence = MetricsCalculator.calculate_test_confidence(
            coverage, total, tactic_effectiveness
        )

        return AdversarialMetrics(
            total_attacks=total,
            successful_bypasses=successful_bypasses,
            partial_bypasses=partial,
            total_bypass_attempts=total_bypass_attempts,
            attack_success_rate=asr,
            control_robustness_score=robustness,
            coverage_ratio=coverage,
            severity_weighted_bypass_score=severity_weighted,
            false_negative_rate=false_negative,
            false_positive_rate=false_positive,
            test_confidence=confidence,
        )

    @staticmethod
    def assess_robustness_tier(metrics: AdversarialMetrics) -> str:
        """Assess overall robustness tier based on metrics.

        Returns:
            One of: "RED", "ORANGE", "YELLOW", "GREEN"
        """
        robustness = metrics.control_robustness_score
        coverage = metrics.coverage_ratio

        # RED: <50% robustness or <30% coverage
        if robustness < 0.5 or coverage < 0.3:
            return "RED"

        # ORANGE: 50-70% robustness or 30-60% coverage
        if robustness < 0.7 or coverage < 0.6:
            return "ORANGE"

        # YELLOW: 70-85% robustness or 60-80% coverage
        if robustness < 0.85 or coverage < 0.8:
            return "YELLOW"

        # GREEN: >85% robustness and >80% coverage
        return "GREEN"

    @staticmethod
    def generate_report(
        metrics: AdversarialMetrics,
        campaign_name: str = "Adversarial Robustness Assessment"
    ) -> str:
        """Generate human-readable metrics report.

        Args:
            metrics: Calculated AdversarialMetrics
            campaign_name: Name of assessment

        Returns:
            Formatted report string
        """
        tier = MetricsCalculator.assess_robustness_tier(metrics)

        report = f"# {campaign_name}\n\n"
        report += f"## Robustness Tier: {tier}\n\n"

        report += "## Core Metrics\n"
        report += f"- **Attack Success Rate (ASR):** {metrics.attack_success_rate*100:.1f}%\n"
        report += f"- **Control Robustness Score:** {metrics.control_robustness_score*100:.1f}%\n"
        report += f"- **Test Coverage:** {metrics.coverage_ratio*100:.1f}%\n"
        report += f"- **Test Confidence:** {metrics.test_confidence*100:.1f}%\n\n"

        report += "## Attack Summary\n"
        report += f"- **Total Attacks:** {metrics.total_attacks}\n"
        report += f"- **Successful Bypasses:** {metrics.successful_bypasses}\n"
        report += f"- **Partial Bypasses:** {metrics.partial_bypasses}\n"
        report += f"- **Total Bypass Attempts:** {metrics.total_bypass_attempts}\n\n"

        report += "## Detection Quality\n"
        report += f"- **False Negative Rate:** {metrics.false_negative_rate*100:.1f}%\n"
        report += f"- **False Positive Rate:** {metrics.false_positive_rate*100:.1f}%\n"
        report += f"- **Severity-Weighted Bypass Score:** {metrics.severity_weighted_bypass_score:.3f}\n\n"

        report += "## Recommendations\n"
        if tier == "RED":
            report += "- **CRITICAL:** Significant robustness gaps detected. Immediate remediation required.\n"
            report += "- Focus on highest-success-rate attack tactics\n"
            report += "- Expand detection rules for missed violations\n"
        elif tier == "ORANGE":
            report += "- **WARNING:** Notable robustness gaps in specific areas.\n"
            report += "- Target medium-success-rate tactics for fixes\n"
            report += "- Increase test coverage to 80%+\n"
        elif tier == "YELLOW":
            report += "- **MONITOR:** Minor robustness issues identified.\n"
            report += "- Continue monitoring attack patterns\n"
            report += "- Ensure coverage remains above 80%\n"
        else:  # GREEN
            report += "- **APPROVED:** Robustness metrics within acceptable range.\n"
            report += "- Continue regular adversarial testing\n"
            report += "- Maintain coverage at current levels\n"

        return report
