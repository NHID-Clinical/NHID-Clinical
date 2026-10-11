#!/usr/bin/env python3
"""
Render the canonical Playbook to PDF from its markdown source.

The Playbook is written once, in `docs/NHID-Clinical-Playbook.md`. This renders
that file rather than restating it in reportlab calls, which is the whole point:
the other PDFs in `specs/` are built from Python literals, and that is exactly
how `NHID-Clinical-v1.3-Overview.pdf` came to claim "847 passing unit tests"
long after the suite had moved on four times. A generated document whose prose
lives only inside its generator cannot be diffed, reviewed, or corrected by
anyone reading the repository.

The markdown renderer this used to define now lives in `src/pilot_pdf.py`,
because the Tier 0 evidence pack needs the same one and two copies of a
markdown renderer drift apart. Everything about the output is unchanged: same
cover, same house style, same page break on every H1.
"""
from __future__ import annotations

import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.generate_pdfs import OUT_DIR  # noqa: E402
from src.pilot_pdf import render_markdown_pdf  # noqa: E402

SRC = os.path.join(_REPO_ROOT, "docs", "NHID-Clinical-Playbook.md")
OUT = os.path.join(OUT_DIR, "NHID-Clinical-Playbook.pdf")


def main() -> int:
    with open(SRC, encoding="utf-8") as f:
        md = f.read()

    # The shared renderer takes no subprocess dependency — the Tier 0 kit
    # imports it and must not be able to execute anything. Discovering the
    # commit is this script's job, and it passes the result in as text.
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True,
                                cwd=_REPO_ROOT).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        commit = "unknown"

    render_markdown_pdf(
        md, OUT,
        title="NHID-Clinical Playbook",
        subtitle="Evaluation, Implementation, and Evidence Guide",
        version="1.0",
        footer_note=f"Framework v1.3  ·  source commit {commit}",
        author="Brianna Baynard",
        page_break_on_h1=True,
    )
    print(f"  ✓  {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
