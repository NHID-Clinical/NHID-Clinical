# NHID-Clinical v1.3 — Certification Framework

**Tiered trust levels for organizations implementing NHID-Clinical.**

---

## Overview

The NHID-Clinical Certification Framework provides three progressive trust tiers for AI voice systems operating in B2B healthcare administrative workflows. Certification is voluntary and additive — L2 requires L1, L3 requires L2.

Certification does not create legal obligations. It signals operational commitment to the NHID-Clinical control baseline and provides a common language for payer procurement teams evaluating AI voice vendors.

---

## Tier Definitions

### L1 — Baseline Conformance

**What it means:** The system passes all five Conformance Test Suite (CTS) tests under controlled evaluation conditions.

**Who it's for:** Any organization deploying an AI voice agent in B2B healthcare administrative workflows. L1 is the entry point — the minimum bar for claiming NHID-Clinical alignment.

**Requirements:**

| Requirement | Detail |
|-------------|--------|
| CTS Completion | All five tests (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01) passed |
| Testing Method | Internal QA team self-attestation |
| Evidence Package | Signed declaration of conformance with test results |
| Audit Logs | Tier 1 structured logs present and verifiable |
| System Prompt Version | Current system prompt / call script version documented |

**Declaration Statement (self-attestation):**
> *"We certify that [System Name], version [X.X], has been evaluated against the NHID-Clinical v1.3 Conformance Test Suite and has passed all five required tests. Evidence is retained on file and available upon request."*

**Badge:**

```
![NHID-Clinical L1](https://img.shields.io/badge/NHID--Clinical-L1%20Baseline-blue)
```

![NHID-Clinical L1](https://img.shields.io/badge/NHID--Clinical-L1%20Baseline-blue)

---

### L2 — Operational Conformance

**What it means:** The system maintains CTS conformance in production, with structured evidence of ongoing operational compliance.

**Who it's for:** Organizations with active deployments handling significant call volume, or those seeking to demonstrate compliance to payer procurement teams.

**Requirements (all L1 requirements plus):**

| Requirement | Detail |
|-------------|--------|
| Production Evidence | Tier 1 audit logs from minimum 30 days of live operation |
| Disclosure Failure Rate | DFR < 2% demonstrated over production period |
| Escalation Compliance | EIT-01 passing rate ≥ 99% in production sample |
| Tier 2 Evidence | First-60-second audio transcripts or recordings available for sample review |
| Policy Version Control | System prompt / call script version history documented with timestamps |
| Review Submission | Evidence package submitted to NHID-Clinical maintainer for review |

**Badge:**

```
![NHID-Clinical L2](https://img.shields.io/badge/NHID--Clinical-L2%20Operational-green)
```

![NHID-Clinical L2](https://img.shields.io/badge/NHID--Clinical-L2%20Operational-green)

---

### L3 — Enterprise Conformance

**What it means:** Full independent verification of CTS conformance and operational evidence by a qualified third-party auditor.

**Who it's for:** Enterprise vendors seeking formal certification for payer procurement, healthcare system deployments, or regulatory-adjacent contexts.

**Requirements (all L1 + L2 requirements plus):**

| Requirement | Detail |
|-------------|--------|
| Independent Audit | Third-party auditor (qualified compliance professional or firm) conducts CTS evaluation |
| Auditor Attestation | Signed auditor declaration included in evidence package |
| Production Monitoring | Continuous or periodic sampling of production calls against CTS thresholds |
| Tier 3 Analytics | Disclosure Failure Rate, Escalation Loop Frequency, and Call Termination Rate tracked and reported |
| Registry Listing | Organization listed in NHID-Clinical registry when available (v1.4+) |
| Annual Renewal | L3 certification expires after 12 months without renewal evaluation |

**Badge:**

```
![NHID-Clinical L3](https://img.shields.io/badge/NHID--Clinical-L3%20Enterprise-gold)
```

![NHID-Clinical L3](https://img.shields.io/badge/NHID--Clinical-L3%20Enterprise-gold)

---

## Certification Comparison Table

| Requirement | L1 Baseline | L2 Operational | L3 Enterprise |
|-------------|:-----------:|:--------------:|:-------------:|
| CTS all 5 tests passed | ✅ | ✅ | ✅ |
| Self-attestation declaration | ✅ | ✅ | ✅ |
| Production evidence (30+ days) | ❌ | ✅ | ✅ |
| DFR < 2% in production | ❌ | ✅ | ✅ |
| Tier 2 audio evidence | ❌ | ✅ | ✅ |
| Evidence package review | ❌ | ✅ | ✅ |
| Independent third-party audit | ❌ | ❌ | ✅ |
| Tier 3 analytics reporting | ❌ | ❌ | ✅ |
| Registry listing (v1.4+) | ❌ | ❌ | ✅ |
| Annual renewal required | ❌ | ❌ | ✅ |

---

## How to Claim Certification

### L1 Process

1. Run all five CTS tests internally using your QA team
2. Document results (test ID, date, tester, pass/fail outcome, notes)
3. Sign and retain the L1 declaration statement
4. Add the L1 badge to your product documentation or README
5. Optionally: notify NHID-Clinical maintainer at [bnbaynard@gmail.com](mailto:bnbaynard@gmail.com) to be acknowledged in the community

### L2 Process

1. Complete L1 requirements
2. Operate in production for minimum 30 days
3. Collect and retain Tier 1 + Tier 2 evidence package
4. Submit evidence summary to NHID-Clinical maintainer for informal review
5. Upon acknowledgement, add L2 badge

### L3 Process

1. Complete L1 + L2 requirements
2. Engage a qualified third-party auditor to conduct CTS evaluation
3. Submit full evidence package including auditor attestation
4. Work with NHID-Clinical maintainer on formal review process
5. Upon verification, receive L3 designation and registry listing (v1.4+)

> **Note:** The L3 formal review process is being defined as part of the v1.4 roadmap. Early adopters interested in L3 pilot certification should contact [bnbaynard@gmail.com](mailto:bnbaynard@gmail.com).

---

## Scope Limitations

- Certification applies to a specific system and version, not an organization broadly
- Certification does not constitute legal compliance verification under HIPAA, TCPA, or any other regulation
- Self-attestation (L1/L2) relies on organizational integrity; NHID-Clinical maintainer does not independently verify L1/L2 claims
- Badges are provided in good faith; misrepresentation of certification level is a violation of CC-BY 4.0 attribution terms

---

*NHID-Clinical · Author: Brianna Baynard · CC-BY 4.0 · v1.3 · 2026*
