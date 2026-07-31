# NHID-Clinical FHIR R4 AuditEvent Mapping

**Version:** 1.0  
**FHIR version:** R4 (4.0.1)  
**Status:** Validated against HL7 FHIR R4 base specification  

> **Scope of conformance claim:** This profile is validated against the HL7 FHIR R4 base specification only. No conformance to any named HL7 Implementation Guide (e.g., IHE BALP) is claimed or implied.

> **Project scope:** NHID-Clinical is a voluntary open proposal by Brianna Baynard. CC BY 4.0. Not a certified standard. Not a regulatory requirement.

---

## Overview

Every NHID-Clinical conformance test suite (CTS) execution produces a FHIR R4 `Bundle` (type: `collection`) containing one `AuditEvent` resource per conformance milestone. The emitter is implemented in [`src/fhir_audit_emitter.py`](../src/fhir_audit_emitter.py).

The Bundle can be stored, transmitted, or ingested by any FHIR R4-compatible system as a healthcare-native audit record of what an AI voice agent did on a call.

---

## Milestones and AuditEvent Mapping

### Milestone 1 — Session Start (`nhid-session-start`)

Emitted: always, once per call session.

| AuditEvent Element | Value |
|---|---|
| `type` | `DCM#110100` Application Activity |
| `subtype[0]` | `nhid-subtype#nhid-session-start` |
| `action` | `E` (Execute) |
| `outcome` | `0` (Success) |
| `agent[0].requestor` | `true` (AI voice agent) |
| `agent[0].type` | `DCM#110153` Source Role ID |
| `agent[1].requestor` | `false` (Payer system) |
| `agent[1].type` | `DCM#110152` Destination Role ID |
| `agent[2].requestor` | `false` (Provider org, on-behalf-of) — _present only when `provider_npi` supplied_ |
| `source.observer` | NHID-Clinical Policy Engine v1 |
| `entity[0].type` | `audit-entity-type#2` System Object |
| `entity[0].role` | `object-role#20` Job |

---

### Milestone 2 — Identity Disclosure (`nhid-identity-disclosure`)

Emitted: when `healthcare_governance.disclosure_timestamp` is set, or when the event's `boundary_violations` includes `IDG-01`, or when the PolicyDecision includes an IDG-01 violation.

Implements: IDG-01 (Identity Disclosure Gate)

| AuditEvent Element | Value |
|---|---|
| `type` | `DCM#110113` Security Alert |
| `subtype[0]` | `nhid-subtype#nhid-identity-disclosure` |
| `action` | `E` (Execute) |
| `outcome` | See outcome table below |
| `entity[1].description` | First 200 chars of `identity_assertion_text` (when present) |

**Outcome coding for this milestone:**

| Condition | `outcome` | `outcomeDesc` |
|---|---|---|
| `disclosure_timestamp` set AND `identity_assertion_text` non-empty | `0` | Disclosure confirmed |
| `disclosure_timestamp` set, `identity_assertion_text` absent | `4` | Timestamp set, assertion text missing |
| `disclosure_timestamp` null (IDG-01 violation) | `8` | Identity not disclosed before data exchange |

---

### Milestone 3 — Authorization Verification (`nhid-auth-verification`)

Emitted: when `provider_npi` is supplied at call time. Captures the fact that the provider organisation's NPI was recorded as the authorizing principal for this call. Maps to the NHID-Auth v2 delegation chain.

| AuditEvent Element | Value |
|---|---|
| `type` | `DCM#110114` User Authentication |
| `subtype[0]` | `nhid-subtype#nhid-auth-verification` |
| `action` | `E` |
| `outcome` | `0` |
| `agent[2].who.identifier.system` | `http://hl7.org/fhir/sid/us-npi` |
| `agent[2].who.identifier.value` | Provider NPI |

---

### Milestone 4 — Pre-Data-Exchange Gate Decision (`nhid-phi-gate`)

Emitted: when `healthcare_governance.phi_accessed` is non-empty, or when the event or decision contains a PDX-01 violation.

Implements: PDX-01 (PHI Data Exchange Gate)

| AuditEvent Element | Value |
|---|---|
| `type` | `DCM#110113` Security Alert |
| `subtype[0]` | `nhid-subtype#nhid-phi-gate` |
| `action` | `E` |
| `outcome` | See outcome table below |

**Outcome coding for this milestone:**

| Condition | `outcome` | `outcomeDesc` |
|---|---|---|
| `disclosure_timestamp` set AND `phi_accessed` non-empty | `0` | Gate cleared |
| `disclosure_timestamp` null AND `phi_accessed` non-empty | `8` | PHI attempted before disclosure |
| PDX-01 violation in boundary_violations, no PHI accessed | `8` | Gate triggered, disclosure missing |

---

### Milestone 5 — PHI Exchange Start (`nhid-phi-exchange`)

Emitted: when `disclosure_timestamp` is set **and** `phi_accessed` is non-empty. Represents the moment PHI exchange began after the gate was cleared.

| AuditEvent Element | Value |
|---|---|
| `type` | `DCM#110110` Patient Record |
| `subtype[0]` | `nhid-subtype#nhid-phi-exchange` |
| `action` | `R` (Read) |
| `outcome` | `0` |
| `entity[1].description` | `"PHI categories accessed: {list}"` |

PHI categories are drawn from `healthcare_governance.phi_accessed`. Possible values per schema: `member_id`, `npi`, `date_of_birth`, `claim_number`, `prior_auth_number`, `diagnosis_code`, `procedure_code`, `provider_tin`.

---

### Milestone 6 — Escalation/Transfer (`nhid-escalation`)

Emitted: when `healthcare_governance.escalation_timestamp` is set, or when the event/decision contains an EIT-01 violation.

Implements: EIT-01 (Escalation & Intervention)

| AuditEvent Element | Value |
|---|---|
| `type` | `DCM#110100` Application Activity |
| `subtype[0]` | `nhid-subtype#nhid-escalation` |
| `action` | `E` |
| `outcome` | See outcome table below |

**Outcome coding:**

| Condition | `outcome` |
|---|---|
| `escalation_outcome == "connected"` | `0` |
| `escalation_outcome` in `{"unavailable", "timeout"}` | `4` |
| EIT-01 violation (no escalation path) | `8` |
| Other / unknown outcome | `4` |

---

### Milestone 7 — Call Termination (`nhid-call-end`)

Emitted: always.

| AuditEvent Element | Value |
|---|---|
| `type` | `DCM#110100` Application Activity |
| `subtype[0]` | `nhid-subtype#nhid-call-end` |
| `action` | `E` |
| `outcome` | Derived from PolicyDecision action (see table below) |

**Outcome coding from PolicyDecision:**

| PolicyDecision action | `outcome` |
|---|---|
| `CONTINUE_AI` | `0` |
| `ESCALATE_HUMAN` | `0` |
| `LOG_ONLY` (no critical violations) | `4` |
| `DISCLOSE_IDENTITY` / `DENY_DATA` (critical violation) | `8` |
| No decision supplied | `0` |

---

## Agent Slices

Every AuditEvent in the Bundle carries the same three agent slices (two when no provider NPI is provided).

### Agent 0 — AI Voice Agent (requestor)

```json
{
  "type": {
    "coding": [{
      "system": "http://dicom.nema.org/resources/ontology/DCM",
      "code": "110153",
      "display": "Source Role ID"
    }]
  },
  "who": {
    "identifier": {
      "system": "https://nhid-clinical.org/fhir/agents",
      "value": "<agent_id>"
    },
    "display": "<agent_name>"
  },
  "requestor": true
}
```

### Agent 1 — Payer System (destination)

```json
{
  "type": {
    "coding": [{
      "system": "http://dicom.nema.org/resources/ontology/DCM",
      "code": "110152",
      "display": "Destination Role ID"
    }]
  },
  "who": { "display": "Payer Organization" },
  "requestor": false
}
```

### Agent 2 — Provider Organization (on-behalf-of, when NPI present)

```json
{
  "type": {
    "coding": [{
      "system": "https://nhid-clinical.org/fhir/CodeSystem/agent-role",
      "code": "principal",
      "display": "Principal Organization (on behalf of)"
    }]
  },
  "who": {
    "identifier": {
      "system": "http://hl7.org/fhir/sid/us-npi",
      "value": "<provider_npi>"
    },
    "display": "<provider_name>"
  },
  "requestor": false
}
```

---

## Source Element

Identical in every AuditEvent. Identifies the NHID-Clinical policy engine as the auditing system.

```json
{
  "site": "nhid-clinical.org",
  "observer": {
    "identifier": {
      "system": "https://nhid-clinical.org/fhir/systems",
      "value": "nhid-policy-engine-v1"
    },
    "display": "NHID-Clinical Policy Engine v1"
  },
  "type": [{
    "system": "http://terminology.hl7.org/CodeSystem/security-source-type",
    "code": "4",
    "display": "Application Server"
  }]
}
```

---

## Entity Slice — Call/Transaction Reference

Every AuditEvent carries a base entity identifying the NHID-Clinical session.

```json
{
  "what": {
    "identifier": {
      "system": "https://nhid-clinical.org/fhir/sessions",
      "value": "<session_id>"
    }
  },
  "type": {
    "system": "http://terminology.hl7.org/CodeSystem/audit-entity-type",
    "code": "2",
    "display": "System Object"
  },
  "role": {
    "system": "http://terminology.hl7.org/CodeSystem/object-role",
    "code": "20",
    "display": "Job"
  },
  "description": "NHID-Clinical call session"
}
```

---

## Required vs. Optional Elements

| Element | Required by R4 | Present in NHID profile | Notes |
|---|---|---|---|
| `type` | **Yes** | **Yes** — always DCM code | |
| `recorded` | **Yes** | **Yes** — from event.timestamp | |
| `agent[*].requestor` | **Yes** | **Yes** — bool on every agent | |
| `source.observer` | **Yes** | **Yes** — policy engine identifier | |
| `outcome` | No | Yes — outcome coded from decision | |
| `outcomeDesc` | No | Yes — human-readable explanation | |
| `action` | No | Yes — `E` or `R` per milestone | |
| `subtype` | No | Yes — custom code for milestone | Extensible binding |
| `agent[*].type` | No | Yes — DCM or NHID-role code | Extensible binding |
| `entity` | No | Yes — session reference | |

---

## Code Systems

| System URI | Description | Standard |
|---|---|---|
| `http://dicom.nema.org/resources/ontology/DCM` | DICOM audit event type codes | DICOM supplement 95 |
| `http://terminology.hl7.org/CodeSystem/audit-entity-type` | Entity type codes | HL7 |
| `http://terminology.hl7.org/CodeSystem/object-role` | Object role codes | HL7 |
| `http://terminology.hl7.org/CodeSystem/security-source-type` | Source type codes | HL7 |
| `https://nhid-clinical.org/fhir/CodeSystem/audit-event-subtype` | NHID milestone subtypes | NHID-Clinical (this spec) |
| `https://nhid-clinical.org/fhir/CodeSystem/agent-role` | NHID agent role (on-behalf-of) | NHID-Clinical (this spec) |
| `http://hl7.org/fhir/sid/us-npi` | US National Provider Identifier | CMS NPPES |

Custom NHID code systems use stable URIs anchored to `nhid-clinical.org`. They are not required to be resolvable for FHIR R4 base validation.

---

## Validation

The example Bundle at [`examples/fhir/nhid-compliant-call-bundle.json`](../examples/fhir/nhid-compliant-call-bundle.json) is validated in CI against FHIR R4 using the official HL7 FHIR validator (`validator_cli.jar`, version `-version 4.0.1`). The CI step is defined in `.github/workflows/nhid-gates.yml` (`fhir_validation` job) and blocks merge on validation errors.

To validate locally:
```bash
java -jar tools/validator_cli.jar -version 4.0.1 examples/fhir/nhid-compliant-call-bundle.json
```

---

## Known Warnings (Acceptable)

| Warning class | Reason acceptable |
|---|---|
| "Unknown code in extensible binding" for `nhid-subtype` codes | NHID-Clinical defines its own subtype system; R4 allows custom codes in extensible bindings |
| "Unknown code in extensible binding" for `nhid-agent-role` principal | Same rationale |
| Terminology server unreachable for DCM system | DCM codes are well-known; offline validation may warn but the codes are valid |

Errors are zero-tolerance. The CI gate fails on any validator Error line; warnings are documented here and are acceptable.

---

## Ingestion by a Payer Organization

See [`examples/fhir/README.md`](../examples/fhir/README.md) for a step-by-step guide to ingesting the Bundle into a FHIR R4-compatible system.
