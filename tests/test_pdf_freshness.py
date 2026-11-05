"""The published PDFs were rebuilt after their sources last changed.

scripts/generate_pdfs.py stamps specs/pdf-sources.sha256 with a fingerprint of
its own text and the Playbook source. Editing either without rebuilding leaves
the stamp stale. Fix: python scripts/generate_pdfs.py, then
git add -f specs/*.pdf specs/pdf-sources.sha256.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pdf_sources import STAMP, fingerprint  # noqa: E402


def test_the_pdfs_were_rebuilt_after_their_sources_changed():
    assert STAMP.exists(), "run python scripts/generate_pdfs.py to create the stamp"
    assert STAMP.read_text(encoding="ascii").strip() == fingerprint(), (
        "a PDF source changed but the PDFs were not rebuilt: "
        "python scripts/generate_pdfs.py && git add -f specs/*.pdf specs/pdf-sources.sha256"
    )
