# NHID-Clinical — Claim Boundaries

**Status:** claim-discipline reference · **Added:** 2026-07-18 · CC BY 4.0

> What NHID-Clinical may and may not claim about itself, so every artifact —
> spec, playbook, site, deck, comment letter — stays inside the same
> defensible line. Pairs with [positioning.md](positioning.md) and
> [terminology.md](terminology.md). Modeled on the discipline already applied
> in the manuscript consistency audit and the
> [scope boundary](scope-boundary-fairness-clinical.md).

---

## In scope / out of scope

**In scope — what NHID-Clinical governs.**

- AI-caller / non-human-actor **disclosure** on the interaction (IDG-01,
  DBC-01).
- **Sequencing** of protected-data exchange behind disclosure (PDX-01).
- **Delegated authority**: verifiable, NPI-anchored, scoped, expiring,
  revocable authorization to represent a provider organization (NHID-Auth
  v2).
- **Scope enforcement** via monotonic narrowing across delegation hops,
  checked by the verifier at evaluation time (application-layer enforcement,
  not a cryptographic guarantee on its own).
- **Escalation** to a human (EIT-01).
- **Accountability and audit evidence** (ATR-01, FHIR AuditEvent).
- **Conformance testing** of the above (deterministic engine + CTS).

**Out of scope — what NHID-Clinical does not govern.**

- The **AI model** itself: accuracy, bias, drift, training data.
- **Clinical safety** or validity of the agent's answers.
- **Model quality** or output correctness of any kind.
- **Fairness, equity**, or adverse-event surveillance.
- **Patient identity** (that is MPI territory) and **data-exchange
  standardization** (that is FHIR territory).

The line: NHID-Clinical scores **observable conduct at the interaction
boundary**, never model internals and never model outputs.

**Deployment caveat — audit artifacts may carry regulated data.** ATR-01
traces can contain PHI or other regulated healthcare context depending on
implementation. The framework does not define how that record is protected;
deployments must set retention, access-control, encryption, and privacy
obligations per organizational policy and applicable regulation, and route
business-associate and data-flow questions to counsel. State this proactively
— it signals maturity to a healthcare security reviewer, who expects the
question.

## Claims to make / claims to avoid

| Make (defensible) | Avoid (overclaim) |
| :-- | :-- |
| "An operational AI governance framework for disclosed non-human actors under delegated authority across healthcare organizational boundaries." | "A healthcare AI governance framework." (implies model/bias/clinical governance) |
| "Governs the moment a non-human actor crosses an organizational boundary." | "Governs healthcare AI." / "Governs autonomous AI." |
| "A non-human-actor identity and delegated-authorization protocol (reference implementation)." | "A universal identity layer." / "Trust infrastructure." / "A control plane." |
| "A healthcare-specific delegation scheme aligned with emerging authenticated-delegation approaches, composable with SPIFFE/OAuth-style stacks." | "A profile of authenticated delegation" (implies an adopted base standard) · "We invented delegated authority / agent identity / scope attenuation." |
| "Mapped to NIST AI RMF and ISO/IEC 42001; designed to support the transparency obligations described in EU AI Act Article 50." | "Compliant with / certified against" any of them. |
| "A voluntary, open proposal and standards candidate." | "An emerging standard." / "The standard for AI agents in healthcare." |
| "Reference implementation; revocation is in-memory; key custody and federation are documented but not built." | "Production-ready." / "Enterprise infrastructure." |
| "Disclosure latency is measured on recorded traffic; the framework does not detect covert agents." | "Detects unauthorized/rogue AI callers." |
| "Delegation makes compromise scoped and revocable rather than unbounded." | "Prevents impersonation / fraud." |

## Maturity boundaries

State the layer's maturity honestly wherever it is discussed. Snapshots as of
this writing; adopt by version from current materials.

| Element | Standing |
| :-- | :-- |
| Governance-layer controls (IDG/PDX/DBC/EIT/ATR-01) + CTS | Reference implementation; deterministic engine with a passing test suite. Checkable today from recorded interactions. |
| Call Authorization Score | Reference implementation; a triage instrument, not a certification. |
| NHID-Auth v2 (delegation, scope, passports, per-call binding) | Working reference *primitive*, not deployed *infrastructure*. |
| Revocation | In-memory in the reference implementation — explicitly not production-grade. |
| Key custody / rotation / per-tenant isolation | Documented production path; not built. |
| Registry (NPI → public key resolution) | Future work; does not exist. Requires a neutral operator. |
| Federation / multi-hop authorization propagation automation | Open problem; documented direction, not a shipped capability. |
| Second independent implementation | Does not exist. This is the gating deficiency for standards-track credibility. |
| Large-scale production validation | Limited public evidence. The recommended first step remains a shadow pilot on the adopter's own traffic. |

## Standards posture

- NHID-Clinical is a **voluntary, open proposal** (CC BY 4.0), submitted as a
  **public comment** to a NIST RFI docket (**NIST-2025-0035-0026**). A public
  comment is **not** a NIST endorsement, adoption, or certification.
- Current honest label: **standards candidate / input to a potential work
  item** — not an emerging standard.
- Gating step to strengthen the standards argument: a **second, independent
  implementation passing the conformance test suite**, plus published
  designs for registry/trust-resolution, revocation and key lifecycle, and
  federation composability.

## Audience-specific framing (same claims, different emphasis)

- **NIST / governance reviewers:** lead with the governance layer, the named
  risk (impersonation latency), the measurement methodology (shadow pilot),
  and the mappings. Strongest on RMF Map and Measure; be candid that
  institutional Govern (an accountable body behind the framework) is not yet
  in place.
- **Healthcare architecture boards:** lead with "sits beside FHIR / OAuth /
  IAM, replaces nothing," and the separately-adoptable layers (behavioral
  layer is near-zero-risk and checkable from call records; cryptographic
  layer is immature and deferrable).
- **Security engineers:** lead with the delegation *protocol*, acknowledge
  SPIFFE-delegation and general authenticated-delegation work as prior/
  parallel art, and disclose the gaps first (in-memory revocation, no
  federation, no second implementation, key lifecycle unspecified). Disclosed
  immaturity is forgiven; immaturity dressed as "infrastructure" is not.

---

CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 — a public comment, not a
NIST endorsement, adoption, or certification.
