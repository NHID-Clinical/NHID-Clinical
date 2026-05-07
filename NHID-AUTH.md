# NHID-Auth v1.0 — Delegated Authorization Layer

**STATUS:** Companion specification to NHID-Clinical v1.3
**DEPENDENCY:** NHID-Clinical v1.3 (context only, not enforcement)
**LICENSE:** CC-BY 4.0

---

## Purpose

NHID-Auth defines how a non-human voice agent is authorized to act on behalf of a real-world entity in healthcare B2B workflows.

**Core Question:** Not just "who is speaking" — but "who allowed them to speak?"

---

## Core Principle

**Identity ≠ Authorization**

Public identifiers (NPI, caller ID, organization name) are not proof of delegated authority.

Authorization must be:
- Explicitly granted
- Scoped to specific actions
- Time-bound
- Revocable

---

## Authorization Model

All valid authorization MUST include:

### 1. Delegating Entity
The entity granting permission:
- Provider organization
- Payer organization
- Healthcare system
- Contracted vendor

### 2. Authorized Actor
The system acting on behalf of the entity:
- AI voice agent
- Vendor automation platform
- Delegated service system

### 3. Scope of Permission
Defines what the agent is allowed to do.

**Examples:**
- Eligibility inquiry only
- Claims status retrieval only
- Appointment scheduling only
- No PHI modification rights

### 4. Duration
Authorization MUST include:
- Start timestamp
- Expiration timestamp OR renewal condition

### 5. Revocation Capability
Authorization MUST be revocable:
- Immediate invalidation mechanism, OR
- Time-bounded expiry enforcement

---

## Attestation Format (Minimum Viable)

NHID-Auth v1.0 does NOT require cryptographic infrastructure.

It defines a structured attestation object:

```json
{
  "delegating_entity": "Provider_OR_Payer_ID",
  "authorized_actor": "Vendor_OR_AI_System_ID",
  "scope": [
    "claims_inquiry",
    "eligibility_check"
  ],
  "issued_at": "YYYY-MM-DDTHH:MM:SSZ",
  "expires_at": "YYYY-MM-DDTHH:MM:SSZ",
  "revocable": true,
  "reference_id": "AUTH-XXXXX"
}
```

---

## Validation Requirements (Conceptual)

NHID-Auth compliance requires verification of:

**A. Existence of delegation**
Attestation must be present

**B. Scope limitation**
Actions must match declared permissions

**C. Temporal validity**
Request must occur within valid time window

**D. Revocation awareness**
System must reject revoked authorizations

---

## Relation to NHID-Clinical v1.3

| Layer | Function |
|-------|----------|
| NHID-Clinical v1.3 | Disclosure BEFORE data exchange |
| NHID-Auth v1.0 | Permission TO act on data |

**They are independent.**

- NHID-Clinical = Behavioral safety gate
- NHID-Auth = Access control system

---

## Non-Goals

NHID-Auth v1.0 does NOT define:

- SIP transport layers
- Cryptographic handshake protocols
- Registry implementation
- Certification programs
- Enforcement infrastructure

These belong to future NHID-Protocol / NHID-Registry layers.

---

## Design Intent

NHID-Auth is intentionally:

- **Portable** (works without crypto requirement)
- **Audit-friendly** (human-readable attestation possible)
- **Extensible** (can upgrade to JWT/PKI later)
- **Decoupled** from NHID-Clinical enforcement

---

## Security Note

This spec assumes:

> Malicious actors may have valid identity signals but invalid authorization

Therefore:
- Identity verification alone is insufficient
- Authorization must be independently validated

---

## Implementation Status

**v1.0 Status:** Conceptual framework
**Future Work:** Registry architecture, JWT implementation, real-time revocation protocols

For pilot implementations, contact: validation@nhid-clinical.org

---

**NHID-Auth v1.0** | Author: Brianna Baynard | CC-BY 4.0 | 2026
