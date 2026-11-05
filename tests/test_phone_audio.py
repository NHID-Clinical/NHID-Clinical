"""
Phone-audio robustness pipeline (src/phone_audio.py), tested offline.

The real measurement needs speech engines the CI runners do not have; these
tests pin the parts that must be right regardless of engine: the phone channel
really is 8 kHz mu-law band-limited audio, the identity backend reproduces the
authored-text figures exactly (so any difference in a real run comes from the
audio path, not the plumbing), and stub results are labelled as unquotable.
"""
from __future__ import annotations

import json
import math
import os
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import cli  # noqa: E402
from src import phone_audio as pa  # noqa: E402


def _tone(freq: float, rate: int = 16000, seconds: float = 0.25):
    return [0.5 * math.sin(2 * math.pi * freq * t / rate) for t in range(int(rate * seconds))]


def _rms(samples):
    return math.sqrt(sum(s * s for s in samples) / len(samples))


# ── the channel ──────────────────────────────────────────────────────────────

def test_the_channel_outputs_8khz_mono_16bit(tmp_path):
    src, out = tmp_path / "in.wav", tmp_path / "out.wav"
    pa.write_wav(src, _tone(1000), 16000)
    pa.phone_channel_file(src, out)
    with wave.open(str(out), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (8000, 1, 2)
        assert abs(w.getnframes() - 2000) <= 1


def test_the_channel_passes_voice_band_and_cuts_outside_it():
    voice = _rms(pa.phone_channel(_tone(1000), 16000)[400:])
    low = _rms(pa.phone_channel(_tone(60), 16000)[400:])
    high = _rms(pa.phone_channel(_tone(6000), 16000)[400:])
    assert voice > 0.25
    assert low < voice / 4 and high < voice / 4


def test_mulaw_round_trip_is_lossy_but_close():
    for x in (-0.9, -0.1, -0.001, 0.0, 0.002, 0.3, 0.95):
        y = pa.mulaw_decode(pa.mulaw_encode(x))
        assert abs(y - x) <= max(0.002, 0.05 * abs(x))
    assert len({pa.mulaw_encode(i / 1000) for i in range(-1000, 1001)}) <= 256


def test_noise_is_seeded():
    tone = _tone(800)
    assert pa.phone_channel(tone, 16000, noise=0.05, seed=1) == pa.phone_channel(tone, 16000, noise=0.05, seed=1)
    assert pa.phone_channel(tone, 16000, noise=0.05, seed=1) != pa.phone_channel(tone, 16000, noise=0.05, seed=2)


# ── text helpers and backends ────────────────────────────────────────────────

def test_stage_directions_are_not_spoken():
    assert pa.speakable("Sure *inhales* let me check *typing* that.") == "Sure let me check that."


def test_word_error_rate():
    assert pa.word_errors("the claim is approved", "the claim is approved") == (0, 4)
    assert pa.word_errors("the claim is approved", "a claim approved") == (2, 4)


def test_the_stub_transcriber_is_deterministic_per_seed():
    text = "this is an automated assistant calling about a prior authorization request"
    a, b = pa.StubTranscriber(0.3, seed=1), pa.StubTranscriber(0.3, seed=2)
    assert a.transcribe(Path("x"), text) == a.transcribe(Path("y"), text)
    assert a.transcribe(Path("x"), text) != b.transcribe(Path("x"), text)


def test_missing_engines_fail_with_a_message(monkeypatch):
    monkeypatch.setattr(pa.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="espeak-ng is not installed"):
        pa.make_synthesizer("espeak")
    assert cli.main(["audio-robustness", "--tts", "espeak", "--asr", "identity"]) == 2


# ── the measurement ──────────────────────────────────────────────────────────

def test_the_identity_backend_reproduces_the_authored_text_figures(tmp_path):
    """The control: with a lossless transcriber the two columns must agree, so a
    difference in a real run is the audio path's doing, not the pipeline's."""
    results = pa.run(tts=pa.StubSynthesizer(), asr=pa.IdentityTranscriber(),
                     out_dir=tmp_path, limit=40)
    assert results["word_error_rate"] == 0
    assert results["authored_text"] == results["phone_transcript"]


def test_transcription_errors_reach_the_engine(tmp_path):
    results = pa.run(tts=pa.StubSynthesizer(), asr=pa.StubTranscriber(0.6, seed=3),
                     out_dir=tmp_path, limit=40)
    assert results["word_error_rate"] > 0.3
    assert results["authored_text"] != results["phone_transcript"]


def test_stub_runs_are_labelled_as_plumbing_and_never_quotable(tmp_path):
    assert cli.main(["audio-robustness", "--tts", "stub", "--asr", "stub", "--limit", "5",
                     "--out", str(tmp_path)]) == 0
    results = json.loads((tmp_path / "results.json").read_text())
    report = (tmp_path / "report.md").read_text()
    assert results["plumbing_only"] is True
    assert "Plumbing check only" in report and "Not a headline detection rate" in report
    assert results["corpus"].startswith("voice-stress") and results["scenarios"] == 5


def test_the_measurement_reads_the_voice_stress_corpus_not_the_pinned_one():
    """The pinned baseline (scripts/check_baseline.py) is the CSV-550 corpus;
    this measurement's default inputs are the voice-stress fixtures."""
    import inspect
    defaults = inspect.signature(pa.run).parameters
    assert defaults["scenarios_csv"].default == pa.VOICE_STRESS / "scenarios.csv"
    assert defaults["turns_csv"].default == pa.VOICE_STRESS / "turns.csv"
    assert pa.VOICE_STRESS.name == "voice-stress"
