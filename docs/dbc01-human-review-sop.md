# DBC-01 Human-Review SOP

## Why this exists

`_DBC_IMPERSONATION_PHRASES` in `src/nhid_policy_engine_v1.py` is a deterministic
substring match. It has a real ceiling: broadening it past the current phrase
list trades detection-rate gains for false-accusation risk.

Measured on the full 550-conversation Fabricate corpus
(`scripts/mine_heuristic_candidate.py`):

| Candidate expansion | New true positives | New false positives |
| :--- | :--- | :--- |
| Broad keywords (`human`, `person`, `real`) | 142 | 260 |
| Negation-filtered (excludes "not a human", "ai system", etc.) | 106 | 153 |

Both candidates produce more false positives than true positives. The false
positives are agents *correctly* disclosing AI status or discussing
escalation ("I can connect you with a human claims specialist") — lexically
indistinguishable from impersonation without genuine semantic understanding.
Pursuing further phrase-list growth is rejected per archive §9.1 invariant
#7: candidates only merge with zero measured false-positive risk.

This is the gap human review exists to close. It is not a new mechanism —
`PolicyAction.LOG_ONLY` (non-blocking) and NHID-CAS's `Review Required` /
`Denied / Degraded` tiers (`src/nhid_cas.py`) already exist for exactly this
purpose. They were never wired into an operational review procedure. This
SOP is that procedure.

## What routes to human review

A session **must** be queued for human review when any of the following is
true:

1. **`evaluate_dbc01()` returns `LOG_ONLY` with a `MAJOR`-severity violation**
   (`reason_code == "DBC01_IMPERSONATION_PHRASE_DETECTED"`). The phrase match
   fired — this is the highest-confidence signal the deterministic engine can
   give you, and it does not block the call by design (`§2.1` of the
   archive). Treat the non-blocking behavior as "log for review," not
   "resolved."
2. **NHID-CAS tier is `Review Required` or worse** (`cas < CAS_CONDITIONAL_TRUST`,
   i.e. `< 0.75`, per `_tier_for_cas()` in `src/nhid_cas.py`). This catches
   sessions where no single deterministic rule fired but the composite trust
   score (identity assertion factor × non-human operational confidence ×
   event completeness) is low — the ambiguous middle ground a phrase list
   cannot reach.
3. **Any `CRITICAL` DBC-01 violation** (Tier A artifact flags) — already
   logged; included here for completeness of the review queue, not because
   detection confidence is in question.

## What does NOT route to human review

- `CONTINUE_AI` decisions with no violations. Re-flagging every clean call
  for review defeats the purpose and trains reviewers to ignore the queue.
- Conversational mentions of "human"/"person"/"real" that don't match a
  known phrase and don't depress the CAS score — per the measurements above,
  treating every such mention as suspect produces more noise than signal.

## Reviewer procedure

1. Pull the session's full event trace (`§2.1`/`§8` audit trail — every
   `LOG_ONLY` decision is already persisted with its triggering phrase or
   CAS breakdown).
2. Read the `identity_assertion_text` (DBC-01 trigger) or `nocf_detail`
   breakdown (CAS trigger) in context — most flagged language is reassurance
   or escalation talk, not impersonation. The reviewer's job is to make the
   call the phrase list structurally cannot.
3. Confirmed impersonation → escalate per the deploying organization's
   incident process (this SOP does not define that process; NHID-Clinical
   ships the detection signal, not the org's incident-response policy — see
   the production-readiness assessment, archive §7.4).
4. False positive → no code change required. Do **not** add the triggering
   phrase to a suppression list without running it through
   `scripts/mine_heuristic_candidate.py` first; ad hoc suppression is how
   detection coverage silently erodes.

## When a new phrase candidate shows up during review

Run it through the mining script before touching `_DBC_IMPERSONATION_PHRASES`:

```
python3 scripts/mine_heuristic_candidate.py "candidate phrase" --negate "disclosure phrase,another one"
```

Zero false positives across the full corpus → eligible to merge, additive
only, with a regression test in `tests/test_dbc01_heuristics.py`. Any false
positives → reject; rely on this SOP's human-review queue for that
phrasing instead of forcing it into the deterministic engine.

## Operational tooling

The routing criteria above are now code-enforced, not just procedural.
`src/dbc01_review_routing.should_route_to_review()` evaluates every
conformance check's `PolicyDecision` and CAS result against this SOP's
"what routes" / "what does NOT route" criteria; `functions/handler.py`
calls it from `_decision_to_dict()` and, when it routes, persists the
session to `nhid_event_store`'s `dbc01_review_queue` table via
`enqueue_dbc01_review()`. The handler's JSON response carries the outcome
in a `human_review` block: `{"queued": bool, "trigger_reason": str|None,
"queue_id": int|None}`.

Reviewers work the queue with `scripts/resolve_dbc01_review.py`:

```
python3 scripts/resolve_dbc01_review.py --list
python3 scripts/resolve_dbc01_review.py --resolve 3 --disposition false_positive --reviewer alice
python3 scripts/resolve_dbc01_review.py --resolve 3 --disposition confirmed_impersonation \
    --reviewer alice --notes "escalated per org incident process"
```

`--list` prints every pending row (session, trigger reason, severity, CAS
score, and the triggering `identity_assertion_text` when present).
`--resolve` requires `--disposition` to be `confirmed_impersonation` or
`false_positive`; it raises rather than silently overwriting if the queue
id is unknown or already resolved — resolution is a one-way transition.
