# NHID-Clinical Technical Specification

**Version:** 1.0 (draft) · **Spec baseline:** NHID-Clinical v1.3 + NHID-Auth v2 · **Date:** 2026-06-21
**Author:** Brianna Nicole Baynard-Malone · **License:** CC BY 4.0
**Source of truth:** [`docs/MASTER-KNOWLEDGE-ARCHIVE.md`](MASTER-KNOWLEDGE-ARCHIVE.md) and the codebase. Where this document and the archive disagree, the archive/code wins; report the discrepancy.

> NHID-Clinical is a voluntary, open behavioral baseline for AI voice agents in B2B healthcare
> payer–provider calls, with an open cryptographic authorization layer (NHID-Auth v2) as a
> reference implementation. **It is not an accredited standard, not a certification program, and
> not a regulatory requirement.** It may align with regulatory direction (NIST AI RMF, ISO/IEC
> 42001) but does not satisfy any regulation by itself. It is published CC BY 4.0 and was
> submitted as a public comment to NIST (docket NIST-2025-0035, comment ID NIST-2025-0035-0026).

---

## Before you read this document: complete the vendor trust questionnaire

If you are a payer, provider, compliance officer, AI voice vendor, or shadow-pilot candidate
evaluating whether to adopt or integrate against NHID-Clinical, start with the
**[Vendor Trust Questionnaire](vendor-trust-questionnaire.md)** before reading further. It is a
structured procurement/trust-assessment tool covering product scope, identity disclosure,
PHI gating, deceptive-behavior safeguards, escalation, key management, call binding, audit
quality, incident response, and testing/determinism — the practical questions this specification
exists to let you answer with evidence rather than a vendor's word.

---

## Table of contents

1. [Scope and positioning](#1-scope-and-positioning)
2. [Behavioral controls](#2-behavioral-controls)
3. [ATR-01 audit structure](#3-atr-01-audit-structure)
4. [CTS and determinism](#4-cts-and-determinism)
5. [CAS summary](#5-cas-summary)
6. [Policy engine action model](#6-policy-engine-action-model)
7. [Cryptographic authorization model (NHID-Auth v2)](#7-cryptographic-authorization-model-nhid-auth-v2)
8. [Delegation chain rules](#8-delegation-chain-rules)
9. [Call binding](#9-call-binding)
10. [Revocation](#10-revocation)
11. [Payer-side verification](#11-payer-side-verification)
12. [Adapter responsibilities](#12-adapter-responsibilities)
13. [FHIR audit trail mapping](#13-fhir-audit-trail-mapping)
14. [Production roadmap gaps](#14-production-roadmap-gaps)

---

## 1. Scope and positioning

NHID-Clinical addresses **Impersonation Latency**: the duration of time an AI voice agent
operates and exchanges operational/PHI data in a B2B healthcare administrative call (eligibility
verification, claim status, prior authorization, and similar workflows) before disclosing that it
is automated. The canonical failure mode observed in production payer call centers: an AI agent
requests a member ID, NPI, or date of birth within the first turns of a call with no prior
disclosure; staff exchange the data and only later — or never — learn the caller was automated.

**In scope:** B2B administrative voice calls between providers (or their AI vendors, calling on
their behalf) and payers.

**Out of scope:** patient-facing calls, internal tooling, clinical decision support, and any
claim that this specification by itself satisfies a named regulatory framework or HL7
Implementation Guide. NHID-Clinical validates FHIR output against the **HL7 FHIR R4 base
specification (v4.0.1) only** — it does not claim conformance to a named IG such as IHE BALP.

**Positioning relative to the five-layer trust stack** (Master Knowledge Archive §3.1):

1. Carrier authentication (STIR/SHAKEN) — outside this spec's scope, assumed pre-existing.
2. **Behavioral disclosure (NHID-Clinical v1.3)** — §2 of this document.
3. **Cryptographic identity (NHID-Auth v2)** — §7–§11 of this document.
4. **Healthcare-native audit trails (FHIR R4 AuditEvent)** — §13 of this document.
5. Enterprise observability (OpenTelemetry) — future work, not in the current reference implementation.

## 2. Behavioral controls

NHID-Clinical v1.3 defines four deterministic behavioral controls plus one supplemental
structural requirement (ATR-01, §3). Full pass/fail conditions, detection keyword lists, and
bot-to-bot variants are documented in the Master Knowledge Archive §2.1 — summarized here:

| ID | Name | Requirement | Severity on failure |
| :-- | :-- | :-- | :-- |
| **IDG-01** | Identity Disclosure Gate | AI agent must identify itself as automated before any data is requested or exchanged | CRITICAL |
| **PDX-01** | Pre-Data Exchange Gate | No PHI/operational data field (`member_id`, `npi`, `date_of_birth`, `claim_number`, `prior_auth_number`, `diagnosis_code`, `procedure_code`, `provider_tin`, `group_number`) may be exchanged until IDG-01 disclosure is confirmed | CRITICAL |
| **DBC-01** | Deceptive Behavior Check | No synthetic voice artifacts (breathing, hesitation, laughter) implying human presence (Tier A, CRITICAL); no explicit human-status claims via text heuristic (Tier B, MAJOR, non-blocking) | CRITICAL (Tier A) / MAJOR, LOG_ONLY (Tier B) |
| **EIT-01** | Escalation Implementation Test | A human escalation path must be communicated and, when requested, honored | CRITICAL |

Note the canonical control names: **PDX-01 is "Pre-Data Exchange Gate,"** not "PHI Data Exchange
Gate" — and **EIT-01 is "Escalation Implementation Test,"** not "Escalation & Intervention." Both
corrections are recorded in the Master Knowledge Archive changelog (v1.1) with their source-code
citations; older PDF artifacts predating that fix may still show the old names — see the
[PDF consistency review](pdf-consistency-and-grammar-review.md).

**Impersonation Latency, formally** (Master Knowledge Archive §2.4.1):

```
IL = t(disclosure) − t(connect)               (time form)
IL(turns) = turns completed before first valid disclosure   (turn form, target = 0)
```

Both anchors are required ATR-01 event fields, so IL is computable from any conformant audit
trail with no human judgment involved — this determinism is what makes IL usable as a
machine-scored metric rather than a subjective call-quality impression.

## 3. ATR-01 audit structure

ATR-01 (Audit Trail Requirements) is enforced structurally rather than behaviorally: every NHID
event must carry a fixed set of top-level fields plus a nested `execution_context` block.
Missing or null fields are a CRITICAL ATR-01 violation regardless of how the other four controls
score.

**Required top-level fields:** `event_id`, `timestamp`, `session_id`, `request_id`, `event_type`,
`actor_id`, `state_before`, `state_after`, `replay_mode`, `external_calls_cached`,
`execution_context`.

**Required `execution_context` sub-fields:** `pipeline_version`, `policy_engine_version`,
`nhid_schema_version`.

The full normalized event schema, its FHIR mapping, lifecycle milestones, extension points, and
versioning strategy are covered in depth in
[fhir-auditevent-standardization-for-ai-agents.md](fhir-auditevent-standardization-for-ai-agents.md);
the field-by-field `AuditEvent` mapping table is in
[fhir-auditevent-mapping.md](fhir-auditevent-mapping.md).

## 4. CTS and determinism

The Conformance Test Suite (CTS) contains 18 YAML test cases — 16 evaluated at the policy-engine
layer, 2 HTTP-infrastructure edge cases skipped in unit context — mapping to the five controls
(identity disclosure, PHI gate, deceptive behavior, escalation, audit trail). The current Python
test suite passes **284 tests (18 skipped — integration tests requiring a live server)**; combined
with the TypeScript middleware suite (66 tests), the project's total passing count is **350**.
Older PDF artifacts referencing 191 or 95 passing tests, or only 2 adapters, predate the adapter
expansion (Vonage, Retell AI, Amazon Connect added) documented in the Master Knowledge Archive
changelog and §7 (Implementation Roadmap) — see the
[PDF consistency review](pdf-consistency-and-grammar-review.md) for the specific stale references found.

**Determinism guarantee:** the policy engine produces identical output for identical input on
every run — no randomness, no LLM calls, no external I/O inside `evaluate_all()`. This is what
lets CAS and IL function as reproducible, auditable, dispute-resolvable scores rather than
one-off judgments. Vendors whose own *compliance behavior* depends on a live LLM's in-context
judgment (rather than a structural gate) are weaker integration candidates for this reason — see
[vendor trust questionnaire](vendor-trust-questionnaire.md) §10.2.

## 5. CAS summary

The Call Authorization Score (CAS) — not "Compliance/Conformance Assurance Score," a name fixed
in the Master Knowledge Archive changelog — is a continuous 0.0–1.0 compliance signal per call:

```
CAS = F_IAF × F_NOCF × ECF
```

| Factor | Definition | Range |
| :-- | :-- | :-- |
| F_IAF | Identity Assurance Factor — 1.0 unless an IDG-01/PDX-01 critical violation occurred, else 0.0 | {0.0, 1.0} |
| F_NOCF | Operational Conformance Factor (see formula below) | 0.0–1.0 |
| ECF | Evidence Completeness Factor — fraction of required ATR-01 fields present | 0.0–1.0 |

**NOCF formula** (`src/nhid_cas.py`):

```
C (coherence)  = (entity_match_rate + intent_accuracy + domain_hit_rate) / 3
E (execution)  = successful_actions / attempted_actions
S (stability)  = 1 − (call_drop_rate + audio_corruption_rate + tool_failure_rate) / 3
L_hat          = max(0, 1 − latency_ms / l_max_ms)
R (risk)       = w_H × hallucination_risk + w_P × pii_leakage_risk + w_I × identity_ambiguity_risk
A_nocf         = C × E × S × L_hat × (1 − R)
```

Weights `w_H=0.40, w_P=0.35, w_I=0.25` apply **only** inside `R`; `l_max_ms` defaults to 2500ms
(floor 1500ms, ceiling 5000ms). The weights-spread-across-C/E/S variant, or a formula using `R`
as a direct multiplier instead of `(1 − R)`, is the old, incorrect version — flagged where found
in the PDF review.

**Tier ladder:** ≥0.90 Verified Trust (L2) · ≥0.75 Conditional Trust (L1) · ≥0.50 Review Required
· ≥0.20 Denied/Degraded · <0.20 Hard Denial. See the
[CAS distribution visual recommendation](visuals-and-graph-recommendations.md#5-cas-distribution-visual)
for how to render this against real call volume once available.

## 6. Policy engine action model

`evaluate_all(session, event)` runs all rule evaluators in sequence, collects violations, and
returns the single highest-priority action:

| Priority | Action | Trigger |
| :-- | :-- | :-- |
| 5 | `DENY_DATA` | IDG-01 or PDX-01 critical violation |
| 4 | `ESCALATE_HUMAN` | EIT-01: escalation requested, path available |
| 3 | `DISCLOSE_IDENTITY` | IDG-01: no prior disclosure detected |
| 2 | `LOG_ONLY` | DBC-01 text heuristic (non-blocking), ATR-01 minor gap |
| 1 | `CONTINUE_AI` | All controls pass |

This priority order is what makes the engine's output deterministic even when multiple rules
fire on the same turn — there is never an ambiguous "which violation matters more" judgment call
left to the caller.

## 7. Cryptographic authorization model (NHID-Auth v2)

NHID-Auth v2 is the reference cryptographic authorization layer (`src/agent_identity.py`),
providing provider-signed agent credentials with NPI binding, scoped delegation chains, per-agent
and per-delegation revocation, and call-SID nonce binding. **Algorithm: Ed25519** — 32-byte keys,
64-byte signatures, chosen for small key size, fast verification, and side-channel resistance
relative to RSA.

**Core data structures:**

```python
@dataclass
class Delegation:
    provider_npi: str          # 10-digit NPI, regex ^\d{10}$
    agent_id: str
    agent_public_key_b64: str
    scope: list[str]           # e.g., ["claims_inquiry", "eligibility_check"]
    expires_at: str            # ISO 8601 UTC
    created_at: str
    delegation_id: str         # UUID v4
    call_sid: str              # binds this credential to a specific call
    nonce: str

@dataclass
class AgentPassport:
    delegation: Delegation
    signature_b64: str         # provider's signature over the delegation
    agent_signature_b64: str   # agent's co-signature (proves key control)

@dataclass
class VerificationResult:
    valid: bool
    reason: str
    delegation_id: str | None
    provider_npi: str | None
    agent_id: str | None
    scope: list[str]
```

The full PKI architecture — trust anchors, who issues keys, multi-tenant key isolation, sub-vendor
chains, JWKS vs. registry-based discovery, rotation, HSM/KMS operational security, and the
migration path to production-grade infrastructure — is covered in depth in
[nhid-auth-pki-and-oauth2-integration.md](nhid-auth-pki-and-oauth2-integration.md) Part 1.

How NHID-Auth coexists with an organization's existing OAuth2/OIDC stack (Auth0, Okta, Entra ID,
Cognito, custom providers) — including scope mapping, JWT claim representation, and replay
prevention when a bearer token spans multiple calls — is covered in the same document, Part 2.

## 8. Delegation chain rules

1. **Maximum 3 hops.** Provider → Vendor → Sub-vendor → Agent is the maximum depth; longer chains
   return `ERR_CHAIN_TOO_LONG`.
2. **Monotonic scope narrowing.** Each hop may only reduce scope, never expand it;
   `ERR_CHAIN_NARROWING` on violation.
3. **NPI anchoring.** Every chain starts with a real 10-digit NPI, validated against NPPES format.
4. **Call-SID nonce binding.** Credentials bound to a specific call; presenting on a different
   call returns `ERR_NONCE_MISMATCH`.
5. **Revocation is permanent.** Reference implementation stores revocation in-memory; production
   requires a persistent store (§10, §14).

Full deployment-pattern guidance (provider-managed keys, vendor-managed agent keys with
provider-signed delegation, multi-hop sub-vendor chains, future registry-based discovery) is in
[nhid-auth-pki-and-oauth2-integration.md](nhid-auth-pki-and-oauth2-integration.md) §1.5–1.6.

## 9. Call binding

Call binding is the mechanism that prevents a captured, still-valid credential from being
replayed on a different call: every `Delegation` carries a `call_sid` and `nonce`, and
`verify_passport` rejects a mismatch with `ERR_NONCE_MISMATCH`. This is also the structural answer
to "why OAuth2 bearer tokens alone don't solve cross-org call authorization" — OAuth2 was not
designed to express per-call scoping, and a delegation's call-SID binding is what closes that gap
(see [PKI/OAuth2 guide](nhid-auth-pki-and-oauth2-integration.md) §2.9).

## 10. Revocation

`revoke_agent(agent_id)` and `revoke_delegation(delegation_id)` are permanent — once revoked, a
credential cannot be reinstated. **The reference implementation stores revocation state
in-memory**, meaning it does not survive a process restart; this is an explicit reference/demo
limitation. Production deployments require a persistent, synchronously-checked revocation store
(DynamoDB or equivalent) — see [PKI/OAuth2 guide](nhid-auth-pki-and-oauth2-integration.md) §1.9
and §14 below.

## 11. Payer-side verification

`verify_passport(passport, provider_pub, call_sid, required_scope?)` is the single payer-side
entry point: it checks the provider signature over the delegation, the agent co-signature, the
expiry, the call-SID binding, and revocation status, returning a `VerificationResult` carrying the
verified `provider_npi`, `agent_id`, `delegation_id`, and `scope` on success, or a `reason` string
(one of the `ERR_*` codes) on failure. `validate_chain(passports, prov_pub)` extends this to
multi-hop chains.

| Code | Meaning |
| :-- | :-- |
| `ERR_EXPIRED` | Delegation TTL elapsed |
| `ERR_REVOKED` | Agent or delegation explicitly revoked |
| `ERR_INVALID_SIG` | Signature verification failed |
| `ERR_NONCE_MISMATCH` | `call_sid` doesn't match credential binding |
| `ERR_SCOPE_VIOLATION` | Requested scope not in delegation |
| `ERR_INVALID_NPI` | NPI fails 10-digit format validation |
| `ERR_CHAIN_NARROWING` | Chain hop attempts to expand scope |
| `ERR_CHAIN_TOO_LONG` | Delegation chain exceeds 3 hops |

A payer that verifies the passport but does **not** independently confirm the NPI is a real,
active NPPES registration has only proven the *delegation* is authentic — not that the NPI itself
is legitimate. NHID-Auth deliberately leaves that second check to the payer's existing
provider-enrollment system (see [PKI/OAuth2 guide](nhid-auth-pki-and-oauth2-integration.md) §1.13).
What a payer should retain to resolve a later dispute is enumerated in the same guide, §1.12.

## 12. Adapter responsibilities

Every vendor adapter (`adapters/vapi_adapter.py`, `twilio_adapter.py`, `vonage_adapter.py`,
`retell_adapter.py`, `amazon_connect_adapter.py`, plus the turn-by-turn
`call_progress_adapter.py`) implements the same contract:

```
Vendor payload → to_nhid_event(payload) → (session_dict, event_dict)
                → evaluate_all(session, event) → PolicyDecision
                → _decision_to_dict(decision, event) → JSON response
```

Every adapter must independently set the ATR-01-required fields (`actor_id`, `replay_mode`,
`external_calls_cached`) from its vendor's native payload shape — there is no shared default;
omitting one is itself an ATR-01 violation regardless of how faithfully the adapter translates
the rest of the call. Disclosure/data-request keyword detection
(`DISCLOSURE_KEYWORDS`, `DATA_REQUEST_KEYWORDS`) is shared logic across adapters, applied to each
vendor's transcript text field after normalization. Latency target: under 200ms per turn
end-to-end (policy evaluation ~50ms, adapter conversion ~20ms).

## 13. FHIR audit trail mapping

Every CTS execution (and every live call, once instrumented) produces a FHIR R4 `Bundle`
containing one `AuditEvent` per lifecycle milestone — session start, identity disclosure,
auth verification, PHI gate decision, PHI exchange start, escalation/transfer, call termination.
The complete element-by-element mapping (agent slices, outcome coding tables, code systems, CI
validation process) is in [fhir-auditevent-mapping.md](fhir-auditevent-mapping.md); the broader
normalization layer — canonical event schema, AI-vs-human participant representation, extension
profile concept, versioning strategy, and the transport/security-vs-clinical/workflow evidence
separation — is in
[fhir-auditevent-standardization-for-ai-agents.md](fhir-auditevent-standardization-for-ai-agents.md).

**Conformance claim, restated for emphasis:** validated against HL7 FHIR R4 base specification
v4.0.1 only, via the official HL7 validator in CI. No named Implementation Guide conformance
(e.g., IHE BALP) is claimed.

## 14. Production roadmap gaps

The reference implementation is deliberately minimal in a few places that production deployments
must address before relying on this as live infrastructure rather than a demonstrated proposal:

| Gap | Current state | Production requirement |
| :-- | :-- | :-- |
| Revocation persistence | In-memory, lost on restart | Durable, synchronously-checked store (§10) |
| Key custody | Demo keypairs generated in-process | KMS/HSM-backed signing, per-tenant isolation (PKI guide §1.4–1.5, §1.11) |
| Public key distribution | Static/manual exchange only | JWKS endpoints, eventually registry-backed discovery (PKI guide §1.8, §1.14) |
| FHIR extension profile | Conceptual only — no extensions shipped | `nhid-participant-kind`, `nhid-execution-context`, `nhid-cas-score`, `nhid-delegation-chain-depth` (FHIR standardization doc §5) |
| FHIR Bundle versioning | Only internal `execution_context` versions exist | Add `nhid_fhir_profile_version` via `Meta.profile` (FHIR standardization doc §6) |
| Enterprise observability layer | Not implemented | OpenTelemetry integration (five-layer trust stack, layer 5) |
| STIR/SHAKEN integration | Not implemented | Planned v2.1 (Master Knowledge Archive §3.2) |
| Attestation registry | Not implemented | Planned v2.1; depends on a registry operator existing (PKI guide §1.14) |
| Real pilot data | None — "no organizations have adopted or piloted it yet" | 90-day shadow pilot program (`roadmap.html`, `pilot.html`) |

None of these gaps block using NHID-Clinical's **behavioral** controls (§2) today — IDG-01/PDX-01/
DBC-01/EIT-01/ATR-01 evaluation has no dependency on the cryptographic layer. They specifically
gate moving from Tier 0/1 (behavioral monitoring, no keys) to a production-grade Tier 2
(cryptographic identity) deployment. See the [staged integration guide](v2-integration-guide.md)
for the tier ladder this maps to.

---

*NHID-Clinical is a voluntary open proposal (CC BY 4.0). Not an accredited standard. Not a
regulatory requirement. Submitted as NIST public comment NIST-2025-0035-0026. See
[the Master Knowledge Archive](MASTER-KNOWLEDGE-ARCHIVE.md) for the authoritative source of all
technical claims in this document.*
