# Playbook — source inventory and provenance

Taken before writing, so the Playbook assembles existing canonical material
rather than restating it from memory. Every substantive section of the Playbook
traces to a row here.

| | |
|---|---|
| **Inventory taken at** | `7c6c89d` |
| **Date** | 2026-09-04 |

## What the structure survey changed

The proposed Playbook architecture was treated as something to validate, not an
outline to fill. Three findings:

**Part II does not need writing.** The control model already exists in canonical
form across `CONTROL_DECISION_TABLE.md` (per-control inputs, expected behaviour,
failure behaviour), `enforcement-profile.md` (the `PolicyDecision` contract,
`PolicyAction` vocabulary, enforcement ladder, consequence matrix) and
`NHID_AUDIT_EVENT_SPEC_v1.0.md` (the audit model). The Playbook assembles and
cross-references these; it does not paraphrase them.

**Part III has a duration problem in its source.** `docs/pilot-kit/README.md`
contains a section headed *"30-day pilot plan"*. The approved evaluation decision
forbids a mandatory 30/60/90-day duration. The kit's substance — capture schema,
measurement script, disclosure timeliness bands, what Tier 0 does and does not
measure — is sound and is absorbed. **The calendar is not.** The Playbook
describes an ordered sequence whose stages depend on each other, with no
prescribed length.

**One naming collision, since resolved.** `specs/NHID-Clinical-v2-Technical-Playbook.pdf`
was 722 words about NHID-Auth v2 tech stack and adoption tiers — a different and
much narrower artifact. Two documents called "Playbook" in one `specs/`
directory was a discoverability problem the Playbook could not solve about
itself, so it was raised rather than worked around. **Resolved 2026-09-04** by
renaming it to `specs/NHID-Auth-v2-Technical-Reference.pdf`. Its contents were
deliberately **not** merged into the Playbook: eliminating a name clash is not a
reason to fold one subject into another.

## Sources by Playbook part

### Part I — Executive Brief

| Source | Contributes |
|---|---|
| `docs/executive-brief.md` | What it is, who for, available-today framing |
| `docs/claim-boundaries.md` | In/out of scope, claims to make and avoid, maturity boundaries, standards posture |
| `docs/positioning.md` | Relationship to existing infrastructure |
| `docs/terminology.md` | Preferred vs deprecated terms; the two-layer model |
| `specification.html` | The five canonical controls as published |

### Part II — Framework

| Source | Contributes |
|---|---|
| `docs/CONTROL_DECISION_TABLE.md` | Per-control intent, inputs, expected and failure behaviour, decision matrix, shadow-mode behaviour |
| `docs/enforcement-profile.md` | `PolicyDecision` output contract, `PolicyAction` vocabulary, enforcement ladder, consequence matrix, CAS authority boundary, normative vs reference-implementation split |
| `docs/NHID_AUDIT_EVENT_SPEC_v1.0.md` | Audit event schema, event types, append-only and tamper-evidence requirements, retention |
| `docs/nhid-clinical-technical-specification.md` | Scope, behavioural controls, ATR-01 structure, CTS/determinism, action model, NHID-Auth v2, delegation chain, call binding |
| `docs/terminology.md` | Non-human actor model, interaction boundary, category vocabulary |
| `src/nhid_policy_engine_v1.py` | Ground truth for evaluation logic |

### Part III — Shadow Evaluation

| Source | Contributes |
|---|---|
| `docs/pilot-kit/` | Capture schema, `measure_pilot.py`, disclosure timeliness bands, what Tier 0 measures, schema-to-engine mapping, report template — **excluding the 30-day plan** |
| `shadow-evaluation-guide.html` | Public methodology, the observe-only framing, payer-side sequence |
| `docs/NHID_METRICS_AND_OBSERVABILITY_v1.md` | Metric definitions, dashboards, alert thresholds, export |
| `docs/safety/synthetic-workflow-validation.md` | Workflow taxonomy, scenario coverage, detection rates and limitations |

### Part IV — Implementation

| Source | Contributes |
|---|---|
| `docs/SYSTEM_ARCHITECTURE.md` | Core engine, integration layers, end-to-end data flow, deployment, design principles, file structure |
| `docs/ATR-01-IMPLEMENTATION.md` | Audit trail implementation and event fields |
| `developers.html` | Staged integration, quick start, hosted API, DLG-01 opt-in, adapters, registry |
| `adapters/*_adapter.py` | The verified integration set |
| `docs/DEPLOYMENT-SECURITY-CHECKLIST.md`, `docs/DOCKER-DEPLOYMENT.md` | Deployment considerations and security boundaries |
| `docs/fhir-auditevent-mapping.md` | FHIR R4 AuditEvent emission |

### Part V — Governance, Evidence & Regulatory

| Source | Contributes |
|---|---|
| `docs/conformance-run-record.md` | The conformance figure and how it was produced |
| `docs/governance-corpus-remediation.md` | Governance detection, false-positive methodology, the 8 unexpected detections, G1–G4 |
| `docs/claims-register.md` | Claims taxonomy, regulatory verdicts D1–D3b, prohibited vocabulary |
| `docs/skipped-test-audit.md` | Why the suite executes everything it collects |
| `docs/safety/adversarial-testing-report.md` | Adversarial corpus, case taxonomy, mutation strategies |
| `docs/EVALUATION_CORPUS_REPORT_v1.md` | Generated corpus report |
| `regulatory-alignment.html` + absorbed `alignment/*` | Regulatory mapping |
| `docs/SECURITY.md` | Disclosure policy, security reporting |
| `docs/release-history.md` | Changelog, with its two annotated entries |
| `docs/csa-ai-caiq-summary.md`, `docs/vendor-trust-questionnaire.md` | Third-party assurance framing |
| `docs/ATR-01-TRACEABILITY-MATRIX.html`, `docs/ATR-01-EVIDENCE-VALIDATION-REPORT.html` | **Absorbed** — traceability matrix, gap analysis, evidence reconstruction, integrity validation |

### Appendices

| Source | Contributes |
|---|---|
| `conformance/nhid_conformance_test_suite_v1.yaml` | 18 CTS cases (1 metadata document + 18 case documents) |
| `traces/nhid-trace-*.md` | Ten synthetic failure traces, one per failure mode |
| `docs/pilot-kit/minimal-event-schema.json`, `pilot-report-template.md` | Worksheet and schema |
| `examples/fhir/*.json` | FHIR bundles validated in CI |
| `docs/terminology.md` | Glossary |

## Figures verified for citation

Re-derived at `7c6c89d`, not copied from prose.

| Figure | Value | Source |
|---|---|---|
| Conformance | 1049 collected / executed / passed; 0 failed, skipped, xfailed, xpassed | `conformance-run-record.md`, clean-clone run |
| Governance detection | 29/32 = 90.6% | `scripts/eval_corpus.py` |
| False positives | 0 of 5 compliant scenarios | `scripts/eval_corpus.py` |
| Unexpected detections | 8, on violation scenarios, reported separately | `scripts/eval_corpus.py` |
| Fabricate corpus | 550 conversations, 127 compliant | row count of the CSVs |
| Fabricate detection | IDG-01 70/70 · PDX-01 41/41 · DBC-01 183/200 · EIT-01 169/171 | `scripts/check_baseline.py` |
| Fabricate false positives | 0 · 0 · 5 · 5 of 127 clean | `scripts/confusion_matrix.py` |
| Adversarial corpus | 40 scenarios | `tests/adversarial_corpus_v1.json` |
| CTS cases | 18 | YAML document count, verified |
| Canonical controls | 5 (4 behavioural + ATR-01 audit) | `check_control_set.py` |
| Vendor adapters | 6, of which 5 have hosted routes | `adapters/*_adapter.py` minus internal plumbing |
| Test files | 47 | `tests/test_*.py` |

**A note on the adapter count.** "6 Adapters" appears on published surfaces and
reconciles with neither the 8 files in `adapters/` nor the 5 hosted
`/v1/adapters/*/check` routes. It is correct: `fabricate_adapter.py` and
`call_progress_adapter.py` are internal plumbing rather than vendor
integrations, leaving six vendor adapters, of which `elevenlabs_postcall` has no
hosted route. The distinction is only recorded in a test docstring, which is
why it reads as a discrepancy until you go looking.

## Open items requiring human judgment

| # | Item |
|---|---|
| P1 | ~~Two artifacts named "Playbook" in `specs/`.~~ **Resolved 2026-09-04** — renamed to `NHID-Auth-v2-Technical-Reference.pdf`. **One consequence to note:** the old URL `/specs/NHID-Clinical-v2-Technical-Playbook.pdf` will now 404. A static host cannot redirect a `.pdf` path (an HTML stub served with `application/pdf` does not render), so unlike the retired HTML routes this one cannot be given a redirect. It was linked only from the downloads page internally; any external link to it breaks |
| P2 | ~~`docs/pilot-kit/README.md` contains a "30-day pilot plan" heading.~~ **Resolved 2026-09-04** — replaced with an ordered workflow carrying no required number of days or weeks |
