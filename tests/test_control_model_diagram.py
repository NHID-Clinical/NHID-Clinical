"""
The five-control model diagram
==============================
The framework is five controls, and four of them are not like the fifth.
IDG-01, PDX-01, DBC-01 and EIT-01 act on the call; ATR-01 records what they
decided and changes no behaviour.

That distinction has been misstated repeatedly in this repository's own
history — the site, the README and a generated PDF have each at some point
described "four controls" — which is why scripts/check_control_set.py exists.
This diagram encodes the same fact structurally rather than in prose, so these
tests check the structure, not the wording: four gates on the timeline, ATR-01
beneath it, and nothing miscounted in either direction.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = (ROOT / "specification.html").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")

BEHAVIOURAL = ("IDG-01", "PDX-01", "DBC-01", "EIT-01")
AUDIT = "ATR-01"


@pytest.fixture(scope="module")
def figure() -> str:
    m = re.search(r'<figure class="control-model".*?</figure>', SPEC, re.S)
    assert m, "the five-control model figure is gone from specification.html"
    return m.group(0)


# ── The structural claim ───────────────────────────────────────────────────

def test_there_are_exactly_four_behavioural_gates(figure):
    """A fifth gate would put ATR-01 on the call timeline, which is the error."""
    assert figure.count('class="cm-gate"') == 4, (
        "the diagram no longer shows exactly four behavioural gates"
    )


@pytest.mark.parametrize("control", BEHAVIOURAL)
def test_each_behavioural_control_is_a_gate(figure, control):
    gates = re.findall(r'<g class="cm-gate">(.*?)</g>', figure, re.S)
    assert any(control in g for g in gates), f"{control} is not drawn as a gate"


def test_the_audit_control_is_not_a_gate(figure):
    """
    ATR-01 must sit in the audit band, never among the gates. If it ever moves,
    the diagram is asserting that the framework has five behavioural controls.
    """
    gates = re.findall(r'<g class="cm-gate">(.*?)</g>', figure, re.S)
    assert not any(AUDIT in g for g in gates), "ATR-01 is drawn as a behavioural gate"
    audit = re.search(r'<g class="cm-audit">(.*?)</g>', figure, re.S)
    assert audit and AUDIT in audit.group(1), "ATR-01 is not in the audit band"


def test_the_audit_band_says_it_changes_no_behaviour(figure):
    audit = re.search(r'<g class="cm-audit">(.*?)</g>', figure, re.S).group(1)
    assert "Changes no behaviour" in audit


def test_all_five_controls_appear(figure):
    for control in BEHAVIOURAL + (AUDIT,):
        assert control in figure, f"{control} is missing from the diagram"


# ── The enforcement ladder, in order ───────────────────────────────────────

def test_the_ladder_is_stated_most_restrictive_first(figure):
    """
    The ordering is what makes the engine deterministic when several controls
    fire on one turn. Stated out of order it would describe a different engine.
    """
    ladder = ["DENY_DATA", "ESCALATE_HUMAN", "DISCLOSE_IDENTITY", "LOG_ONLY", "CONTINUE_AI"]
    positions = [figure.find(a) for a in ladder]
    assert all(p >= 0 for p in positions), f"an action is missing: {ladder}"
    assert positions == sorted(positions), "the enforcement ladder is out of order"


# ── Accessibility ──────────────────────────────────────────────────────────

def test_the_diagram_is_announced_as_an_image_with_a_description(figure):
    """
    A diagram carrying the framework's central distinction cannot be decorative.
    The description has to convey the shape, not just name the picture.
    """
    assert 'role="img"' in figure
    assert "aria-labelledby" in figure
    assert "<title" in figure and "<desc" in figure


def test_the_description_explains_the_four_versus_one_split(figure):
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", figure, re.S).group(1)
    assert "four" in desc.lower(), "the description does not say how many act on the call"
    assert re.search(r"ATR-01[^.]*records", desc, re.S), (
        "the description does not say what ATR-01 does differently"
    )
    for control in BEHAVIOURAL:
        assert control in desc, f"{control} is absent from the accessible description"


# ── It stays legible instead of crushing ───────────────────────────────────

def test_the_figure_scrolls_rather_than_collapsing_on_narrow_screens(figure):
    """
    Below roughly 34rem the labels collide. The figure scrolls inside its own
    box so the page itself never scrolls sideways — the same rule the Phase D
    containment work applied everywhere else.
    """
    assert re.search(r"\.control-model\s*\{[^}]*overflow-x:\s*auto", CSS)
    assert re.search(r"\.control-model svg\s*\{[^}]*min-width:", CSS)


def test_the_audit_band_is_drawn_differently_from_the_gates():
    """The distinction must survive someone reading only the shapes."""
    gate = re.search(r"\.cm-gate rect\s*\{([^}]*)\}", CSS).group(1)
    audit = re.search(r"\.cm-audit rect\s*\{([^}]*)\}", CSS).group(1)
    assert "stroke-dasharray" in audit and "stroke-dasharray" not in gate, (
        "ATR-01's band is no longer visually distinguishable from a gate"
    )


def test_both_themes_are_grounded():
    assert re.search(r'\[data-theme="dark"\]\s*\.cm-gate rect', CSS)
    assert re.search(r'\[data-theme="dark"\]\s*\.cm-audit rect', CSS)
