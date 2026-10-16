"""
Governance Evaluation Corpus v2 — validation failure-mode set
=============================================================
v2 is an additive, non-destructive companion to the frozen v1 baseline. It
holds the failure modes a validation reviewer asks about and that v1 does not
isolate: cross-turn disclosure contradiction, PHI-before-disclosure, honoured
vs denied escalation, incomplete audit, and deceptive human persona.

Its ground truth is spec-faithful — a control is expected wherever its intent
applies — so the measured detection shows exactly where the engine succeeds and
where it has gaps. No expected outcome was weakened to raise a rate, which means
some scenarios are *expected misses*. Those misses are the point: they localise
the engine's cross-turn blindness and the open DBC-01 scope question (see
docs/validation/EVALUATION_CORPUS_V2_FINDINGS.md).

These tests do three things:
  1. keep the generated v2 report from going stale (the same guard v1 has);
  2. confirm v1 is untouched by v2's existence;
  3. pin the measured per-rule outcome — hits AND documented misses — so neither
     a regression nor an undocumented improvement can land silently. If the
     engine later detects a case this corpus currently misses, that is good
     news, but it must arrive together with a report regenerate and an update
     to these expectations and the findings doc — not quietly.
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
CORPUS = REPO_ROOT / "tests" / "evaluation_corpus_v2.json"
REPORT = REPO_ROOT / "docs" / "EVALUATION_CORPUS_REPORT_v2.md"
GROUPS = ["compliant_scenarios", "single_rule_violations", "multi_rule_combinations"]


@pytest.fixture(scope="module")
def corpus():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenarios(corpus):
    return [s for g in GROUPS for s in corpus[g]]


def _detected(scenario_id, turns):
    ids = set()
    for i, turn in enumerate(carry_disclosure_forward(turns)):
        decision = evaluate_all(build_session(turn), build_event(scenario_id, i, turn))
        ids.update(extract_rule_ids(decision.violations))
    return ids


# ── The generated v2 report cannot go stale ────────────────────────────────

def _check_args():
    return [str(CORPUS), "--report", str(REPORT), "--check"]


def test_v2_report_is_committed_and_current():
    from scripts.eval_corpus import main as eval_main

    assert REPORT.exists(), "the v2 corpus report must be committed, not generated on demand"
    assert eval_main(_check_args()) == 0, (
        "docs/EVALUATION_CORPUS_REPORT_v2.md is stale — run "
        "`python scripts/eval_corpus.py tests/evaluation_corpus_v2.json "
        "--report docs/EVALUATION_CORPUS_REPORT_v2.md --write-report` and commit it"
    )


def test_v2_report_carries_the_research_boundary():
    text = REPORT.read_text(encoding="utf-8")
    assert "not a conformance claim" in text
    for forbidden in ("certified", "assured", "independently validated"):
        assert forbidden not in text.lower(), f"report claims {forbidden!r}"


def test_v1_report_is_untouched_by_v2():
    """v2 is additive. The v1 report and corpus must stay byte-for-byte as
    frozen; the default-corpus path of eval_corpus must still reproduce v1."""
    from scripts.eval_corpus import main as eval_main, DEFAULT_CORPUS, REPORT as V1_REPORT

    assert DEFAULT_CORPUS.name == "evaluation_corpus_v1.json"
    assert V1_REPORT.name == "EVALUATION_CORPUS_REPORT_v1.md"
    assert V1_REPORT != REPORT
    assert eval_main(["--check"]) == 0, "v1 report drifted — v2 work must not touch it"


# ── Compliant scenarios stay clean ─────────────────────────────────────────

def test_v2_compliant_scenarios_are_clean(corpus):
    for s in corpus["compliant_scenarios"]:
        sid = s["scenario_id"]
        assert not s.get("expected_violations"), f"{sid} is not a compliant scenario"
        fired = sorted(_detected(sid, s["turns"]))
        assert fired == [], f"{sid} emitted {fired} — that is a false positive"


# ── The measured per-rule outcome, pinned ──────────────────────────────────
#
# Spec-faithful ground truth vs what the engine, as published, actually detects.
# HIT = detected; MISS = expected by spec, not detected. The misses are
# documented in docs/validation/EVALUATION_CORPUS_V2_FINDINGS.md and must change
# only alongside a report regenerate and a findings update.

def _scenario(scenarios, sid):
    for s in scenarios:
        if s["scenario_id"] == sid:
            return s
    raise AssertionError(f"scenario {sid} not in corpus")


def test_phi_before_disclosure_is_detected(scenarios):
    """Same-turn / undisclosed PHI request: both controls fire. The engine's
    strongest case."""
    s = _scenario(scenarios, "nhid_ec2_combo_phi_preauth_undisclosed")
    assert {"IDG-01", "PDX-01"} <= _detected(s["scenario_id"], s["turns"])


def test_undisclosed_persona_phi_detects_idg_and_pdx_but_not_dbc(scenarios):
    """Undisclosed named-human persona requesting PHI on the opening turn.
    IDG-01 and PDX-01 fire; DBC-01 does NOT — the open scope question, scored
    honestly (see findings doc §DBC-01)."""
    s = _scenario(scenarios, "nhid_ec2_combo_undisclosed_persona_phi")
    got = _detected(s["scenario_id"], s["turns"])
    assert {"IDG-01", "PDX-01"} <= got
    assert "DBC-01" not in got, (
        "DBC-01 now fires on an undisclosed persona — update the v2 report, this "
        "test, and the findings doc's DBC-01 section together"
    )


def test_escalation_not_honored_is_detected(scenarios):
    s = _scenario(scenarios, "nhid_ec2_eit01_not_honored")
    assert "EIT-01" in _detected(s["scenario_id"], s["turns"])


def test_crossturn_contradiction_is_the_documented_idg_miss(scenarios):
    """Disclose AI at turn 0, claim to be a human nurse at turn 2. IDG-01's
    contradiction check is scoped to the disclosing turn, so a *later* turn's
    contradiction is not caught. This is the precise gap the findings doc
    records; pinned so it cannot regress or improve unnoticed."""
    s = _scenario(scenarios, "nhid_ec2_idg01_contradiction_crossturn")
    assert "IDG-01" not in _detected(s["scenario_id"], s["turns"]), (
        "cross-turn IDG-01 contradiction is now detected — good; update the v2 "
        "report, this test, and the findings doc together"
    )


def test_late_persona_misses_both_idg_and_dbc(scenarios):
    """Disclose AI, then present a deceptive human persona in a later turn.
    Both the cross-turn IDG-01 contradiction and later-turn DBC-01 persona
    detection are out of scope, so neither fires. PDX-01 is correctly NOT
    expected (the PHI follows the original disclosure)."""
    s = _scenario(scenarios, "nhid_ec2_combo_contradiction_persona_late")
    got = _detected(s["scenario_id"], s["turns"])
    assert "IDG-01" not in got and "DBC-01" not in got, (
        "a later-turn persona is now detected — update the v2 report, this test, "
        "and the findings doc together"
    )
    assert "PDX-01" not in got, "PDX-01 fired on post-disclosure PHI — a false positive"
