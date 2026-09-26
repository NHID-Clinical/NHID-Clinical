"""
Canonical visual models — reference architecture and evidence lifecycle
=======================================================================
Two more diagrams, each drawn to hold a line the repository keeps having to
restate in prose.

  reference architecture   An architecture diagram that draws only what works
                           is a sales diagram. claim-boundaries.md records key
                           custody as documented-but-not-built, the registry as
                           future work needing a neutral operator, and
                           federation as an open problem. The figure is split:
                           built above the divider, not built below it, drawn
                           where it would go.

  evidence lifecycle       project-state.md §5 is titled "Evidence — four
                           distinct bodies, never to be merged". A reader
                           looking at four percentages naturally wants to
                           average them, so the figure gives a combined number
                           nowhere to go: four peers, no arrow between them, no
                           total beneath them.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DEV = (ROOT / "developers.html").read_text(encoding="utf-8")
EVID = (ROOT / "evidence-pack.html").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
CLAIMS = (ROOT / "docs" / "claim-boundaries.md").read_text(encoding="utf-8")
STATE = (ROOT / "docs" / "project-state.md").read_text(encoding="utf-8")


def _figure(html: str, cls: str) -> str:
    m = re.search(r'<figure[^>]*class="[^"]*\b' + cls + r'\b[^"]*".*?</figure>', html, re.S)
    assert m, f"the {cls} figure is gone"
    return m.group(0)


@pytest.fixture(scope="module")
def arch():
    return _figure(DEV, "arch-model")


@pytest.fixture(scope="module")
def evidence():
    return _figure(EVID, "evidence-model")


# ── Reference architecture: what is not built is drawn as not built ────────

@pytest.mark.parametrize("absent", ["Key custody", "Registry", "federation"])
def test_the_unbuilt_components_are_named(arch, absent):
    block = re.search(r'<g class="ra-absent">(.*?)</g>', arch, re.S)
    assert block, "the not-built band is gone from the architecture diagram"
    assert absent.lower() in block.group(1).lower(), (
        f"{absent!r} is no longer shown as unbuilt; the diagram now implies it exists"
    )


def test_the_unbuilt_band_is_drawn_hollow():
    """
    A filled box reads as a component. These are placeholders for things that
    do not exist, so they are hollow and dashed.
    """
    absent = re.search(r"\.ra-absent rect\s*\{([^}]*)\}", CSS).group(1)
    built = re.search(r"\.ra-box rect\s*\{([^}]*)\}", CSS).group(1)
    assert "fill: none" in absent, "unbuilt components must not be filled like real ones"
    assert "stroke-dasharray" in absent and "stroke-dasharray" not in built


def test_the_claims_document_still_says_these_are_not_built():
    """If any of the three ships, the diagram is wrong and should fail here first."""
    assert re.search(r"Key custody[^|]*\|[^|]*not built", CLAIMS, re.I)
    assert re.search(r"Registry[^|]*\|[^|]*(Future work|does not exist)", CLAIMS, re.I)
    assert re.search(r"Federation[^|]*\|[^|]*(open problem|not a shipped)", CLAIMS, re.I)


def test_the_architecture_states_the_gap_it_is_drawing(arch):
    assert "reference implementation and deployable infrastructure" in arch


def test_the_adapter_counts_match_the_project_state(arch):
    """
    Eight adapter modules exist and five are wired to hosted routes. Those are
    verified numbers, so the diagram must not round or inflate them.
    """
    assert "8 modules" in arch and "5 wired" in arch
    assert "Eight adapter modules exist" in STATE
    assert "Five are wired to hosted routes" in STATE


def test_the_architecture_uses_the_maturity_language(arch):
    """
    Status vocabulary was defined once, in Phase D. A second one invented here
    would be exactly the drift the maturity work removed.
    """
    for state in ("implemented", "verified", "conceptual", "future"):
        assert f"maturity-{state}" in arch, f"the caption does not label anything {state}"


# ── Evidence lifecycle: four bodies, no total ──────────────────────────────

def test_the_never_merged_rule_is_still_the_projects_position():
    assert "never to be merged" in STATE


def test_all_four_evidence_bodies_appear(evidence):
    for body in ("Conformance suite", "Fabricate corpus", "Governance corpus", "Adversarial corpus"):
        assert body in evidence, f"{body} is missing from the evidence lifecycle"


def test_the_four_are_drawn_as_peers_with_no_total(evidence):
    """
    The rule is structural: four boxes side by side, nothing joining them, and
    no summary box for a combined figure to live in.
    """
    band = re.search(r'<g class="ev-body">(.*?)</g>', evidence, re.S)
    assert band, "the four-bodies band is gone"
    assert band.group(1).count("<rect") == 4, "there must be exactly four evidence bodies"
    assert "ev-flow" not in band.group(1), "an arrow between the bodies implies they combine"


def test_the_figure_says_why_a_combined_figure_is_not_published(evidence):
    assert "would describe none of them" in evidence
    assert "does not publish one" in evidence


def test_the_atr01_absence_is_explained_not_scored(evidence):
    """
    ATR-01 is absent from the Fabricate corpus because that corpus cannot
    measure it. Shown as 0% it would read as a failing control.
    """
    assert "structural limit, not a score of zero" in evidence


# ── Shared standards ───────────────────────────────────────────────────────

@pytest.mark.parametrize("fig", ["arch", "evidence"])
def test_each_model_is_announced_with_a_description(fig, request):
    figure = request.getfixturevalue(fig)
    assert 'role="img"' in figure and "aria-labelledby" in figure
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", figure, re.S)
    assert desc and len(desc.group(1).split()) >= 50, (
        "the description must convey the shape, not name the picture"
    )


@pytest.mark.parametrize("cls", ["arch-model", "evidence-model"])
def test_each_model_scrolls_rather_than_crushing(cls):
    block = re.search(re.escape("." + cls) + r"\s*\{([^}]*)\}", CSS).group(1)
    assert "overflow-x: auto" in block
    assert re.search(re.escape("." + cls) + r" svg\s*\{[^}]*min-width:", CSS)


@pytest.mark.parametrize("selector", [".ra-box rect", ".ra-core rect", ".ev-body rect", ".ev-core rect"])
def test_both_themes_are_grounded(selector):
    assert re.search(r'\[data-theme="dark"\]\s*' + re.escape(selector), CSS)
