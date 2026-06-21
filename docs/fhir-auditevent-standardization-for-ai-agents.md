# Standardized Clinical Audit Event Formats for AI Agents

**Version:** 1.0 · **FHIR version:** R4 (4.0.1) · **Status:** Reference normalization layer, validated against base spec only

> **Scope of conformance claim:** This document describes how NHID-Clinical's internal event
> model normalizes into FHIR R4 `AuditEvent`. It is validated against the **HL7 FHIR R4 base
> specification only**. No conformance to any named HL7 Implementation Guide (e.g., IHE BALP)
> is claimed or implied — see the [PDF consistency review](pdf-consistency-and-grammar-review.md)
> for places where older drafts incorrectly implied such conformance.
>
> For the detailed, field-by-field milestone-to-AuditEvent mapping (the 7 milestones, agent
> slices, outcome coding tables, code systems, and CI validation process), see
> [fhir-auditevent-mapping.md](fhir-auditevent-mapping.md). This document covers the layer
> *above* that mapping: the canonical event model it's built on, how to extend it, how to
> version it, and how it's meant to be consumed downstream.

---

## 1. Why a separate normalization layer

NHID's policy engine emits internal events shaped for **deterministic policy evaluation** (the `session`/`event` dicts described in the Master Knowledge Archive §5.2) — fast, flat, Python-native. FHIR `AuditEvent` is shaped for **healthcare-native interoperability** — verbose, coded, designed to be ingested by systems NHID-Clinical doesn't control. Forcing the policy engine to *produce* FHIR-shaped events directly would couple a fast internal hot path to a slow, externally-governed schema. Instead, `src/fhir_audit_emitter.py` is a one-way translation layer: internal event → FHIR `AuditEvent`, run after the policy decision is already made.

This also means the FHIR layer can evolve (new milestones, new extensions) without touching the policy engine's evaluation logic, and the policy engine's internal schema can evolve without breaking previously-emitted FHIR bundles, as long as the emitter's mapping is versioned (§6).

## 2. Canonical event types and lifecycle milestones

Every call session produces a deterministic sequence of milestones, each emitted as exactly one `AuditEvent` (some conditionally — see [the mapping doc](fhir-auditevent-mapping.md) for exact emission conditions):

| Order | Milestone code | Fires on | Implements control |
| :-- | :-- | :-- | :-- |
| 1 | `nhid-session-start` | Always, once per call | — (structural) |
| 2 | `nhid-identity-disclosure` | Disclosure occurs, or IDG-01 violation | IDG-01 |
| 3 | `nhid-auth-verification` | `provider_npi` supplied | NHID-Auth v2 (delegation chain) |
| 4 | `nhid-phi-gate` | PHI access attempted, or PDX-01 violation | PDX-01 |
| 5 | `nhid-phi-exchange` | Disclosure confirmed AND PHI accessed | PDX-01 (post-gate) |
| 6 | `nhid-escalation` | Escalation requested, or EIT-01 violation | EIT-01 |
| 7 | `nhid-call-end` | Always | — (structural; outcome reflects final `PolicyDecision`) |

This ordering is the call's **lifecycle skeleton**. A fully conformant call emits milestones 1, 2, 4 (cleared), 5 (if PHI was actually needed), 7 — milestones 3 and 6 are conditional on whether the call used cryptographic delegation or an escalation was requested at all. A non-conformant call's milestone sequence is itself diagnostic: e.g., milestone 4 firing with an `outcome=8` *before* milestone 2 ever fires with `outcome=0` is the FHIR-native signature of an IDG-01/PDX-01 impersonation-latency violation.

## 3. Normalized event schema

The schema below is the **pre-FHIR canonical form** — what `fhir_audit_emitter.py` consumes before producing the AuditEvent resources. It is the same shape as the ATR-01-required event fields (Master Knowledge Archive §2.2/§5.2), organized here for downstream consumers who want to validate or process events *before* they're translated to FHIR (e.g., for the per-turn webhook use case in §4).

```json
{
  "event_id": "uuid-v4",
  "timestamp": "2026-06-01T10:00:01Z",
  "session_id": "CA123456789",
  "request_id": "req-001",
  "event_type": "POLICY",
  "actor_id": "agent_beacon_001",
  "state_before": "ACTIVE",
  "state_after": "ACTIVE",
  "replay_mode": "live",
  "external_calls_cached": false,
  "counterparty_type": "human_operator",
  "execution_context": {
    "pipeline_version": "1.0.0",
    "policy_engine_version": "1.0.0",
    "nhid_schema_version": "1.0"
  },
  "healthcare_governance": {
    "disclosure_timestamp": "2026-06-01T10:00:01Z",
    "identity_assertion_text": "I am an automated system",
    "deceptive_artifact_flags": [],
    "escalation_timestamp": null,
    "escalation_outcome": null,
    "phi_accessed": []
  },
  "input_payload": {
    "speech_text": "What is the member ID?",
    "raw_form_fields": null
  },
  "delegation": {
    "provider_npi": "1234567890",
    "delegation_id": "8f14e45f-...-uuid",
    "agent_public_key_b64": null
  }
}
```

The `delegation` block is present only when NHID-Auth v2 (Tier 2) is in use; its absence is itself meaningful (it means milestone 3, `nhid-auth-verification`, will not be emitted for this session).

### 3.1 Field-to-FHIR-element responsibilities

| Normalized field | Lands in FHIR as | Notes |
| :-- | :-- | :-- |
| `event_id` | Not directly mapped — `AuditEvent.id` is server-assigned on Bundle construction | `event_id` is retained as a correlation key in application logs |
| `timestamp` | `AuditEvent.recorded` | Required by R4 |
| `session_id` | `AuditEvent.entity[0].what.identifier.value` (base entity, every event) | See "Entity Slice" in the mapping doc |
| `actor_id` | `AuditEvent.agent[0].who.identifier.value` (AI agent slice) | |
| `execution_context.*` | Not emitted as FHIR elements directly — retained in the internal event log alongside the Bundle, since R4 has no native "pipeline version" concept | Candidate for a custom extension if downstream consumers need it in-band (§5) |
| `healthcare_governance.disclosure_timestamp` / `identity_assertion_text` | Milestone 2 `outcome`/`outcomeDesc`, `entity[1].description` | |
| `healthcare_governance.phi_accessed` | Milestone 4/5 `outcome`, `entity[1].description` ("PHI categories accessed: …") | |
| `healthcare_governance.escalation_timestamp` / `escalation_outcome` | Milestone 6 `outcome` | |
| `delegation.provider_npi` | `AuditEvent.agent[2].who.identifier` (`http://hl7.org/fhir/sid/us-npi` system) | Principal/on-behalf-of agent slice |
| `counterparty_type` | Not directly mapped to a standard FHIR element today — see §4 (AI vs. human participants) | Candidate extension |

## 4. Representing AI vs. human participants

FHIR R4's `AuditEvent.agent.type` is an extensible binding, which is exactly the hook NHID-Clinical uses (per the [mapping doc](fhir-auditevent-mapping.md)'s DICOM-coded agent slices) — but DICOM's role codes (`110153` Source Role ID, `110152` Destination Role ID) describe *transport roles*, not *humanness*. They don't, by themselves, say "the source role was filled by software, not a person."

**Current approach:** the AI/human distinction lives in the *behavioral* milestones, not the agent slice — `nhid-identity-disclosure`'s `identity_assertion_text` and the underlying `disclosure_timestamp` are the audit-trail proof that the calling party was AI, because that's the exact fact IDG-01 requires to be spoken and logged. `session.counterparty_type` (`human_operator` | `ai_agent` | `ivr_system` | `unknown`) captures the *other* party's nature for the bot-to-bot stricter-enforcement variant of IDG-01, but is not currently surfaced as a first-class FHIR element.

**Recommended extension (not yet implemented):** an `nhid-participant-kind` extension on `AuditEvent.agent`, bound to a small fixed code set (`human`, `ai-agent`, `ivr-system`, `unknown`), applied to *both* agent slices (the requestor and the destination), so a downstream FHIR consumer can answer "which side(s) of this call were automated?" without parsing `entity.description` free text. This is the single highest-value addition recommended in this document — see the [visuals and graph recommendations](visuals-and-graph-recommendations.md) memo for how this would feed a CAS distribution / bot-to-bot violation dashboard.

## 5. NHID extension profile concept (without claiming formal IG conformance)

NHID-Clinical can define its own **extension definitions** (`StructureDefinition` resources of kind `Extension`) anchored at `https://nhid-clinical.org/fhir/StructureDefinition/*` without that constituting, or being described as, conformance to a named Implementation Guide. This is the same posture the project already takes with its custom code systems (`nhid-subtype`, `agent-role` — see the mapping doc's "Code Systems" table): stable, self-hosted URIs, openly published, base-spec-valid, but explicitly *not* claiming IHE BALP or any other named IG's conformance requirements.

Candidate extensions for a future `nhid-fhir-extensions` profile bundle:

| Extension | Applies to | Carries |
| :-- | :-- | :-- |
| `nhid-participant-kind` | `AuditEvent.agent` | `human` \| `ai-agent` \| `ivr-system` \| `unknown` (§4) |
| `nhid-execution-context` | `AuditEvent` (top-level) | `pipeline_version`, `policy_engine_version`, `nhid_schema_version` — currently only in the internal log, not the FHIR Bundle |
| `nhid-cas-score` | `AuditEvent` (the `nhid-call-end` milestone instance) | The numeric CAS score and tier for the call, so the score travels with the audit bundle rather than requiring a separate API call to retrieve it |
| `nhid-delegation-chain-depth` | `AuditEvent.agent[2]` (principal slice) | Number of hops in the delegation chain that authorized this call (1–3), for payer-side risk scoring of deep chains |

These are proposals, not shipped behavior — none exist in `src/fhir_audit_emitter.py` today. Treat this table as the starting backlog for a `v1.1` extension profile, gated on real downstream-consumer demand rather than speculative completeness.

## 6. Versioning strategy for audit payloads

Three independent version numbers already exist in `execution_context` (`pipeline_version`, `policy_engine_version`, `nhid_schema_version`) — the discipline going forward should be:

- **`nhid_schema_version`** bumps on any change to the *shape* of the normalized event (§3) — adding/removing/renaming a field, changing a field's required-ness. Consumers parsing the normalized event (not the FHIR Bundle) key their parsing logic off this.
- **`policy_engine_version`** bumps on any change to *evaluation behavior* (new control, changed pass/fail condition, changed CAS formula) — this is what lets a payer explain "why did the same transcript score differently before and after this date."
- A new, **fourth** version field is recommended for the FHIR layer specifically: `nhid_fhir_profile_version`, carried as a `Meta.profile` canonical URL with a version suffix (e.g., `https://nhid-clinical.org/fhir/StructureDefinition/nhid-call-bundle|1.0`) on the emitted `Bundle`. This decouples "the policy engine changed" from "the FHIR mapping changed" — today a single `fhir_audit_emitter.py` change to, say, an outcome-coding table would have no dedicated version signal in the output Bundle itself. Not yet implemented; recommended for the next emitter revision.
- **Backward compatibility rule:** within a major `nhid_schema_version`, only add optional fields — never repurpose or remove a field a downstream consumer may already depend on. Breaking changes require a major version bump and a migration note in the changelog (same discipline the Master Knowledge Archive already applies to itself).

## 7. Separating transport/security evidence from clinical/workflow evidence

Keep two distinct evidence categories distinct, both in storage and in downstream analysis, even though both ultimately attach to the same `session_id`:

| Evidence category | Examples | Where it lives today |
| :-- | :-- | :-- |
| **Transport/security evidence** | OAuth2 token validation results, TLS/transport metadata, `AgentPassport` signature verification results, call-SID nonce checks | Outside the FHIR Bundle — these are infrastructure-layer facts, not clinical/workflow facts. See the [PKI/OAuth2 integration guide](nhid-auth-pki-and-oauth2-integration.md) §1.12 for what a payer should separately retain here. |
| **Clinical/workflow evidence** | Disclosure occurred, PHI categories accessed, escalation requested/honored, call outcome | The FHIR `AuditEvent` Bundle described in this document and the mapping doc |

Mixing these (e.g., embedding a raw OAuth bearer token or a full Ed25519 signature blob inside a FHIR `AuditEvent.entity.description` field) would bloat the clinical audit record with security material that has its own, different retention/access-control requirements (security evidence often needs *tighter* access restriction than the behavioral record, since it could itself be replayed or reused if leaked). Keep a foreign-key-style reference (`delegation_id`, already present per §3.1) connecting the two stores instead of inlining one into the other.

## 8. Preserving deterministic replayability

The policy engine guarantees identical output for identical input (Master Knowledge Archive §2.3: "no randomness, no LLM calls, no external I/O in the policy engine"). The FHIR emission layer must preserve this property to remain trustworthy as evidence:

- `fhir_audit_emitter.py` must be a **pure function** of the normalized event + the `PolicyDecision` — no wall-clock reads other than what's already in `event.timestamp`, no non-deterministic ID generation in a way that would change milestone *content* (random UUIDs for `AuditEvent.id` are fine; they're identifiers, not evaluated content).
- `replay_mode: "replay"` (one of the three allowed values alongside `"live"`/`"test"`) exists precisely so a stored event can be re-run through the emitter later — for audits, for regression testing the emitter itself after a code change, or for regenerating a Bundle under a new `nhid_fhir_profile_version` (§6) without re-running the original call.
- Any future extension (§5) must be derivable purely from fields already in the normalized event — an extension that required a fresh external lookup at emission time would break replayability for archived events.

## 9. Supporting machine validation, per-turn webhook evaluation, and long-term retention

The same normalized schema (§3) is designed to serve three different consumption patterns without three different schemas:

- **Machine validation:** the example Bundle (`examples/fhir/nhid-compliant-call-bundle.json`) is validated in CI against the official HL7 FHIR R4 validator (`.github/workflows/nhid-gates.yml`, `fhir_validation` job) — see the mapping doc's "Validation" section. Any schema change must keep this example passing.
- **Per-turn webhook evaluation:** `POST /v1/webhooks/call-progress` (Master Knowledge Archive §5.4) evaluates one normalized event per turn, statelessly, with the caller maintaining `session_state` across turns. FHIR emission for a still-in-progress call is necessarily partial — only the milestones reached so far exist — and downstream consumers polling for live status should treat an absent later milestone as "not yet reached," not as a failure.
- **Final call-bundle emission and long-term retention / SIEM ingestion:** once `nhid-call-end` fires, the Bundle is complete and becomes the durable artifact. This is the form intended for ingestion into a payer's SIEM or long-term compliance archive (see [`examples/fhir/README.md`](../examples/fhir/README.md) for the ingestion walkthrough) — at that point the Bundle should be treated as immutable; corrections require a new, linked Bundle (e.g., via `AuditEvent.entity` referencing the original `session_id`), not in-place edits to already-retained records.

---

*NHID-Clinical is a voluntary open proposal (CC BY 4.0). Not an accredited standard. Not a regulatory requirement. Validated against HL7 FHIR R4 base spec v4.0.1 only — no named Implementation Guide conformance is claimed. See [the Master Knowledge Archive](MASTER-KNOWLEDGE-ARCHIVE.md) for the authoritative source of all technical claims in this document.*
