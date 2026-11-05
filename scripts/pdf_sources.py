"""The sources the published PDFs are built from, and their fingerprint.

scripts/generate_pdfs.py writes specs/pdf-sources.sha256 after building the
PDFs. tests/test_pdf_freshness.py recomputes it: a source edited without a
rebuild (a changed paragraph in make_shadow_guide(), a Playbook edit, a test
count bump) leaves the stamp stale and fails the suite.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    "scripts/generate_pdfs.py",
    "scripts/build_playbook_pdf.py",
    "docs/NHID-Clinical-Playbook.md",
)
STAMP = ROOT / "specs" / "pdf-sources.sha256"


def fingerprint() -> str:
    digest = hashlib.sha256()
    for rel in SOURCES:
        digest.update(rel.encode())
        # Line endings normalised, so a Windows checkout computes the same value.
        digest.update((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def write_stamp() -> str:
    STAMP.write_text(fingerprint() + "\n", encoding="ascii")
    return STAMP.relative_to(ROOT).as_posix()
