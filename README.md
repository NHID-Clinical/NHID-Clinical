# NHID-Clinical

Voluntary proposal for non-human identity disclosure in healthcare payer–provider voice workflows.

**This is a pre-standardization open proposal by Brianna Baynard — not an accredited standard, regulatory requirement, or certification authority.**

Website: [nhid-clinical.org/specification.html](https://nhid-clinical.org/specification.html)

---

## Repo structure

```
schema/     JSON Schema (Draft 2020-12) for NHID canonical event objects
src/        Policy engine — pure Python, no I/O, fully deterministic
tests/      Conformance test suite (YAML) + failure harness (pytest) + trace generator
traces/     10 pre-generated trace files, one per failure mode
```

---

## Quick start

```bash
git clone https://github.com/thankcheeses/NHID-Clinical.git
cd NHID-Clinical
git checkout claude/code-review-fixes-98Ir1
pip install -r requirements.txt

# Run unit tests (no server needed)
python -m pytest tests/failure_injection_harness.py -v -k "not integration"

# Generate all 10 failure traces
python tests/trace_generator.py --offline

# Validate schema is well-formed JSON Schema
python -m jsonschema schema/nhid_trace_schema_v1.json
```

Integration tests (against a live FastAPI server) are auto-skipped if nothing is running at `http://127.0.0.1:8000`.

---

## Artifacts

| File | What it is |
|---|---|
| `schema/nhid_trace_schema_v1.json` | Canonical event schema. Every pipeline stage emits objects conforming to this. |
| `src/nhid_policy_engine_v1.py` | Evaluates IDG-01, PDX-01, DBC-01, EIT-01, ATR-01. Returns a `PolicyDecision` dataclass. Never raises. |
| `tests/nhid_conformance_test_suite_v1.yaml` | 18 machine-readable test cases (pass/fail/edge) loadable by any YAML-aware test runner. |
| `tests/failure_injection_harness.py` | pytest suite — sends chaos inputs (null bytes, missing fields, replay) to a FastAPI endpoint. |
| `tests/trace_generator.py` | CLI; writes 10 markdown traces to `/traces/`. Deterministic: identical output on every run. |

---

## Conformance tests

| ID | What it checks |
|---|---|
| IDG-01 | AI discloses non-human identity before any data exchange |
| PDX-01 | PHI request blocked when disclosure has not yet occurred |
| DBC-01 | No deceptive audio artifacts (fake breathing, scripted hesitation) |
| EIT-01 | Escalation path to a human is available and immediate |
| ATR-01 | Audit trail contains required fields (`disclosure_timestamp`, `escalation_outcome`, `phi_accessed`) |

---

## What this is not

- Not a compliance certification
- Not an audit program
- Not a HIPAA or TCPA legal requirement
- Not a registry or enforcement body

Self-administered conformance only. No external authority validates results.

---

## License

CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 · [contact@nhid-clinical.org](mailto:contact@nhid-clinical.org)
