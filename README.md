# NHID-Clinical

A voluntary, early-stage proposal for AI voice agent behavior in healthcare payer–provider calls.

**Not a standard. Not a certification. Built by one person based on time spent in payer operations.**

**Status: Reference implementation — production-ready for demos and pilots, not yet battle-tested at scale.**

Website: [nhid-clinical.org](https://nhid-clinical.org)

---

## The problem in one sentence

AI voice agents call payer offices, collect operational data, and only disclose they're automated when challenged — sometimes minutes into the call. And with a real NPI from the public NPPES registry, they can impersonate any provider.

## What this proposes

Four behaviors (v1.3) + cryptographic agent authorization (v1.4):

1. Identify as automated before asking for any data
2. No audio designed to sound human (fake breathing, filler, call center noise)
3. Immediate transfer to a human on request
4. Basic log: what happened and when
5. **(v1.4)** Delegated agent passport signed by the provider's private key — a public NPI alone is no longer sufficient

---

## What's new in v1.4

The core gap in v1.3 was authorization: an AI agent could provide a real, public NPI from NPPES and pass identity checks. Any caller with internet access could do the same.

v1.4 closes that with seven concrete fixes to `src/agent_identity.py`:

1. **NPI binding** — `create_delegation()` now accepts a `provider_npi` parameter; every passport is cryptographically bound to a specific 10-digit NPI
2. **UUID delegation IDs** — replaced the deterministic `del_{agent_id}_{timestamp}` ID with UUID4; no more predictable or colliding IDs
3. **Canonical signing** — `to_json()` uses `sort_keys=True` for deterministic byte output across all Python runtimes
4. **Scope enforcement** — `verify_passport()` accepts `required_scope`; a delegation for `["eligibility"]` cannot be used for `"prior_auth"`
5. **Per-delegation revocation** — `revoke_delegation(delegation_id)` revokes one specific token without killing all delegations for that agent
6. **Chain validation** — `validate_chain()` verifies up to 3-hop delegation chains with monotonic scope narrowing (no sub-delegate can claim broader scope than they were given)
7. **Structured error codes** — `ERR_EXPIRED`, `ERR_REVOKED`, `ERR_INVALID_SIG`, `ERR_NONCE_MISMATCH`, `ERR_SCOPE_VIOLATION`, `ERR_INVALID_NPI`, `ERR_CHAIN_NARROWING`, `ERR_CHAIN_TOO_LONG`

```python
# v1.4 payer verification — NPI is now bound and verified, not a placeholder
result = manager.verify_passport(passport, provider_pub, required_scope=["eligibility"])
# result.provider_npi == "1234567890"   ← cryptographically verified
# result.valid == False unless caller holds provider's private key
```

See [`examples/issue_and_verify.py`](examples/issue_and_verify.py) for a full runnable walkthrough.

**Honest limitations:** Provider key management is still on the honor system — this implementation doesn't solve key distribution. Revocation is in-memory only; production needs a CRL or short-TTL enforcement. FHIR export is basic AuditEvent format; no deep Provenance or Consent resource mappings yet.

---

## Repo structure

```
schema/       Canonical event schema (JSON Schema Draft 2020-12)
conformance/  Machine-readable conformance test cases (YAML)
src/          Policy engine + cryptographic identity layer (pure Python)
tests/        pytest suite — unit tests + integration harness + trace generator
traces/       10 pre-generated failure traces
examples/     Runnable end-to-end demos
```

## How to run and verify

### Install

```bash
git clone https://github.com/thankcheeses/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
```

### Run unit tests

```bash
pytest tests/ -q
```

Expected output:

```
95 passed, 18 skipped
```

(18 integration tests auto-skip when no server is running — expected.)

### Run the v1.4 example

```bash
python examples/issue_and_verify.py
```

Shows: key generation → NPI-bound delegation → passport → scope enforcement → per-delegation revocation → 2-hop chain validation.

### What you are verifying

- **Deterministic policy engine** — identical input, identical output; IDG-01, PDX-01, DBC-01, EIT-01, ATR-01
- **Cryptographic identity layer** — Ed25519 delegation, call-bound nonces, revocation
- **Chain validation** — monotonic scope narrowing across agent hops
- **Audit-safe trace behavior** — event records complete and append-only

---

## Artifacts

| File | What it does |
|---|---|
| `schema/nhid_trace_schema_v1.json` | Event schema every pipeline stage emits against |
| `conformance/nhid_conformance_test_suite_v1.yaml` | 18 machine-readable pass/fail/edge conformance cases |
| `src/nhid_policy_engine_v1.py` | Evaluates IDG-01, PDX-01, DBC-01, EIT-01, ATR-01. Never raises. |
| `src/voice_policy.py` | Policy engine with global safety phrases, PHI gate, ruleset evaluation |
| `src/agent_identity.py` | Ed25519 passports, NPI binding, scope enforcement, chain validation (v1.4) |
| `tests/test_voice_policy.py` | 70 unit tests — policy engine correctness |
| `tests/test_identity.py` | 25 unit tests — identity layer (5 original + 20 new in v1.4) |
| `tests/failure_injection_harness.py` | Integration tests (auto-skip without server) |
| `examples/issue_and_verify.py` | Runnable v1.4 passport demo |
| `traces/` | 10 pre-generated failure traces |

---

## Status

- No payer or vendor has adopted this yet
- Working schema, policy engine, conformance suite, trace generator, and cryptographic identity layer
- Actively looking for feedback from payer ops, provider-side AI teams, health IT

## Contact

[contact@nhid-clinical.org](mailto:contact@nhid-clinical.org) · CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026
