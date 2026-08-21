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
  v2), evaluated in the policy path by **DLG-01** when a deployment opts in.
- **Scope enforcement** via monotonic narrowing across delegation hops,
  checked by the verifier at evaluation time (application-layer enforcement,
  not a cryptographic guarantee on its own). A verified scope additionally
  constrains PDX-01: a delegation for eligibility does not authorize
  requesting a claim number.
- **Escalation** to a human (EIT-01).
- **Accountability and audit evidence** (ATR-01, FHIR AuditEvent).
- **Conformance testing** of the above (deterministic engine + CTS).

**What DLG-01 does and does not establish.** State all four of these together
or none of them:

1. It is **opt-in**. Without a `DelegationContext` the control is not
   evaluated and the engine behaves exactly as it did before. Do not describe
   delegated authority as verified "by default", "always", or "on every call".
2. It verifies a delegation against a **trust anchor the deploying
   organization configured itself**. There is no directory, registry, or
   discovery service. NHID-Clinical does not vouch for any provider key; it
   checks signatures against keys the deployer already chose to trust.
   An NPI with no configured anchor is refused, not accepted.
3. The NPI is **format-validated and cryptographically bound** to the
   delegation. It is **not verified against NPPES** or any external source.
   A well-formed NPI in a delegation signed by a trusted key means that key's
   holder asserted it — nothing more.
4. Enforcement covers **what the agent asked for on the interaction**, drawn
   from speech patterns and declared `phi_accessed` fields. It is not a
   database-layer or API-layer authorization control, and it does not prevent
   an agent from obtaining data by some path the interaction does not reveal.

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
| "A voluntary open proposal with standards-oriented artifacts." | "An emerging standard." / "The standard for AI agents in healthcare." / "A standards candidate" (implies a formal standards process has started). |
| "Reference implementation; revocation is in-memory; key custody and federation are documented but not built." | "Production-ready." / "Enterprise infrastructure." |
| "Disclosure latency is measured on recorded traffic; the framework does not detect covert agents." | "Detects unauthorized/rogue AI callers." |
| "Delegation makes compromise scoped and revocable rather than unbounded." | "Prevents impersonation / fraud." |

## Maturity boundaries

State the layer's maturity honestly wherever it is discussed. Snapshots as of
this writing; adopt by version from current materials.

| Element | Standing |
| :-- | :-- |
| Governance-layer controls (IDG/PDX/DBC/EIT/ATR-01) + CTS | Reference implementation; deterministic engine with a passing test suite. Checkable today from recorded interactions. |
| Call Authorization Score | **Research component, not a product capability.** Nothing in the repository produces its inputs, so no real call can be scored. Not to be surfaced publicly. |
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
- Current honest label: **a voluntary open proposal with standards-oriented
  artifacts / input to a potential work item** — not an emerging standard, and
  not a "standards candidate" in the sense of an opened standards-body process.
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

## Maintainer / Reviewer Claims Control (v1.x)

This is the **authoritative pre-publish gate** for external claims — the
operational form of the tables above. It is a project governance control, not an
informal checklist: it exists to prevent uncontrolled external assertions.

> **Reviewer test.** *Could this claim be independently verified from repository
> artifacts (code, tests, docs) or public records (the NIST filing)?* If not, it
> does not ship.

**How to use.** Before any artifact goes out — spec, site copy, deck, comment
letter, README, social post — every external claim it makes MUST map to an
allowed row below (or a close paraphrase). If a claim matches a prohibited row,
or matches nothing here, **cut it or rewrite it to the nearest allowed form.**
When unsure, default to the weaker claim.

### Not allowed — CAS is a research component

`src/nhid_cas.py` computes a 0–1 score with tiers named "Verified Trust" and
"Conditional Trust" plus a `badge_eligible` L1/L2 value. Nothing in this
repository produces its inputs (`hallucination_risk`, `deepfake_risk_score`,
`sip_attestation`, `oig_exclusion_match`, `entity_match_rate`), so no real call
can be scored, and its tier names read as a trust rating this project does not
issue.

Do not present CAS, a CAS tier, or a conformance badge as a product capability,
on any public page, in any published artifact, or in procurement material. The
module and its 38 tests are retained for research; the score never influences a
policy decision and `evaluate_all()` structurally cannot read it.

### Allowed — with verifiable basis

| Claim | Verifiable basis |
| :-- | :-- |
| "An open **policy-and-evidence layer** for healthcare administrative AI voice interactions." *(anchor claim)* | `src/nhid_policy_engine_v1.py` + CTS + adapters + `src/fhir_audit_emitter.py` + `scripts/export_evidence_pack.py` |
| "**Implements enforcement behavior at the interaction boundary.**" | `PolicyAction` + `evaluate_all()` emit the action; CTS asserts `expected_policy_action` |
| "Runs **receiver-side** on inbound calls **or sender-side** in a vendor's own call path." | The engine evaluates observable conduct and is orientation-neutral: `evaluate_all(session, event)` takes no party argument. Say "supported by the engine, adapters and evidence export"; do **not** say a packaged sender-side product exists, and do not imply any vendor has deployed it. |
| "**Separates identity disclosure, authorization evaluation, enforcement decision, and evidence capture into distinct control stages.**" | `PolicyDecision` flow (IDG/PDX → decision → Enforcement Profile → ATR-01 / FHIR); `docs/enforcement-profile.md`. This staged separation is a core strength — it is not "a disclosure banner." |
| "A **deterministic, testable conformance model** (same inputs → identical output)." | `conformance/nhid_conformance_test_suite_v1.yaml` + `src/cts_runner.py`; passing unit suite |
| "Five controls (IDG/PDX/DBC/EIT/ATR-01) plus a documented **Enforcement Profile — not a sixth control.**" | `docs/enforcement-profile.md`; `evaluate_all` ladder |
| "Emits **FHIR AuditEvent** evidence for the interaction." | `src/fhir_audit_emitter.py`, `nhid_audit_export.py` |
| "**Mapped to** NIST AI RMF and ISO/IEC 42001; **designed to support** EU AI Act Art. 50 transparency obligations." | `regulatory-alignment.html` — mapping only |
| "Addresses an **underserved operational gap** in cross-organizational healthcare AI voice workflows." | Narrow scope; conservative, hedged |
| "A **voluntary open proposal with standards-oriented artifacts**; submitted a **public comment** to NIST (NIST-2025-0035-0026)." | Public comment ≠ endorsement or an opened standards process |
| "Revocation is **checked at verification and in-memory** in the reference implementation." | `src/agent_identity.py` — not live / not cross-org |
| "**Delegated authority is verified in the policy path (DLG-01) when a deployment opts in**, and the verified scope constrains the data boundary." | `evaluate_dlg01` + `evaluate_pdx01` in `src/nhid_policy_engine_v1.py`; `tests/test_dlg01_delegated_authority.py`. Always pair with the four limits stated in the in-scope section above. |
| "The **evidence pack is reproducible** and marks anything it could not generate as unavailable." | `scripts/export_evidence_pack.py` + `tests/test_export_evidence_pack.py`. It is not an attestation, audit opinion, or assurance engagement. |
| "A **bot-to-bot disclosure gate** exists for agent-to-agent contexts." | `evaluate_bot_to_bot()` — disclosure only, not mutual authorization |

### Prohibited — and why

| Claim | Why prohibited |
| :-- | :-- |
| "NHID is **a standard / the standard / an emerging standard / a standards candidate.**" | No adoption body, no accreditation, no second implementation, no opened standards-body process. |
| "**Provides authentication of AI agents.**" | Conflates identity declaration, credential verification, authorization, and enforcement. **Use instead:** *"NHID evaluates declared identity, authorization context, and interaction policy. It does not replace an underlying identity provider or cryptographic identity infrastructure."* |
| "**Nobody** is solving receiver-side enforcement." | False — runtime enforcement is actively researched. Say *"no widely adopted, standardized receiver-side model exists."* |
| "**Solved agent identity** / **prevents impersonation or fraud.**" | Too broad; NHID makes compromise scoped and revocable, it does not prevent it. |
| "**Production-ready** / enterprise infrastructure / a trust or control plane." | Reference primitive; in-memory revocation, no registry, no federation, no key lifecycle. |
| "**Compliant with / certified against** NIST / ISO / EU AI Act." | Mapping ≠ compliance ≠ certification. |
| "**Detects** unauthorized / rogue / covert AI callers." | Measures disclosure on recorded traffic; does not detect covert agents. |
| "A **universal identity layer** / a **healthcare AI governance framework.**" | Implies the model/bias/clinical scope NHID explicitly excludes. |
| "**Adopted by** [any payer / provider / vendor]." | Zero production adoption today. |

**Standing decision (do not reopen):** enforcement is documented as an
Enforcement Profile over the five controls, **not** an `ENF-01` sixth control —
the implementation already produces enforcement outcomes, so a sixth control
would duplicate them. See `docs/enforcement-profile.md`.

---

CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 — a public comment, not a
NIST endorsement, adoption, or certification.
