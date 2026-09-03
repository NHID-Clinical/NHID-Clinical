#!/usr/bin/env python3
"""
NHID-Clinical – Confusion-matrix baseline guard
================================================
Runs scripts/confusion_matrix.py over the committed Fabricate corpus and fails
if any per-control detection or false-positive count moved from the recorded
baseline. This catches unintended engine/lexicon drift, not corpus changes.

If a change legitimately moves the baseline, update EXPECTED below in the SAME
commit as the engine change, and record the new numbers in the archive per the
change-control protocol (docs/MASTER-KNOWLEDGE-ARCHIVE.md §9.1).

Usage:
  python scripts/check_baseline.py
"""

from __future__ import annotations

import re
import subprocess
import sys

CORPUS = ["fixtures/fabricate/conversations.csv", "fixtures/fabricate/turns.csv"]

# Verified baseline (CSV-550 corpus). Detection is measured over conversations
# that declare the violation; FPs over the disjoint compliant population only.
# Updated 2026-07-31: DBC-01 & EIT-01 refined per Phase 4 fixes (artifact isolation,
# escalation honor patterns). See docs/MASTER-KNOWLEDGE-ARCHIVE.md §9.1.
EXPECTED = {
    #  control    detected expected  fp
    "IDG-01": (70, 70, 0),
    "PDX-01": (41, 41, 0),
    "DBC-01": (183, 200, 5),
    "EIT-01": (169, 171, 5),
}

ROW = re.compile(
    r"^(IDG-01|PDX-01|DBC-01|EIT-01)\s+(\d+)/(\d+)\s+[\d.]+%\s+(\d+)/\d+\s+[\d.]+%",
)


def main() -> int:
    result = subprocess.run(
        [sys.executable, "scripts/confusion_matrix.py", *CORPUS],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        print(output)
        print("BASELINE FAIL: confusion_matrix.py exited non-zero")
        return 1

    observed: dict[str, tuple[int, int, int]] = {}
    for line in output.splitlines():
        m = ROW.match(line.strip())
        if m:
            observed[m.group(1)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))

    failures = []
    for control, expected in EXPECTED.items():
        got = observed.get(control)
        if got is None:
            failures.append(f"{control}: row missing from confusion-matrix output")
        elif got != expected:
            failures.append(
                f"{control}: expected {expected[0]}/{expected[1]} detected, "
                f"{expected[2]} FP — got {got[0]}/{got[1]} detected, {got[2]} FP"
            )

    if failures:
        print(output)
        for f in failures:
            print("BASELINE FAIL:", f)
        print(
            "\nIf this change is intentional, update EXPECTED in "
            "scripts/check_baseline.py in the same commit and record the new "
            "numbers per docs/MASTER-KNOWLEDGE-ARCHIVE.md §9.1."
        )
        return 1

    print("BASELINE PASS:", ", ".join(f"{c} {d}/{e} ({fp} FP)" for c, (d, e, fp) in EXPECTED.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
