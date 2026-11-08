"""Phone-audio robustness: what a phone line and a transcriber do to detection.

Every published detection figure in this repository is measured on text: the
Fabricate CSV-550 corpus, and the voice-stress corpus, whose "ASR noise" is
itself authored text. A real call reaches the engine only after a phone channel
(300-3400 Hz, 8 kHz, mu-law) and a speech-to-text system the project does
not control. This module measures that gap on the voice-stress corpus:

    authored turn text --TTS--> audio --phone channel--> 8 kHz mu-law
        --ASR--> transcribed text --> the same adapter and engine as before

and reports, per control, detection and false positives on the authored text
next to the same figures on the transcribed text, with the word error rate and
the backends named. Both columns go through the same
adapter conversion (``adapters.fabricate_adapter``) and confusion matrix
(``scripts.confusion_matrix.compute``), so they differ only by what the audio
path did to the words.

What it is not
--------------
* A headline rate. Like the voice-stress figures, it is a separate research
  measurement, reported with its corpus, backends and denominators.
* A measure of real callers. Synthetic voices are not people; one transcriber
  is not every payer's.
* Acoustic detection. DBC-01's stage-direction markers (``*inhales*``) are text
  conventions; spoken aloud they vanish or become words, and the report counts
  that loss rather than hiding it. Nothing here analyses the audio signal.

Backends
--------
The phone channel is pure standard library (no ffmpeg, no numpy), so it runs
the same on every CI runner. Speech backends are optional and external:

* TTS: ``espeak`` (the ``espeak-ng`` CLI) or ``piper`` (the ``piper`` CLI and a
  voice model file).
* ASR: ``faster-whisper`` (``pip install faster-whisper``; downloads a model).
* ``stub`` / ``identity``: deterministic stand-ins with no speech at all, for
  tests and for checking the plumbing. They never produce a published figure.
"""
from __future__ import annotations

import array
import csv
import hashlib
import json
import math
import random
import re
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Sequence

PHONE_RATE = 8000
LOW_HZ = 300.0
HIGH_HZ = 3400.0

ROOT = Path(__file__).resolve().parents[1]
VOICE_STRESS = ROOT / "fixtures" / "voice-stress"

_STAGE_DIRECTION = re.compile(r"\*[^*]{1,40}\*")
_WORD = re.compile(r"[a-z0-9']+")


# ── text helpers ─────────────────────────────────────────────────────────────

def speakable(text: str) -> str:
    """What a voice actually says: stage directions like ``*inhales*`` are not words."""
    return re.sub(r"\s+", " ", _STAGE_DIRECTION.sub(" ", text or "")).strip()


def words(text: str) -> List[str]:
    return _WORD.findall((text or "").lower())


def word_errors(reference: str, hypothesis: str) -> tuple[int, int]:
    """(word-level edit distance, reference length), for WER = errors / length."""
    ref, hyp = words(reference), words(hypothesis)
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1], len(ref)


# ── audio I/O and the phone channel ──────────────────────────────────────────

def read_wav(path: Path) -> tuple[List[float], int]:
    """Mono float samples in [-1, 1] and the sample rate. 16-bit PCM only."""
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"{path}: expected 16-bit PCM, got {8 * w.getsampwidth()}-bit")
        channels, rate = w.getnchannels(), w.getframerate()
        data = array.array("h", w.readframes(w.getnframes()))
    if channels > 1:
        data = array.array("h", (int(sum(data[i:i + channels]) / channels)
                                 for i in range(0, len(data), channels)))
    return [s / 32768.0 for s in data], rate


def write_wav(path: Path, samples: Sequence[float], rate: int) -> None:
    pcm = array.array("h", (max(-32768, min(32767, int(round(s * 32767)))) for s in samples))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def _biquad(samples: Sequence[float], rate: int, freq: float, kind: str, q: float = 0.7071) -> List[float]:
    """RBJ-cookbook second-order low- or high-pass."""
    w0 = 2 * math.pi * freq / rate
    alpha, cos_w0 = math.sin(w0) / (2 * q), math.cos(w0)
    if kind == "low":
        b0, b1, b2 = (1 - cos_w0) / 2, 1 - cos_w0, (1 - cos_w0) / 2
    else:
        b0, b1, b2 = (1 + cos_w0) / 2, -(1 + cos_w0), (1 + cos_w0) / 2
    a0, a1, a2 = 1 + alpha, -2 * cos_w0, 1 - alpha
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    out, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
    for x in samples:
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out.append(y)
        x2, x1, y2, y1 = x1, x, y1, y
    return out


def _resample(samples: Sequence[float], src: int, dst: int) -> List[float]:
    if src == dst or not samples:
        return list(samples)
    n = max(1, int(len(samples) * dst / src))
    step, last = src / dst, len(samples) - 1
    out = []
    for i in range(n):
        pos = i * step
        j = min(int(pos), last)
        frac = pos - j
        nxt = samples[min(j + 1, last)]
        out.append(samples[j] * (1 - frac) + nxt * frac)
    return out


_MU = 255.0


def mulaw_encode(x: float) -> int:
    """Mu-law: one sample in [-1, 1] to an 8-bit code.

    The continuous mu-law curve (mu = 255), which approximates G.711's
    segmented encoder rather than reproducing it bit for bit; reports say
    "mu-law", never "G.711", for that reason."""
    x = max(-1.0, min(1.0, x))
    y = math.copysign(math.log1p(_MU * abs(x)) / math.log1p(_MU), x)
    return int(round((y + 1) / 2 * 255))


def mulaw_decode(code: int) -> float:
    y = code / 255 * 2 - 1
    return math.copysign((math.pow(1 + _MU, abs(y)) - 1) / _MU, y)


def phone_channel(samples: Sequence[float], rate: int, *, noise: float = 0.0,
                  seed: int = 0) -> List[float]:
    """Band-limit to 300-3400 Hz, resample to 8 kHz, add optional white noise,
    and round-trip through 8-bit mu-law. Returns 8 kHz samples."""
    shaped = _biquad(_biquad(samples, rate, HIGH_HZ, "low"), rate, LOW_HZ, "high")
    shaped = _resample(_biquad(shaped, rate, HIGH_HZ, "low"), rate, PHONE_RATE)
    if noise:
        rng = random.Random(seed)
        shaped = [s + rng.gauss(0.0, noise) for s in shaped]
    return [mulaw_decode(mulaw_encode(s)) for s in shaped]


def phone_channel_file(wav_in: Path, wav_out: Path, *, noise: float = 0.0, seed: int = 0) -> None:
    samples, rate = read_wav(wav_in)
    write_wav(wav_out, phone_channel(samples, rate, noise=noise, seed=seed), PHONE_RATE)


# ── backends ─────────────────────────────────────────────────────────────────

class Synthesizer(Protocol):
    name: str

    def synthesize(self, text: str, wav_out: Path) -> None: ...


class Transcriber(Protocol):
    name: str

    def transcribe(self, wav: Path, reference: str) -> str: ...


class StubSynthesizer:
    """A tone per word: real audio for the channel to process, but not speech."""

    name = "stub"

    def synthesize(self, text: str, wav_out: Path) -> None:
        rate, samples = 16000, []
        for i, _ in enumerate(words(text) or [""]):
            freq = 300 + 150 * (i % 8)
            samples += [0.3 * math.sin(2 * math.pi * freq * t / rate) for t in range(rate // 10)]
        write_wav(wav_out, samples, rate)


class IdentityTranscriber:
    """Returns the reference unchanged: the control that proves the plumbing is lossless."""

    name = "identity"

    def transcribe(self, wav: Path, reference: str) -> str:
        return reference


class StubTranscriber:
    """Seeded word-level substitutions and deletions at a set rate. Plumbing only."""

    name = "stub"
    _VOCAB = ("the", "a", "uh", "and", "to", "of", "it", "on")

    def __init__(self, error_rate: float = 0.1, seed: int = 0) -> None:
        self.error_rate, self.seed = error_rate, seed

    def transcribe(self, wav: Path, reference: str) -> str:
        digest = hashlib.sha256(f"{self.seed}:{reference}".encode()).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
        out = []
        for word in reference.split():
            roll = rng.random()
            if roll < self.error_rate / 2:
                continue
            out.append(rng.choice(self._VOCAB) if roll < self.error_rate else word)
        return " ".join(out)


class EspeakSynthesizer:
    name = "espeak-ng"

    def __init__(self, voice: str = "en-us") -> None:
        self.binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if not self.binary:
            raise RuntimeError("espeak-ng is not installed (apt install espeak-ng)")
        self.voice = voice

    def synthesize(self, text: str, wav_out: Path) -> None:
        subprocess.run([self.binary, "-v", self.voice, "-w", str(wav_out), text],
                       check=True, capture_output=True)


class PiperSynthesizer:
    name = "piper"

    def __init__(self, model: str) -> None:
        self.binary = shutil.which("piper")
        if not self.binary:
            raise RuntimeError("piper is not installed (pip install piper-tts)")
        if not model or not Path(model).is_file():
            raise RuntimeError("piper needs --piper-model pointing at a voice .onnx file")
        self.model = model

    def synthesize(self, text: str, wav_out: Path) -> None:
        subprocess.run([self.binary, "--model", self.model, "--output_file", str(wav_out)],
                       input=text.encode("utf-8"), check=True, capture_output=True)


class FasterWhisperTranscriber:
    def __init__(self, model_size: str = "small") -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed (pip install faster-whisper)") from exc
        self.name = f"faster-whisper:{model_size}"
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, wav: Path, reference: str) -> str:
        segments, _ = self._model.transcribe(str(wav), language="en", beam_size=1)
        return " ".join(s.text.strip() for s in segments).strip()


def make_synthesizer(name: str, piper_model: str = "") -> Synthesizer:
    if name == "stub":
        return StubSynthesizer()
    if name == "espeak":
        return EspeakSynthesizer()
    if name == "piper":
        return PiperSynthesizer(piper_model)
    raise ValueError(f"unknown TTS backend {name!r}")


def make_transcriber(name: str, *, error_rate: float = 0.1, seed: int = 0,
                     whisper_model: str = "small") -> Transcriber:
    if name == "identity":
        return IdentityTranscriber()
    if name == "stub":
        return StubTranscriber(error_rate, seed)
    if name == "faster-whisper":
        return FasterWhisperTranscriber(whisper_model)
    raise ValueError(f"unknown ASR backend {name!r}")


# ── the measurement ──────────────────────────────────────────────────────────

@dataclass
class TurnResult:
    reference: str
    spoken: str
    transcript: str
    errors: int
    length: int
    had_stage_direction: bool


def _transcribe_turn(text: str, tts: Synthesizer, asr: Transcriber, work: Path,
                     noise: float, seed: int, cache: Dict[str, TurnResult]) -> TurnResult:
    if text in cache:
        return cache[text]
    spoken = speakable(text)
    if not spoken:
        transcript = ""
    else:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        raw, phone = work / f"{key}.wav", work / f"{key}.phone.wav"
        tts.synthesize(spoken, raw)
        phone_channel_file(raw, phone, noise=noise, seed=seed)
        transcript = asr.transcribe(phone, spoken)
    errors, length = word_errors(spoken, transcript)
    result = TurnResult(text, spoken, transcript, errors, length, spoken != (text or "").strip())
    cache[text] = result
    return result


def load_scenarios(scenarios_csv: Path, limit: Optional[int] = None) -> List[dict]:
    with open(scenarios_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def run(*, tts: Synthesizer, asr: Transcriber, out_dir: Path,
        scenarios_csv: Path = VOICE_STRESS / "scenarios.csv",
        turns_csv: Path = VOICE_STRESS / "turns.csv",
        limit: Optional[int] = None, noise: float = 0.0, seed: int = 0) -> dict:
    """Measure detection on authored text and on phone-channel transcripts."""
    from adapters.fabricate_adapter import (
        _voice_stress_row_to_legacy,
        fabricate_conversation_to_eval_shape,
        load_voice_stress_turns,
    )
    from scripts.confusion_matrix import compute

    rows = load_scenarios(scenarios_csv, limit)
    turns_by = load_voice_stress_turns(str(turns_csv))
    out_dir.mkdir(parents=True, exist_ok=True)

    clean, heard, cache = [], [], {}
    with tempfile.TemporaryDirectory(prefix="nhid-phone-") as tmp:
        work = Path(tmp)
        for row in rows:
            raw = turns_by.get(row["id"], [])
            if not raw:
                continue
            legacy = _voice_stress_row_to_legacy(row)
            transcribed = []
            for turn in raw:
                result = _transcribe_turn(turn.get("text", ""), tts, asr, work, noise, seed, cache)
                transcribed.append({**turn, "text": result.transcript})
            clean.append(fabricate_conversation_to_eval_shape(legacy, raw))
            heard.append(fabricate_conversation_to_eval_shape(legacy, transcribed))

    errors = sum(r.errors for r in cache.values())
    length = sum(r.length for r in cache.values())
    results = {
        "kind": "phone-audio robustness (research measurement, not a headline rate)",
        "corpus": f"voice-stress ({scenarios_csv.relative_to(ROOT) if scenarios_csv.is_relative_to(ROOT) else scenarios_csv})",
        "scenarios": len(clean),
        "distinct_turn_texts": len(cache),
        "tts": tts.name,
        "asr": asr.name,
        "versions": _versions(tts, asr),
        "channel": "300-3400 Hz band-limit, 8 kHz (linear resampling), "
                   "8-bit continuous mu-law (approximates G.711)"
                   + (f", white noise sd={noise}" if noise else ""),
        "seed": seed,
        "word_error_rate": (errors / length) if length else None,
        "turns_with_stage_directions": sum(r.had_stage_direction for r in cache.values()),
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authored_text": compute(clean),
        "phone_transcript": compute(heard),
        "plumbing_only": tts.name == "stub" or asr.name in ("stub", "identity"),
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(render_report(results), encoding="utf-8")
    return results


RECORDED_SOURCE = "scripted consented volunteers, fictional identities"


class _Recorded:
    """Stands in for a synthesizer in the report: the speech was a person's."""
    name = "consented recording"


def _load_manifest(audio_dir: Path, known: Dict[tuple, dict]) -> Dict[tuple, Path]:
    """Read and check `manifest.json`. Raises ValueError, before anything is
    transcribed or written, if any clip lacks consent, lies outside the folder
    or names a turn the corpus does not have."""
    root = audio_dir.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"no manifest.json in {audio_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("recordings") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest.json has no recordings")
    clips: Dict[tuple, Path] = {}
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or e.get("consent") is not True:
            raise ValueError(f"recording {i} does not carry consent: true; refusing the whole run "
                             "(docs/validation/volunteer-call-protocol.md)")
        path = (root / str(e.get("file", ""))).resolve()
        if not path.is_relative_to(root) or path == root:
            raise ValueError(f"recording {i} points outside {audio_dir}")
        if not path.is_file():
            raise ValueError(f"recording {i}: {e.get('file')} does not exist")
        key = (str(e.get("scenario_id")), int(e.get("turn_index", -1)))
        if key not in known:
            raise ValueError(f"recording {i}: turn {key[1]} of {key[0]} is not in the corpus")
        clips[key] = path
    return clips


def run_recordings(*, audio_dir: Path, asr: Transcriber, out_dir: Path,
                   scenarios_csv: Path = VOICE_STRESS / "scenarios.csv",
                   turns_csv: Path = VOICE_STRESS / "turns.csv") -> dict:
    """Tier 4: score consented volunteer recordings of voice-stress scenarios.

    Each clip is one spoken turn, recorded over a real phone line by adult
    volunteers using fictional identities (volunteer-call-protocol.md).
    `manifest.json` maps clips to corpus turns (`scenario_id`, `turn_index`,
    `file`, `consent`). The clips are not passed through the simulated phone
    channel: they already crossed a real one. A scenario is scored only when
    every spoken turn has a clip. Only aggregate figures are written: no audio
    and no transcripts leave the run.
    """
    from adapters.fabricate_adapter import (
        _voice_stress_row_to_legacy,
        fabricate_conversation_to_eval_shape,
        load_voice_stress_turns,
    )
    from scripts.confusion_matrix import compute

    rows = {r["id"]: r for r in load_scenarios(scenarios_csv)}
    turns_by = load_voice_stress_turns(str(turns_csv))
    known = {(sid, int(t.get("turn_index", i))): t
             for sid, ts in turns_by.items() for i, t in enumerate(ts)}
    clips = _load_manifest(Path(audio_dir), known)

    clean, heard, incomplete = [], [], []
    errors = length = stage = distinct = 0
    for sid in sorted({k[0] for k in clips}):
        raw = turns_by.get(sid, [])
        spoken_turns = [(int(t.get("turn_index", i)), t) for i, t in enumerate(raw)]
        if any(speakable(t.get("text", "")) and (sid, idx) not in clips for idx, t in spoken_turns):
            incomplete.append(sid)
            continue
        transcribed = []
        for idx, t in spoken_turns:
            spoken = speakable(t.get("text", ""))
            text = asr.transcribe(clips[(sid, idx)], spoken) if spoken else ""
            e, n = word_errors(spoken, text)
            errors, length, distinct = errors + e, length + n, distinct + (1 if spoken else 0)
            stage += spoken != (t.get("text") or "").strip()
            transcribed.append({**t, "text": text})
        legacy = _voice_stress_row_to_legacy(rows[sid])
        clean.append(fabricate_conversation_to_eval_shape(legacy, raw))
        heard.append(fabricate_conversation_to_eval_shape(legacy, transcribed))

    results = {
        "kind": "phone-audio robustness, consented recordings (research measurement, not a headline rate)",
        "source": RECORDED_SOURCE,
        "evidence_tier": 4,
        "corpus": "voice-stress, scenarios acted from the script",
        "scenarios": len(clean),
        "incomplete_scenarios": incomplete,
        "distinct_turn_texts": distinct,
        "tts": _Recorded.name,
        "asr": asr.name,
        "versions": _versions(_Recorded(), asr),
        "channel": "a real phone line, as recorded (no simulated channel applied)",
        "seed": 0,
        "word_error_rate": (errors / length) if length else None,
        "turns_with_stage_directions": stage,
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authored_text": compute(clean),
        "phone_transcript": compute(heard),
        "plumbing_only": asr.name in ("stub", "identity"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(render_report(results), encoding="utf-8")
    return results


def _versions(tts: Synthesizer, asr: Transcriber) -> Dict[str, str]:
    """What produced the figures, so a result can be reproduced or compared."""
    import platform
    from importlib import metadata

    found = {"python": platform.python_version()}
    for package in ("faster-whisper", "ctranslate2", "piper-tts"):
        try:
            found[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            pass
    binary = getattr(tts, "binary", None)
    if binary and tts.name == "espeak-ng":
        try:
            out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10)
            found["espeak-ng"] = out.stdout.strip().split("\n")[0][:80]
        except (OSError, subprocess.SubprocessError):
            found["espeak-ng"] = "unknown"
    model = getattr(tts, "model", None)
    if model:
        found["piper voice"] = Path(model).name
    return found


def _cell(rate, num, den) -> str:
    return "n/a" if den == 0 else f"{num}/{den} ({rate:.1%})"


def render_report(results: dict) -> str:
    lines = [
        "# Phone-audio robustness",
        "",
        "Research measurement on the voice-stress corpus. **Not a headline detection rate**: "
        "synthetic voices are not real callers, and one transcriber is not every payer's.",
        "",
    ]
    if results.get("source"):
        lines += [f"> **Evidence tier {results['evidence_tier']}: {results['source']}.** "
                  "Not deployment or healthcare-use evidence. Scenarios not fully recorded "
                  f"and therefore not scored: {len(results.get('incomplete_scenarios', []))}.", ""]
    if results["plumbing_only"]:
        lines += ["> **Plumbing check only.** A stub or identity backend was used, so these "
                  "figures say nothing about real speech. Do not quote them.", ""]
    wer = results["word_error_rate"]
    lines += [
        f"- Corpus: {results['corpus']}, {results['scenarios']} scenarios, "
        f"{results['distinct_turn_texts']} distinct turn texts",
        f"- TTS: `{results['tts']}` · ASR: `{results['asr']}` · seed {results['seed']}",
        f"- Versions: {', '.join(f'{k} {v}' for k, v in results['versions'].items())}",
        f"- Channel: {results['channel']}",
        f"- Word error rate: {'n/a' if wer is None else f'{wer:.1%}'}",
        f"- Turns carrying text stage directions (e.g. `*inhales*`), which are not spoken: "
        f"{results['turns_with_stage_directions']}",
        f"- Measured: {results['measured_at']}",
        "",
        "| Control | Detected, authored text | Detected, phone transcript | "
        "False positives, authored | False positives, phone |",
        "| :-- | :-- | :-- | :-- | :-- |",
    ]
    by_clean = {c["control"]: c for c in results["authored_text"]["controls"]}
    for c in results["phone_transcript"]["controls"]:
        a = by_clean[c["control"]]
        lines.append(
            f"| {c['control']} | {_cell(a['detection_rate'], a['detected'], a['expected'])} | "
            f"{_cell(c['detection_rate'], c['detected'], c['expected'])} | "
            f"{_cell(a['fp_rate'], a['fp'], a['clean'])} | {_cell(c['fp_rate'], c['fp'], c['clean'])} |")
    lines += [
        "",
        "Detection is over scenarios that declare the control; false positives are over the "
        "corpus's negative controls (`scripts/confusion_matrix.py`). ATR-01 is untestable in "
        "transcript replay. DBC-01's stage-direction markers are text conventions, so their "
        "loss in speech is part of what this measures, not a defect to tune away.",
        "",
    ]
    return "\n".join(lines)
