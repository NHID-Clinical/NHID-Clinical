# Implementation Specification

## 1. Architecture

The repository is primarily a static-site implementation with shared CSS and page-local HTML/JavaScript. The visual redesign must fit that architecture first. Do not introduce a large client framework, data layer, build system, or hosted service merely to achieve a design treatment.

### Required presentation boundary

Create a shared visual layer that can be consumed by existing static routes:

```text
assets/
  css/
    cinematic-trust-lattice.css     # global tokens, shell, components, responsive rules
  js/
    cinematic-ui.js                 # optional small shared progressive-enhancement helpers
  diagrams/
    trust-lattice.svg               # accessible, production SVG; source text must be editable
  images/
    cinematic/                      # optional non-essential raster art only
```

The style layer must be loaded **after** existing `nhid-clinical-ui.css` and `assets/css/premium.css` during migration. It should use `ctl-*` classes to prevent uncontrolled overrides and retain compatibility aliases for existing variables where necessary.

### Component model for static HTML

Build small class-based / progressively enhanced presentation modules rather than an application framework:

| Module | Suggested selector / file | Inputs | Must not own |
|---|---|---|---|
| Site header | `.ctl-site-header` / `cinematic-ui.js` | Current route, nav items, theme preference | Routing, auth, analytics implementation. |
| Dropdown navigation | `.ctl-nav-menu` | Trigger, menu IDs, keyboard events | Content source / route authorization. |
| Trust Lattice | `.ctl-trust-lattice` / `assets/diagrams/trust-lattice.svg` | Layer labels, optional decorative mode | Product claims or control logic. |
| Public hero | `.ctl-hero` | Eyebrow, title, description, actions, boundary note | URL routing and business decisions. |
| Evidence frame | `.ctl-evidence-frame` | Claim, source, limitation, state | Evidence truth / fetching / scoring logic. |
| Document shell | `.ctl-document-shell` | TOC anchors, main content, context rail | Markdown/specification parsing semantics. |
| Status primitive | `.ctl-status[data-state]` | `verified`, `review`, `blocked`, `pending`, `complete` | Result calculation. |
| Simulator shell | `.zls-shell` | Existing module state and callbacks | Scoring, timer semantics, persistence, telemetry. |
| Matrix / map | `.ctl-map-matrix` | Existing data model and selected item | Filtering/model calculations. |

## 2. Implementation sequence

### Phase A — foundation

1. Add global token / reset / focus / reduced-motion rules to `assets/css/cinematic-trust-lattice.css`.
2. Add semantic shell components: status strip, header, public hero, buttons, evidence cards, metric rail, document shell, status labels.
3. Create `assets/diagrams/trust-lattice.svg` using semantic labels and an accessible `title` / `desc`; it must not be generated raster text.
4. Modify `index.html` to load the new CSS after current CSS and migrate its header, hero, metric rail, controls, evidence callout, and public sections.
5. Verify the new shell in light and dark themes without changing all legacy page selectors yet.

### Phase B — public and document routes

1. Migrate framework landing, payers, shadow evaluation guide, evidence pack, roadmap, about/news/community.
2. Migrate the specification, regulatory alignment, technical stack, interoperability, developers, and docs shells.
3. Replace page-local visual duplication with shared class names only when behavior remains unchanged.
4. Remove inline visual styles only when a route has a matching reusable component/class.

### Phase C — simulator and map

1. Establish a separate `.zls-*` namespace for the simulator. It imports semantic tokens but has its own density, grid, action and trace patterns.
2. Migrate simulator entry and training modules in order, verifying existing state/score rules after each module.
3. Add interactive accessibility alternatives before replacing any existing interaction.
4. Apply the light analytical map treatment in the AI Governance Map’s own codebase/repository. Do not couple the map’s deployment to the static-site project without an explicit integration decision.

### Phase D — cleanup

1. Collapse conflicting legacy visual rules only after each route has visual regression review.
2. Keep a migration changelog noting route, shared classes adopted, old rules removed, and validation result.
3. Do not delete current assets or content until all routes have a replacement and owner review.

## 3. UI implementation details

### Trust Lattice

The lattice is the signature brand artifact. Implement it as an accessible SVG or HTML/CSS composition, not as rasterized mockup text.

```html
<figure class="ctl-trust-lattice" aria-labelledby="trust-lattice-title trust-lattice-desc">
  <svg viewBox="0 0 640 560" role="img">
    <title id="trust-lattice-title">Five-layer conceptual trust lattice</title>
    <desc id="trust-lattice-desc">A conceptual sequence with five layers: disclose, authorize, scope, audit, and observe.</desc>
    <!-- Vector planes, connectors and text labels live here. -->
  </svg>
  <figcaption>
    A conceptual pathway for explaining disclosure, authorization, scope, audit evidence and observability. It is not a certification or a real-time production state diagram.
  </figcaption>
</figure>
```

Use a `prefers-reduced-motion` fallback that disables traveling tokens and opacity pulses. For users who require a concise alternative, render a linked ordered list below the visual.

### Buttons

Use rectangular `6px` radius actions. One primary action per primary section; a maximum of two visual actions in a hero.

```html
<a class="ctl-button ctl-button--primary" href="/framework/">Explore the framework <span aria-hidden="true">→</span></a>
<a class="ctl-button ctl-button--secondary" href="/simulator.html">Run the simulator <span aria-hidden="true">→</span></a>
```

Buttons that trigger in-page content need native `<button type="button">`, `aria-expanded`, `aria-controls`, Escape handling if a popup/modal, focus restoration, and keyboard functionality.

### Status pattern

Do not use only a green tick / amber yellow / red fill. The component always includes explicit text:

```html
<span class="ctl-status" data-state="blocked">
  <svg aria-hidden="true" viewBox="0 0 16 16"><!-- status icon --></svg>
  <span>Data exchange blocked</span>
</span>
```

### Evidence pattern

Use the following hierarchy when presenting a visible claim: **claim → scope → observed/source artifact → status → limitation → next action**. A claim should never appear as an unqualified card title with a green badge.

### Navigation and skip behavior

Place a visible-on-focus skip link before the status strip. Each page needs a stable `main` landmark. Dropdown menus need Arrow Up/Down, Escape, Tab exit behavior and a programmatic focus return to their trigger.

## 4. Event schema and data boundaries

The redesign does not alter existing event schemas. However, when visualizing simulator or conformance data, map presentation to existing fields through an adapter function / rendering helper. Never embed a new invented field inside policy, scoring or persistence code just to satisfy the UI.

| UI concept | Presentation inputs | Existing behavior to preserve |
|---|---|---|
| Event timeline | timestamp, actor, control ID, event type, outcome, source reference | Existing simulation event order and scoring. |
| Control posture | control ID, evaluation result, explanation, next action | Existing pass/fail/risk logic. |
| Trace panel | raw/selectable trace or explicitly marked illustrative fixture | Existing audit envelope generation. |
| Evidence card | claim, artifact ID/link, status, limitation | Existing evidence-pack source truth. |
| Training record | module, task result, timestamp, education summary | Existing record semantics; training only. |
| Governance Map cell | framework, dimension/control, mapping strength, source | Existing map taxonomy and filter behavior. |

All rendering helpers must handle missing optional fields safely and display a text fallback such as “Source reference unavailable” rather than throwing or silently inventing content.

## 5. State machine requirements

### Navigation state

```text
closed → opening → open → closing → closed
```

- Trigger keyboard/click opens a menu.
- Escape, outside click, route change, or focus leaving the contained menu closes it.
- Closed state returns focus to trigger if the close action began inside the menu.
- Mobile drawer locks background scrolling only while open and remains keyboard operable.

### Evidence detail state

```text
idle → loading → ready
                ↘ empty
                ↘ error
```

- `loading` exposes `aria-busy="true"` and text status.
- `empty` tells users that no matching artifact exists and provides a clear reset/filter action.
- `error` provides source/record context and retry/back action.
- `ready` exposes sources, status text, limitation and source action.

### Simulator task state

```text
briefing → active → paused/learning-mode → submitted → feedback → next-task
                           ↘ unavailable/error
```

- Current simulator scoring, timers, state transitions and storage remain source of truth.
- The visual layer receives current state and uses it to decorate layout only.
- A non-timed learning mode is an alternate presentation path; it must not silently modify baseline scoring or assessment semantics.
- Feedback names why an action was correct/incorrect, related control(s), and next action.

### Theme state

```text
system-preference → saved-light | saved-dark | current-render
```

Existing local-storage theme behavior must remain supported. All new tokens must have both light and dark values.

## 6. Failure handling

| Failure | Required behavior |
|---|---|
| CSS fails to load | Existing HTML remains readable and functional; do not move key content into pseudo-elements or background images. |
| Illustration/SVG unavailable | Hero retains title, description and action hierarchy; a concise text list represents the Trust Lattice. |
| JavaScript disabled | Navigation links, document content, simulator instructional information and source artifacts remain accessible. Progressive tabs/menus gracefully expose all content. |
| Trace payload absent | Render a labelled unavailable state and retain action / source context. |
| Filter fetch fails | Announce failure and provide retry/reset path; retain last safe visible state if present. |
| Unsupported browser feature | Use solid backgrounds and borders if `backdrop-filter`, `mask-image`, `color-mix`, or SVG effects are unavailable. |
| Small viewport | Convert rails to disclosures/drawers; avoid fixed-height hero/console panels or horizontal clipping of primary content. |
| User activates reduced motion | Disable nonessential lattice travel, transitions and auto-updating animated counters. |

## 7. Explicit test harness hooks

Do not create a new test suite in this handoff commit. Add or maintain the following hooks when implementation begins:

| Hook | What it verifies |
|---|---|
| `data-testid="ctl-site-header"` | Header remains present across migrated public routes. |
| `data-testid="ctl-skip-link"` | Keyboard user can bypass persistent navigation. |
| `data-testid="ctl-primary-action"` | Hero action URL remains correct. |
| `data-testid="ctl-trust-lattice"` | Lattice has a non-empty accessible name/description or is truly decorative. |
| `data-testid="ctl-status-*"` | State text is rendered alongside semantic visual encoding. |
| `data-testid="ctl-evidence-source"` | Evidence card surfaces a source / unavailable fallback. |
| `data-testid="ctl-simulator-state"` | Simulator shell renders the state supplied by existing logic without recomputing it. |
| `data-testid="ctl-non-timed-mode"` | Alternate simulator path is discoverable where timing exists. |
| `data-testid="ctl-theme-toggle"` | Light/dark preference changes presentation and retains readable text. |
| `data-testid="ctl-map-legend"` | Governance map exposes a text mapping-strength legend. |

Add semantic tests first: heading hierarchy, nav/menu keyboard operation, status labels, focus visibility, light/dark class application, and existing simulator action semantics. Include screenshots only as supplementary visual regression snapshots—not as a substitute for semantic tests.

## 8. Acceptance criteria

A migrated route is acceptable only if all applicable conditions below are true:

1. Existing page content, links, legal positioning, specification language and interactive behavior remain intact.
2. The route applies the token layer and shared components instead of page-local ad hoc styling.
3. Body and metadata text remains readable in light and dark theme, including when zoomed to 200%.
4. Keyboard focus is visible and menu/dialog behavior has appropriate focus management.
5. Essential visual information has a semantic HTML/SVG/text alternative.
6. Motion honors reduced-motion preferences.
7. Mobile layout has no horizontal loss of primary information.
8. Simulator state is presented but not reimplemented in the visual layer.
9. The route visually matches the relevant preview’s hierarchy and tone without copying AI-generated text or invented facts.
10. Repository tests, lint/build commands, and manual-route review have been run and their actual results reported.
