#!/usr/bin/env python3
"""Propagate a new suite count to every published surface, in one pass.

Adding a test makes roughly twenty files stale at once. scripts/validate_ci.py
warns and scripts/check_number_drift.py then names the surfaces one at a time,
which works but takes a round trip per file. This does the whole set, and the
drift guard remains the check that it worked.

  python scripts/bump_published_test_count.py 921 924 939 942

Historical entries are never touched: they record what was true when they were
written. A recorded transition ("Suite 1356 -> 1752") is protected by shape, so
a number inside one is never rewritten -- the blind substitution this replaces
damaged such a line on three consecutive bumps and was caught each time only by
reading the diff.
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
    # Added 2026-10-11. All four are in check_number_drift's WATCHED list but
    # were missing here, so a bump passed, the drift guard then failed, and the
    # remaining surfaces were fixed one round trip at a time — six extra passes
    # for the 1119 -> 1156 bump. This script exists to avoid exactly that.
    # The archive and the Playbook carry historical figures too; the guard
    # below only rewrites a whole-number match, and the archive's dated
    # entries were checked by hand on that bump. Re-read the diff rather than
    # trusting this list blindly.
    "docs/project-state.md", "docs/MASTER-KNOWLEDGE-ARCHIVE.md",
    "docs/NHID-Clinical-Playbook.md", "evidence-pack.html",
]


#: A recorded transition: "Suite 1356 -> 1752", "851 → 920 passed". Always a
#: historical delta, never a claim about the current count, so the numbers
#: inside one are protected from rewriting.
#:
#: This exists because the blind substitution below rewrote such a line on
#: three consecutive bumps -- "Suite 1356 → 1752" became "→ 1784", then
#: "Suite 1752 → 1796" became "→ 1779" -- each time inside a dated archive
#: entry describing what a past change did. Each was caught by reading the
#: diff, which is not a control. The shape is the signal: a current-state
#: claim never takes the form "A -> B".
TRANSITION = re.compile(r"\d{3,5}\s*(?:→|->)\s*\d{3,5}")


def _rewrite(src: str, pairs: list[tuple[str, str]]) -> tuple[str, int]:
    """Substitute each (old, new) in `src`, leaving recorded transitions alone.

    Returns the new text and how many figures moved.
    """
    protected: list[str] = []

    def _stash(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"\x00{len(protected) - 1}\x00"

    guarded = TRANSITION.sub(_stash, src)

    moved = 0
    for old, new in pairs:
        pattern = rf"(?<!\d){re.escape(old)}(?!\d)"
        guarded, n = re.subn(pattern, new, guarded)
        moved += n

    restored = re.sub(r"\x00(\d+)\x00",
                      lambda m: protected[int(m.group(1))], guarded)
    return restored, moved


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    old_pass, new_pass, old_total, new_total = sys.argv[1:5]
    pairs = [(old_pass, new_pass)]
    if old_total != old_pass:
        pairs.append((old_total, new_total))
    changed = 0
    for rel in SURFACES:
        p = ROOT / rel
        src = p.read_text()
        out, n = _rewrite(src, pairs)
        if out != src:
            p.write_text(out)
            changed += n
            print(f"  {rel}: {n}")
    print(f"{changed} figures updated across {len(SURFACES)} surfaces")
    print("Now run scripts/check_number_drift.py -- it is the check, not this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
