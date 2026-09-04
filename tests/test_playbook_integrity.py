"""The canonical Playbook says what the repository actually measures.

The Playbook is the most quotable document in the project: it is what someone
evaluating NHID-Clinical downloads and reads. It is also the easiest place for a
figure to go stale, because it restates numbers that live in five other files.

These are the invariants that would embarrass the project if they broke, not a
spell-check.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "NHID-Clinical-Playbook.md"
PDF = ROOT / "specs" / "NHID-Clinical-Playbook.pdf"
CANONICAL = ("IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01")


@pytest.fixture(scope="module")
def md() -> str:
    return SRC.read_text(encoding="utf-8")


def test_the_playbook_exists(md):
    assert len(md.split()) > 3000, "the Playbook is unexpectedly short"


def test_all_five_controls_are_named(md):
    missing = [c for c in CANONICAL if c not in md]
    assert not missing, f"Playbook omits {missing}"


def test_the_behavioural_audit_split_is_preserved(md):
    """Four behavioural + ATR-01 audit. Five total, and the distinction stated."""
    assert re.search(r"[Ff]our are deterministic behaviou?ral controls", md) or \
           re.search(r"four deterministic behaviou?ral controls", md), \
        "the four-behavioural / one-audit distinction is not stated"
    assert "audit and evidence control" in md, "ATR-01 is not identified as the audit control"


def test_no_sixth_control_is_invented(md):
    """DLG-01 is opt-in and must not be presented as one of the five."""
    ids = set(re.findall(r"\b[A-Z]{3}-\d{2}\b", md)) - {"CAS"}
    unexpected = ids - set(CANONICAL) - {"DLG-01"}
    assert not unexpected, f"Playbook names control ids outside the canonical set: {unexpected}"
    if "DLG-01" in md:
        assert "not one of the five" in md or "opt-in" in md, \
            "DLG-01 appears without being marked opt-in / outside the five"


def _unit_published() -> str:
    """The canonical conformance count, read from its source of truth.

    Hardcoding it here would mean every propagation breaks this test -- which is
    exactly what happened the first time: the figure moved from 1031 to 1073
    across sixty-four places and this assertion was not one of them.
    """
    import ast
    src = (ROOT / "scripts" / "validate_ci.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "UNIT_PUBLISHED":
                    return str(ast.literal_eval(node.value))
    raise AssertionError("UNIT_PUBLISHED not found in scripts/validate_ci.py")


@pytest.mark.parametrize("figure,why", [
    (None, "conformance count"),          # resolved from UNIT_PUBLISHED
    ("93.8", "governance detection rate"),
    ("30 of 32", "governance detection ratio"),
    ("0 of 5", "false positives over compliant scenarios"),
])
def test_verified_figures_appear(md, figure, why):
    expected = _unit_published() if figure is None else figure
    assert expected in md, f"the Playbook does not carry the {why} ({expected})"


def test_the_measurements_are_not_conflated(md):
    """The whole point of Part V §1. A detection rate is not a pass rate.

    Whitespace is normalised first: the source is hard-wrapped, so "not\na
    detection rate" is the same sentence and a raw substring check misses it.
    """
    flat = re.sub(r"\s+", " ", md)
    for phrase in ("not a detection rate", "not a test pass rate"):
        assert phrase in flat, f"missing the separation statement: {phrase!r}"


def test_no_prescribed_evaluation_duration(md):
    """The approved decision forbids a mandatory 30/60/90-day evaluation.

    A duration may be *mentioned* only to disclaim it, so the surrounding
    context decides. Anything else is a prescription.
    """
    negating = ("superseded", "no prescribed", "not a calendar", "forbids",
                "does not carry", "none has a required length")
    offenders = []
    for m in re.finditer(r"\b\d+\s*[-/]?\s*(?:day|week|month)\b", md, re.I):
        window = md[max(0, m.start() - 260): m.end() + 260].lower()
        if not any(n in window for n in negating):
            offenders.append(md[max(0, m.start() - 70): m.end() + 70].replace("\n", " "))
    assert not offenders, f"prescribed duration in the Playbook: {offenders}"


def test_regulatory_language_stays_a_mapping(md):
    assert "not a compliance claim" in md.lower(), "the mapping/compliance boundary is not stated"
    assert "requires qualified human judgment" in md.lower() or \
           "qualified human judgment" in md.lower(), "legal interpretation is not reserved to people"


def test_no_unsupported_adoption_or_deployment_claims(md):
    """The framework has no deployments, customers, or partners. Say so, and
    never the opposite."""
    assert re.search(r"no known production deployments", md, re.I), \
        "the Playbook does not state that there are no production deployments"
    banned = [
        r"\bour customers\b", r"\bin production at\b", r"\bdeployed at\b",
        r"\bdesign partners (?:are|include)\b", r"\bcertified by\b",
        r"\bindustry standard\b", r"\bis the standard\b",
    ]
    hits = [p for p in banned if re.search(p, md, re.I)]
    assert not hits, f"unsupported adoption/status language: {hits}"


def test_the_open_questions_are_recorded_not_resolved(md):
    for g in ("G1", "G2", "G3", "G4"):
        assert g in md, f"{g} is not carried into the Playbook"
    assert "Unresolved" in md or "unresolved" in md, "G1-G4 are not marked unresolved"


def test_maturity_labels_are_defined_and_used(md):
    for label in ("Implemented", "Reference implementation", "Conceptual", "Future", "Unknown"):
        assert label in md, f"maturity label {label!r} is never used"
    assert "Conceptual" in md and "TrustLayer" in md, \
        "TrustLayer must appear with an explicit maturity label"


def test_provenance_is_recorded(md):
    for field in ("Playbook version", "Framework version", "Source commit", "Canonical location"):
        assert field in md, f"provenance field missing: {field}"


def test_publication_is_not_claimed_to_confer_status(md):
    assert "does not confer status" in md.lower() or \
           "publication does not" in md.lower(), \
        "the Playbook does not disclaim that publishing it makes it a standard"


def test_pdf_matches_the_source_on_every_heading():
    """A renderer that silently drops a section is worse than one that crashes.

    Not skipped when the PDF is absent. specs/*.pdf is gitignored and the
    published PDFs are force-added, so an untracked Playbook PDF would 404 on
    the live site while these tests quietly skipped -- which is what a clean
    clone revealed.
    """
    assert PDF.exists(), (
        f"{PDF.relative_to(ROOT)} is missing. specs/*.pdf is gitignored; the "
        "published PDFs are tracked with `git add -f`. Run "
        "`python scripts/generate_pdfs.py` and force-add it."
    )
    pytest.importorskip("pdfminer.high_level")
    from pdfminer.high_level import extract_text

    flat = re.sub(r"[*`]", "", re.sub(r"\s+", " ", extract_text(str(PDF))))
    heads = [h.strip("# ").strip() for h in re.findall(r"^#{1,2} .+$", SRC.read_text(), re.M)]
    missing = [h for h in heads if re.sub(r"[*`]", "", re.sub(r"\s+", " ", h)) not in flat]
    assert not missing, f"headings absent from the rendered PDF: {missing}"


def test_pdf_carries_the_same_figures():
    assert PDF.exists(), f"{PDF.relative_to(ROOT)} is missing — see the test above"
    pytest.importorskip("pdfminer.high_level")
    from pdfminer.high_level import extract_text
    text = extract_text(str(PDF))
    for figure in (_unit_published(), "93.8"):
        assert figure in text, f"the rendered PDF is missing {figure!r}"
