# NHID-Clinical Tonic Corpus Evaluation Summary — RETRACTED

**Original date**: 2026-08-11 · **Retracted**: 2026-10-21 · CC BY 4.0

> **This document is withdrawn in full. Do not cite any figure that was in it.**
>
> It reported a per-control evaluation of a "Tonic Fabricate Synthetic
> Evaluation" corpus of 150 sessions / 1,227 turns, with detection rates and
> accuracies at or near **100%** and false-positive rates at **0%** across
> IDG-01, PDX-01, DBC-01, EIT-01 and ATR-01.

## Why it is retracted

1. **Nothing can reproduce it.** The figures came from
   `corpus_evaluation_output/corpus_metrics.json`, written by
   `scripts/evaluate_tonic_corpus.py`, which hardcoded its input to a path
   inside a single ephemeral session's upload directory
   (`/root/.claude/uploads/<session-id>/…nhid_corpus_flat.csv`). That file does
   not exist and was **never tracked in git**, so the corpus was never available
   to anyone — including the maintainer. The measurement cannot be re-run,
   checked, or disputed.

2. **The outputs were committed anyway**, so unreproducible numbers shipped with
   the repository and were then quoted as per-control evidence in
   `docs/CONTROL_DECISION_TABLE.md`. Those files are now deleted and the
   directory is gitignored.

3. **The figures contradict every reproducible measurement of the same engine.**
   A DBC-01 at "100% accuracy, 0% false positives" cannot coexist with the
   CI-gated Fabricate result of **183/200 (91.5%) with 5 false positives**, or
   with **0/28** on the voice-stress corpus. The same applies to EIT-01, which
   measures 169/171 on Fabricate and **12/25 with 6 false positives** on
   voice-stress.

A measurement that no artifact reproduces is not evidence, however carefully it
was computed at the time. This is the same failure as §7.1a of the archive
(retracted in place) and `docs/pilot-kit/pilot_evidence.json` (deleted rather
than refreshed).

## Where the reproducible figures live

| Corpus | Size | Command | Reported in |
| :--- | :--- | :--- | :--- |
| Fabricate (CSV-550) | 550 conversations, 127 compliant | `python scripts/check_baseline.py` | [`../evidence-pack.html`](../evidence-pack.html), [`CONTROL_DECISION_TABLE.md`](CONTROL_DECISION_TABLE.md) |
| Voice-stress | 300 scenarios, 95 negative controls | `python scripts/confusion_matrix.py --voice-stress fixtures/voice-stress/scenarios.csv fixtures/voice-stress/turns.csv` | [`validation/FABRICATE_VOICE_STRESS_FINDINGS.md`](validation/FABRICATE_VOICE_STRESS_FINDINGS.md) |
| Governance Evaluation | 25 scenarios, 55 turns | `python scripts/eval_corpus.py` | [`EVALUATION_CORPUS_REPORT_v1.md`](EVALUATION_CORPUS_REPORT_v1.md) |

Both commands print their own numbers, so no document needs to be trusted about
them. What each result is permitted to prove is fixed by
[`validation/evidence-provenance-matrix.md`](validation/evidence-provenance-matrix.md);
these are **tier 3** (synthetic-corpus) results and may not be described in the
language of a higher tier.

## What was not retracted

The schema-adapter work this document also described is real and remains:
`adapters/fabricate_adapter.py` converts both the two-table CSV export and the
JSONL export into the engine's eval shape, and its exclusions (ATR-01 untestable
in replay; PDX-01's pre-disclosure scope filter) are documented in that file and
in [`../fixtures/fabricate/README.md`](../fixtures/fabricate/README.md).

`scripts/evaluate_tonic_corpus.py` is kept but now **requires** a corpus path
argument and exits non-zero without one, so it can never again produce figures
from an input nobody else can reach.
