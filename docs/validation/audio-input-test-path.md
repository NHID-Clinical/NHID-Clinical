# Audio-Input Test Path — design, and the honest limits of what exists

**Status:** design + boundary statement · **Added:** 2026-10-14 · CC BY 4.0

> What the current "voice" testing actually is, what it is **not**, and the
> smallest feasible path to a *genuine* audio-input test — with the external
> dependencies named explicitly. **Nothing paid was run, no credentials were
> used, and no "successful live test" is claimed here.**

---

## What exists today (and must not be overstated)

`tests/elevenlabs_cts_runner.py` runs the conformance scenarios through the
**ElevenLabs Conversational AI simulation API** — structured, text-level
conversational turns. It is a useful conversational-control test, and it is
honest about its limits in one respect already: runs that fail on insufficient
credits are recorded as `NOT_EXECUTED`, never `FAIL`.

**It is not acoustic testing.** It does **not** establish:

- robustness to real recorded caller audio,
- ASR/transcription error behaviour,
- interruption or barge-in handling,
- overlapping-speech handling,
- background-noise robustness.

No artifact in this repository may describe the ElevenLabs runner as
acoustic/audio-robustness testing. It is text-level conversational control.

---

## The smallest genuine audio-input path

The goal is to feed **real or recorded audio** through a speech→text leg and
then score the resulting transcript with the *same* engine the synthetic corpus
uses, so audio results are directly comparable and land at **tier 4** in
[`evidence-provenance-matrix.md`](evidence-provenance-matrix.md).

```
  audio source ──▶ transcription ──▶ turn alignment ──▶ eval shape ──▶ evaluate_all()
  (wav / stream)    (ASR)             (speaker + time)   (scenario JSON)   (existing engine)
```

Design, smallest version first:

1. **`AudioSource`** — yields audio: a local WAV file (offline, no credential)
   or a telephony/stream leg (credentialed). The file source is enough to build
   and test everything downstream with **zero external dependency**.
2. **`Transcriber`** — an interface with two implementations:
   - `MockTranscriber` — reads a committed transcript sidecar next to a fixture
     WAV; deterministic, offline, used in CI.
   - `<Provider>Transcriber` — a real ASR provider (Deepgram, Whisper API, the
     telephony vendor's STT). **Needs a credential; not built live here.**
3. **`TurnAligner`** — converts timestamped ASR output into the corpus turn
   shape (speaker, text, `time_in_call_secs`), reusing the same field names the
   `fabricate_adapter` and corpus already use so nothing downstream changes.
4. **`evaluate_all()`** — unchanged. The whole point is that audio reaches the
   existing engine as an ordinary eval-shaped scenario.

Everything except step 2's real provider and step 1's live stream is
**offline-testable today** with a committed fixture WAV + sidecar transcript.

## What must be built offline first (no credentials, no cost)

- The `AudioSource`/`Transcriber`/`TurnAligner` interfaces and the `Mock`
  implementations.
- A tiny committed fixture: one short synthetic WAV (or a silence/tone stub) and
  its hand-written transcript sidecar in the corpus scenario shape.
- Offline tests proving: a fixture WAV → mock transcript → aligned turns →
  `evaluate_all()` → the expected control outcome; and that a missing/garbled
  audio source yields `NOT_EXECUTED`/`not_evaluated`, never a fabricated pass.

This gives a complete, reviewable audio **path** with no external account.

## What needs a credential or external account (explicitly)

| Step | Needs | Not done here because |
| :-- | :-- | :-- |
| Real ASR | Deepgram / Whisper API key, **or** a local Whisper model + GPU | no credential; local Whisper is an option but not wired |
| Live telephony leg | Twilio/Telnyx/etc. number + credentials (and cost) | paid; not authorized |
| ElevenLabs beyond simulation | `ELEVENLABS_API_KEY` + credits | paid; already gated as `NOT_EXECUTED` |

Real recorded audio to transcribe can come from the consented-volunteer
protocol ([`volunteer-call-protocol.md`](volunteer-call-protocol.md)) or, for
pipeline prototyping only, the Synth-DoPaCo audio set
([`data-sources-inventory.md`](data-sources-inventory.md)) — with the standing
caveat that clinical doctor–patient audio does not validate authorization
behaviour.

## Claim boundary

Any result from this path is **tier 4** (or tier 5 if on a public audio
dataset): "scored on transcribed audio," labelled with its data classification,
denominator, and the limitation that transcription introduces its own errors
and that acted/third-party audio is not real healthcare traffic. It never
becomes evidence of deployment, certification, or healthcare use.

**Recorded non-actions:** no ASR credential used, no telephony leg opened, no
paid ElevenLabs run, no live audio captured, no cost incurred.
