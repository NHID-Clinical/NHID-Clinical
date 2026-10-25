"""The Downloads page shows pages, size and date read from the PDFs it ships.

specs/index.html keeps a placeholder per document because the maintained PDFs
regenerate whenever a published count moves; `scripts/fill_download_meta.py`
fills the placeholders inside the built `_site/` copy. These tests run the
filler on a temporary copy of the page and the PDFs, and hold the two things
that matter: every card ends up with real metadata, and every card points at
a PDF that exists.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "fill_download_meta.py"


def _load():
    spec = importlib.util.spec_from_file_location("fill_download_meta", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _site(tmp_path: Path) -> Path:
    (tmp_path / "specs" / "archive").mkdir(parents=True)
    shutil.copy(ROOT / "specs" / "index.html", tmp_path / "specs" / "index.html")
    for pdf in (ROOT / "specs").glob("*.pdf"):
        shutil.copy(pdf, tmp_path / "specs" / pdf.name)
    for pdf in (ROOT / "specs" / "archive").glob("*.pdf"):
        shutil.copy(pdf, tmp_path / "specs" / "archive" / pdf.name)
    return tmp_path


def test_every_card_points_at_a_pdf_that_exists():
    html = (ROOT / "specs" / "index.html").read_text(encoding="utf-8")
    refs = set(re.findall(r'data-pdf="([^"]+)"', html))
    assert len(refs) == 8
    for rel in refs:
        assert (ROOT / rel.lstrip("/")).is_file(), f"{rel} is not in the repository"
    on_disk = {f"/specs/{p.name}" for p in (ROOT / "specs").glob("*.pdf")} | {f"/specs/archive/{p.name}" for p in (ROOT / "specs" / "archive").glob("*.pdf")}
    assert refs == on_disk, f"cards and PDFs differ: {refs ^ on_disk}"


def test_the_filler_writes_pages_size_and_date(tmp_path):
    site = _site(tmp_path)
    filled = _load().fill(site)
    assert filled == 8
    html = (site / "specs" / "index.html").read_text(encoding="utf-8")
    metas = re.findall(r'<span class="pdf-meta" data-pdf="[^"]+">([^<]*)</span>', html)
    assert len(metas) == 8
    for meta in metas:
        assert re.fullmatch(r"\d+ pages? · [\d.]+ (KB|MB) · \d{1,2} \w{3} \d{4}", meta), meta


def test_the_repository_page_keeps_placeholders():
    """The build fills them; the committed page must not carry a stale copy."""
    html = (ROOT / "specs" / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'<span class="pdf-meta" data-pdf="[^"]+">PDF</span>', html).__len__() == 8


def test_a_missing_pdf_fails_the_build(tmp_path):
    import pytest
    site = _site(tmp_path)
    (site / "specs" / "NHID-Clinical-Playbook.pdf").unlink()
    with pytest.raises(SystemExit):
        _load().fill(site)
