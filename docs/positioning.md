# NHID-Clinical — Positioning

**Status:** positioning statement · **Added:** 2026-07-18 · CC BY 4.0

> This document defines the category NHID-Clinical occupies and, just as
> deliberately, the categories it does not. It is the canonical answer to
> "what exactly is this?" for readers arriving from AI governance, security
> engineering, healthcare architecture, or standards work. Companion
> documents: [terminology](terminology.md) (preferred and deprecated terms)
> and [claim boundaries](claim-boundaries.md) (what may and may not be
> claimed).

---

## The thesis, in one sentence

**NHID-Clinical does not govern the AI model. It governs the moment a
non-human actor crosses an organizational boundary** — proving who the
agent is, who authorized it, what scope it holds, whether it disclosed
itself, and what happened during the interaction.

## The category, stated precisely

NHID-Clinical is an **operational AI governance framework for disclosed
non-human actors operating under delegated authority across healthcare
organizational boundaries.**

Each word is load-bearing:

- **Operational** — the framework is pipeline-native and evidence-producing,
  not a policy document. The word is earned by the deterministic conformance
  test suite and the machine-readable audit output (FHIR AuditEvent), which
  make a claim of conformance *checkable in a terminal* rather than asserted
  on paper. Remove the test suite and "operational" would be an unearned
  adjective.
- **AI governance** — the umbrella. NHID-Clinical belongs to the part of AI
  governance concerned with the conduct, identity, and accountability of AI
  systems in deployment — not model development, validation, or safety.
- **Non-human actors** — the subject. A machine actor acting on behalf of an
  organization, frequently with no human participant present in the
  interaction. (Not "autonomous" — see [terminology](terminology.md) for why
  that word is deprecated.)
- **Delegated authority** — the mechanism. The actor represents a provider
  organization only because that organization granted it scoped authority.
- **Cross-organizational** — the boundary. NHID-Clinical governs the
  interaction *between* two organizations, not activity inside a single
  trust domain.
- **Healthcare** — the domain, and the differentiation. See "Where the
  differentiation actually is," below.

## Where it sits in the landscape

```
AI Governance
│
└── Operational AI Governance
    │
    └── NHID-Clinical
        │
        ├── Governance layer (transparency + accountability)
        │   ├── AI-caller disclosure ....... IDG-01, DBC-01
        │   ├── data-exchange sequencing ... PDX-01
        │   ├── escalation to a human ...... EIT-01
        │   ├── audit evidence ............. ATR-01 (FHIR AuditEvent)
        │   └── conformance testing ........ CTS + deterministic engine
        │
        └── Identity / security layer (delegated authorization)
            ├── agent identity ............. Ed25519 agent passport
            ├── delegated authority ........ NPI-anchored delegation
            ├── scoped authorization ....... monotonic scope narrowing
            ├── per-interaction binding .... call-SID nonce
            └── revocation ................. permanent, per-agent/delegation
```

## The two-layer model (read this before choosing a single label)

NHID-Clinical is a **stack that crosses one category line the literature
keeps separate.** A single label flattens it; be explicit about the layers
instead.

| Layer | What it is | Native category | Audience that owns it |
| :-- | :-- | :-- | :-- |
| **Governance layer** — IDG-01, PDX-01, DBC-01, EIT-01, ATR-01, CAS, CTS | Transparency, accountability, and audit rules on the interaction | Operational AI governance / agent governance | NIST AI RMF, ISO/IEC 42001, compliance |
| **Identity / security layer** — NHID-Auth v2 | Non-human actor identity and scoped delegation | Non-human identity governance / AI security (authorization) | Security engineering, the SPIFFE/OAuth world |

Consequences for how the project talks about itself:

- **"AI governance" is the correct umbrella**, because a governance program
  can legitimately contain a security mechanism as a component (the way a
  governance program can require TLS). Keep it.
- **Never let "governance" erase the security layer** when the audience is
  security engineers. To that room, NHID-Auth v2 is a *protocol* — a wire
  format, a verification algorithm, and trust-chain semantics — and calling
  it "governance" reads as policy-soft and buries the project's most rigorous
  artifact. Present the layer whose vocabulary the room respects.
- **Never let "non-human identity" swallow the whole**, either. That framing
  loses disclosure, escalation, accountability, and audit — which are the
  governance-layer controls and half the point.

## What NHID-Clinical governs — and does not

**Governs** (the actor's observable conduct and accountability at the
boundary):

- whether the caller disclosed that it is a non-human/AI system, before any
  protected data moved;
- whether the actor holds verifiable, scoped, revocable authority to
  represent the provider organization it names;
- whether a human-escalation path exists and is honored;
- whether the interaction produced a machine-readable audit record.

**Does not govern** (deliberately out of scope — see
[scope-boundary-fairness-clinical.md](scope-boundary-fairness-clinical.md)):

- the AI model itself — its accuracy, bias, drift, or training data;
- clinical safety or validity of the agent's answers;
- model quality or output correctness of any kind;
- fairness, equity, or adverse-event surveillance.

The boundary is precise: NHID-Clinical scores **observable conduct on the
interaction**, never model internals and never model outputs. DBC-01 (the
deceptive-behavior check) is the control that sits closest to the line — it
evaluates whether the agent performed human-presence artifacts or denied
being AI *on the wire*, not the model that produced that behavior. Keep this
distinction sharp; blurring it re-enters model-governance territory and
forfeits the boundary that makes the project defensible.

## Relationship to adjacent systems

NHID-Clinical replaces none of these. Sorted by what each *is* to the
framework, rather than a flat "complements everything":

**Substrate / dependency — build on, cite as foundation.**

- **FHIR / SMART on FHIR** — the audit substrate. NHID-Clinical emits FHIR
  R4 `AuditEvent` bundles; it does not compete with the data-exchange
  standard. FHIR standardizes *how healthcare data moves*; it has no concept
  of "the caller was a disclosed AI acting under delegated authority."
- **NIST AI RMF** and **ISO/IEC 42001** — evidence targets, mapped not
  certified. These are meta-frameworks (risk-management functions, a
  management-system standard); NHID-Clinical is a concrete, testable control
  set an organization can cite *toward* them. They do not map to it; it maps
  to them.

**Composable complement — sits beside, documented coexistence.**

- **OAuth 2.x / OIDC** — the cleanest relationship. OAuth authorizes the
  software client at the transport/gateway layer ("may this client call this
  API"); NHID-Auth authorizes the specific interaction ("was this call
  delegated by this provider, in this scope, bound to this call"). The two
  checks are architecturally separate and neither substitutes for the other.
  See [nhid-auth-pki-and-oauth2-integration.md](nhid-auth-pki-and-oauth2-integration.md).

**Prior / parallel art — cite, do not claim to precede.**

- **SPIFFE / SPIRE** — the closest technical analogue for short-lived,
  cryptographically verifiable, scoped machine identity. SPIFFE solves
  runtime *workload attestation within a trust domain*; cross-domain
  delegation on top of it is an active area of work (e.g. delegated
  authentication extensions to SPIFFE trust domains). NHID-Auth is
  SPIFFE-adjacent in shape but targets a problem SPIFFE does not attempt:
  delegation *across organizational boundaries nobody jointly controls.*
- **General authenticated-delegation research** — cross-organizational
  authenticated delegation and scoped authority for AI agents is a live
  research topic in the general (non-healthcare) setting. NHID-Clinical does
  **not** claim to have invented delegated authority, scope attenuation, or
  agent passports. Its contribution is a **healthcare profile** of that
  pattern, and it should position as downstream of and composable with the
  general-layer work, not as its origin.

**Structurally inadequate for this job — contrast, name the reason.**

- **IAM platforms** (Okta, Entra, Ping, Cognito) — govern the identity
  lifecycle of actors *you* provision (employees, service accounts). NHID's
  subject is a *counterparty's* agent, whose identity you never provisioned,
  arriving on a channel (voice) with no login step. IAM sits beside NHID, not
  inside it.
- **Master Patient Index / HIE infrastructure** — different subject entirely
  (patient identity resolution; org-to-org data-sharing under a standing
  agreement). Named here only to prevent "an identity system in healthcare"
  readers from conflating them. Structural echo worth noting: MPI/HIE and
  NHID are all trust bridges across fragmented organizations — but MPI
  resolves *patients* probabilistically, HIE establishes *organizational*
  trust once at onboarding, and NHID verifies a *non-human actor's authority*
  cryptographically, per interaction.

## Where the differentiation actually is

The cryptography is not the moat. Ed25519, scoped delegation chains, and
short-lived verifiable credentials are competent applications of existing
patterns with substantial prior art. Narrowing the category into "delegated
authority for AI agents" moves NHID-Clinical from an obscure, uncontested
niche into an active and rigorously scrutinized research space — which
*strengthens* defensibility and *reduces* uniqueness at the same time.

Under this positioning, **healthcare-specificity is the differentiation** —
no longer a mere qualifier:

- the **provider organization (NPI) as the delegation trust root**;
- **payer–provider administrative workflow** semantics (eligibility, claims
  status, prior authorization);
- the **voice channel** and its disclosure problem, where verification must
  happen with no login step and often no human present;
- **FHIR-native audit** artifacts that land in systems healthcare compliance
  teams already operate;
- the **impersonation-latency** metric, grounded in real administrative call
  operations;
- **conformance testing** that makes a vendor's claim checkable rather than
  attested.

General-layer efforts solve authenticated delegation in the abstract.
NHID-Clinical applies that governance-and-identity model to a specific,
high-stakes healthcare interaction. Keep "healthcare" in the one-line
positioning and never drop it.

## Standards status (honest)

NHID-Clinical is a **voluntary, open proposal** — not an accredited standard,
a certification, or a regulatory requirement, and **not an "emerging
standard"** in the formal sense (which implies multi-stakeholder convergence
and competing implementations already underway). The accurate current label
is a **standards candidate / input to a potential work item.**

The gating deficiency for standards-track credibility is a **second,
independent implementation that passes the conformance test suite.** In the
now-contested general delegation space, reviewers will benchmark NHID-Clinical
against general-layer proposals, so this bar is higher, not lower, than it
would be for an uncontested niche. Related open work items the project itself
flags: a registry / trust-resolution model (NPI → public key), specified
revocation and key lifecycle, and federation patterns composable with
SPIFFE/OAuth-style stacks. See [claim-boundaries.md](claim-boundaries.md).

## Terms to refuse

Never self-describe with: **autonomous** (implies independent
goal-pursuit/planning the deployments do not have), **emerging standard**,
**universal / general identity layer**, **control plane** or **trust
infrastructure** (imply production-grade federation, lifecycle automation,
and live enforcement not yet built — the reference implementation's
revocation is in-memory), or **general healthcare AI governance** (implies
model safety, bias, and clinical validation, all out of scope). Full list
and rationale in [terminology](terminology.md) and
[claim-boundaries](claim-boundaries.md).

---

## Appendix — proposed README opening (draft, for review)

A drop-in replacement for the repository README's tagline block, aligning the
public front door with this positioning. **Draft only** — not yet applied to
`README.md`; the maturity lines and "Not a standard / Not a certification /
Not a product" language are preserved verbatim.

> **NHID-Clinical**
>
> **An operational AI governance framework for disclosed non-human actors
> operating under delegated authority across healthcare organizational
> boundaries.**
>
> NHID-Clinical does not govern the AI model. It governs the moment a
> non-human actor crosses an organizational boundary — proving who the agent
> is, who authorized it, what scope it holds, whether it disclosed itself,
> and what happened during the interaction. Two layers: a **governance layer**
> (AI-caller disclosure, escalation, and machine-readable audit, with a
> deterministic conformance suite) and a **non-human-actor identity and
> delegated-authorization protocol** (NHID-Auth v2). Today the concrete
> channel is payer–provider voice workflows; the model is designed to
> generalize to other real-time, cross-organizational healthcare
> interactions.
>
> Built from direct payer operations experience — the **impersonation
> latency** problem, seen firsthand on live eligibility, claims, and
> prior-authorization lines.
>
> **Not a standard. Not a certification. Not a product.** An open, testable
> reference for the ecosystem.

---

CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 — a public comment, not a
NIST endorsement, adoption, or certification.
