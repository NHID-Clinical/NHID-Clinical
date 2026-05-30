# NHID-Clinical

A voluntary, early-stage proposal for AI voice agent behavior in healthcare payer–provider calls.

**Not a standard. Not a certification. Built by one person based on time spent in payer operations.**

Website: [nhid-clinical.org](https://nhid-clinical.org)

---

## The problem in one sentence

AI voice agents call payer offices, collect operational data, and only disclose they're automated when challenged — sometimes minutes into the call.

## What this proposes

Four behaviors:

1. Identify as automated before asking for any data
2. No audio designed to sound human (fake breathing, filler, call center noise)
3. Immediate transfer to a human on request
4. Basic log: what happened and when

## Repo structure

```
schema/       Canonical event schema (JSON Schema Draft 2020-12)
conformance/  Machine-readable conformance test cases (YAML)
src/          Policy engine + cryptographic identity layer (pure Python)
tests/        pytest suite — unit tests + integration harness + trace generator
traces/       10 pre-generated failure traces
```

## How to Run and Verify NHID-Clinical

### Install

```bash
git clone https://github.com/thankcheeses/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
```

### Run unit tests (core deterministic engine)

```bash
pytest tests/ -q
```

Expected output (no server required):

```
Unit invariant preserved: 72 passed, 0 skipped
Integration suite: 18 tests, may pass or skip (expected)
```

### What you are verifying

- **Deterministic policy engine correctness** — identical input always produces identical output
- **Reproducible evaluation logic** — IDG-01, PDX-01, DBC-01, EIT-01, ATR-01 rule enforcement
- **Audit-safe trace behavior** — event records are complete and append-only

### Run integration tests (optional system validation)

Integration tests require a live NHID-Clinical server at `http://127.0.0.1:8000`. They auto-skip cleanly when no server is present and are not required to verify policy engine correctness.

```bash
pytest tests/
```

Unit invariant preserved: 72 passed, 0 skipped
Integration suite: 18 tests, may pass or skip (expected)

## API Endpoints

### Public Endpoints (no auth required)

GET /v1/compliance/states
Returns US state AI disclosure requirements mapped to NHID-Clinical rules.

GET /v1/attest/verify/{reference_id}
Payers call this during a live voice call to verify an AI caller's attestation.
Returns: valid, delegating_entity, authorized_actor, scope, expires_at, revoked, expired

### Authenticated Endpoints (X-API-Key required)

POST /v1/policy/evaluate
Evaluates a voice transcript against NHID-Clinical policy rules.
Request: { "session_id": "call_123", "agent_id": "vendor_1", "transcript_text": "I want to speak to a human", "disclosure_confirmed": true }
Response: { "action": "escalate", "reason_code": "HUMAN_ESCALATION_REQUESTED", "policy_version": "VOICE-POLICY-v1.0" }

POST /v1/attest
Vendors call this to generate a signed attestation proving delegated authority from a provider.
Request: { "delegating_entity": "NPI-1234567890", "authorized_actor": "vendor-id", "scope": ["claims_inquiry"], "expires_at": "2027-01-01T00:00:00Z" }
Response: { "reference_id": "uuid", "token": "signed-jwt", "revocation_endpoint": "/v1/attest/revoke/uuid" }

POST /v1/payer/screen
Payers call this to screen an incoming AI call before exchanging any data.
Request: { "caller_npi": "1234567890", "reference_id": "uuid", "requested_scope": "claims_inquiry" }
Response: { "verified": true, "compliant": true, "recommended_action": "accept", "reason": "..." }


## Artifacts

| File | What it does |
|---|---|
| `schema/nhid_trace_schema_v1.json` | Event schema every pipeline stage emits against |
| `conformance/nhid_conformance_test_suite_v1.yaml` | 18 machine-readable pass/fail/edge conformance cases |
| `src/nhid_policy_engine_v1.py` | Evaluates IDG-01, PDX-01, DBC-01, EIT-01, ATR-01. Never raises. |
| `src/voice_policy.py` | Full policy evaluation functions with deterministic return types |
| `src/agent_identity.py` | Ed25519 agent passports, delegation chains, revocation (v1.4 preview) |
| `tests/test_voice_policy.py` | 47 unit tests — policy engine correctness, no server required |
| `tests/test_identity.py` | 4 unit tests — identity layer correctness, no server required |
| `tests/failure_injection_harness.py` | 21 unit tests + 18 integration tests (auto-skip when no server present) |
| `tests/trace_generator.py` | Writes 10 failure traces to `traces/`. Same output every run. |

## Status

- No payer or vendor has adopted this yet
- Working schema, policy engine, conformance suite, and trace generator
- Actively looking for feedback from payer ops, provider-side AI teams, health IT

## Contact

[contact@nhid-clinical.org](mailto:contact@nhid-clinical.org) · CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026
