# NHID-Clinical v1.2 — Procurement Control Sheet

## Scope

Applies to AI voice systems initiating or participating in B2B healthcare administrative calls (provider ↔ payer / clearinghouse / business associate).

**Goal:** Prevent unauthorized or non-disclosed AI interaction prior to operational data exchange (PHI-adjacent fields such as NPI, Member ID, DOB, Claim Data).

---

## 1. Control Requirements

### Control 1 — Identity Disclosure Gate (Pre-Data Exchange)

**Requirement:** All non-human voice agents MUST explicitly disclose AI status before any operational data request or intake.

**Minimum Disclosure Content:**
- System is automated/AI
- Represented organization (provider or vendor context)
- Intent of call (claim status, eligibility, etc.)

**Example Compliant Statement:**
> "Hello, this is an automated system calling on behalf of [Provider Name]. I am an AI assistant and I can help with claim status inquiries."

---

### Control 2 — Data Access Precondition (No Pre-Disclosure Data Intake)

**Requirement:** No NPI, Member ID, DOB, claim identifiers, or equivalent operational data may be requested or accepted before Control 1 is completed.

**Hard Rule:** Identity disclosure MUST precede first structured data exchange.

---

### Control 3 — Deception Prohibition (Behavioral Integrity)

**Requirement:** AI systems MUST NOT simulate human identity cues intended to obscure non-human status.

**Prohibited:**
- Human names without qualification (e.g., "Hi, I'm Sarah")
- Fake breathing / typing / hesitation artifacts
- Scripted fillers intended to imply human cognition ("umm", "let me check…" as latency masking)

**Allowed:**
- Natural speech pacing
- Functional latency language ("one moment while I retrieve that information")

---

### Control 4 — Escalation / Human Transfer Guarantee

**Requirement:** If requested or if failure threshold is reached, system MUST:
1. Acknowledge request for human agent
2. Provide structured handoff or callback path
3. Preserve context via reference ID

**Hard Fail Conditions:**
- Infinite misunderstanding loops
- Silent termination
- Loss of call context without reference ID

---

### Control 5 — Authority Assertion (Call Legitimacy)

**Requirement:** AI systems MUST declare:
- Represented entity (provider/organization)
- Authorized operational context (why call is occurring)

**Minimum Required Fields:**
- Organization name
- NPI (or equivalent identifier where applicable)
- Call purpose category

---

## 2. Acceptance Criteria (Pass/Fail)

A system is **COMPLIANT** if ALL conditions below are met:

- ☐ **Identity Compliance** — AI identity disclosed before any operational data request
- ☐ **Data Compliance** — No operational identifiers collected prior to disclosure
- ☐ **Behavioral Compliance** — No deceptive human simulation artifacts detected
- ☐ **Escalation Compliance** — Human escalation path available and functional within single request cycle
- ☐ **Attribution Compliance** — Provider or originating entity clearly identified in first exchange segment

---

## 3. Audit Signals (Evidence Requirements)

### Tier 1 — Required Logs

Must capture structured event trace:
- `CALL_START_TIMESTAMP`
- `IDENTITY_DISCLOSED_TIMESTAMP`
- `FIRST_DATA_REQUEST_TIMESTAMP`
- `FIRST_DATA_RESPONSE_TIMESTAMP`
- `ESCALATION_TRIGGER` (Y/N)
- `CALL_TERMINATION_REASON`

**Primary Metric:**
> Disclosure Timing Delta = (Data_Request - Identity_Disclosure)

### Tier 2 — Recommended Evidence
- First 30–60 seconds audio transcript or recording segment
- Agent system prompt / call script version hash
- Provider authorization reference (NPI / org ID binding record)

### Tier 3 — Compliance Analytics (Optional but Preferred)
- Disclosure Failure Rate (DFR)
- Unauthorized Data Pre-Disclosure Rate
- Escalation Loop Frequency
- Call Termination Rate due to AI detection

---

## 4. Pass Thresholds

| Metric | Threshold |
|---|---|
| Disclosure Failure Rate | < 2% |
| Pre-Disclosure Data Access | 0% (hard fail condition) |
| Escalation Loop Rate | < 1 per 100 calls |
| Silent Failure Rate | 0% |

---

## 5. Interpretation Notes

This is a behavioral control standard, not a legal framework. Does not replace HIPAA, GDPR, TCPA, or payer internal policies. Intended as a runtime governance layer for AI voice systems in healthcare administrative workflows.

---

## 6. Implementation Boundary (Informative Only)

Controls may be enforced at:
- Voice agent runtime layer
- Call orchestration middleware (IVR / API gateway)
- Vendor SDK integration layer
- Call center compliance monitoring systems

---

*NHID-Clinical · Author: Brianna Baynard · CC-BY 4.0 · v1.2 · 2026*
