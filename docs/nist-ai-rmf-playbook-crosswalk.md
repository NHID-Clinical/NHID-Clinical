# NHID-Clinical — NIST AI RMF Playbook Crosswalk

**Status:** subcategory-level crosswalk · **Prepared:** 2026-10-15 · CC BY 4.0

> Written for a governance, risk or compliance reader at a payer, TPA or provider
> organization who is asking one question: *does NHID-Clinical evidence help with
> our own NIST AI RMF program, and where exactly?* The answer is subcategory by
> subcategory below. **Mapped, not certified.** Nothing here is a compliance
> determination, a certification, or a statement that any organization meets
> any AI RMF outcome. Claim discipline follows
> [claim-boundaries.md](claim-boundaries.md) and [terminology.md](terminology.md).

---

## What the Playbook is, and what this crosswalk is

The **NIST AI RMF Playbook** provides suggested actions for achieving the
outcomes in the AI RMF 1.0 Core — 72 subcategories across the Govern, Map,
Measure and Manage functions. NIST is explicit about its standing: "The Playbook
is neither a checklist nor set of steps to be followed in its entirety."
Playbook suggestions are voluntary, and organizations borrow as many or as few
as apply to their use case.

This crosswalk maps NHID-Clinical artifacts — controls, documents, test
material and tooling in this repository — to the subcategories where they are
**evidence toward** an outcome *for the deploying organization*. Three things
follow from that framing:

1. **The outcomes belong to the deploying organization, not to NHID-Clinical.**
   An AI RMF outcome is achieved (or not) by the organization that designs,
   deploys or uses an AI system. NHID-Clinical can supply evidence an
   organization cites in its own program; it cannot achieve an outcome on
   anyone's behalf.
2. **NHID-Clinical is scoped to one interaction class.** It evaluates observable
   conduct on B2B healthcare administrative voice calls — disclosure,
   sequencing of protected-data requests, claims of human status, escalation,
   and the audit record — in either call direction
   ([payer-initiated-calls.md](payer-initiated-calls.md)). It does not govern
   the AI model, its accuracy, fairness, or clinical safety
   ([scope-boundary-fairness-clinical.md](scope-boundary-fairness-clinical.md)).
   So most of the 72 subcategories are organizational and stay entirely with
   the deployer; they are listed in [Out of scope](#out-of-scope) so the gap
   is visible rather than implied away.
3. **"Deploying organization" covers two positions.** (a) An organization that
   puts an AI voice agent on these calls, directly or through a vendor: NHID
   evidence describes *its* agent's conduct. (b) An organization that
   *receives* such calls — typically a payer — and treats the counterparty's
   agent as a third-party AI system: NHID evidence is a way to evaluate that
   agent from its call records without access to its model. Rows that apply
   mainly to (b) are the third-party rows (GOVERN 6.x, MAP 4.x, MANAGE 3.1).

**Strength key**

| Strength | Meaning |
| :-- | :-- |
| **Direct** | The control's output is evidence of the outcome itself, for the voice-call channel. |
| **Partial** | The artifact covers part of the outcome; the rest is the deployer's. |
| **Supporting** | An input the deployer can use while achieving the outcome; it does not cover the outcome by itself. |

The figures NHID-Clinical publishes are self-measured, mostly over synthetic or
authored corpora, and there are no production deployments or independent
validations to cite ([project-state.md §8](project-state.md)). This crosswalk
deliberately states no test counts or detection rates; where a figure is needed,
read it from its source of truth with its corpus and denominator attached.

---

## Main crosswalk

Only subcategories where an NHID-Clinical artifact genuinely contributes. The
"official outcome" column is a short paraphrase; the exact NIST wording is in
the Playbook. "Control" means one of the v1.3 controls — IDG-01, PDX-01,
DBC-01, EIT-01, ATR-01 — or the opt-in DLG-01; the
[Enforcement Profile](enforcement-profile.md) is a documented layer over those
controls, not a control.

### GOVERN

| Subcategory | Official outcome (paraphrase) | NHID control / artifact | What the evidence shows | Strength | What the deploying organization still has to do |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **GOVERN 1.4** | The risk-management process and its outcomes are established through transparent policies, procedures and controls based on organizational risk priorities. | IDG-01 (`src/nhid_policy_engine_v1.py`); normative control text in [technical spec §2](nhid-clinical-technical-specification.md) and `specification.html` | One suggested action is to establish policies on public disclosure of the use of AI. IDG-01 records, per call, whether the agent stated it is an automated system before protected data was requested, and the specification gives control text an organization can adopt as a written procedure. | Supporting | Write and own the policy. Decide the rest of the documentation policy (business justification, training data, algorithmic methodology, and so on) — NHID covers only disclosure of AI use on the call. |
| **GOVERN 4.3** | Organizational practices enable AI testing, identification of incidents, and information sharing. | Conformance Test Suite (`conformance/nhid_conformance_test_suite_v1.yaml`, `src/cts_runner.py`); deterministic engine; evidence pack (`scripts/export_evidence_pack.py`) | A runnable, deterministic test harness for disclosure, sequencing, human-status claims, escalation and audit conduct. Per-call violation records identify one class of candidate incident (misdisclosure, data requested before disclosure). The evidence pack is a reproducible bundle that can be shared, and it marks anything it could not generate as unavailable. | Supporting | Set the testing policy, incident definitions, incident-handling procedure and information-sharing policy. Decide who receives shared material. |
| **GOVERN 6.1** | Policies and procedures address AI risks from third-party entities, including infringement of third-party rights. | [Vendor Trust Questionnaire](vendor-trust-questionnaire.md); receiver-side conformance check on a vendor's own call transcripts | The questionnaire supplies procurement questions on the vendor agent's disclosure, data gating, escalation, key management and audit, and asks for testing against the vendor's actual traffic — two of the policy topics the Playbook lists (transparency into third-party system functions; thorough testing of third-party AI systems). | Supporting | Adopt the policy. Cover intellectual property, training data, supply chain and contract terms, none of which NHID addresses. The questionnaire is a procurement aid, not a certification. |
| **GOVERN 6.2** | Contingency processes handle failures or incidents in high-risk third-party data or AI systems. | Questionnaire §9 (incident response and revocation) and §10.3 (behavior under partial outage); NHID-Auth v2 revocation (`nhid_event_store.record_revocation` / `is_delegation_revoked`) | Questions that test whether one non-conformant agent can be disabled without taking down all traffic, and whether the vendor fails closed. Where a deployment uses NHID-Auth v2, a revoked delegation stays revoked across restarts within that deployment. | Supporting | Write the contingency and redundancy plan. Revocation does **not** propagate across organizations, and DLG-01 is opt-in. |

### MAP

| Subcategory | Official outcome (paraphrase) | NHID control / artifact | What the evidence shows | Strength | What the deploying organization still has to do |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **MAP 1.1** | Intended purposes, beneficial uses, context-specific laws, norms and expectations, and deployment settings are understood and documented, including users, impacts and assumed limitations. | [Scope boundary](scope-boundary-fairness-clinical.md); [technical spec §1](nhid-clinical-technical-specification.md); [payer-initiated calls](payer-initiated-calls.md); `regulatory-alignment.html` | Documents the interaction class NHID-Clinical governs (B2B administrative voice calls between providers or their vendors and payers, in both call directions), the counterparty's expectation of knowing it is talking to an AI system, the regulatory drivers that bear on it, and what is out of scope. | Supporting | Document the agent's own purpose, business use, users, impacts and non-AI alternatives. NHID's scope statement describes the governance layer, not the deployer's AI system. The regulatory page is a reference, not legal advice. |
| **MAP 2.2** | The system's knowledge limits and how its output may be used and overseen by humans are documented well enough to support informed decisions. | [Enforcement Profile](enforcement-profile.md) receiver obligations; "Limitation" rows in the [Control Decision Table](CONTROL_DECISION_TABLE.md); ASR dependency declaration in the [scope boundary](scope-boundary-fairness-clinical.md) | States how each `PolicyDecision` is meant to be acted on by a receiving system, and what each control cannot see — disclosure adequacy, escalation quality, and anything that was spoken but mis-transcribed. | Supporting | Document the voice agent's own knowledge limits and the settings outside its intended use. NHID documents the limits of its checks, not of the agent. |
| **MAP 3.5** | Processes for human oversight are defined, assessed and documented in line with GOVERN policies. | EIT-01; the `ESCALATE_HUMAN` receiver obligation in the [Enforcement Profile](enforcement-profile.md); DBC-01 review routing (`src/dbc01_review_routing.py`) | EIT-01 assesses, per call, whether a human handoff path existed and whether a request for a human was honored; an "honored" outcome with no timestamp is treated as a claim, not a record, and does not clear the control. DBC-01 findings are routed to a human reviewer rather than resolved automatically. | Partial | Define oversight roles, staffing and training, and what a reviewer does with a finding. EIT-01 does not judge the quality of a handoff or confirm a real human answered. |
| **MAP 4.1** | Approaches for mapping technology and legal risks of components, including third-party data and software, are in place, followed and documented. | Adapter contract ([technical spec §12](nhid-clinical-technical-specification.md); `adapters/`); [FHIR AuditEvent mapping](fhir-auditevent-mapping.md) | Documents how a voice-platform payload is translated into the engine's event contract and which audit fields each adapter must supply, which makes the telephony and transcription components visible as dependencies. | Supporting | Inventory third-party components (voice platform, ASR, model provider); review their contracts, licences, release schedules and support. NHID does not assess them. |
| **MAP 4.2** | Internal risk controls for components of the AI system, including third-party AI technologies, are identified and documented. | IDG-01, PDX-01, DBC-01, EIT-01, ATR-01 and opt-in DLG-01, with pass and fail conditions and stated limitations in the [Control Decision Table](CONTROL_DECISION_TABLE.md); [Vendor Trust Questionnaire](vendor-trust-questionnaire.md) | A documented, testable control set a deployer can apply to a third-party voice agent's observable conduct, each control with its own pass condition and limitation. | Partial | Choose which controls to adopt. Apply procurement, security, privacy and bias review to the vendor's models and data — outside NHID. |

### MEASURE

| Subcategory | Official outcome (paraphrase) | NHID control / artifact | What the evidence shows | Strength | What the deploying organization still has to do |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **MEASURE 1.1** | Measurement approaches and metrics are selected for the most significant mapped risks; risks that will not or cannot be measured are documented. | Impersonation Latency ([terminology.md](terminology.md)); Tier 0 pilot metrics ([pilot kit](pilot-kit/README.md)); [scope boundary](scope-boundary-fairness-clinical.md); [claim boundaries](claim-boundaries.md) | Defines a metric for one named risk — time and turns before non-human disclosure — and states what it does not establish. Documents what is not measured: fairness, clinical safety, ASR accuracy, and ATR-01 under transcript replay. | Partial | Select metrics for the agent's other mapped risks; set acceptable limits and course-correction triggers. |
| **MEASURE 2.1** | Test sets, metrics, and details of the tools used in TEVV are documented. | CTS YAML; test sets `fixtures/fabricate/`, `fixtures/voice-stress/`, `tests/evaluation_corpus_v1.json`, `tests/adversarial_corpus_v1.json`; [Governance Evaluation Corpus report](EVALUATION_CORPUS_REPORT_v1.md); [conformance run record](conformance-run-record.md); [project-state §5](project-state.md) | Test sets, the commands that run them, installed dependencies, and the separation between the evidence bodies are written down; figures are reported per corpus with denominators and never merged. | Partial | Document TEVV for the rest of the agent (task accuracy, robustness). The corpora are synthetic or authored, not the deployer's traffic. |
| **MEASURE 2.3** | Performance or assurance criteria are measured and demonstrated in conditions similar to deployment; measures are documented. | Tier 0 [Shadow Pilot Kit](pilot-kit/README.md) (`nhid pilot`, `src/pilot_measure.py`) | Replays the deployer's own captured call turns through the engine, offline, and reports disclosure timing, pre-disclosure protected-data requests, escalation honor rate, per-control violations and the transcription-attestation split. Synthetic corpora are labelled research components, not operational performance. | Partial | Run the pilot. Fill in what the kit marks "not recorded — fill in" (hand review, false positives, dropped calls). Measure task performance separately. |
| **MEASURE 2.4** | The functionality and behavior of the system and its components are monitored in production. | Pilot kit (batch); `POST /v1/webhooks/call-progress` (`adapters/call_progress_adapter.py`, turn by turn); [metrics and observability](NHID_METRICS_AND_OBSERVABILITY_v1.md) | Mechanisms to evaluate the agent's disclosure, sequencing, human-status claims and escalation behavior on production call records, as a batch or per turn. | Partial | Operate the monitoring, alerting and comparison against pre-deployment results. No production deployment of NHID-Clinical exists to cite. |
| **MEASURE 2.5** | The system is demonstrated to be valid and reliable; limits of generalizability are documented. | Impersonation Latency "does not establish" list ([terminology.md](terminology.md)); ASR dependency ([scope boundary](scope-boundary-fairness-clinical.md)); deterministic engine (same inputs → identical output) | Construct-validity limits of NHID's own metric and its dependence on transcription are documented; determinism makes NHID's results reproducible. | Supporting | Demonstrate the agent itself is valid and reliable for its task. NHID does not, and an audit trail is not validity evidence. |
| **MEASURE 2.7** | Security and resilience are evaluated and documented. | NHID-Auth v2 and DLG-01 (`src/agent_identity.py`, `evaluate_dlg01` in `src/nhid_policy_engine_v1.py`, `tests/test_dlg01_delegated_authority.py`); call-SID binding; evasion corpus (`tests/adversarial_corpus_v1.json`, `scripts/redteam_corpus.py`) | When a deployment opts in, DLG-01 verifies a dual-signed, NPI-bound, scoped, expiring delegation bound to the specific call, against trust anchors the deployer configured; tests cover forged signatures, expiry, revocation, wrong call binding and scope widening. A separate corpus tests the controls' resistance to evasive phrasing. | Partial | Security-test the agent itself (prompt injection, data extraction, infrastructure). Limits that travel with this row: DLG-01 is opt-in; there is no registry or discovery; the NPI is format-validated and bound, not checked against NPPES; revocation does not cross organizations; key custody and rotation are not built. |
| **MEASURE 2.8** | Risks associated with transparency and accountability are examined and documented. | ATR-01 (`src/fhir_audit_emitter.py`, `src/audit_store.py`, [FHIR mapping](fhir-auditevent-mapping.md)); IDG-01; DBC-01; EIT-01 | The first suggested action is to instrument the system with "histories, audit logs and other information". ATR-01 requires a machine-readable trace for every interaction, exportable as FHIR R4 `AuditEvent` and persisted in a hash-chained store. IDG-01 and DBC-01 examine, per call, the two transparency risks NHID names — not disclosing, and claiming human or licensed-professional status. EIT-01 records escalations, one of the accountability signals the Playbook asks organizations to track. | **Direct** — for the voice-call channel and those named risks | Protect the trace (it may contain PHI), decide who reviews it, and track the organizational side — roles, committees, go/no-go decisions — which NHID does not touch. |
| **MEASURE 2.9** | The model is explained, validated and documented, and output is interpreted in context to inform responsible use. | `PolicyDecision` (`action`, `reason_code`, `violations[]`) from a rule-based evaluator | Every NHID finding about the agent's conduct carries a stable reason code and the rule that produced it. | Supporting | Explain the agent's model — out of NHID scope. NHID explains its own findings, not the agent's outputs. |
| **MEASURE 2.10** | Privacy risk is examined and documented. | PDX-01; DLG-01 scope constraint on PDX-01 (`PDX01_SCOPE_NOT_AUTHORIZED`) | Records whether protected data was requested before disclosure, or outside a verified delegation scope — one privacy-relevant sequencing risk. Detection is lexical plus one structural rule. | Supporting | Everything else: data minimization, retention, de-identification, HIPAA analysis, and protection of the ATR-01 trace, which may itself contain PHI. |
| **MEASURE 2.13** | The effectiveness of the TEVV metrics and processes in use is evaluated and documented. | [Claims register](claims-register.md); "Not detected" and "False positives" sections of the [corpus report](EVALUATION_CORPUS_REPORT_v1.md); [governance-corpus-remediation.md](governance-corpus-remediation.md); DBC-01 phrase-candidate measurement (`scripts/mine_heuristic_candidate.py`); baseline guard (`scripts/check_baseline.py`) | Documents where NHID's checks miss or over-fire, why some heuristic expansions were rejected, and how CI stops published figures drifting from what the code produces. | Partial | Evaluate the metrics' effectiveness on the deployer's own traffic. All NHID figures are self-measured; none is independently validated. |
| **MEASURE 3.1** | Approaches, personnel and documentation are in place to identify and track existing, unanticipated and emergent risks from intended versus actual performance. | Pilot kit metrics; canonical failure traces (`traces/`) | A repeatable measurement of one known risk on real traffic, and documented examples of how specific failures surface in the record. | Supporting | Personnel, cadence, error-response tracking and emergent-risk identification. |
| **MEASURE 3.3** | Feedback processes let end users and impacted communities report problems and appeal outcomes, integrated into evaluation metrics. | EIT-01; escalation honor rate in the pilot kit | The person on the call can ask for a human, and whether that was honored is recorded and reported as a metric. That is in-call recourse — not a problem-report or appeal process. | Supporting | Build the report-and-appeal channel (see [Gaps](#gaps-nhid-clinical-could-close)). |

### MANAGE

| Subcategory | Official outcome (paraphrase) | NHID control / artifact | What the evidence shows | Strength | What the deploying organization still has to do |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **MANAGE 2.3** | Procedures are followed to respond to and recover from a previously unknown risk once identified. | "When a new phrase candidate shows up during review" in the [DBC-01 human-review SOP](dbc01-human-review-sop.md); `scripts/mine_heuristic_candidate.py`; `src/dbc01_review_routing.py` | A documented procedure for newly observed impersonation phrasing: measure the candidate against the corpus first, merge only with no measured false positives and a regression test, otherwise keep it in human review. | Supporting | Own incident response and recovery; the SOP itself leaves the organization's incident process to the deployer. Where the SOP's routing criteria and `src/dbc01_review_routing.py` differ, the code is current (see [Gaps](#gaps-nhid-clinical-could-close)). |
| **MANAGE 2.4** | Mechanisms are in place and responsibilities assigned to supersede, disengage or deactivate systems whose performance is inconsistent with intended use. | [Enforcement Profile](enforcement-profile.md) (`DENY_DATA`, `ESCALATE_HUMAN`, the Enforcement Ladder); NHID-Auth v2 revocation; questionnaire §9.1; ATR-01 record preservation | Per turn, the engine names one receiver action, most protective first. A revoked delegation stops verifying within the deployment. The questionnaire asks whether a single agent can be disabled. The audit record preserves material for later review. | Partial | Assign who disengages a vendor or agent and on what thresholds, and actually execute the actions — in a Tier 0 shadow pilot they are logged, not enforced. |
| **MANAGE 3.1** | Risks and benefits from third-party resources are regularly monitored, and risk controls are applied and documented. | Receiver-side evaluation of vendor call records (engine, adapters, pilot kit); [Vendor Trust Questionnaire](vendor-trust-questionnaire.md); evidence pack | Evaluates the counterparty's agent from its observable conduct, without access to its model — the Playbook suggests TEVV for third-party systems that addresses transparency "without exposing proprietary algorithms". | Partial | Set the monitoring cadence, apply risk tolerance, decide on decommissioning, and monitor the vendor's other risks. |
| **MANAGE 4.1** | Post-deployment monitoring plans are implemented, including user input, appeal and override, decommissioning, incident response, recovery and change management. | Pilot-kit evaluation workflow; call-progress webhook; EIT-01 (override to a human for the counterparty); DBC-01 review queue | Supplies monitoring inputs for the call channel and a check that the human on the call can override the agent by asking for a person. | Partial | Write and implement the plan. Appeal, decommissioning, incident response, recovery and change management are the deployer's. |
| **MANAGE 4.3** | Incidents and errors are communicated to relevant AI actors, including affected communities; tracking and response processes are followed and documented. | ATR-01 / FHIR `AuditEvent` record; evidence pack; questionnaire §9.3 | A per-call, machine-readable record of a misdisclosure or a pre-disclosure data request that can be shared with the counterparty; the questionnaire asks a vendor how it notifies counterparties. | Supporting | Define what counts as an incident, who is notified and how, and keep the incident database. NHID has no incident-communication guidance yet (see [Gaps](#gaps-nhid-clinical-could-close)). |

**Totals:** 26 subcategories in this table — Direct 1, Partial 11,
Supporting 14. The remaining 46 are listed under [Out of scope](#out-of-scope).

> **Correction to an earlier mapping.** `regulatory-alignment.html` previously
> mapped GOVERN 1.1 → IDG-01, MANAGE 2.2 → EIT-01 and MEASURE 2.5 → ATR-01.
> Read against the official outcome statements those do not hold: GOVERN 1.1 is
> about legal and regulatory requirements being understood, managed and
> documented; MANAGE 2.2 is about mechanisms to sustain the value of deployed AI
> systems; MEASURE 2.5 is about demonstrating validity and reliability. This
> crosswalk replaces that table.

---

## Documentation questions NHID evidence can help answer

Each Playbook subcategory ends with "Transparency & Documentation" questions.
These are the ones where an NHID-Clinical artifact gives a deployer something
concrete to point to. Questions are quoted verbatim; several appear under more
than one subcategory, and one place they appear is cited. "Helps answer" means
for the voice-call channel only.

| Playbook question (verbatim) | Subcategory | NHID artifact | What it answers — and what it does not |
| :-- | :-- | :-- | :-- |
| "Did you establish mechanisms that facilitate the AI system’s auditability (e.g. traceability of the development process, the sourcing of training data and the logging of the AI system’s processes, outcomes, positive and negative impact)?" | GOVERN 6.1 | ATR-01 trace; FHIR R4 `AuditEvent` export (`src/fhir_audit_emitter.py`, [mapping](fhir-auditevent-mapping.md)); hash-chained audit store (`src/audit_store.py`) | The logging part, for each call: disclosure, protected-data gate, escalation and call outcome. Not development traceability or training-data sourcing. |
| "Did you ensure that the AI system can be audited by independent third parties?" | GOVERN 6.1 | Evidence pack (`scripts/export_evidence_pack.py`) with re-run commands in its manifest; deterministic engine; CTS | A third party can re-run the same inputs and must get identical findings. It does not mean any third party has audited anything. |
| "How will the results be independently verified?" | MAP 4.1 | Evidence-pack manifest (`REPRODUCTION_COMMANDS`); [conformance run record](conformance-run-record.md) | By re-running the named commands against the same inputs. No independent verification has been performed to date. |
| "To what extent can users or parties affected by the outputs of the AI system test the AI system and provide feedback?" | GOVERN 4.3 | Receiver-side evaluation: the engine, adapters and pilot kit run on the receiving organization's own call records, offline | A payer on the receiving end of an AI caller can test that agent's disclosure and escalation conduct without the vendor's cooperation. Feedback to the vendor is not built in. |
| "What testing, if any, has the entity conducted on the AI system to identify errors and limitations (i.e. manual vs automated, adversarial and stress testing)?" | MEASURE 1.1 | CTS; shadow pilot on the deployer's own traffic; evasion corpus (`tests/adversarial_corpus_v1.json`); `fixtures/voice-stress/` | Automated testing of the agent's disclosure, sequencing, human-status claims and escalation. The adversarial and stress material tests NHID's checks, not the agent's robustness. |
| "To what extent has the entity documented the AI system’s development, testing methodology, metrics, and performance outcomes?" | MEASURE 2.1 | [Pilot report template](pilot-kit/pilot-report-template.md) (filled by `nhid pilot`); [Control Decision Table](CONTROL_DECISION_TABLE.md) | Testing methodology, metrics and outcomes for the disclosure and escalation behavior. Not the agent's development. |
| "To what extent has the entity documented the post-deployment AI system’s testing methodology, metrics, and performance outcomes?" | MANAGE 4.1 | Pilot kit output; [pilot-kit README](pilot-kit/README.md) ("What Tier 0 measures", disclosure timeliness bands) | The post-deployment measurement of one risk, with its method and limits. |
| "What metrics has the entity developed to measure performance of the AI system, including error logging?" | MEASURE 3.1 | Impersonation Latency; first-turn disclosure rate; never-disclosed rate; pre-disclosure protected-data exposure; escalation honor rate; per-control violations; ATR-01 | Metrics for conduct on the call. Not task accuracy. |
| "What justifications, if any, has the entity provided for the assumptions, boundaries, and limitations of the AI system?" | MEASURE 2.4 | [Scope boundary](scope-boundary-fairness-clinical.md); [claim boundaries](claim-boundaries.md); Impersonation Latency definition in [terminology.md](terminology.md) | Justified boundaries and limits for the monitoring layer — including the ASR dependency and what the latency metric does not establish. The agent's own limits stay the deployer's to justify. |
| "Does the AI system provide sufficient information to assist the personnel to make an informed decision and take actions accordingly?" | MAP 2.2 | IDG-01 (the human on the call is told it is an AI system); `PolicyDecision` with a single receiver action and its obligation ([Enforcement Profile](enforcement-profile.md)) | Gives receiving staff and systems one unambiguous action per turn and tells the human counterparty what they are talking to. |
| "What type of information is accessible on the design, operations, and limitations of the AI system to external stakeholders, including end users, consumers, regulators, and individuals impacted by use of the AI system?" | MAP 2.2 | IDG-01 disclosure on the call; evidence pack; public specification and control text | That the caller is an AI system, and — through the evidence pack — what the governance checks found. Not the agent's design. |
| "If a third party created the AI system or some of its components, how will you ensure a level of explainability or interpretability? Is there documentation?" | MANAGE 3.1 | [Vendor Trust Questionnaire](vendor-trust-questionnaire.md); `PolicyDecision.reason_code` and `violations[]` | Explainable findings about the third-party agent's conduct, plus documented vendor answers. Not model explainability. |
| "To what extent has the entity clarified the roles, responsibilities, and delegated authorities to relevant stakeholders?" | MEASURE 2.8 | NHID-Auth v2 delegation and opt-in DLG-01 ([PKI and OAuth2 integration](nhid-auth-pki-and-oauth2-integration.md)) | The delegated authority of the AI agent itself: which provider organization (by NPI) authorized it, for what scope, until when — verified against trust anchors the deployer configured. Personnel roles remain the deployer's. |
| "To what extent does the plan specifically address risks associated with acquisition, procurement of packaged software from vendors, cybersecurity controls, computational infrastructure, data, data science, deployment mechanics, and system failure?" | GOVERN 6.1 | [Vendor Trust Questionnaire](vendor-trust-questionnaire.md) §6–§10 | Procurement questions on key management, call binding, audit, incident response and fail-safe behavior. Not computational infrastructure or data science. |

---

## Out of scope

Subcategories NHID-Clinical does not address. Two different reasons, kept
apart because they mean different things to a reviewer.

**Deliberately excluded by the scope boundary** — NHID-Clinical evaluates
observable conduct at the interaction boundary and never model internals or
model outputs ([scope-boundary-fairness-clinical.md](scope-boundary-fairness-clinical.md),
[positioning.md](positioning.md)).

| Subcategory | Topic | Why NHID does not address it |
| :-- | :-- | :-- |
| MEASURE 2.11 | Fairness and bias | Out of scope by design. `language` and `interpreter_present` are recorded so an organization can stratify its own reporting; NHID computes no subgroup comparison. Its findings also inherit whatever ASR error distribution sits beneath them. |
| MEASURE 2.6 | Safety; failing safely | Clinical safety and validity of outputs are out of scope. The Enforcement Ladder chooses the most data-protective action per turn; that is not a safety demonstration. |
| MEASURE 2.12 | Environmental impact of training and management | No model training or model management. |
| MEASURE 2.2 | Evaluations involving human subjects | A shadow pilot runs on the deployer's own records; human-subject protections, consent and representativeness are the deployer's. |
| MAP 2.1 | The task and the methods (classifier, generative model, etc.) | Model and method choices are not inspected. |
| MAP 2.3 | Scientific integrity and TEVV considerations, including training-data representativeness | Training data and construct validation of the agent are outside the boundary. NHID's own corpora are documented under MEASURE 2.1. |
| MANAGE 3.2 | Monitoring pre-trained models | NHID never sees a model. |

**Organizational — remains the deploying organization's.** These are about the
organization's own structures, decisions and risk posture. NHID-Clinical has no
standing to supply them, and its documents should not be cited as if it did.

| Subcategories | Topic | Note |
| :-- | :-- | :-- |
| GOVERN 1.1 | Legal and regulatory requirements understood, managed and documented | `regulatory-alignment.html` lists drivers relevant to these calls; it is a reference, not legal advice or a legal determination. |
| GOVERN 1.2, 1.3, 1.5, 1.6, 1.7 | Trustworthy-AI policy, risk-tolerance-based process, periodic review, AI inventory, decommissioning | Organizational policy and process. |
| GOVERN 2.1, 2.2, 2.3 | Roles and communication lines, training, executive accountability | Workforce and leadership. NHID-Clinical itself has no institutional governance body behind it ([claim-boundaries.md](claim-boundaries.md)). |
| GOVERN 3.1, 3.2 | Diverse decision-making teams; human-AI configuration roles | Workforce composition and role policy. The Enforcement Profile defines receiver *system* obligations, not human roles. |
| GOVERN 4.1, 4.2 | Safety-first culture; impact assessment | Organizational culture and impact-assessment policy. |
| GOVERN 5.1, 5.2 | Collecting and adjudicating external feedback | No feedback mechanism exists in NHID (see Gaps). |
| MAP 1.2, 1.3, 1.4, 1.5, 1.6 | Interdisciplinary actors, mission, business value, **risk tolerance**, requirements elicitation | The deployer's. NHID control text can be adopted as system requirements, but eliciting requirements and setting risk tolerance are not something NHID can do. |
| MAP 3.1, 3.2, 3.3, 3.4 | Benefits, costs, targeted application scope, operator proficiency | Business and workforce determinations. |
| MAP 5.1, 5.2 | Likelihood and magnitude of impacts; stakeholder engagement | Impact estimation and engagement practice. |
| MEASURE 1.2, 1.3 | Regular reassessment of metrics; independent assessors and affected communities | The deployer's process. Every NHID figure is self-measured, so independent assessment is exactly what NHID cannot supply. |
| MEASURE 3.2, 4.1, 4.2, 4.3 | Risk tracking where measurement is immature; consultation with domain experts and end users; field-data improvement | Deployment-context consultation and field data belong to the deployer. |
| MANAGE 1.1, 1.2, 1.3, 1.4 | Go/no-go, risk prioritization, risk response, residual risk | Decisions only an accountable organization can make. NHID's maturity table ([claim-boundaries.md](claim-boundaries.md)) states its own residual limits; it does not document anyone else's. |
| MANAGE 2.1, 2.2 | Resources and non-AI alternatives; sustaining the value of deployed systems | Business decisions. MANAGE 2.2 was previously mis-mapped to EIT-01. |
| MANAGE 4.2 | Continual-improvement activities and engagement | Organizational practice. |

---

## Gaps NHID-Clinical could close

**Candidate work, not current capability.** Each item names the Playbook hook
that motivates it. None of these exists today, and none should be described as
if it did.

1. **A deployer documentation template keyed to the Playbook questions.** A
   fill-in document that takes each question in the table above and names the
   evidence-pack field or file that answers it, with a "not covered by NHID"
   line where it stops. *Hook:* GOVERN 1.4 ("Establish and regularly review
   documentation policies"); MAP 4.2 ("Supply resources such as model
   documentation templates").
2. **Incident-communication guidance for misdisclosure events.** What a
   receiving or deploying organization records and tells the counterparty when
   IDG-01 or PDX-01 fails on a real call: fields, timing, recipients, and how
   the ATR-01 record is shared without over-sharing PHI. The questionnaire asks
   vendors this question (§9.3); NHID does not yet answer it. *Hook:* MANAGE
   4.3 ("Establish procedures to regularly share information about errors,
   incidents and negative impacts…"; "Maintain a database of reported
   errors…").
3. **A report-and-appeal path for the person on the call.** A way for a payer
   representative to flag a call after the fact ("I think that was an
   undisclosed AI", "I asked for a human and did not get one"), carried as a
   field on the event and counted alongside the engine's findings — so reports
   can be compared with what the engine saw. *Hook:* MEASURE 3.3 ("Measure
   efficacy of end user and operator error reporting processes"); GOVERN 5.1.
4. **Map pilot-kit output fields to monitoring actions.** A short table showing
   which pilot outputs (Impersonation Latency, timeliness bands, escalation
   honor rate, transcription attestation, "not recorded" fields) answer which
   suggested action — for example, comparing pilot results with CTS and corpus
   results answers "Monitor and document how metrics and performance indicators
   observed in production differ from the same metrics collected during
   pre-deployment testing". *Hook:* MEASURE 2.4; MANAGE 4.1.
5. **Deactivation thresholds without a composite score.** Guidance on turning
   per-call findings into vendor- or agent-level bypass and deactivation
   triggers — each control with its own threshold and denominator, never a
   blended number (the composite score was withdrawn and has no successor).
   *Hook:* MANAGE 2.4 ("Regularly review Identify system incident thresholds
   for activating bypass or deactivation responses").
6. **A machine-readable "not measured" statement in the evidence pack.** The
   pack already marks unavailable artifacts; it could also carry the standing
   list of what NHID does not measure (fairness, clinical safety, ASR accuracy,
   ATR-01 under replay) so the limit travels with the evidence. *Hook:* MEASURE
   1.1 ("Document risks or trustworthiness characteristics identified in the
   Map function that will not be measured, including justification for non-
   measurement").
7. **Documentation alignment.** The [DBC-01 human-review SOP](dbc01-human-review-sop.md)
   still lists a composite-score trigger among its routing criteria, and the
   [Enforcement Profile](enforcement-profile.md) still mentions the composite
   score in §10.1–10.3 and Appendix 10.A, although §10.4 marks it withdrawn and
   `src/dbc01_review_routing.py` removed the trigger. Oversight personnel read
   these documents. *Hook:* MAP 3.5 ("Verify that model documents contain
   interpretable descriptions of system mechanisms, enabling oversight personnel
   to make informed, risk-based decisions").

---

## Provenance

Source: NIST *AI RMF Playbook*, suggested actions and Transparency &
Documentation questions for the 72 subcategories of the AI RMF 1.0 Core
(NIST AI 100-1) — <https://airc.nist.gov/airmf-resources/playbook/>. Crosswalk
prepared 2026-10-15 against NHID-Clinical v1.3 as it stands in this repository.
Subcategory statements, suggested actions and documentation questions are
NIST's work and in the public domain; the paraphrases, mappings and strength
ratings are NHID-Clinical's (CC BY 4.0) and are a mapping, not a certification,
an attestation, or a NIST endorsement. NHID-Clinical's submission to docket
NIST-2025-0035 (NIST-2025-0035-0026) is a public comment, not a NIST
endorsement, adoption, or certification.

---

CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 — a public comment, not a
NIST endorsement, adoption, or certification.
