# CSA AI-CAIQ v1.1.0 Self-Assessment — Summary

**Status: DRAFT INTERNAL SELF-ASSESSMENT — NOT a CSA STAR registry submission.**

This document and the accompanying filled questionnaire
(`docs/csa-ai-caiq-v1.1-self-assessment.xlsx`) are an internal exercise for the NHID-Clinical
project owner. They have not been submitted to the Cloud Security Alliance, are not published to
the STAR registry, and have not been independently reviewed or audited. Treat all answers as a
first-pass, honest self-assessment intended to surface gaps — not a certification, not a vendor
attestation to a counterparty, and not a substitute for a real compliance program if NHID-Clinical
is ever operated as a hosted service rather than distributed as a specification + reference
implementation.

## Methodology

- Source questionnaire: AI-CAIQ v1.1.0 (320 question rows across 18 AICM domains), filled
  programmatically row-by-row against NHID-Clinical's actual documented controls and code
  (`docs/nhid-clinical-technical-specification.md`,
  `docs/nhid-auth-pki-and-oauth2-integration.md`, `docs/vendor-trust-questionnaire.md`,
  `src/`, `tests/`, `scripts/validate_ci.py`, `README.md`).
- **SSRM framing is load-bearing here.** NHID-Clinical is a specification + reference
  implementation (Python/TypeScript source, a public demo Lambda API, docs, and tests) — it is
  **not** a hosted multi-tenant cloud service. It has no datacenter, no fleet of managed
  endpoints, and no employee workforce of its own. Per CSA's Shared Security Responsibility
  Model, most physical/infrastructure/HR-layer controls are honestly `N/A` for NHID-Clinical
  itself, with ownership assigned to `Service Customer` (i.e., whoever deploys the reference
  implementation in production owns those controls for their own deployment).
- Where NHID-Clinical has real, testable, documented controls, the answer is `Yes` or `Partial`
  with a specific citation to the doc/code that backs the claim. Where a control genuinely
  doesn't exist, the answer is `No` or `N/A` and says so plainly — answers were deliberately not
  padded with vague reassurance language. A few rows are marked `Partial`/`Shared` even where
  NHID-Clinical's own implementation is thin, because the *concept* is documented in enough depth
  (e.g., key-rotation recommendations, SSRM-equivalent gap tables) that an adopter has real
  guidance to work from, even though no automation enforces it yet.
- 320 of 322 spreadsheet rows are actual questions (rows 3–322); row 323 ("End of Standard") and
  row 324 (CSA copyright footer) were left untouched, as were the `Introduction`, `LLM Taxonomy`,
  and `Change Log` sheets.

## Overall tally

| Answer | Count | % of 320 |
| :-- | --: | --: |
| Yes | 6 | 1.9% |
| Partial | 94 | 29.4% |
| No | 100 | 31.3% |
| N/A | 120 | 37.5% |

The `N/A` share is large and expected — it is mostly Datacenter Security (28/28), Universal
Endpoint Management (15/15), Model Security (19/19), Infrastructure Security (13/13), and Human
Resources (19/19, minus 3 AI-training-specific Partial/No rows), all domains where NHID-Clinical
genuinely has nothing of its own to assess because it isn't a hosted service, doesn't train a
model, and doesn't employ a workforce.

## Per-domain posture

| Domain | Posture | Detail |
| :-- | :-- | :-- |
| **Audit & Assurance** | Weak-to-moderate | 5 Partial, 2 No. ATR-01's structural audit-trail requirement and the CI-enforced 284-test baseline give real, narrow evidence; there is no independent third-party audit and no formal audit-management program. |
| **Application & Interface Security** | Moderate, genuine strength in a few rows | 12 Partial, 3 No, 2 Yes, 1 N/A. The five canonical behavioral controls (IDG-01/PDX-01/DBC-01/EIT-01) and CI-gated testing are real, specific, code-backed answers. Sandboxing, general adversarial-input defense for an underlying LLM, and static analysis are not implemented. |
| **Business Continuity Management and Operational Resilience** | Weak | 9 No, 3 N/A, 3 Partial, 1 Yes. No formal BC/DR plan exists; the closest analogue is Git/GitHub's inherent redundancy and the CI regression gate. Honestly weak — this is a real gap if NHID-Clinical's public demo API is depended on. |
| **Change Control and Configuration Management** | Moderate | 7 Partial, 2 No, 1 N/A, 1 Yes. Git/GitHub PR review plus the CI exact-test-count baseline (`scripts/validate_ci.py`) function as real, if lightweight, change control. |
| **Cryptography, Encryption & Key Management** | Moderate, well-documented gaps | 10 Partial, 11 No, 2 N/A. Ed25519 design choices and key-lifecycle recommendations are unusually well documented (`docs/nhid-auth-pki-and-oauth2-integration.md`), but the reference implementation explicitly ships demo-only key generation with no KMS/HSM custody, no persistent revocation, and no rotation automation — these are honest, acknowledged gaps, not hidden ones. |
| **Datacenter Security** | N/A across the board | 28/28 N/A. No datacenter or physical facility of NHID-Clinical's own. |
| **Data Security and Privacy Lifecycle Management** | Weak-to-moderate, mostly N/A | 7 Partial, 10 No, 13 N/A. PDX-01's PHI-field taxonomy is real and specific; broader data lifecycle controls (DPIAs, subject access requests, retention schedules, training-data governance) are N/A because NHID-Clinical retains no personal data and trains no model. |
| **Governance, Risk and Compliance** | Moderate, a real strength on explainability | 10 Partial, 7 No, 1 Yes. Explainability (GRC-13.1) is a genuine `Yes` — the policy engine's determinism is a first-class, documented design property. The regulatory-alignment matrix and explicit non-certification framing are real governance-adjacent strengths. No formal AIRM program, ethics committee, or bias/fairness evaluation exists. |
| **Human Resources** | N/A across the board (project has no workforce) | 19 N/A, 2 No, 1 Partial. The 1 Partial (HRS-15.1) credits the project's external AI-behavior guidance as a loose analogue to an internal AI acceptable-use policy. |
| **Identity & Access Management** | **Strongest domain** | 15 Partial, 5 No, 2 N/A. NHID-Auth v2 (Ed25519 provider-signed delegation, NPI binding, scoped delegation chains, call-SID nonce binding, per-agent/per-delegation revocation) gives this domain the deepest, most specific, code-and-test-backed answers in the assessment — but even here, every answer is capped at `Partial` rather than `Yes`, because the reference implementation's revocation store is in-memory only and key custody is demo-grade, both explicitly documented as non-production-ready by the project's own docs. |
| **Interoperability & Portability** | Moderate strength | 2 Partial, 1 No, 1 Yes, 1 N/A. FHIR R4 base-spec conformance, a uniform adapter contract across 5 vendor payload shapes, and CC BY 4.0 open licensing are genuine interoperability strengths; IPY-02.1 is a clean `Yes` (public programmatic API). |
| **Infrastructure Security** | N/A across the board | 13/13 N/A. No infrastructure of NHID-Clinical's own beyond a single public demo Lambda, which isn't a customer-facing multi-tenant environment. |
| **Logging and Monitoring** | Moderate, second-strongest domain | 10 Partial, 10 No, 1 N/A. ATR-01 and the FHIR R4 `AuditEvent` mapping are real, specific, documented controls. Tamper-evidence, log access control, alerting, and SIEM-style correlation are explicitly not implemented — flagged as the deploying organization's responsibility per the vendor trust questionnaire. |
| **Model Security** | N/A across the board | 19/19 N/A. NHID-Clinical does not train, fine-tune, host, or serve any AI/ML model — its policy engine is deterministic and rule-based, not a trained model. This is a correct and important N/A, not a dodge: model security questions belong to whichever voice AI vendor's underlying LLM/TTS/ASR is being evaluated, not to NHID-Clinical. |
| **Security Incident Management, E-Discovery, & Cloud Forensics** | Weak | 15 No, 1 Partial. No incident response plan, no breach notification process, no incident metrics program exists for the project itself. This is an honest, real gap. |
| **Supply Chain Management, Transparency, and Accountability** | Weak-to-moderate | 11 No, 6 Partial, 2 N/A. The SSRM concept is applied in substance throughout the project's own documentation (this assessment is itself the first formal attempt to make that delineation explicit), but no formal SBOM, vendor inventory, or supply-chain risk program exists. |
| **Threat & Vulnerability Management** | Weak | 12 No, 5 Partial. No penetration testing, no vulnerability scanning tool, no patching SLA. The Impersonation Latency framing functions as an informal, narrow threat model for the project's specific domain only. |
| **Universal Endpoint Management** | N/A across the board | 15/15 N/A. No managed endpoint fleet of NHID-Clinical's own. |

## Overall honest assessment

As of 2026-06-24, NHID-Clinical's AI-CAIQ v1.1 posture is exactly what you'd expect from an
early-stage, single-maintainer open specification with a reference implementation, evaluated
against a framework built for operating cloud services: it is **strong and specific in the
narrow slice of domains its actual code addresses — Identity & Access Management (NHID-Auth v2),
Logging and Monitoring (ATR-01/FHIR AuditEvent), Application & Interface Security (the five
canonical behavioral controls plus CI-enforced testing), and explainability within Governance,
Risk and Compliance — and honestly absent everywhere a real operating company would need a
formal program it doesn't have:** no incident response plan, no business continuity plan, no
independent audit, no penetration testing, no formal supply-chain or vulnerability-management
program, and (correctly) no model-security posture to claim since it trains no model. The large
`N/A` count (120/320, 37.5%) is not evasion — it reflects that NHID-Clinical genuinely has no
datacenter, endpoint fleet, workforce, or AI model of its own to assess, and the SSRM ownership
column consistently pushes those controls to whichever organization actually deploys the
reference implementation. The `Yes` count is deliberately small (6/320) because almost every real
control NHID-Clinical has is capped at `Partial` by an acknowledged, documented limitation — most
visibly, NHID-Auth v2's in-memory revocation and demo-grade key generation, which the project's
own production-roadmap-gaps table (`docs/nhid-clinical-technical-specification.md` §14) already
flags as not production-ready. The fair summary for a reader deciding whether to trust this
project: the behavioral and cryptographic-identity *design* is unusually well thought through and
honestly documented for a project at this stage, but nothing here should be read as evidence of
an operated, audited, production-hardened security program — because there isn't one yet, and the
project says so itself.
