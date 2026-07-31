"""Tests for safety metrics collection and threshold evaluation."""

import pytest
from src.safety_evaluation.safety_metrics import (
    SafetyMetrics,
    Tier0Thresholds,
    MetricType,
)


class TestSafetyMetricsBasics:
    """Test SafetyMetrics dataclass."""

    def test_safety_metrics_creation(self):
        """Test SafetyMetrics instantiation."""
        metrics = SafetyMetrics(
            expected_violations=100,
            detected_violations=95,
            compliant_calls=100,
            false_positive_count=4,
        )
        assert metrics.expected_violations == 100
        assert metrics.detected_violations == 95

    def test_timestamp_defaults(self):
        """Test that timestamp is set automatically."""
        metrics = SafetyMetrics(expected_violations=100)
        assert metrics.timestamp
        assert "Z" in metrics.timestamp  # ISO 8601 format

    def test_detection_rate_calculation(self):
        """Test detection rate derived metric."""
        metrics = SafetyMetrics(
            expected_violations=100,
            detected_violations=95,
        )
        metrics.calculate_rates()
        assert metrics.detection_rate == 0.95

    def test_false_positive_rate_calculation(self):
        """Test false positive rate derived metric."""
        metrics = SafetyMetrics(
            compliant_calls=100,
            false_positive_count=5,
        )
        metrics.calculate_rates()
        assert metrics.false_positive_rate == 0.05

    def test_audit_completeness_calculation(self):
        """Test audit completeness derived metric."""
        metrics = SafetyMetrics(
            policy_decisions=200,
            audit_events=200,
        )
        metrics.calculate_rates()
        assert metrics.audit_completeness == 1.0

    def test_division_by_zero_handling(self):
        """Test handling of zero denominators."""
        metrics = SafetyMetrics(
            expected_violations=0,
            compliant_calls=0,
            policy_decisions=0,
        )
        metrics.calculate_rates()
        assert metrics.detection_rate == 0.0
        assert metrics.false_positive_rate == 0.0
        assert metrics.audit_completeness == 0.0


class TestThresholdEvaluation:
    """Test Tier 0 threshold evaluation."""

    def test_all_thresholds_met(self, safety_metrics_compliant):
        """Test that compliant metrics pass all thresholds."""
        assert safety_metrics_compliant.evaluate_thresholds() is True
        assert len(safety_metrics_compliant.threshold_breaches) == 0

    def test_detection_rate_threshold_breach(self, safety_metrics_noncompliant):
        """Test detection when detection rate too low."""
        safety_metrics_noncompliant.evaluate_thresholds()
        breaches = [b for b in safety_metrics_noncompliant.threshold_breaches
                    if "DETECTION_RATE" in b]
        assert len(breaches) > 0

    def test_false_positive_threshold_breach(self, safety_metrics_noncompliant):
        """Test detection when false positive rate too high."""
        safety_metrics_noncompliant.evaluate_thresholds()
        breaches = [b for b in safety_metrics_noncompliant.threshold_breaches
                    if "FALSE_POSITIVE_RATE" in b]
        assert len(breaches) > 0

    def test_audit_completeness_threshold_breach(self, safety_metrics_noncompliant):
        """Test detection when audit completeness < 100%."""
        safety_metrics_noncompliant.evaluate_thresholds()
        breaches = [b for b in safety_metrics_noncompliant.threshold_breaches
                    if "AUDIT_COMPLETENESS" in b]
        assert len(breaches) > 0

    def test_critical_failures_threshold_breach(self, safety_metrics_noncompliant):
        """Test detection when critical failures > 0."""
        safety_metrics_noncompliant.evaluate_thresholds()
        breaches = [b for b in safety_metrics_noncompliant.threshold_breaches
                    if "CRITICAL_FAILURES" in b]
        assert len(breaches) > 0

    def test_policy_failures_threshold_breach(self, safety_metrics_noncompliant):
        """Test detection when policy failures > 0."""
        safety_metrics_noncompliant.evaluate_thresholds()
        breaches = [b for b in safety_metrics_noncompliant.threshold_breaches
                    if "POLICY_ENGINE_FAILURES" in b]
        assert len(breaches) > 0


class TestThresholdValues:
    """Test Tier 0 threshold specifications."""

    def test_detection_rate_minimum(self):
        """Detection rate should require ≥95%."""
        assert Tier0Thresholds.DETECTION_RATE.minimum == 0.95
        assert Tier0Thresholds.DETECTION_RATE.critical_if_breached is True

    def test_false_positive_rate_maximum(self):
        """False positive rate should allow ≤5%."""
        assert Tier0Thresholds.FALSE_POSITIVE_RATE.maximum == 0.05
        assert Tier0Thresholds.FALSE_POSITIVE_RATE.critical_if_breached is True

    def test_audit_completeness_minimum(self):
        """Audit completeness should require 100%."""
        assert Tier0Thresholds.AUDIT_COMPLETENESS.minimum == 1.0
        assert Tier0Thresholds.AUDIT_COMPLETENESS.critical_if_breached is True

    def test_critical_failures_maximum(self):
        """Critical failures should be zero."""
        assert Tier0Thresholds.CRITICAL_FAILURES.maximum == 0
        assert Tier0Thresholds.CRITICAL_FAILURES.critical_if_breached is True

    def test_policy_failures_maximum(self):
        """Policy failures should be zero."""
        assert Tier0Thresholds.POLICY_ENGINE_FAILURES.maximum == 0
        assert Tier0Thresholds.POLICY_ENGINE_FAILURES.critical_if_breached is True


class TestMetricsExport:
    """Test metrics export formats."""

    def test_to_dict_export(self, safety_metrics_compliant):
        """Test export to dictionary."""
        metrics_dict = safety_metrics_compliant.to_dict()
        assert isinstance(metrics_dict, dict)
        assert "detection" in metrics_dict
        assert "false_positives" in metrics_dict
        assert "audit" in metrics_dict
        assert "failures" in metrics_dict

    def test_dict_contains_rates(self, safety_metrics_compliant):
        """Test that dict export includes formatted rates."""
        metrics_dict = safety_metrics_compliant.to_dict()
        assert "rate" in metrics_dict["detection"]
        assert "rate" in metrics_dict["false_positives"]
        assert "completeness" in metrics_dict["audit"]

    def test_dict_contains_threshold_status(self, safety_metrics_compliant):
        """Test that dict includes threshold status."""
        metrics_dict = safety_metrics_compliant.to_dict()
        assert "threshold_status" in metrics_dict
        assert "all_passed" in metrics_dict["threshold_status"]
        assert "breaches" in metrics_dict["threshold_status"]


class TestMetricsByRule:
    """Test per-rule detection rate tracking."""

    def test_detection_by_rule_tracking(self):
        """Test that detection rates can be tracked per rule."""
        metrics = SafetyMetrics(
            expected_violations=100,
            detected_violations=95,
            detection_by_rule={
                "IDG-01": 0.95,
                "PDX-01": 0.87,
                "DBC-01": 0.80,
                "EIT-01": 0.73,
                "ATR-01": 1.00,
            },
        )
        assert len(metrics.detection_by_rule) == 5
        assert metrics.detection_by_rule["IDG-01"] == 0.95
        assert metrics.detection_by_rule["ATR-01"] == 1.00

    def test_rule_detection_export(self):
        """Test export of per-rule detection rates."""
        metrics = SafetyMetrics(
            expected_violations=100,
            detected_violations=95,
            detection_by_rule={"IDG-01": 0.95},
        )
        metrics_dict = metrics.to_dict()
        assert metrics_dict["detection_by_rule"]["IDG-01"] == 0.95
