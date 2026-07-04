---
name: nhid-architecture-contract
description: >-
  Load when you need to understand WHY the NHID-Clinical system is built the way it is
  before you change it — the load-bearing design decisions, the invariants that must
  hold, and the honestly-stated weak points. Load it before refactoring the policy
  engine, changing how violations or CAS are computed, touching the review queue or the
  event contract, or reconciling the Lambda handler vs the FastAPI server. Answers:
  "why does reason_code not match the violations?", "why is DBC-01 non-blocking?", "why
  are there two CAS functions?", "why does evaluate_* never raise?", "what must I not
  break?". It is the contract, not a how-to: it will not tell you how to run, test, or
  debug (see the sibling skills).
---

# NHID-Clinical Architecture Contract

Verified as of 2026-07-04. These are the decisions the system leans on. Break one and you
silently corrupt conformance results.

## Load-bearing decisions (and why)

### 1. Engine purity: `evaluate_*` never raises
Every control function in `src/nhid_policy_engine_v1.py` (`evaluate_idg01`, `evaluate_pdx01`,
`evaluate_dbc01`, `evaluate_eit01`, `evaluate_atr01`, `evaluate_bot_to_bot`) returns a
`PolicyDecision` and is wrapped so it never throws. On an internal error it returns
`_internal_error_decision(...)` which emits an **ATR-01 CRITICAL**, `reason_code =
"INTERNAL_POLICY_ERROR"`, action `LOG_ONLY`, `next_state = "ERROR"`.
**Why**: a live call must always get a decision; a crash mid-call is worse than a logged
error. **Invariant**: never let an exception escape an `evaluate_*`.

### 2. `evaluate_all` merges ALL violations; `reason_code` is only the dominant rule
`evaluate_all` runs all six checks, concatenates **every** `BoundaryViolation` into one
`violations` list, then picks the response's `action`/`reason_code`/`next_state` from the
**highest-priority** decision by `_priority`:
`DENY_DATA=5 > ESCALATE_HUMAN=4 > DISCLOSE_IDENTITY=3 > LOG_ONLY=2 > CONTINUE_AI=1`.
**Consequence / invariant**: a DBC-01 MAJOR can be present in `violations` while `reason_code`
reflects an unrelated higher-priority rule (e.g. ATR-01's `DENY_DATA`). **Any consumer
deciding on a specific control MUST scan `decision.violations`, never `reason_code`.** This is
exactly why `src/dbc01_review_routing.should_route_to_review()` scans `violations`.

### 3. DBC-01 is always `LOG_ONLY` by design; the review queue closes the gap
Every DBC-01 hit sets action `LOG_ONLY` (non-blocking), `next_state = "DECEPTION_FLAGGED"`.
**Why**: text-based deception detection is imperfect; auto-blocking a call on a substring match
is unacceptable. The enforcement gap is closed OUT of band: `should_route_to_review()` sends
flagged sessions to the `dbc01_review_queue` table in `nhid_event_store.py` for human
disposition. Do not "fix" DBC-01 by making it block — that inverts a deliberate design.

### 4. Two deliberate CAS implementations, one tier ladder
CAS = Call Authorization Score.
- `src/nhid_cas.py::compute_cas` — the full telemetry model, `CAS = F_IAF × F_NOCF × ECF`
  (multiplicative). Used with rich per-call telemetry.
- `functions/handler.py::_policy_cas` — a **simpler bucketed** variant for the disclosure-level
  conformance response (F_NOCF bucketed by critical-violation count).

Both funnel through the same `_tier_for_cas()` thresholds (`src/nhid_cas.py:46`): ≥0.90
Verified Trust/L2, ≥0.75 Conditional/L1, ≥0.50 Review Required, ≥0.20 Denied/Degraded, below
Hard Denial. **Why two**: the handler rarely has full NOCF telemetry. **Invariant**: routing
reads `cas["score"]`; the human-review threshold is `< CAS_CONDITIONAL_TRUST` (0.75). If the
two give different scores for the same event, that is expected — see `nhid-debugging-playbook`.

### 5. The nested `healthcare_governance` event contract
The behavioral controls read their inputs from `event["healthcare_governance"]`
(`disclosure_timestamp`, `identity_assertion_text`, `deceptive_artifact_flags`,
`escalation_timestamp`, `escalation_outcome`, `phi_accessed`) — NOT the event top level. The
top level carries ATR-01's audit fields. **Invariant**: put governance inputs in the nested
block. Storing `deceptive_artifact_flags` at top level is the classic silent-zero bug.

### 6. Sticky disclosure: a disclosure never expires
Once identity is disclosed on a turn, the disclosure (timestamp + assertion text) is carried
forward to every later turn, including caller turns. **Why**: a disclosure made once is still
true when the caller speaks. **Incident**: blanking `identity_assertion_text` on caller turns
made IDG-01 fire on essentially every post-disclosure turn.

### 7. The review queue is one-way DB-backed state
`dbc01_review_queue` rows go `pending → resolved` only (`resolve_dbc01_review` guards this);
no silent re-resolution. `UNIQUE(session_id, event_id, request_id)` + `INSERT ... ON CONFLICT
DO NOTHING` makes enqueue idempotent. **Invariant**: don't add a path that reopens a resolved
review.

### 8. Demo-vs-framework boundary inside `functions/`
`functions/handler.py` serves both framework routes and website-demo routes (`/v1/demo/*`,
Twilio/ElevenLabs demo webhooks). The demo code is fenced and must never be cited as engine
capability. See `nhid-change-control` §7.

### 9. Deterministic Ed25519 identity
`src/agent_identity.py` (NHID-Auth v2) must serialize/sign/verify deterministically — the
`identity_determinism` job in `.github/workflows/nhid-gates.yml` enforces it. **Invariant**:
identity operations are reproducible bit-for-bit.

## Known weak points (stated plainly, not masked)

| Weak point | Reality |
|---|---|
| Repo-root clutter | Many modules and generator scripts live at repo root, not under `src/`; `nhid_events.db` (a SQLite file) is **committed** to the tree and can carry state between runs. |
| Dual runtime surfaces | AWS Lambda (`functions/handler.py`) and FastAPI (`main.py`) both exist with partially duplicated logic (e.g. the two CAS variants). Changing behavior may require touching both. |
| ATR-01 untestable in replay | ATR-01 needs a full audit envelope, which transcript replay never has. It shows 0% in the confusion matrix by design; it is verified only via `tests/failure_injection_harness.py` + the CTS YAML `ATR-01-FAIL-MISSING` case. |
| DBC-01 Tier C FP cost | New production detection behavior with a measured ~4–11% FP-on-compliant rate; live-vs-gated is an **open owner decision** (Bree). |
| Substring-matching ceiling | DBC-01 detection is capped by lexical matching; residual misses are non-lexical "implied humanity." Proven, not a bug to keyword away. |

## When NOT to use this skill

- Exact control/rule_id/field definitions → `nhid-domain-reference`.
- Diagnosing a specific failure → `nhid-debugging-playbook`.
- The rules for making a change → `nhid-change-control`.
- The history behind these decisions → `nhid-failure-archaeology`.
- Running/operating the surfaces → `nhid-run-and-operate`.
- Siblings: `nhid-config-and-flags`, `nhid-build-and-env`,
  `nhid-diagnostics-and-tooling`, `nhid-validation-and-qa`, `nhid-docs-and-positioning`,
  `nhid-dbc01-semantic-ceiling-campaign`, `nhid-proof-and-analysis-toolkit`,
  `nhid-research-frontier`, `nhid-research-methodology`, `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- Priority ladder: `grep -n "_priority\|DENY_DATA\|ESCALATE_HUMAN" src/nhid_policy_engine_v1.py`.
- Internal-error path: `grep -n "_internal_error_decision\|INTERNAL_POLICY_ERROR" src/nhid_policy_engine_v1.py`.
- CAS variants: `grep -n "def compute_cas" src/nhid_cas.py` and `grep -n "_policy_cas" functions/handler.py`.
- Tier thresholds: `grep -n "_tier_for_cas\|CAS_" src/nhid_cas.py`.
- Review queue invariants: `grep -n "dbc01_review_queue\|ON CONFLICT\|resolve_dbc01_review" nhid_event_store.py`.
- Determinism gate: `grep -n "identity_determinism" .github/workflows/nhid-gates.yml`.
