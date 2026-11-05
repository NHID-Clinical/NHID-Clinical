"""Every public fact in docs/agents/surfaces.json is on every surface that must state it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_surfaces  # noqa: E402


def test_every_public_fact_reaches_every_surface():
    found = check_surfaces.problems()
    assert not found, "\n".join(found)


def test_the_check_notices_a_missing_fact(tmp_path, monkeypatch):
    page = tmp_path / "page.html"
    page.write_text("nothing here", encoding="utf-8")
    manifest = tmp_path / "surfaces.json"
    manifest.write_text('{"facts": [{"id": "x", "fact": "f", "must_contain": {"page.html": ["share-safe"]},'
                        ' "must_not_contain": {"page.html": ["nothing"]}}]}', encoding="utf-8")
    monkeypatch.setattr(check_surfaces, "ROOT", tmp_path)
    monkeypatch.setattr(check_surfaces, "MANIFEST", manifest)
    found = check_surfaces.problems()
    assert any("missing 'share-safe'" in f for f in found)
    assert any("still says 'nothing'" in f for f in found)
