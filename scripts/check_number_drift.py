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

Watched surfaces (drift-prone list from the docs-and-positioning protocol):
  README.md, evidence-pack.html, simulator.html, faq.html, index.html,
  .github/CONTRIBUTING.md, .github/workflows/ci.yml (job name),
  webplatform/templates/*.html, and the docs/ pages that quote suite totals.

The docs/ and index.html/faq.html entries were added after the DLG-01 work
found six files still claiming a superseded count while this guard reported
PASS — the guard was narrower than the actual claim surface, which is the exact
failure it exists to prevent.

Usage:
  python scripts/check_number_drift.py
"""

from __future__ import annotations

import ast
import glob
import re
import sys
from pathlib import Path

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

    print(
        f"DRIFT PASS: watched surfaces consistent with {unit_expected} passed "
        f"and DBC-01 {dbc_rate}%"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
