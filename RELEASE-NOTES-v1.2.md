# NHID-Clinical v1.2 Release Notes

**Release Date:** Q2 2026  
**Status:** Released  
**Author:** Brianna Baynard ([@baynardmalone](https://twitter.com/baynardmalone))

---

## What's New in v1.2

v1.2 is an incremental refinement of v1.1. The core principles remain unchanged — proactive disclosure before any data exchange, and no deceptive audio artifacts. This release addresses practical edge cases identified through real-world feedback and resolves GitHub issues #1–5.

---

## Changes

### 1.3.1 — Handling IVR Interruptions & Timeouts *(New)*

**Problem:** Strict payer IVR systems sometimes barge in or time out before a standalone disclosure can complete, causing calls to fail before they start.

**Change:** Adds a **"Combined Turn" exception** and **Resilience Mode**.

- AI agents must attempt standalone disclosure first
- If an IVR interruption or timeout occurs before disclosure can complete, the agent may combine disclosure + data request on the next attempt
- Resilience Mode activates after at least one failed standalone disclosure attempt

**Why it matters:** Prevents compliant calls from failing due to aggressive IVR timeout logic that is outside the agent's control.

---

### 1.5 — Bot-to-Bot Interaction Workflow *(New Section)*

**Problem:** When two automated systems call each other, the existing disclosure rules could cause deadlock loops — both sides waiting for the other to speak first.

**Change:** Adds specific guidance for bot-to-bot calls.

- Condensed disclosure format allowed: `"Automated Caller"` is sufficient when both sides are automated
- Bot-to-bot detection via silence patterns or audio fingerprinting
- Deadlock prevention: after 2 failed acknowledgment attempts, the initiating agent proceeds to data exchange
- Impersonation risk is recognized as near-zero in pure bot-to-bot scenarios

**Why it matters:** Solves a real architectural gap that caused infinite loops in automated payer-provider integrations.

---

### 2.4.1 — Failover Confirmation Logging *(New)*

**Problem:** Voicemail drops and missed callbacks created "silent failure" liability — no record of what happened or when.

**Change:** Requires positive logging for all voicemail and callback interactions.

- Mandatory fields: timestamp, response codes, Callback Ticket ID
- Agents may not promise specific callback times unless contractually guaranteed by the payer
- All failover paths must generate an auditable confirmation record

**Why it matters:** Reduces compliance debt and missed deadline liability. Makes failover paths as auditable as live calls.

---

### 3.2 — Escalation Transfer Tiers *(New)*

**Problem:** v1.1 required "safe failover" but did not define what that means for legacy vs. modern telephony systems.

**Change:** Defines two compliant escalation methods.

**Type A — Warm Transfer (Preferred):**
- Full CTI data payload passed to receiving agent
- Reference ID generated and communicated to caller
- Context preserved — caller does not repeat themselves

**Type B — Cold Transfer + Verbal Handoff (Minimum Viable):**
- Verbal summary provided before transfer
- Reference ID issued
- Acceptable for legacy systems that cannot support CTI data

**Non-Compliant (Explicit):**
- Blind transfers with no context or reference ID
- Disconnection without explanation

**Why it matters:** Gives compliance and engineering teams clear, tiered guidance instead of vague "safe failover" language.

---

### 4.3 — Network-Layer Identity / Tier 3 Evidence *(New — Optional)*

**Problem:** Verbal disclosure alone can be spoofed, disputed, or missed in noisy telephony environments.

**Change:** Introduces optional SIP/VoIP header-based identity assertion.

Proposed headers:
- `X-AI-Agent-ID` — unique agent identifier
- `X-AI-Provider-NPI` — provider NPI for the deploying organization
- `X-Disclosure-Mode` — indicates disclosure method used (verbal, header, combined)

These headers provide cryptographic, machine-readable proof of identity that does not rely on audio. In VoIP-native environments, this can reduce impersonation latency to near zero.

**Status:** Optional in v1.2. Community feedback requested on adoption feasibility before making mandatory in a future version.

**Why it matters:** Future-proofs the standard for modern SIP-native infrastructure and reduces reliance on verbal channels that can fail.

---

## What Did Not Change

The following core requirements remain identical to v1.1:

- Proactive disclosure **before** any PHI or operational data exchange
- Prohibition on deceptive audio artifacts (no fake breathing, typing sounds, unqualified human names)
- Pre-Data Exchange Gate as the primary compliance boundary
- Emphasis on auditability and escalation to human agents
- Voluntary, open-source, B2B healthcare administrative focus
- Alignment with NIST AI RMF, HIPAA principles, California B.O.T. Act, and FCC proposed rules

---

## Issues Resolved

| Issue | Description | Resolution |
|-------|-------------|------------|
| #1 | Bot-to-bot deadlock with no guidance | Section 1.5 |
| #2 | IVR barge-in causing disclosure failures | Section 1.3.1 |
| #3 | Escalation undefined for legacy systems | Section 3.2 |
| #4 | Silent failure on voicemail/callback paths | Section 2.4.1 |
| #5 | No technical identity layer beyond verbal | Section 4.3 |

---

## Known Limitations in v1.2

The following remain out of scope and are tracked for future versions:

- Patient-facing and direct-to-consumer workflows
- Outbound payer-initiated calls
- International compliance (GDPR, non-U.S. jurisdictions)
- Multilingual support and accessibility accommodations
- Formal certification or enforcement mechanisms

---

## How to Contribute

v1.3 planning is open. We are specifically seeking feedback on:

- Whether the SIP header proposal (Section 4.3) is feasible for your stack
- Whether the Combined Turn exception creates unintended compliance gaps
- Edge cases in multi-payer or multi-vendor integrations
- Accessibility requirements for multilingual or hearing-impaired workflows

[Open a GitHub Discussion](https://github.com/thankcheeses/NHID-Clinical/discussions) or [file an issue](https://github.com/thankcheeses/NHID-Clinical/issues).

---

**Author:** Brianna Baynard  
**License:** CC-BY 4.0 — use freely, give credit  
**Contact:** validation@nhid-clinical.org
