# NHID-Clinical Site — Design Handoff

> Companion to `docs/design-system-audit.md` (raw extraction). This doc translates that
> extraction into a forward-looking spec. **Correction to brief:** the original ask assumed
> a Next.js/React/Tailwind/shadcn stack. The actual codebase is static HTML (30 pages) +
> one global stylesheet (`nhid-clinical-ui.css`, 3049 lines) + vanilla JS (`site.js`, no
> build step, no `package.json`). Everything below is scoped to that reality — the
> "Frontend Mapping" section gives a CSS-custom-property + BEM-modifier plan, not a
> React/Tailwind one, since introducing those frameworks isn't implied by anything here.

## Overview

**Purpose of UI:** Marketing/documentation site for NHID-Clinical, an open spec for AI
voice-agent disclosure in B2B healthcare payer-provider calls. Pages split into three
families: marketing (index, about, pricing, for-payers), technical reference
(developers, specification, technical-stack, conformance), and interactive tools
(governance-simulator/gov-sim, demo, simulator).

**Core user flow:** Land on `index.html` → orient via global nav (dropdown groups:
Product / Resources / Company, inferred from `.nav-dropdown`) → either read technical
docs or try the live governance simulator / Twilio demo call → search via the
client-side overlay (`Cmd/Ctrl`-free, click-triggered) for any of 13 indexed pages.

## Component Tree (as built, not idealized)

```
<body data-theme="light|dark">
├── .site-header
│   ├── .brand
│   ├── .nav-links / .nav-dropdown (×3, each with .nav-dropdown-trigger + .nav-dropdown-menu)
│   ├── .nav-actions
│   │   ├── .icon-button.search-toggle  → opens .search-overlay
│   │   ├── .icon-button.theme-toggle   → flips [data-theme]
│   │   └── .icon-button.menu-button    → opens #mobile-nav drawer
│   └── .nav-backdrop (click-to-close target)
├── #mobile-nav (.mobile-nav)
│   ├── .mobile-nav-group ×N
│   └── .mobile-nav-footer → .mobile-theme-toggle
├── #search-overlay
│   ├── #search-input
│   └── #search-results → .search-result-item ×N (client-rendered from SEARCH_INDEX)
├── <main> (per-page content)
│   ├── .hero-section → .hero-grid → .hero-copy / .hero-art
│   ├── .page-section ×N
│   ├── card family: .content-card | .card | .pilot-card | .news-card | .community-card
│   │                | .phase-card | .pricing-card  (5 near-duplicate variants — see below)
│   └── badge family: .badge(.badge-green) | .news-badge(.badge-release|.badge-program|.badge-comm)
│                      | .spec-badge(.spec-badge-green) | .stack-layer-badge | .nist-gov-badge
└── .site-footer
```

`window.NHIDDemoStatus` (in `site.js`) is the one stateful UI component: polls
`/v1/demo/call-status` and re-renders a status card with rule-violation badges —
relevant only to `demo.html`.

## Layout System

- No grid framework; layout is per-section flex/grid declared inline in the stylesheet.
- Single mobile breakpoint that matters: **720px** (repeated 3× as a literal — should be
  one `@media` block or a CSS custom property used in a build-time include, since this is
  a no-build site).
- Secondary breakpoints at 800px and 1060px exist but are page-specific, not part of a
  shared system.
- `prefers-reduced-motion: reduce` is honored (good), but only disables 2 selectors —
  most `transition:` declarations elsewhere are not covered.

## Design Tokens (current state → recommended)

| Category | Current | Recommendation |
|---|---|---|
| Color | 9 real tokens in `:root`, but ~80 more colors hardcoded as hex/rgba throughout (incl. an entire untokenized dark-mode palette) | Add `--success`, `--danger`, `--warning` semantic tokens; add `--ink-dark`, `--body-dark`, etc. dark-mode pairs instead of literal hex under `[data-theme="dark"]` |
| Typography | Inter (400–800) + IBM Plex Mono (400–500), ~37 unique font-sizes, no scale | Collapse to a 6–8 step type scale (`--text-xs` … `--text-5xl`) using the existing `clamp()` pattern for the 3 hero/heading sizes |
| Spacing | No scale at all | Introduce `--space-1` (4px) through `--space-12` (96px) on an 4 or 8px base; retrofit incrementally, not a forced rewrite |
| Radius | `--radius` (6px) / `--radius-sm` (3px) defined but used twice; 15+ other hardcoded radii | Standardize on 3 shapes: `--radius-pill` (999px), `--radius-card` (1rem/1.1rem — already the dominant value), `--radius-chip` (0.5rem) |
| Motion | 10 distinct durations, 2 easings | Standardize on `--duration-fast` (150ms), `--duration-base` (240ms), `--duration-slow` (300ms) + the existing `cubic-bezier(0.4,0,0.2,1)` as `--ease-standard` |

## Interaction Design

- **Hover/active:** consistent "lift" pattern — `transform` + `box-shadow` transition on
  cards and primary buttons (`260ms ease` is the dominant value; a few outliers at
  `240ms`/`220ms` should converge on one).
- **Nav dropdown:** click-to-open, click-outside-to-close, single-open-at-a-time
  (closes siblings) — implemented correctly in `site.js` with `aria-expanded` sync.
- **Mobile drawer:** open/close locks `body.style.overflow`, returns focus to the
  trigger button on close (`menuBtn.focus()` in `closeDrawer()`) — correct focus
  management, worth preserving in any rewrite.
- **Micro-interactions:** `pulse-dot` keyframe (likely a "live"/recording indicator) and
  `float-note` (decorative). Both should be added to the `prefers-reduced-motion` block,
  which currently only disables 2 unrelated selectors.

## State Logic

- **Loading:** `NHIDDemoStatus.poll()` shows `"Waiting for a call…"` until the first
  successful response — the only loading state in the codebase.
- **Empty:** search results show `No results for "<query>"` (`.search-empty`) — the only
  empty state implemented.
- **Error:** the demo-status poller silently swallows fetch errors (`.catch(function(){})`)
  with no user-visible error state — a real gap if the backend is ever down during a demo.
- **Edge states:** no other loading/empty/error states found elsewhere in the site (all
  other pages are static content with no async data).

## Accessibility

- **Strong:** nav/dropdown/drawer interactions wire `aria-expanded`, `aria-haspopup`,
  `aria-controls`, `aria-label` correctly (309 `aria-*` attributes across 28 files);
  `Escape` closes both search and mobile drawer; focus returns to trigger on drawer close.
- **Gap — focus visibility:** explicit `:focus`/`:focus-visible`/`outline` rules appear
  only 4 times in the entire 3049-line stylesheet. Recommend a single global
  `:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }` rule as a
  cheap, high-impact fix.
- **Gap — contrast:** not measured in this pass (would require rendering each
  text/background pairing); flag the dark-mode muted text colors (`#728a9e` on
  `#091524`-family backgrounds) as a contrast-ratio check priority given how close the
  hue/lightness are.
- **Gap — reduced motion coverage:** only 2 of the ~28 `transition:` declarations and
  neither `@keyframes` block are covered by `prefers-reduced-motion`.

## Frontend Mapping (for this stack — no framework assumed)

Since there's no build step, "componentizing" means consistent class-naming + token
discipline, not React components:

1. **Tokens first:** extend `:root` in `nhid-clinical-ui.css` with the semantic color,
   spacing, radius, and duration tokens above. Add a parallel `[data-theme="dark"]`
   block that *only* reassigns those same custom properties — delete the scattered
   hardcoded dark hex values once each is migrated.
2. **Card consolidation:** merge `.pilot-card / .news-card / .community-card / .phase-card
   / .pricing-card` into one `.card` base + BEM modifiers (`.card--pilot`, `.card--news`,
   etc.), since the underlying box model (border, radius, shadow, padding) is already
   near-identical across all five.
3. **Badge consolidation:** same treatment — one `.badge` base + `.badge--success`,
   `.badge--release`, `.badge--program` modifiers, replacing the current mixed
   `badge-X` / `X-badge` naming.
4. **Search index:** generate `SEARCH_INDEX` at deploy time from page `<title>`/meta
   description rather than hand-maintaining it in `site.js`, so the 17 un-indexed pages
   (30 HTML files vs. 13 entries) stop silently falling out of search.

## Implementation Notes

- No npm/build tooling exists today — any token refactor should stay plain-CSS
  (custom properties), not introduce a CSS preprocessor or framework as a side effect of
  this cleanup.
- Recommend doing the color/dark-mode tokenization first (highest severity, contained
  blast radius — it's one file) before touching the card/badge class consolidation
  (touches all 30 HTML files' `class=` attributes).
- This handoff and the raw JSON extraction are audit artifacts only — **no CSS/HTML was
  modified in this pass**, per scope.
