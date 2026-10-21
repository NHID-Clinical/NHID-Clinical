"""
Propagating a new test count must not rewrite history
=====================================================
`scripts/bump_published_test_count.py` moves the published suite count across
seventeen surfaces in one pass. It did so by blind regex substitution of the
old number, which rewrote a *recorded transition* inside a dated archive entry
on three consecutive bumps:

    "Suite 1356 → 1752"  became  "→ 1784"     (2026-10-21, caught in review)
    "Suite 1356 → 1752"  became  "→ 1790"     (same day, caught again)
    "Suite 1752 → 1796"  became  "→ 1779"     (same day, caught again)

Each one falsified a record of what a past change did, and each was caught only
by a human reading the diff — which is not a control. The shape is the signal: a
claim about the current count never takes the form "A → B", and a transition is
always history.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.bump_published_test_count import TRANSITION, _rewrite

ROOT = Path(__file__).resolve().parents[1]


# ── a current claim moves ───────────────────────────────────────────────────

def test_a_current_state_claim_is_rewritten():
    text = "Expected: **1796 passing**, 0 skipped, 0 xfailed.\n"
    out, moved = _rewrite(text, [("1796", "1779")])
    assert out == "Expected: **1779 passing**, 0 skipped, 0 xfailed.\n"
    assert moved == 1


def test_a_badge_url_is_rewritten():
    text = "python%20tests-1796%20passing-brightgreen"
    out, _ = _rewrite(text, [("1796", "1779")])
    assert "tests-1779%20passing" in out


def test_a_table_cell_is_rewritten():
    text = "| `UNIT_PUBLISHED` | **1796** | `scripts/validate_ci.py` |"
    out, moved = _rewrite(text, [("1796", "1779")])
    assert "**1779**" in out and moved == 1


# ── a recorded transition does not ──────────────────────────────────────────

@pytest.mark.parametrize("line", [
    "Suite 1752 → 1796. Both pinned baselines unmoved throughout:",
    "Suite 1356 -> 1752. Both pinned baselines unmoved.",
    "851 → 920 passed",
    "the suite went 1796 -> 1779 in that change",
    "Suite 1752→1796.",
])
def test_a_recorded_transition_is_left_alone(line):
    """Both arrow forms, with and without spaces."""
    out, moved = _rewrite(line, [("1796", "1779"), ("1752", "9999")])
    assert out == line, f"history was rewritten: {out!r}"
    assert moved == 0


def test_the_exact_line_that_was_damaged_three_times():
    line = ("**Mathematical audit.** Suite 1752 → 1796. Both pinned baselines "
            "unmoved throughout.")
    out, _ = _rewrite(line, [("1796", "1779")])
    assert out == line


def test_a_claim_on_the_same_line_as_a_transition_still_moves():
    """The protection is scoped to the transition, not to the whole line."""
    line = "Suite 1752 → 1796 at the time; the suite now publishes 1796 passing."
    out, moved = _rewrite(line, [("1796", "1779")])
    assert "Suite 1752 → 1796 at the time" in out, "the record stands"
    assert "publishes 1779 passing" in out, "the live claim moved"
    assert moved == 1


# ── the real documents survive a simulated bump ─────────────────────────────

ARCHIVE = ROOT / "docs" / "MASTER-KNOWLEDGE-ARCHIVE.md"


def test_the_archives_transitions_survive_a_simulated_bump():
    """Run the rewriter over the real archive and assert every transition it
    contains is byte-identical afterwards. This is the assertion that would
    have caught all three incidents."""
    text = ARCHIVE.read_text(encoding="utf-8")
    before = TRANSITION.findall(text)
    assert before, "the archive records no transitions; this test has lost its subject"

    out, _ = _rewrite(text, [("1779", "4242"), ("1796", "4242"), ("1752", "4242")])
    assert TRANSITION.findall(out) == before, (
        "a recorded transition in the archive was rewritten by a count bump"
    )


def test_the_two_known_historical_lines_are_still_present_and_correct():
    """Named explicitly, because these are the exact records that were damaged."""
    text = ARCHIVE.read_text(encoding="utf-8")
    assert "Suite 1356 → 1752" in text, "§19.15's delta"
    assert "Suite 1752 → 1796" in text, "§19.16's delta"


def test_the_transition_pattern_does_not_match_an_ordinary_claim():
    for ordinary in ("1796 passing", "**1796**", "(1796 expected)",
                     '"total_tests": 1796'):
        assert not TRANSITION.search(ordinary), ordinary
