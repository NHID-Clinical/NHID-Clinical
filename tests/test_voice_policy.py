"""
Conformance tests for the deterministic voice policy engine (voice_policy.py).

These are pure unit tests — no I/O, no database, no network, no server. They
exercise the reference policy engine directly and define the expected NHID
voice conformance behaviour:

  - REQUIRE_UPFRONT_DISCLOSURE : AI identity must be disclosed on the first turn
  - HUMAN_ESCALATION_REQUESTED : escalate to a human on trigger phrases
  - Rule-based (ruleset) evaluation with custom phrase lists, priorities, and
    enable/disable flags
  - Backward-compatible legacy (non-ruleset) behaviour
"""

import pytest

from src.voice_policy import (
    check_disclosure,
    check_escalation,
    run_voice_policy,
    POLICY_VERSION,
    _ESCALATION_PHRASES,
)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: check_disclosure
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckDisclosure:
    def test_needs_disclosure_when_state_empty(self):
        assert check_disclosure({}) is True

    def test_needs_disclosure_when_explicitly_false(self):
        assert check_disclosure({"disclosure_confirmed": False}) is True

    def test_no_disclosure_when_confirmed(self):
        assert check_disclosure({"disclosure_confirmed": True}) is False


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: check_escalation
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckEscalation:
    @pytest.mark.parametrize("phrase", _ESCALATION_PHRASES)
    def test_detects_each_trigger_phrase_verbatim(self, phrase):
        assert check_escalation(phrase) is True

    def test_case_insensitive_all_caps(self):
        assert check_escalation("SPEAK TO A HUMAN") is True

    def test_case_insensitive_mixed(self):
        assert check_escalation("Real Person please") is True

    def test_phrase_embedded_in_sentence(self):
        assert check_escalation("I really want to speak to a human right now") is True

    def test_talk_to_someone_mid_sentence(self):
        assert check_escalation("Can I talk to someone else instead?") is True

    def test_no_false_positive_empty_string(self):
        assert check_escalation("") is False

    def test_no_false_positive_generic_query(self):
        assert check_escalation("What is the weather today?") is False

    def test_no_false_positive_clinical_content(self):
        assert check_escalation("I have a question about my medication dosage") is False

    def test_no_false_positive_affirmative(self):
        assert check_escalation("Yes, that sounds correct") is False

    def test_no_false_positive_scheduling_request(self):
        assert check_escalation("Can you help me with scheduling?") is False


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: run_voice_policy (legacy path)
# ─────────────────────────────────────────────────────────────────────────────

class TestRunVoicePolicy:
    def test_disclose_on_first_turn(self):
        result = run_voice_policy("Hello", {"disclosure_confirmed": False})
        assert result["action"] == "disclose"
        assert result["reason_code"] == "REQUIRE_UPFRONT_DISCLOSURE"
        assert result["policy_version"] == POLICY_VERSION

    def test_disclose_on_empty_state(self):
        assert run_voice_policy("Some text", {})["action"] == "disclose"

    def test_allow_after_disclosure_confirmed(self):
        result = run_voice_policy("How can I help you?", {"disclosure_confirmed": True})
        assert result["action"] == "allow"
        assert result["reason_code"] is None
        assert result["policy_version"] == POLICY_VERSION

    def test_escalate_on_trigger_phrase_after_disclosure(self):
        result = run_voice_policy("I want to speak to a human", {"disclosure_confirmed": True})
        assert result["action"] == "escalate"
        assert result["reason_code"] == "HUMAN_ESCALATION_REQUESTED"
        assert result["policy_version"] == POLICY_VERSION

    def test_disclosure_takes_priority_over_escalation(self):
        """Escalation phrase on first turn must still return disclose, not escalate."""
        result = run_voice_policy("speak to a human", {"disclosure_confirmed": False})
        assert result["action"] == "disclose"
        assert result["reason_code"] == "REQUIRE_UPFRONT_DISCLOSURE"

    @pytest.mark.parametrize("phrase", _ESCALATION_PHRASES)
    def test_all_escalation_phrases_trigger_escalate(self, phrase):
        result = run_voice_policy(phrase, {"disclosure_confirmed": True})
        assert result["action"] == "escalate"

    def test_allow_returns_none_reason_code(self):
        result = run_voice_policy("I have a routine question", {"disclosure_confirmed": True})
        assert result["reason_code"] is None

    def test_state_dict_is_not_mutated(self):
        """run_voice_policy must never modify the session state dict passed to it."""
        state = {"disclosure_confirmed": True, "escalated": False}
        snapshot = dict(state)
        run_voice_policy("some text", state)
        assert state == snapshot


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: rule-based (ruleset) evaluation path
# ─────────────────────────────────────────────────────────────────────────────

class TestRulesetPolicyEngine:
    """
    Unit tests for the rule-based evaluation path in run_voice_policy.

    These tests exercise the `ruleset=` parameter path and verify:
      - Custom phrase lists are authoritative — no fallback to hardcoded defaults
      - An empty phrase list means "match nothing" in ruleset mode
      - Hardcoded defaults are only used in the legacy (no-ruleset) path
      - Disabled rules are skipped regardless of phrase content
      - Policy version from the ruleset is embedded in the decision
    """

    _CONFIRMED = {"disclosure_confirmed": True}
    _UNCONFIRMED = {"disclosure_confirmed": False}

    def _make_ruleset(
        self,
        phrases=None,
        disclosure_enabled=True,
        escalation_enabled=True,
    ):
        return [
            {
                "rule_key": "REQUIRE_UPFRONT_DISCLOSURE",
                "rule_type": "builtin",
                "enabled": disclosure_enabled,
                "priority": 0,
                "params": {},
            },
            {
                "rule_key": "HUMAN_ESCALATION_REQUESTED",
                "rule_type": "phrase_match",
                "enabled": escalation_enabled,
                "priority": 1,
                "params": {"phrases": phrases if phrases is not None else []},
            },
        ]

    # ── Custom phrase list tests ──────────────────────────────────────────────

    def test_custom_phrase_triggers_escalate(self):
        """A phrase from the org's custom list must trigger escalation."""
        ruleset = self._make_ruleset(phrases=["supervisor", "billing dispute"])
        result = run_voice_policy(
            "I need to speak to a supervisor",
            self._CONFIRMED,
            ruleset=ruleset,
            policy_version="VOICE-POLICY-v99",
        )
        assert result["action"] == "escalate"
        assert result["reason_code"] == "HUMAN_ESCALATION_REQUESTED"

    def test_custom_policy_version_embedded_in_decision(self):
        """The policy_version in the decision must reflect the supplied version string."""
        ruleset = self._make_ruleset(phrases=["supervisor"])
        result = run_voice_policy(
            "supervisor please",
            self._CONFIRMED,
            ruleset=ruleset,
            policy_version="VOICE-POLICY-v1780043501",
        )
        assert result["policy_version"] == "VOICE-POLICY-v1780043501"

    def test_hardcoded_phrase_not_in_custom_list_does_not_escalate(self):
        """
        A phrase from the hardcoded _ESCALATION_PHRASES that is NOT in the
        custom list must NOT trigger escalation in ruleset mode.
        This is the core authoritativeness test.
        """
        ruleset = self._make_ruleset(phrases=["supervisor", "billing dispute"])
        result = run_voice_policy(
            "I want to speak to a human",
            self._CONFIRMED,
            ruleset=ruleset,
        )
        assert result["action"] == "allow", (
            "Hardcoded phrases must not fire in ruleset mode; "
            "only the configured custom phrases should be used."
        )

    @pytest.mark.parametrize("hardcoded_phrase", _ESCALATION_PHRASES)
    def test_none_of_the_hardcoded_phrases_fire_with_custom_empty_ruleset_phrases(
        self, hardcoded_phrase
    ):
        """
        In ruleset mode with a custom list that doesn't include a legacy phrase,
        none of the legacy hardcoded phrases should escalate.
        """
        ruleset = self._make_ruleset(phrases=["unique-org-phrase-xyz"])
        result = run_voice_policy(hardcoded_phrase, self._CONFIRMED, ruleset=ruleset)
        assert result["action"] == "allow", (
            f"Hardcoded phrase '{hardcoded_phrase}' must not fire "
            f"when the custom list excludes it."
        )

    # ── Empty phrase list tests ───────────────────────────────────────────────

    def test_empty_phrase_list_allows_all_transcripts(self):
        """
        Empty phrases in ruleset mode = no triggers configured → all transcripts
        pass (action=allow). Must NOT fall back to hardcoded defaults.
        """
        ruleset = self._make_ruleset(phrases=[])
        result = run_voice_policy(
            "speak to a human",  # in hardcoded defaults
            self._CONFIRMED,
            ruleset=ruleset,
        )
        assert result["action"] == "allow", (
            "Empty phrase list must mean 'no triggers' not 'use hardcoded defaults'."
        )

    def test_empty_phrase_list_does_not_escalate_any_legacy_phrase(self):
        """Parametric check: every hardcoded phrase passes through on empty custom list."""
        ruleset = self._make_ruleset(phrases=[])
        for phrase in _ESCALATION_PHRASES:
            result = run_voice_policy(phrase, self._CONFIRMED, ruleset=ruleset)
            assert result["action"] == "allow", (
                f"'{phrase}' must not escalate when phrase list is empty."
            )

    # ── Disabled rule tests ───────────────────────────────────────────────────

    def test_disabled_escalation_rule_allows_trigger_phrase(self):
        """A disabled phrase_match rule must be skipped — trigger phrase passes through."""
        ruleset = self._make_ruleset(
            phrases=["supervisor"],
            escalation_enabled=False,
        )
        result = run_voice_policy("supervisor please", self._CONFIRMED, ruleset=ruleset)
        assert result["action"] == "allow"

    def test_disabled_disclosure_rule_skips_first_turn_requirement(self):
        """A disabled REQUIRE_UPFRONT_DISCLOSURE rule must not enforce disclosure."""
        ruleset = self._make_ruleset(
            phrases=["supervisor"],
            disclosure_enabled=False,
        )
        result = run_voice_policy("hello", self._UNCONFIRMED, ruleset=ruleset)
        assert result["action"] == "allow"

    def test_both_rules_disabled_always_allows(self):
        """With all rules disabled every transcript must be allowed."""
        ruleset = self._make_ruleset(
            phrases=["supervisor"],
            disclosure_enabled=False,
            escalation_enabled=False,
        )
        for text in ["", "speak to a human", "supervisor", "Hello how are you?"]:
            result = run_voice_policy(text, self._UNCONFIRMED, ruleset=ruleset)
            assert result["action"] == "allow", (
                f"All-disabled ruleset must allow '{text}'."
            )

    # ── Legacy path isolation ─────────────────────────────────────────────────

    def test_legacy_path_still_uses_hardcoded_defaults(self):
        """
        When called WITHOUT a ruleset (legacy path), hardcoded phrases must still
        trigger escalation — backward compat for callers that haven't migrated.
        """
        for phrase in _ESCALATION_PHRASES:
            result = run_voice_policy(phrase, self._CONFIRMED)  # no ruleset= arg
            assert result["action"] == "escalate", (
                f"Legacy path must still escalate on '{phrase}'."
            )

    def test_ruleset_none_and_ruleset_keyword_behave_identically(self):
        """Passing ruleset=None explicitly must fall through to the legacy path."""
        phrase = "speak to a human"
        legacy_result = run_voice_policy(phrase, self._CONFIRMED)
        explicit_none_result = run_voice_policy(phrase, self._CONFIRMED, ruleset=None)
        assert legacy_result["action"] == explicit_none_result["action"] == "escalate"
