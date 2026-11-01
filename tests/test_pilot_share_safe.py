"""
``nhid pilot --share-safe``: an evidence pack meant to leave the payer's machine.

Before: the pack named per-call files after the payer's own call ids, named the
capture file in the report, and nothing checked that transcript text or
identifiers stayed out of it. Now call ids are pseudonymised, the pack is
scanned in staging, and it is released only if the scan passes. A failed scan
leaves nothing at ``--out`` and never prints the matched text.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import src.pilot_report as pilot_report  # noqa: E402
from src import cli  # noqa: E402
from src import pilot_share_safe as safe  # noqa: E402
from src.pilot_measure import demo_records  # noqa: E402

DEMO_IDS = {r["session_id"] for r in demo_records()}


def _run(out: Path, *extra: str) -> int:
    return cli.main(["pilot", "--demo", "--share-safe", "--out", str(out), *extra])


def _pack_text(out: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8")
                     for p in out.rglob("*") if p.suffix in {".md", ".json"})


def test_a_clean_run_releases_a_pack_with_no_ids_or_transcript(tmp_path):
    out = tmp_path / "pack"
    assert _run(out) == 0
    text = _pack_text(out)
    names = [p.relative_to(out).as_posix() for p in out.rglob("*")]
    for sid in DEMO_IDS:
        assert sid not in text and not any(sid in n for n in names)
    assert "MOCK-123456" not in text
    assert "calling on behalf of Riverbend Imaging" not in text
    assert safe.scan_pack(out, demo_records()) == []
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["scan"]["result"] == "passed"
    assert "not de-identification" in manifest["statement"]
    assert {f["path"] for f in manifest["files"]} >= {"pilot_report.md", "metrics.json"}


def test_the_lookup_table_and_key_stay_outside_the_pack(tmp_path):
    out = tmp_path / "pack"
    assert _run(out) == 0
    local = tmp_path / "pack.local"
    assert (local / "session-map.csv").exists() and (local / "pseudonym.key").exists()
    assert not list(out.rglob("session-map.csv")) and not list(out.rglob("*.key"))
    rows = (local / "session-map.csv").read_text().splitlines()[1:]
    assert {row.split(",")[1] for row in rows} == DEMO_IDS


def test_the_report_does_not_name_the_capture_file(tmp_path):
    capture = tmp_path / "member-4471-calls.jsonl"
    capture.write_text("\n".join(json.dumps(r) for r in demo_records()))
    out = tmp_path / "pack"
    assert cli.main(["pilot", str(capture), "--share-safe", "--out", str(out)]) == 0
    assert "member-4471" not in _pack_text(out)


@pytest.mark.parametrize("leak, category", [
    ("I am an automated system calling on behalf of Riverbend Imaging", "transcript text"),
    ("see call demo-late for details", "identifier from the input"),
    ("member MOCK-123456 was discussed", "identifier from the input"),
    ("ssn 123-45-6789", "ssn-like number"),
    ("born 04/12/1961", "slash-format date"),
    ("call back on (555) 201-3344", "phone number"),
    ("write to someone@example.org", "email address"),
])
def test_each_kind_of_leak_stops_the_release(tmp_path, monkeypatch, capsys, leak, category):
    real = pilot_report.generate_report
    monkeypatch.setattr(pilot_report, "generate_report",
                        lambda *a, **k: real(*a, **k) + f"\n\n{leak}\n")
    out = tmp_path / "pack"
    assert _run(out) == 1
    assert not out.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".nhid-pack-")]
    err = capsys.readouterr().err
    assert f"pilot_report.md" in err and category in err
    assert leak not in err


def test_pseudonyms_are_stable_with_a_key_file_and_differ_without(tmp_path):
    key = tmp_path / "pilot.key"
    key.write_text(os.urandom(32).hex())
    runs = []
    for name in ("a", "b"):
        assert _run(tmp_path / name, "--pseudonym-key-file", str(key)) == 0
        runs.append(sorted(p.name for p in (tmp_path / name / "per-call").iterdir()))
    assert runs[0] == runs[1]
    assert _run(tmp_path / "c") == 0
    assert sorted(p.name for p in (tmp_path / "c" / "per-call").iterdir()) != runs[0]


def test_a_bad_key_file_is_refused(tmp_path):
    key = tmp_path / "short.key"
    key.write_text("abcd")
    assert _run(tmp_path / "pack", "--pseudonym-key-file", str(key)) == 2


def test_a_non_empty_output_directory_is_refused(tmp_path):
    out = tmp_path / "pack"
    out.mkdir()
    (out / "old-raw-pack.json").write_text("{}")
    assert _run(out) == 2


def test_default_mode_is_unchanged(tmp_path):
    out = tmp_path / "plain"
    assert cli.main(["pilot", "--demo", "--out", str(out)]) == 0
    assert {p.stem for p in (out / "per-call").iterdir()} == DEMO_IDS
    assert not (out / "manifest.json").exists()


def test_the_offline_guard_covers_the_share_safe_module():
    guard = Path(__file__).resolve().parents[1] / "scripts" / "check_offline_kit.py"
    assert '"src/pilot_share_safe.py"' in guard.read_text()
