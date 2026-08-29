"""
Governance Evaluation Corpus — metric regression tests
======================================================
Two things went wrong with this corpus's published numbers, and these tests
exist so neither can recur silently.

1. A "0% false-positive rate" was published against it for a month. Nothing
   computed that number, and when measured it was never true: `build_session`
   and `build_event` render each turn independently, so every turn after the
   disclosing one looked undisclosed and all five compliant scenarios emitted
   IDG-01/PDX-01. That is a harness wiring gap, not engine behaviour — the same
   defect already fixed for the Tonic corpus.

2. A per-rule detection figure went stale when a scenario was added, because
   nothing tied the published number to the measured one.

The load-bearing invariant is the first test: making disclosure sticky must fix
the false positives *without moving detection*. If carrying disclosure forward
ever changes a detection rate, it is masking a real violation and must not ship.
"""
import json
from pathlib import Path

import pytest

from src.nhid_policy_engine_v1 import evaluate_all
from src.synthetic_eval_loop import (
    build_event,
    build_session,
    carry_disclosure_forward,
    extract_rule_ids,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPO_ROOT / "tests" / "evaluation_corpus_v1.json"
GROUPS = ["compliant_scenarios", "single_rule_violations", "multi_rule_combinations"]


@pytest.fixture(scope="module")
def corpus():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenarios(corpus):
    return [s for g in GROUPS for s in corpus[g]]


def _detected(scenario_id, turns):
    ids = set()
    for i, turn in enumerate(turns):
        decision = evaluate_all(build_session(turn), build_event(scenario_id, i, turn))
        ids.update(extract_rule_ids(decision.violations))
    return ids


# ── The load-bearing invariant ─────────────────────────────────────────────

def test_carrying_disclosure_forward_never_loses_a_detection(scenarios):
    """
    Carrying disclosure forward may remove false positives and may enable the
    sequencing checks that need to know which turn disclosed. What it must
    never do is *lose* an expected detection — that would mean the fix is
    hiding a real violation, and the corpus figures would improve for the wrong
    reason.

    Stated as a subset rather than equality because the sequencing signal
    legitimately gains detections: PDX-01 on nhid_ec_pdx01_002 and
    nhid_ec_combo_006 (protected-data request bundled into the disclosing
    utterance) and IDG-01 on nhid_ec_combo_002 (a disclosure that introduces a
    human persona). Those are asserted by name below so the gain cannot quietly
    become a loss somewhere else.
    """
    for s in scenarios:
        expected = set(s.get("expected_violations") or [])
        if not expected:
            continue
        sid = s["scenario_id"]
        before = _detected(sid, s["turns"]) & expected
        after = _detected(sid, carry_disclosure_forward(s["turns"])) & expected
        assert before <= after, (
            f"{sid}: carrying disclosure forward LOST detections "
            f"{sorted(before - after)} — the fix is masking a real violation"
        )


def test_the_sequencing_signal_gains_exactly_the_expected_detections(scenarios):
    gained = {}
    for s in scenarios:
        expected = set(s.get("expected_violations") or [])
        if not expected:
            continue
        sid = s["scenario_id"]
        before = _detected(sid, s["turns"]) & expected
        after = _detected(sid, carry_disclosure_forward(s["turns"])) & expected
        if after - before:
            gained[sid] = sorted(after - before)
    assert gained == {
        "nhid_ec_combo_002": ["IDG-01"],
        "nhid_ec_combo_006": ["PDX-01"],
        "nhid_ec_pdx01_002": ["PDX-01"],
    }, f"unexpected change in what the sequencing signal detects: {gained}"


# ── False positives on compliant scenarios ─────────────────────────────────

def test_every_compliant_scenario_is_clean(corpus):
    """
    Compliant scenarios declare no expected violations, so anything they emit
    is a false positive. The corpus false-positive rate is 0%, and this is what
    holds it there.

    `nhid_ec_comp_005` was the last exception: its final turn sets
    `escalation_path_available: false` on the turn where the escalation was
    honored, and EIT-01 keyword-matched the agent's own line ("connecting you
    to a supervisor") as a request, reaching EIT01_NO_ESCALATION_PATH without
    consulting the `escalation_outcome: honored` beside it. EIT-01 now settles
    recorded fulfilment before consulting availability, so it is clean.
    """
    for s in corpus["compliant_scenarios"]:
        sid = s["scenario_id"]
        assert not s.get("expected_violations"), f"{sid} is not a compliant scenario"
        fired = sorted(_detected(sid, carry_disclosure_forward(s["turns"])))
        assert fired == [], f"{sid} emitted {fired} — that is a false positive"


def test_without_the_fix_every_compliant_scenario_would_report_a_violation(corpus):
    """Pins the defect itself, so a revert cannot pass unnoticed."""
    dirty = [
        s["scenario_id"] for s in corpus["compliant_scenarios"]
        if _detected(s["scenario_id"], s["turns"])
    ]
    assert len(dirty) == len(corpus["compliant_scenarios"])


# ── carry_disclosure_forward semantics ─────────────────────────────────────

def test_disclosure_is_carried_to_later_turns():
    turns = [
        {"speech_text": "I am an automated system.",
         "disclosure_timestamp": "2026-07-30T10:00:00Z",
         "identity_assertion_text": "I am an automated system"},
        {"speech_text": "What is your member ID?"},
    ]
    carried = carry_disclosure_forward(turns)
    assert carried[1]["disclosure_timestamp"] == "2026-07-30T10:00:00Z"
    assert carried[1]["identity_assertion_text"] == "I am an automated system"


def test_a_conversation_that_never_discloses_gains_no_disclosure():
    turns = [{"speech_text": "What is your member ID?"}, {"speech_text": "And your date of birth?"}]
    carried = carry_disclosure_forward(turns)
    for original, result in zip(turns, carried):
        assert result.get("disclosure_timestamp") is None
        assert result.get("identity_assertion_text") is None
        assert result["speech_text"] == original["speech_text"]
        # No turn can claim disclosure was established when none ever happened.
        assert result["disclosure_established_prior"] is False


def test_turns_before_the_disclosure_are_untouched():
    """A late disclosure must not retroactively clear the turns that preceded it."""
    turns = [
        {"speech_text": "What is your member ID?"},
        {"speech_text": "I am an automated system.",
         "disclosure_timestamp": "2026-07-30T10:00:05Z",
         "identity_assertion_text": "I am an automated system"},
    ]
    carried = carry_disclosure_forward(turns)
    assert carried[0].get("disclosure_timestamp") is None


def test_a_turn_keeps_its_own_assertion_text():
    """Otherwise the weak-disclosure scenarios would be evaluated against
    an earlier turn's stronger wording."""
    turns = [
        {"speech_text": "I am an automated system.",
         "disclosure_timestamp": "2026-07-30T10:00:00Z",
         "identity_assertion_text": "I am an automated system"},
        {"speech_text": "This is the claims system.",
         "identity_assertion_text": "claims system"},
    ]
    assert carry_disclosure_forward(turns)[1]["identity_assertion_text"] == "claims system"


def test_the_input_turns_are_not_mutated():
    turns = [
        {"disclosure_timestamp": "2026-07-30T10:00:00Z", "identity_assertion_text": "AI"},
        {"speech_text": "next"},
    ]
    carry_disclosure_forward(turns)
    assert "disclosure_timestamp" not in turns[1]


def test_empty_conversation_is_handled():
    assert carry_disclosure_forward([]) == []


# ── The generated report cannot go stale ───────────────────────────────────

def test_report_is_committed_and_current():
    """
    The previous report was hand-written prose. When a scenario was added its
    per-rule IDG-01 line went stale, and the file was later deleted — taking the
    only correct copy of the number with it. This one is generated, and this
    test is the guard that catches an edited corpus with a forgotten regenerate.
    """
    from scripts.eval_corpus import REPORT, main as eval_main

    assert REPORT.exists(), "the corpus report must be committed, not generated on demand"
    assert eval_main(["--check"]) == 0, (
        "docs/EVALUATION_CORPUS_REPORT_v1.md is stale — run "
        "`python scripts/eval_corpus.py --write-report` and commit it"
    )


def test_report_carries_the_research_boundary():
    from scripts.eval_corpus import REPORT

    text = REPORT.read_text(encoding="utf-8")
    assert "not a conformance claim" in text
    for forbidden in ("certified", "assured", "independently validated"):
        assert forbidden not in text.lower(), f"report claims {forbidden!r}"
