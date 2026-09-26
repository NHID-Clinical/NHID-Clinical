"""
The Trust Gateway — real engine output, and the guard that keeps it real
========================================================================
The component this replaces carried an honest disclaimer: "Illustrative —
dialogue, mock config payloads, and artwork are for explanation only." That is
the right disclaimer for a mock, and the wrong artifact for a page whose whole
argument is that the controls are checkable in a terminal.

So the Gateway renders output rather than an example. Two real scenarios from
the governance evaluation corpus are replayed through `evaluate_all` — the same
function the conformance suite and the hosted API call — and the action, reason
code and violations are recorded verbatim.

The load-bearing test here is the drift guard: it re-runs the engine and
compares. Without it, "real engine output" would be a claim about the day
someone generated the file. With it, the claim is true on every commit.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = (ROOT / "specification.html").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
JS = (ROOT / "site.js").read_text(encoding="utf-8")
FIXTURE = ROOT / "assets" / "data" / "gateway-trace.json"

BEGIN = "<!-- BEGIN GENERATED trust-gateway -->"
END = "<!-- END GENERATED trust-gateway -->"


@pytest.fixture(scope="module")
def trace() -> dict:
    assert FIXTURE.exists(), "the gateway fixture is missing; run build_gateway_fixture.py"
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# ── The guard that makes the claim true ────────────────────────────────────

def test_the_page_still_matches_what_the_engine_produces():
    """
    The whole component rests on this. If the engine changes and the page does
    not, the page is showing history while claiming to show behaviour.
    """
    result = subprocess.run(
        [sys.executable, "scripts/build_gateway_fixture.py", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        "the Trust Gateway has drifted from the engine:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_the_fixture_is_generated_not_written(trace):
    assert trace["generated_by"] == "scripts/build_gateway_fixture.py"
    assert trace["engine"].endswith("evaluate_all")
    assert trace["source_corpus"] == "tests/evaluation_corpus_v1.json"


def test_the_scenarios_are_real_corpus_scenarios(trace):
    """
    Neither scenario was authored for this page. Both are in the corpus that
    produces the published governance figure, which is what stops the Gateway
    becoming a curated demo.
    """
    corpus = json.loads((ROOT / "tests" / "evaluation_corpus_v1.json").read_text(encoding="utf-8"))
    known = {
        s["scenario_id"]
        for group in ("compliant_scenarios", "single_rule_violations", "multi_rule_combinations")
        for s in corpus.get(group, [])
    }
    for scenario in trace["scenarios"]:
        assert scenario["id"] in known, f"{scenario['id']} is not a corpus scenario"


# ── What it demonstrates ───────────────────────────────────────────────────

def test_it_shows_both_a_pass_and_the_failure_it_exists_for(trace):
    actions = {s["id"]: {t["action"] for t in s["turns"]} for s in trace["scenarios"]}
    compliant = actions.get("nhid_ec_comp_001", set())
    failing = actions.get("nhid_ec_combo_008", set())
    assert compliant == {"CONTINUE_AI"}, (
        "the compliant scenario should pass cleanly on every turn"
    )
    assert "DENY_DATA" in failing, "the failure scenario no longer blocks data"
    assert "ESCALATE_HUMAN" in failing, "the failure scenario no longer reaches escalation"


def test_every_action_shown_is_one_the_engine_can_return(trace):
    """Guards against a rendering bug inventing an outcome."""
    legal = {"DENY_DATA", "ESCALATE_HUMAN", "DISCLOSE_IDENTITY", "LOG_ONLY", "CONTINUE_AI"}
    for scenario in trace["scenarios"]:
        for turn in scenario["turns"]:
            assert turn["action"] in legal, f"unknown action {turn['action']!r}"


def test_violations_carry_the_engines_own_reason(trace):
    for scenario in trace["scenarios"]:
        for turn in scenario["turns"]:
            for v in turn["violations"]:
                assert v["rule_id"].startswith(("IDG", "PDX", "DBC", "EIT", "ATR"))
                assert v["description"], "a violation was rendered without its reason"


# ── Progressive enhancement ────────────────────────────────────────────────

def test_the_turns_are_server_rendered():
    """
    With JavaScript disabled the reader must still see the whole trace. The
    stepper is an enhancement over complete content, not the thing that
    produces it.
    """
    block = SPEC[SPEC.index(BEGIN):SPEC.index(END)]
    assert block.count('class="tg-turn"') == 7, (
        "the turns are no longer rendered into the page"
    )
    for token in ("tg-action", "tg-reason"):
        assert token in block


def test_the_controls_start_hidden_so_they_never_sit_dead():
    """Without the script the buttons would do nothing, so they are not shown."""
    assert 'class="tg-controls" hidden' in SPEC


def test_the_script_reveals_the_controls_only_after_wiring_them():
    assert "controls.hidden = false" in JS
    assert JS.index("addEventListener") < JS.index("controls.hidden = false"), (
        "the controls are revealed before their handlers are attached"
    )


def test_the_script_bails_out_rather_than_half_enhancing():
    """A missing element must leave the static content intact, not break it."""
    assert re.search(r"if \(!controls \|\| !prev \|\| !next \|\| !all \|\| !position\) return;", JS)


# ── Accessibility ──────────────────────────────────────────────────────────

def test_the_step_position_is_announced():
    assert 'aria-live="polite"' in SPEC, "stepping gives a screen reader no feedback"


def test_the_controls_are_real_buttons():
    """Not divs. Keyboard operation and focus come free with the right element."""
    block = SPEC[SPEC.index('<div class="tg-controls"'):SPEC.index(BEGIN)]
    # previous, next, show-all. The fourth element is the position readout,
    # which is a span because it is announced, not activated.
    assert block.count('<button type="button"') == 3
    assert '<div role="button"' not in block
    assert 'data-tg-position' in block


def test_focus_is_visible():
    assert re.search(r"\.tg-step:focus-visible\s*\{[^}]*outline:", CSS)


def test_motion_is_opt_in():
    assert "prefers-reduced-motion: no-preference" in CSS


# ── It says what it is ─────────────────────────────────────────────────────

def test_the_page_states_the_output_is_real_and_how_to_reproduce_it():
    assert "Nothing here is written by hand" in SPEC
    assert "build_gateway_fixture.py --check" in SPEC


def test_the_other_control_component_also_states_its_provenance():
    """
    The front-desk walkthrough on developers.html is the site's other component
    showing control behaviour. It used to be an illustration, and this test
    required it to say so.

    It is no longer an illustration: scripts/build_walkthrough_fixture.py
    replays real corpus scenarios through evaluate_all and the scene plays back
    the recording, guarded by --check in CI exactly as the Trust Gateway is. So
    the requirement is now the stronger one the disclaimer stood in for — a
    component showing control behaviour must state where its output came from —
    and it is checked in full by tests/test_walkthrough_fixture.py.

    What must never happen is either component going unlabelled.
    """
    dev = (ROOT / "developers.html").read_text(encoding="utf-8")
    assert "src/nhid_policy_engine_v1.py :: evaluate_all" in dev, (
        "the front-desk walkthrough no longer names the engine its output "
        "comes from"
    )
    assert "scripts/build_walkthrough_fixture.py" in dev, (
        "the front-desk walkthrough no longer names the script that recorded "
        "its output"
    )
    assert "the verdicts are not" in dev, (
        "the front-desk walkthrough no longer separates what is staging from "
        "what is engine output"
    )
