# NHID-Clinical — Terminology

**Status:** terminology reference · **Added:** 2026-07-18 · CC BY 4.0

> The controlled vocabulary for describing NHID-Clinical consistently across
> the specification, playbook, website, and external communications. Pairs
> with [positioning.md](positioning.md) (the category) and
> [claim-boundaries.md](claim-boundaries.md) (what may be claimed).

---

## Preferred vs. deprecated terms

| Use | Not | Why |
| :-- | :-- | :-- |
| **non-human actor**, **AI-operated system**, **delegated AI agent** | autonomous AI, autonomous agent | "Autonomous" implies independent goal-pursuit and planning; healthcare deployments retain human oversight and mixed authority. The actual problem is a machine actor acting for an organization *without a human present in the interaction*. |
| **operational AI governance framework** | AI governance framework (unqualified), healthcare AI governance framework | Unqualified "AI governance" implies model validation, bias, and clinical-safety governance — all out of scope. "Operational" scopes it to deployment-time conduct, identity, and audit. |
| **non-human-actor identity and delegated-authorization protocol** (for the lower layer) | identity layer (unqualified), trust infrastructure, control plane | The lower layer is a protocol with prior art, not general identity infrastructure. "Trust infrastructure" / "control plane" imply production-grade federation and enforcement not yet built. |
| **mapped to** / **aligns with** / **can support** (standards) | compliant with, certified, required by | NHID-Clinical maps to external frameworks; it is not certified against any and mandated by none. Reproduce the framework's existing "mapped, not certified" discipline. |
| **standards candidate** / **input to a work item** | emerging standard, the standard | "Emerging standard" implies multi-stakeholder convergence and competing implementations already underway. Not yet true. |
| **reference implementation** | production system, deployed infrastructure | The engine and NHID-Auth v2 are reference code. Revocation is durable within a deployment but does not propagate across organizations; trust anchors are static with no discovery; key custody is demo-grade. |
| **cross-organizational** | cross-domain (alone) | "Cross-organizational" names the actual boundary — between two organizations that do not jointly control a trust domain. |

## The two layers

- **Governance layer** — the transparency and accountability controls on the
  interaction: identity disclosure (IDG-01), pre-data-exchange sequencing
  (PDX-01), deceptive-behavior check (DBC-01), escalation (EIT-01), audit
  trail (ATR-01), the Call Authorization Score (CAS), and the Conformance
  Test Suite (CTS). Native category: operational AI governance / agent
  governance. Present with governance/compliance vocabulary.
- **Identity / security layer** — NHID-Auth v2: the cryptographic
  non-human-actor identity and scoped-delegation mechanism. Native category:
  non-human identity governance / AI security. Present with protocol/security
  vocabulary to a security-engineering audience.

## Core concepts

- **Impersonation Latency** — the elapsed time between interaction start and the
  point at which a non-human actor discloses its non-human identity to the human
  recipient. Reported in seconds and in conversational turns, with turns as the
  normative unit (`IL = 0` turns means disclosure preceded any data request).

  The term is deliberate and retained: the window it names is the interval during
  which a human recipient may reasonably believe they are talking to another
  human. Naming that window is the point.

  What the metric **does not** establish, stated explicitly because the name
  invites the opposite reading:

  - It does **not** determine that impersonation occurred.
  - It does **not** establish intent, malicious or otherwise.
  - It does **not** detect an impersonator, and NHID-Clinical performs no
    voice, acoustic or signal analysis of any kind.
  - It does **not** prevent impersonation.
  - It does **not** establish authentication or authorization. A disclosed
    agent may still be unauthorized; an undisclosed one may be perfectly
    authorized.

  Impersonation Latency measures disclosure timing. Everything else about the
  caller is a separate question answered — or not answered — by other controls.

  **Measurement validity:** disclosure is observed through a transcript, so a
  reported Impersonation Latency is only as accurate as the transcription path
  that produced it. See the ASR dependency in
  [scope-boundary-fairness-clinical.md](scope-boundary-fairness-clinical.md).
- **Delegated authority / delegation** — a provider organization granting a
  non-human actor scoped authority to act on its behalf, expressed as a
  signed, NPI-anchored, expiring, revocable object.
- **Scope attenuation (monotonic narrowing)** — the safety property of the
  delegation chain: each hop may only restrict, never expand, the authority
  it received, as checked by the verifier at evaluation time. A compromised
  middle hop cannot grant itself authority the provider never gave. Say
  "checked/enforced by the verifier," not "structurally enforced" — the
  latter implies a cryptographic guarantee where the reference implementation
  performs application-layer checks.
- **Agent passport** — the presented credential: a delegation plus the
  provider's signature and the agent's co-signature (NHID-Auth v2 reference
  object).
- **Per-interaction binding** — binding a delegation to a specific call
  (call-SID nonce), so a valid credential replayed from a different
  interaction fails verification.
- **Call Authorization Score (CAS)** — a per-interaction score summarizing
  governance-layer conformance, bucketed into trust tiers. A triage
  instrument, not an acquittal of model quality.
- **Conformance / conformance testing** — evaluation of an interaction
  against the controls by a deterministic engine (same inputs → identical
  outputs), which is what makes a conformance claim checkable rather than
  attested.
- **Disclosure** — a non-human actor stating, before protected data is
  exchanged, that it is an automated/AI system.

## Control identifiers (governance layer)

| ID | Name | Requirement (one line) |
| :-- | :-- | :-- |
| **IDG-01** | Identity Disclosure Gate | Disclose non-human identity before any PHI exchange. |
| **PDX-01** | Pre-Data Exchange Gate | No protected data until identity is disclosed. |
| **DBC-01** | Deceptive Behavior Check | No claim of human status or licensed-professional standing. Evaluated on the agent's own identity assertion text. Acoustic-artifact detection was withdrawn in v1.3.2 — it read a field the agent supplied about itself. |
| **EIT-01** | Escalation Implementation Test | A clear human-handoff path, honored on request. |
| **ATR-01** | Audit Trail | Every interaction produces a machine-readable trace. |

## Category words — quick reference

- **Correct umbrella:** operational AI governance framework.
- **Correct for the lower layer (security audience):** non-human-actor
  identity and delegated-authorization protocol / delegation scheme.
- **Correct for the repository:** reference architecture (applies to the
  repo, not to the playbook, which is an implementation guide).
- **Correct current standing:** standards candidate.
- **Refuse:** autonomous · emerging standard · universal/general identity
  layer · control plane · trust infrastructure · general healthcare AI
  governance · compliant/certified (unless an actual certification exists).

---

CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 — a public comment, not a
NIST endorsement, adoption, or certification.
