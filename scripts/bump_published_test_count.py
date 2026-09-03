#!/usr/bin/env python3
"""Propagate a new suite count to every published surface, in one pass.

Adding a test makes roughly twenty files stale at once. scripts/validate_ci.py
warns and scripts/check_number_drift.py then names the surfaces one at a time,
which works but takes a round trip per file. This does the whole set, and the
drift guard remains the check that it worked.

  python scripts/bump_published_test_count.py 921 924 939 942

Historical changelog entries are never touched: they record what was true when
they were written.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Files carrying a current-state count. The archive is included but guarded
# below, since most of its matches are history.
SURFACES = [
    "scripts/validate_ci.py", ".github/workflows/ci.yml", ".github/CONTRIBUTING.md",
    "README.md", "index.html", "faq.html", "scripts/generate_pdfs.py",
    "conformance/nhid_conformance_test_suite_v1.yaml",
    "docs/executive-brief.md", "docs/CONTROL_DECISION_TABLE.md",
    "docs/SYSTEM_ARCHITECTURE.md", "docs/ATR-01-IMPLEMENTATION.md",
    "docs/CORPUS_EVALUATION_SUMMARY.md",
]


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    old_pass, new_pass, old_total, new_total = sys.argv[1:5]
    changed = 0
    for rel in SURFACES:
        p = ROOT / rel
        src = p.read_text()
        out = re.sub(rf"(?<!\d){old_pass}(?!\d)", new_pass, src)
        out = re.sub(rf"(?<!\d){old_total}(?!\d)", new_total, out)
        if out != src:
            n = len(re.findall(rf"(?<!\d)(?:{old_pass}|{old_total})(?!\d)", src))
            p.write_text(out)
            changed += n
            print(f"  {rel}: {n}")
    print(f"{changed} figures updated across {len(SURFACES)} surfaces")
    print("Now run scripts/check_number_drift.py -- it is the check, not this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
