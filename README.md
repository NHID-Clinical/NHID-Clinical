# NHID-Clinical

**A voluntary behavioral baseline for AI voice agents in B2B healthcare payer–provider calls — with an open cryptographic authorization layer (v2) in reference implementation.**

Built by a former payer operations associate who saw the problem firsthand on live calls. Not a standard. Not a certification. An open, testable reference.

[![CI](https://github.com/NHID-Clinical/NHID-Clinical/actions/workflows/ci.yml/badge.svg)](https://github.com/NHID-Clinical/NHID-Clinical/actions)
[![Tests](https://img.shields.io/badge/tests-327%20passing-brightgreen)](https://github.com/NHID-Clinical/NHID-Clinical/actions)
[![Version](https://img.shields.io/badge/version-v1.3-0b6ebc)](https://nhid-clinical.org/specification.html)
[![License: CC BY 4.0](https://img.shields.io/badge/license-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/)
[![NIST](https://img.shields.io/badge/NIST-2025--0035--0026-blue)](https://www.regulations.gov/comment/NIST-2025-0035-0026)
[![Discord](https://img.shields.io/badge/Discord-join-5865f2?logo=discord&logoColor=white)](https://discord.gg/CU7BwHwVYC)

[Website](https://nhid-clinical.org) · [Simulator](https://nhid-clinical.org/simulator.html) · [Spec](https://nhid-clinical.org/specification.html) · [v2 Identity Layer](https://nhid-clinical.org/roadmap.html) · [Discord](https://discord.gg/CU7BwHwVYC)

## Live API — Try It Now

The conformance API is live. No signup, no key required for the demo and vendor adapter routes.

```bash
# Test a non-compliant VAPI call (PHI requested before identity disclosure → IDG-01 + PDX-01 FAIL)
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/adapters/vapi/check \
  -H "Content-Type: application/json" \
  -d @tests/demo_scenarios/vapi_noncompliant.json | python3 -m json.tool
```

```json
{
  "conformant": false,
  "action": "DENY_DATA",
  "violations": [
    { "rule_id": "IDG-01", "severity": "critical" },
    { "rule_id": "PDX-01", "severity": "critical" }
  ]
}
```

| Endpoint | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /v1/demo/check` | none | Raw NHID event → conformance result |
| `POST /v1/adapters/vapi/check` | none | Native VAPI payload → conformance result |
| `POST /v1/adapters/twilio/check` | none | Native Twilio payload → conformance result |
| `POST /v1/adapters/vonage/check` | none | Native Vonage payload → conformance result |
| `POST /v1/adapters/retell/check` | none | Native Retell AI payload → conformance result |
| `POST /v1/adapters/connect/check` | none | Amazon Connect Contact Lens → conformance result |
| `POST /v1/webhooks/call-progress` | none | Turn-by-turn in-call evaluation |
| `GET /v1/public/vendor/{id}/badge` | none | Public CAS badge SVG (embeddable) |
| `GET /v1/vendor/metrics/summary` | `x-api-key` | Per-vendor pass rate + CAS trend |
| `POST /v1/pilot/enroll` | none | Shadow pilot enrollment |
| `POST /v1/conformance/check` | `x-api-key` | Production conformance check |

**New here?** Start with the [5-minute quickstart](docs/5-minute-quickstart.md), then the [staged v2 integration guide](docs/v2-integration-guide.md) (Tier 0: 15 min → Tier 2: 1 day).

---

## The Four Controls

| Control | Name | Requirement |
| :--- | :--- | :--- |
| **IDG-01** | Identity Disclosure Gate | AI agent must identify itself as automated **before** any PHI exchange |
| **PDX-01** | PHI Data Exchange Gate | No protected data until identity is disclosed |
| **DBC-01** | Deceptive Behavior Check | No synthetic voice artifacts designed to impersonate a human |
| **EIT-01** | Escalation & Intervention | Human escalation path must be communicated and available |

5 deterministic CTS tests · same inputs → identical trace output · 327 passing across the Python test suite (261) and TypeScript middleware (66)

---

## Five-Layer Trust Stack

| Layer | Standard | Role |
| :--- | :--- | :--- |
| **0** | NPI Gap | The problem — no existing diagram addresses cross-org NPI authorization |
| **1** | STIR/SHAKEN (RFC 8224) | Carrier number authentication — A/B/C attestation |
| **2** | **NHID-Clinical v1.3** | Behavioral disclosure baseline — 4 controls, 5 CTS tests |
| **3** | NHID-Auth v2 | Cryptographic authorization layer — reference implementation live (CC BY 4.0) |
| **4** | FHIR AuditEvent R4 / IHE BALP | Healthcare-native audit logging |
| **5** | OpenTelemetry spans | SIEM / enterprise observability export |

[Full technical architecture →](https://nhid-clinical.org/technical-stack.html)

---

## Meet Beacon

Beacon is the NHID-Clinical reference voice agent — an outbound AI administrative caller operating under the v1.3 behavioral baseline and NHID-Auth v2 authorization layer.

Beacon calls insurance offices on behalf of provider organizations to check claim status. Before any PHI is exchanged, Beacon discloses that it is an automated AI system and obtains consent. Every call produces a machine-readable audit trace.

| Property | Value |
| :--- | :--- |
| Agent ID | `agent_4001krn32nmwe5t8mqzgee0w84rj` |
| Voice | Eryn (ElevenLabs) |
| LLM | Gemini 2.5 Flash |
| Canonical prompt | [`agents/beacon_system_prompt.md`](agents/beacon_system_prompt.md) |

Beacon is a reference implementation, not a product or commercial offering.

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

```
NHID-Clinical/
├── schema/          # Canonical event schema (JSON Schema Draft 2020-12)
├── src/             # Policy engine + cryptographic identity layer (pure Python)
├── tests/           # Conformance suite (YAML) + failure harness (pytest) + trace generator
│   └── demo_scenarios/  # Pre-built VAPI + Twilio test payloads
├── traces/          # 10 pre-generated failure traces
├── adapters/        # Vendor adapters — VAPI, Twilio, Vonage, Retell, Amazon Connect
├── functions/       # AWS Lambda handler
├── vendor/          # Vendor compliance dashboard (static HTML, no build step)
├── tools/           # Pilot report generator
├── docs/            # 5-minute quickstart, staged v2 integration guide
├── NHIDClinical.psm1  # PowerShell module for payer teams
101	└── specs/           # PDF artifacts — Core Specification + Operational Blueprint
```

## Quick Start

```bash
git clone https://github.com/NHID-Clinical/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
python -m pytest tests/ -v
```

Expected output: `261 passing` in ~1.4s (requires `cryptography` package for identity tests; ~6 skip when no server is running).

---

## NHID-Auth v2 — Cryptographic Agent Identity

v1.3 verifies disclosure behavior. v2 verifies authorization: provider-signed agent credentials with NPI binding, scoped delegation chains (max 3 hops), per-agent revocation, and call-SID nonce binding. Reference implementation in `src/agent_identity.py` (42 tests). Released June 2026 under CC BY 4.0.

```bash
python -m pytest tests/test_identity.py -v
python examples/issue_and_verify.py
```

[Details →](https://nhid-clinical.org/roadmap.html)

---

## Contributing & Pilot Partners

We are actively seeking payer and provider organizations to run a **90-day shadow evaluation** — no vendor changes required.

[Become a Pilot Partner →](https://nhid-clinical.org/for-payers.html)

[Community](https://nhid-clinical.org/community.html) · [Discord](https://discord.gg/CU7BwHwVYC) · [contact@nhid-clinical.org](mailto:contact@nhid-clinical.org)

---

<div align="center">
  <sub>CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 · <a href="https://nhid-clinical.org">nhid-clinical.org</a></sub>
</div>
