"""
Journey wayfinder — the arc, made navigable
===========================================
The IA consolidation mapped every destination to a journey, but only inside
ia-disposition.md. A reader landing on evidence-pack.html from a search result
had no way to see they were partway through an arc.

The wayfinder is generated, not hand-written, so the order cannot drift between
nine pages and adding a destination is one edit rather than nine. These tests
guard the generation and the shape it produces.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from add_journey_wayfinder import ARC, BEGIN, END  # noqa: E402


def _page(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_generated_blocks_are_current():
    """The load-bearing one: nine pages cannot drift out of order silently."""
    result = subprocess.run(
        [sys.executable, "scripts/add_journey_wayfinder.py", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


@pytest.mark.parametrize("path", [entry[0] for entry in ARC])
def test_every_destination_in_the_arc_carries_one(path):
    html = _page(path)
    assert BEGIN in html and END in html, f"{path} has no wayfinder"
    assert html.count(BEGIN) == 1, f"{path} has more than one wayfinder"


@pytest.mark.parametrize("path", [entry[0] for entry in ARC])
def test_it_is_a_labelled_landmark(path):
    """
    A navigation block needs its own label so a screen reader can seek it or
    skip it; an unlabelled second <nav> is just noise after the primary one.
    """
    block = _slice(_page(path))
    assert "<nav" in block and 'aria-label="Where this page sits in the journey"' in block


def _slice(html: str) -> str:
    return html[html.index(BEGIN):html.index(END)]


def test_the_first_page_offers_no_previous_step():
    block = _slice(_page(ARC[0][0]))
    assert "wayfinder-prev" not in block, "the first step cannot have a step before it"
    assert "wayfinder-next" in block


def test_the_last_page_offers_no_next_step():
    block = _slice(_page(ARC[-1][0]))
    assert "wayfinder-next" not in block, "the last step cannot have a step after it"
    assert "wayfinder-prev" in block


@pytest.mark.parametrize("path", [entry[0] for entry in ARC])
def test_every_page_offers_the_source(path):
    """
    "Where is the technical source?" is the last question in the brief's arc,
    and it is reachable from every step rather than only the end.
    """
    block = _slice(_page(path))
    assert "github.com/NHID-Clinical/NHID-Clinical" in block
    assert 'rel="noopener noreferrer"' in block


def test_adjacent_links_actually_point_at_the_neighbouring_destination():
    """A wayfinder that points at the wrong page is worse than none."""
    for i, (path, _href, _j, _q) in enumerate(ARC):
        block = _slice(_page(path))
        if i > 0:
            assert f'href="{ARC[i - 1][1]}"' in block, f"{path}: wrong previous link"
        if i < len(ARC) - 1:
            assert f'href="{ARC[i + 1][1]}"' in block, f"{path}: wrong next link"


def test_the_arc_answers_the_questions_the_brief_named():
    """
    The redesign brief names the journey. The arc must still answer it, or the
    wayfinder is guiding readers through a different product than the one asked
    for.
    """
    questions = " ".join(q for *_x, q in ARC).lower()
    for expected in ("what is this", "what does it control", "how do i evaluate",
                     "how do i implement", "where is the evidence"):
        assert expected in questions, f"the arc no longer answers {expected!r}"


def test_legal_pages_are_left_out_of_the_arc():
    """
    Privacy and SMS opt-in are not steps in a journey. Numbering them would be
    worse than omitting them.
    """
    paths = {entry[0] for entry in ARC}
    assert "privacy.html" not in paths
    assert "sms-opt-in.html" not in paths
    for legal in ("privacy.html", "sms-opt-in.html"):
        assert BEGIN not in _page(legal), f"{legal} should carry no wayfinder"


def test_the_wayfinder_can_shrink():
    css = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
    for selector in (".wayfinder", ".wayfinder-steps", ".wayfinder-steps li"):
        block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
        assert block and "min-width: 0" in block.group(1), f"{selector} may overflow"


def test_focus_is_visible_on_the_links():
    css = (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")
    assert re.search(r"\.wayfinder-steps a:focus-visible\s*\{[^}]*outline:", css)
