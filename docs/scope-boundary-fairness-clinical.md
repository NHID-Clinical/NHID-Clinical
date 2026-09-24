# NHID-Clinical Scope Boundary: Fairness and Clinical Governance

**Status:** scope statement · **Added:** 2026-07-08 · CC BY 4.0

NHID-Clinical addresses **identity disclosure, delegated authorization, escalation, and
auditability** for non-human actors in B2B healthcare voice workflows. It does **not**
evaluate or govern:

- Model fairness or bias
- Clinical safety or validity of outputs
- Patient outcome equity
- Harm or adverse-event surveillance
- Algorithmic transparency beyond identity and authorization

These areas are intentionally out of scope. NHID-Clinical assumes that organizations
already have (or will establish) separate processes for clinical validation, fairness
auditing, and broader AI risk management.

## Dependency declaration: automatic speech recognition

A scope exclusion is incomplete without saying what the excluded thing is still needed
for. This is that statement.

**NHID-Clinical evaluates transcript and event data. It does not perform speech
recognition, and it does not establish the accuracy of the transcription path that feeds
it.** The policy engine reads text: IDG-01 matches disclosure and persona phrases against
`identity_assertion_text`, PDX-01 detects protected-data requests in `speech_text`, and
EIT-01 detects an escalation request in what the **human** recipient said. All three are
downstream of an ASR system this framework neither supplies nor measures.

The consequences are concrete, and deployments must plan for them:

- A disclosure that was spoken but mis-transcribed is recorded as a **missing disclosure
  that did not happen**.
- An escalation request that was spoken but mis-transcribed produces **no escalation
  finding**, and the audit record then attests to a compliant interaction. This is the
  failure mode the evidence cannot reveal on its own.
- Word error rates are not uniform across speakers. Published measurements report
  materially higher error rates for some speaker groups than others, and error in
  conversational, multi-speaker audio is substantially worse than in dictation. Whatever
  that distribution is in a given deployment, NHID-Clinical's findings inherit it.

**Therefore:** every conformance figure produced by this framework is valid only to the
precision of the transcription path beneath it. The event schema carries an optional
`transcription_attestation` for exactly this reason, with three honest states —
`measured`, `attested` and `unattested`. Where it is absent or `unattested`, a report
must say so rather than imply a precision it cannot support.

Assuring ASR quality, including across speaker groups, is the deploying organization's
responsibility. NHID-Clinical's contribution is to make the dependency explicit and to
carry the attestation alongside the finding.

## Integration approach (not expansion)

NHID-Clinical is designed to work *underneath* fairness and clinical governance programs,
not replace them:

- **Stratification is not implemented.** An earlier version of this note said
  Impersonation Latency "can be stratified by workflow or population segment when a
  separate fairness program requires it." That described an intention, not a capability:
  nothing in `src/`, `schema/`, `tests/` or `scripts/` performs stratification, and no
  protected-attribute or segment input exists. What the schema now carries is an optional
  `language` and `interpreter_present` pair on the event — enough for a deploying
  organization to stratify **its own** reporting, and nothing more. NHID-Clinical does not
  compute, store or report a subgroup comparison.
- Organizations should pair NHID-Clinical with their chosen fairness and clinical
  governance frameworks (e.g. NIST AI RMF, internal review boards, or vendor fairness
  programs). NHID-Clinical provides the identity and audit foundation; it does not perform
  the fairness or clinical analysis.
- **Linkage fields (recommended convention, not implemented):** organizations that want to
  tie NHID audit events to external reviews can carry identifiers such as
  `fairness_review_id` or `clinical_validation_profile` as pass-through metadata alongside
  their event pipeline. Adding these as first-class optional ATR-01 fields would be a
  schema change to `schema/nhid_trace_schema_v1.json` and is an **open decision (owner:
  Bree)** — it is deliberately not part of this note.

## Practical guidance by role

- **Payers:** use NHID-Clinical to screen caller identity and authorization. Continue
  using existing clinical and fairness review processes for the *content* of calls.
- **Vendors:** implement the NHID controls for disclosure and audit. Maintain separate
  fairness testing and clinical validation programs for your models.
- **Providers:** issue scoped credentials through NHID-Auth v2 where needed. Keep clinical
  oversight and fairness review of agent behavior under your existing governance
  structures.

**Bottom line:** NHID-Clinical solves the "who is calling and are they authorized?"
problem. It does not solve the "is this AI making fair and clinically appropriate
decisions?" problem. Keeping this boundary clear protects both adopters and the framework.
