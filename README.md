# NHID-Clinical

[![CI](https://github.com/NHID-Clinical/NHID-Clinical/actions/workflows/ci.yml/badge.svg)](https://github.com/NHID-Clinical/NHID-Clinical/actions)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![NIST Submission](https://img.shields.io/badge/NIST-2025--0035--0026-blue)](https://www.regulations.gov/comment/NIST-2025-0035-0026)
[![Version](https://img.shields.io/badge/Version-v1.3%20Open%20Core-green)](https://nhid-clinical.org/specification.html)

A voluntary, early-stage proposal for AI voice agent behavior in healthcare payer–provider calls.

**Not a standard. Not a certification. Built by one person based on time spent in payer operations.**

Website: [nhid-clinical.org](https://nhid-clinical.org)

---

## The Five-Layer Trust Stack

| Layer | Standard | Role |
| :--- | :--- | :--- |
| **0** | NPI Gap | The problem — no existing diagram addresses cross-org NPI authorization |
| **1** | STIR/SHAKEN (RFC 8224) | Carrier number authentication — A/B/C attestation |
| **2** | **NHID-Clinical v1.3** | Behavioral disclosure baseline — 4 controls, 5 CTS tests |
| **3** | NHID-Auth v2 (Ed25519 + DPoP) | Delegation chain + call-nonce binding (v2 roadmap) |
| **4** | FHIR AuditEvent R4 / IHE BALP | Healthcare-native audit logging |
| **5** | OpenTelemetry spans | SIEM / enterprise observability export |

[Full technical architecture →](https://nhid-clinical.org/technical-stack.html)

---

## Regulatory Alignment

| Regulatory Driver | Specific Requirement | NHID-Clinical Control |
| :--- | :--- | :--- |
| **CMS-0057-F** | FHIR API, 72hr turnaround, 5yr retention | FHIR AuditEvent + ATR-01 |
| **MACPAC May 2026** | AI transparency, human review | EIT-01 + ATR-01 |
| **DOJ FCA 2026** | Explainability + audit trail | LOG + CTS evidence |
| **State AI Laws** | Inspectable, auditable AI decisions | IDG-01 + DBC-01 |
| **NIST CAISI 2026** | Cross-org agent identity | NHID-Auth v2 |

[Full regulatory alignment matrix →](https://nhid-clinical.org/regulatory-alignment.html)

---

## Repository Structure

| Code | Built With |
| :--- | :--- |
| `schema/` | Canonical event schema (JSON Schema Draft 2020-12) |
| `src/` | Policy engine + cryptographic identity layer (pure Python) |
| `tests/` | Conformance suite (YAML) + failure harness (pytest) + trace generator |
| `traces/` | 10 pre-generated failure traces |

## Quick Start

```bash
git clone https://github.com/NHID-Clinical/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
python -m pytest tests/ -v
```

Expected output: `173 passed, 18 skipped` in ~1.4s.

---

## NIST Submission

Submitted to NIST docket **NIST-2025-0035** · Comment ID: **NIST-2025-0035-0026**

## v2 Roadmap (Locked Commercial Tier)

v1.3 closes the disclosure gap. **v2 closes the authorization gap** — Ed25519 delegation chains, scope attenuation, revocation, call-bound nonces. Targeting Q3 2026. [Full roadmap →](https://nhid-clinical.org/roadmap.html)

## Contributing

[Community](https://nhid-clinical.org/community.html) · [Discord](https://discord.gg/CU7BwHwVYC) · [contact@nhid-clinical.org](mailto:contact@nhid-clinical.org)

CC BY 4.0 · Brianna Baynard · [nhid-clinical.org](https://nhid-clinical.org)
