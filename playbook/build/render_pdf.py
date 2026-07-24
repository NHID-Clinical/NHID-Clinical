#!/usr/bin/env python3
"""Render playbook/dist/book.html to a PDF via headless Chromium, then stamp
document metadata from the build's sidecar JSON.

Portable: Chromium is resolved from Playwright's default, then $CHROMIUM_PATH,
then a glob under $PLAYWRIGHT_BROWSERS_PATH. Document metadata (Title, Author,
Subject, Keywords, Creator) is set with PyMuPDF because Chromium's print-to-PDF
cannot set those fields itself.

Run build_pdf.py first. See README.md.
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "playbook" / "dist"
HTML_PATH = DIST / "book.html"
META_PATH = DIST / "book.meta.json"
PDF_PATH = DIST / "NHID-Clinical-Operational-Playbook.pdf"

PAGE = {"width": "6.25in", "height": "9.25in"}
MARGIN = {"top": "0.95in", "bottom": "0.95in", "left": "0.75in", "right": "0.75in"}

HEADER_TEMPLATE = """
<div style="font-family: Helvetica, Arial, sans-serif; font-size: 7.2pt;
            color: #8a919e; width: 100%; padding: 0 0.75in; margin-top: -0.1in;
            display: flex; justify-content: space-between; letter-spacing: 0.04em;">
  <span>NHID-CLINICAL: THE OPERATIONAL PLAYBOOK</span>
  <span>DRAFT MANUSCRIPT</span>
</div>
"""

FOOTER_TEMPLATE = """
<div style="font-family: Helvetica, Arial, sans-serif; font-size: 8pt;
            color: #6b7280; width: 100%; text-align: center; margin-bottom: -0.1in;">
  <span class="pageNumber"></span>
</div>
"""


def _resolve_chromium():
    """Return an executable_path for Chromium, or None to use Playwright's default."""
    override = os.environ.get("CHROMIUM_PATH")
    if override and Path(override).exists():
        return override
    browsers = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers:
        for pat in ("chromium-*/chrome-linux/chrome", "chromium-*/chrome-linux/headless_shell"):
            hits = sorted(Path(browsers).glob(pat))
            if hits:
                return str(hits[-1])
    return None  # let Playwright locate its managed browser


def _stamp_metadata():
    import fitz  # PyMuPDF

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    doc = fitz.open(PDF_PATH)
    doc.set_metadata(
        {
            "title": meta["title"],
            "author": meta["author"],
            "subject": meta["subject"],
            "keywords": meta["keywords"],
            "creator": meta["creator"],
            "producer": meta["creator"],
        }
    )
    doc.saveIncr()
    doc.close()


def main():
    if not HTML_PATH.exists():
        sys.exit(f"error: {HTML_PATH} not found — run build_pdf.py first")

    from playwright.sync_api import sync_playwright

    exe = _resolve_chromium()
    with sync_playwright() as p:
        launch_kwargs = {"executable_path": exe} if exe else {}
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()
        page.goto(f"file://{HTML_PATH}")
        page.wait_for_timeout(300)
        page.pdf(
            path=str(PDF_PATH),
            width=PAGE["width"],
            height=PAGE["height"],
            margin=MARGIN,
            display_header_footer=True,
            header_template=HEADER_TEMPLATE,
            footer_template=FOOTER_TEMPLATE,
            print_background=True,
        )
        browser.close()

    if META_PATH.exists():
        _stamp_metadata()

    size_kb = PDF_PATH.stat().st_size / 1024
    print(f"Wrote {PDF_PATH} ({size_kb:.0f} KB), metadata stamped")


if __name__ == "__main__":
    main()
