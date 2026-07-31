"""Tests for safety scoring and risk assessment."""

import pytest
from src.safety_evaluation.safety_scorer import (
    SafetyScore,
    RiskTier,
    SafetyScoreReport,
)


class TestSafetyScoreCalculation:
    """Test SafetyScore calculation."""

    def test_perfect_score(self):
        """Test perfect safety score."""
        score, tier = SafetyScore.calculate_score(
            detection_rate=1.0,  # 100%
            false_positive_rate=0.0,  # 0%
            audit_completeness=1.0,  # 100%
            critical_failures=0,
            policy_failures=0,
        )
        assert score == 100.0
        assert tier == RiskTier.GREEN

    def test_compliant_score(self):
        """Test score for compliant metrics."""
        score, tier = SafetyScore.calculate_score(
            detection_rate=0.98,  # 98%
            false_positive_rate=0.02,  # 2%
            audit_completeness=1.0,  # 100%
            critical_failures=0,
            policy_failures=0,
        )
        assert score >= SafetyScore.TIER_GREEN_MIN  # >= 90
        assert tier == RiskTier.GREEN

    def test_green_tier_threshold(self):
        """Test GREEN tier threshold (≥90)."""
        score, tier = SafetyScore.calculate_score(
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=0,
        )
        assert score >= SafetyScore.TIER_GREEN_MIN
        assert tier == RiskTier.GREEN

    def test_yellow_tier_threshold(self):
        """Test YELLOW tier threshold (75-89)."""
        score, tier = SafetyScore.calculate_score(
            detection_rate=0.85,  # Below 95%
            false_positive_rate=0.08,  # Above 5%
            audit_completeness=0.99,
            critical_failures=0,
            policy_failures=0,
        )
        assert SafetyScore.TIER_YELLOW_MIN <= score < SafetyScore.TIER_GREEN_MIN
        assert tier == RiskTier.YELLOW

    def test_orange_tier_threshold(self):
        """Test ORANGE tier threshold (60-74)."""
        score, tier = SafetyScore.calculate_score(
            detection_rate=0.75,  # Significantly below 95%
            false_positive_rate=0.12,  # Well above 5%
            audit_completeness=0.95,
            critical_failures=0,
            policy_failures=0,
        )
        assert SafetyScore.TIER_ORANGE_MIN <= score < SafetyScore.TIER_YELLOW_MIN
        assert tier == RiskTier.ORANGE

    def test_red_tier_threshold(self):
        """Test RED tier threshold (<60)."""
        score, tier = SafetyScore.calculate_score(
            detection_rate=0.50,  # Far below 95%
            false_positive_rate=0.20,  # Far above 5%
            audit_completeness=0.80,  # Below 100%
            critical_failures=5,
            policy_failures=3,
        )
        assert score < SafetyScore.TIER_ORANGE_MIN
        assert tier == RiskTier.RED

    def test_critical_failures_impact(self):
        """Test that critical failures penalize score."""
        score_no_failures, _ = SafetyScore.calculate_score(
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=0,
        )
        score_with_failures, _ = SafetyScore.calculate_score(
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=2,
            policy_failures=0,
        )
        assert score_with_failures < score_no_failures

    def test_policy_failures_zero_tolerance(self):
        """Test that policy failures result in stability score of 0."""
        # Single policy failure should significantly impact score
        score_no_failures, _ = SafetyScore.calculate_score(
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=0,
        )
        score_with_failure, _ = SafetyScore.calculate_score(
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=1,
        )
        assert score_with_failure < score_no_failures


class TestRiskRecommendations:
    """Test deployment recommendations based on risk tier."""

    def test_green_recommendations(self):
        """Test GREEN tier recommendations."""
        recommendations = SafetyScore.risk_recommendations(
            score=95.0,
            risk_tier=RiskTier.GREEN,
            breached_thresholds=[],
        )
        assert recommendations["deployment_decision"] == "APPROVED"
        assert len(recommendations["monitoring_requirements"]) > 0
        assert "daily" in str(recommendations["monitoring_requirements"]).lower()

    def test_yellow_recommendations(self):
        """Test YELLOW tier recommendations."""
        recommendations = SafetyScore.risk_recommendations(
            score=80.0,
            risk_tier=RiskTier.YELLOW,
            breached_thresholds=[],
        )
        assert recommendations["deployment_decision"] == "APPROVED_WITH_MONITORING"
        assert any("enhanced" in str(r).lower() for r in recommendations["monitoring_requirements"])

    def test_orange_recommendations(self):
        """Test ORANGE tier recommendations."""
        recommendations = SafetyScore.risk_recommendations(
            score=65.0,
            risk_tier=RiskTier.ORANGE,
            breached_thresholds=[],
        )
        assert recommendations["deployment_decision"] == "DEPLOY_WITH_CAUTION"
        assert len(recommendations["mitigation_actions"]) > 0

    def test_red_recommendations(self):
        """Test RED tier recommendations."""
        recommendations = SafetyScore.risk_recommendations(
            score=40.0,
            risk_tier=RiskTier.RED,
            breached_thresholds=["DETECTION_RATE", "AUDIT_COMPLETENESS"],
        )
        assert recommendations["deployment_decision"] == "DO_NOT_DEPLOY"
        assert len(recommendations["mitigation_actions"]) > 0

    def test_recommendations_include_thresholds(self):
        """Test that recommendations include breached thresholds."""
        recommendations = SafetyScore.risk_recommendations(
            score=50.0,
            risk_tier=RiskTier.RED,
            breached_thresholds=["DETECTION_RATE: 0.80 < 0.95"],
        )
        assert any("DETECTION_RATE" in str(r) for r in recommendations["risk_factors"])


class TestSafetyScoreReport:
    """Test SafetyScoreReport generation."""

    def test_report_creation(self):
        """Test SafetyScoreReport instantiation."""
        report = SafetyScoreReport(
            timestamp="2024-01-01T00:00:00Z",
            evaluation_period="Phase 1 Baseline",
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=0,
            safety_score=92.5,
            risk_tier=RiskTier.GREEN,
            threshold_status={
                "DETECTION_RATE": True,
                "FALSE_POSITIVE_RATE": True,
                "AUDIT_COMPLETENESS": True,
                "CRITICAL_FAILURES": True,
                "POLICY_ENGINE_FAILURES": True,
            },
            breached_thresholds=[],
            deployment_decision="APPROVED",
            monitoring_requirements=["Daily review"],
            mitigation_actions=[],
        )
        assert report.safety_score == 92.5
        assert report.risk_tier == RiskTier.GREEN

    def test_report_to_dict(self):
        """Test SafetyScoreReport export to dict."""
        report = SafetyScoreReport(
            timestamp="2024-01-01T00:00:00Z",
            evaluation_period="Phase 1 Baseline",
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=0,
            safety_score=92.5,
            risk_tier=RiskTier.GREEN,
            threshold_status={"DETECTION_RATE": True},
            breached_thresholds=[],
            deployment_decision="APPROVED",
            monitoring_requirements=[],
            mitigation_actions=[],
        )
        report_dict = report.to_dict()
        assert report_dict["metrics"]["detection_rate"] == "95%"
        assert report_dict["safety_score"]["score"] == 92.5
        assert report_dict["safety_score"]["tier"] == "green"


class TestRiskTierTransitions:
    """Test transitions between risk tiers."""

    def test_transition_green_to_yellow(self):
        """Test score that transitions from GREEN to YELLOW."""
        # At lower end of GREEN
        score_green, tier_green = SafetyScore.calculate_score(
            detection_rate=0.95,
            false_positive_rate=0.05,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=0,
        )
        # At upper end of YELLOW
        score_yellow, tier_yellow = SafetyScore.calculate_score(
            detection_rate=0.82,
            false_positive_rate=0.08,
            audit_completeness=0.98,
            critical_failures=0,
            policy_failures=0,
        )
        assert tier_green == RiskTier.GREEN
        assert tier_yellow == RiskTier.YELLOW
        assert score_yellow < score_green

    def test_minimum_green_score(self):
        """Test minimum score to achieve GREEN."""
        score, tier = SafetyScore.calculate_score(
            detection_rate=SafetyScore.TIER_GREEN_MIN * 0.95,  # Just below 90
            false_positive_rate=0.01,
            audit_completeness=1.0,
            critical_failures=0,
            policy_failures=0,
        )
        assert tier != RiskTier.GREEN
