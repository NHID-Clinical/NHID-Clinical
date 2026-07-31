# NHID-Clinical Vendor Trust Questionnaire

**Version:** 1.0 · **Spec baseline:** NHID-Clinical v1.3 + NHID-Auth v2 · **Status:** Reference procurement tool, not a certification

> NHID-Clinical is a voluntary, open behavioral baseline for AI voice agents in B2B healthcare
> payer–provider calls. It is **not an accredited standard, not a certification program, and not
> a regulatory requirement.** This questionnaire is a procurement and trust-assessment aid for
> parties evaluating an AI voice vendor — it has no enforcement mechanism of its own. CC BY 4.0.

## How to use this document

This questionnaire is meant to be **placed in front of** the [technical specification](nhid-clinical-technical-specification.md) when sharing NHID-Clinical with a counterparty. Send it to a vendor, have them complete it, and use the answers — together with a live conformance run against the vendor's actual call traffic (`POST /v1/demo/check` or a vendor-specific adapter route) — to form a trust judgment. It is written for four audiences:

- **Healthcare payers** screening inbound AI voice traffic from provider-side vendors.
- **Providers** selecting or auditing the AI voice platform calling on their behalf.
- **Compliance officers** who need a defensible, repeatable record of what was asked and answered.
- **AI voice vendors** who want to get ahead of these questions before a payer or provider asks them.
- **Shadow-pilot participants** deciding whether to onboard a vendor into a 90-day observation pilot (see `roadmap.html` / `for-payers.html`).

Each section lists the question, why it matters, and what a credible answer looks like at each of the three integration tiers (Tier 0 — behavioral check only, Tier 1 — continuous monitoring, Tier 2 — cryptographic identity). A vendor answering "not applicable" or "not yet implemented" to a Tier 2 question is not automatically disqualified — NHID-Clinical v1.3 alone does not require cryptographic identity. Treat Tier 2 gaps as a roadmap conversation, not a hard fail. Treat Tier 0 gaps (disclosure, PHI gating, escalation) as a hard fail.

---

## 1. Product scope and intended workflows

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 1.1 | What B2B healthcare administrative workflows does your AI voice agent perform (eligibility verification, claim status, prior authorization, other)? | NHID-Clinical's behavioral baseline is scoped to provider-to-payer administrative calls — not patient-facing calls, not clinical decision support. Confirms the engagement is in scope. | A specific, bounded list. A vendor claiming "anything a human rep can do" without a workflow list is a red flag. |
| 1.2 | Does the agent ever call patients directly, or only payer/provider administrative lines? | Patient-facing calls carry different consent and disclosure obligations outside this baseline's scope. | Clear separation of B2B administrative calling from any patient-facing product line. |
| 1.3 | What percentage of your current call volume is fully autonomous vs. human-supervised? | Establishes blast radius if a control fails. | A real number, with a description of supervision (live barge-in, post-call review, none). |
| 1.4 | Who is the calling party of record — the vendor, or the provider the vendor represents? | Sets up the NPI-binding and delegation questions in Section 6. | "We call on behalf of [provider], identified by NPI [or: we are the provider, calling directly]." |

## 2. Identity disclosure controls (maps to IDG-01)

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 2.1 | Does the agent state that it is an automated system before any operational data is requested or exchanged? | This is IDG-01, the first and most load-bearing control. | "Yes, on every call, before any data request" with a sample disclosure script. |
| 2.2 | At what point in the call (turn number / elapsed seconds) does disclosure happen, on average and at worst case? | NHID-Clinical measures this directly as **Impersonation Latency** — `IL = t(disclosure) − t(connect)`, target `IL(turns) = 0`. | A measured number, not "immediately" with no data behind it. Ideally turn 0. |
| 2.3 | What happens if the disclosure step is skipped due to a bug or vendor outage — does the call proceed, or does it fail closed? | Determines whether disclosure is enforced structurally or is just a script line that can silently fail. | Fail-closed: no data exchange proceeds if the disclosure step did not execute and log. |
| 2.4 | Can you provide a sample call transcript showing the disclosure moment? | Verifiable evidence beats a policy statement. | An actual transcript excerpt, or a live demo call. |

## 3. PHI / operational-data gating (maps to PDX-01)

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 3.1 | What categories of data does the agent request or access (member ID, NPI, date of birth, claim number, prior-auth number, diagnosis/procedure code, group number, tax ID)? | Defines the PHI surface that must be gated behind disclosure. | An explicit list matching the categories actually exchanged. |
| 3.2 | Is there a structural gate that prevents any of those fields from being requested before disclosure is confirmed, or is ordering left to the conversation script? | A script convention ("we always say X before Y") is weaker than an engine-level gate that blocks the action. | A described or demonstrable gate, ideally enforced in code/policy engine rather than prompt instruction alone. |
| 3.3 | What happens on the rare turn where a human caller volunteers PHI before the agent has disclosed? | Tests the gate against real-world conversational disorder, not just the scripted happy path. | A defined fallback (e.g., agent disregards/does not act on the data and proceeds to disclose first). |

## 4. Deceptive behavior safeguards (maps to DBC-01)

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 4.1 | Does the voice agent use synthetic breathing, hesitation sounds, filler words, or other artifacts designed to imply human presence? | This is the deceptive-behavior control. Some commercial TTS stacks add these by default for "naturalism." | "No" with a description of the TTS configuration, or a documented opt-out from vendor defaults. |
| 4.2 | Will the agent ever explicitly claim to be a human or a "real person" if asked directly? | Direct deception is a hard fail regardless of voice naturalism settings. | "Never — the agent is instructed to acknowledge automation if asked, even mid-call." |
| 4.3 | Do you run or can you run a text-heuristic check against transcripts for impersonation phrases ("I am a human", "you're speaking with a live agent", etc.)? | A concrete, automatable test a vendor can run today against their own logs. | Willingness to run `nhid_policy_engine_v1.evaluate_all` (or equivalent) against a transcript sample. |

## 5. Escalation and human handoff (maps to EIT-01)

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 5.1 | When a caller asks for a human, does the agent honor it immediately, or attempt to retain the caller first? | EIT-01 requires the escalation path to be both communicated and honored on request. | Immediate honor, with a defined maximum number of retention attempts (ideally zero) before transfer/handoff. |
| 5.2 | What happens if no live human transfer destination exists for a given workflow (e.g., a demo, after-hours, or unstaffed line)? | A transfer to nowhere is worse than no transfer attempt — it strands the caller in dead air. | A graceful decline-and-explain-then-end flow (acknowledge, state the alternative contact path, end the call cleanly) rather than invoking a transfer tool with no destination. |
| 5.3 | Is the escalation outcome (connected / unavailable / timeout) logged per call? | Feeds directly into ATR-01 and the FHIR `nhid-escalation` audit milestone. | Yes, with the outcome value retained alongside the call record. |

## 6. Key management and cryptographic identity (NHID-Auth v2, optional — Tier 2)

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 6.1 | Does each AI agent instance have its own keypair, or is a single key shared across all calls/customers? | Shared keys remove the ability to revoke or attribute a single compromised agent without affecting all traffic. | Per-agent (or per-tenant-minimum) keypairs. Ed25519 if following the NHID-Auth v2 reference. |
| 6.2 | Who generates and holds the agent's private key — the vendor platform, or the provider? | Determines the delegation pattern (see the PKI guide, §"Deployment patterns"). | A clear statement of which of the three deployment patterns applies: provider-managed, vendor-managed with provider-signed delegation, or multi-hop sub-vendor chain. |
| 6.3 | Is the provider's NPI cryptographically bound into the delegation, or only referenced informally (e.g., in a free-text field)? | NPI binding is what makes a delegation auditable and disputable later — see PKI guide §"Binding keys to provider identity." | NPI present as a structured, signed field inside the delegation object, validated against the 10-digit NPPES format. |
| 6.4 | How are agent keys rotated, and what is the rotation window? | Stale keys with no rotation policy are a standing compromise risk. | A defined rotation interval (days/weeks) and a described re-delegation process that doesn't require a new provider trust decision each time. |
| 6.5 | If your platform serves multiple provider customers, are keys isolated per customer/provider org, or shared across your tenant base? | Multi-tenant key sharing means one breached customer can impersonate another customer's agents. | Per-tenant key isolation, ideally with per-tenant signing material in KMS/HSM. |

## 7. Call binding and replay protection (Tier 2)

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 7.1 | Is a cryptographic credential bound to a specific call (e.g., via call-SID nonce), or can the same signed credential be replayed across multiple calls? | Without call binding, a captured credential is reusable indefinitely. | Call-SID (or equivalent) nonce binding, with `ERR_NONCE_MISMATCH`-style rejection on mismatch. |
| 7.2 | What is the credential's time-to-live, and is it short enough to bound the blast radius of a leak? | A long-lived, call-unbound credential is functionally a permanent bearer token. | A bounded TTL (typically call-duration-scale, not days). |
| 7.3 | If you also use OAuth2/OIDC for API transport, how do you avoid a long-lived bearer token substituting for call-specific authorization? | OAuth2 access tokens alone don't express "this specific agent is authorized for this specific call on this specific provider's behalf" — see the OAuth2/OIDC integration guide. | A description matching one of the two reference integration tiers in that guide (OAuth2-for-transport-only vs. full Tier 2 overlay). |

## 8. Audit and evidence quality (maps to ATR-01)

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 8.1 | Do you retain a structured, timestamped record of disclosure, PHI access, and escalation events per call? | This is the minimum ATR-01 field set: `event_id`, `timestamp`, `actor_id`, `state_before`/`state_after`, plus `execution_context`. | A described schema or willingness to map to the [FHIR AuditEvent standardization guide](fhir-auditevent-standardization-for-ai-agents.md). |
| 8.2 | Can that record be exported in a healthcare-native audit format (FHIR R4 `AuditEvent`)? | Lets a payer ingest the evidence into their own compliance/SIEM tooling instead of trusting vendor-side self-attestation. | Yes, or a credible roadmap commitment with a date. |
| 8.3 | Is the audit record tamper-evident (e.g., append-only, hash-chained, or stored in a system the calling agent cannot itself rewrite)? | Self-reported, mutable logs are weak evidence in a dispute. | A described tamper-evidence mechanism, even a simple one (separate write-only store, vendor cannot edit after write). |

## 9. Incident response and revocation

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 9.1 | If a single agent's behavior is found non-conformant (e.g., fails IDG-01 repeatedly), can you disable that agent without taking down all traffic? | Tests granularity of control — see Delegation Chain Rules in the PKI guide. | Per-agent and per-delegation revocation, independent of other agents. |
| 9.2 | How quickly does a revocation take effect once issued? | A revocation that takes hours to propagate is not an incident-response control. | Real-time or near-real-time (revocation checked on every call, not cached for long periods). |
| 9.3 | What is your process for notifying a payer/provider counterparty of a confirmed disclosure or PHI-gating failure? | Tests whether the vendor treats this as an operational incident requiring disclosure, vs. something to quietly patch. | A defined notification SLA and contact path. |

## 10. Testing, determinism, and deployment assurances

| # | Question | Why it matters | Credible answer |
| :-- | :-- | :-- | :-- |
| 10.1 | Will you allow a counterparty to run a conformance check against a sample of your real call transcripts (e.g., via `POST /v1/demo/check` or a vendor-specific adapter route)? | This is the cheapest, fastest verification available — no contracts, no code changes. | Yes, with a sample within 1–2 business days. |
| 10.2 | Is your disclosure/escalation/audit behavior deterministic given the same inputs, or can it vary run to run (e.g., due to an LLM making the disclosure decision live)? | NHID-Clinical's own policy engine is deterministic by design (no randomness, no LLM, no external I/O in the evaluation path). A vendor whose *compliance* behavior is itself non-deterministic is harder to certify against. | A description of how disclosure/escalation are enforced — ideally a structural gate or scripted requirement, not solely an LLM's in-context judgment that could vary. |
| 10.3 | What happens during a partial outage of your platform (e.g., TTS provider down, transfer line down) — does the call fail safe (disclose and end) or fail open (continue without disclosure/escalation)? | Establishes behavior under degraded conditions, which is when controls are most likely to be skipped. | Documented fail-safe behavior. |

---

## Scoring guidance (informal — not a certification score)

This questionnaire does not produce a CAS (Call Authorization Score) by itself — CAS is computed
per-call from actual transcript/event data by the policy engine, not from questionnaire answers.
Use the questionnaire to triage:

- **Hard fail / do not proceed:** "No" or evasive answers to Sections 2, 3, or 5 (disclosure, PHI gating, escalation). These are the load-bearing behavioral controls.
- **Proceed with monitoring:** Solid Tier 0/1 answers, weak or "not yet" Tier 2 answers. Reasonable starting point for a shadow pilot (see `roadmap.html`).
- **Strong candidate:** Solid answers across all ten sections, willingness to run a live conformance check immediately.

Next step after completing this questionnaire: see the [technical specification](nhid-clinical-technical-specification.md) for the underlying control definitions, and the [PKI and OAuth2/OIDC integration guide](nhid-auth-pki-and-oauth2-integration.md) if Tier 2 cryptographic identity is in scope for this engagement.
