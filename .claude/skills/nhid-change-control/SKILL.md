---
name: nhid-change-control
description: >-
  Load BEFORE changing anything in the NHID-Clinical repo — code, tests, lexicons,
  docs, config, or the policy engine. This is the gate-keeping runbook: how changes
  are classified and what each class requires. Load it when you are about to edit
  src/nhid_policy_engine_v1.py, add a detection phrase, add or remove a test, bump the
  test count, touch scripts/validate_ci.py or .github/workflows/ci.yml, edit
  docs/MASTER-KNOWLEDGE-ARCHIVE.md, or ship new production detection behavior. It
  states the non-negotiable invariants WITH the historical incident behind each, so
  you do not re-cause a settled failure. Trigger phrases: "add a phrase", "bump the
  test count", "change the engine", "update the archive", "ship this to production",
  "is this change allowed".
---

# NHID-Clinical Change Control

Verified as of 2026-07-04. This repo is a voluntary behavioral-conformance framework for
AI voice agents in healthcare. Changes here are gated by discipline, not by a CI robot
alone — the CI robot only catches the test-count invariant. Everything else is on you.

## Jargon (defined once)

- **Control**: one of the five policy rules — IDG-01, PDX-01, DBC-01, EIT-01, ATR-01. See
  `nhid-domain-reference`.
- **Lexicon**: a hardcoded tuple/frozenset of substrings the engine matches (e.g.
  `_DBC_IMPERSONATION_PHRASES` in `src/nhid_policy_engine_v1.py`).
- **Corpus**: the labeled conversation dataset under `fixtures/fabricate/` used to measure
  detection and false positives.
- **False positive (FP)**: the engine flags a conversation whose ground truth is clean
  (`scenario_type == "compliant"`).
- **The test-count invariant**: CI requires the suite to report exactly **330 passed /
  18 skipped** (verify: `grep UNIT_EXPECTED scripts/validate_ci.py` → `330`).

## The change-classification table

Classify your change FIRST. The gate is cumulative — a production-surface change must also
satisfy every lighter gate.

| Class | Examples | Required gate |
|---|---|---|
| **doc-only** | archive prose, a devlog, README copy | Honest framing; supersede-don't-delete (below); never edit a HISTORICAL row (below). No test impact. |
| **test-only** | add/rewrite a test | Atomic test-count propagation (below) if the count changes. If a test itself encoded a bug, rewrite in place with a `v1.1 CONTRACT CHANGE`-style comment and keep net count stable. |
| **eval-harness** | `adapters/fabricate_adapter.py`, `scripts/confusion_matrix.py`, `src/synthetic_eval_loop.py` | No label leakage (below); re-run `scripts/confusion_matrix.py` and record numbers; harness changes do not change engine behavior. |
| **engine-behavior** | edit an `evaluate_*` in `src/nhid_policy_engine_v1.py`, add a lexicon phrase | Zero-FP bar for phrases (below); additive-only lexicon edits (below); re-run confusion matrix; **prove** the change with numbers, never by eye. Route through `nhid-corpus-heuristic-mining` for phrase mining. |
| **production-surface** | making new detection behavior live in Beacon/Lambda (e.g. DBC-01 Tier C), touching `functions/handler.py` response contract | Everything above **plus an explicit named-owner decision** (below). Never flip production detection on silently. |

## Non-negotiables, each with its incident

### 1. Archive §9.1 invariants are law
Read them verbatim before an engine or test change:
`grep -n "9.1" docs/MASTER-KNOWLEDGE-ARCHIVE.md` then read that section. They are numbered
invariants (#1–#7+). **Invariant #7** is the zero-FP bar (below). **Invariant #5** is atomic
test-count propagation (below) — it exists *because test-count drift kept recurring* across
the 284→294→303→306→327→330 bumps and repeatedly broke CI or left stale docs.

### 2. Zero-false-positive bar for new detection phrases (§9.1 #7)
A candidate phrase may be merged into a lexicon only if it produces **zero** false positives
across the full corpus. **Incident**: broad keyword candidates (`human`, `person`, `real `)
measured **142 true positives / 260 false positives**; negation-filtered, 106/153. Both are
net-negative. The ceiling is proven — do not "just add more keywords." Vet every candidate
with `scripts/mine_heuristic_candidate.py` (see `nhid-corpus-heuristic-mining` for the full
decision procedure). Do not duplicate that procedure here; invoke it.

### 3. Additive-only lexicon edits
When you add a phrase, append it — never reorder, rewrite, or remove existing entries. Removing
a high-value phrase is measured harm: `our team` = 344 true positives vs 2 false positives;
trimming it to shed ~2 FPs costs ~344 real detections. Deletions require the same owner
decision as a production change.

### 4. Atomic test-count propagation (§9.1 #5)
If your change alters the passing test count, update **all** of these in one commit:
- `scripts/validate_ci.py` → `UNIT_EXPECTED`
- `.github/workflows/ci.yml` → the job **name** string (currently `"Unit invariant: 330 passed"` — the number is hardcoded in the name)
- `.github/CONTRIBUTING.md` → the `(330 expected)` line
- `README.md` → badge + prose (there are multiple; grep first)
- `docs/MASTER-KNOWLEDGE-ARCHIVE.md` → the **LIVE** invariant rows only

Verify nothing was missed: `grep -rn "330" scripts/validate_ci.py .github/ README.md`.

### 5. LIVE vs HISTORICAL archive rows — never edit history
The archive contains a progression ladder (284→294→303→306→327→330) and frozen changelog
rows. Those are **HISTORICAL**: a row that says "294" is a record of a past state and must stay
294. Only update rows that state the *current* invariant. **Incident**: recurring count drift
came partly from someone "fixing" a historical row to the new number. If unsure whether a row
is live or historical, it is historical — leave it.

### 6. Supersede-don't-delete for measurements
When a measurement is invalidated, mark it superseded and point to the replacement; do not
delete it. **Incident/precedent**: the v1.1 eval repair invalidated the §2.5 per-rule rates
(DBC-01 0.5%, EIT-01 94.7%). They were NOT deleted — §2.5 was annotated "superseded by §2.5.1"
and §2.5.1 carries the corrected numbers. History is evidence; keep it.

### 7. Demo-vs-framework fencing
Website/demo code (root `*.html`, `functions/twilio_demo_handler.py`, demo routes, the
`/v1/demo/*` and `/v1/webhooks/twilio-demo/*` endpoints) is **not** framework behavior and
never counts as a conformance capability. **Incident**: repeated commits had to label work
"website demo feature, not framework" to stop demo code being cited as engine capability. Keep
the boundary explicit in code comments and docs.

### 8. New production detection behavior needs a named owner
Turning on a new detector in the live engine path (Beacon/Lambda) is a production-surface
change. **Current open example (as of 2026-07-04)**: DBC-01 Tier C implied-humanity detection
ships in `src/nhid_policy_engine_v1.py` with a measured ~4–11% FP-on-compliant cost; whether it
stays live or is gated eval-only is an **open decision owned by Bree**. A future session must
NOT resolve this silently — surface it. See `nhid-dbc01-semantic-ceiling-campaign` Phase 2.

## Pre-commit checklist

- [ ] Change classified against the table; the right gate satisfied.
- [ ] If engine/lexicon: `python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv` run; numbers recorded; no regression on IDG/PDX/EIT.
- [ ] If phrase added: passed the zero-FP bar via `mine_heuristic_candidate.py`; appended additively.
- [ ] If count changed: all five propagation sites updated; `python3 scripts/validate_ci.py` prints `CI PASS: 330 passed` (or the new number).
- [ ] Archive: superseded not deleted; no historical row edited.
- [ ] If production-surface: owner decision recorded, not assumed.

## When NOT to use this skill

- Diagnosing a failure → `nhid-debugging-playbook`.
- Executing the phrase-mining decision itself → `nhid-corpus-heuristic-mining`.
- What counts as evidence / how to add a test mechanically → `nhid-validation-and-qa`.
- The archive's structure and house style → `nhid-docs-and-positioning`.
- The actual DBC-01 improvement campaign → `nhid-dbc01-semantic-ceiling-campaign`.
- Why an invariant exists (the full story) → `nhid-failure-archaeology`.
- Sibling references: `nhid-architecture-contract`, `nhid-domain-reference`,
  `nhid-config-and-flags`, `nhid-build-and-env`, `nhid-run-and-operate`,
  `nhid-diagnostics-and-tooling`, `nhid-proof-and-analysis-toolkit`,
  `nhid-research-frontier`, `nhid-research-methodology`.

## Provenance and maintenance

- Invariants: `grep -n "9.1" docs/MASTER-KNOWLEDGE-ARCHIVE.md`, read that section.
- Test-count truth: `grep UNIT_EXPECTED scripts/validate_ci.py`.
- Propagation sites: `grep -rn "330" scripts/validate_ci.py .github/workflows/ci.yml .github/CONTRIBUTING.md README.md`.
- Zero-FP bar mechanism: `scripts/mine_heuristic_candidate.py --help`.
- Tier C open decision: `grep -n "Tier C\|Bree\|open decision" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
- If UNIT_EXPECTED ≠ 330 when you read this, the count has moved; trust the file, update this line.
