#!/usr/bin/env python3
"""Structural validation gate for the compiled playbook PDF.

Checks, against playbook/dist/NHID-Clinical-Operational-Playbook.pdf:
  - page count within a plausible band
  - all 20 chapter titles present
  - all 5 part-divider titles present
  - front matter + table of contents present
  - document metadata populated (Title, Author, Subject, Keywords)
  - no empty / near-empty body pages

Exits non-zero on any failure. Run after render_pdf.py.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PDF_PATH = REPO / "playbook" / "dist" / "NHID-Clinical-Operational-Playbook.pdf"
CHAPTERS_DIR = REPO / "playbook" / "chapters"

PART_TITLES = [
    "The Problem",
    "The Framework",
    "Implementation",
    "Enterprise Adoption",
    "The Future",
]
MIN_PAGES, MAX_PAGES = 180, 320
MIN_METADATA = ("title", "author", "subject", "keywords")


def _chapter_titles():
    import re

    titles = []
    for path in sorted(CHAPTERS_DIR.glob("chapter-*.md")):
        m = re.search(r"^# Chapter \d+ — (.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            titles.append(m.group(1).strip())
    return titles


def main():
    if not PDF_PATH.exists():
        sys.exit(f"error: {PDF_PATH} not found — run build_pdf.py then render_pdf.py")

    import fitz  # PyMuPDF

    doc = fitz.open(PDF_PATH)
    pages_text = [doc[i].get_text() for i in range(doc.page_count)]
    full_text = "\n".join(pages_text)
    failures = []

    # Page count band.
    if not (MIN_PAGES <= doc.page_count <= MAX_PAGES):
        failures.append(f"page count {doc.page_count} outside [{MIN_PAGES}, {MAX_PAGES}]")

    # All 20 chapter titles present.
    chapter_titles = _chapter_titles()
    if len(chapter_titles) != 20:
        failures.append(f"expected 20 chapter source files, found {len(chapter_titles)}")
    for t in chapter_titles:
        # PDF text may wrap; compare on a whitespace-insensitive basis.
        needle = " ".join(t.split())
        haystack = " ".join(full_text.split())
        if needle not in haystack:
            failures.append(f"chapter title missing from PDF: {t!r}")

    # All 5 part dividers.
    for pt in PART_TITLES:
        if pt not in full_text:
            failures.append(f"part title missing from PDF: {pt!r}")

    # Front matter + TOC markers.
    for marker in ("About this manuscript", "Licensing and attribution", "Contents"):
        if marker not in full_text:
            failures.append(f"front-matter/TOC marker missing: {marker!r}")

    # Metadata populated.
    meta = doc.metadata or {}
    for field in MIN_METADATA:
        if not (meta.get(field) or "").strip():
            failures.append(f"PDF metadata field empty: {field}")

    # No empty / near-empty body pages (allow the intentionally sparse
    # title/part-divider pages, which still carry running-header text).
    for i, txt in enumerate(pages_text):
        if len(txt.strip()) < 15:
            failures.append(f"page {i + 1} is empty/near-empty ({len(txt.strip())} chars)")

    doc.close()

    print(f"pages: {doc.page_count}")
    print(f"chapters checked: {len(chapter_titles)} · parts: {len(PART_TITLES)}")
    print(f"metadata: title={meta.get('title')!r} author={meta.get('author')!r}")

    if failures:
        print("\nVALIDATION FAILED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nVALIDATION PASSED")


if __name__ == "__main__":
    main()
