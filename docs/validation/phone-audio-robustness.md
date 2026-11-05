# Phone-audio robustness: what a phone line and a transcriber do to detection

**Status:** research measurement, tooling built, **not yet measured with real speech engines** ·
**Added:** 2026-11-05 · CC BY 4.0

Every detection figure the project publishes is measured on text. The Fabricate CSV-550
corpus is authored text, and so is the voice-stress corpus, including its "ASR noise".
A real call reaches the engine only after two things NHID-Clinical does not control:
- a phone channel (300–3400 Hz, 8 kHz, μ-law, as on G.711 lines);
- a speech-to-text system.

`nhid audio-robustness` measures that gap.

```
authored turn text ─TTS─▶ audio ─phone channel─▶ 8 kHz μ-law ─ASR─▶ transcript
      │                                                              │
      └──── adapter + engine + confusion matrix ─┬─ same code ───────┘
                                                 ▼
             detection and false positives: authored text vs phone transcript
```

**The channel is an approximation.** It uses the continuous μ-law curve, not G.711's
segmented encoder bit for bit. It resamples by linear interpolation after 3400 Hz
low-pass filtering. It is pure Python, so it runs the same on every CI runner. Reports
say "μ-law", not "G.711".

**Why this scorer.** The Tier 0 pilot scorer (`src/pilot_measure.measure_records`) takes
disclosure timing from fields the capture source supplies, not from the words. Transcription
errors could therefore never change its result. This measurement needs a scorer that reads
the words, so it uses the corpus adapter and confusion matrix that produced the voice-stress
findings. It reads only the voice-stress corpus. The Fabricate CSV-550 corpus is the pinned
baseline (`scripts/check_baseline.py`) and is kept off this path.

Both columns go through the same adapter conversion (`adapters/fabricate_adapter.py`) and
the same confusion matrix (`scripts/confusion_matrix.py`), so they differ only by what the
audio path did to the words. The identity transcriber is the control: with it,
the two columns are identical (`tests/test_phone_audio.py`).

## Run it

The speech engines are not dependencies of the project. Install them on the machine that
runs the measurement:

```bash
pip install -e .                      # from a checkout
sudo apt install espeak-ng            # TTS (or: pip install piper-tts, and a voice .onnx)
pip install faster-whisper            # ASR; downloads the model on first run
nhid audio-robustness --tts espeak --asr faster-whisper --whisper-model small \
    --out phone-audio-results/
```

Options:
- `--noise 0.02` adds white noise on the line.
- `--limit N` runs only the first N of the 300 scenarios.
- `--tts piper --piper-model voice.onnx` uses a more natural voice.

Every run writes `report.md` and `results.json`, naming:
- the corpus, scenario count and backends, with package and engine versions and the
  Piper voice file;
- the word error rate;
- each control's detections and false positives, with their denominators.

`--tts stub` and `--asr stub|identity` exercise the plumbing with no speech at all. Their
reports are marked **plumbing check only**, and their figures are never quoted.

## What it measures, and what it cannot

- It measures **how much transcription errors on synthetic speech over a simulated phone
  line move the controls**, for one TTS voice and one transcriber.
- It does not measure real callers, real payer phone systems or another transcriber.
  The evidence tier is **3** (synthetic corpus, synthetic speech), not 4: see
  [`evidence-provenance-matrix.md`](evidence-provenance-matrix.md). Consented human audio
  (tier 4) is the [`volunteer-call-protocol.md`](volunteer-call-protocol.md) path.
- **DBC-01 stage directions do not survive speech.**
  - The corpus marks some deceptive sounds as text (`*inhales*`). A voice does not say
    them, so `speakable()` drops them, and the report counts how many turns carried
    one.
  - The voice-stress DBC-01 scenarios also turn on a few exact phrases ("As the
    specialist handling your case…"). Each of those phrases is shared by every scenario
    in its group, so one mistranscription can lose the whole group at once.
  - That correlated loss is a finding about phrase heuristics, not noise to tune away.
- It does not analyse the audio signal. No acoustic deepfake detection exists in this
  repository ([`DBC-01-SCOPE-AND-LIMITATIONS.md`](DBC-01-SCOPE-AND-LIMITATIONS.md)).

## Results

| Run | TTS | ASR | Channel | WER | Status |
| :-- | :-- | :-- | :-- | :-- | :-- |
| — | espeak-ng | faster-whisper small | 300–3400 Hz, 8 kHz, μ-law | — | **Not yet measured** |

Add a row only from a `results.json` produced by a real-engine run. Give the date and
commit, and attach the report.
