# NHID-Clinical Voice-Stress Evaluation Corpus

Hand-authored scenarios that put the governance controls under acoustic and
conversational stress: ASR-style transcription noise, disfluency, interruption,
repeated disclosure, language switching, and authorization edge cases.

**Status:** research measurement · **Added:** 2026-10-14 · README added 2026-10-19

> This corpus is **not** the pinned baseline. `scripts/check_baseline.py`
> measures only the CSV-550 fabricate corpus and is deliberately left that way.
> The voice-stress numbers are a separate measurement and must not be quoted as
> a headline detection rate — see
> [`../../docs/validation/FABRICATE_VOICE_STRESS_FINDINGS.md`](../../docs/validation/FABRICATE_VOICE_STRESS_FINDINGS.md).

## Files

| File | Rows | Primary key |
|------|-----:|-------------|
| `scenarios.csv` | 300 | `id` (UUID) |
| `turns.csv` | 1,582 | `id` |
| `assertions.csv` | 2,071 | `id` |
| `corpus.jsonl` | — | nested export of the same scenarios |

## Read this before you join anything

**`turns.scenario_id` and `assertions.scenario_id` resolve to
`scenarios.id`** — the UUID column — **not** to `scenarios.scenario_id`.

`scenarios.scenario_id` is a human-readable label
(`no_disclosure_ever-001`). It matches **0 of 300** child keys. Joining the two
identically-named columns is syntactically valid, returns an empty result, and
raises no error:

```sql
-- WRONG: returns 0 rows, silently
JOIN turns t ON t.scenario_id = s.scenario_id
-- RIGHT
JOIN turns t ON t.scenario_id = s.id
```

`scripts/check_fixture_integrity.py` asserts both halves of this: that the
documented key resolves completely, and that the decoy column resolves not at
all. Checking only "some column joins" would pass if the two were swapped.

## Known-stale columns — do not trust, count rows

`scenarios.csv` ships two declared-count columns that disagree with the data.
They are **not corrected**; the export is preserved as shipped, matching the
precedent in [`../fabricate/staging/README.md`](../fabricate/staging/README.md).

| Column | Rows wrong | Declared sum | Actual rows |
|--------|-----------:|-------------:|------------:|
| `num_turns` | 148 / 300 | 1,782 | **1,582** |
| `num_assertions` | 300 / 300 | 806 | **2,071** |

`num_assertions` is wrong for every single row. Both divergences are pinned by
`scripts/check_fixture_integrity.py`, so a *new* divergence fails CI while the
documented staleness does not. Derive counts with `COUNT(*)` over the child
tables.

## What is scoreable, and what is not

`scripts/confusion_matrix.py` can only score a scenario that declares an
IDG-01, PDX-01, DBC-01 or EIT-01 expectation. The split:

| Population | Count | Note |
|------------|------:|------|
| Negative controls (`is_negative_control = 1`) | 95 | the false-positive denominator |
| Positives | 205 | |
| &nbsp;&nbsp;— scoreable | **118** | carry a core IDG/PDX/DBC/EIT expectation |
| &nbsp;&nbsp;— not scoreable | **87** | see below |

Why the 87 cannot be scored:

| `expected_control` | Count | Reason |
|--------------------|------:|--------|
| `NHID-Auth (proposed, not an existing control)` | 67 | a proposed control detects nothing until it exists |
| `ATR-01, NHID-Auth (proposed)` | 10 | both unscoreable in transcript replay |
| `ATR-01` | 5 | untestable in replay (the harness synthesizes the envelope it would check) |
| `none` | 5 | the `repeats_introduction_indefinitely_loop-*` rows: `expected_result = FLAG_FOR_REVIEW` with no control named — an open-gap marker, not a labelling error |

**Negative controls may name a control without setting its flag.** Six
`repeated_disclosure_no_double_count-*` rows carry `expected_control = IDG-01`
with `expected_idg01_violation = 0`. That is correct: `expected_control` names
the control *under test*, and for a negative control the expected outcome is
`ALLOW`. The integrity guard enforces label/flag agreement only on
non-negative-control rows, where it currently holds exactly.

## Reproduce the measurement

```bash
python scripts/confusion_matrix.py --voice-stress \
    fixtures/voice-stress/scenarios.csv fixtures/voice-stress/turns.csv
python scripts/check_fixture_integrity.py
```

## Claim boundary

Transcript-replay measurements on a synthetic, hand-authored corpus — **tier 3**
on [`../../docs/validation/evidence-provenance-matrix.md`](../../docs/validation/evidence-provenance-matrix.md).
They do not establish acoustic robustness, real-caller behaviour, deployment, or
certification, and the scenario text is synthetic throughout: no real people,
no real identifiers, no PHI.
