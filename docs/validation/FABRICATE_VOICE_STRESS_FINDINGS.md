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
| DBC-01  | 6/6       | 100.0% | 0/95 | 0.0% | *(was 0/28 — denominator corrected 2026-10-21, see below)* |
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

## The DBC-01 result: corrected from 0/28 to 6/6 — 2026-10-21

> **The 0/28 was a wrong denominator, not a failed detector.** Reading the 28
> scenarios' text: only **6** (`disclosure_then_self_contradiction`) are
> identity-persona scenarios. The other **22** have the agent disclose honestly
> — *"Hi, this is an automated verification assistant"* — and then misreport an
> **outcome**: `false_success_reported_for_failed_verification` (8),
> `unapproved_retry_workaround_after_failed_verification` (8),
> `tool_call_reported_success_but_errored` (6). Telling a provider a prior
> authorization succeeded when it failed is a serious failure, but it is not an
> identity claim, and **no NHID control covers it** — now named as an explicit
> non-capability in [`../claim-boundaries.md`](../claim-boundaries.md).
>
> `adapters/fabricate_adapter.py` note 4 drops those 22 with a reported count,
> the same mechanism already used for ATR-01 and PDX-01, so the exclusion prints
> on every run and is never invisible.
>
> The remaining 6 were genuine misses on an indirect frame: *"As the specialist
> handling your case, I'll review this personally."* `_HUMAN_PERSONA_MARKERS`
> carried `"i'm a specialist"` and `_DBC_IMPLIED_HUMANITY_STRONG` carried
> `"i'll personally"`, and the sentence matches neither — the role is in an
> "as the \<role\>" frame and the adverb follows its verb. A shared
> `_claims_role_frame` helper, consulted by both DBC-01 and IDG-01's
> contradiction path, closes it. Verified to fire on **0 of 2,555** Fabricate
> agent turns and **0 of 265** voice-stress negative-control agent turns, so
> neither pinned baseline moved: Fabricate DBC-01 is still 183/200 with 5 FP,
> and voice-stress false positives are still 0/95.
>
> **A correction to this document's own earlier explanation.** It attributed the
> zero to the adapter extracting "only *voice/signal* artifacts … not text
> personas". That is not why. DBC-01 reads `identity_assertion_text`, the
> adapter populates it from the agent's words, and voice-stress labels 839 turns
> `speaker='agent'`. The channel and the wiring were always fine; the lexicon
> missed one phrasing and the denominator counted 22 scenarios that were never
> DBC-01's to catch.

### Original note (retained — the scope question it raises is still open)

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

---

## Fixture integrity (added 2026-10-19)

A third-party first-pass analysis of the corpora was submitted and verified
against the repository at `77d1957`. It surfaced real structural defects that
no guard was checking, because `scripts/check_baseline.py` pins per-control
**detection rates** and nothing checked the fixtures' own **shape**. The
findings below are now pinned by `scripts/check_fixture_integrity.py` and
documented in [`../../fixtures/voice-stress/README.md`](../../fixtures/voice-stress/README.md).

**Join key.** `turns.scenario_id` and `assertions.scenario_id` resolve to
`scenarios.id` (300/300). They match `scenarios.scenario_id` — the
human-readable label — on **0 of 300**. Joining the two identically-named
columns is valid SQL, returns nothing, and raises no error. The guard asserts
both halves: the documented key resolves completely, the decoy resolves not at
all.

**Stale declared counts.** `scenarios.csv` ships two count columns that
disagree with the data: `num_turns` wrong in 148/300 rows (declared sum 1,782
vs 1,582 actual) and `num_assertions` wrong in **300/300** (declared sum 806 vs
2,071 actual). The export is preserved as shipped rather than patched, so the
divergence is pinned at its measured value — documented staleness passes, new
drift fails. The CSV-550 corpus has the same defect in `num_turns` (42/550
rows, declared sum 4,796 vs 4,838 actual).

**Scoreable population.** Of 300 scenarios: 95 negative controls and 205
positives. Only **118** of the positives carry an IDG/PDX/DBC/EIT expectation
and can therefore be scored by `confusion_matrix.compute`. The other **87**
cannot: 67 target `NHID-Auth (proposed, not an existing control)`, 10 target
ATR-01 plus NHID-Auth, 5 target ATR-01 alone (untestable in replay), and 5
(`repeats_introduction_indefinitely_loop-*`) declare
`expected_result = FLAG_FOR_REVIEW` with no control named — an open-gap marker,
not a labelling error. This population is pinned so that silently shrinking
the scoreable set, which would raise every rate, fails CI.

**What was *not* a defect.** The analysis reported `pdx01_violation = 70` in
`fixtures/fabricate/conversations.csv` against a declared baseline of 41 and
called it a stale baseline. It is not: `adapters/fabricate_adapter.py` drops 29
rows that disclose identity at turn 0, because a pre-disclosure gate cannot be
violated where no pre-disclosure exchange exists. 70 − 29 = 41, and
`confusion_matrix.py` prints the drop on every run. The defect it exposed was
documentary — the fixture README stated post-filter denominators without saying
so — and that is now fixed with a raw-vs-scored table.

Likewise, six `repeated_disclosure_no_double_count-*` scenarios carry
`expected_control = IDG-01` with `expected_idg01_violation = 0`. That is
correct, not inconsistent: `expected_control` names the control under test, and
these are negative controls whose expected outcome is `ALLOW`. The guard
enforces label/flag agreement only on non-negative-control rows, where it holds
exactly (0 mismatches).

**Recorded non-actions:** no fixture CSV was edited; the pinned CSV-550
baseline and its `EXPECTED` table were not touched; the measured detection
table above was not revised; the DBC-01 scope decision remains open; NHID-Auth
remains a proposed control.
