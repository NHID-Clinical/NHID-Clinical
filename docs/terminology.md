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
| **reference implementation** | production system, deployed infrastructure | The engine and NHID-Auth v2 are reference code; revocation is in-memory, key custody is demo-grade. |
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

- **Impersonation latency** — the measurable trust delay between a non-human
  actor initiating an interaction and the receiving organization verifying
  that the actor is authorized to represent the claimed provider
  organization. Measured operationally as disclosure latency,
  `Δt(interaction_start → identity_resolution)`, in time and in conversational
  turns. The named problem is the full window; the measured metric today is
  the disclosure component.
- **Delegated authority / delegation** — a provider organization granting a
  non-human actor scoped authority to act on its behalf, expressed as a
  signed, NPI-anchored, expiring, revocable object.
- **Scope attenuation (monotonic narrowing)** — the safety property of the
  delegation chain: each hop may only restrict, never expand, the authority
  it received. A compromised middle hop cannot grant itself authority the
  provider never gave.
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
| **DBC-01** | Deceptive Behavior Check | No synthetic human-presence artifacts; no false human-status claims. |
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
