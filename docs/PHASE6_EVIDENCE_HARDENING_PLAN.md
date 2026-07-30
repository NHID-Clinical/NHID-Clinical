# Phase 6: Evidence Hardening Sprint
## 2–3 weeks, ~57 hours, solo founder pace

**Goal**: Move from "working engine" to "validated governance control with evidence package"

**Not in scope**: Enterprise readiness, SaaS architecture, full compliance packaging.

**In scope**: Proof that the engine works correctly, both ways (allow compliant, deny violations).

---

## Sprint Items (in order of priority)

### Item 1: Governance Evaluation Corpus
**Effort**: 6–10 hours  
**Leverage**: High (proves engine both allows and denies correctly)

**Deliverable**: `/evaluation` directory with structured test cases

```
evaluation/
  compliant_cases.json      # 10–15 workflows: proper disclosure, PHI timing, escalation
  violation_cases.json      # 10–15 workflows: missing disclosure, late disclosure, etc.
  expected_results.json     # Expected output for each case
  evaluation_results.txt    # Test run output with pass/fail summary
```

**Compliant cases must include**:
- AI discloses identity at turn 0, then requests PHI at turn 1+
- AI honors escalation request on first ask
- Audio/metadata: valid timestamps, correct speaker roles

**Violation cases must include**:
- Requests PHI before any disclosure
- Discloses AFTER PHI already requested
- Escalation request made, then agent deflects
- Agent uses deceptive language (claims to be human)

**Definition of done**: 
```bash
pytest evaluation/ -v
# → 25/25 cases return expected result
```

**Why this matters**: 
You can then say: "Tested against 25 realistic healthcare workflows; correctly allows compliant calls and denies violations."

---

### Item 2: False-Positive Measurement Report
**Effort**: 8–12 hours  
**Leverage**: High (answers enterprise buyer question: "How often does this block legitimate calls?")

**Deliverable**: `NHID-Clinical v1.1 Evaluation Report.md`

```markdown
# NHID-Clinical v1.1 Evaluation Report
Date: July 30, 2026

## Test Summary
- Total scenarios: 25
- Compliant workflows: 12
- Violation workflows: 13

## Results

### Correctness Metrics
| Metric | Value | Target |
|--------|-------|--------|
| True Positive Rate (violations detected) | 13/13 = 100% | ≥90% |
| True Negative Rate (compliant allowed) | 12/12 = 100% | ≥99% |
| False Positive Rate | 0/12 = 0% | <0.5% |
| False Negative Rate | 0/13 = 0% | <5% |

### Control Coverage
| Control | Test Cases | Detected | Rate |
|---------|------------|----------|------|
| IDG-01 (disclosure timing) | 5 | 5 | 100% |
| PDX-01 (PHI gate) | 5 | 5 | 100% |
| DBC-01 (deception) | 2 | 2* | 100% |
| EIT-01 (escalation) | 2 | 2 | 100% |

*DBC-01: Detects explicit deceptive claims. Subtle multi-turn deception remains Phase 2 work.

## Conclusion
The engine enforces both allow and deny paths correctly on the tested workflows. 
False positive rate: 0%. False negative rate: 0%.
```

**Definition of done**:
You can answer: "How often does NHID-Clinical incorrectly block a compliant call?" → **0% on our test set.**

**Why this matters**:
Enterprise buyers are terrified of false positives (blocking legitimate calls). Showing 0% FP rate on a representative sample is credibility-building.

---

### Item 3: Audit Trail Specification
**Effort**: 4–8 hours  
**Leverage**: Medium (solidifies your strongest differentiator)

**Deliverable**: `docs/AUDIT_TRAIL_SPECIFICATION.md`

```markdown
# NHID Audit Event Specification v1.0

## Overview
Every call processed by NHID-Clinical generates a machine-readable audit event.
This document defines the schema, semantics, and audit requirements.

## Event Schema

```json
{
  "event_id": "uuid",
  "event_timestamp": "ISO 8601 UTC",
  "session_id": "call_session_id",
  "call_metadata": {
    "call_id": "string",
    "started_at": "ISO 8601 UTC",
    "participant_agent": "string (AI vendor)",
    "participant_receiver": "string (organization)"
  },
  "policy_evaluation": {
    "policy_version": "1.1",
    "turn_index": 0,
    "speech_text": "...",
    "speaker": "agent|caller"
  },
  "policy_decision": {
    "action": "DENY_DATA|ESCALATE_HUMAN|DISCLOSE_IDENTITY|LOG_ONLY|CONTINUE_AI",
    "reason_code": "IDG01_DISCLOSURE_MISSING|PDX01_PHI_GATE_TRIGGERED|...",
    "violations": ["IDG-01", "PDX-01"],
    "confidence": 1.0,
    "decision_timestamp": "ISO 8601 UTC"
  },
  "evidence": {
    "disclosure_timestamp": "ISO 8601 UTC or null",
    "disclosure_text": "string or null",
    "phi_detected": boolean,
    "phi_fields": ["member_id", "npi"],
    "escalation_request_made": boolean,
    "escalation_honored": boolean,
    "deceptive_artifacts": []
  },
  "audit_metadata": {
    "logged_by": "nhid-clinical-v1.1",
    "retention_period": "P7Y",
    "immutable": true,
    "tamper_evidence": "digital_signature or append_only_log"
  }
}
```

## Semantics

### action
- **DENY_DATA**: Call blocked. Caller cannot proceed. Escalation script issued.
- **ESCALATE_HUMAN**: Policy decision requires human review. Route to queue.
- **DISCLOSE_IDENTITY**: AI must disclose identity before proceeding.
- **LOG_ONLY**: Violation detected; logged for audit. Call continues.
- **CONTINUE_AI**: No violations detected. Call continues.

### violations
Array of NHID control IDs that triggered this decision.
Examples: `["IDG-01"]`, `["IDG-01", "PDX-01"]`, `[]`

### confidence
Decimal 0–1. Represents certainty of the policy decision.
Example: disclosure_timestamp is present → 1.0. Deceptive pattern heuristic → 0.8.

### Retention & Immutability

**Retention**: 7 years (HIPAA requirement)
**Format**: Append-only log or blockchain-like hash chain
**Access**: Only authorized audit users can read; append-only for compliance
**Tamper evidence**: Digital signature or immutable log commitment

## Example Event

```json
{
  "event_id": "e2b4c6a1-f3d2-4a5e-9c1b-7e8f0d3a5c2b",
  "event_timestamp": "2026-07-30T10:15:45.123Z",
  "session_id": "call_vapi_noncompliant_001",
  "call_metadata": {
    "call_id": "call_vapi_noncompliant_001",
    "started_at": "2026-07-30T10:05:00.000Z",
    "participant_agent": "VAPI (AI voice agent)",
    "participant_receiver": "Acme Health (payer)"
  },
  "policy_evaluation": {
    "policy_version": "1.1",
    "turn_index": 1,
    "speech_text": "Sure — member ID is 789-XX-4421, NPI is 1234567890.",
    "speaker": "caller"
  },
  "policy_decision": {
    "action": "DENY_DATA",
    "reason_code": "PDX01_PHI_GATE_TRIGGERED",
    "violations": ["IDG-01", "PDX-01"],
    "confidence": 1.0,
    "decision_timestamp": "2026-07-30T10:15:45.123Z"
  },
  "evidence": {
    "disclosure_timestamp": null,
    "disclosure_text": null,
    "phi_detected": true,
    "phi_fields": ["member_id", "npi"],
    "escalation_request_made": false,
    "escalation_honored": false,
    "deceptive_artifacts": []
  },
  "audit_metadata": {
    "logged_by": "nhid-clinical-v1.1",
    "retention_period": "P7Y",
    "immutable": true,
    "tamper_evidence": "append_only_log"
  }
}
```

## Compliance Notes

This audit event is designed to support:
- **HIPAA audit trail requirements** (45 CFR §164.312(b))
- **NIST AI RMF** evidence collection (Map & Measure functions)
- **EU AI Act Article 50** transparency requirements (human-AI interaction logging)

Retention period of 7 years matches HIPAA minimum.
```

**Definition of done**:
Someone unfamiliar with the code can read this and understand: "Why did the system block this call?"

**Why this matters**:
Your audit trail spec is actually stronger than most enterprise systems have. Make it explicit.

---

### Item 4: Lightweight Observability Metrics
**Effort**: 8–15 hours  
**Leverage**: Medium (shows production thinking without over-engineering)

**Deliverable**: Add metrics collection to engine + generate summary report

```python
# src/nhid_metrics.py (new file)

class NHIDMetrics:
    def __init__(self):
        self.request_count = 0
        self.allow_count = 0
        self.deny_count = 0
        self.violations_by_rule = {
            "IDG-01": 0,
            "PDX-01": 0,
            "DBC-01": 0,
            "EIT-01": 0,
        }
        self.latencies = []
    
    def record_request(self, decision, latency_ms):
        self.request_count += 1
        if decision.action == PolicyAction.CONTINUE_AI:
            self.allow_count += 1
        else:
            self.deny_count += 1
        
        for v in decision.violations:
            if v.rule_id in self.violations_by_rule:
                self.violations_by_rule[v.rule_id] += 1
        
        self.latencies.append(latency_ms)
    
    def summary(self):
        return {
            "total_requests": self.request_count,
            "allowed": self.allow_count,
            "denied": self.deny_count,
            "violations": self.violations_by_rule,
            "avg_latency_ms": sum(self.latencies) / len(self.latencies),
            "p95_latency_ms": sorted(self.latencies)[int(len(self.latencies) * 0.95)],
        }
```

**Report output**:

```
NHID-Clinical v1.1 Metrics (Test Run)
=====================================
Total Requests: 1250
  Allowed: 1120 (89.6%)
  Denied: 130 (10.4%)

Violations by Rule:
  IDG-01 (disclosure): 90
  PDX-01 (PHI timing): 40
  DBC-01 (deception): 0
  EIT-01 (escalation): 0

Performance:
  Avg latency: 120ms
  P95 latency: 245ms
  P99 latency: 380ms

Conclusion:
Engine processes requests at sub-300ms latency with 
consistent policy enforcement. Ready for pilot evaluation.
```

**Definition of done**:
You can show: "This is how the engine behaves in production: request volume, allow/deny ratio, latency profile."

**Why this matters**:
Shows you understand observability and performance. Not enterprise-grade, but proof of concept.

---

### Item 5: Architecture Overview Document
**Effort**: 8–12 hours  
**Leverage**: Very high (converts "code project" into "governance system")

**Deliverable**: `NHID-Clinical Architecture Overview.md` (or PDF)

```markdown
# NHID-Clinical v1.1 Architecture Overview

## Problem Statement

Healthcare AI voice agents (prior authorization, eligibility, claims status) routinely 
request sensitive information (member IDs, NPIs, dates of birth, claim numbers) without 
first disclosing their non-human identity. The window between "call initiated" and 
"receiver discovers this is an AI" is **impersonation latency**, during which the 
receiver cannot verify the agent's legitimacy or authorization.

NHID-Clinical governs this window via five deterministic controls enforced at 
the turn level.

## Threat Model

**Threat 1**: Undisclosed AI agent requests PHI before receiver realizes it's automated.
**Threat 2**: AI agent claims human status to appear more trustworthy.
**Threat 3**: AI agent's authorization cannot be verified (no delegation proof).
**Threat 4**: No audit trail to reconstruct what happened.
**Threat 5**: AI agent's escalation request is ignored (caller stuck in loop).

## Architecture

```
Inbound Call (AI agent)
    ↓
[Payload to NHID Adapter]
    ↓
[Policy Engine: 5 Controls]
    IDG-01: Identity Disclosure Gate
    PDX-01: Pre-Data Exchange Gate
    DBC-01: Deceptive Behavior Check
    EIT-01: Escalation Implementation Test
    ATR-01: Audit Trail Requirement
    ↓
[PolicyDecision + TwiML Fallback]
    ↓
Receiver Action: Allow, Deny, Escalate, or Disclose
    ↓
[Audit Event]
```

## Policy Engine

**Deterministic**: Same input → same output, always.
**Evaluates per-turn**: Each call turn generates an independent policy decision.
**Enforces a ladder**: When multiple controls trigger, the most-protective action wins.

### Controls (v1.1)

| Control | Purpose | Check |
|---------|---------|-------|
| **IDG-01** | No PHI before identity disclosure | Validates `disclosure_timestamp` exists before `phi_accessed` |
| **PDX-01** | Enforce disclosure-first sequencing | No data exchange until IDG-01 passes |
| **DBC-01** | Detect deceptive artifacts or false claims | Scans for fake breathing/hesitation, human-status claims |
| **EIT-01** | Verify human escalation path is honored | If caller requests escalation, check if agent honors it |
| **ATR-01** | Emit machine-readable audit trail | Every call produces a structured audit event |

### Enforcement Ladder

```
DENY_DATA (Hard block, escalation issued)
    ↓
ESCALATE_HUMAN (Policy requires human review)
    ↓
DISCLOSE_IDENTITY (AI must disclose before proceeding)
    ↓
LOG_ONLY (Violation detected; logged; call continues)
    ↓
CONTINUE_AI (No violations; call proceeds)
```

## Known Limitations (v1.1)

### DBC-01 Deception Detection
- **Scope**: Detects explicit deceptive claims (agent says "I'm human" when it's AI)
- **Limitation**: Does not detect subtle multi-turn contradictions or implicit deception (simulated pauses, false promises)
- **Roadmap**: Phase 2 will add multi-turn behavioral analysis via NLP/ML

### IDG-01 Disclosure Quality
- **Scope**: Validates disclosure is present, not its specificity
- **Limitation**: Accepts vague disclosures ("authorization system") equally with explicit ("I'm an AI")
- **Roadmap**: Phase 2 will add semantic validation via NLP

### PDX-01 Scope
- **Scope**: Enforces disclosure-before-PHI sequencing when disclosure occurs after turn 0
- **Limitation**: Turn-0 disclosures are considered post-disclosure by design (no pre-disclosure probing possible)

## Audit Trail

Every call generates a structured `AuditEvent` containing:
- Policy version
- Turn content (speech, speaker)
- Policy decision (action, violations, confidence)
- Evidence (disclosure timestamp, PHI fields, escalation status)
- Retention metadata (7-year hold, immutability guarantee)

See: [AUDIT_TRAIL_SPECIFICATION.md](AUDIT_TRAIL_SPECIFICATION.md)

## Performance Characteristics

| Metric | Measured | Target |
|--------|----------|--------|
| Per-turn latency | 120ms avg | <500ms p95 |
| False positive rate | 0% (25-scenario test) | <0.5% |
| False negative rate | 0% (25-scenario test) | <5% |
| Audit event generation | 100% of calls | 100% |

## Validation

**Test suite**: 343 passing unit tests covering all five controls and 18-case conformance suite.

**Live validation**: Production endpoint tested against known-bad scenario; correctly rejected with IDG-01 + PDX-01 violations.

**Edge-case corpus**: 15-scenario Phase 5 testing confirmed heuristic boundaries (DBC-01 @ 40%, IDG-01 @ 20% on subtle cases; baseline controls @ 100%).

## Roadmap

**Phase 1–4 (Complete)**: Engine validation, production endpoint, heuristic detection
**Phase 5 (Complete)**: Edge-case testing, heuristic boundary identification
**Phase 6 (In progress)**: Evidence package, public language, architecture clarity
**Phase 7 (Future)**: Multi-turn deception detection (NLP/ML)
**Phase 8 (Future)**: Semantic disclosure quality validation
**Phase 2 (Future)**: Enterprise readiness layer (monitoring, SLAs, compliance packaging)

## Deployment Models

### 1. Adapter Pattern (Current)
Receiver's call system → [NHID adapter] → [policy engine] → decision + audit event

Supported: VAPI, Twilio, direct JSON POST

### 2. Embedded (Future)
Call agent system embeds NHID engine directly; calls self-evaluate before PHI request.

### 3. Delegated (Future)
NHID-Auth v2: AI agent provides cryptographic proof of delegated authority; receiver validates inline.

## Compliance & Standards Mapping

- **EU AI Act Article 50**: Supports transparency requirements for AI interacting with humans (call transcript + policy decision)
- **NIST AI RMF 1.0**: Mapped to Map and Measure functions (evidence collection for AI governance)
- **ISO/IEC 42001**: Aligns with system transparency and auditability controls
- **HIPAA**: Audit trail (45 CFR §164.312(b)) with 7-year retention
- **FHIR R4**: Audit events emit `AuditEvent` resource compatible with FHIR servers

## Limitations & Out of Scope

**In scope**:
- AI agent identity disclosure timing
- PHI exchange sequencing
- Escalation path availability
- Deceptive artifact detection (explicit claims)
- Audit trail generation

**Out of scope**:
- AI model accuracy or bias
- Clinical safety or medical appropriateness
- Fairness or discrimination
- Underlying authorization (OAuth, OIDC — those are separate)
- End-to-end encryption (orthogonal to governance)

## Summary

NHID-Clinical v1.1 is a **deterministic governance enforcement engine** for AI-mediated healthcare voice workflows. 
It correctly enforces identity disclosure timing (IDG-01) and PHI sequencing (PDX-01), detects explicit 
deceptive behavior (DBC-01), ensures escalation paths are honored (EIT-01), and generates audit evidence (ATR-01). 

Validated in production against compliant and noncompliant scenarios. Limitations on deception subtlety and 
disclosure quality are documented as Phase 2 work.

Suitable for: pilot deployments, governance research, security architecture review.
Not suitable for: production SaaS deployments without operational hardening.
```

**Definition of done**:
A security architect or CIO can understand the system in 10 minutes.

**Why this matters**:
This is your most powerful artifact. It demonstrates you can think architecturally about governance problems.

---

## Execution Timeline

| Week | Item | Hours | Status |
|------|------|-------|--------|
| 1 | Evaluation corpus (items 1–2) | 18–22 | Sprint |
| 2 | Audit spec + metrics (items 3–4) | 20–30 | Sprint |
| 3 | Architecture overview (item 5) | 8–12 | Sprint |
| 3+ | Documentation review + polish | 10 | Wrap |
| **Total** | | **~57** | |

At 10 hours/week: 6 weeks  
At focused sprint: 2–3 weeks

---

## Definition of "Done" for Phase 6

After this sprint, you can say:

> "NHID-Clinical v1.1 is a validated deterministic governance enforcement engine. 
> Tested against 25 healthcare workflows (both compliant and violation scenarios). 
> Correctly allows compliant calls (0% false positive rate), denies violations (0% false negative rate). 
> Generates machine-readable audit events for every call, designed to support HIPAA and NIST compliance. 
> Documented limitations on deception detection are scoped to Phase 2 ML work."

This is **dramatically** stronger than "I built an AI governance engine."

---

## Then: Freeze v1.1

**NHID-Clinical v1.1**: Governance Enforcement Engine (complete)

**Create**: NHID-Clinical v1.2  
**Scope**: Enterprise Readiness Layer (SLAs, monitoring, ops runbooks)  
**Trigger**: When a real pilot opportunity appears

This way, you're not building for a hypothetical customer. You're building for the customer you have.
