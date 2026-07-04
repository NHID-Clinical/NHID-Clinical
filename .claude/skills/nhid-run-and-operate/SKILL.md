---
name: nhid-run-and-operate
description: >-
  Load when you need to RUN or OPERATE the NHID-Clinical system — call an API route,
  start the FastAPI server, work the DBC-01 human-review queue, run a batch eval over the
  corpus, or find where events/results land. Load it when asked to "check a conformance
  event", "list/resolve pending reviews", "run the eval", "start the server", "hit the
  badge endpoint", or "operate the queue". It is the operator runbook with copy-paste
  command blocks per operation; it does not teach the domain or how to change code.
  Trigger phrases: "run the conformance check", "resolve a review", "batch eval",
  "start uvicorn", "vendor badge", "where do results go".
---

# NHID-Clinical Run & Operate

Verified as of 2026-07-04. Two runtime surfaces: an AWS Lambda handler and a FastAPI dev
server. Plus operator CLIs for the review queue and batch evals.

## Surface 1 — Lambda API (`functions/handler.py`)

Routes (from the handler docstring; `— API key required` where noted). `X-API-Key` is checked
against `NHID_API_KEY`.

| Route | Auth |
|---|---|
| `GET /health` | none |
| `POST /v1/conformance/check` | API key |
| `POST /v1/demo/check` | none |
| `POST /v1/adapters/{vapi,twilio,vonage,retell,connect}/check` | none |
| `POST /v1/webhooks/call-progress` | (turn-by-turn) |
| `GET /v1/public/vendor/{id}/badge` | none (SVG badge) |
| `GET /v1/vendor/metrics/summary` | API key |
| `POST /v1/pilot/enroll` | (pilot enrollment) |
| `POST /v1/cts/evaluate` | (conformance-suite eval) |
| `POST /v1/identity/verify-passport` | NHID-Auth v2 |
| `/v1/webhooks/twilio-demo/voice`, `/v1/demo/call*`, `/v1/demo/sms-opt-in`, `/v1/webhooks/elevenlabs/postcall` | **DEMO — fenced, not framework** |

The conformance response includes `conformant`, `action`, `reason_code`, `violations[]`,
`next_state`, `cas` (with `score`, `tier`), and a `human_review` block
(`{queued, trigger_reason, queue_id}`).

## Surface 2 — FastAPI dev server (`main.py`)

```bash
uvicorn app:app --reload --port 8000     # app.py's voice_app, mounted at /voice by main.py
# or: python main.py   (uvicorn on 0.0.0.0:8000)
```

`main.py` (v1.4.0) mounts `app.py`'s `voice_app` at `/voice` and includes routers
`nhid_api_endpoints`, `nhid_attest`, `nhid_payer`, `nhid_audit_export`. `GET /health`.
`X-API-Key` gate vs `NHID_API_KEY`. This is the server the 18 integration tests need.

## Operate the DBC-01 human-review queue (end to end)

1. A conformance check whose decision carries a DBC-01 violation, OR whose CAS score
   `< 0.75` (`CAS_CONDITIONAL_TRUST`), is routed by `should_route_to_review()` and enqueued
   into the `dbc01_review_queue` table.
2. List pending reviews:
   ```bash
   python3 scripts/resolve_dbc01_review.py --list
   ```
3. Resolve one (one-way: `pending → resolved`):
   ```bash
   python3 scripts/resolve_dbc01_review.py --resolve <QUEUE_ID> \
     --disposition confirmed_impersonation \
     --reviewer "your-name" --notes "optional"
   # --disposition must be: confirmed_impersonation | false_positive
   ```
A resolved review cannot be silently re-resolved. See `nhid-architecture-contract` §7.

## Run a batch eval over the corpus

Direct confusion matrix (recommended — see `nhid-diagnostics-and-tooling`):
```bash
python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv
```
Or convert then batch-eval:
```bash
python3 adapters/fabricate_adapter.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv --out conversations.json
python3 scripts/run_batch_eval.py conversations.json
```
`fabricate_adapter.py` also accepts a single JSONL corpus: `... <corpus.jsonl> --out out.json`.

## Where things land

`nhid_event_store.py` (SQLite `nhid_events.db` at repo root) tables:
`events`, `processed_requests`, `conformance_results`, `revoked_delegations`,
`dbc01_review_queue`. Override the path with `NHID_EVENT_DB`.

## When NOT to use this skill

- Setting up the environment from scratch → `nhid-build-and-env`.
- Interpreting the eval numbers → `nhid-diagnostics-and-tooling`.
- What a route's decision *means* → `nhid-domain-reference`.
- Config/env values → `nhid-config-and-flags`.
- Something broke → `nhid-debugging-playbook`.
- Siblings: `nhid-change-control`, `nhid-failure-archaeology`,
  `nhid-architecture-contract`, `nhid-validation-and-qa`, `nhid-docs-and-positioning`,
  `nhid-dbc01-semantic-ceiling-campaign`, `nhid-proof-and-analysis-toolkit`,
  `nhid-research-frontier`, `nhid-research-methodology`, `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- Routes: `sed -n '40,62p' functions/handler.py`.
- Server command: `sed -n '1,25p' tests/failure_injection_harness.py` and `grep -n "mount\|include_router" main.py`.
- Review CLI: `python3 scripts/resolve_dbc01_review.py --help`.
- Adapter CLI: `sed -n '48,56p' adapters/fabricate_adapter.py`.
- Tables: `grep -n "CREATE TABLE" nhid_event_store.py`.
