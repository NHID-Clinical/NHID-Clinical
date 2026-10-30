# NHID-Clinical

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/logo-lockup-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/brand/logo-lockup.svg">
    <img alt="NHID-Clinical" src="assets/brand/logo-lockup.svg" width="520">
  </picture>
</p>

<p align="center">
  <b>An operational AI governance framework for AI agents calling payers: disclosure before data, evidence per call.</b>
</p>

<p align="center">
  <a href="https://github.com/NHID-Clinical/NHID-Clinical/actions"><img alt="CI" src="https://github.com/NHID-Clinical/NHID-Clinical/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python Tests" src="https://img.shields.io/badge/python%20tests-2078%20passing-brightgreen?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-v1.3-0b6ebc?style=flat-square">
  <img alt="Code license" src="https://img.shields.io/badge/code-Apache--2.0-lightgrey?style=flat-square">
  <img alt="Spec license" src="https://img.shields.io/badge/spec%20%26%20docs-CC%20BY%204.0-lightgrey?style=flat-square">
  <a href="https://nhid-clinical.org"><img alt="Website" src="https://img.shields.io/badge/website-nhid--clinical.org-0b6ebc?style=flat-square"></a>
  <a href="https://www.regulations.gov/comment/NIST-2025-0035-0026"><img alt="NIST public comment" src="https://img.shields.io/badge/NIST-2025--0035--0026-0b6ebc?style=flat-square"></a>
</p>

<p align="center">
  <a href="https://nhid-clinical.org"><img alt="Website" src="https://img.shields.io/badge/Website-0d2846?style=for-the-badge"></a>&nbsp;
  <a href="https://nhid-clinical.org/specification.html"><img alt="Specification" src="https://img.shields.io/badge/Specification-0d2846?style=for-the-badge"></a>&nbsp;
  <a href="https://nhid-clinical.org/shadow-evaluation-guide.html"><img alt="Shadow evaluation" src="https://img.shields.io/badge/Shadow%20evaluation-14778f?style=for-the-badge"></a>
</p>

<p align="center">
  <sub>Not a standard, a certification or a product. Mapped, not certified. NIST-2025-0035-0026 is a public comment, not an endorsement.</sub>
</p>

---

## What it is

An AI voice agent phones a payer, says it is calling for a provider, and asks for a patient's eligibility, claim status or other protected health information. The payer's representative receives the call and has to decide what to disclose. NHID-Clinical is the open specification, the deterministic reference implementation and the evidence format for that moment: five testable controls, evaluated on every turn, with a machine-readable record of what the agent said and when. A payer can run it on the receiving side; a voice-AI vendor can run it in its own call path to produce evidence for its customers. Same controls, same artifacts. It governs conduct at the interaction boundary, not the AI model, and disclosing, logging or passing every control never by itself authorizes a disclosure.

## The disclosure gate

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/diagrams/disclosure-before-phi-dark.svg">
    <img alt="Four lanes: the AI voice agent calling for a provider, the payer representative, the policy engine and the operational workflow. The agent discloses, the engine returns CONTINUE_AI with IDG01_DISCLOSURE_CONFIRMED, and only then does the NPI exchange cross the disclosure gate. Two dashed branches show the gate staying closed: a PHI request before disclosure returns DENY_DATA with PDX01_PHI_GATE_TRIGGERED, and an interrupted disclosure returns DISCLOSE_IDENTITY with IDG01_DISCLOSURE_INTERRUPTED. An ATR-01 band spans every lane." src="assets/diagrams/disclosure-before-phi.svg" width="880">
  </picture>
  <br>
  <sub>Reference, a conceptual model. The same figure is on the <a href="https://nhid-clinical.org/specification.html#sequence">specification page</a>.</sub>
</p>

<p align="center">
  <a href="https://nhid-clinical.org/specification.html#trust-gateway"><img alt="The Trust Gateway on the specification page, Scenario B: an agent calling as a human persona asks for a member ID with no disclosure and the engine returns DENY_DATA with PDX01_PHI_GATE_TRIGGERED; the representative asks for a supervisor and the engine returns ESCALATE_HUMAN; the agent refuses and the engine records EIT01_ESCALATION_NOT_HONORED." src="assets/images/trust-gateway.png" width="760"></a>
  <br>
  <sub>The <a href="https://nhid-clinical.org/specification.html#trust-gateway">Trust Gateway</a>: corpus scenarios replayed through the engine and recorded verbatim. Shown here, Scenario B (<code>nhid_ec_combo_008</code>): a caller-agent with a human persona asks for protected data before disclosing. A still from the page; <code>scripts/build_gateway_fixture.py</code> regenerates it and CI fails if the page stops matching the engine.</sub>
</p>

## Five controls

Four act on the call. One records it.

| ID | Control | Rule | Limit |
| :-- | :-- | :-- | :-- |
| **IDG-01** | Identity Disclosure Gate | Disclose non-human identity before any PHI exchange. A disclosure counts only if it was heard. | Shows the agent *said* it is automated, not that its claims are true. |
| **PDX-01** | Pre-Data Exchange Gate | No protected data until identity is disclosed. | Closes the impersonation-latency window. Same-turn disclosure plus a request still fails. |
| **DBC-01** | Deceptive Behavior Check | No claim of human status or licensed-professional standing. | Judged on the agent's own words. Non-blocking (`LOG_ONLY`) and routed to human review. |
| **EIT-01** | Escalation Implementation Test | A clear human-handoff path, honored on request. | A handoff counts only when it is recorded with a timestamp and an outcome. |
| **ATR-01** | Audit Trail Requirements | Every interaction produces a machine-readable trace. | Records what the other four decided. Changes no behavior. |

**DLG-01, Delegated Authority**, is optional and opt-in, not a sixth control: a signed, scoped, unexpired, unrevoked delegation from the provider, checked against a trust anchor the deployer configures (no registry; the NPI is not checked against NPPES; it constrains what the agent may ask for on the call, and is not database or API authorization). Normative text: [specification](https://nhid-clinical.org/specification.html#dlg-01).

Every control evaluates the same turn independently through `evaluate_all`, and the most restrictive outcome wins: `DENY_DATA > ESCALATE_HUMAN > DISCLOSE_IDENTITY > LOG_ONLY > CONTINUE_AI`. There is no composite score, tier or badge ([enforcement profile](docs/enforcement-profile.md)). [Impersonation latency](docs/terminology.md) is the number of turns between connect and disclosure, target zero; it measures timing and does not detect or prevent impersonation.

## Run it

Python 3.10 or later.

```bash
git clone https://github.com/NHID-Clinical/NHID-Clinical.git && cd NHID-Clinical
pip install -r requirements.txt
python -m uvicorn app:app --port 8000 &    # the integration tests need it
python -m pytest tests/ -q
```

Expected: **2078 passing**, 0 skipped. Without the API the server-dependent integration tests skip themselves; CI starts it and requires zero skips. One request to the hosted adapter route, synthetic payload, no key:

```bash
curl -s -X POST https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod/v1/adapters/vapi/check \
  -H "Content-Type: application/json" -d @tests/demo_scenarios/vapi_noncompliant.json
```

## Three paths

- **Payers and health plans** (the receiving side): run an observe-only [shadow evaluation](https://nhid-clinical.org/shadow-evaluation-guide.html) on call traces you already hold. Nothing is inserted into the call.
- **Voice-AI vendors** (the calling side): produce the [vendor evidence pack](https://nhid-clinical.org/evidence-pack.html): conformance results, disclosure transcript, escalation phrases, a FHIR R4 `AuditEvent` sample.
- **Developers**: check one turn against the hosted API or run the engine locally, from the [developers page](https://nhid-clinical.org/developers.html).

<details>
<summary><b>Evidence and limitations</b></summary>

The framework produces machine-readable governance evidence from healthcare voice-AI interactions. Everything it concludes is bounded by the evidence reaching the evaluation path, so the limits below are properties of the design, not caveats bolted onto it.

**It evaluates transcript and event evidence.** Controls read text. A disclosure that was spoken but mis-transcribed reads as a missing disclosure; an escalation request that was mis-transcribed produces **no finding at all**, and the record then attests to a compliant interaction, the one failure mode the evidence cannot reveal on its own.

**Transcription accuracy is not established here.** NHID-Clinical does not perform speech recognition and does not independently establish ASR accuracy. An event may carry a `transcription_attestation` of `measured`, `attested` or `unattested`, so the dependency travels with the record instead of being assumed away. Assuring transcription quality, including across speaker groups, is the deploying organization's job. See the [dependency declaration](docs/scope-boundary-fairness-clinical.md).

**Population-level fairness stratification is not implemented.** `language` and `interpreter_present` are recorded so an organization can run its own reporting; the framework does not stratify, and no code here computes a per-population figure.

**It is not** a clinical safety validation system, a certification, a compliance badge, or a universal measure of AI safety. It does not govern the AI model (accuracy, bias, drift, clinical safety, output quality are [out of scope by design](docs/scope-boundary-fairness-clinical.md)), does not detect covert agents, and does not verify that the agent's reported results are true. Standards work is **mapped, not certified**.

Detection figures, their corpora and denominators, and the four evidence populations that are never combined are on the [evidence pack page](https://nhid-clinical.org/evidence-pack.html). Pinned baselines: `scripts/check_baseline.py`.

</details>

<details>
<summary><b>Composes with, does not replace</b></summary>

- **FHIR / SMART on FHIR**: audit substrate. NHID-Clinical emits FHIR R4 `AuditEvent` (base v4.0.1, no implementation guide claimed); FHIR carries the data, NHID-Clinical governs the AI actor requesting it.
- **OAuth 2.x / OIDC**: transport and client authorization ("may this client call this API"); NHID-Auth authorizes the specific interaction ("was this call delegated, in this scope"). Two separate checks; neither substitutes for the other.
- **IAM platforms**: govern actors *you* provision; NHID-Clinical governs a *counterparty's* agent you never provisioned, arriving with no login step.
- **AI governance frameworks** (NIST AI RMF, ISO/IEC 42001): meta-frameworks NHID-Clinical maps to as evidence targets, not competitors.

NHID-Clinical evaluates declared identity, authorization context and interaction policy; it does not replace an identity provider or cryptographic identity infrastructure. Category thesis: [docs/positioning.md](docs/positioning.md). Controlled vocabulary: [docs/terminology.md](docs/terminology.md). What may be claimed: [docs/claim-boundaries.md](docs/claim-boundaries.md).

</details>

<details>
<summary><b>Status</b></summary>

A working reference implementation, not a production-scale product. The measured record is [docs/project-state.md](docs/project-state.md).

**Available today**
- Deterministic policy engine and the conformance test suite; every published figure is measured from `src/nhid_policy_engine_v1.py` and no other module
- Hosted v1.3 conformance API; demo and adapter routes need no key
- [Tier 0 Shadow Pilot Kit](docs/pilot-kit/README.md): measure impersonation latency on your own call logs, offline, observe-only
- Evidence pack export a vendor can hand to a reviewer
- [Enforcement Profile](docs/enforcement-profile.md): how each `PolicyDecision` maps to a receiver action (a documented layer over the five controls, not a sixth control)
- NHID-Auth v2 delegated-authority layer, published as reference code
- Figures generated from the engine and the committed corpora, not drawn by hand; the [visual system](docs/visual-system.md) is normative and CI fails if a published figure stops matching its source
- A documented validation path: a [verified dataset inventory](docs/validation/data-sources-inventory.md), an [evidence-provenance matrix](docs/validation/evidence-provenance-matrix.md), and an [evaluation corpus v2](docs/validation/EVALUATION_CORPUS_V2_FINDINGS.md) built from the cases the engine is known to miss
- [DBC-01 scoped in writing](docs/validation/DBC-01-SCOPE-AND-LIMITATIONS.md): transcript-based detection of explicit or implied human-status claims; acoustic artifact detection is not claimed

**In progress**: first shadow-evaluation partners (observe-only, no vendor changes); an independent review of DBC-01 against its intended threat model.

**Not yet**: production deployments; a certification, accreditation or standard; any regulatory endorsement. **No design partners, pilot partners, customers or deployments exist today**, and none are represented as existing.

A dated architecture review from July 2026 is preserved in [docs/review-2026-07-30.md](docs/review-2026-07-30.md); its figures were measured against a control tier since withdrawn, so it is history rather than current state.

</details>

<details>
<summary><b>Hosted API endpoints</b></summary>

Base URL `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod`. Synthetic data only, never PHI.

| Endpoint | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /v1/demo/check` | none | Raw NHID event → conformance result |
| `POST /v1/adapters/vapi/check` | none | Native VAPI payload → result |
| `POST /v1/adapters/twilio/check` | none | Native Twilio payload → result |
| `POST /v1/adapters/vonage/check` | none | Native Vonage payload → result |
| `POST /v1/adapters/retell/check` | none | Native Retell AI payload → result |
| `POST /v1/adapters/connect/check` | none | Amazon Connect → result |
| `POST /v1/webhooks/call-progress` | none | Turn-by-turn in-call evaluation |
| `POST /v1/cts/evaluate` | none | Run the CTS YAML suite |
| `POST /v1/conformance/check` | `x-api-key` | Conformance check |

Guides: [5-minute quickstart](docs/5-minute-quickstart.md) · [v2 integration guide](docs/v2-integration-guide.md).

</details>

<details>
<summary><b>Regulatory alignment (mapped, not certified; not legal advice)</b></summary>

| Driver | Requirement | NHID-Clinical control |
| :--- | :--- | :--- |
| CMS-0057-F | FHIR API, audit retention | FHIR AuditEvent + ATR-01 |
| MACPAC 2026 | AI transparency, human review | EIT-01 + ATR-01 |
| State AI laws | Auditable AI decisions | IDG-01 + DBC-01 |
| NIST CAISI RFI | Cross-org agent identity | NHID-Auth v2 |
| EU AI Act Art. 50(1) | Designed to support the obligation to inform people they are interacting with an AI system | IDG-01 + DBC-01 |
| ISO/IEC 42001 | AI management system transparency controls | Full control set + ATR-01 |
| NIST AI RMF 1.0 | Subcategory outcomes, evidence toward, not certification | IDG-01, DBC-01, EIT-01, ATR-01 + CTS ([crosswalk](docs/nist-ai-rmf-playbook-crosswalk.md)) |

[Full matrix →](https://nhid-clinical.org/regulatory-alignment.html)

</details>

<details>
<summary><b>Repository layout</b></summary>

| Path | What's there |
| :-- | :-- |
| `*.html` (root) | The public website, served by GitHub Pages: `index.html` plus the section pages. |
| `src/nhid_policy_engine_v1.py` | **The conformance engine.** The five controls (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01) plus the opt-in DLG-01 gate. Every published detection figure, baseline and CI guard measures this module and no other. |
| `functions/handler.py` | The conformance API, and the only HTTP surface that runs the engine above. Deployed as AWS Lambda from `template.yaml`. |
| `app.py`, `nhid_policy.py`, `llm.py`, `twilio_helper.py` (root) | A separate reference **voice pipeline**: Twilio webhooks, turn handling, LLM routing. It uses its own small state machine (`nhid_policy.py`, actions `DISCLOSE`/`ESCALATE`/`BLOCK`/`ROUTE_LLM`), **not the conformance engine**, and implements none of the five controls. A call-handling example; not the thing the conformance claims are about. |
| `main.py`, `nhid_api_*.py`, `nhid_attest.py`, `nhid_payer.py`, `nhid_audit_export.py` (root) | A third surface: the authenticated API routers, mounted behind an API key. `src/voice_policy.py` is the rule evaluator these use. |
| `nhid_event_store.py` (root) | Durable event and revocation storage (SQLite). |
| `src/` | Packaged modules: the conformance engine, agent identity and the trust anchor (`agent_identity.py`, `trust_anchor.py`, `udap_agent_extension.py`, `udap_jws.py`), the audit store, the CLI, and the [specification reading aid](docs/spec-rag.md) (`nhid_spec_rag.py`, a retrieval index over `docs/`; it returns quotations, never a control decision). |
| `adapters/` | Vendor call-payload adapters (VAPI, Twilio, Vonage, Retell, Amazon Connect). |
| `middleware/` | TypeScript middleware and its test suite. |
| `tests/` | The Python conformance and invariant tests (2078 passing, all phases: foundations, adversarial, synthetic, hardening). |
| `eval/` | The reading aid's question set, scorer and tests, deliberately outside `tests/`, which is the conformance suite the published count describes. |
| `scripts/` | CI guards (`validate_ci.py`, `check_baseline.py`, `check_number_drift.py`, `check_control_set.py`) and the generators that write engine output into the pages. |
| `schema/` | Event and audit-trace schemas. |
| `conformance/` | The CTS YAML suite. |
| `docs/` | Specification docs, the [Executive Brief](docs/executive-brief.md), the [Tier 0 Shadow Pilot Kit](docs/pilot-kit/README.md), the [payer brief](docs/payer-brief.md), and the knowledge archive. |
| `specs/` | The published PDFs (maintained and archived). |
| `assets/` | Brand SVGs, diagrams, images, and site CSS. |

</details>

<details>
<summary><b>NHID-Auth v2 and related repositories</b></summary>

**NHID-Auth v2** verifies authorization where v1.3 verifies disclosure behavior: Ed25519 agent passports, NPI binding, scoped delegation (at most three hops, narrowing only), revocation, and call-SID binding, verified offline against a trust anchor the receiver configures. Reference code in `src/agent_identity.py`; no adapter or SIP path carries a passport today. [Details →](https://nhid-clinical.org/framework/nhid-auth.html)

```bash
python -m pytest tests/test_identity.py -v
python examples/issue_and_verify.py
```

Three public repositories, three jobs, one vocabulary:

| Repository | What it is |
| :-- | :-- |
| **[NHID-Clinical](https://github.com/NHID-Clinical/NHID-Clinical)** (this one) | The open framework: control definitions, the deterministic engine, the conformance suite, the event schema, the shadow-evaluation method. Apache-2.0 code, CC BY 4.0 specification. Free, and the governance verdict is never paywalled. |
| **[NHID-Clinical-SaaS](https://github.com/NHID-Clinical/NHID-Clinical-SaaS)** | The commercial product: a healthcare voice-AI governance monitoring and evidence platform built on these controls. Hosted ingestion, cross-vendor normalization, retained evidence, a findings workflow and reporting. **Zero deployments, zero pilots, zero validated willingness-to-pay.** |
| **[Simulator](https://github.com/NHID-Clinical/Simulator)** | *Zero Latency*, a five-module interactive course that teaches the controls by making you run them. Static HTML, no build. A learning tool: not the framework, not the product, and not a certification. |

</details>

## Contributing

We are looking for the first **shadow-evaluation partners**: observe-only, no vendor changes, on call traces you already hold. If you are on the payer side, the [payer brief](docs/payer-brief.md) says what a representative can and cannot verify on an automated call today. The analysis is an offline batch on de-identified transcripts, run in your environment; there is no hosted scorer and no request for call audio.

Code contributions: [CONTRIBUTING](.github/CONTRIBUTING.md) · [Discussions](https://github.com/NHID-Clinical/NHID-Clinical/discussions) · [contact@nhid-clinical.org](mailto:contact@nhid-clinical.org). Repository settings only the owner can change are listed in [docs/maintainer-checklist-github.md](docs/maintainer-checklist-github.md).

## Creator and project lead

<img src="assets/maintainer/brianna-baynard.jpg" width="96" align="left" alt="Brianna Baynard" />

**Brianna Baynard**, AI Governance & Security Researcher · AIGP · ISC² CC · WGU Cybersecurity. Background in healthcare payer operations, identity-verification workflows and regulated-data environments; NHID-Clinical grew out of the impersonation-latency problem seen firsthand on live eligibility, claims and prior-authorization lines. Maintained as an open reference implementation for technical review; criticism is welcome.

[LinkedIn](https://www.linkedin.com/in/brianna-baynard) · [X @baynardmalone](https://x.com/baynardmalone) · [X @NHIDClinical](https://x.com/NHIDClinical) · [NIST public comment](https://www.regulations.gov/comment/NIST-2025-0035-0026)

<br clear="left"/>

## License

| Part | License | What it covers |
|---|---|---|
| **Software** | [Apache-2.0](LICENSE) | `src/`, `adapters/`, `scripts/`, `tests/`, `tools/`, `functions/`, `middleware/`, `simulator/`, top-level Python modules |
| **Specification & docs** | [CC BY 4.0](LICENSE-DOCS) | `docs/`, `specs/`, `schema/`, conformance suite definitions, `content/`, website pages |

Code is Apache-2.0 rather than Creative Commons because CC licenses carry no patent grant and no warranty disclaimer written for software. See [NOTICE](NOTICE).

<div align="center">
  <sub>Code Apache-2.0 · Spec &amp; docs CC BY 4.0 · Brianna Baynard · <a href="https://www.regulations.gov/comment/NIST-2025-0035-0026">NIST-2025-0035-0026</a> · <a href="https://nhid-clinical.org">nhid-clinical.org</a></sub>
</div>
