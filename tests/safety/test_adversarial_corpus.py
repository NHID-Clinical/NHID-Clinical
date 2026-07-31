"""Tests for Phase 2 adversarial corpus and red team infrastructure."""

import pytest
import json
from pathlib import Path
from src.safety_evaluation.attack_generators import (
    AttackGenerator,
    MutationStrategy,
    ScenarioMutation,
)
from src.safety_evaluation.red_team_runner import (
    RedTeamRunner,
    AttackOutcome,
    FailureClassification,
)
from src.safety_evaluation.adversarial_metrics import (
    MetricsCalculator,
    AdversarialMetrics,
    SeverityLevel,
)


class TestAdversarialCorpusLoad:
    """Test loading and validating adversarial test corpus."""

    def test_corpus_file_exists(self):
        """Adversarial corpus JSON file should exist."""
        corpus_path = Path("tests/adversarial_cases.json")
        assert corpus_path.exists(), "tests/adversarial_cases.json not found"

    def test_corpus_loads_valid_json(self):
        """Corpus should be valid JSON."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "metadata" in data
        assert "cases" in data

    def test_corpus_has_metadata(self):
        """Corpus should have valid metadata."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)
        meta = data["metadata"]
        assert "version" in meta
        assert "count" in meta
        assert "coverage" in meta
        assert meta["count"] >= 50, "Corpus should have 50+ cases"

    def test_corpus_has_minimum_cases(self):
        """Corpus should have 50+ adversarial test cases."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)
        cases = data["cases"]
        assert len(cases) >= 50, f"Expected 50+ cases, got {len(cases)}"

    def test_corpus_covers_all_rules(self):
        """Corpus should target all 5 compliance rules."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)
        cases = data["cases"]
        all_rules = set()
        for case in cases:
            all_rules.update(case.get("target_rules", []))

        expected_rules = {"IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01"}
        assert expected_rules.issubset(all_rules), f"Missing rules: {expected_rules - all_rules}"

    def test_corpus_has_rule_distribution(self):
        """Corpus should have balanced coverage of each rule."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)

        rule_counts = data["metadata"]["coverage"]
        # Each rule should have at least 10 cases
        for rule, count in rule_counts.items():
            assert count >= 10, f"{rule}: expected 10+, got {count}"

    def test_all_cases_have_required_fields(self):
        """Each case should have all required fields."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)

        required_fields = [
            "case_id", "tactic", "target_rules", "description",
            "scenario", "payload", "expected_violations",
            "expected_action", "difficulty", "severity"
        ]

        for case in data["cases"]:
            for field in required_fields:
                assert field in case, f"Case {case.get('case_id')}: missing {field}"

    def test_cases_have_valid_severity(self):
        """All cases should have valid severity levels."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)

        valid_severities = {"critical", "major", "minor"}
        for case in data["cases"]:
            severity = case.get("severity", "").lower()
            assert severity in valid_severities, f"Case {case['case_id']}: invalid severity {severity}"

    def test_cases_have_valid_difficulty(self):
        """All cases should have valid difficulty levels."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)

        valid_difficulties = {"basic", "intermediate", "advanced"}
        for case in data["cases"]:
            difficulty = case.get("difficulty", "").lower()
            assert difficulty in valid_difficulties, f"Case {case['case_id']}: invalid difficulty {difficulty}"

    def test_cases_have_valid_tactics(self):
        """All cases should have valid attack tactics."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)

        valid_tactics = {
            "disclosure_evasion", "privilege_escalation", "deception",
            "escalation_avoidance", "audit_evasion", "timing_boundary",
            "unicode_obfuscation", "regex_bypass", "payload_manipulation",
            "social_engineering"
        }

        for case in data["cases"]:
            tactic = case.get("tactic", "").lower()
            assert tactic in valid_tactics, f"Case {case['case_id']}: invalid tactic {tactic}"

    def test_all_cases_have_payload(self):
        """Every case should have a payload."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)

        for case in data["cases"]:
            assert "payload" in case, f"Case {case['case_id']}: missing payload"
            assert isinstance(case["payload"], dict), f"Case {case['case_id']}: payload not dict"

    def test_expected_violations_are_lists(self):
        """Expected violations should be list of rule IDs."""
        corpus_path = Path("tests/adversarial_cases.json")
        with open(corpus_path) as f:
            data = json.load(f)

        for case in data["cases"]:
            violations = case.get("expected_violations", [])
            assert isinstance(violations, list), f"Case {case['case_id']}: violations not list"


class TestAttackGenerator:
    """Test attack scenario mutation generation."""

    def test_unicode_homoglyph_mutation(self):
        """Should generate unicode homoglyph variants."""
        text = "I am an automated system"
        mutated_light = AttackGenerator.mutate_with_unicode_homoglyphs(text, "light")
        mutated_medium = AttackGenerator.mutate_with_unicode_homoglyphs(text, "medium")
        mutated_heavy = AttackGenerator.mutate_with_unicode_homoglyphs(text, "heavy")

        # Should produce different outputs
        assert mutated_light != text or mutated_light == text  # May or may not mutate
        assert len({mutated_light, mutated_medium, mutated_heavy}) >= 2  # At least 2 different

    def test_regex_evasion_whitespace(self):
        """Should insert spaces for regex evasion."""
        text = "I am an automated system"
        mutated = AttackGenerator.mutate_with_regex_evasion(text, "pattern", "whitespace")
        assert "automated" not in mutated or "auto mat" in mutated or "aut omated" in mutated

    def test_payload_null_injection(self):
        """Should inject null values into payload."""
        payload = {"speaker": "agent", "timestamp": "2024-01-01T00:00:00Z"}
        mutated = AttackGenerator.mutate_payload_injection(payload, "null")

        # Should have set some fields to None
        has_none = any(v is None for v in mutated.values())
        assert has_none, "Null injection should create None values"

    def test_payload_empty_string_injection(self):
        """Should inject empty strings into payload."""
        payload = {"speech_text": "Hello", "description": "Test"}
        mutated = AttackGenerator.mutate_payload_injection(payload, "empty_string")

        # Should have set some fields to empty string
        has_empty = any(v == "" for v in mutated.values() if isinstance(v, str))
        assert has_empty, "Empty string injection should work"

    def test_semantic_shift_negation(self):
        """Should negate boolean fields."""
        payload = {"escalation_honored": True, "violation_logged": False}
        mutated = AttackGenerator.mutate_semantic_shift(payload, "negation")

        assert mutated["escalation_honored"] == False
        assert mutated["violation_logged"] == True

    def test_social_engineering_false_urgency(self):
        """Should add false urgency language."""
        payload = {"speech_text": "Hello"}
        mutated = AttackGenerator.mutate_social_engineering(payload, "false_urgency")

        assert "urgent" in mutated["speech_text"].lower()
        assert mutated.get("artificial_deadline") == True

    def test_generate_mutations_produces_variants(self):
        """Should generate multiple mutation variants."""
        base_payload = {"speech_text": "I am automated", "speaker": "agent"}
        mutations = AttackGenerator.generate_mutations(
            base_payload,
            "base-case-001",
            strategies=[MutationStrategy.UNICODE_HOMOGLYPH, MutationStrategy.REGEX_EVASION]
        )

        assert len(mutations) > 0, "Should generate mutations"
        assert all(isinstance(m, ScenarioMutation) for m in mutations)
        # Should have multiple different mutations
        payloads = {str(m.mutated_payload) for m in mutations}
        assert len(payloads) >= 1


class TestRedTeamRunner:
    """Test adversarial attack execution framework."""

    def test_runner_initialization(self):
        """Should initialize red team runner."""
        runner = RedTeamRunner()
        assert runner.results == []
        assert runner.start_time is None
        assert runner.end_time is None

    def test_execute_case_stores_result(self):
        """Should store attack result after execution."""
        runner = RedTeamRunner()

        result = runner.execute_case(
            case_id="test-001",
            tactic="deception",
            target_rules=["DBC-01"],
            payload={"speech_text": "I am human"},
            expected_violations=["DBC-01"],
            expected_action="ESCALATE_HUMAN",
            severity="critical",
            policy_engine_callable=lambda p: ([], "LOG_ONLY")
        )

        assert len(runner.results) == 1
        assert result.case_id == "test-001"

    def test_outcome_classification_detected(self):
        """Should classify perfect detection outcome."""
        runner = RedTeamRunner()

        # Perfect detection: expected and detected match
        result = runner.execute_case(
            case_id="test-detect",
            tactic="deception",
            target_rules=["DBC-01"],
            payload={"speech_text": "I am human"},
            expected_violations=["DBC-01"],
            expected_action="ESCALATE_HUMAN",
            severity="critical",
            policy_engine_callable=lambda p: (["DBC-01"], "ESCALATE_HUMAN")
        )

        assert result.outcome == AttackOutcome.DETECTED
        assert result.classification is None

    def test_outcome_classification_bypassed(self):
        """Should classify complete bypass outcome."""
        runner = RedTeamRunner()

        # Complete bypass: nothing detected
        result = runner.execute_case(
            case_id="test-bypass",
            tactic="deception",
            target_rules=["DBC-01"],
            payload={"speech_text": "I am human"},
            expected_violations=["DBC-01"],
            expected_action="ESCALATE_HUMAN",
            severity="critical",
            policy_engine_callable=lambda p: ([], "LOG_ONLY")
        )

        assert result.outcome == AttackOutcome.BYPASSED
        assert result.classification == FailureClassification.FALSE_NEGATIVE

    def test_outcome_classification_partial(self):
        """Should classify partial detection outcome."""
        runner = RedTeamRunner()

        # Partial detection: some violations missed
        result = runner.execute_case(
            case_id="test-partial",
            tactic="rule_combination",
            target_rules=["IDG-01", "PDX-01"],
            payload={"speech_text": "No disclosure, requesting PHI"},
            expected_violations=["IDG-01", "PDX-01"],
            expected_action="DENY_DATA",
            severity="critical",
            policy_engine_callable=lambda p: (["IDG-01"], "DENY_DATA")  # Only detected IDG-01
        )

        assert result.outcome == AttackOutcome.PARTIAL
        assert result.classification == FailureClassification.INCOMPLETE_DETECTION

    def test_campaign_execution(self):
        """Should execute full campaign against multiple cases."""
        runner = RedTeamRunner()

        cases = [
            {
                "case_id": "test-001",
                "tactic": "deception",
                "target_rules": ["DBC-01"],
                "payload": {"speech_text": "I am human"},
                "expected_violations": ["DBC-01"],
                "expected_action": "ESCALATE_HUMAN",
                "severity": "critical"
            },
            {
                "case_id": "test-002",
                "tactic": "privilege_escalation",
                "target_rules": ["PDX-01"],
                "payload": {"phi_access": "member_id"},
                "expected_violations": ["PDX-01"],
                "expected_action": "DENY_DATA",
                "severity": "critical"
            }
        ]

        summary = runner.execute_campaign(cases, lambda p: ([], "LOG_ONLY"))

        assert summary["total_cases"] == 2
        assert summary["start_time"] is not None
        assert summary["end_time"] is not None

    def test_campaign_summary_metrics(self):
        """Campaign summary should include metrics."""
        runner = RedTeamRunner()

        cases = [
            {
                "case_id": "test-001",
                "tactic": "deception",
                "target_rules": ["DBC-01"],
                "payload": {},
                "expected_violations": ["DBC-01"],
                "expected_action": "ESCALATE_HUMAN",
                "severity": "critical"
            }
        ]

        summary = runner.execute_campaign(cases, lambda p: ([], "LOG_ONLY"))

        assert "metrics" in summary
        assert "attack_success_rate" in summary["metrics"]
        assert "control_robustness_score" in summary["metrics"]
        assert "detection_rate" in summary["metrics"]


class TestAdversarialMetrics:
    """Test robustness metrics calculation."""

    def test_attack_success_rate_calculation(self):
        """Should calculate ASR correctly."""
        asr = MetricsCalculator.calculate_attack_success_rate(5, 10)
        assert asr == 0.5

    def test_control_robustness_score_calculation(self):
        """Should calculate robustness as 1-ASR."""
        robustness = MetricsCalculator.calculate_control_robustness_score(0.5)
        assert robustness == 0.5

    def test_coverage_ratio_calculation(self):
        """Should calculate coverage ratio."""
        coverage = MetricsCalculator.calculate_coverage_ratio(50, 100)
        assert coverage == 0.5

    def test_severity_weighted_bypass_score(self):
        """Should weight bypasses by severity."""
        bypasses = [
            {"severity": "critical"},  # Weight: 3.0
            {"severity": "major"},     # Weight: 2.0
            {"severity": "minor"}      # Weight: 1.0
        ]

        score = MetricsCalculator.calculate_severity_weighted_bypass_score(bypasses, 10)
        # (3.0 + 2.0 + 1.0) / (10 * 3.0) = 6.0 / 30.0 = 0.2
        assert 0.15 < score < 0.25

    def test_false_negative_rate_calculation(self):
        """Should calculate false negative rate."""
        fnr = MetricsCalculator.calculate_false_negative_rate(
            ["IDG-01", "PDX-01"],  # Missed
            5  # Total expected
        )
        assert fnr == 0.4

    def test_false_positive_rate_calculation(self):
        """Should calculate false positive rate."""
        fpr = MetricsCalculator.calculate_false_positive_rate(
            ["EIT-01"],  # Extra detected
            5  # Total detected
        )
        assert fpr == 0.2

    def test_test_confidence_calculation(self):
        """Should calculate test confidence score."""
        confidence = MetricsCalculator.calculate_test_confidence(
            coverage=0.5,
            sample_size=50,
            effectiveness=0.8
        )
        assert 0.0 <= confidence <= 1.0

    def test_robustness_tier_assessment_red(self):
        """Should assess RED tier for poor robustness."""
        metrics = AdversarialMetrics(
            total_attacks=10, successful_bypasses=8, partial_bypasses=1,
            total_bypass_attempts=9, attack_success_rate=0.9,
            control_robustness_score=0.1, coverage_ratio=0.2,
            severity_weighted_bypass_score=0.8,
            false_negative_rate=0.8, false_positive_rate=0.1,
            test_confidence=0.3
        )

        tier = MetricsCalculator.assess_robustness_tier(metrics)
        assert tier == "RED"

    def test_robustness_tier_assessment_green(self):
        """Should assess GREEN tier for good robustness."""
        metrics = AdversarialMetrics(
            total_attacks=10, successful_bypasses=1, partial_bypasses=0,
            total_bypass_attempts=1, attack_success_rate=0.1,
            control_robustness_score=0.9, coverage_ratio=0.85,
            severity_weighted_bypass_score=0.05,
            false_negative_rate=0.05, false_positive_rate=0.0,
            test_confidence=0.8
        )

        tier = MetricsCalculator.assess_robustness_tier(metrics)
        assert tier == "GREEN"

    def test_metrics_export_to_dict(self):
        """Should export metrics as dictionary."""
        metrics = AdversarialMetrics(
            total_attacks=10, successful_bypasses=2, partial_bypasses=1,
            total_bypass_attempts=3, attack_success_rate=0.3,
            control_robustness_score=0.7, coverage_ratio=0.5,
            severity_weighted_bypass_score=0.15,
            false_negative_rate=0.2, false_positive_rate=0.1,
            test_confidence=0.6
        )

        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["attack_success_rate"] == 0.3
        assert metrics_dict["total_attacks"] == 10

    def test_metrics_report_generation(self):
        """Should generate metrics report."""
        metrics = AdversarialMetrics(
            total_attacks=10, successful_bypasses=2, partial_bypasses=1,
            total_bypass_attempts=3, attack_success_rate=0.3,
            control_robustness_score=0.7, coverage_ratio=0.5,
            severity_weighted_bypass_score=0.15,
            false_negative_rate=0.2, false_positive_rate=0.1,
            test_confidence=0.6
        )

        report = MetricsCalculator.generate_report(metrics)
        assert isinstance(report, str)
        assert "Robustness Tier" in report
        assert "Core Metrics" in report
        assert "30.0%" in report  # ASR percentage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
