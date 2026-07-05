# Visuals and Graph Recommendations

**Version:** 1.0 · **Status:** Recommendations memo — none of these visuals exist yet unless noted

> This memo recommends new diagrams and charts for the specification, whitepaper, and
> website-facing technical docs. It does not create the visuals themselves (that's a design/
> illustration task, typically SVG, matching the existing `docs/assets/archive/fig1–fig7-*.svg`
> brand style referenced throughout the Master Knowledge Archive). For each item: intended
> audience, the decision it supports, its data source, and where it belongs.

## Existing visuals (for context, not new work)

The Master Knowledge Archive already includes 7 SVG figures (`fig1-trust-stack.svg` through
`fig7-il-formula.svg`) covering the five-layer trust stack, impersonation-latency anatomy, the
formal IL measurement diagram, and the API request flow. The recommendations below are
additive — they cover ground those seven do not.

---

### 1. Cryptographic Call Binding Sequence Diagram

| | |
| :-- | :-- |
| **Audience** | Vendor engineering teams implementing Tier 2; payer security reviewers evaluating a vendor's NHID-Auth integration |
| **Decision it supports** | "Is this vendor's cryptographic flow actually correct end-to-end, or are they missing a step (e.g., skipping agent co-signature, not checking call-SID binding)?" |
| **Draws from** | `src/agent_identity.py` API reference (Master Knowledge Archive §4.3), the Tier 2 integration example (§4.6), [the PKI/OAuth2 integration guide](nhid-auth-pki-and-oauth2-integration.md) §1.3–1.4 |
| **Belongs in** | Technical specification (cryptographic authorization model section), PKI/OAuth2 integration guide |

A sequence diagram (swimlanes: Provider, Vendor/Agent, Payer) showing, in order: provider key generation (once) → agent key generation (per agent/tenant) → delegation issuance (provider signs `Delegation` naming the agent's public key + NPI + scope + TTL + call-SID) → provider signature → agent co-signature (proves the agent controls the private key matching the public key named in the delegation) → call-bound passport presented to payer → payer-side verification (`verify_passport`, checking signature, expiry, revocation, nonce match) → audit emission (the verification result feeds into the `nhid-auth-verification` FHIR milestone). This is the single most-requested diagram for vendor engineering onboarding, since the current documentation describes each step in prose/code but has no single at-a-glance picture of the full flow.

### 2. Trust and Key Management Diagram

| | |
| :-- | :-- |
| **Audience** | Payer/provider compliance officers and security architects evaluating a multi-vendor, multi-hop deployment |
| **Decision it supports** | "Where does trust actually originate in this deployment, and what's the blast radius if one node in this diagram is compromised?" |
| **Draws from** | [PKI/OAuth2 integration guide](nhid-auth-pki-and-oauth2-integration.md) §1.2 (trust anchors), §1.5 (multi-tenant isolation), §1.6 (sub-vendor chains), §1.9 (revocation store) |
| **Belongs in** | PKI/OAuth2 integration guide, vendor trust questionnaire (as a reference image when discussing Section 6/7 questions) |

A layered box diagram: Provider (NPI trust anchor) at the top, branching down to Vendor platform(s), then Sub-vendor (when present, capped at 3 hops total), then Agent instance(s) at the leaves — with a side panel showing the public-key-resolution path (static exchange / JWKS / future registry, per §1.8 of the PKI guide) and a separate, explicitly-flagged revocation store node showing it's checked synchronously at verification time, not pulled periodically.

### 3. OAuth2 + NHID-Auth Overlay Diagram

| | |
| :-- | :-- |
| **Audience** | Vendor backend engineers who already have OAuth2/OIDC infrastructure and need to see where NHID-Auth fits without re-architecting it |
| **Decision it supports** | "Do I need to replace my existing OAuth2 setup, or just add something alongside it?" (Answer: alongside — this diagram makes that visually obvious in a way the prose in §2.2 of the integration guide cannot.) |
| **Draws from** | [PKI/OAuth2 integration guide](nhid-auth-pki-and-oauth2-integration.md) §2.2 (the existing ASCII overlay), §2.10 (Tier 1 vs. Tier 2 reference patterns) |
| **Belongs in** | OAuth2/OIDC integration guide (replacing/supplementing the ASCII diagram already there), technical specification |

Two parallel lanes feeding into the same policy engine + FHIR audit emitter: (1) OAuth2 access token → API gateway → "is this client allowed to call this API at all"; (2) NHID-Auth passport → policy engine → "is this specific call's claimed authorization real." Both lanes terminate at the same audit emission step, visually reinforcing that they're complementary checks feeding one record, not competing systems.

### 4. FHIR AuditEvent Mapping Diagram

| | |
| :-- | :-- |
| **Audience** | Payer-side FHIR/interoperability engineers integrating the audit Bundle into an existing FHIR-based system or SIEM |
| **Decision it supports** | "Which of my existing FHIR ingestion pipelines/validators do I point this at, and which AuditEvent fields should my dashboards key off?" |
| **Draws from** | [fhir-auditevent-mapping.md](fhir-auditevent-mapping.md) (the 7-milestone table, agent slices, code systems), [fhir-auditevent-standardization-for-ai-agents.md](fhir-auditevent-standardization-for-ai-agents.md) §2 (lifecycle) and §5 (extension points) |
| **Belongs in** | FHIR AuditEvent standardization doc, technical specification (FHIR audit trail mapping section) |

A timeline/swimlane diagram: the 7 call-lifecycle milestones along the x-axis (session-start → identity-disclosure → auth-verification → phi-gate → phi-exchange → escalation → call-end), each annotated with its DICOM/HL7 type code and which NHID field(s) populate it, plus call-out boxes at the `nhid-identity-disclosure` and `nhid-phi-gate` milestones showing the recommended (not-yet-implemented) `nhid-participant-kind` extension point.

### 5. CAS Distribution Visual

| | |
| :-- | :-- |
| **Audience** | Payer call-center operations leadership deciding whether/how to use CAS as a procurement or monitoring signal; vendors wanting to see where their calls land |
| **Decision it supports** | "What does a 'normal' distribution of CAS scores actually look like across real call volume, and where's the cutoff worth acting on?" |
| **Draws from** | Master Knowledge Archive §3.3 (CAS formula and tier ladder: Verified Trust ≥0.90, Conditional Trust ≥0.75, Review Required ≥0.50, Denied/Degraded ≥0.20, Hard Denial <0.20) |
| **Belongs in** | Shadow evaluation guide, `for-payers.html`, technical specification (CAS summary section) |

A histogram of CAS scores (x-axis: score bucket 0.0–1.0, y-axis: call count) overlaid with the five tier-ladder bands as shaded background regions, so a payer running a shadow pilot can drop their own real call-volume data into the same chart shape. **Data source note:** this requires real or pilot-sample call data to populate — until a shadow pilot produces real numbers, render this with the existing example Bundle's score plus clearly-labeled synthetic/illustrative data, not fabricated "real" production statistics.

### 6. Shadow Pilot Trend Graphs

| | |
| :-- | :-- |
| **Audience** | Payer compliance teams running a 90-day shadow pilot (see `roadmap.html`/`pilot.html`); the NHID-Clinical community reviewing anonymized pilot results |
| **Decision it supports** | "Is behavior improving, worsening, or flat over the pilot window, and which control is the biggest outlier?" |
| **Draws from** | The 90-day pilot structure (Month 1 baseline, Month 2 gap analysis, Month 3 report) |
| **Belongs in** | Shadow evaluation guide, pilot report template (a new artifact the pilot's "Month 3 — Report" step would produce) |

Four line charts sharing a common time axis (the pilot's 90 days, or whatever window a given deployment observes): violation counts over time (stacked by control: IDG-01/PDX-01/DBC-01/EIT-01/ATR-01), disclosure compliance trend (% of calls with `IL(turns) = 0`), escalation compliance trend (% of escalation requests honored), CAS percentile trend (median + 10th percentile CAS per week), and impersonation latency trend (median `IL` in turns/seconds per week). **Data source note:** same caveat as #5 — these are templates to populate with a pilot's actual data, not pre-filled with invented numbers, since "No organizations have adopted or piloted it yet" is the accurate current project status.

### 7. Vendor Maturity Matrix

| | |
| :-- | :-- |
| **Audience** | Payers/providers comparing multiple vendor candidates side by side; vendors positioning themselves against competitors |
| **Decision it supports** | "Which vendors are Tier 0/1/2-capable, and where does each one's gap actually sit?" |
| **Draws from** | The integration tier ladder (Master Knowledge Archive §1.5, the [staged integration guide](v2-integration-guide.md)), the [vendor trust questionnaire](vendor-trust-questionnaire.md) sections 1–10 |
| **Belongs in** | Vendor trust questionnaire (as a fillable summary table at the end), `for-payers.html` |

A matrix with vendors as rows and four capability columns — **Behavioral conformance** (Tier 0: passes IDG-01/PDX-01/DBC-01/EIT-01 on a sample check), **Cryptographic identity** (Tier 2: has per-agent keys, valid delegation chain), **Audit maturity** (emits FHIR-mappable, tamper-evident audit records — questionnaire §8), **Deployment effort** (Tier 0/1/2, per the integration guide's time estimates: 15 min / ~2 hr / ~1 day) — each cell colored/scored from the questionnaire answers. This is the one recommended visual that's a **filled-in worksheet rather than a fixed illustration**: it should ship as a table template (markdown or spreadsheet) a payer fills in per vendor, not a static pre-rendered graphic.

---

## Summary table

| # | Visual | Audience | Primary location |
| :-- | :-- | :-- | :-- |
| 1 | Crypto call binding sequence diagram | Vendor engineers, security reviewers | Technical spec, PKI guide |
| 2 | Trust & key management diagram | Compliance officers, security architects | PKI guide, vendor questionnaire |
| 3 | OAuth2 + NHID-Auth overlay diagram | Vendor backend engineers | OAuth2/OIDC guide, technical spec |
| 4 | FHIR AuditEvent mapping diagram | FHIR/interoperability engineers | FHIR standardization doc, technical spec |
| 5 | CAS distribution visual | Payer ops leadership, vendors | Shadow eval guide, for-payers.html |
| 6 | Shadow pilot trend graphs (4) | Pilot compliance teams, community | Shadow eval guide, pilot report template |
| 7 | Vendor maturity matrix | Payers comparing vendors | Vendor questionnaire, for-payers.html |

All seven are additive to the existing fig1–fig7 SVG set and should follow the same brand style
(SVG source, 300-DPI PNG export for the PDF build, page footer "NHID-Clinical · CC BY 4.0 ·
nhid-clinical.org") described in the Master Knowledge Archive changelog. Items 5 and 6 require
real or pilot data to be meaningful — until a pilot runs, render them with clearly-labeled
illustrative placeholder data rather than implying production statistics that don't exist yet.
