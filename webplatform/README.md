# NHID-Clinical Web Platform

A unified, demo-ready web platform for the NHID-Clinical conformance framework.
It is a **thin FastAPI layer over the existing codebase** — the policy engine,
Lambda handler, event store, synthetic eval loop, vendor adapters, and NHID-Auth v2
identity manager are all imported and reused. **No policy logic is reimplemented.**

## Run it (one command, from a fresh clone)

```bash
bash webplatform/start.sh
# → http://localhost:8080
```

`start.sh` creates a virtualenv, installs the repo + web-layer requirements, and
launches uvicorn. Set `PORT=9000` to change the port. Data is written to a
platform-local SQLite DB (`webplatform/nhid_platform.db`) so the committed
`nhid_events.db` is never touched.

Manual alternative (from the repo root, deps already installed):

```bash
python -m uvicorn webplatform.app:app --host 0.0.0.0 --port 8080
```

> The package is named `webplatform` (not `platform`) on purpose — a top-level
> `platform` package would shadow Python's stdlib `platform` module and break uvicorn.

## Pages

| Page | Route | What it does | Audience |
|---|---|---|---|
| Dashboard | `/` | CAS trust-tier distribution, per-control detection rates, audit KPIs | Payer executives |
| Transcript Analyzer | `/analyzer` | Runs a transcript through the live engine (decision + CAS + violations + review routing) | Ops / QA |
| Synthetic Generator | `/generator` | Runs the real eval loop over the Fabricate corpus; ingests events | Your team |
| Vendor Verification | `/vendors` | Adapter conformance check + Ed25519 passport verify (with tamper demo) | Vendors |
| Audit Log | `/audit` | Durable event trail + DBC-01 human-review queue (one-way resolution) | Regulators |

## API (all return real engine output)

- `GET  /api/health`
- `GET  /api/dashboard` · `POST /api/dashboard/refresh`
- `GET  /api/scenarios`
- `POST /api/analyze`  `{scenario}` or `{turns, conversation_id}`
- `POST /api/generate` `{sample_size, persist}`
- `POST /api/verify/passport` `{tamper}` or `{mode:"supplied", passport:{…}}`
- `POST /api/adapters/{vendor}/check`  (vendor ∈ vapi, twilio, vonage, retell, connect)
- `GET  /api/audit/events?limit=N` · `GET /api/audit/reviews`
- `POST /api/audit/reviews/{id}/resolve` `{disposition}`

## Tests

```bash
python -m pytest webplatform/tests -q
```

Every route is exercised through FastAPI's TestClient against the real engine.

## How it wires to the existing code

`webplatform/nhid_bridge.py` is the only seam. It imports:

- `functions.handler.lambda_handler` — conformance, adapter, and passport routes
- `nhid_event_store` — durable events, conformance results, DBC-01 review queue
- `src.synthetic_eval_loop` + `adapters.fabricate_adapter` — generator & detection rates
- `src.nhid_cas` — CAS thresholds
- `src.agent_identity.AgentIdentityManager` — mint/verify demo passports

If it exists in the repo, the platform calls it. Nothing is duplicated.
