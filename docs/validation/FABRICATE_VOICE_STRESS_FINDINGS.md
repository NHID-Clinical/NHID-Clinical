# Fabricate voice-stress corpus — unblocked, measured, reported

**Status:** research measurement · **Added:** 2026-10-14 · CC BY 4.0

> The voice-stress export (`fixtures/voice-stress/`, 300 scenarios / 1,582
> turns) was staged in the repository but **unrunnable**: the adapter function
> `convert_voice_stress` existed, yet no runner routed to it, so the corpus had
> never been scored. This unblocks it with the smallest honest change, runs it,
> and reports the measured result. **The pinned CSV-550 baseline in
> `scripts/check_baseline.py` was not touched**, and no expected outcome was
> weakened to raise a rate.
>
> This is a measurement of one hand-authored corpus. It is not a conformance
> claim, a certification, an assurance score, or independent validation.

---

## What was blocking it

`scripts/confusion_matrix.py` could load the two-table CSV-550 export
(`convert_csv`) and the JSONL export (`convert_jsonl`), but not the later
voice-stress two-table export, whose columns are named differently
(`expected_*_violation`, `scenario_id` as the grouping key). The translator for
that shape — `convert_voice_stress` — already lived in
`adapters/fabricate_adapter.py`, but nothing called it. The corpus was staged
and inert.

Two small, scoped changes unblock it:

1. `scripts/confusion_matrix.py` gains a `--voice-stress <scenarios.csv>
   <turns.csv>` route that calls `convert_voice_stress`. The default CSV-550 and
   JSONL paths are unchanged.
2. `adapters/fabricate_adapter._voice_stress_row_to_legacy` maps this export's
   `is_negative_control` flag onto the `scenario_type == "compliant"` value that
   `confusion_matrix.compute` measures false positives over. Without it the FP
   denominator was zero (the export marks its clean population by a flag, not by
   that literal string) and a false positive on a clean scenario could not
   surface. This is scoped to the voice-stress translator; the CSV-550 path
   (`convert_csv`) never calls it, so the pinned baseline is unaffected.

Neither change edits `scripts/check_baseline.py` or its `EXPECTED` table.

## Measured result (2026-10-14)

Voice-stress corpus, 300 scenarios, **95 negative controls** (the false-positive
population). ATR-01 is untestable in transcript replay, so its 26 expectations
are dropped and reported, exactly as for CSV-550.

| control | detection | rate | FP / clean | FP rate |
| :------ | :-------- | ---: | :--------- | ------: |
| IDG-01  | 65/65     | 100.0% | 0/95 | 0.0% |
| PDX-01  | 8/8       | 100.0% | 0/95 | 0.0% |
| DBC-01  | 0/28      | **0.0%** | 0/95 | 0.0% |
| EIT-01  | 12/25     | 48.0% | 6/95 | 6.3% |

Reproduce:

```
python scripts/confusion_matrix.py --voice-stress \
    fixtures/voice-stress/scenarios.csv fixtures/voice-stress/turns.csv
```

## Before / after — the CSV-550 baseline did not move

The point of "before/after" here is that unblocking a second corpus must not
disturb the first. It did not:

```
python scripts/check_baseline.py
# BASELINE PASS: IDG-01 70/70 (0 FP), PDX-01 41/41 (0 FP),
#                DBC-01 183/200 (5 FP), EIT-01 169/171 (5 FP)
```

The engine was not changed, so detection on CSV-550 is byte-for-byte what it
was. The voice-stress numbers are a *new, separate* measurement, not a revision
of the baseline.

## The DBC-01 result: 0/28 — the open scope question, again

**DBC-01 detects none of the 28 voice-stress scenarios that target it.** This is
the same gap the synthetic v2 corpus isolates
([`EVALUATION_CORPUS_V2_FINDINGS.md`](EVALUATION_CORPUS_V2_FINDINGS.md)): DBC-01
as published does not detect the deceptive-persona / disclosure-contradiction
patterns these scenarios are built from, and the fabricate adapter correctly
extracts only *voice/signal* artifacts (synthetic breathing, synthetic typing)
into `deceptive_artifact_flags`, not text personas. A 0/28 here is honest, not a
regression:

- It is **not** masked. The 28 scenarios keep their DBC-01 expectation; they are
  reported as misses, not dropped.
- It is the **same specification decision** the maintainer owns — extend DBC-01
  to text/cross-turn personas, route these to IDG-01, or document the boundary —
  and it is surfaced here, not decided.
- Several of these scenarios also reference *"NHID-Auth (proposed, not an
  existing control)"* in `expected_control`; a proposed control cannot detect
  anything until it exists. Those rows are scored against the real controls only.

Until that decision is made, the voice-stress DBC-01 figure stays 0/28 and is
reported as such. It must **not** be pinned into `check_baseline.py` or quoted
as a headline detection rate.

## The EIT-01 result: 48% detection, 6 false positives

EIT-01 detects 12 of 25 and fires on 6 of 95 negative controls (6.3% FP). The
misses and false positives are a transcript-text heuristic's inherent two-sided
error on the acoustic-stress phrasings this corpus introduces (ASR-style
transcription noise, disfluency, interruption). This is a reviewable signal for
tuning the escalation-honor lexicon, tied to the same honest-measurement
discipline — not a number to pin or to tune the corpus against.

## Claim boundary

These are transcript-replay measurements on a synthetic corpus. They are
**tier 3** on the evidence ladder
([`evidence-provenance-matrix.md`](evidence-provenance-matrix.md)): richer than
the small hand-authored sets, but still synthetic text, scored by the same
engine. They do not establish acoustic robustness, real-caller behaviour,
deployment, or certification.

**Recorded non-actions:** the engine was not changed; the CSV-550 pinned
baseline was not edited; no expected outcome was weakened; the DBC-01 scope
decision is left to the maintainer; the voice-stress numbers are not pinned as a
CI baseline, because doing so before the DBC-01 decision would freeze a known
gap as if it were intended.
