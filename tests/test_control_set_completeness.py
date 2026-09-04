"""The control set is five, and every surface that claims to present it says so.

Why this test exists
--------------------
`specification.html` — the page navigation labels "Specification (v1.3)" — named
IDG-01, DBC-01, EIT-01 and ATR-01 and omitted **PDX-01**, the gate that stops PHI
moving before disclosure is confirmed. It had been wrong long enough to grow a
section titled "Why These Four" around the omission.

Nothing caught it. The drift guard compares numbers on a watch list that did not
include the page, and the page was internally consistent anyway: it said four and
listed four. The defect was in the *set*, and no check looked at sets.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "scripts" / "check_control_set.py"


def _guard():
    spec = importlib.util.spec_from_file_location("check_control_set", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_guard_passes_on_the_current_tree():
    r = subprocess.run([sys.executable, str(GUARD)], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, f"control-set guard failed:\n{r.stdout}\n{r.stderr}"


def test_authoritative_surfaces_name_all_five():
    g = _guard()
    import os
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        assert g.check_authoritative() == []
    finally:
        os.chdir(cwd)


def test_the_canonical_set_is_exactly_these_five():
    """A guard whose definition of 'the set' can drift silently is not a guard."""
    g = _guard()
    assert g.CANONICAL == ("IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01")


@pytest.mark.parametrize("phrase,flagged,why", [
    ("The proposal suggests four behaviors for AI voice agents", True,
     "the exact wording of the original defect"),
    ("defines four controls", True, "a bare count that is wrong"),
    ("the five controls", False, "correct"),
    ("all five controls", False, "correct"),
    ("NHID-Clinical defines four deterministic behavioral controls", False,
     "four behavioral + ATR-01 audit is the correct description"),
    ("evaluate against the v1.3 controls", False,
     "a version number is not a count -- an earlier regex captured the 3"),
    ("ATR-01 behavior is recorded", False,
     "a control id is not a count -- an earlier regex captured the 01"),
    ("only two controls fired in this scenario", False,
     "counting an occurrence, not asserting the set size"),
])
def test_count_claim_detection(phrase, flagged, why):
    g = _guard()
    hits = []
    for m in g.COUNT_CLAIM.finditer(phrase):
        window = phrase[max(0, m.start() - 70): m.end() + 70]
        if g.BEHAVIORAL_OK.search(window):
            continue
        raw = m.group(1).lower()
        claimed = g.WORD_TO_INT.get(raw)
        if claimed is None:
            if not raw.isdigit():
                continue
            claimed = int(raw)
        if claimed != len(g.CANONICAL):
            hits.append(m.group(0))
    assert bool(hits) is flagged, f"{why}: {phrase!r} -> {hits}"


# specification.html as it stood at ba93e21, before PDX-01 was restored to it.
# Committed rather than fetched: CI checks out with fetch-depth 1, so
# `git show ba93e21:specification.html` fails on the runner and this test used
# to skip there while passing locally. A regression guard that only runs on one
# machine is not a guard, and this was the skip behind CI reporting "1144
# passed, 1 skipped" under a job named "0 skipped".
PRE_FIX = ROOT / "tests" / "fixtures" / "specification-pre-pdx01-ba93e21.html"


def test_guard_would_have_caught_the_original_defect():
    """Regression proof against the real pre-fix file, not a synthetic one."""
    g = _guard()
    assert PRE_FIX.exists(), (
        "the pre-fix specification fixture is missing; without it this test "
        "proves nothing about the original defect"
    )
    named = g._named(g._visible_text(PRE_FIX))
    assert "PDX-01" not in named, "the pre-fix file should be missing PDX-01"
    assert len(named) == 4


def test_the_fixture_is_the_real_pre_fix_file_when_history_is_available():
    """
    Belt and braces. Where the full history *is* present — a maintainer's
    checkout — confirm the committed fixture still matches the commit it claims
    to be, so it cannot be quietly edited into a synthetic example.

    Skipped only on a shallow clone, where there is nothing to compare against.
    """
    original = subprocess.run(
        ["git", "show", "ba93e21:specification.html"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if original.returncode != 0:
        pytest.skip("shallow checkout: ba93e21 not reachable, nothing to compare")
    assert PRE_FIX.read_text(encoding="utf-8") == original.stdout, (
        "the committed fixture no longer matches ba93e21:specification.html"
    )
