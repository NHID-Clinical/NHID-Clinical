<div align="center">

# NHID-Clinical

**Non-Human Identity Disclosure Standard for Healthcare Voice Workflows**

A minimum, voluntary, testable control baseline for non-human identity disclosure in B2B healthcare administrative voice interactions.

[![Spec](https://img.shields.io/badge/spec-v1.3-blue?style=flat-square)](https://nhid-clinical.org/specification.html)
[![Implementation](https://img.shields.io/badge/impl-v1.4-005a9c?style=flat-square)](https://github.com/thankcheeses/NHID-Clinical/releases)
[![Tests](https://img.shields.io/badge/tests-95%20passing-brightgreen?style=flat-square)](#evidence)
[![License](https://img.shields.io/badge/spec%20license-CC%20BY%204.0-blue?style=flat-square)](LICENSE)
[![NIST](https://img.shields.io/badge/NIST-docket%20AI--2025--0035-005a9c?style=flat-square)](https://www.regulations.gov/comment/NIST-2025-0035-0026)
[![Status](https://img.shields.io/badge/status-pilot--ready-orange?style=flat-square)](https://nhid-clinical.org)

[Website](https://nhid-clinical.org) · [Specification](https://nhid-clinical.org/specification.html) · [NIST Submission](https://www.regulations.gov/comment/NIST-2025-0035-0026) · [Pilot Program](https://nhid-clinical.org/pilot.html)

</div>

---

## The Problem

A payer representative answers an eligibility call. The voice on the line is fluent, professional, and asking for PHI. They cannot tell — in the first thirty seconds — whether they are talking to a human or an AI agent.

This is **impersonation latency**: the gap between when an AI voice agent connects to a payer line and when the human operator can reliably identify it as non-human. Existing frameworks do not address this.

NHID-Clinical addresses that gap.

## What This Is

A voluntary minimum control baseline. Five normative requirements. Five deterministic conformance tests. Three certification tiers. Technology-agnostic.

| Tier | Method | Audience |
|------|--------|----------|
| **L1** | Self-attestation | Vendors entering market |
| **L2** | Evidence-backed | Vendors with operational data |
| **L3** | Independent audit | Payer-facing production deployments |

## What This Is Not

- Not a replacement for HIPAA, TCPA, or state AI disclosure law
- Not a voice biometrics or anti-fraud spec — see Pindrop, Nuance for that layer
- Not consumer-facing — strictly B2B provider-to-payer administrative workflows
- Not a procurement requirement (yet)

## Open Core vs Commercial

NHID-Clinical follows an open-core model. The specification is and will remain freely available under CC BY 4.0. The cryptographic identity layer and tier-3 certification infrastructure are commercial.

| Component | License | Status |
|-----------|---------|--------|
| Specification (v1.3) | CC BY 4.0 | Open, stable, NIST-submitted |
| Five normative controls + CTS tests | CC BY 4.0 | Open |
| Reference implementation (voice policy, PHI gating, FHIR mapping) | Open source | Open |
| NHID-Auth identity layer (Ed25519 passports, delegation chains) | Commercial | Pilot partners |
| L3 certification badge + cryptographic verification | Commercial | Pilot partners |

For pilot access to commercial features: [nhid-clinical.org/pilot.html](https://nhid-clinical.org/pilot.html)

## Evidence

Reference implementation. 95 tests passing covering identity, voice policy, and failure injection.

<div align="center">

https://github.com/user-attachments/assets/13a8d270-7787-43fc-bdad-87415fb23c85

</div>

```
============================= test session starts =============================
collected 113 items

tests/failure_injection_harness.py ....................                  [ 17%]
tests/test_identity.py .........................                         [ 39%]
tests/test_voice_policy.py ..............................                [ 65%]
tests/test_voice_policy.py ........................................      [100%]

================== 95 passed, 18 skipped in 4.45s =============================
```

## Quickstart

```bash
git clone https://github.com/thankcheeses/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
pytest
```

Run the reference server:

```bash
uvicorn src.main:app --reload
# OpenAPI docs at http://localhost:8000/docs
```

Live backend: `https://nhid-clinical-production.up.railway.app/health`

## The Five Controls

1. **Proactive disclosure** — automated status declared before protected data exchange
2. **Authorization verification** — caller authority verifiable by the receiving party
3. **Safe escalation** — globally enforced human-handoff phrases that tenant config cannot silence
4. **PHI gating** — protected information blocked until disclosure state is confirmed
5. **Auditable trail** — FHIR AuditEvent mapping for every disclosure decision

See [`docs/specification.md`](docs/specification.md) for normative language.

## Repository Layout

```
NHID-Clinical/
├── docs/                  Specification, FHIR mapping, conformance tests
├── src/
│   ├── agent_identity.py  Ed25519 identity passport + delegation chain
│   ├── voice_policy.py    Disclosure state machine and safety phrases
│   └── main.py            FastAPI reference server
├── tests/                 95 passing tests
└── site/                  nhid-clinical.org source
```

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

## Pilot Program

No-cost validation for healthcare voice AI vendors and payer operations teams. The pilot tests one outbound or inbound workflow against the L1 or L2 conformance criteria and returns a written assessment and pathway.

Request access: [nhid-clinical.org/pilot.html](https://nhid-clinical.org/pilot.html)

## Status

- No payer or vendor has adopted this yet
- Working schema, policy engine, conformance suite, trace generator, and cryptographic identity layer
- Actively looking for feedback from payer ops, provider-side AI teams, health IT

## Citation

```bibtex
@misc{nhidclinical2026,
  author       = {Baynard, Brianna},
  title        = {NHID-Clinical: Non-Human Identity Disclosure Standard for Healthcare Voice Workflows},
  year         = {2026},
  version      = {1.4},
  url          = {https://nhid-clinical.org},
  note         = {Submitted to NIST AI Safety Institute, docket NIST-2025-0035-0026}
}
```

## License

- **Specification and documentation**: [CC BY 4.0](LICENSE)
- **Reference implementation**: Open source, see [LICENSE](LICENSE)
- **NHID-Auth and L3 certification components**: Commercial license, contact for terms

## Contact

- **Website**: [nhid-clinical.org](https://nhid-clinical.org)
- **Email**: [contact@nhid-clinical.org](mailto:contact@nhid-clinical.org)
- **Author**: Brianna Baynard
- **NIST docket**: [NIST-2025-0035-0026](https://www.regulations.gov/comment/NIST-2025-0035-0026)
