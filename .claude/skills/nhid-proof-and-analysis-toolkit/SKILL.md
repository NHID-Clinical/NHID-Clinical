---
name: nhid-proof-and-analysis-toolkit
description: >-
  Load when you need to PROVE something about NHID-Clinical detection quality rather than
  assert it — design an eval, check whether a number is trustworthy, decide between rival
  detection semantics, or establish a ceiling. This is the first-principles analysis
  toolkit ("prove it, don't just install it"): each method is a recipe with steps, the
  command, what invalidates it, and a worked example from this repo's history. Load it
  before building an eval harness, before trusting a reported rate, or when someone says
  "just add it and see". Trigger phrases: "is this eval valid", "prove detection
  improved", "which semantics is right", "have we hit the ceiling", "audit for leakage",
  "how do I measure this properly".
---

# NHID-Clinical Proof & Analysis Toolkit

Verified as of 2026-07-04. These are the reusable analysis methods behind every real result in
this repo. Each has a worked example you can re-read in the archive (§2.5 / §2.5.1) or
`docs/devlog_2026-07-02_eval-repair.md`.

## Recipe 1 — Disjoint-population confusion matrix
**When**: any time you report detection AND false positives for a control.
**Steps**: measure detection over conversations that *declare* the violation; measure FP over the
*disjoint* `scenario_type == "compliant"` population; never let a conversation count in both.
**Command**: `python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv`.
**Invalidated by**: mixing populations, or measuring FP on the same conversations you measured
detection on.
**Worked example**: the v1.1 matrix (DBC 183/200 91.5% / 5 FP on 127 compliant).

## Recipe 2 — Label-leakage audit
**When**: before trusting ANY eval number, especially a suspiciously high one.
**Steps**: list every input the detector reads; trace each back to its source; if any input is
computed from the ground-truth label, the eval is void — fix the harness, re-measure.
**Invalidated by**: skipping the trace because the number "looks right."
**Worked example**: the adapter set `escalation_path_available = not eit01_violation`, feeding the
answer into EIT-01. The resulting ~95–100% "detection" was meaningless; removing the leak is what
made the ~98% real. (`grep -n "escalation_path_available" adapters/fabricate_adapter.py`.)

## Recipe 3 — Ceiling proof by exhaustive candidate mining
**When**: before concluding "we need a smarter method," first measure the *best possible* version
of the dumb method.
**Steps**: enumerate the broadest reasonable lexical candidates; measure their TP and FP on the
full corpus with `scripts/mine_heuristic_candidate.py`; if the best lexical version is
net-negative, the ceiling is real and a semantic method is justified.
**Invalidated by**: testing only a couple of phrases and generalizing.
**Worked example**: broad keywords (`human`, `person`, `real `) = **142 TP / 260 FP**;
negation-filtered = 106/153. Both net-negative → lexical ceiling proven, human-review pivot
justified.

## Recipe 4 — Semantics bake-off
**When**: a rule needs a semantic judgment call (what counts as "honored"? "pre-disclosure"?).
**Steps**: enumerate the rival semantics; implement each; run ALL against ALL corpora; pick by
the numbers, not by intuition; record why the loser lost.
**Invalidated by**: choosing a semantics because it's "cleaner" without running it.
**Worked example**: EIT-01 escalation semantics — "honored anywhere" 43–60% detection;
"honored after last ask" 43% on adversarial; **caller-anchored ask-again ~98%** (and ISO FP
17.1%→5.7%). Caller-anchored won on evidence.

## Recipe 5 — Root-cause separation
**When**: a *flood* of failures appears at once.
**Steps**: refuse the single-cause story; partition the failures; find a distinct mechanism for
each partition; verify each mechanism independently, including that fixing it doesn't break the
others.
**Invalidated by**: accepting the first plausible cause for all of it.
**Worked example**: the v1.1 repair split the failure flood into three causes (adapter caller-turn
blanking; label leakage; a genuine engine gap) — only one warranted an engine change.

## Recipe 6 — Cost-benefit lexicon accounting
**When**: before adding OR removing any lexicon phrase.
**Steps**: build a per-phrase TP/FP table over the corpus; a phrase earns its place only if TP
dwarfs FP; a removal is justified only if the phrase's TP is near zero.
**Invalidated by**: reasoning about a phrase without its corpus counts.
**Worked example**: `our team` 344 TP / 2 FP; `i'll personally` 40/2; `my team` 30/2 → keep all;
trimming any to shed ~2 FP costs 30–344 detections.

## The through-line

Every recipe exists to replace a gut call with a reproducible number. If you cannot express your
claim as **command + corpus + expected output**, you do not yet have a result — see
`nhid-validation-and-qa`.

## When NOT to use this skill

- Running the tools operationally / reading their output → `nhid-diagnostics-and-tooling`.
- Executing the DBC-01 improvement campaign → `nhid-dbc01-semantic-ceiling-campaign`.
- The phrase-vetting decision procedure → `nhid-corpus-heuristic-mining`.
- The discipline of turning a hunch into an accepted result → `nhid-research-methodology`.
- Siblings: `nhid-change-control`, `nhid-debugging-playbook`, `nhid-failure-archaeology`,
  `nhid-architecture-contract`, `nhid-domain-reference`, `nhid-config-and-flags`,
  `nhid-build-and-env`, `nhid-run-and-operate`, `nhid-validation-and-qa`,
  `nhid-docs-and-positioning`, `nhid-research-frontier`.

## Provenance and maintenance

- Confusion matrix logic: `grep -n "compliant\|expected\|ALL_CONTROLS" scripts/confusion_matrix.py`.
- Leakage example: `grep -n "escalation_path_available\|escalation_outcome" adapters/fabricate_adapter.py`.
- Mining bar: `python3 scripts/mine_heuristic_candidate.py --help`.
- Worked-example numbers: archive §2.5 / §2.5.1 and `docs/devlog_2026-07-02_eval-repair.md`.
