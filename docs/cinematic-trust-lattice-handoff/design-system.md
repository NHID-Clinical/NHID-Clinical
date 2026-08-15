# Cinematic Trust Lattice Design System

## 1. Intent

The system should make NHID Clinical feel like **serious, inspectable trust infrastructure** for healthcare AI. It must be more memorable and cinematic than the present Swiss-clinical layer without becoming cyberpunk, surveillance-themed, generic enterprise SaaS, a medical device, or a false marker of certification.

The visual premise is a **Trust Lattice**: a restrained three-dimensional stack of transparent planes that represent a conceptual trust pathway. Its labels are always readable text in HTML/SVG: **Disclose, Authorize, Scope, Audit, Observe**. Use it as an explanatory hero visual and architecture motif, not as a decorative background on every route.

> The interface should communicate **verification before data movement**, not “AI magic.”

## 2. Visual rules

| Element | Required treatment | Exclusions |
|---|---|---|
| Overall tone | Midnight-navy command space paired with quiet ice-blue evidence workspaces. | Purple generative-AI gradients, neon overload, generic dark-mode SaaS. |
| Typography | Strong editorial sans for statements; Inter for UI and prose; IBM Plex Mono only for data, IDs, JSON, timestamps and labels. | Full-page monospace; handwriting; tiny low-contrast labels. |
| Geometry | Six-pixel small controls, 10px panels, 14px only for major visualization containers; one-pixel dividers. | Pills as default controls; large bubbly cards; heavy rounded frames. |
| Color | Cobalt for primary action/information, teal for verified/trust evidence, amber for review, red for blocked/failure. | Color-only state indication; green/red-only semantics. |
| Depth | Layer with luminance, border, and sparse 2–8px shadows. | Floating-card carpets; blur-heavy glassmorphism. |
| Motion | 160–220ms deliberate transitions; one optional slow lattice/light-line animation. | Loops that block reading; motion without reduced-motion fallback. |
| Illustration | Trust Lattice, trace lines, small exact technical diagrams, audit envelopes. | Robots, humanoid assistants, brains, stock doctors, patient images, locks-as-decoration. |

## 3. Token layer

Use CSS custom properties. The names below can be introduced in a new file such as `assets/css/cinematic-trust-lattice.css`, loaded after `/nhid-clinical-ui.css` and `/assets/css/premium.css`. Existing token aliases should be retained during migration so legacy pages do not drift.

```css
:root {
  /* Surfaces and ink */
  --ctl-ink-950: #07111f;
  --ctl-ink-900: #0b1d35;
  --ctl-ink-800: #102b48;
  --ctl-text-strong: #10233d;
  --ctl-text: #40536a;
  --ctl-text-muted: #68788d;
  --ctl-paper: #ffffff;
  --ctl-canvas: #f4f8fb;
  --ctl-mist: #eaf3fa;
  --ctl-line: #c8d7e5;

  /* Semantic roles */
  --ctl-cobalt: #1e63db;
  --ctl-cobalt-hover: #164da8;
  --ctl-cobalt-soft: #e8f0ff;
  --ctl-teal: #0b8276;
  --ctl-teal-bright: #55d9cb;
  --ctl-teal-soft: #e4f7f3;
  --ctl-amber: #986600;
  --ctl-amber-soft: #fff5d7;
  --ctl-red: #b42318;
  --ctl-red-soft: #fff0ef;
  --ctl-focus: #0b57d0;

  /* Shape and elevation */
  --ctl-radius-sm: 6px;
  --ctl-radius-md: 10px;
  --ctl-radius-lg: 14px;
  --ctl-shadow-1: 0 2px 8px rgba(16, 35, 61, 0.08);
  --ctl-shadow-2: 0 5px 16px rgba(16, 35, 61, 0.12);
  --ctl-grid-line: rgba(80, 167, 218, 0.10);

  /* Typography and measure */
  --ctl-font-ui: "Inter", system-ui, sans-serif;
  --ctl-font-data: "IBM Plex Mono", ui-monospace, monospace;
  --ctl-prose: 68ch;
  --ctl-container: 1320px;
}

[data-theme="dark"] {
  --ctl-text-strong: #f2f7fc;
  --ctl-text: #c2d0df;
  --ctl-text-muted: #96abc0;
  --ctl-paper: #102038;
  --ctl-canvas: #07111f;
  --ctl-mist: #0d1c30;
  --ctl-line: #29445e;
  --ctl-cobalt: #79b7ff;
  --ctl-cobalt-hover: #afd3ff;
  --ctl-cobalt-soft: #142e51;
  --ctl-teal: #55d9cb;
  --ctl-teal-bright: #75ece0;
  --ctl-teal-soft: #103c3b;
  --ctl-amber: #ffd26c;
  --ctl-amber-soft: #3a2c10;
  --ctl-red: #ffaaa4;
  --ctl-red-soft: #411f25;
  --ctl-focus: #a3caff;
  --ctl-shadow-1: 0 2px 10px rgba(0, 0, 0, 0.24);
  --ctl-shadow-2: 0 6px 20px rgba(0, 0, 0, 0.34);
  --ctl-grid-line: rgba(144, 211, 255, 0.09);
}
```

## 4. Typography

| Role | Family | Size / line-height | Use |
|---|---|---:|---|
| Display statement | Inter, 700–800 | `clamp(2.5rem, 5.25vw, 4.9rem) / 1.03` | Hero and major page statements only. |
| Page heading | Inter, 700 | `clamp(2rem, 3.2vw, 3.25rem) / 1.08` | Public route headings. |
| Section heading | Inter, 700 | `1.35–1.75rem / 1.18` | Major sections, documents, panels. |
| Body | Inter, 400–500 | `1rem–1.125rem / 1.65–1.8` | Public prose. |
| Metadata | Inter, 600–700 | `0.75–0.88rem / 1.4` | Dates, labels, tags, navbar. |
| Data and code | IBM Plex Mono, 400–600 | `0.75–0.94rem / 1.6` | IDs, traces, JSON, scores, timestamps. |

Do not reproduce the AI-generated mockup text as image text. Use semantically correct HTML headings, paragraphs, links, lists, tables, code blocks, and document metadata.

## 5. Layout model

| Zone | Background | Content behavior |
|---|---|---|
| Status strip | `--ctl-ink-900` | Fixed legal/status boundary; plain language; one dense line that wraps gracefully. |
| Navigation | Transparent/opaque navy in hero or paper on evidence surfaces | Persistent desktop navigation, accessible dropdowns, an explicit mobile drawer. |
| Public hero | `--ctl-ink-950` with a quiet 42px technical grid | Editorial two-column layout with copy on the left and Trust Lattice / route visual on the right. |
| Evidence workspace | `--ctl-canvas` / `--ctl-mist` | Practical table, filters, source controls, short cards; brighter and more readable. |
| Document workspace | Ice-blue side rails + paper document column | Stacked TOC, readable prose measure, semantic callouts and norm blocks. |
| Simulator | `--ctl-ink-950` through `--ctl-ink-800` | Denser app shell, persistent session context, loudest state change is task risk—not decoration. |
| Map | Brighter analysis canvas with dark top bar | Matrix/graph navigation, persistent legend, filter state, explicit label-plus-color encoding. |

## 6. Reusable visual components

| Component | Responsibility | Content / state requirements |
|---|---|---|
| `CtlStatusStrip` | Show framework state and legal boundary | Text only; no implied accreditation. |
| `CtlSiteHeader` | Global navigation and theme control | Semantic nav, dropdown/menu keyboard behavior, current-page indication. |
| `CtlHero` | Public/technical page statement and action hierarchy | Two actions maximum; trust-boundary note; visual has an accessible textual equivalent. |
| `TrustLattice` | Explain the five conceptual trust layers | HTML/SVG labels; provide a list/table alternative; decorative version must be `aria-hidden`. |
| `CtlEvidenceFrame` | Present claim, evidence, limitation and source action | State label + icon + text; no color-only evidence state. |
| `CtlMetricRail` | Show verifiable counts and facts | Values sourced from real content/release metadata; no stale hardcoded result claims. |
| `CtlDocumentShell` | Specification, alignment and developer documentation | Sticky TOC, skip link, full-width tables on small screens with alternate representation. |
| `CtlControlCard` | Describe control/rule/implementation artifact | Control ID in text, short description, source/action link. |
| `CtlStatus` | Verified/review/blocked/complete status | Text, icon/pattern and semantic color. |
| `CtlTracePanel` | Display raw or illustrative evidence data | Keep raw text selectable, scrollable and labelled; hide sensitive implementation tokens. |
| `CtlSimulatorShell` | Maintain simulator session and task context | Must receive state via props; must not own scoring or persistence. |
| `CtlMapMatrix` | Map frameworks to controls | Keyboard navigable cells or accessible tabular equivalent; a persistent textual legend. |

## 7. Interaction and accessibility constraints

All visual implementation must target practical WCAG 2.2 AA behavior. The project should meet or exceed the following rules:

| Requirement | Implementation rule |
|---|---|
| Contrast | Body text meets at least 4.5:1 against its actual background. Large headings and graphical controls are tested separately. |
| Focus | Every keyboard focusable element uses a minimum `3px solid var(--ctl-focus)` outline with a visible offset. Do not use glow-only focus. |
| State | Never encode verified, review, risk, pass or failure solely by hue; include plain-language state plus icon or pattern. |
| Motion | Honor `prefers-reduced-motion`; pause / remove lattice light travel, hover translation, counters and transitions. |
| Touch | Minimum 44×44px actionable target or equivalent padded hit target. |
| Documents | Use actual heading hierarchy, semantic tables, `th`/`scope`, native disclosure elements where appropriate, and copyable code. |
| Diagrams | Pair every essential visual diagram with text/structured data or an accessible SVG description. |
| Simulator | Every timed, drag/drop, colour-coded or audio-style scenario needs a keyboard-operable and non-colour alternative. Timed exercises require a clearly labelled non-timed learning option. |
| Theme | Theme preferences must preserve semantic distinction, legibility, focus and border visibility. |

## 8. Motion rules

Use motion only to explain system behavior:

- A Trust Lattice may animate one token vertically through five layers after it enters the viewport; animation duration should be 2.4–3.2 seconds and run once.
- A trace timeline may reveal real event sequence incrementally only if the full event list remains immediately accessible.
- Buttons may translate one pixel on hover; they should not scale, bounce, pulse or glow as a default affordance.
- Nav transitions, filters, tabs and drawers should take 160–220ms.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
```

## 9. Explicit exclusions

The following are intentionally out of bounds for this redesign: certification seals, “compliant” marketing language not grounded in a real result, green-check-only UI, humanoid AI art, stock clinical photography, decorative locks, generic cloud/brain icons, opaque glass panels with illegible copy, infinite dashboards, decorative gradients, rounded-pill navigation, and pricing/enterprise-product claims beyond present project content.

## 10. CSS migration approach

1. Add `assets/css/cinematic-trust-lattice.css` after current shared styles.
2. Introduce `ctl-*` components/classes and the new token layer without deleting old selectors.
3. Migrate the homepage and one documentation route first.
4. Replace repetitive inline styles as each route is migrated.
5. Once all public pages use the new component boundary, remove obsolete premium overrides only after visual and regression review.
6. Keep simulator-specific CSS in a separate namespace so public-site and operational-console modes do not merge accidentally.
