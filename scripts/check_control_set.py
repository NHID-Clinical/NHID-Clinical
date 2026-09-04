#!/usr/bin/env python3
"""
NHID-Clinical — control-set completeness guard
==============================================

Failure mode this exists for
----------------------------
On 2026-09-03, `specification.html` — the page reached from navigation as
"Specification (v1.3)" — was found to name IDG-01, DBC-01, EIT-01 and ATR-01,
and **not PDX-01**. The Pre-Data Exchange Gate, the control that stops PHI
moving before disclosure is confirmed, was absent from the document a reader
would treat as authoritative. It had been so long enough that the page had grown
a section titled "Why These Four" around the omission.

**No existing guard could see it.** `check_number_drift.py` compares *numbers*
across a watch list, and that page was not on the list. Even if it had been, the
page was internally consistent: it said four, and it listed four. Nothing was
numerically wrong. What was wrong was the *set*.

Two rules, and why a raw count is not one of them
-------------------------------------------------
The obvious rule — "a surface naming N of the five must name all five" — was
tried first and rejected. It cannot tell *enumerating* the control set from
*mapping* against it. A regulatory-alignment row citing "IDG-01 + DBC-01", or a
FHIR field map citing three controls, is not claiming the set has three members.
At a threshold of three it fired on eight surfaces, nearly all of them correct;
at four it still fired on mapping documents. A guard that cries wolf gets muted,
and a muted guard is worse than none.

So this checks the two things that are genuinely wrong when this bug occurs:

**Rule 1 — count claims must be true.** Any surface asserting how many controls
exist ("four behaviors", "the five controls") must say five and name all five.
This is exactly what `specification.html` failed: it said *"four behaviors"*,
listed four, and was internally consistent while being wrong. A count claim is a
factual claim, and factual claims are checkable.

The one legitimate exception is spelled out rather than guessed: *"four
deterministic behavioral controls"* is correct, because IDG-01, PDX-01, DBC-01
and EIT-01 are behavioral and ATR-01 is the audit control. Saying so explicitly
passes; saying a bare "four controls" does not.

**Rule 2 — authoritative surfaces carry the whole set.** A short curated list of
surfaces exists to define the framework. Those must name all five, always. It is
a whitelist, not a heuristic, so it yields no false positives and needs no
exemptions.

Everything else — mapping tables, single-control deep-dives, dated news — is
left alone deliberately.

Usage:
  python scripts/check_control_set.py
"""
from __future__ import annotations

import glob
import html
import re
import sys
from pathlib import Path

CANONICAL = ("IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01")

# Rule 2. Adding a surface here asserts that a reader may treat it as the
# authoritative control set.
AUTHORITATIVE = (
    "specification.html",
    "framework/controls.html",
    "index.html",
    "README.md",
    "specs/NHID-Clinical-v1.3-Core-Specification.pdf",
)

# Where published prose lives. Deliberately not a blanket repo walk: source
# code, fixtures and tests name controls constantly and are not "surfaces".
SURFACE_GLOBS = (
    "*.html",
    "framework/*.html",
    "platform/*.html",
    "alignment/*.html",
    "specs/*.html",
    "docs/*.md",
    "docs/*.html",
    "README.md",
)

# Dated or quoting surfaces, where a historical count claim is the record and
# rewriting it would falsify that record.
COUNT_CLAIM_EXEMPT = {
    "news.html",
    "docs/MASTER-KNOWLEDGE-ARCHIVE.md",
    "docs/claims-register.md",
    "docs/skipped-test-audit.md",
    "docs/ia-disposition.md",
    "docs/project-state.md",
}

# A bare "N controls" is not a claim about the size of the canonical set --
# "only two controls fired here" is a true sentence, and "v1.3 controls" is not
# a count at all (an earlier draft of this regex captured the "3" out of "v1.3"
# and the "01" out of "ATR-01 behavior"). So a qualifier is required: the phrase
# must be quantifying *the* set, not counting an occurrence.
_QUALIFIER = (
    r"(?:the|all|its|these|defines?|defining|suggests?|specifies?|proposes?"
    r"|comprises?|contains?|consists\s+of)"
)
_NUMBER = r"(one|two|three|four|five|six|\d+)"
# Two shapes, because the qualifier can fall on either side of the number.
#   "the proposal suggests four behaviors"  -> qualifier precedes  (shape 1)
#   "four suggested behaviors"              -> qualifier follows   (shape 2)
# Shape 2 was found on specs/index.html after shape 1 alone had been declared
# sufficient, which is the second time a version of this guard has been too
# narrow. Shape 2 is deliberately restricted to adjectives that only appear when
# the control set itself is being counted.
_SET_ADJ = r"(?:suggested|canonical|behaviou?ral|deterministic|core|policy)"
COUNT_CLAIM = re.compile(
    r"(?:\b" + _QUALIFIER + r"\s+" + _NUMBER
    + r"\s+(?:deterministic\s+)?(?:canonical\s+)?(?:behaviors?|behaviours?|controls?)\b"
    + r"|\b" + _NUMBER + r"\s+" + _SET_ADJ
    + r"\s+(?:behaviors?|behaviours?|controls?)\b)",
    re.I,
)
# Naming the subset is what matters, not the exact adjective. "four
# behavioural controls" is already unambiguous; requiring the word
# "deterministic" made the guard fire on four correct surfaces, and a guard
# that flags correct text gets muted.
BEHAVIORAL_OK = re.compile(
    r"four\s+(?:deterministic\s+)?behaviou?ral\s+controls?", re.I)
WORD_TO_INT = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def _visible_text(path: Path) -> str:
    raw = path.read_text(errors="replace")
    if path.suffix == ".html":
        m = re.search(r"<main\b.*?</main>", raw, re.S | re.I)
        raw = m.group(0) if m else raw
        raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return raw


def _load(surface: str) -> str | None:
    p = Path(surface)
    if not p.exists():
        return None
    if p.suffix == ".pdf":
        from pdfminer.high_level import extract_text
        return extract_text(surface)
    return _visible_text(p)


def _named(text: str) -> set[str]:
    return {c for c in CANONICAL if re.search(r"\b" + re.escape(c) + r"\b", text)}


def check_authoritative() -> list[str]:
    """Rule 2."""
    failures = []
    for surface in AUTHORITATIVE:
        text = _load(surface)
        if text is None:
            failures.append(surface + ": listed as authoritative but does not exist")
            continue
        missing = [c for c in CANONICAL if c not in _named(text)]
        if missing:
            failures.append(
                surface + ": authoritative surface omits " + ", ".join(missing)
                + ". A reader treats this document as the control set; it must "
                "name all five."
            )
    return failures


def check_count_claims() -> list[str]:
    """Rule 1. Applies to every published surface, not only authoritative ones."""
    failures = []
    seen: set[str] = set()
    surfaces: list[str] = []
    for pattern in SURFACE_GLOBS:
        surfaces.extend(sorted(glob.glob(pattern)))
    surfaces.extend(sorted(glob.glob("specs/*.pdf")))

    for surface in surfaces:
        if surface in seen or surface in COUNT_CLAIM_EXEMPT:
            continue
        seen.add(surface)
        text = _load(surface)
        if text is None or not _named(text):
            continue
        for m in COUNT_CLAIM.finditer(text):
            window = text[max(0, m.start() - 70): m.end() + 70]
            if BEHAVIORAL_OK.search(window):
                continue
            # The pattern alternates, so the number lands in whichever
            # branch matched; take the first group that captured.
            captured = next((g for g in m.groups() if g), None)
            if captured is None:
                continue
            raw = captured.lower()
            claimed = WORD_TO_INT.get(raw)
            if claimed is None:
                try:
                    claimed = int(raw)
                except ValueError:
                    continue
            if claimed != len(CANONICAL):
                phrase = re.sub(r"\s+", " ", m.group(0)).strip()
                failures.append(
                    surface + ': claims "' + phrase + '" but there are '
                    + str(len(CANONICAL)) + " canonical controls ("
                    + ", ".join(CANONICAL) + "). If this counts only the "
                    'behavioral subset, say so explicitly: "four deterministic '
                    'behavioral controls".'
                )
    return failures


def main() -> int:
    try:
        import pdfminer  # noqa: F401
    except ImportError:
        print(
            "CONTROL SET FAIL: pdfminer.six is not installed, so published PDFs "
            "were not checked. It is in requirements.txt — a skipped check must "
            "not report success."
        )
        return 1

    failures = check_authoritative() + check_count_claims()
    if failures:
        for f in failures:
            print("CONTROL SET FAIL: " + f)
        return 1
    print(
        "CONTROL SET PASS: " + str(len(AUTHORITATIVE))
        + " authoritative surfaces name all of " + ", ".join(CANONICAL)
        + "; no surface misstates the control count"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
