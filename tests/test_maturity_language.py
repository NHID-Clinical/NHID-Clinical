"""
Maturity language — the six states, and what keeps them honest
==============================================================
NHID-Clinical publishes work at very different standings: a deterministic engine
with a passing test suite, and a registry that does not exist, are both "on the
site". Before Phase D the site had no way to say which was which — status was
carried by whatever pill a page happened to use, and the words "implemented",
"verified" and "future" appeared as labels almost nowhere.

The six states are not a design invention. They are the standings already
recorded in docs/claim-boundaries.md §"Maturity boundaries", the authoritative
claims document. These tests pin the CSS to that document so the visual language
cannot quietly grow a seventh state, drop one, or start meaning something the
claims register does not support.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
CLAIMS = (ROOT / "docs" / "claim-boundaries.md").read_text(encoding="utf-8")

STATES = ("verified", "implemented", "reference", "conceptual", "research", "future")


def _block(selector: str, css: str = CSS) -> str:
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else ""


# ── The scale exists and is complete ───────────────────────────────────────

@pytest.mark.parametrize("state", STATES)
def test_every_state_is_defined(state):
    assert _block(f".maturity-{state}"), f".maturity-{state} has no rule"


def test_there_are_exactly_six_states():
    """
    A seventh state means someone introduced a standing the claims document does
    not recognise.

    A state is identified by what makes it one — a `.maturity-*` rule that
    defines its own glyph — rather than by its name. That way a structural
    class like .maturity-legend is not miscounted, and a new state cannot slip
    in under a name this test did not anticipate.
    """
    found = {
        m.group(1)
        for m in re.finditer(r"^\.maturity-([a-z]+)\s*\{([^}]*)\}", CSS, re.M)
        if "--maturity-glyph" in m.group(2)
    }
    assert found == set(STATES), f"state set drifted: {sorted(found)}"


# ── State is never carried by colour alone ─────────────────────────────────

@pytest.mark.parametrize("state", STATES)
def test_each_state_has_a_distinct_glyph(state):
    """
    Colour alone fails greyscale, colour-blindness and print. Each chip also
    renders its own word, so the glyph is the third signal, not the only one.
    """
    assert re.search(r"--maturity-glyph:", _block(f".maturity-{state}")), \
        f".maturity-{state} has no glyph; colour would be its only signal"


def test_the_glyphs_are_all_different():
    glyphs = re.findall(r"--maturity-glyph:\s*\"([^\"]+)\"", CSS)
    assert len(glyphs) == len(STATES), f"expected {len(STATES)} glyphs, found {len(glyphs)}"
    assert len(set(glyphs)) == len(glyphs), f"two states share a glyph: {glyphs}"


def test_the_glyph_is_decorative_not_the_label():
    """
    The word is the label. If the glyph were the only content, a screen reader
    would announce a shape.
    """
    assert re.search(r"\.maturity::before\s*\{[^}]*content:\s*var\(--maturity-glyph\)", CSS)


# ── Both themes are designed, not inverted ─────────────────────────────────

@pytest.mark.parametrize("state", STATES)
def test_every_state_is_redefined_for_dark(state):
    assert re.search(
        r'\[data-theme="dark"\]\s*\.maturity-' + state + r'\s*\{', CSS
    ), f".maturity-{state} has no dark-theme grounding and will glow or vanish"


# ── The scale stays tied to the claims document ────────────────────────────

def test_the_claims_document_still_carries_the_maturity_boundaries():
    """
    If this section is renamed or removed, the CSS comment citing it is stale and
    the six states have lost their source of authority.
    """
    assert "## Maturity boundaries" in CLAIMS


@pytest.mark.parametrize("standing,state", [
    ("Reference implementation", "reference"),
    ("Research component", "research"),
    ("Future work", "future"),
])
def test_the_standings_the_scale_names_appear_in_the_claims_document(standing, state):
    """
    Each of these phrases is used verbatim in claim-boundaries.md to describe a
    real element. The state exists because the standing does, not the reverse.
    """
    assert standing.lower() in CLAIMS.lower(), (
        f"claim-boundaries.md no longer describes anything as {standing!r}; "
        f"check whether .maturity-{state} still has a subject"
    )


def test_cas_is_still_recorded_as_a_research_component():
    """
    The Call Authorization Score is the sharpest case the scale exists for: the
    claims document calls it a research component and says it is not to be
    surfaced publicly. If that ever softens, the research state is doing work
    the document no longer backs.
    """
    assert re.search(r"Call Authorization Score.*Research component", CLAIMS, re.S | re.I)


# ── Containment, since chips sit inside flex and grid rows ─────────────────

def test_the_chip_and_its_legend_may_shrink():
    assert re.search(r"min-width:\s*0", _block(".maturity"))
    assert re.search(r"min-width:\s*0", _block(".maturity-legend"))
