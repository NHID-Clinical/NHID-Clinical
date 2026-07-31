# NHID-Clinical FHIR R4 AuditEvent Examples

This directory contains example FHIR R4 Bundles produced by the NHID-Clinical
conformance test suite emitter (`src/fhir_audit_emitter.py`).

Every Bundle is validated against HL7 FHIR R4 (version 4.0.1) in CI before merge.
No conformance to any named HL7 Implementation Guide is claimed.

---

## Files

| File | Call scenario | Milestones |
|---|---|---|
| `nhid-compliant-call-bundle.json` | Full conformant call — all 7 milestones | session-start, identity-disclosure, auth-verification, phi-gate, phi-exchange, escalation, call-end |

---

## Full Conformant Call (`nhid-compliant-call-bundle.json`)

### Scenario

Beacon (an outbound AI voice agent, `agent_4001krn32nmwe5t8mqzgee0w84rj`) calls a payer
to check claim status on behalf of Sunny Dental Group (NPI 1234567890).

| Milestone | Outcome | Notes |
|---|---|---|
| Session start | Success | Call initiated |
| Identity disclosure | Success (outcome=0) | Agent disclosed non-human identity at T+5s |
| Auth verification | Success (outcome=0) | Provider NPI 1234567890 recorded |
| PHI gate | Success (outcome=0) | Gate cleared — disclosure confirmed before PHI |
| PHI exchange | Success (outcome=0) | claim_number + npi accessed |
| Escalation | Success (outcome=0) | Caller requested human; transfer connected |
| Call end | Success (outcome=0) | CONTINUE_AI — no violations |

### Structure

```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    { "resource": { "resourceType": "AuditEvent", ... } },
    ...
  ]
}
```

---

## How a Payer Would Ingest This Bundle

### 1. Receive the Bundle

The Bundle can be delivered via:
- REST POST to `[base]/Bundle` on your FHIR R4 server
- File transfer / SFTP at the end of a call batch
- Embedded in the NHID-Clinical session trace alongside the NHID trace JSON

### 2. POST each AuditEvent individually (recommended for searchability)

```bash
# Extract each AuditEvent and POST it to your FHIR server
# Example using jq + curl against a FHIR R4 server:

cat nhid-compliant-call-bundle.json \
  | jq -c '.entry[].resource' \
  | while read ae; do
      curl -s -X POST "$FHIR_BASE/AuditEvent" \
        -H "Content-Type: application/fhir+json" \
        -d "$ae"
    done
```

### 3. Query by session

```bash
# Find all audit events for a session
curl "$FHIR_BASE/AuditEvent?entity-name=CA1234567890abcdef1234567890abcd"
```

Or using the NHID session identifier system:
```bash
curl "$FHIR_BASE/AuditEvent?entity:identifier=https://nhid-clinical.org/fhir/sessions|CA1234567890abcdef1234567890abcd"
```

### 4. Query by agent

```bash
# All events from a specific AI agent
curl "$FHIR_BASE/AuditEvent?agent:identifier=https://nhid-clinical.org/fhir/agents|agent_4001krn32nmwe5t8mqzgee0w84rj"
```

### 5. Query for violations (outcome != 0)

```bash
curl "$FHIR_BASE/AuditEvent?outcome=4,8,12"
```

### 6. Retention

CMS-0057-F requires 5-year retention for prior authorization records. AuditEvents
from NHID-Clinical call sessions should be retained for the same period as the
underlying claim records they accompany.

---

## Generating Your Own Bundles

```python
from src.fhir_audit_emitter import build_audit_bundle
import json

# session — NHID-Clinical session context
session = {"session_id": "CA...", "turn_count": 3}

# event — one NHID-Clinical trace event (conforming to nhid_trace_schema_v1)
event = { ... }

# decision — optional PolicyDecision from evaluate_all()
bundle = build_audit_bundle(session, event, provider_npi="1234567890")
print(json.dumps(bundle, indent=2))
```

See [`docs/fhir-auditevent-mapping.md`](../../docs/fhir-auditevent-mapping.md)
for the full element-level mapping specification.

---

## Validating Locally

```bash
# Download the HL7 FHIR validator (requires Java 17+)
mkdir -p tools
curl -L -o tools/validator_cli.jar \
  https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar

# Validate the example bundle against R4
java -jar tools/validator_cli.jar -version 4.0.1 examples/fhir/nhid-compliant-call-bundle.json
```

Expected output: zero errors. Warnings about custom code systems are acceptable
(see [`docs/fhir-auditevent-mapping.md`](../../docs/fhir-auditevent-mapping.md)
for the documented-acceptable warning list).
