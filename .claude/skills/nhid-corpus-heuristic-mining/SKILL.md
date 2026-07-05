---
name: nhid-corpus-heuristic-mining
description: Use when a NHID-Clinical policy-engine text heuristic (DBC-01 impersonation phrases, EIT-01 escalation triggers, or similar substring-match rules) shows a low real-corpus detection rate and someone asks whether to expand the phrase list, change detection approach, or add human review. Walks through measuring a candidate against the full corpus before merging, and recognizing when the right answer is human-in-the-loop instead of more code.
---

# NHID corpus heuristic mining

NHID-Clinical's text heuristics (`_DBC_IMPERSONATION_PHRASES`,
`_ESCALATION_TRIGGERS` in `src/nhid_policy_engine_v1.py`) are deterministic
substring matches by design — auditable, no model calls, no false-positive
drift from a vendor model update. That determinism is a strength
(`evidence-pack.html`'s "Deterministic output" guarantee) but it means
coverage only grows by literally adding phrases, and every phrase is a
trade against false positives. This skill is the repeatable process for
deciding whether a low detection rate on real corpus data is (a) a phrase
list that needs a few more entries, (b) a heuristic that has hit its
structural ceiling and needs human review instead, or (c) a different bug
entirely (adapter/eval-loop plumbing, not the heuristic).

## Step 0: confirm it's actually the heuristic's fault

Before touching the phrase list, check whether the low rate is a plumbing
problem instead. NHID-Clinical's synthetic eval loop
(`src/synthetic_eval_loop.py:build_event()`) hardcodes several fields
(`execution_context`, `replay_mode`, `external_calls_cached`, etc.) as
constants for every turn — no corpus input can ever change them. If the
control you're investigating reads one of those hardcoded fields (this is
exactly what happened with ATR-01), the 0% is a measurement artifact, not a
detection gap, and no amount of corpus mining will move it. Verify by
reading the control's `evaluate_*()` function and tracing every field it
reads back to `build_event()` / the adapter — if a field is a literal
constant rather than `turn.get(...)`, the corpus structurally cannot
exercise that control. Document this and stop; the right verification path
is the unit/conformance/failure-injection tests that already construct
malformed events directly (e.g. `tests/failure_injection_harness.py`,
`tests/nhid_conformance_test_suite_v1.yaml`).

## Step 1: mine the real corpus for missed cases

For a heuristic that genuinely reads corpus-derived fields (DBC-01 reading
`identity_assertion_text`, for example), find what it's currently missing:

```python
import csv
from src.nhid_policy_engine_v1 import _assertion_implies_human  # or the relevant matcher

with open("fixtures/fabricate/conversations.csv") as f:
    convs = {r["id"]: r for r in csv.DictReader(f)}
with open("fixtures/fabricate/turns.csv") as f:
    turns = [t for t in csv.DictReader(f) if t["speaker"] == "agent"]

missed = [
    t for t in turns
    if convs[t["conversation_id"]]["dbc01_violation"] == "1"
    and _assertion_implies_human(t["text"].lower()) is None
]
```

Read a sample of `missed` and look for a real lexical pattern shared across
multiple conversations — not a one-off phrasing.

## Step 2: vet every candidate against the FULL corpus before merging

Run `python3 scripts/mine_heuristic_candidate.py "<candidate>"` (add
`--negate "phrase,phrase"` to exclude disclosure language that shares a
keyword). This reports new true positives (in violation conversations) vs.
new false positives (in clean conversations) for that exact candidate.

Per archive §9.1 invariant #7: **a candidate only merges with zero
measured false positives across the full corpus.** This is non-negotiable —
two prior candidates ("i'll personally": 5 FP, "my team": 29 FP) were
rejected on exactly this basis, and two broader keyword experiments during
this skill's authoring (142 TP/260 FP, 106 TP/153 FP) were rejected the
same way. A candidate that clears the bar gets added additively (never
reorder/edit existing phrases) with one new regression test per phrase in
the relevant `test_*_heuristics.py` file, using the real corpus sentence as
the test fixture.

## Step 3: recognize when you've hit the ceiling

If multiple candidates in a row produce more false positives than true
positives, that's not bad luck — it's proof the heuristic class (substring
matching) cannot separate the signal you're chasing from legitimate speech.
Continuing to mine phrases at that point burns effort and risks shipping a
false-positive regression under pressure to "improve the number." Stop, and
say so explicitly with the measured numbers (don't just lower confidence
quietly) — see `docs/dbc01-human-review-sop.md` for how this was resolved
for DBC-01.

## Step 4: route the residual gap to human review, not more code

NHID-Clinical already has the mechanism for this and it was sitting
unused: `PolicyAction.LOG_ONLY` (non-blocking, but logged) and NHID-CAS's
`Review Required` / `Denied / Degraded` trust tiers (`src/nhid_cas.py`,
`_tier_for_cas()`). Before inventing a new escalation path, check whether
an existing non-blocking decision path or scoring tier already exists that
nothing currently treats as a review queue — formalizing that into an SOP
is usually the correct "fix," not new detection code. See
`docs/dbc01-human-review-sop.md` as the template: it defines exactly which
decisions/tiers route to a human reviewer and what the reviewer does with
them, without claiming the deterministic engine can do something it
measurably cannot.

## Step 5: update everything atomically, additive-only

Per the project's existing test-discipline pattern: bump
`UNIT_EXPECTED` in `scripts/validate_ci.py` to match the new test count in
the same commit as the new tests, update the CI job-name label
(`.github/workflows/ci.yml`) if it encodes the count, and add the new
detection-rate numbers + methodology to `docs/MASTER-KNOWLEDGE-ARCHIVE.md`
(additive subsection, never edit historical entries) and `evidence-pack.html`
if the numbers are public-facing. Re-run
`python3 -m pytest tests/ -q` and `python3 scripts/validate_ci.py` before
committing.
