"""Tests for adversarial corpus stress testing."""

import pytest
from src.safety_evaluation.adversarial_corpus import (
    AdversarialCase,
    AdversarialTactic,
    AdversarialCaseBuilder,
    TIER_0_ADVERSARIAL_CASES,
    get_adversarial_cases_by_tactic,
    get_adversarial_cases_by_rule,
)


class TestAdversarialCaseBasics:
    """Test AdversarialCase dataclass."""

    def test_adversarial_case_creation(self):
        """Test AdversarialCase instantiation."""
        case = AdversarialCase(
            case_id="test-001",
            tactic=AdversarialTactic.DECEPTION,
            target_rules=["DBC-01"],
            description="Human mimicry attack",
            scenario="Bot claims to be human operator",
            payload={"speaker": "agent", "identity": "human"},
            expected_violations=["DBC-01"],
            expected_action="ESCALATE_HUMAN",
            difficulty_level="intermediate",
            severity="critical",
        )
        assert case.case_id == "test-001"
        assert case.tactic == AdversarialTactic.DECEPTION
        assert "DBC-01" in case.target_rules


class TestAdversarialCaseBuilder:
    """Test AdversarialCaseBuilder convenience methods."""

    def test_timing_boundary_case_builder(self):
        """Test building a timing boundary attack."""
        case = AdversarialCaseBuilder.timing_boundary_case(
            rule_id="PDX-01",
            millisecond_offset=0,
            description="Exact boundary test",
        )
        assert case.tactic == AdversarialTactic.TIMING_BOUNDARY
        assert case.target_rules == ["PDX-01"]
        assert case.payload["offset_ms"] == 0

    def test_deception_case_builder(self):
        """Test building a deception attack."""
        case = AdversarialCaseBuilder.deception_case(
            deception_type="human_mimicry",
            description="Claims to be human",
            identity_text="I'm a person calling from the office",
        )
        assert case.tactic == AdversarialTactic.DECEPTION
        assert case.target_rules == ["DBC-01"]
        assert "person" in case.payload["identity_assertion_text"]

    def test_unicode_obfuscation_builder(self):
        """Test building a Unicode obfuscation attack."""
        case = AdversarialCaseBuilder.unicode_obfuscation_case(
            obfuscation_type="cyrillic_homoglyph",
            crafted_text="I аm а human",
            description="Cyrillic character substitution",
        )
        assert case.tactic == AdversarialTactic.UNICODE_OBFUSCATION
        assert "DBC-01" in case.target_rules
        assert "IDG-01" in case.target_rules

    def test_regex_bypass_builder(self):
        """Test building a regex bypass attack."""
        case = AdversarialCaseBuilder.regex_bypass_case(
            pattern_name="automated_disclosure",
            bypass_input="I'm an auto mat ED assistant",
            description="Whitespace bypass",
        )
        assert case.tactic == AdversarialTactic.REGEX_BYPASS
        assert "automated" not in case.payload["speech_text"].replace(" ", "")

    def test_rule_combination_builder(self):
        """Test building a multi-rule violation."""
        case = AdversarialCaseBuilder.rule_combination_case(
            rules=["IDG-01", "PDX-01"],
            description="Combined violations",
            scenario_payload={"violations": 2},
        )
        assert case.tactic == AdversarialTactic.RULE_COMBINATION
        assert case.target_rules == ["IDG-01", "PDX-01"]

    def test_chaos_case_builder(self):
        """Test building a chaos/stress test."""
        case = AdversarialCaseBuilder.chaos_case(
            chaos_type="language_switching",
            description="Multi-language call",
            payload={"languages": ["en", "es", "en"]},
        )
        assert case.tactic == AdversarialTactic.CHAOS
        assert "IDG-01" in case.target_rules


class TestTier0AdversarialBaseline:
    """Test Tier 0 adversarial corpus baseline."""

    def test_baseline_has_cases(self):
        """Tier 0 should have adversarial test cases."""
        assert len(TIER_0_ADVERSARIAL_CASES) >= 15

    def test_baseline_covers_tactics(self):
        """Baseline should cover multiple attack tactics."""
        tactics = {case.tactic for case in TIER_0_ADVERSARIAL_CASES}
        assert len(tactics) >= 3  # At least 3 different tactics

    def test_baseline_covers_rules(self):
        """Baseline should target multiple compliance rules."""
        all_rules = set()
        for case in TIER_0_ADVERSARIAL_CASES:
            all_rules.update(case.target_rules)
        assert len(all_rules) >= 3  # At least 3 rules targeted

    def test_all_cases_have_payloads(self):
        """All adversarial cases should have payload."""
        for case in TIER_0_ADVERSARIAL_CASES:
            assert case.payload is not None
            assert isinstance(case.payload, dict)

    def test_all_cases_have_expected_violations(self):
        """All adversarial cases should have expected_violations list (may be empty for chaos tests)."""
        for case in TIER_0_ADVERSARIAL_CASES:
            assert isinstance(case.expected_violations, list)
            assert all(isinstance(v, str) for v in case.expected_violations)

    def test_all_cases_have_difficulty_levels(self):
        """All adversarial cases should have difficulty level."""
        for case in TIER_0_ADVERSARIAL_CASES:
            assert case.difficulty_level in ["basic", "intermediate", "advanced"]

    def test_all_cases_have_severity(self):
        """All adversarial cases should have severity."""
        for case in TIER_0_ADVERSARIAL_CASES:
            assert case.severity in ["critical", "major", "minor"]


class TestAdversarialQueryFunctions:
    """Test adversarial case lookup functions."""

    def test_get_cases_by_tactic(self):
        """Test filtering cases by tactic."""
        deception_cases = get_adversarial_cases_by_tactic(AdversarialTactic.DECEPTION)
        assert len(deception_cases) > 0
        assert all(c.tactic == AdversarialTactic.DECEPTION for c in deception_cases)

    def test_get_cases_by_rule(self):
        """Test filtering cases by target rule."""
        dbc01_cases = get_adversarial_cases_by_rule("DBC-01")
        assert len(dbc01_cases) > 0
        assert all("DBC-01" in c.target_rules for c in dbc01_cases)

    def test_get_cases_by_rule_idg01(self):
        """Test getting IDG-01 targeted cases."""
        idg01_cases = get_adversarial_cases_by_rule("IDG-01")
        assert len(idg01_cases) > 0
        assert all("IDG-01" in c.target_rules for c in idg01_cases)

    def test_get_cases_by_rule_pdx01(self):
        """Test getting PDX-01 targeted cases."""
        pdx01_cases = get_adversarial_cases_by_rule("PDX-01")
        assert len(pdx01_cases) > 0
        assert all("PDX-01" in c.target_rules for c in pdx01_cases)


class TestAdversarialTactics:
    """Test specific adversarial tactics."""

    def test_timing_boundary_cases_exist(self):
        """Should have timing boundary attack cases."""
        timing_cases = get_adversarial_cases_by_tactic(AdversarialTactic.TIMING_BOUNDARY)
        assert len(timing_cases) > 0

    def test_deception_cases_exist(self):
        """Should have deception attack cases."""
        deception_cases = get_adversarial_cases_by_tactic(AdversarialTactic.DECEPTION)
        assert len(deception_cases) > 0

    def test_unicode_obfuscation_cases_exist(self):
        """Should have Unicode obfuscation cases."""
        unicode_cases = get_adversarial_cases_by_tactic(
            AdversarialTactic.UNICODE_OBFUSCATION
        )
        assert len(unicode_cases) > 0

    def test_regex_bypass_cases_exist(self):
        """Should have regex bypass cases."""
        regex_cases = get_adversarial_cases_by_tactic(AdversarialTactic.REGEX_BYPASS)
        assert len(regex_cases) > 0

    def test_rule_combination_cases_exist(self):
        """Should have multi-rule violation cases."""
        combo_cases = get_adversarial_cases_by_tactic(
            AdversarialTactic.RULE_COMBINATION
        )
        assert len(combo_cases) > 0
