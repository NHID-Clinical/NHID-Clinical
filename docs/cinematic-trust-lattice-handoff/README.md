# NHID Clinical — Cinematic Trust Lattice Redesign Handoff

> **Status:** This is the current source of truth for the visual redesign direction requested by the project owner. It applies to the full NHID Clinical public ecosystem, the Zero Latency simulator, and the AI Governance Map visual extension. It is an implementation handoff, **not** a request to alter policy logic, test behavior, claims, compliance position, or production integrations.

## Read this first

Claude Code must read the files in this order before changing implementation files:

1. [`design-system.md`](design-system.md) — required visual language, tokens, accessibility rules, and exclusions.
2. [`app-wide-system.md`](app-wide-system.md) — route-by-route treatment and reusable component boundaries.
3. [`implementation-spec.md`](implementation-spec.md) — architecture, state boundaries, acceptance criteria, failure handling, and test hooks.
4. [`product-triage.md`](product-triage.md) — sequencing and work that is intentionally deferred.
5. [`coding-agent-prompt.md`](coding-agent-prompt.md) — ready-to-paste execution instructions.
6. [`reference/preview-coverage-map.md`](reference/preview-coverage-map.md) — how the supplied URLs map to previews.
7. [`reference/previews/`](reference/previews/) — visual evidence and composition reference.

The older [`reference/prior-design-recommendation.md`](reference/prior-design-recommendation.md) is **historical context only**. If it conflicts with this package, this package takes precedence.

## Design decision

The approved visual direction is **Cinematic Trust Lattice**.

The public site should feel like **critical trust infrastructure for healthcare AI**: precise, consequential, evidence-led, editorial, and technically inspectable. Its hero uses a midnight-navy control space with a luminous five-layer Trust Lattice: **Disclose → Authorize → Scope → Audit → Observe**. This is a visual metaphor, not a literal system diagram and not a new product claim.

The simulator is a related but deliberately more operational **Zero Latency command surface**. It retains dark, compact, task-focused instrumentation. The AI Governance Map is a brighter analysis workspace that uses the same semantic colors, terminology, and visual precision without using a terminal-only aesthetic.

## Saved visual previews

The following completed, approved-for-reference images are saved locally in [`reference/previews/`](reference/previews/). They are creative direction references only; all production content must be rendered in semantic HTML/CSS/SVG, not embedded as screenshot text.

| File | Route family represented | Purpose |
|---|---|---|
| `00-homepage-hero.png` | Homepage | Flagship hero with Trust Lattice visual and metric rail. |
| `01-framework-landing.png` | Framework, About, News, Community | Public framework narrative and open-artifacts treatment. |
| `02-for-payers.png` | For Payers | Executive decision and shadow-evaluation entry point. |
| `03-shadow-evaluation-guide.png` | Shadow Evaluation Guide | Operational 90-day evaluation journey. |
| `04-evidence-center.png` | Evidence Pack | Trace-backed evidence workspace. |
| `05-specification-regulatory.png` | Specification, Regulatory Alignment | Documentation and alignment workspace. |
| `06-technical-stack-interoperability.png` | Technical Stack, Interoperability | Five-layer architecture and integration pathway. |
| `07-developer-portal.png` | Developers | Quickstart, API documentation, and implementation readiness. |
| `08-roadmap.png` | Roadmap | Public commitments, phases, and explicit boundaries. |
| `09-simulator-briefing.png` | Simulator entry, Module 1 | Training scenario briefing and timeline interaction. |
| `10-simulator-validation.png` | Simulator Modules 2–4 | Passport inspection, triage, and deployment safeguards. |

Four planned supporting visuals could not be rendered because the daily image-generation quota was reached: **Simulator Command Center / Knowledge Base, AI Governance Map, Community-News-About hub, and Simulator Record**. They remain fully specified in [`app-wide-system.md`](app-wide-system.md) and must be implemented as semantic UI using the shared system; they do not block implementation.

## Repository baseline observed for this handoff

| Area | Verified baseline |
|---|---|
| Repository | `NHID-Clinical/NHID-Clinical` |
| Baseline branch | `main` |
| Baseline commit | `35defe2` — `Fix Tonic corpus evaluation: IDG-01 false positives and EIT-01 non-detection (#367)` |
| Homepage implementation | Static `index.html` with `/nhid-clinical-ui.css` and `/assets/css/premium.css` |
| Shared visual primitives | Existing Inter, Raleway, and IBM Plex Mono fonts; light/dark theme via `data-theme` |
| Core product constraints | Preserve existing specification language, open-framework positioning, not-certification boundary, simulator behavior, conformance logic, tests, and integration behavior |

## Non-negotiable preservation requirements

Implementation must preserve the following unless a separate, explicit change request is approved:

| Preserve | Reason |
|---|---|
| The voluntary, open, practitioner-led, non-certification and non-regulatory positioning | This is core legal and product-boundary content. |
| Existing specification/control names, including IDG-01, PDX-01, DBC-01, EIT-01, ATR-01, and CAS | These are referenced by documentation, tests, simulator content, and evidence artifacts. |
| Existing URLs, internal links, static-file behavior, simulator parameters, APIs, adapters, and test harnesses | This package changes presentation, not data, routing, or product logic. |
| Semantic HTML, access to source artifacts, and textual alternatives | Screenshots are direction only and may not replace accessible interface content. |
| The current light/dark theme preference and reduced-motion support | Extend them; do not remove them. |

## Implementation boundary

The target is a **visual-system rebuild** over the existing architecture. Claude Code should create reusable presentation components and CSS primitives, migrate pages incrementally, and keep business logic separate. It must not introduce a visual change that implies certification, compliance approval, live production verification, real-time monitoring, patient data access, or a live integration where none exists.

## Definition of done

The redesign is ready for review only when each applicable route renders with the common visual system; all existing links and interactive behaviors work; public and simulator modes remain distinct; mobile/dark/reduced-motion states are complete; no essential information is trapped in raster assets; and existing repository checks pass or any pre-existing failures are clearly reported.

## References

The source pages and assets are in this repository. This handoff is grounded in the existing `index.html`, `nhid-clinical-ui.css`, `assets/css/premium.css`, and the public route inventory reviewed during the design assessment.
