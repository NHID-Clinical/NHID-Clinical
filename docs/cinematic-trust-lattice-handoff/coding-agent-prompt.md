# Ready-to-Paste Claude Code Prompt

```text
You are implementing the approved whole-ecosystem visual redesign for the NHID Clinical repository. Work in the existing repository architecture and do not replace the static site, simulator logic, content model, APIs, adapters, or test suite with a new framework.

## Required read order

Read these files before editing any implementation file:

1. `docs/cinematic-trust-lattice-handoff/README.md`
2. `docs/cinematic-trust-lattice-handoff/design-system.md`
3. `docs/cinematic-trust-lattice-handoff/app-wide-system.md`
4. `docs/cinematic-trust-lattice-handoff/implementation-spec.md`
5. `docs/cinematic-trust-lattice-handoff/product-triage.md`
6. `docs/cinematic-trust-lattice-handoff/reference/preview-coverage-map.md`
7. Relevant assets in `docs/cinematic-trust-lattice-handoff/reference/previews/`

The current package is the source of truth. `reference/prior-design-recommendation.md` is historical context only and cannot override the current package.

## Goal

Implement the **Cinematic Trust Lattice** visual system across the NHID Clinical public site, Zero Latency simulator, and—only in its own source repository—the AI Governance Map. The public site must feel like precise, inspectable healthcare AI trust infrastructure: midnight-navy editorial heroes, cobalt/teal semantic light, ice-blue evidence workspaces, thin technical grids, high-contrast typography, restrained corners/shadows, and the editable five-layer Trust Lattice signature visual.

## Preserve exactly

Do not change any of the following without a separate explicit request:

- Existing open-framework, voluntary, practitioner-led, non-certification, and non-regulatory positioning.
- Existing policy/specification language, including IDG-01, PDX-01, DBC-01, EIT-01, ATR-01, CAS and all normative text.
- Existing URLs, internal links, API behavior, simulator query parameters, conformance logic, scores, test behavior, adapters, storage and analytics behavior.
- Existing dark-mode preference persistence.
- Existing content and factual claims unless you find an obvious layout-only error; do not invent claims, test counts, integrations, certifications, live monitoring, customers, or data.

The reference images define hierarchy, composition and style—not literal UI text, feature scope, API responses, data, or legal claims. Do not ship AI-generated visual text inside raster screenshot images.

## Implement in this order

### 1. Foundation

- Create `assets/css/cinematic-trust-lattice.css`, loaded after the current shared CSS.
- Implement all `--ctl-*` design tokens, light/dark variants, typography, buttons, focus, semantic states, technical grid background, responsive rules and reduced-motion fallback from `design-system.md`.
- Keep existing legacy CSS compatible during migration. Use `ctl-*` public classes and `zls-*` simulator classes to avoid indiscriminate overrides.
- Build an editable accessible `assets/diagrams/trust-lattice.svg` or equivalent semantic HTML/CSS component. It must include a `title`, `desc`, text labels, and a text/list fallback for essential information.
- Add/retain a skip link and make global nav/menu keyboard accessible.

### 2. Homepage and high-value public journey

- Migrate `index.html`, then framework, payer, shadow-evaluation and evidence routes using previews 00–04 and the route rules in `app-wide-system.md`.
- Use semantic HTML elements and shared CSS classes. Use one or two actions in a hero; never default to rounded pill controls.
- Preserve the public boundary note and open-vs-operated distinction.
- Do not hard-code test counts unless the existing repository exposes an authoritative source. If not, phrase the metric as a dated/sourced artifact or leave it out.

### 3. Documentation and technical routes

- Migrate specification, regulatory alignment, technical stack, interoperability, developer and docs routes using previews 05–07.
- Build/use a document shell with sticky TOC, readable prose width, source/context rail and selectable code panels.
- Keep every visible “mapped to” statement precise. Never change it to “certified”, “approved” or “compliant” unless the repository already establishes that claim in approved text.

### 4. Public ecosystem and roadmap

- Migrate roadmap, news, about and community with the shared public shell. Use preview 08 for roadmap and the route treatment in `app-wide-system.md` for the ecosystem pages.
- Verify canonical/working Community URL behavior before changing links or redirects.

### 5. Simulator

- Implement the Zero Latency shell with a separate `zls-*` namespace using previews 09–10.
- Presentation components receive existing simulator data/state/callbacks. They must not calculate score, own timers, write records, alter persistence, or replace module logic.
- Every status includes icon/pattern, color and text.
- Provide a discoverable keyboard-operable alternative to drag/drop and a non-timed learning path for timed interactions, without silently changing baseline assessment/scoring semantics.
- Simulator Record is a training/evidence document and must never look like a certificate, credential, badge or performance attestation.

### 6. Governance Map

- Do not change the separately deployed AI Governance Map from this repository unless you locate and enter its real source project.
- When working in that project, use the token roles and analytic map rules from the handoff. Preserve all existing map logic/data/filter behavior. Include an accessible text legend and matrix/detail fallback.

## Accessibility requirements

- All normal body text meets 4.5:1 contrast against its actual background.
- Every interactive item has a prominent `3px` visible focus outline with offset, not glow-only focus.
- No information is color-only.
- Semantic HTML, headings, landmarks, native controls, labelled forms, tables and selectable code are required.
- All essential diagrams have text/structured alternatives.
- Respect `prefers-reduced-motion` and current light/dark theme behavior.
- Verify 200% zoom and a narrow mobile viewport with no loss of primary content.
- Keep all interactive content available with JavaScript disabled where progressive enhancement is appropriate.

## Explicit exclusions

Do not add humanoid AI art, stock healthcare photography, fake security shields, certification badges, decorative locks, purple/fuchsia AI gradients, generic SaaS card grids, infinite dashboard widgets, a new frontend framework, authentication, data ingestion, analytics, backend calls, real PHI, new legal claims, or a pricing/commerce experience.

## Required validation before reporting completion

1. Read `README.md` / package precedence one more time and inspect `git diff` for scope drift.
2. Run all documented relevant repository checks: lint, type check, tests, content checks and build. Do not invent commands—read package scripts/Makefile/README first.
3. Run existing tests before and after migrating simulator behavior.
4. Manually inspect every migrated route in light and dark themes at desktop and mobile widths.
5. Keyboard-test skip link, nav menus, theme toggle, all primary actions, TOC, tabs/disclosures, filters and simulator actions.
6. Verify reduced-motion behavior and no-color-only statuses.
7. Confirm preview screenshot assets are reference-only and not replacing semantic UI content.

## Final implementation report

Report in this exact structure:

1. **Scope completed** — routes and components migrated.
2. **Changed files** — each file and a one-line purpose.
3. **Preserved behavior** — links, state/data boundaries, policy/spec claims and simulator logic retained.
4. **Component APIs** — reusable public/simulator/map primitives and inputs.
5. **Validation** — commands run with literal pass/fail results; manual route and accessibility checks performed.
6. **Known risks or follow-ups** — including unavailable preview assets, real content/data validation needs, canonical route decisions, or unimplemented map source.
7. **Diff summary** — confirm no unrelated modifications are included.

Do not claim a check was run if it was not run. Do not claim certification, regulatory alignment, security, privacy, accessibility, or product behavior beyond the evidence available in the repository.
```
