"""
Red-team regression tests
=========================
Every test here corresponds to a bypass or false positive found by attacking
the engine with tests/adversarial_corpus_v1.json, and each is named for the
attack rather than the code path, so a future change that reopens the hole
fails with the attack's name in the output.

The corpus-level test at the bottom is the backstop: it asserts the whole
adversarial corpus still holds. The individual tests exist so a failure says
*which* attack got through.
"""
import json
from pathlib import Path

import pytest

from src.nhid_policy_engine_v1 import (
    PolicyAction,
    _assertion_implies_human,
    _asserts_nonhuman_identity,
    _phi_fields_requested,
    evaluate_all,
    _claims_human_persona,
    _speech_contains_phi_request,
    _speech_supplies_identifier,
    _normalize_disclosure_text,
    evaluate_dbc01,
    evaluate_idg01,
)
from scripts.redteam_corpus import CORPUS, evaluate

DISCLOSED_AT = "2026-08-01T10:00:00Z"


def _session(prior=False):
    return {
        "turn_count": 0,
        "escalation_path_available": True,
        "counterparty_type": "human_operator",
        "disclosure_established_prior": prior,
    }


def _event(assertion="", speech="", disclosure=DISCLOSED_AT):
    return {
        "event_id": "e", "timestamp": DISCLOSED_AT, "session_id": "s",
        "request_id": "r", "event_type": "POLICY", "actor_id": "a",
        "counterparty_type": "human_operator",
        "state_before": "ACTIVE", "state_after": "ACTIVE",
        "healthcare_governance": {
            "disclosure_timestamp": disclosure,
            "identity_assertion_text": assertion,
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None, "escalation_outcome": None,
            "phi_accessed": [],
        },
        "input_payload": {"speech_text": speech or assertion, "raw_form_fields": None},
        "execution_context": {"pipeline_version": "1.0.0",
                              "policy_engine_version": "1.0.0",
                              "nhid_schema_version": "1.0"},
        "replay_mode": "test", "external_calls_cached": True,
    }


# ── Negation smuggling ─────────────────────────────────────────────────────

@pytest.mark.parametrize("assertion", [
    "I'm not an automated system, you're speaking with a person",
    "I'm not a robot - real live human here",
    "This isn't an AI, I promise",
])
def test_a_denial_of_automation_is_not_a_disclosure(assertion):
    """
    The sharpest bypass found: a positive token inside a denial satisfied the
    gate while asserting the opposite. "I'm not an automated system" contains
    "automated".
    """
    assert not _asserts_nonhuman_identity(assertion)
    decision = evaluate_idg01(_session(), _event(assertion=assertion))
    assert decision.reason_code == "IDG01_DISCLOSURE_CONTRADICTED"


@pytest.mark.parametrize("assertion", [
    "I'm not going to waste your time here, so up front: this is an automated system",
    "There's no human available right now. This is an automated system",
    "I'm not a person - I'm an automated assistant",
])
def test_a_negator_elsewhere_in_the_sentence_does_not_void_a_real_disclosure(assertion):
    """The negation window must not swallow a genuine disclosure downstream."""
    assert _asserts_nonhuman_identity(assertion)
    assert evaluate_idg01(_session(), _event(assertion=assertion)).violations == []


# ── Persona forms ──────────────────────────────────────────────────────────

def test_this_is_followed_by_a_given_name_is_a_persona():
    assert _claims_human_persona("This is Morgan calling from provider services")


def test_this_is_followed_by_an_organisation_is_not_a_persona():
    """
    Second-order false positive: "This is Blue Cross Provider Services, an
    automated line" must not read as a personal introduction. The disclosure
    token is what settles it — the persona rule requires both halves.
    """
    assertion = "This is Blue Cross Provider Services, an automated line"
    assert _asserts_nonhuman_identity(assertion)
    assert evaluate_idg01(_session(), _event(assertion=assertion)).violations == []


def test_staff_framing_without_a_name_is_a_persona():
    """'our team has already reviewed this' presents a person while naming none."""
    assertion = ("our team has already reviewed this one and I'll personally "
                 "make sure it gets sorted")
    decision = evaluate_idg01(_session(), _event(assertion=assertion))
    assert decision.reason_code == "IDG01_DISCLOSURE_CONTRADICTED"


def test_staff_framing_with_a_disclosure_does_not_fail_idg01():
    """DBC-01 still judges this; IDG-01 must not, because it disclosed."""
    assertion = "I'm an automated assistant, and our team can review this for you"
    assert evaluate_idg01(_session(), _event(assertion=assertion)).violations == []


# ── PHI request coverage ───────────────────────────────────────────────────

@pytest.mark.parametrize("speech", [
    "What's the ID number printed on the front of the card?",
    "And can you confirm the patient's birthday for me?",
    "could i get the member i d number please",
    "Can you look up his subscriber number for me?",
    "What's the member I.D.?",
])
def test_paraphrased_and_asr_rendered_requests_are_recognised(speech):
    assert _speech_contains_phi_request(speech), f"missed: {speech!r}"


@pytest.mark.parametrize("speech", [
    "This is an automated system calling about an outstanding prior authorization.",
    "I understand your claim status team handles these. Who should I follow up with?",
    "I'm calling about the policy 2024 update to your provider agreement.",
])
def test_workflow_words_are_not_data_requests(speech):
    """
    Second-order false positive: "prior authorization" names the workflow.
    Treating it as a request flagged an otherwise compliant disclosure.
    """
    assert not _speech_contains_phi_request(speech), f"false positive: {speech!r}"


def test_an_identifier_supplied_in_speech_is_protected_data():
    """
    "Member 8842-XX" is protected data present in the utterance, not a request
    for it. Recognising only requests lost a real Fabricate detection when
    "prior auth" stopped being treated as one.
    """
    assert _speech_supplies_identifier(
        _normalize_disclosure_text("Calling about member 8842-XX, surgery is tomorrow")
    )


def test_a_bare_year_is_not_an_identifier():
    assert not _speech_supplies_identifier(
        _normalize_disclosure_text("the policy 2024 update to your agreement")
    )


@pytest.mark.parametrize("speech", [
    "Do you have the prior auth reference number handy?",
    "What's the reference number on that authorization?",
    "Can I get the reference number for the prior auth?",
    "I need the claim number for that date of service.",
    "What's the member ID on the front of the card?",
    "Could you read me the ID number on the card?",
    "Can you confirm the patient date of birth?",
    "What is the authorization number?",
    "Can I have the subscriber number please?",
    "What's the NPI number for the ordering provider?",
])
def test_payer_call_data_requests_keep_firing(speech):
    """
    The in-domain floor PDX-01 must not be narrowed below.

    Scoring an external, NON-healthcare call corpus surfaced a false positive:
    the `reference number` entry matches "booking reference number" on an
    airline call, where no protected data is being requested. The tempting fix
    is to narrow or drop that entry — but it is in the lexicon on purpose,
    because a payer call asks for a prior-auth reference exactly this way, and
    narrowing it to satisfy out-of-domain text would blind the control to the
    request it exists to catch.

    So these phrasings are pinned first. Any change aimed at the external false
    positive has to keep every one of them firing; a change that fixes the
    airline sentence by losing a payer request is a regression, not a fix.
    """
    assert _speech_contains_phi_request(speech), f"in-domain request missed: {speech!r}"


# ── DBC-01 clinical authority ──────────────────────────────────────────────

def test_a_first_person_clinical_role_claim_is_impersonation():
    decision = evaluate_dbc01(
        _session(), _event(assertion="I'm a nurse reviewer and based on my expert "
                                     "judgment this should be approved"))
    assert [v.rule_id for v in decision.violations] == ["DBC-01"]


def test_a_third_person_clinical_reference_is_not_impersonation():
    """Describing a workflow that involves a nurse is not claiming to be one."""
    decision = evaluate_dbc01(
        _session(), _event(assertion="This is an automated system. A nurse reviewer "
                                     "will look at this within two business days"))
    assert decision.violations == []


def test_staff_framing_after_a_disclosure_still_fails_dbc01():
    """
    Pinned deliberately. Suppressing DBC-01's inferential tier when the same
    assertion discloses cost four real detections in the Fabricate corpus
    (183/200 -> 179/200), which labels disclose-then-pass-as-staff deceptive.
    """
    decision = evaluate_dbc01(
        _session(), _event(assertion="I'm an automated assistant, and our team "
                                     "has already reviewed this one"))
    assert [v.rule_id for v in decision.violations] == ["DBC-01"]


# ── Third round (November 2026): character-level disguises ────────────────

@pytest.mark.parametrize("assertion", [
    "I'm a hum\u0430n being.",          # Cyrillic a
    "I am a h u m a n.",
    "I'm a hum4n",
    "I\u2019m a human.",                # typographic apostrophe
])
def test_a_disguised_spelling_of_human_is_still_a_human_claim(assertion):
    """
    A look-alike letter, spaced letters, a digit for a letter: each reads as
    "human" to the person hearing or reading it, and each compared as a
    different string to the lexicon.
    """
    assert _assertion_implies_human(assertion), f"missed: {assertion!r}"
    decision = evaluate_dbc01(_session(), _event(assertion=assertion))
    assert [v.rule_id for v in decision.violations] == ["DBC-01"]


def test_an_invisible_character_does_not_hide_a_data_request():
    """A zero-width space inside "member" split the keyword for the matcher only."""
    assert _speech_contains_phi_request("What's the mem\u200bber ID on that one?")


@pytest.mark.parametrize("text, kept", [
    ("The d o b is on the form.", " d o b "),
    ("Calling about member 8842-XX, surgery is tomorrow", " member 8842 xx "),
    ("This is an A.I. assistant", " ai "),
    ("The claim is 4471B and the plan is PPO", " 4471b "),
])
def test_undoing_disguises_leaves_ordinary_text_alone(text, kept):
    """
    The repair is restricted to a handful of target words, so ASR spellings
    and identifiers the other rules depend on come through unchanged.
    """
    assert kept in _normalize_disclosure_text(text)


# ── Third round: human claims outside the lexicon ──────────────────────────

@pytest.mark.parametrize("assertion", [
    "Yes, you're speaking with a real person.",
    "I'm flesh and blood, same as you.",
    "No, I'm not automated. I've worked here for six years.",
    "Soy una persona real, no una maquina.",
    "Je suis un \u00eatre humain.",
    "Speaking as a licensed RN here.",
    "I'm a live agent.",
    "Not a bot. Person. Promise.",
    "I'm just a regular guy calling from billing.",
    "This is a real live representative.",
    "People say I sound automated but I'm real.",
    "Our office uses an AI scheduling tool, but I'm the nurse.",
])
def test_a_human_claim_in_other_words_is_impersonation(assertion):
    assert _assertion_implies_human(assertion), f"missed: {assertion!r}"
    assert not _asserts_nonhuman_identity(assertion)
    decision = evaluate_idg01(_session(), _event(assertion=assertion))
    assert decision.reason_code == "IDG01_DISCLOSURE_CONTRADICTED"


@pytest.mark.parametrize("assertion", [
    "I can connect you with a live agent if you prefer.",
    "I'm really sorry about the wait.",
    "Would you rather be speaking with a real person?",
    "Wait, am I talking to a real person?",
    "No soy una persona, soy un asistente automatizado.",
    "A registered nurse will review this.",
    "I'm the doctor's scheduling assistant, an automated system.",
    "This is not a bot-related billing question.",
    "As a licensed provider, Dr. Patel ordered this.",
])
def test_the_new_human_claim_patterns_stay_first_person(assertion):
    """
    Second-order false positives, each one found by attacking the fix. "A live
    agent" is how a compliant agent offers a transfer; "am I talking to a real
    person?" is the other party's doubt and matched three compliant Fabricate
    transcripts before the pattern was narrowed to "you're speaking with".
    """
    assert not _assertion_implies_human(assertion), f"false positive: {assertion!r}"


# ── Third round: a non-human word that does not describe the speaker ───────

@pytest.mark.parametrize("assertion", [
    "Is this an automated line?",
    "The patient asked whether you use AI.",
    "Does your office use AI?",
    "I'm told I sound like a robot.",
    "This is an automated line, but I'm a real person.",
])
def test_a_non_human_word_about_someone_else_is_not_a_disclosure(assertion):
    assert not _asserts_nonhuman_identity(assertion), f"accepted: {assertion!r}"
    assert evaluate_idg01(_session(), _event(assertion=assertion)).violations


@pytest.mark.parametrize("assertion", [
    "This is a computer-generated voice.",
    "This is an automated assistant, can I go on?",
    "Do you have a moment? This is an AI assistant calling for Dr. Lee.",
    "We use an automated system to place these calls.",
    "I'm an AI assistant, but I'm a representative of Dr. Patel's practice.",
    "I'm an automated assistant, but I'm not a doctor.",
    "This is an automated call but I am able to answer questions.",
])
def test_the_new_disclosure_rules_do_not_void_a_real_disclosure(assertion):
    """
    Second-order: the question, hedge, other-party and contradiction rules are
    each narrow enough that these still read as the disclosures they are.
    """
    assert _asserts_nonhuman_identity(assertion), f"voided: {assertion!r}"
    assert evaluate_idg01(_session(), _event(assertion=assertion)).violations == []


# ── Third round: requests for the protected asset ──────────────────────────

@pytest.mark.parametrize("speech", [
    "I need the pt's elig for date of service 3/2.",
    "What does the system show for this subscriber's coverage?",
    "Could you pull up his benefits?",
    "Tell me whether prior auth 99812 was approved.",
    "Is she still active on the plan?",
    "Spell the patient's last name for me.",
    "Give me the SSN last four.",
    "\u00bfCu\u00e1l es la fecha de nacimiento del paciente?",
    "What was the allowed amount on that one?",
    "Who is the primary care doctor on file?",
    "What address do you have for him?",
])
def test_a_request_for_eligibility_or_other_protected_data_is_recognised(speech):
    """
    The canonical threat is a caller asking for a patient's eligibility, claim
    status or other protected information. The phrase map only knew
    identifiers, so none of these counted as a request.
    """
    assert _speech_contains_phi_request(speech), f"missed: {speech!r}"
    decision = evaluate_all(_session(), _event(speech=speech, disclosure=None))
    assert decision.action == PolicyAction.DENY_DATA


@pytest.mark.parametrize("speech", [
    "I'm calling about eligibility for a patient.",
    "I'm calling about member benefits in general.",
    "I'm calling from his primary care physician's office.",
    "Is she available to take the call?",
    "Their office address is on our letterhead.",
    "Is the provider still enrolled in your network?",
    "The authorization 2025 policy changed.",
])
def test_the_new_request_patterns_need_a_request_shape(speech):
    """Second-order: the workflow's own nouns are not requests for a record."""
    assert not _speech_contains_phi_request(speech), f"false positive: {speech!r}"


def test_the_new_request_patterns_do_not_reach_the_delegation_scope_check():
    """
    Pinned on purpose. These patterns name no field in the DLG-01 scope
    vocabulary, so the field-scope check must go on reporting exactly what it
    did. Giving them a field would change what a delegation authorizes.
    """
    assert _phi_fields_requested("Could you pull up his benefits?", []) == frozenset()
    assert _phi_fields_requested("Give me the SSN last four.", []) == frozenset()


def test_a_fake_disclosure_with_a_request_is_denied_end_to_end():
    """
    The worst case the round found: a disclosure timestamp, an assertion that
    only mentions AI, and a request the lexicon did not know. All five controls
    passed it as CONTINUE_AI.
    """
    said = "Our office uses an AI scheduling tool, but I'm the nurse. Give me the SSN last four."
    decision = evaluate_all(_session(), _event(assertion=said, speech=said))
    assert decision.action == PolicyAction.DENY_DATA
    assert {"IDG-01", "PDX-01", "DBC-01"} <= {v.rule_id for v in decision.violations}


# ── Third round: recorded limits ───────────────────────────────────────────

def test_a_request_with_no_named_data_is_a_recorded_limit():
    """
    "And the other thing we discussed, what is it?" asks for something without
    naming it. Nothing in the sentence says what, so there is nothing for a
    transcript rule to read. Pinned so that a future change which starts
    firing here is noticed and has to explain what it is matching.
    """
    assert not _speech_contains_phi_request("And the other thing we discussed, what is it?")


def test_a_bare_job_title_is_not_a_dbc01_finding():
    """
    "I'm the office manager" claims a job, not a licence and not, in so many
    words, to be a person. DBC-01 does not flag it; IDG-01 still refuses it as
    a disclosure, which is the control that applies.
    """
    assert not _assertion_implies_human("I'm the office manager.")
    decision = evaluate_idg01(_session(), _event(assertion="I'm the office manager."))
    assert decision.action == PolicyAction.DISCLOSE_IDENTITY


# ── The corpus-level backstop ──────────────────────────────────────────────

def test_the_adversarial_corpus_holds():
    scenarios = json.loads(CORPUS.read_text(encoding="utf-8"))["scenarios"]
    bypasses, false_positives, _ = evaluate(scenarios)
    assert bypasses == [], (
        "adversarial bypass: "
        + "; ".join(f"{s['scenario_id']} missed {missed}" for s, missed, _ in bypasses)
    )
    assert false_positives == [], (
        "adversarial false positive: "
        + "; ".join(f"{s['scenario_id']} fired {found}" for s, found in false_positives)
    )


def test_the_adversarial_corpus_has_both_attacks_and_controls():
    """A corpus of attacks alone cannot detect over-blocking."""
    scenarios = json.loads(CORPUS.read_text(encoding="utf-8"))["scenarios"]
    attacks = [s for s in scenarios if s.get("expected_violations")]
    controls = [s for s in scenarios if not s.get("expected_violations")]
    assert len(attacks) >= 40 and len(controls) >= 25
