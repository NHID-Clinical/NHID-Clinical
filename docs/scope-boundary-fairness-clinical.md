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

## Integration approach (not expansion)

NHID-Clinical is designed to work *underneath* fairness and clinical governance programs,
not replace them:

- **CAS and Impersonation Latency** metrics can be stratified by workflow or population
  segment when a separate fairness program requires it — they are per-call measurements
  with no protected-attribute inputs of their own.
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
