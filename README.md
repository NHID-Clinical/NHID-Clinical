# NHID-Clinical v1.3

**Non-Human Identity Disclosure Standard for Healthcare Voice Workflows**

![License](https://img.shields.io/badge/License-CC--BY--4.0-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Released-brightgreen?style=for-the-badge)
![Compliance](https://img.shields.io/badge/Compliance-HIPAA--Aligned-orange?style=for-the-badge)
[![Version](https://img.shields.io/badge/version-1.3-blue?style=for-the-badge)](https://github.com/thankcheeses/NHID-Clinical)
[![Domain](https://img.shields.io/badge/domain-AI_Governance-0052CC?style=for-the-badge)](https://github.com/thankcheeses/NHID-Clinical)
[![Validation](https://img.shields.io/badge/Validation-Now_Live-brightgreen?style=for-the-badge)](https://nhid-clinical.org/validation/)

---

## 🎯 **NEW: Pilot Validation Program Now Live**

[![Validation Program](https://img.shields.io/badge/🎯_Pilot_Validation-Now_Live-brightgreen?style=for-the-badge)](https://nhid-clinical.org/validation/)

**First validations offered at no cost** for AI voice agent platforms in healthcare.

[**→ Request Validation**](https://nhid-clinical.org/validation/) | [View Conformance Test Suite](conformance.md) | [Certification Framework](certification.md)

---

## 🎯 What Problem Does This Solve?

Picture this: You're a customer service rep at an insurance company. A call comes in from what sounds like a medical office — they need a claim status update. You spend 3–5 minutes gathering information. NPI. Member ID. Date of service. Patient details.

Then something feels off. You ask: "Am I speaking with a real person?"

Silence. Then: "I am an automated assistant."

You just spent 3–5 minutes providing protected operational data to an AI agent that never disclosed itself. Your company has no standard for this. So you do what you're trained to do: terminate the call and read the script.

*"We do not speak with AI agents. Please have a human representative call back."*

**This happens thousands of times per day across healthcare.**

Welcome to **"Impersonation Latency"** — the compliance and operational black hole where payer systems have no standard for what a legitimate AI-initiated call looks like, so they reject all of them.

---

## 🩺 Abstract

**NHID-Clinical** defines a minimum control baseline for non-human identity disclosure in B2B healthcare voice interactions.

The standard addresses a documented gap between existing consumer-protection laws, healthcare privacy regulations, and real-world payer–provider administrative workflows. It specifically targets **"Impersonation Latency"**—the operational waste and security risk caused when a human provider cannot immediately distinguish an AI agent from a human counterpart.

> **Scope Note:** This standard is built for **B2B Administrative Workflows** (Provider-to-Payer, Business Associate-to-Payer). It does *not* currently cover direct-to-consumer or patient-facing clinical triage scenarios.

---


## 💡 How NHID-Clinical Works

### ✅ Compliant Call Flow

![Compliant Call Flow](assets/diagrams/compliant-call-flow.svg)

### ❌ Non-Compliant Call Flow

![Non-Compliant Call Flow](assets/diagrams/non-compliant-call-flow.svg)

**The "Green Lane" Principle:** When AI agents identify themselves upfront and follow the rules, everyone wins:
- **Providers** save time (no "are you human?" loops)
- **Payers** reduce operational costs (faster calls)
- **Patients** get faster service (providers aren't stuck on hold)
- **Compliance teams** sleep better (clear audit trails)

---

## 🚨 The Problem Statement

**The scenario:** A provider office deploys a third-party AI voice agent platform to call insurance companies on their behalf — handling eligibility checks, claim status inquiries, and administrative follow-ups. A payer customer service rep answers. They spend 3–5 minutes gathering information — NPI, member ID, date of service, patient information. Then something doesn't add up. They ask: *"Are you a real person?"* They find out they've been talking to an AI the entire time.

**The payer's current response:** Terminate the call. Read from a script: *"We do not speak with AI agents. Please have a human representative call back."*

That call is dead. The provider's workflow is broken. And nobody has written down what an acceptable AI-initiated call even looks like — so payers default to a blanket "no."

**NHID-Clinical standardizes that manual control** — replacing ad-hoc termination policies with a clear, testable baseline for what a compliant AI-initiated B2B healthcare call looks like.

❌ **What's Broken:**
* AI agents call payer reps without disclosing they are automated systems
* Payer reps unknowingly share PHI — NPI, DOB, member ID, date of service — with an undisclosed non-human entity
* Disclosure only happens *reactively* (when challenged: "Are you even a real person?")
* Some agents use fake breathing, typing sounds, and "umm..." pauses to pass as human
* Payers have no standard for accepting compliant AI calls — so they reject all of them

✅ **What NHID-Clinical Fixes:**
* **Pre-Data Exchange Gate:** AI must identify itself *before* any PHI is collected
* **No Deceptive Artifacts:** No fake breathing, typing sounds, or unqualified human names
* **Clear Escalation Path:** When the payer rep needs a human, there's a guaranteed path out
* **Auditable Compliance:** Payers get a standard they can accept, not just a blanket rejection policy

> 💡 **Key Insight:** The administrative cost of AI-driven healthcare transactions is rising, not falling.

U.S. health system administrative complexity costs $350 billion annually (Health Affairs, 2025). AI deployment in prior authorization and billing has created "adversarial AI friction" — payers and providers use AI against each other, increasing transaction volumes rather than reducing costs.

The Peterson Health Technology Institute (April 2026) found that while AI speeds up individual tasks, it does not lower the average cost per claim once AI solution costs are factored in. The system is doing "more work faster," not "less work."

Key cost drivers:

**Transaction Volume Inflation:** A single claim now cycles through 3-4x more automated loops (appeals, resubmissions, denials) than in 2024. Even if cost per transaction drops, total cost per claim rises.

**Verification Overhead:** Payers allocate 30-40% of administrative time for complex claims to human oversight of AI-generated billing and appeals. This "verification tax" includes:
- Manual review of queries flagged as suspicious or bot-driven
- Appeal cycle management (82% overturn rate in Medicare Advantage plans as of Q2 2026)
- Downcoding review processes responding to AI-generated upcoding
- Forensic analysis to detect AI hallucinations in clinical documentation

**AI Governance Liability:** New insurance and legal exposure costs for AI systems that deny necessary care.

While some insurers report 30-40% reductions in routine claims processing costs, overall system costs are inflated by AI-vs-AI conflict.

**NHID-Clinical addresses one friction point:** eliminating wasted operational time when payer representatives cannot immediately distinguish AI voice agents from human callers during B2B workflows.

---

## 🎭 Positioning: This Isn't Just Another Framework

**What NHID-Clinical is:**
- ✅ A **voluntary** governance standard with binary, testable requirements
- ✅ Operational logic gates that QA teams can actually implement
- ✅ Designed by someone who spent 8 months enforcing HIPAA compliance in actual payer operations

**What NHID-Clinical is NOT:**
- ❌ A replacement for HIPAA, GDPR, or other legal requirements
- ❌ An "ethical AI" philosophy paper with no implementation guidance
- ❌ A legal mandate — this is a voluntary operational standard

**Think of it like this:** HIPAA says "protect patient data." NHID-Clinical provides operational guidance for *how to handle disclosure* when AI agents are involved in voice workflows — it does not create legal obligations or extend HIPAA's scope.

This standard is informed by real payer-side enforcement practices where calls are terminated when non-human or unverifiable entities attempt to access protected operational data.

---

## 📜 Regulatory Context & Compatibility

> **Note:** The mappings below are **informational only**. NHID-Clinical does not create or extend legal obligations under any of the listed frameworks. Consult qualified legal counsel for compliance determinations.

NHID-Clinical operates at the **operational layer**, complementing existing legal frameworks without conflict:

| Framework | What It Does | How NHID-Clinical Relates (Informational) |
|-----------|-------------|----------------------|
| **HIPAA** | Protects patient health information | NHID supports practices aligned with HIPAA's "Minimum Necessary" principle by ensuring identity is verified before operational data is exchanged. NHID does not interpret or extend HIPAA obligations. |
| **TCPA / FCC** | Governs outbound call consent | NHID addresses B2B inbound handshake content in workflows not covered by TCPA's consumer-protection scope. |
| **California B.O.T. Act** | Requires bot disclosure in online/social media contexts (Bus. & Prof. Code §17940–17945) | NHID applies analogous disclosure principles to B2B voice workflows — a channel the Act does not explicitly govern. This is alignment in intent, not statutory coverage. |
| **NIST AI RMF** | Framework for AI risk management | NHID operationalizes GOVERN, MAP, MEASURE, and MANAGE functions (see alignment table below) |

---

## 🛡️ The Standard (The Actual Rules)

> **Terminology:** The key words MUST, MUST NOT, SHOULD, and MAY in this section are used in accordance with [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119). These terms apply to implementations claiming NHID-Clinical conformance.

### 1. 📞 Outbound AI Agent Disclosure (Primary Scenario)

When a healthcare provider deploys an AI agent to call a payer or clearinghouse:

**Mandatory Identity Disclosure**
- AI MUST state "I am an automated system" (or equivalent) before any exchange of operational data (NPI, Member ID, Claim Number, or equivalent identifiers)
- AI MUST state the authorizing provider's name and NPI
- Example: "Hello, this is an automated system calling on behalf of Dr. Smith's Dental Office, NPI 1234567890."

**Prohibition of Deceptive Audio Artifacts**
- AI agents MUST NOT use simulated presence cues (breathing sounds, typing, artificial hesitation) designed to imply human presence
- Natural speech pacing and prosody are permitted
- Deceptive audio artifacts create unnecessary trust assumptions that can compromise security

**Authentication Best Practice**
- Human operators SHOULD verify provider identity before exchanging sensitive data
- Organizations are RECOMMENDED to implement verifiable digital tokens or BAA-linked reference codes rather than relying solely on public identifiers (NPI, EIN)
- Technical specifications for digital token and BAA-linked authentication protocols are candidates for a future companion specification

**Rationale:**
B2B healthcare calls present a unique threat vector. Unlike consumer-facing AI (regulated by TCPA/FCC), healthcare provider-to-payer calls currently operate in a regulatory gray area. HIPAA requires security and audit trails, but does not specify audio disclosure timing or authentication methods for non-human actors. This section provides operational guidance aligned with 2026 security best practices.

---

### 2. 🚪 Proactive Identity Assertion (PIA)

**The Rule:**
All non-human voice agents MUST proactively disclose their non-human identity **during the initial greeting** and **prior to the solicitation or intake of any operational data** (e.g., NPI, Member ID, Claim Number).

**Why "Pre-Data Exchange" Matters:**
Instead of saying "you must disclose within 3 seconds" (which fails in laggy VoIP calls), we say: **"Disclose BEFORE asking for sensitive data."** This is auditable, technology-agnostic, and accounts for real-world latency.

**✅ Compliant Example:**
> *"Hello, I am an automated assistant for BlueCross Claims. I can help you with status and eligibility. To begin, please say the NPI."*

**❌ Non-Compliant Example:**
> *"Hello, this is Sarah. Can I get the NPI?"*
> 
> **Violation:** Uses a human name without qualification AND requests data before disclosure.

---

### 3. 🎭 Prohibition of Deceptive Artifacts ("The Turing Boundary")

**The Rule:**
Agents MUST NOT employ synthetic audio artifacts that serve no communicative function other than to imply biological presence or mask processing latency.

**Translation:** Stop making your bots pretend to breathe.

**❌ Prohibited "Masking" Techniques:**

| Prohibited Artifact | Why It Is Banned | Compliant Alternative |
| :--- | :--- | :--- |
| **Synthetic Breathing** | Implies biological life functions | Natural prosody and pacing |
| **Fake Typing Sounds** | Deceptively implies human physical work | "Searching the system..." |
| **Scripted "Umm / Ahh"** | Masks processing latency deceptively | "One moment while I retrieve that..." |
| **Unqualified Human Name** | Creates false assumption of humanity | "This is Alex, an automated assistant..." |

**✅ What's ALLOWED (and encouraged):**
- Natural prosody and conversational tone
- Clear inflection and pacing for comprehension
- Professional, friendly language

**The Principle:** If an audio element serves no communicative purpose except to trick someone into thinking you're human—it's banned.

---

### 4. 🆘 Escalation & Safe Failover

**The Rule:**
When a human stakeholder explicitly requests a transfer or indicates the agent is failing to understand:

1.  **Immediate Acknowledgement (MUST):** *"I understand you need to speak to a specialist."*
2.  **Context Preservation (MUST):** Generate a reference number so the human doesn't have to re-explain everything
3.  **Safe Failover:**
    * ✅ **If human staff available (MUST):** Transfer immediately
    * 🌙 **If after hours (SHOULD):** State hours of operation + offer voicemail/callback

**❌ What's NOT Allowed (MUST NOT):**
- Infinite "I didn't understand" loops
- Sudden disconnection without explanation
- Forcing callers to restart from scratch

---

## ✅ Conformance & Certification

NHID-Clinical v1.3 introduces a formal conformance test suite and tiered certification framework.

| Document | Description |
|----------|-------------|
| [**Conformance Test Suite (CTS)**](conformance.md) | Five deterministic pass/fail tests (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01) — the authoritative checklist for claiming NHID-Clinical conformance |
| [**Certification Framework**](certification.md) | L1 (Baseline), L2 (Operational), L3 (Enterprise) trust tiers with badge system and evidence requirements |
| [**Registry Architecture**](registry.md) | Conceptual design for public verification layer (planned for v1.4+) |

---

## 📊 Audit & Evidence Requirements

**You don't need fancy compliance software.** Here's what counts as proof:

### Tier 1 (Minimum Required):
- **Transaction Log:** Text log showing "Identity Disclosed" timestamp vs. "Data Request" timestamp
- **Script Version Control:** Documentation proving the disclosure language was in production

### Tier 2 (Recommended):
- **Audio Snippet:** First 30 seconds of call recording (subject to your retention policies)

**The Goal:** Make compliance auditable without creating operational burden.

---

## 🔗 FHIR Technical Mapping (Companion Guidance)

**NHID-Clinical v1.3** is fundamentally an **operational governance standard** focused on real-time voice/agent behavior in B2B healthcare workflows. This section provides **recommended technical bindings** to HL7 FHIR for implementers who want to align with modern interoperability and audit requirements.

This mapping is **informative** and does not change the core conformance requirements of NHID-Clinical. It is designed to make adoption easier in FHIR-native environments while preserving the original intent: eliminating impersonation latency through clear, upfront, non-deceptive disclosure.

### Why FHIR Mapping?

- Many payers and large providers are moving to FHIR-based systems for audit, provenance, and security logging
- Supports stronger evidence for L2/L3 certification and HIPAA-adjacent audit readiness
- Enables future interoperability with broader HL7 AI transparency efforts

### Core Mappings

| NHID-Clinical Concept | Primary FHIR Resource | Recommended Usage | Notes / Extensions |
|----------------------|----------------------|-------------------|-------------------|
| **Proactive Identity Assertion (PIA)** & Mandatory Disclosure | `AuditEvent` + `Provenance` | Record the disclosure event with timestamp. Link to subsequent data requests. | Use `AuditEvent.occurredPeriod` to prove disclosure happened *before* data exchange |
| **Pre-Data Exchange Gate** | `AuditEvent` (sequence of events) | Two correlated events: (1) disclosure, (2) data request | Critical for auditability. `AuditEvent.entity.detail` can log the spoken disclosure text |
| **Agent & Organization Identification** (NPI, etc.) | `AuditEvent.agent` | `agent.who` reference to `Practitioner` or `Organization` with NPI identifier | Use standard NPI system URI: `http://hl7.org/fhir/sid/us-npi` |
| **Prohibition of Deceptive Artifacts** ("Turing Boundary") | `AuditEvent` + Extension | Custom extension: `nhid-deceptiveArtifacts` (boolean + description) | Flag compliance with natural prosody only |
| **Escalation & Safe Failover** | `AuditEvent` + `Task` / `Communication` | Log escalation request, reference ID, and outcome | `Task` for tracking human handoff with context preservation |
| **Audit Trail Requirements (All Tiers)** | `AuditEvent` (primary) | Structured logging for every interaction (L1 minimum) | Aligns with ATR-01 test |

### Example FHIR `AuditEvent` Records

**1. Compliant Disclosure + Data Request (Green Lane)**

```json
{
  "resourceType": "AuditEvent",
  "id": "nhid-compliant-call-20260503-001",
  "meta": {
    "profile": ["https://nhid-clinical.org/fhir/StructureDefinition/nhid-auditevent-disclosure"]
  },
  "action": "E",
  "recorded": "2026-05-03T14:22:45.123Z",
  "agent": [
    {
      "type": {
        "coding": [{ "code": "automated-voice-agent", "display": "Automated Voice Agent" }]
      },
      "who": {
        "identifier": {
          "system": "https://nhid-clinical.org/agent",
          "value": "agent-xyz-789"
        }
      },
      "requestor": false,
      "extension": [
        {
          "url": "https://nhid-clinical.org/fhir/Extension/nhid-compliance-level",
          "valueCode": "L2"
        }
      ]
    }
  ],
  "entity": [
    {
      "type": { "text": "VoiceCallSession" },
      "detail": [
        {
          "type": "nhidDisclosureStatement",
          "valueString": "Hello, this is an automated system calling on behalf of Dr. Smith's Dental Office, NPI 1234567890."
        },
        {
          "type": "nhidDisclosureTimestamp",
          "valueDateTime": "2026-05-03T14:22:41Z"
        },
        {
          "type": "nhidFirstDataRequestTimestamp",
          "valueDateTime": "2026-05-03T14:22:48Z"
        }
      ]
    }
  ]
}
```

**2. Escalation Event**

```json
{
  "resourceType": "AuditEvent",
  "id": "nhid-escalation-001",
  "action": "E",
  "recorded": "2026-05-03T14:25:12Z",
  "entity": [
    {
      "type": { "text": "VoiceCallSession" },
      "detail": [
        {
          "type": "nhidEscalationTrigger",
          "valueString": "Caller requested: Transfer me to a human"
        },
        {
          "type": "nhidReferenceID",
          "valueString": "ESC-REF-784291"
        },
        {
          "type": "nhidEscalationOutcome",
          "valueString": "Warm transfer completed with full context"
        },
        {
          "type": "nhidContextPreserved",
          "valueBoolean": true
        }
      ]
    }
  ]
}
```

**3. Non-Compliant Detection (Red Lane)**

```json
{
  "resourceType": "AuditEvent",
  "id": "nhid-noncompliant-deceptive-001",
  "action": "E",
  "recorded": "2026-05-03T09:15:33Z",
  "outcome": "8",
  "agent": [
    {
      "type": { "text": "Suspected AI Agent" },
      "name": "Sarah (unqualified)",
      "extension": [
        {
          "url": "https://nhid-clinical.org/fhir/Extension/nhid-deceptive-flag",
          "valueBoolean": true
        }
      ]
    }
  ],
  "entity": [
    {
      "detail": [
        {
          "type": "nhidDisclosureStatement",
          "valueString": "Hi, this is Sarah. Can I please have your NPI number?"
        },
        {
          "type": "nhidViolationDetected",
          "valueString": "Data requested before disclosure + deceptive unqualified name"
        }
      ]
    }
  ]
}
```

**4. After-Hours Failover**

```json
{
  "resourceType": "AuditEvent",
  "action": "E",
  "recorded": "2026-05-03T22:45:10Z",
  "entity": [
    {
      "detail": [
        {
          "type": "nhidEscalationTrigger",
          "valueString": "After-hours human request"
        },
        {
          "type": "nhidReferenceID",
          "valueString": "CB-20260503-3341"
        },
        {
          "type": "nhidFailoverAction",
          "valueString": "Callback offered for next business day"
        }
      ]
    }
  ]
}
```

### Implementation Note

Systems claiming NHID-Clinical conformance MAY use FHIR resources for logging. Use of FHIR is not required for L1 Baseline but is strongly recommended for L2/L3 production evidence and audit packages. This mapping is compatible with the AI Transparency on FHIR IG and standard `AuditEvent` / `Provenance` patterns.

---

## 📈 Success Metrics

How do you know if NHID-Clinical is working?

| Metric | Definition | Success Target |
| :--- | :--- | :--- |
| **Disclosure Failure Rate (DFR)** | Calls where data was requested *before* identity disclosure | **< 2%** |
| **Escalation Loop Frequency** | Callers repeating "Agent" or "Representative" >2 times | **< 1 per 100 calls** |
| **Average Handle Time (AHT)** | Reduction in duration by eliminating verification loops | **-15 to -30 seconds** |
| **Provider Satisfaction** | Post-interaction feedback rating | **> 85% Positive** |

---

## 🔗 Framework Alignment (ISO 42001 & NIST AI RMF)

NHID-Clinical is designed to operationalize high-level governance requirements into testable logic gates.

| NHID-Clinical Control | NIST AI RMF 1.0 (US) | ISO/IEC 42001:2023 (Global) | Operational Function |
| :--- | :--- | :--- | :--- |
| **Proactive Identity Assertion (PIA)** | **MEASURE 2.6** (Transparency)<br>**MAP 3.4** (Context) | **A.7.2** (System Transparency)<br>**B.9.1** (Communication) | Ensures stakeholders know they are interacting with an AI system *before* risk exposure. |
| **The "Turing Boundary"** (No Deception) | **GOV 1.5** (Risk Mgmt)<br>**MAP 3.4** (Human-AI Interaction) | **A.5.8** (Safety & Trust)<br>**A.9.2** (AI System Impact) | Prevents manipulative design patterns (e.g., fake breathing) that erode trust. |
| **Pre-Data Exchange Gate** | **MANAGE 1.2** (Risk Treatment)<br>**GOV 5.1** (Legal Compliance) | **A.6.2** (Data Management)<br>**A.8.2** (Data Privacy) | Enforces "Minimum Necessary" data access by verifying identity *before* PHI intake. |
| **Safe Failover / Escalation** | **MANAGE 4.2** (Human Oversight)<br>**GOV 5.2** (Feedback Loops) | **A.8.3** (Human Oversight)<br>**A.6.3** (Incident Management) | Guarantees a "Human-in-the-Loop" fallback when AI fails or trust is broken. |
| **Audit Logging** | **MANAGE 4.1** (Monitoring)<br>**MEASURE 2.2** (Validation) | **A.4.2** (Documentation)<br>**A.9.3** (Performance Eval) | Provides the evidentiary chain required for compliance audits. |


---

## 🚧 Known Gaps & Future Scope

**What v1.3 DOES NOT Cover (yet):**

- ⏳ **Patient-facing workflows:** Direct-to-consumer or clinical triage
- 📞 **Outbound calls (payer-initiated):** Proactive outbound calls originated by payers are not covered. Provider-initiated outbound calls to payers are addressed in Section 1.
- 🌍 **International compliance:** GDPR or non-U.S. regulatory contexts
- ♿ **Accessibility:** Multilingual support, deaf/hard-of-hearing accommodations
- 🔗 **Multi-entity integrations:** Complex scenarios with multiple payers/vendors
- 🏛️ **Live registry:** The registry architecture is defined in v1.3 but a live public registry is planned for v1.4+
- 🔧 **Technical implementation bindings:** Runtime enforcement specifications, event schemas (e.g., OpenTelemetry), and policy engine integrations (e.g., OPA/Cedar) are intentionally out of scope for v1.x. NHID-Clinical defines the governance layer — how systems should behave. Implementation specs are candidates for a companion technical specification.

**Translation:** This is v1.3, not the final word on AI identity in healthcare. We're building iteratively based on real operational feedback.

### Deliberate Scope Choice

NHID-Clinical v1.3 intentionally focuses exclusively on B2B administrative workflows. This is not a limitation — it is a deliberate strategy to achieve deep validation in the highest-value, highest-compliance segment before any expansion.

B2C/patient-facing use cases involve materially different regulatory, technical, and ethical considerations (FCC TCPA consent requirements, consumer protection laws, patient harm liability, accessibility standards) and will be addressed in a future major version once B2B adoption and certification are proven.

---

## 🗺️ v1.4 Roadmap

| Issue | Category | Priority | Why It Matters |
|-------|----------|----------|----------------|
| **Live Registry Launch** | Infrastructure | 🔴 High | Public verification layer for certified implementations |
| **Multilingual Support** | Accessibility | 🟡 Medium | Extend standard to non-English B2B workflows |
| **Outbound Call Guidance (Payer-initiated)** | Scope Expansion | 🔴 High | Payer-initiated outbound calls currently out of scope |
| **Technical Implementation Bindings** | Engineering | 🟡 Medium | Runtime enforcement spec with event schema (OpenTelemetry) and policy engine (OPA/Cedar) guidance |
| **Pilot Certification Program** | Enforcement | 🟢 Low | Work with 2–3 early vendors for first L1/L2 certifications |

**📅 Target Release:** Q1–Q2 2027  
**🐛 Track Progress:** [View Issues](https://github.com/thankcheeses/NHID-Clinical/issues)

---

## 🤝 How to Contribute

This is an **open standard**—your input makes it better.

**We're looking for:**
- 💬 **Technical feedback** on implementation feasibility
- 🏥 **Real-world experience** from healthcare IT teams
- ⚖️ **Compliance perspective** from HIPAA officers and payer operations
- 🐛 **Edge cases** we haven't thought of yet

**How to participate:**
1. 🗣️ [Open a GitHub Discussion](https://github.com/thankcheeses/NHID-Clinical/discussions) for questions
2. 🐛 [File an Issue](https://github.com/thankcheeses/NHID-Clinical/issues) for specific problems
3. 📧 Email feedback to: [validation@nhid-clinical.org](mailto:validation@nhid-clinical.org)

---

## 📄 License

This work is licensed under **Creative Commons Attribution 4.0 International (CC-BY 4.0)**.

**What this means:**
- ✅ You can use it commercially
- ✅ You can modify it for your organization
- ✅ You can share it freely
- ⚠️ You must give credit to the original author

**Author:** Brianna Baynard  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Brianna%20Baynard-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/brianna-baynard)


---

## 📚 Changelog

### v1.3 (Current)
- 📋 Introduced Conformance Test Suite (CTS) — five deterministic pass/fail tests (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01)
- 🏅 Added tiered Certification Framework — L1 (Baseline), L2 (Operational), L3 (Enterprise)
- 🗂️ Defined Registry Architecture — public verification layer design for v1.4+ implementation
- 🔤 Adopted RFC 2119 MUST/SHOULD/MAY terminology throughout control requirements
- 📝 Regulatory language precision — all framework alignment tables labeled informational only; removed overreach in HIPAA framing
- 💲 Explicit non-validated framing on $40M industry cost estimate

### v1.2
- 🤖 Added Bot-to-Bot Interaction Workflow (Section 1.5) — deadlock prevention
- 📞 Added IVR Interruption & Resilience Mode (Section 1.3.1)
- 📋 Added Failover Confirmation Logging with Callback Ticket ID (Section 2.4.1)
- 🔀 Defined Escalation Transfer Tiers — Type A (Warm) and Type B (Cold) (Section 3.2)
- 🔐 Introduced optional Network-Layer Identity via SIP headers (Section 4.3)

### v1.1
- ✨ Shifted from "3-second window" to **"Pre-Data Exchange gate"** for better auditability
- 📝 Added "Known Gaps & Future Scope" for transparency
- 🎯 Refined positioning to emphasize governance best practice over regulatory equivalence
- 🎭 Clarified distinction between natural prosody (good) and deceptive artifacts (bad)
- 📊 Added success metrics and audit requirements

### v1.0 (Initial Draft)
- 🚀 Initial release with temporal disclosure requirements
- 🗺️ NIST/HIPAA alignment mapping

---

## 🙏 Acknowledgments

This standard was developed based on operational experience in payer-side HIPAA enforcement, federal compliance systems, and regulated healthcare workflows.

Special thanks to the healthcare IT community for feedback during early drafts, and to the NIST AI RMF team for providing the governance framework that made this operationalization possible.

---

**Built with ❤️ by someone who spent too many hours asking "Wait, am I talking to a robot?"**

*Let's make healthcare AI transparent, trustworthy, and a little less frustrating.*
