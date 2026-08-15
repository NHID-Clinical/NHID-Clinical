# App-Wide System and Route Treatment

## Coverage rule

This is a whole-ecosystem redesign. Every route must share the same identity, semantic colors, typography roles, focus treatment, and disclosure boundary, but must **not** use the same density or background treatment. The public framework, documents, simulator, and governance map have different jobs.

## Public navigation model

The current grouped structure is sound. Retain it, but restyle it as a precise dark-on-hero / light-on-document navigation system.

| Group | Existing destinations | Implementation treatment |
|---|---|---|
| Framework | Framework overview, Specification, Controls, NHID-Auth, Reference Implementation, Conformance Suite, Technical Stack, Regulatory Alignment | Public architecture/document routes. Use a small down-chevron, keyboardable disclosure, active-route indicator and a two-column mega-panel only if content remains manageable. |
| Platform | TrustLayer overview and related platform pages | Preserve existing routes and claims. Keep visually distinct from the open framework through restrained “operated infrastructure” metadata, never paywall implied framework content. |
| Simulator | Simulator entry | Switch to Zero Latency app mode after the entry page. |
| Docs | Developer guide, API explorer, Interoperability | Documentation/technical shell. |
| Resources | Evidence Pack, Shadow Evaluation Guide, For Payers, Roadmap, FAQ, Governance Map | Evidence and decision-support shell. |
| About | About and GitHub | Public ecosystem shell. |

On mobile, use one scrollable drawer with grouped headings. The active route and expanded group need text/semantic state; do not rely only on the hue change.

## Route-by-route treatment

| Route family | Visual mode | Required modules | Preserve / avoid |
|---|---|---|---|
| `/` | Flagship public hero | Dark Trust Lattice hero, metric rail, public boundary note, framework controls, evidence/API section, open-vs-operated comparison | Preserve current open-framework and TrustLayer distinctions; do not make Trust Lattice a factual architecture assertion. |
| `/framework/` | Framework landing | Public hero, lattice overview, “open artifacts” panel, five-layer explanation, contribution path | Use `01-framework-landing.png` as reference. Reuse source links and current controls. |
| `/news.html` and `/news/` | Editorial updates | Dark compact hero, chronological update rail, artifact labels, source links, release / evidence cards | Do not imitate a social feed or imply activity where no update exists. |
| `/about.html` and `/about/` | Organization narrative | Practitioner-led narrative, project boundary panel, maintainer/contributor section, source/public-record links | Keep independence and non-certification language exact unless separately approved. |
| `/community.html` and `/community/` | Contribution hub | Contribution pathway, open-work items, GitHub discussions/issues links, code of conduct / governance links | Confirm route health and redirect consistency before style changes. |
| `/for-payers.html` | Executive decision brief | Payer hero, 90-day evaluation narrative, three-phase pathway, outcome rail, boundaries | Use `02-for-payers.png`. No ROI claims or regulated-outcome claims without source. |
| `/shadow-evaluation-guide.html` | Operational guide | Guided evaluation hero, vertical 01/02/03 path, sticky period navigation, evidence collection modules, export/download references | Use `03-shadow-evaluation-guide.png`; preserve actual kit contents and duration language. |
| `/evidence-pack.html` | Evidence center | Search/filter rail, claim/evidence/detail composition, trace viewer, limitations, source/download action | Use `04-evidence-center.png`. Use real data or mark all samples “illustrative.” |
| `/specification.html` and `/specs/` | Formal documentation | Metadata hero, sticky TOC, prose column, normative callout, code/evidence block, alignment context rail | Use `05-specification-regulatory.png`. Preserve normative keyword capitalization and source text. |
| `/regulatory-alignment.html` | Standards mapping | Document shell plus “mapped to” matrix, scope/disclaimer banner, source citations | Never say “certified,” “approved,” or “compliant with” unless proven and specifically approved. |
| `/technical-stack.html` | Architecture | Five-layer exploded lattice / accessible SVG, integration pathway, protocol mapping, artifact links | Use `06-technical-stack-interoperability.png`. Explain visuals in text. |
| `/interoperability.html` | Integration evidence | Technical architecture shell, provider-to-payer flow, adapter / standard mapping, runnable example links | Do not manufacture protocol support; source content controls claims. |
| `/developers.html` and `/docs.html` | Developer portal | Documentation nav, quickstart, request/response code, implementation readiness, reference links | Use `07-developer-portal.png`. Code must remain selectable and actual. |
| `/roadmap.html` | Public commitments | Public-roadmap hero, state legend, explicit phase columns, uncertainty / boundary note | Use `08-roadmap.png`; avoid promises and fake completion ticks. |
| `/simulator.html` and `/simulator/` | Simulator entry | Transition from public hero into operational app shell, mission briefing, scenario selection, read rule action | Use `09-simulator-briefing.png`. Preserve query parameters and existing scenario behavior. |
| `Simulator/index.html`, `zero-latency-module1-v2.html` | Simulator briefing / Module 1 | Scenario task prompt, call timeline, visible data gate, paired visual/text status, control reference | Use `09-simulator-briefing.png`. Provide a non-timed option and keyboard instructions. |
| `zero-latency-module2.html` | Passport inspection | Verification artifact inspection, claimed vs verified view, decision actions, control impact rail | Treat passport artifacts as product data; do not fake real cryptographic state. |
| `zero-latency-module3.html` | Compliance triage | Incoming trace, decision desk, explicit mismatch display, structured action options, audit-write acknowledgement | Use `10-simulator-validation.png`. Preserve existing educational scoring and records. |
| `zero-latency-module4.html` | Deployment safeguards | Configuration checks, preview/diff, risk controls, deployment restriction / escalation state | Keyboard alternative to any drag/drop or visual-only placement action is mandatory. |
| `nhid-knowledge-base.html` | Simulator knowledge base | Operational topic search, selected rule explanation, source/related-controls panel, return-to-scenario link | The future Command Center / KB mockup is described in the README pending rendering. |
| `zero-latency-dashboard.html` | Simulator command center | Latency timeline, control posture, module readiness, explain-this-finding knowledge panel | Use public metric semantics but a separate dense app-shell namespace. |
| `simulator-record.html` | Training record | Structured record, replayable training events, training-only boundary, export/review action | Never style as a certificate, badge, accreditation, clinical score, or performance attestation. |
| `https://ai-governance-map.vercel.app/` | Governance map application | Dark top bar, bright analytical matrix, framework filters, legend, selected control detail, source/evidence links | Use the same tokens but preserve the map’s application logic. Implement only in the map project / its deployment repository. |

## Public templates

### 1. Flagship / marketing-information page

Use this sequence:

1. Dark Trust Lattice hero with one central public statement and a maximum of two actions.
2. Small boundary note: voluntary, open, testable, not certification.
3. Ice-blue metric or alignment rail.
4. One main explanatory architecture/evidence block.
5. A practical next step.
6. A citation/artifact/source route.

### 2. Evidence/decision page

Use this sequence:

1. Compact dark title band.
2. One contextual sentence and task-specific action.
3. Brighter structured workspace with filters, sources, and limitations.
4. State labels with text + icon + color.
5. Trace/source/dataset representation.
6. Footnote defining scope and what is not represented.

### 3. Documentation page

Use a sticky left TOC, central paper document area, and optional right context rail. It should prioritize 68ch prose measure, source links, code readability, and text-based tables. Use dark sections only for metadata headers, illustrative code, or contained trace evidence.

### 4. Simulator page

Use an application shell with an always-visible module/session context, current task, visible event stream, clear action surface, and control impact. Visual energy belongs to the event/timeline evidence; static chrome should remain quiet. Simulator presentation components must accept existing state and callbacks; they may not calculate a result, modify persistence, or replace the learning engine.

## Required responsive transformation

| Desktop design | Tablet | Mobile |
|---|---|---|
| Two-column public hero | Art moves below statement with fixed minimum clearance | One column; hero art becomes a short accessible static / non-essential visual block. |
| Three-rail evidence/document workspace | Context rail moves below document | TOC becomes disclosure; filter rail becomes a dialog/drawer; show tables in an accessible detail view. |
| Matrix/grid | Horizontal scrolling only as last resort | Provide row-by-row comparison / selected-item detail fallback. |
| Simulator three-column console | Activity rail collapses to a summary | Task first, details as expandable subsections; action targets retain 44px hit areas. |
| Public navigation | Collapsed groups | One keyboard-operable drawer with explicit group headings. |

## Loading, empty and error states

Every visual mode must include implementation design for state, not only happy paths.

| State | Treatment |
|---|---|
| Loading evidence | Text skeleton blocks plus “Loading evidence…” live status; do not use vague spinners alone. |
| Empty filters | “No matching artifacts” plus clear reset filter action and source context. |
| Missing trace detail | Show “Trace detail unavailable” with the record/source identifier and a recovery action; do not leave blank code panels. |
| Simulator time unavailable | Preserve scenario details; offer non-timed learning path and explanatory notice. |
| Bad API/sample result | Display response category, human-readable explanation, source / request identifier if present, and a recovery action. |
| Missing route | Use a public 404 that links to framework, docs, simulator, evidence pack and GitHub; it must share the visual system. |
| Offline / static fallback | Documentation and static simulator learning content should remain usable without remote visual assets; show an unobtrusive offline state when required. |

## Preview usage rule

The images in `reference/previews/` define **hierarchy, composition, surface treatment, and mood**. They do not authorize the implementation of imaginary controls, numbers, claims, titles, statuses, code, integration support, or policy language. Implement only verified content from the repository or clearly mark content as illustrative.
