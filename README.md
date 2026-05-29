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
72 passed, 18 skipped
```

The 72 unit tests verify deterministic policy engine correctness. They require no server, no API keys, and no accounts. **72 unit tests must pass with zero skips.** If any of the 72 show as skipped, something in the environment is broken.

The 18 skipped tests are integration tests — skipping is expected behavior when no server is running.

### What you are verifying

- **Deterministic policy engine correctness** — identical input always produces identical output
- **Reproducible evaluation logic** — IDG-01, PDX-01, DBC-01, EIT-01, ATR-01 rule enforcement
- **Audit-safe trace behavior** — event records are complete and append-only

### Run integration tests (optional system validation)

Integration tests require a live NHID-Clinical server at `http://127.0.0.1:8000`. They auto-skip cleanly when no server is present and are not required to verify policy engine correctness.

```bash
pytest tests/
```

Expected when no server running: `72 passed, 18 skipped`  
Expected when server running: `90 passed, 0 skipped`

Integration tests validate end-to-end policy enforcement, trace reproducibility, and conformance against a running implementation.

## Artifacts

| File | What it does |
|---|---|
| `schema/nhid_trace_schema_v1.json` | Event schema every pipeline stage emits against |
| `conformance/nhid_conformance_test_suite_v1.yaml` | 18 machine-readable pass/fail/edge conformance cases |
| `src/nhid_policy_engine_v1.py` | Evaluates IDG-01, PDX-01, DBC-01, EIT-01, ATR-01. Never raises. |
| `src/voice_policy.py` | Full policy evaluation functions with deterministic return types |
| `src/agent_identity.py` | Ed25519 agent passports, delegation chains, revocation (v1.4 preview) |
| `tests/test_voice_policy.py` | 54 unit tests — policy engine correctness, no server required |
| `tests/test_identity.py` | 18 unit tests — identity layer correctness, no server required |
| `tests/failure_injection_harness.py` | 18 integration tests — auto-skip when no server present |
| `tests/trace_generator.py` | Writes 10 failure traces to `traces/`. Same output every run. |

## Status

- No payer or vendor has adopted this yet
- Working schema, policy engine, conformance suite, and trace generator
- Actively looking for feedback from payer ops, provider-side AI teams, health IT

## Contact

[contact@nhid-clinical.org](mailto:contact@nhid-clinical.org) · CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026
