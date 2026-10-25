"""The words `docs/claim-boundaries.md` rules out stay out of what is published.

`claim-boundaries.md` is the authority on what may be claimed and in what words
(CLAUDE.md §4). Two of its prohibitions were being broken by the project's own
documents on 25 Oct 2026: `terminology.md` listed "standards candidate" as the
*preferred* term while `claim-boundaries.md:154,251` forbid it, and
`index.html` called DLG-01 "a sixth" control against CLAUDE.md §3. Both were
found by reading, not by a test. This is the test.

Scope is what a reader meets: the published pages, the README, and the docs
that describe the project's standing. `claim-boundaries.md` and
`terminology.md` are excluded because they quote the forbidden words in order
to forbid them; the knowledge archive and `docs/archive/` are history.

A phrase inside a sentence that negates it ("not a sixth control", "rules out
'standards candidate'") is a statement of the rule, not a breach — the same
negation handling `test_canonical_threat_model.py` uses.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Forbidden on any published surface. Each entry is a phrase from
#: claim-boundaries.md / terminology.md's "refuse" column, or CLAUDE.md §3.
FORBIDDEN = (
    "standards candidate",
    "emerging standard",
    "sixth control",
    "a sixth",
    "production-ready",
    "production ready",
    "control plane",
    "trust infrastructure",
    "universal identity layer",
)

PUBLISHED_PAGES = (
    "index.html", "about.html", "specification.html", "shadow-evaluation-guide.html",
    "developers.html", "evidence-pack.html", "regulatory-alignment.html",
    "framework/nhid-auth.html", "faq.html", "specs/index.html", "privacy.html", "sms-opt-in.html",
)

STANDING_DOCS = (
    "README.md", "docs/positioning.md", "docs/project-state.md", "docs/executive-brief.md",
    "docs/nhid-clinical-technical-specification.md", "docs/canonical-threat-model.md",
    "docs/NHID-Clinical-Playbook.md",
)

NEGATIONS = re.compile(
    r"\b(?:never|not|n't|avoid|rather than|instead of|unless|rules? out|forbid\w*|"
    r"refuse\w*|withdrawn|incorrect(?:ly)?|wrong|do not|don't|must not|no longer|"
    r"is no|there is no|nor)\b",
    re.I,
)
NEGATION_WINDOW = 180


def _asserted(text: str) -> list[str]:
    """Forbidden phrases the text asserts, skipping ones it negates."""
    text = re.sub(r"<[^>]+>", " ", text)
    hits = []
    for phrase in FORBIDDEN:
        for m in re.finditer(re.escape(phrase), text, re.I):
            before = text[max(0, m.start() - NEGATION_WINDOW):m.start()]
            sentence = re.split(r"(?<=[.!?])\s|\n\s*[-*|]\s|\n\n", before)[-1]
            after = text[m.end():m.end() + 40]
            if NEGATIONS.search(sentence) or NEGATIONS.search(after.split(".")[0]):
                continue
            hits.append(f"{phrase!r} near: …{text[max(0, m.start()-50):m.end()+30].strip()}…")
    return hits


@pytest.mark.parametrize("relative", PUBLISHED_PAGES + STANDING_DOCS)
def test_no_published_surface_asserts_a_forbidden_claim(relative):
    path = ROOT / relative
    if not path.is_file():
        pytest.skip(f"{relative} is not present")
    hits = _asserted(path.read_text(encoding="utf-8", errors="replace"))
    assert not hits, f"{relative} asserts a claim docs/claim-boundaries.md rules out: {hits}"


def test_the_guard_recognises_an_asserted_claim():
    """A guard that has never failed has not been tested."""
    for sample in (
        "NHID-Clinical is a standards candidate.",
        "Five checks on every call, and a sixth when you opt in.",
        "A production-ready trust infrastructure for healthcare AI.",
    ):
        assert _asserted(sample), sample


def test_the_guard_leaves_a_negated_claim_alone():
    for sample in (
        "This is documented behaviour of the engine, **not a sixth control**.",
        "claim-boundaries.md rules out \"standards candidate\": no process has been opened.",
        "It is not production-ready infrastructure; it is a reference implementation.",
        "Refuse: emerging standard, control plane, trust infrastructure.",
    ):
        assert not _asserted(sample), sample


def test_the_withdrawn_dbc01_tier_is_not_described_as_live():
    """DBC-01's acoustic-artifact tier was withdrawn in v1.3.2; the engine
    analyses no audio and ignores self-reported flags. The spec page and the
    technical specification described it as current for a release after that."""
    phrases = ("fabricated breathing", "synthetic keyboard", "call-center ambience",
               "no synthetic voice artifacts", "no audio artifacts")
    for relative in ("specification.html", "docs/nhid-clinical-technical-specification.md"):
        text = (ROOT / relative).read_text(encoding="utf-8").lower()
        found = [p for p in phrases if p in text]
        assert not found, f"{relative} still describes the withdrawn acoustic tier as a rule: {found}"


def test_atr01_missing_fields_are_described_with_the_engines_action():
    """The spec said missing audit fields are 'a CRITICAL ATR-01 violation';
    the engine records a critical-severity finding and takes LOG_ONLY. Both
    halves must be stated, or a reader expects a block the engine never does."""
    for relative in ("specification.html", "docs/nhid-clinical-technical-specification.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "LOG_ONLY" in text, f"{relative} does not state the engine's ATR-01 action"
        assert "critical findings, not warnings" not in text
        assert "are a CRITICAL ATR-01 violation" not in text
