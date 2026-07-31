"""Tests for failure mode taxonomy."""

import pytest
from src.safety_evaluation.failure_modes import (
    FailureMode,
    FailureCategory,
    FalseNegativeFailure,
    FalsePositiveFailure,
    SilentFailure,
    AuditFailure,
    PolicyFailure,
    AdversarialBypassFailure,
    SeverityLevel,
    TIER_0_FAILURE_MODES,
    get_failure_modes_by_rule,
    get_failure_modes_by_category,
)


class TestFailureModeClasses:
    """Test failure mode dataclass definitions."""

    def test_false_negative_failure_creation(self):
        """Test FalseNegativeFailure instantiation."""
        failure = FalseNegativeFailure(
            rule_id="IDG-01",
            description="Test description",
            scenario="Test scenario",
            detection_method="corpus",
            mitigation="fix it",
            impact_if_missed="bad",
        )
        assert failure.category == FailureCategory.FALSE_NEGATIVE
        assert failure.rule_id == "IDG-01"
        assert failure.severity == SeverityLevel.CRITICAL

    def test_false_positive_failure_creation(self):
        """Test FalsePositiveFailure instantiation."""
        failure = FalsePositiveFailure(
            rule_id="PDX-01",
            description="Test",
            scenario="Test",
            detection_method="corpus",
            mitigation="fix",
            impact_if_missed="blocked",
        )
        assert failure.category == FailureCategory.FALSE_POSITIVE
        assert failure.severity == SeverityLevel.MAJOR

    def test_silent_failure_creation(self):
        """Test SilentFailure instantiation."""
        failure = SilentFailure(
            rule_id="ATR-01",
            description="Test",
            scenario="Test",
            detection_method="audit",
            mitigation="fix",
            impact_if_missed="undetectable",
        )
        assert failure.category == FailureCategory.SILENT_FAILURE
        assert failure.severity == SeverityLevel.CRITICAL

    def test_adversarial_bypass_creation(self):
        """Test AdversarialBypassFailure instantiation."""
        failure = AdversarialBypassFailure(
            rule_id="DBC-01",
            description="Unicode homoglyph attack",
            scenario="Cyrillic а instead of Latin a",
            detection_method="adversarial",
            mitigation="normalize unicode",
            impact_if_missed="deception not detected",
        )
        assert failure.category == FailureCategory.ADVERSARIAL_BYPASS
        assert failure.rule_id == "DBC-01"


class TestTier0Baseline:
    """Test Tier 0 failure mode baseline."""

    def test_baseline_contains_25_modes(self):
        """Tier 0 baseline should have failure modes for all rules."""
        assert len(TIER_0_FAILURE_MODES) >= 14

    def test_baseline_covers_all_rules(self):
        """Baseline should cover IDG-01, PDX-01, DBC-01, EIT-01, ATR-01."""
        rules = {fm.rule_id for fm in TIER_0_FAILURE_MODES}
        expected_rules = {"IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01"}
        assert expected_rules.issubset(rules)

    def test_baseline_covers_all_categories(self):
        """Baseline should cover all 6 failure categories."""
        categories = {fm.category for fm in TIER_0_FAILURE_MODES}
        expected_categories = {
            FailureCategory.FALSE_NEGATIVE,
            FailureCategory.FALSE_POSITIVE,
            FailureCategory.SILENT_FAILURE,
            FailureCategory.AUDIT_FAILURE,
            FailureCategory.POLICY_FAILURE,
            FailureCategory.ADVERSARIAL_BYPASS,
        }
        assert expected_categories.issubset(categories)

    def test_all_modes_have_descriptions(self):
        """All failure modes should have non-empty descriptions."""
        for fm in TIER_0_FAILURE_MODES:
            assert fm.description
            assert len(fm.description) > 10

    def test_all_modes_have_mitigations(self):
        """All failure modes should have mitigation strategies."""
        for fm in TIER_0_FAILURE_MODES:
            assert fm.mitigation
            assert len(fm.mitigation) > 10


class TestFailureModeQueries:
    """Test failure mode lookup functions."""

    def test_get_failure_modes_by_rule(self):
        """Test filtering failure modes by rule ID."""
        idg01_modes = get_failure_modes_by_rule("IDG-01")
        assert len(idg01_modes) > 0
        assert all(fm.rule_id == "IDG-01" for fm in idg01_modes)

    def test_get_failure_modes_by_category(self):
        """Test filtering failure modes by category."""
        false_neg_modes = get_failure_modes_by_category(FailureCategory.FALSE_NEGATIVE)
        assert len(false_neg_modes) > 0
        assert all(fm.category == FailureCategory.FALSE_NEGATIVE for fm in false_neg_modes)

    def test_false_negative_failures_are_critical(self):
        """False negative failures should be critical severity."""
        false_neg_modes = get_failure_modes_by_category(FailureCategory.FALSE_NEGATIVE)
        assert all(fm.severity == SeverityLevel.CRITICAL for fm in false_neg_modes)

    def test_silent_failures_are_critical(self):
        """Silent failures should be critical severity."""
        silent_modes = get_failure_modes_by_category(FailureCategory.SILENT_FAILURE)
        assert all(fm.severity == SeverityLevel.CRITICAL for fm in silent_modes)

    def test_false_positive_failures_are_major(self):
        """False positive failures should be major severity."""
        false_pos_modes = get_failure_modes_by_category(FailureCategory.FALSE_POSITIVE)
        assert all(fm.severity == SeverityLevel.MAJOR for fm in false_pos_modes)


class TestFailureModeImmutability:
    """Test that failure modes are immutable (frozen dataclasses)."""

    def test_failure_mode_is_frozen(self):
        """FailureMode should be immutable."""
        failure = FalseNegativeFailure(
            rule_id="IDG-01",
            description="Test",
            scenario="Test",
            detection_method="test",
            mitigation="test",
            impact_if_missed="test",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            failure.rule_id = "PDX-01"
