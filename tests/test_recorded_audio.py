"""Consented recordings (tier 4): `nhid audio-robustness --audio-dir DIR`.

docs/validation/volunteer-call-protocol.md. Volunteers act out voice-stress
scenarios on a real phone line with fictional identities; each spoken turn is
a WAV clip. A `manifest.json` beside the clips maps each clip to its corpus
turn and records consent. The clips are transcribed with the same Transcriber
and scored with the same adapter and confusion matrix as the synthetic run.

What must hold whatever the transcriber:
  * no clip is used without `consent: true`, and the whole run is refused, not
    just the clip;
  * a clip outside the folder is refused;
  * a scenario is scored only when every spoken turn has a clip;
  * nothing is written but aggregate figures: no audio, no transcripts;
  * the identity transcriber reproduces the authored-text figures exactly.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import cli  # noqa: E402
from src import phone_audio as pa  # noqa: E402

TURNS = pa.VOICE_STRESS / "turns.csv"


def _turns(scenario_id):
    with open(TURNS, newline="", encoding="utf-8") as f:
        return sorted((r for r in csv.DictReader(f) if r["scenario_id"] == scenario_id),
                      key=lambda r: int(r["turn_index"]))


def _record(tmp_path, scenario_ids, *, consent=True, skip_turn=None, file_for=None):
    rec = tmp_path / "recordings"
    rec.mkdir(exist_ok=True)
    entries = []
    for sid in scenario_ids:
        for t in _turns(sid):
            if not pa.speakable(t["text"]) or (sid, int(t["turn_index"])) == skip_turn:
                continue
            name = f"vol_{sid}_{t['turn_index']}.wav"
            pa.write_wav(rec / name, [0.0] * 800, pa.PHONE_RATE)
            entries.append({"scenario_id": sid, "turn_index": int(t["turn_index"]),
                            "file": file_for or name, "consent": consent})
    (rec / "manifest.json").write_text(json.dumps({
        "protocol": "docs/validation/volunteer-call-protocol.md", "recordings": entries}))
    return rec


SCENARIOS = ["NHID-VSTRESS-00001", "NHID-VSTRESS-00002"]


def test_identity_transcription_reproduces_the_authored_figures(tmp_path):
    rec = _record(tmp_path, SCENARIOS)
    r = pa.run_recordings(audio_dir=rec, asr=pa.IdentityTranscriber(), out_dir=tmp_path / "out")
    assert r["scenarios"] == 2
    assert r["word_error_rate"] == 0
    assert r["phone_transcript"] == r["authored_text"]


def test_a_clip_without_consent_refuses_the_whole_run(tmp_path):
    rec = _record(tmp_path, SCENARIOS, consent=False)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="consent"):
        pa.run_recordings(audio_dir=rec, asr=pa.IdentityTranscriber(), out_dir=out)
    assert not out.exists()


def test_consent_must_be_literally_true(tmp_path):
    rec = _record(tmp_path, SCENARIOS, consent="yes")
    with pytest.raises(ValueError, match="consent"):
        pa.run_recordings(audio_dir=rec, asr=pa.IdentityTranscriber(), out_dir=tmp_path / "out")


def test_a_clip_outside_the_folder_is_refused(tmp_path):
    (tmp_path / "elsewhere.wav").write_bytes(b"")
    rec = _record(tmp_path, SCENARIOS[:1], file_for="../elsewhere.wav")
    with pytest.raises(ValueError, match="outside"):
        pa.run_recordings(audio_dir=rec, asr=pa.IdentityTranscriber(), out_dir=tmp_path / "out")


def test_a_scenario_missing_a_spoken_turn_is_not_scored(tmp_path):
    rec = _record(tmp_path, SCENARIOS, skip_turn=(SCENARIOS[1], 0))
    r = pa.run_recordings(audio_dir=rec, asr=pa.IdentityTranscriber(), out_dir=tmp_path / "out")
    assert r["scenarios"] == 1
    assert r["incomplete_scenarios"] == [SCENARIOS[1]]


def test_an_unknown_turn_is_refused(tmp_path):
    rec = _record(tmp_path, SCENARIOS[:1])
    m = json.loads((rec / "manifest.json").read_text())
    m["recordings"][0]["scenario_id"] = "NHID-VSTRESS-99999"
    (rec / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="not in the corpus"):
        pa.run_recordings(audio_dir=rec, asr=pa.IdentityTranscriber(), out_dir=tmp_path / "out")


def test_only_aggregates_are_written_and_the_label_is_tier_4(tmp_path):
    rec = _record(tmp_path, SCENARIOS)
    out = tmp_path / "out"
    r = pa.run_recordings(audio_dir=rec, asr=pa.IdentityTranscriber(), out_dir=out)
    assert sorted(p.name for p in out.iterdir()) == ["report.md", "results.json"]
    assert r["source"] == "scripted consented volunteers, fictional identities"
    assert r["evidence_tier"] == 4
    report = (out / "report.md").read_text()
    assert "scripted consented volunteers, fictional identities" in report
    first_turn = _turns(SCENARIOS[0])[0]["text"]
    assert first_turn not in (out / "results.json").read_text() + report


def test_the_cli_runs_recordings_and_refuses_without_consent(tmp_path, capsys):
    (tmp_path / "a").mkdir()
    ok = _record(tmp_path / "a", SCENARIOS)
    assert cli.main(["audio-robustness", "--audio-dir", str(ok), "--asr", "identity",
                     "--out", str(tmp_path / "out-a")]) == 0
    (tmp_path / "b").mkdir()
    refused = _record(tmp_path / "b", SCENARIOS, consent=False)
    assert cli.main(["audio-robustness", "--audio-dir", str(refused), "--asr", "identity",
                     "--out", str(tmp_path / "out-b")]) == 2
    assert "consent" in capsys.readouterr().err
