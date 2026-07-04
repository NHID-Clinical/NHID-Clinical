---
name: nhid-dbc01-semantic-ceiling-campaign
description: >-
  Load when the task is to IMPROVE DBC-01 detection past the substring-matching ceiling,
  or to decide/act on the DBC-01 Tier C live-vs-eval-gated question. This is the flagship
  executable campaign for the project's hardest live problem: numbered, decision-gated
  phases with exact commands and expected numbers, a ranked solution menu with proof
  obligations, explicitly fenced wrong paths, and a promotion protocol. Load it when
  asked to "get DBC-01 above the ceiling", "reduce DBC-01 misses", "should Tier C be
  live", "build a semantic detector for impersonation", or "beat 91.5%". Do NOT load it
  for a routine DBC-01 bug (that's nhid-debugging-playbook) or for simple phrase vetting
  (nhid-corpus-heuristic-mining).
---

# Campaign: DBC-01 Semantic Ceiling

Verified as of 2026-07-04. **Hardest live problem.** DBC-01 (Deceptive Behavior Check) detects
an agent implying it is human. Lexical/substring matching is at its ceiling: ~87–98% detection
with a 4–11% false-positive (FP) cost, and the residual misses are non-lexical. This campaign is
how you move the needle *with evidence*, not vibes.

Run the phases in order. Each gate has expected numbers; if you see something else, branch as
noted. Never skip a gate.

## Phase 0 — Reproduce the baseline (gate)

```bash
python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv
```
**Expected (observed 2026-07-04):**

| control | detect | rate | FP/clean | FP rate |
|---|---|---|---|---|
| IDG-01 | 70/70 | 100.0% | 0/127 | 0.0% |
| PDX-01 | 41/41 | 100.0% | 0/127 | 0.0% |
| DBC-01 | 183/200 | 91.5% | 5/127 | 3.9% |
| EIT-01 | 168/171 | 98.2% | 3/127 | 2.4% |

- **If DBC-01 ≠ 183/200 (91.5%) / 5 FP** → STOP. The engine or lexicon moved since 2026-07-04.
  Run `git log --oneline -- src/nhid_policy_engine_v1.py | head` and re-establish the true
  baseline before doing anything else. Do not compare a new detector against a stale number.

## Phase 1 — Characterize the residual

The confusion matrix prints `DBC-01 missed (17): <ids>`. Pull the transcripts for a sample:
```bash
# find the missed conversation, read its agent turns
grep -n "<missed-conversation-id>" fixtures/fabricate/turns.csv
```
Classify each miss:
- **single-cue implicit**: one soft "we-language"/ownership phrase not in the lexicon.
- **fully non-lexical**: deception carried by structure/context, no phrase to match.

**Gate**: if the misses are mostly non-lexical, a bigger keyword list cannot fix this — proceed
to a semantic approach (Phase 3), NOT more phrases. Confirm the misses are genuinely non-lexical
before spending effort.

## Phase 2 — The Tier C gating decision (OPEN; owner: Bree)

DBC-01 Tier C (`_speech_implies_human()`) is **new production detection behavior** currently live
in the engine path. Its measured FP-on-compliant cost by corpus: **CSV 3.9%, adversarial 11.4%,
baseline 1.8%, v2_iso 0%**. The options:

| Option | Meaning |
|---|---|
| Keep live | Tier C fires in Beacon/Lambda (current state) |
| Eval-only | detection measured but not live in production |
| Flag-gated | live behind an explicit flag/owner toggle |

**This decision is NOT yours to make silently.** It is owned by **Bree** and open as of
2026-07-04. If your task forces the question, surface it to the owner with the FP table above and
the evidence that would change the answer (e.g. a production FP audit, or a downstream cost of the
11.4% adversarial FP). Do not flip it in a commit. See `nhid-change-control` §8.

## Phase 3 — Solution menu (ranked, each with a proof obligation)

| Rank | Approach | Proof obligation before it can ship |
|---|---|---|
| a | **LLM-judge second stage** on turns DBC-01 already flags `LOG_ONLY` | Evaluate the judge on the SAME disjoint-population confusion matrix. Must **beat 91.5% detection without exceeding 3.9% FP on CSV**. State a latency + $ budget up front (this runs per flagged turn). |
| b | **Embedding-similarity** to labeled violation exemplars | Choose the similarity threshold on a **train split**; report detection/FP on a **held-out split** only. No threshold tuned on the test set. |
| c | **Human-review-only for the residual** (ALREADY SHIPPED) | This is the respectable do-nothing-more baseline: the residual is routed to `dbc01_review_queue` and dispositioned by a human. Any new detector must beat this on cost, not just detection. |
| d | **Hybrid**: keep Tier C, add queue-triage priority | Prioritize review-queue items by severity/confidence; obligation: don't change detection numbers, only ordering. |

Start from (c) as the honest baseline. Prefer (a) only if you can meet its obligation.

## Fenced wrong paths (with the evidence)

- **More keyword broadening** — proven net-negative: broad keywords measured **142 TP / 260 FP**;
  negation-filtered 106/153. Do not do this. (`nhid-failure-archaeology` #3.)
- **Trimming the top-3 phrases to cut FP** — costs **30–344 real detections per ~2 FPs**
  (`our team` 344/2, `i'll personally` 40/2, `my team` 30/2). No.
- **Any eval where a label-derived field feeds the detector** — that is *label leakage* and voids
  the result (the historical `escalation_path_available = not eit01_violation` disaster). Audit
  inputs first (`nhid-proof-and-analysis-toolkit` recipe 2).
- **Judging improvement by reading a few transcripts** — only the confusion matrix counts.

## Promotion protocol (route through `nhid-change-control`)

A new detector ships only with:
- [ ] Its own confusion-matrix row on the CSV corpus (command + numbers recorded).
- [ ] **Zero regression** on IDG-01/PDX-01/EIT-01.
- [ ] Test-count propagation if any tests were added (`nhid-change-control`).
- [ ] An archive §2.5.x entry marking what it supersedes (`nhid-docs-and-positioning`).
- [ ] If it becomes live production behavior → the Phase 2 owner decision.

## Falsifiable success milestone

> DBC-01 detection **> 95%** on the CSV-550 corpus at **FP ≤ 3.9%**, with **no regression** on
> the other three controls, reproduced by a committed script (`scripts/confusion_matrix.py`).

Anything short of a reproduced matrix meeting that bar is a hypothesis, not a result.

## When NOT to use this skill

- A routine DBC-01 bug (0 detections, wrong routing) → `nhid-debugging-playbook`.
- Just vetting one candidate phrase → `nhid-corpus-heuristic-mining`.
- The analysis methods in the abstract → `nhid-proof-and-analysis-toolkit`.
- Framing this as an SOTA research bet → `nhid-research-frontier` / `nhid-research-methodology`.
- Siblings: `nhid-change-control`, `nhid-failure-archaeology`, `nhid-architecture-contract`,
  `nhid-domain-reference`, `nhid-config-and-flags`, `nhid-build-and-env`,
  `nhid-run-and-operate`, `nhid-diagnostics-and-tooling`, `nhid-validation-and-qa`,
  `nhid-docs-and-positioning`.

## Provenance and maintenance

- Re-run Phase 0 baseline: the command above; the DBC-01 row must be 183/200, 5 FP.
- Tier C code: `grep -n "_speech_implies_human\|Tier C\|IMPLIED_HUMANITY" src/nhid_policy_engine_v1.py`.
- Ceiling evidence: `grep -n "142\|260\|our team" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
- Open decision: `grep -n "Bree\|Tier C\|open decision" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
- Per-corpus FP table source: archive §2.5.1.
