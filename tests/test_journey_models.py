"""
Canonical visual models — the boundary and the shadow evaluation
================================================================
Two diagrams, each drawn to settle a specific misreading that prose had not.

  interaction boundary   positioning.md states the thesis: NHID-Clinical "does
                         not govern the AI model. It governs the moment a
                         non-human actor crosses an organizational boundary."
                         The common misreading is that this is healthcare AI
                         governance broadly, so the model itself is drawn
                         inside the provider organization and labelled as out
                         of scope.

  shadow evaluation      "observe-only, non-intercepting" has been on the page
                         for a long time and kept being read as interception,
                         so the figure is one-way by construction: exactly one
                         arrow crosses from the call into the evaluation, and
                         none returns.

These tests check the structural claims, not the prose around them.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
GUIDE = (ROOT / "shadow-evaluation-guide.html").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
POSITIONING = (ROOT / "docs" / "positioning.md").read_text(encoding="utf-8")


def _figure(html: str, cls: str) -> str:
    """The figure element carrying `cls`, which may sit among other classes."""
    m = re.search(r'<figure[^>]*class="[^"]*\b' + cls + r'\b[^"]*".*?</figure>', html, re.S)
    assert m, f"the {cls} figure is gone"
    return m.group(0)


@pytest.fixture(scope="module")
def boundary():
    return _figure(INDEX, "boundary-model")


@pytest.fixture(scope="module")
def shadow():
    return _figure(GUIDE, "shadow-model")


# ── The interaction boundary ───────────────────────────────────────────────

def test_the_thesis_is_still_what_the_diagram_draws():
    """If positioning.md changes its thesis, the diagram is drawing the old one."""
    assert "does not govern the AI model" in POSITIONING
    assert "crosses an organizational boundary" in POSITIONING


def test_the_model_itself_is_drawn_as_out_of_scope(boundary):
    """
    The single most useful thing this figure does is exclude something. If the
    out-of-scope block goes, the diagram starts implying the project governs
    the model.
    """
    outside = re.search(r'<g class="ib-outside">(.*?)</g>', boundary, re.S)
    assert outside, "the out-of-scope block is gone from the boundary diagram"
    body = outside.group(1)
    assert "Not governed here" in body
    assert "The model itself" in body


def test_the_out_of_scope_block_is_drawn_quietly():
    """It is there to be excluded, not to compete with what is in scope."""
    outside = re.search(r"\.ib-outside rect\s*\{([^}]*)\}", CSS).group(1)
    gate = re.search(r"\.ib-gate rect\s*\{([^}]*)\}", CSS).group(1)
    assert "stroke-dasharray" in outside, "out-of-scope should be dashed"
    assert "stroke-dasharray" not in gate, "what is governed should be solid"


def test_the_boundary_is_between_two_organizations(boundary):
    assert boundary.count('<g class="ib-org">') == 2, "the diagram needs both organizations"
    assert "ORGANIZATIONAL BOUNDARY" in boundary


def test_the_five_questions_map_to_the_five_controls(boundary):
    for control in ("IDG", "PDX", "DBC", "EIT", "ATR"):
        assert control in boundary, f"{control} is not tied to a boundary question"
    assert boundary.count('class="ib-gate-q"') == 5, "there should be five questions"


# ── Shadow evaluation ──────────────────────────────────────────────────────

def test_exactly_one_arrow_crosses_into_the_evaluation(shadow):
    """
    The tap is the only connection between the call and the evaluation, and it
    represents recording that already happens.
    """
    assert shadow.count('class="sm-tap"') == 1, "there must be exactly one crossing"
    assert shadow.count('class="sm-tap-head"') == 1


def test_nothing_flows_back_into_the_call(shadow):
    """
    The claim is non-interception. A second crossing, in either direction,
    would contradict the figure's whole reason for existing.
    """
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", shadow, re.S).group(1)
    assert "No arrow returns upward" in desc or "no arrow returns" in desc.lower()
    assert re.search(r"cannot alter, delay, block or intercept", shadow), (
        "the figure no longer states what the evaluation cannot do"
    )


def test_the_live_call_is_labelled_unchanged(shadow):
    assert "UNCHANGED" in shadow
    assert "OBSERVE ONLY" in shadow


def test_the_traces_are_the_adopters_own(shadow):
    """
    The evaluation reads traces the adopter already holds, under their existing
    obligations. Losing that framing would imply data moves to this project.
    """
    assert "Call traces you hold" in shadow
    assert "your existing obligations" in shadow.lower() or "existing obligations" in shadow


# ── Both models, shared standards ──────────────────────────────────────────

@pytest.mark.parametrize("fig,name", [("boundary", "boundary-model"), ("shadow", "shadow-model")])
def test_each_model_is_announced_with_a_description(fig, name, request):
    figure = request.getfixturevalue(fig)
    assert 'role="img"' in figure
    assert "aria-labelledby" in figure
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", figure, re.S)
    assert desc and len(desc.group(1).split()) >= 40, (
        f"{name} needs a description that conveys the shape, not just a caption"
    )


@pytest.mark.parametrize("cls", ["boundary-model", "shadow-model"])
def test_each_model_scrolls_rather_than_crushing(cls):
    block = re.search(re.escape("." + cls) + r"\s*\{([^}]*)\}", CSS).group(1)
    assert "overflow-x: auto" in block
    assert re.search(re.escape("." + cls) + r" svg\s*\{[^}]*min-width:", CSS)


@pytest.mark.parametrize("selector", [".ib-gate rect", ".ib-actor rect", ".sm-eval rect", ".sm-tap"])
def test_both_themes_are_grounded(selector):
    assert re.search(r'\[data-theme="dark"\]\s*' + re.escape(selector), CSS), (
        f"{selector} has no dark-theme grounding"
    )
