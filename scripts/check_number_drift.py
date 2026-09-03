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
COUNT_CLAIMS = [
    re.compile(r"python%20tests-(\d+)%20passing"),  # shields.io badge (the middleware badge has its own count)
    re.compile(r"\b(\d{3})\b (?:Python )?tests? passing"),
    re.compile(r"\*\*(\d{3})\*\* (?:passing|passed|Python tests)"),
    re.compile(r"\b(\d{3})\b passing\b"),
    re.compile(r"\b(\d{3})\b passed\b"),
    re.compile(r"\((\d{3}) expected\)"),
]

# "DBC-01 ... 91.5%" style rate claims within one line.
DBC_RATE_CLAIM = re.compile(r"DBC-01[^%\n]{0,80}?(\d{1,3}\.\d)%")


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
    stats, false_positives = evaluate_corpus(scenarios)
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
