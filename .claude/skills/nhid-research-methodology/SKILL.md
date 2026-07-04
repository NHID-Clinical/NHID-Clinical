---
name: nhid-research-methodology
description: >-
  Load when you are turning a hunch about NHID-Clinical into an accepted result — deciding
  whether an idea is proven, how to run an investigation, or when to adopt vs retire a
  change. This is the discipline layer: the evidence bar (one mechanism explains ALL
  observations including negatives, survives adversarial refutation), the
  predict-numbers-before-running rule, and the idea lifecycle from hunch to adopted change
  or documented retirement. Load it for "is this actually proven", "how should I
  investigate", "should we adopt or drop this", "what's our standard of proof". Do NOT
  load it for a routine bug (that's nhid-debugging-playbook) or for the mechanics of the
  measurement tools (nhid-diagnostics-and-tooling).
---

# NHID-Clinical Research Methodology

Verified as of 2026-07-04. This is how a hunch becomes something the project accepts. It is
stricter than "the tests pass."

## The evidence bar

An explanation is accepted only if:
1. **One mechanism explains ALL observations, including the negatives.** A story that explains why
   something looks good but not why the fix doesn't break it is incomplete.
   *Worked example*: the v1.1 label-leakage hypothesis explained BOTH why EIT-01 looked ~perfect
   (the label was wired into the detector) AND why de-leaking it didn't crater detection (~98%
   held because the underlying signal was real). Both halves had to hold.
2. **It survives adversarial refutation.** Before accepting your own mechanism, try to break it —
   run the corpus that should disconfirm it. If you can't refute it and it explains the negatives,
   it's accepted.

## Predict the numbers before you run

State the expected detection/FP **before** executing. A prediction that matches is evidence; a
post-hoc rationalization is not.
- *Worked example A*: the EIT-01 semantics bake-off — each rival semantics had a predicted
  behavior; caller-anchored ask-again was chosen because its measured ~98% matched the reasoning,
  while the rivals' predicted-and-confirmed collapse (43–60%) ruled them out.
- *Worked example B*: `scripts/mine_heuristic_candidate.py` encodes a pre-registered prediction —
  a phrase is asserted to have zero corpus FPs *before* merge; the script tests that prediction.

## The idea lifecycle

```
hunch
  → corpus measurement        (mine_heuristic_candidate.py OR confusion_matrix.py)
  → eval-only implementation   (behind a flag; never live-first)
  → decision gate w/ NAMED owner
  → EITHER adopted change       (count propagation + archive entry; nhid-change-control)
     OR documented retirement    (recorded in the archive so it isn't re-tried)
```
- *Adopted*: three mined phrases cleared the zero-FP bar and were appended additively.
- *Retired*: broad-keyword expansion was measured (142 TP / 260 FP), found net-negative, and
  **documented as retired** — that record is why nobody should re-propose it.
- *Adopted after ceiling proof*: the human-review pivot was adopted only after the lexical ceiling
  was proven.
- *At the gate now*: DBC-01 Tier C live-vs-eval-gated is an **open decision, owner Bree** (as of
  2026-07-04). An idea at the gate is not yet a result.

## Where good ideas have historically come from

- **Real-corpus mining, not intuition** — every accepted lexicon change came from measuring the
  corpus, not from brainstorming phrases.
- **Adversarial corpora** — the adversarial battery surfaced failure modes the friendly corpus hid.
- **Treating a failing test as evidence about the TEST, not just the code** — the v1.1 repair found
  that 3 tests had encoded the bug itself; they were rewritten in place (`CONTRACT CHANGE`), net
  count 0. When a test and the code disagree, question both.

## Anti-patterns (each is a settled lesson)

| Anti-pattern | Why it's banned |
|---|---|
| "Add it and see" without a pre-stated prediction | produces unfalsifiable results |
| Trusting a high number without a leakage audit | the EIT ~95% disaster |
| One cause for a flood of failures | missed 2 of the 3 v1.1 causes |
| Adopting live-first instead of eval-first | skips the owner decision gate |
| Deleting a retired idea's record | invites re-litigation |

## When NOT to use this skill

- A routine bug to fix now → `nhid-debugging-playbook`.
- The mechanics of the measurement tools → `nhid-diagnostics-and-tooling`.
- The analysis recipes themselves → `nhid-proof-and-analysis-toolkit`.
- Where to aim ambition → `nhid-research-frontier`.
- The gate/rules for adopting a change → `nhid-change-control`.
- Siblings: `nhid-failure-archaeology`, `nhid-architecture-contract`,
  `nhid-domain-reference`, `nhid-config-and-flags`, `nhid-build-and-env`,
  `nhid-run-and-operate`, `nhid-validation-and-qa`, `nhid-docs-and-positioning`,
  `nhid-dbc01-semantic-ceiling-campaign`, `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- Lifecycle worked examples: archive §2.5 / §2.5.1 and `docs/devlog_2026-07-02_eval-repair.md`.
- Retired-idea record (broad keywords): `grep -n "142\|260\|ceiling" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
- Pre-registered prediction mechanism: `python3 scripts/mine_heuristic_candidate.py --help`.
- Contract-change precedent: `grep -n "CONTRACT CHANGE" tests/test_fabricate_adapter.py`.
- Open decision (Bree): `grep -n "Bree\|Tier C" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
