# NHID-Clinical

**Non-Human Identity Disclosure Standard for Healthcare Voice Workflows**
Version: 1.3 | Status: Open Governance Proposal | License: CC BY 4.0

---

## What This Is

NHID-Clinical defines a minimum, voluntary, testable control baseline for non-human identity disclosure in B2B healthcare administrative voice interactions.

It addresses a documented gap in provider-to-payer voice workflows (eligibility, claim status, prior authorization) where AI voice agents operate without disclosing their automated status before exchanging operational data.

**This is not a regulation, certification program, or compliance requirement.** It is an open governance proposal submitted to NIST docket NIST-2025-0035 (Comment ID: NIST-2025-0035-0026).

---

## The Problem: Impersonation Latency

An AI calls as "Sarah from Dr. Smith's office." It handles several minutes of normal workflow conversation. Only when challenged does it admit it is automated. By then, sensitive operational data has already been exchanged without clear consent or accountability.

This is impersonation latency: the measurable trust delay between an AI agent initiating a call and the receiving system verifying the caller is authorized to represent the claimed provider.

---

## The Four Controls (v1.3)

| ID | Name | Requirement |
|----|------|-------------|
| IDG-01 | Identity Disclosure Gate | AI MUST identify as automated before any operational data exchange |
| DBC-01 | Deceptive Behavior Check | AI MUST NOT use fake breathing, typing sounds, or scripted human-like hesitation |
| EIT-01 | Escalation and Immediate Transfer | AI MUST provide immediate human handoff when requested |
| ATR-01 | Audit Trail Requirements | AI MUST log disclosure timestamp vs. first data request timestamp |

---

## Conformance Test Suite

Five deterministic pass/fail tests. All five must pass for NHID-Clinical v1.3 conformance.

```bash
git clone https://github.com/NHID-Clinical/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
pytest tests/ -q
```

Expected: `95 passed, 18 skipped`

The 18 skipped tests are integration tests requiring a live FastAPI server. They are optional and do not affect policy engine verification.

---

## Repository Structure

```
src/
  agent_identity.py              # NHID-Auth delegation and NPI binding
  voice_policy.py                # Core disclosure and escalation policy engine
  nhid_policy_engine_v1.py       # Five CTS rule implementations
tests/
  test_identity.py               # Identity and delegation tests
  test_voice_policy.py           # Policy engine tests
  failure_injection_harness.py   # Chaos and adversarial input tests
conformance/
  nhid_conformance_test_suite_v1.yaml   # 18 machine-readable CTS cases
specs/
  NHIDClinicalv1.3_Overview.pdf
  NHID-Clinical-Operational-Blueprint-v1.3.pdf
```

---

## Framework Alignment

| NHID-Clinical Control | NIST AI RMF 1.0 | ISO/IEC 42001:2023 |
|----------------------|-----------------|-------------------|
| Proactive Identity Assertion | MEASURE 2.6, MAP 3.4 | A.7.2, B.9.1 |
| No Deceptive Artifacts | GOV 1.5, MAP 3.4 | A.5.8, A.9.2 |
| Pre-Data Exchange Gate | MANAGE 1.2, GOV 5.1 | A.6.2, A.8.2 |
| Safe Failover / Escalation | MANAGE 4.2, GOV 5.2 | A.8.3, A.6.3 |
| Audit Logging | MANAGE 4.1, MEASURE 2.2 | A.4.2, A.9.3 |

---

## NIST Submission

Submitted to NIST AI Safety Institute public comment docket NIST-2025-0035.
Comment ID: **NIST-2025-0035-0026**
This is a public comment. It does not imply NIST endorsement or recognition.

---

## Website

**[nhid-clinical.org](https://nhid-clinical.org)**

---

## License

CC BY 4.0 - Brianna Baynard-Malone
contact@nhid-clinical.org