#!/usr/bin/env python3
"""
NHID-Clinical – Published-number drift guard
=============================================
Recurring failure mode in this repo: a count or detection rate changes, and a
stale copy survives in README badges, website pages, or CONTRIBUTING. This
script derives the canonical values from their source-of-truth files and fails
if any watched public surface claims a different number.

Sources of truth:
  - scripts/validate_ci.py      → UNIT_PUBLISHED (published unit-test count)
  - scripts/check_baseline.py   → EXPECTED (per-control detection/FP baseline)
  - scripts/eval_corpus.py      → measured live from the corpus, not a constant

Watched surfaces (drift-prone list from the docs-and-positioning protocol):
  README.md, evidence-pack.html, simulator.html, faq.html, index.html,
  .github/CONTRIBUTING.md, .github/workflows/ci.yml (job name),
  webplatform/templates/*.html, and the docs/ pages that quote suite totals.

The docs/ and index.html/faq.html entries were added after the DLG-01 work
found six files still claiming a superseded count while this guard reported
PASS — the guard was narrower than the actual claim surface, which is the exact
failure it exists to prevent.

The Governance Evaluation Corpus checks were added after an audit found IDG-01
published at 71.4% for a month (measured: 62.5%), a turn count of 99 that no
revision of the corpus ever had (measured: 55), and a "0% false-positive rate"
that nothing computed. Those figures are derived by *running* the corpus rather
than read from a constant, because a constant can be updated to match a wrong
published claim — which is how a superseded unit count once survived across the
whole repository while this guard passed.

Usage:
  python scripts/check_number_drift.py
"""

from __future__ import annotations

import ast
import glob
import re
import sys
from pathlib import Path

# Run as `python scripts/check_number_drift.py` — which is how CI invokes it —
# sys.path[0] is scripts/, not the repository root, so `from scripts.eval_corpus
# import ...` below fails with ModuleNotFoundError. Both corpus checks then
# degrade to warnings while the guard still exits PASS, which is precisely the
# silent-drift failure this script exists to prevent. It went unnoticed because
# the container it was written in happened to make the package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WATCHED = [
    "README.md",
    "evidence-pack.html",
    "simulator.html",
    "index.html",
    "faq.html",
    ".github/CONTRIBUTING.md",
    "docs/ATR-01-IMPLEMENTATION.md",
    "docs/CONTROL_DECISION_TABLE.md",
    "docs/CORPUS_EVALUATION_SUMMARY.md",
    "docs/SYSTEM_ARCHITECTURE.md",
    "docs/executive-brief.md",
    "docs/ops/inbound-knowledge-base.md",
    # Added 2026-09-06. Both were outside this list, which is why the archive
    # carried a stale 987 through four reconciliations while every watched
    # surface was corrected. The archive states the count once, in its
    # "Current state" block; its dated entries quote historical figures on
    # purpose and are written so they cannot be mistaken for current claims.
    "docs/MASTER-KNOWLEDGE-ARCHIVE.md",
    "docs/project-state.md",
    "conformance/nhid_conformance_test_suite_v1.yaml",
    *sorted(glob.glob("webplatform/templates/*.html")),
]

# Two corpora are measured in this repo and they report different DBC-01 rates:
# the 550-conversation Fabricate corpus (the baseline this guard derives from,
# 91.5%) and the 150-session Tonic corpus (100% against its seeded violations).
# These files document the Tonic evaluation, so their DBC-01 figures are a
# different measurement rather than a stale copy of this one. They stay under
# the unit-count check; only the rate check is exempt.
DBC_RATE_EXEMPT = frozenset({
    "docs/CORPUS_EVALUATION_SUMMARY.md",
    "docs/SYSTEM_ARCHITECTURE.md",
})

# Patterns whose captured number is a claim about the unit-test count.
#
# These were written as `\d{3}` when the suite was in the hundreds. When it
# crossed 1000 every one of them except the badge silently stopped matching, and
# this guard went on printing "DRIFT PASS: watched surfaces consistent with 1148
# passed" while README carried four claims it was no longer reading. Verified by
# corrupting them: the guard passed. `\d{3,4}` restores coverage.
#
# This is the third instance of the same failure in this repository — a check
# that narrowed until it verified less than its output claimed (the PDFs outside
# WATCHED, 2026-09-03; the nightly's shallow checkout, issue #385). Whenever the
# published count changes magnitude, re-run the corruption test below rather than
# trusting a PASS:
#
#   sed -i 's/\*\*1148 passing\*\*/**1147 passing**/' README.md
#   python scripts/check_number_drift.py   # must FAIL, then: git checkout README.md
COUNT_CLAIMS = [
    re.compile(r"python%20tests-(\d+)%20passing"),  # shields.io badge (the middleware badge has its own count)
    re.compile(r"\b(\d{3,4})\b (?:Python )?tests? passing"),
    re.compile(r"\*\*(\d{3,4})\*\* (?:passing|passed|Python tests)"),
    re.compile(r"\*\*(\d{3,4}) (?:passing|passed)\b"),
    re.compile(r"\b(\d{3,4})\b passing\b"),
    re.compile(r"\b(\d{3,4})\b passed\b"),
    re.compile(r"\((\d{3,4}) expected\)"),
    # A bare bolded value in a table cell declaring the constant, e.g.
    #   | `UNIT_PUBLISHED` | **1148** | scripts/validate_ci.py |
    # None of the prose patterns above match a cell like this. Found by
    # corrupting the archive's "Current state" block and watching the guard pass
    # — the canonical block would have been the one place not covered.
    # Delimiters vary by document: the archive bolds the value, project-state
    # backticks it. Both were tested by corruption; the bold-only version of
    # this pattern silently missed project-state.
    re.compile(r"UNIT_PUBLISHED`?\s*\|\s*[`*]{0,2}(\d{3,4})[`*]{0,2}\s*\|"),
]

# "DBC-01 ... 91.5%" style rate claims within one line.
DBC_RATE_CLAIM = re.compile(r"DBC-01[^%\n]{0,80}?(\d{1,3}\.\d)%")

# Per-line opt-out. A line carrying this marker is skipped by the count, corpus
# and DBC-rate checks.
#
# It exists because two watched documents are *records* as well as references:
# MASTER-KNOWLEDGE-ARCHIVE.md and project-state.md carry dated entries quoting
# the figures of their moment, a no-API measurement that is legitimately not the
# published count, and — in one table — claims catalogued precisely because they
# were wrong ("25 scenarios, 99 turns … never true at any revision"). Rewriting
# those to match today's invariant would falsify the record the documents exist
# to keep.
#
# Every use must state a reason on the same line. This is not a way to silence
# the guard on a surface that makes a live claim: if the number is what a reader
# would take as current, fix the number instead. Audit them with
#   grep -rn 'drift-ok' -- README.md docs/
DRIFT_OK = re.compile(r"drift-ok:")

# This guard's own output, pasted into a document as a record of a past run, is
# not a claim about the current count. Without this, transcripts of earlier runs
# in the archive's changelog fail the very check that produced them — and the
# only ways to satisfy it would be to edit captured output (falsifying a record)
# or to stop quoting runs at all. Deliberately anchored: no prose sentence a
# reader would take as a live claim begins "DRIFT PASS:".
GUARD_ECHO = re.compile(r"^\s*DRIFT (?:PASS|FAIL|WARN):")

# Whole-remainder opt-out, for a file that ends in a dated changelog. Every line
# from this marker to end-of-file is exempt from the count, corpus and DBC-rate
# checks.
#
# The archive's changelog is ~900 lines of dated entries, each quoting the
# metrics of its own day ("851 → 920 passed", "unchanged at 987"). Those are the
# point of the section. Marking thirty-odd lines individually would be noise
# that obscures the handful of genuine per-line exemptions above, so the section
# is declared once, at its heading, where a reader can see the scope.
#
# Use this ONLY where everything below really is a historical record. Anything
# above the marker is still checked, which is where live claims belong.
DRIFT_OK_REST_OF_FILE = re.compile(r"drift-ok-from-here:")


def _module_constant(path: str, name: str):
    tree = ast.parse(Path(path).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise LookupError(f"{name} not found in {path}")


# ── Governance Evaluation Corpus claims ────────────────────────────────────
# Deliberately narrow patterns. Three corpora are measured in this repo and all
# three report per-rule rates, so a generic "IDG-01 … NN%" match would collide
# across them. These match only phrasings that are unambiguously about the
# 25-scenario corpus.
CORPUS_TURNS_CLAIM = re.compile(r"(\d+) scenarios?, (\d+) turns")
CORPUS_AGGREGATE_CLAIM = re.compile(r"(\d{1,3}\.\d)% aggregate detection")
CORPUS_RATIO_CLAIM = re.compile(r"\((\d+)/(\d+) violations\)")
# Any surviving zero-false-positive claim on a line that also talks about
# scenarios. The measured rate is not zero; if it ever becomes zero, this
# pattern should be replaced with a comparison, not deleted.
# The lookbehind matters: without it this matches the "0% false-positive"
# inside "20% false-positive rate" and fails on correct text.
ZERO_FP_CLAIM = re.compile(
    r"(?<![\d.])0% false[- ]positives?|(?<![\d.])0 false positives", re.I
)


def _corpus_facts():
    """Measure the corpus by running it. Returns None if it cannot be run."""
    try:
        from scripts.eval_corpus import (  # noqa: PLC0415
            DEFAULT_CORPUS, collect_scenarios, evaluate_corpus, load_corpus,
        )
    except Exception:
        return None
    if not Path(DEFAULT_CORPUS).exists():
        return None
    scenarios = collect_scenarios(load_corpus(DEFAULT_CORPUS))
    stats, false_positives, _unexpected = evaluate_corpus(scenarios)
    clean = len(false_positives)
    dirty = sum(1 for rules in false_positives.values() if rules)
    return {
        "scenarios": len(scenarios),
        "turns": sum(len(s.get("turns", [])) for s in scenarios),
        "expected": sum(b["expected"] for b in stats.values()),
        "detected": sum(b["detected"] for b in stats.values()),
        "clean": clean,
        "dirty": dirty,
    }


def _check_corpus_claims(corpus, failures):
    aggregate = (
        f"{100.0 * corpus['detected'] / corpus['expected']:.1f}"
        if corpus["expected"] else None
    )
    for path in WATCHED:
        p = Path(path)
        if not p.exists():
            continue
        for lineno, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if DRIFT_OK_REST_OF_FILE.search(line):
                break
            if DRIFT_OK.search(line) or GUARD_ECHO.search(line):
                continue
            for m in CORPUS_TURNS_CLAIM.finditer(line):
                if int(m.group(1)) != corpus["scenarios"]:
                    continue  # a different corpus's scenario count
                if int(m.group(2)) != corpus["turns"]:
                    failures.append(
                        f"{path}:{lineno}: claims '{m.group(0)}' but the corpus "
                        f"has {corpus['turns']} turns"
                    )
            if aggregate:
                for m in CORPUS_AGGREGATE_CLAIM.finditer(line):
                    if m.group(1) != aggregate:
                        failures.append(
                            f"{path}:{lineno}: claims '{m.group(0)}' but the "
                            f"measured aggregate is {aggregate}%"
                        )
            for m in CORPUS_RATIO_CLAIM.finditer(line):
                if int(m.group(2)) != corpus["expected"]:
                    continue  # not this corpus's denominator
                if int(m.group(1)) != corpus["detected"]:
                    failures.append(
                        f"{path}:{lineno}: claims '{m.group(0)}' but the corpus "
                        f"detects {corpus['detected']}/{corpus['expected']}"
                    )
            # A zero-FP claim only belongs to this corpus if the line is
            # about it. Fabricate and Tonic legitimately report 0 FP, so the
            # line must either say "scenario" or carry this corpus's aggregate
            # or ratio signature. The "scenario" test alone missed the README
            # row that names the corpus only by its 81.2% / 26-of-32 figures.
            about_this_corpus = (
                "scenario" in line.lower()
                or (aggregate and CORPUS_AGGREGATE_CLAIM.search(line))
                or any(int(m.group(2)) == corpus["expected"]
                       for m in CORPUS_RATIO_CLAIM.finditer(line))
            )
            if corpus["dirty"] and about_this_corpus:
                for m in ZERO_FP_CLAIM.finditer(line):
                    failures.append(
                        f"{path}:{lineno}: claims '{m.group(0)}' but "
                        f"{corpus['dirty']} of {corpus['clean']} compliant "
                        f"scenarios emit a violation"
                    )


PUBLISHED_PDFS = "specs/*.pdf"


def _check_published_pdfs(unit_expected):
    """Read the text of every downloadable PDF and hold it to the same count.

    PDFs are the surface where a stale number survives longest: the site can be
    corrected in an afternoon, but a downloaded file keeps asserting whatever it
    said the day it was generated. This guard watched only HTML and Markdown, so
    `NHID-Clinical-v1.3-Overview.pdf` went on claiming "847 passing unit tests"
    across four count changes -- 847 to 851 to 920 to 924 to 987 -- while every
    web page was reconciled each time.

    A missing extractor is reported as a FAILURE, not a warning. The last time a
    check here degraded to a warning and still exited 0, it hid for a month.
    """
    failures = []
    paths = sorted(glob.glob(PUBLISHED_PDFS))
    if not paths:
        return [f"no PDFs matched {PUBLISHED_PDFS}: the published-artifact check ran against nothing"]
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        return [
            "pdfminer.six is not installed, so the published PDFs were not checked. "
            "Install it (it is in requirements.txt) rather than letting this pass."
        ]

    claim = re.compile(r"\b(\d{2,5})\s+passing\s+(?:unit\s+)?tests?\b", re.I)
    for path in paths:
        try:
            text = " ".join(extract_text(path).split())
        except Exception as exc:  # a PDF we cannot read is a PDF we cannot vouch for
            failures.append(f"{path}: could not extract text ({exc})")
            continue
        for m in claim.finditer(text):
            if int(m.group(1)) != unit_expected:
                failures.append(
                    f"{path}: claims '{m.group(0)}' but the suite invariant is "
                    f"{unit_expected} passed. Regenerate with scripts/generate_pdfs.py."
                )
    return failures


def main() -> int:
    unit_expected = _module_constant("scripts/validate_ci.py", "UNIT_PUBLISHED")
    baseline = _module_constant("scripts/check_baseline.py", "EXPECTED")
    detected, expected, _fp = baseline["DBC-01"]
    dbc_rate = f"{100.0 * detected / expected:.1f}"

    failures = []

    for path in WATCHED:
        p = Path(path)
        if not p.exists():
            continue
        for lineno, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if DRIFT_OK_REST_OF_FILE.search(line):
                break
            if DRIFT_OK.search(line) or GUARD_ECHO.search(line):
                continue
            for pat in COUNT_CLAIMS:
                for m in pat.finditer(line):
                    if int(m.group(1)) != unit_expected:
                        failures.append(
                            f"{path}:{lineno}: claims '{m.group(0)}' but the "
                            f"suite invariant is {unit_expected} passed"
                        )
            if path in DBC_RATE_EXEMPT:
                continue
            for m in DBC_RATE_CLAIM.finditer(line):
                if m.group(1) != dbc_rate:
                    failures.append(
                        f"{path}:{lineno}: claims DBC-01 {m.group(1)}% but the "
                        f"recorded baseline is {dbc_rate}%"
                    )

    failures += _check_published_pdfs(unit_expected)

    # The CI job name hardcodes the count by change-control convention.
    ci_yml = Path(".github/workflows/ci.yml").read_text()
    if f"{unit_expected} passed" not in ci_yml:
        failures.append(
            f".github/workflows/ci.yml: job name does not mention "
            f"'{unit_expected} passed' (atomic count propagation missed?)"
        )

    corpus = _corpus_facts()
    if corpus is None:
        print("DRIFT WARN: could not measure the evaluation corpus; "
              "its published figures were not checked this run")
    else:
        _check_corpus_claims(corpus, failures)

    # The generated report is the surface README links to for these figures.
    # An edited corpus with a forgotten regenerate makes it stale.
    try:
        from scripts.eval_corpus import main as _eval_main  # noqa: PLC0415
        if _eval_main(["--check"]) != 0:
            failures.append(
                "docs/EVALUATION_CORPUS_REPORT_v1.md is stale — run "
                "`python scripts/eval_corpus.py --write-report` and commit it"
            )
    except Exception as exc:  # pragma: no cover - defensive
        print(f"DRIFT WARN: could not verify the corpus report ({exc})")

    if failures:
        for f in failures:
            print("DRIFT FAIL:", f)
        print(
            "\nReconcile every published surface in the same commit: "
            "UNIT_PUBLISHED in scripts/validate_ci.py, the ci.yml job name, "
            ".github/CONTRIBUTING.md, the README badge and body, the website "
            "stats strip, and scripts/generate_pdfs.py."
        )
        return 1

    summary = (
        f"DRIFT PASS: watched surfaces consistent with {unit_expected} passed "
        f"and DBC-01 {dbc_rate}%"
    )
    if corpus:
        summary += (
            f"; corpus {corpus['scenarios']} scenarios / {corpus['turns']} turns, "
            f"{corpus['detected']}/{corpus['expected']} detected, "
            f"{corpus['dirty']}/{corpus['clean']} compliant scenarios firing"
        )
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
