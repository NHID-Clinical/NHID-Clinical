# Devlog — 2026-07-02 · Policy-engine eval repair (v1.1 patch set)

**Spec baseline unchanged:** NHID-Clinical v1.3 / NHID-Auth v2 ·
`POLICY_ENGINE_VERSION = 1.0.0` (v1.1 = patch-set label, not a release).
**Suite:** 330 passed / 18 skipped / 0 failed. `UNIT_EXPECTED = 330` invariant holds.

## What we tested
Full replay of `src/nhid_policy_engine_v1.py` via `adapters/fabricate_adapter.py`
+ `src/synthetic_eval_loop.py` against four Fabricate battle-test corpora:
CSV export (550 convs / 127 compliant), `nhid_v2_iso_corpus` (175 / 35),
`nhid_adversarial_battery` (175 / 35), `nhid_baseline_corpus` (200 / 57).
New reproducible runner: `scripts/confusion_matrix.py` (detection over convs
declaring each expected violation; FP over the disjoint `scenario_type=="compliant"`
population).

## Root causes (three classes, only one a real engine gap)
- **Wiring/adapter:** IDG-01 fired on every post-disclosure caller turn (adapter
  blanked `identity_assertion_text` on caller turns); ATR-01 untestable in replay;
  PDX-01 disclose-at-turn-0 puts probes out of pre-disclosure scope.
- **Label leakage:** old adapter set `escalation_path_available = not eit01_violation`
  — ground-truth label wired into detector input; EIT-01 could not be missed.
- **Genuine engine gap:** DBC-01 never scanned mid-call implied-humanity language
  (baseline 0.5–2.5%).

## Fixes
- Engine (live path): DBC-01 Tier C `_speech_implies_human()` + implied-humanity
  lexicons; EIT-01 honor verification (`escalation_outcome` → CRITICAL
  `EIT01_ESCALATION_NOT_HONORED`, backward-compatible — fires only when the field is set).
- Adapter: removed leakage; sticky caller-turn disclosure assertion; caller-anchored
  ask-again escalation semantics; ATR-01/PDX-01-turn-0 exclusions (logged); CSV+JSONL
  ingestion; `convert` alias retained.

## Results (v1.1)
| Corpus | IDG-01 | PDX-01 | DBC-01 | EIT-01 |
| :--- | :--- | :--- | :--- | :--- |
| CSV 550 | 100% (0 FP) | 100% (0 FP) | 91.5% (3.9% FP) | 98.2% (2.4% FP) |
| v2_iso | n/a | n/a | 86.7% (0 FP) | 98.6% (5.7% FP) |
| adversarial | 100% (0 FP) | 100% (0 FP) | 97.7% (11.4% FP) | 97.5% (0 FP) |
| baseline | 100% (0 FP) | 100% (0 FP) | 87.0% (1.8% FP) | 100% (1.8% FP) |

DBC-01: 0.5/2.5% → 87–98%. EIT-01 held ~98% *after* de-leaking.

## Decisions
- **EIT-01 semantics:** caller-anchored ask-again (beat "honor anywhere" ~43–60% and
  "honor after last ask" 43% on adversarial). Cut ISO EIT FP 17.1% → 5.7%.
- **DBC-01 lexicon:** keep as-is. `our team` = 344 TP vs 2 FP; trimming top-3 phrases
  costs 30–344 real detections to shed ~2 FPs each. FP rate is the honest precision cost.
- **3 tests rewritten in place** (`v1.1 CONTRACT CHANGE`): `TestEscalationPathAvailable`
  → `TestEscalationOutcome`; `TestIdentityAssertionText` method → sticky-disclosure.
  Net count 0; revertible without touching the engine.

## Known limits (documented, not masked)
- 2 residual ISO EIT FPs = label-semantics mismatch (info-gather-then-transfer;
  conditional escalation), not bugs.
- DBC-01 recall cost: subtle single-cue misses (`ISO-00003/00040`, `ADV-00147/00171`,
  `CONV-00023/00033`).
- ATR-01 untestable in replay — verify in the FastAPI integration harness.

## Open decision (owner: Bree)
Ship DBC-01 Tier C into the live engine (Beacon/Lambda) or gate it eval-only. It's
new production behavior with the measured ~4–11% FP-on-compliant-speech cost.

## Artifacts
`NHID_v1.1_eval_patch.diff` (applies clean against baseline) · changed files
(adapter, engine, adapter tests, `confusion_matrix.py`) · `NHID_v1.1_eval_writeup.md`
· Master Knowledge Archive drop-in `§2.5.1` (supersedes 2 rows in existing §2.5).
