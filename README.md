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
schema/     Canonical event schema (JSON Schema Draft 2020-12)
src/        Policy engine + cryptographic identity layer (pure Python)
tests/      Conformance suite (YAML) + failure harness (pytest) + trace generator
adapters/   Vendor format adapters (Twilio → NHID trace)
traces/     10 pre-generated failure traces
```

## Quick start

```bash
git clone https://github.com/thankcheeses/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
python -m pytest tests/ -v
```

Expected output: `25 passed, 18 skipped` — the 18 skipped are integration tests that require a live server at `http://127.0.0.1:8000` and are automatically skipped if none is running.

```bash
# Generate all 10 failure traces (no server needed)
python tests/trace_generator.py --offline

# Run the Twilio adapter demo
python adapters/twilio_adapter.py
```

## Artifacts

| File | What it does |
|---|---|
| `schema/nhid_trace_schema_v1.json` | Event schema every pipeline stage emits against |
| `src/nhid_policy_engine_v1.py` | Evaluates IDG-01, PDX-01, DBC-01, EIT-01, ATR-01. Never raises. |
| `src/agent_identity.py` | Ed25519 agent passports, delegation chains, revocation (v1.4 preview) |
| `tests/nhid_conformance_test_suite_v1.yaml` | 18 machine-readable pass/fail/edge test cases |
| `tests/failure_injection_harness.py` | pytest suite — chaos inputs, policy evaluation, replay determinism |
| `tests/test_identity.py` | 4 tests: key generation, delegation, expiry, revocation |
| `tests/trace_generator.py` | Writes 10 failure traces to `/traces/`. Same output every run. |
| `adapters/twilio_adapter.py` | Maps Twilio transcripts to NHID-Clinical event traces |

## Status

- No payer or vendor has adopted this yet
- Working schema, policy engine, conformance suite, and trace generator
- Actively looking for feedback from payer ops, provider-side AI teams, health IT

## Contact

[contact@nhid-clinical.org](mailto:contact@nhid-clinical.org) · CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026
