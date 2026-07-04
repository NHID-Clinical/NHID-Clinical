---
name: nhid-diagnostics-and-tooling
description: >-
  Load when you need to MEASURE something in NHID-Clinical instead of eyeballing it —
  detection rate, false positives, whether a change helped, whether CI will pass, or
  whether ATR-01 is exercisable. Load it before claiming any control got better/worse,
  before merging a lexicon change, or when reading confusion-matrix output. It maps each
  diagnostic script to the question it answers and how to interpret its output (including
  when a false positive is a label-semantics mismatch, not a bug). Trigger phrases: "did
  detection improve", "run the confusion matrix", "what's the FP rate", "measure this",
  "is this FP real", "which tool tells me".
---

# NHID-Clinical Diagnostics & Tooling

Verified as of 2026-07-04. **Rule of the house: never judge a detection change by eye.** Use
these tools; report their numbers.

## Which question → which tool

| Question | Tool |
|---|---|
| Per-control detection & FP on the corpus | `scripts/confusion_matrix.py` |
| Is a candidate DBC-01 phrase safe to add? | `scripts/mine_heuristic_candidate.py` (decision procedure: `nhid-corpus-heuristic-mining`) |
| Detection rates from a converted conversation JSON | `scripts/run_batch_eval.py` (`src/synthetic_eval_loop.compute_detection_rates`) |
| Will CI pass? (test-count invariant) | `scripts/validate_ci.py` |
| Is ATR-01 / a server path exercised? | `tests/failure_injection_harness.py` (needs live server) |
| Identity determinism / perf smoke (system-level) | `.github/workflows/nhid-gates.yml` jobs |

## `scripts/confusion_matrix.py` — the primary instrument

```bash
python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv
```

**How it measures (disjoint populations):**
- **Detection** for a control is computed ONLY over conversations that declare that control in
  their expected violations. `detected/expected`.
- **False positives** are computed ONLY over the disjoint set of conversations whose
  `scenario_type == "compliant"` (ground-truth clean). A flagged compliant conversation = 1 FP.
- **ATR-01 is excluded** (`ALL_CONTROLS` omits it) — untestable in replay by design.

**Verified CSV-550 baseline (as of 2026-07-04):**

| control | detect | rate | FP/clean | FP rate |
|---|---|---|---|---|
| IDG-01 | 70/70 | 100.0% | 0/127 | 0.0% |
| PDX-01 | 41/41 | 100.0% | 0/127 | 0.0% |
| DBC-01 | 183/200 | 91.5% | 5/127 | 3.9% |
| EIT-01 | 168/171 | 98.2% | 3/127 | 2.4% |

It also prints `... missed (N): <ids>` and `... FP on compliant (N): <ids>`, plus `note:
dropped ... expectation(s)` for ATR-01 and turn-0 PDX-01 exclusions.

**Interpreting output:**
- A **missed** ID = a conversation that declares the violation but the engine didn't detect it.
  For DBC-01 these are the non-lexical residual (implicit "we-language"). Confirm by reading the
  transcript — do NOT reflexively add a keyword (see `nhid-failure-archaeology` #3).
- An **FP on compliant** ID = the engine flagged a clean conversation. Some are genuine
  precision cost; some are **label-semantics mismatches** (the corpus label is arguably wrong),
  e.g. the EIT-01 ISO cases `NHID-V2-ISO-00159` (info-gather-then-transfer) and
  `NHID-V2-ISO-00172` (conditional escalation). A label-semantics mismatch is NOT an engine bug;
  document it, don't chase it.

## `scripts/validate_ci.py` — drift detector

```bash
python3 scripts/validate_ci.py       # expect: CI PASS: 330 passed
```
Fails unless the suite reports exactly `UNIT_EXPECTED` (330) passed and a skip count in
`{0, 18}`. Run it after any test change (see `nhid-change-control` for propagation).

## `tests/failure_injection_harness.py` — ATR-01 & server paths

ATR-01 and other envelope-level checks can only be exercised against a live server. Start it
(`uvicorn app:app --reload --port 8000`) then run the harness. Without the server these 18 tests
skip — that is expected, not a failure.

## nhid-gates system diagnostics

`.github/workflows/nhid-gates.yml` runs `identity_determinism` (Ed25519 reproducibility),
`performance_smoke` (cold start < 1s, 1000 verifies < 2s), `api_contract`, `security_gates`,
`fhir_validation`. Treat these as the system-level health signals.

## When NOT to use this skill

- The decision procedure for adding a phrase → `nhid-corpus-heuristic-mining`.
- Why a number is what it is (history) → `nhid-failure-archaeology`.
- The analysis *methods* behind the tools (confusion matrix, leakage audit) → `nhid-proof-and-analysis-toolkit`.
- Running a full improvement campaign → `nhid-dbc01-semantic-ceiling-campaign`.
- What counts as acceptable evidence → `nhid-validation-and-qa`.
- Siblings: `nhid-change-control`, `nhid-debugging-playbook`, `nhid-architecture-contract`,
  `nhid-domain-reference`, `nhid-config-and-flags`, `nhid-build-and-env`,
  `nhid-run-and-operate`, `nhid-docs-and-positioning`, `nhid-research-frontier`,
  `nhid-research-methodology`.

## Provenance and maintenance

- Re-baseline: `python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv` (the table above must match; if not, the engine/lexicon moved — see `nhid-failure-archaeology`).
- Population logic: `grep -n "compliant\|ALL_CONTROLS\|expected" scripts/confusion_matrix.py`.
- CI invariant: `grep -nE "UNIT_EXPECTED|skipped" scripts/validate_ci.py`.
- Gates: `grep -nE "^  [a-z_]+:" .github/workflows/nhid-gates.yml`.
