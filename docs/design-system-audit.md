# NHID-Clinical Site — Design System Extraction (Raw JSON)

> Forensic extraction of every design decision found in `nhid-clinical-ui.css` / `site.js` / HTML pages, as they exist today — no judgment, no proposed fixes. See `docs/design-system-handoff.md` for the synthesized recommendations.

```json
{
  "_meta": {
    "project": "NHID-Clinical marketing/docs site",
    "actual_stack": "Static HTML (30 pages) + single global stylesheet (nhid-clinical-ui.css, 3049 lines) + vanilla JS (site.js, no framework, no bundler, no package.json)",
    "note": "The audit brief assumed Next.js/React/Tailwind/shadcn. None of that is present in this repo. This extraction reflects the real stack: hand-written CSS with custom properties, BEM-ish class names, inline SVG icons, data-theme attribute for dark mode."
  },
  "colors": {
    "css_variables_root": {
      "--ink": "#082a5b",
      "--ink-soft": "#334155",
      "--body": "#5d6b7a",
      "--blue": "#0b6ebc",
      "--blue-soft": "#eaf5fb",
      "--teal": "#188eaa",
      "--teal-soft": "#e8f8f4",
      "--line": "rgba(190, 213, 226, 0.78)",
      "--paper": "#ffffff",
      "--mist": "#f8fbfd",
      "--shadow": "0 28px 80px rgba(20, 74, 105, 0.1)",
      "--text (alias)": "var(--ink-soft)",
      "--text-muted (alias)": "var(--body)",
      "--bg (alias)": "var(--mist)",
      "--bg-2 (alias)": "#eaf5fb",
      "--surface (alias)": "var(--paper)",
      "--border (alias)": "var(--line)",
      "--radius": "6px",
      "--radius-sm": "3px"
    },
    "primary": ["#0b6ebc (--blue, links/CTAs)", "#082a5b (--ink, headings)"],
    "secondary": ["#188eaa (--teal)"],
    "neutral": ["#334155 (--ink-soft)", "#5d6b7a (--body)", "#64748b", "#94a3b8", "rgba(190,213,226,0.78) (--line)", "#ffffff (--paper)", "#f8fbfd (--mist)"],
    "semantic": {
      "success_green_NOT_UNIFIED": ["#059669 (8 uses)", "#10a36c (4 uses)"],
      "error_red_NOT_UNIFIED": ["#dc2626 (9 uses)", "#cf222e (1 use, GitHub-red)", "#991b1b (2 uses)"],
      "warning_amber_NOT_TOKENIZED": ["#b45309", "#d4a052", "#8a5b12"],
      "info_blue": ["#0b6ebc", "#0e78a5"]
    },
    "dark_theme_palette_HARDCODED_NOT_VARIABLES": {
      "note": "[data-theme=\"dark\"] overrides use raw hex literals scattered through the file instead of a parallel set of CSS custom properties. No --dark-* tokens exist.",
      "backgrounds": ["#091524", "#0d1d2f", "#0b1e33", "#0c1e30"],
      "text": ["#a0b8d0", "#8aabcc", "#728a9e"],
      "accent_blue": ["#58b4f0", "#7ec8f4"],
      "accent_teal": ["#3ecece"],
      "accent_amber": ["#d4a052"]
    },
    "most_repeated_non_variable_hex_literals": {
      "#dc2626": 9, "#059669": 8, "#091524": 7, "#58b4f0": 5, "#334155": 5,
      "#0f578b": 5, "#5a7a96": 4, "#10a36c": 4, "#0d1d2f": 4
    },
    "opacity_variations": {
      "note": "rgba() alpha channel is used ad hoc — over 60 distinct alpha values found (0.05, 0.06, 0.07, 0.1, 0.12, 0.14, 0.15, 0.2, 0.23, 0.24, 0.28, 0.3, 0.32, 0.35, 0.38, 0.4, 0.42, 0.45, 0.5, 0.52, 0.55, 0.6, 0.62, 0.64, 0.65, 0.66, 0.7, 0.72, 0.74, 0.75, 0.76, 0.78, 0.8, 0.82, 0.84, 0.85, 0.86, 0.88, 0.9, 0.92, 0.96, 0.98 ...). No consistent opacity scale (e.g. 8/16/24/32%)."
    },
    "dark_mode_mapping": "Toggled via [data-theme=\"dark\"] attribute on <html>, set/read via localStorage('nhid-theme') in site.js. Mechanism is sound; token implementation is not (see inconsistencies)."
  },

  "typography": {
    "families": {
      "loaded_via_google_fonts": "Inter:wght@400;500;600;700;800 & IBM Plex Mono:wght@400;500",
      "--display / --font-display": "\"Inter\", system-ui, sans-serif",
      "--sans / --font-body": "\"Inter\", system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif",
      "monospace (code/inline, no variable)": "\"IBM Plex Mono\", \"Fira Code\", \"Courier New\", monospace — only 2 usages in whole file"
    },
    "font_sizes_distinct_values": [
      "0.68rem", "0.7rem", "0.72rem", "0.75rem", "0.77rem", "0.78rem", "0.8rem", "0.82rem",
      "0.83rem", "0.85rem", "0.875rem", "0.87rem", "0.88rem", "0.9rem", "0.92rem", "0.95rem",
      "0.96rem", "0.975rem", "1rem", "1.05rem", "1.08rem", "1.1rem", "1.15rem", "1.2rem",
      "1.25rem", "1.3rem", "1.35rem", "1.65rem", "1.75rem", "2rem", "2.1rem", "2.27rem",
      "clamp(1.15rem, 2vw, 1.35rem)", "clamp(1.35rem, 2.2vw, 2.05rem)", "clamp(1.6rem, 3vw, 2.2rem)",
      "clamp(2.2rem, 5vw, 3.5rem)", "clamp(2.3rem, 4vw, 3.5rem)", "clamp(3.4rem, 8vw, 7.15rem)"
    ],
    "inconsistency_note": "~37 distinct font-size values across the file with no shared scale/variable (no --text-xs/sm/md style tokens) — sizes were hand-tuned per component.",
    "font_weights_used": [500, 600, 700, 800],
    "weight_note": "400 (regular) is never explicitly declared — relies on browser/body default. Bold body copy never uses 400 in this file.",
    "line_heights_distinct_values": [1, 1.05, 1.15, 1.2, 1.22, 1.25, 1.35, 1.45, 1.5, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 0.9],
    "letter_spacing_distinct_values": ["-0.075em", "-0.06em", "-0.055em", "-0.05em", "-0.04em", "-0.035em", "-0.03em", "-0.025em", "-0.02em", "0.01em", "0.04em", "0.06em", "0.08em", "0.1em", "0.16em"],
    "pattern_note": "Tight negative tracking (-0.02 to -0.075em) on large display headings; positive tracking (0.06–0.16em) on small uppercase eyebrow/label/badge text. Pattern is consistent even though no named tokens exist.",
    "text_styles_inferred_combinations": [
      { "name": "hero-display", "evidence": "font-size: clamp(3.4rem,8vw,7.15rem); line-height: 0.9; letter-spacing: -0.075em; weight inferred 700-800" },
      { "name": "section-heading", "evidence": "font-size: clamp(2.2-2.3rem, ~4-5vw, 3.5rem); weight 700-800" },
      { "name": "eyebrow-label", "evidence": "font-size: 0.78rem; letter-spacing: 0.16em; weight 700-800; uppercase (inferred from tracking pattern)" },
      { "name": "body-copy", "evidence": "font-size: 0.875-1rem; line-height: 1.6-1.85" }
    ]
  },

  "spacing_and_layout": {
    "spacing_scale": "No --space-* custom properties exist. Margin/padding values are hand-set per rule (not extracted exhaustively here — would require per-selector parsing beyond regex scope).",
    "border_radius_distinct_values": ["2px", "3px", "4px", "0.25rem", "0.5rem", "0.65rem", "0.75rem", "0.85rem", "1rem", "1.1rem", "1.15rem", "1.32rem", "1.4rem", "1.6rem", "2rem", "50%", "999px (pill)"],
    "radius_token_note": "--radius (6px) and --radius-sm (3px) exist but are only referenced twice in the whole file (lines 1475, 1784); everywhere else radii are hardcoded per-component, producing 15+ distinct values for what is conceptually ~3 shapes (pill, card, chip).",
    "breakpoints": ["max-width: 1060px (line 1965)", "max-width: 800px (line 2466)", "max-width: 720px (lines 2001, 2169, 2702)", "prefers-reduced-motion: reduce (line 2076)"],
    "breakpoint_note": "No named breakpoint variables; 720px is the dominant mobile cutoff but is repeated as a literal 3 separate times.",
    "z_index_layers": {
      "1": "decorative background layer (line 283)",
      "50": "site header (line 89)",
      "150": "mobile nav backdrop (line 829)",
      "200": "mobile nav drawer / search overlay (lines 794, 2841)",
      "9999": "top-level overlay, likely ElevenLabs widget or skip-link (line 3047)"
    },
    "container_widths": "Not captured by regex pass — uses .container class; max-width values embedded in selector bodies not grepped in this pass."
  },

  "components": [
    {
      "name": "icon-button (theme-toggle / search-toggle / search-close / menu-button)",
      "evidence": "21 occurrences each across pages — shared header utility button",
      "variants": ["theme-toggle", "search-toggle", "search-close", "menu-button"],
      "state_logic": "site.js toggles aria-expanded / data-theme / overlay hidden attribute"
    },
    {
      "name": "secondary-button",
      "usage_count_index_html": 9
    },
    {
      "name": "cta-button",
      "usage_count_index_html": 6
    },
    {
      "name": "content-card / card / card-link",
      "usage_count_index_html": "7 + 5 + 6 = 18 combined card-family usages on index.html alone"
    },
    {
      "name": "pilot-card, news-card, community-card, phase-card, pricing-card",
      "note": "5 near-identical page-specific card variants instead of one parameterized .card component — naming suggests copy-pasted per page rather than shared/extended"
    },
    {
      "name": "badge family (badge, badge-green, news-badge, spec-badge, stack-layer-badge, nist-gov-badge)",
      "note": "6+ badge class variants with inconsistent naming convention (badge-X vs X-badge appears both ways: 'badge-release' vs 'news-badge', 'spec-badge-green' vs 'badge-green')"
    },
    {
      "name": "nav / nav-dropdown / mobile-nav",
      "dependencies": "site.js wires aria-haspopup, aria-expanded, click-outside-to-close, Escape-to-close",
      "note": "Well-implemented interaction pattern with real ARIA wiring — one of the stronger parts of the codebase"
    },
    {
      "name": "search-overlay",
      "dependencies": "Hardcoded SEARCH_INDEX array in site.js (13 pages indexed) — not generated from the HTML, will silently drift out of date as pages are added/renamed"
    },
    {
      "name": "NHIDDemoStatus (demo.html live call status widget)",
      "note": "Only genuinely dynamic/stateful component in the JS — polls /v1/demo/call-status and renders badges/log via string-concatenated innerHTML (XSS-safe here only because escapeHtml() is applied to user-influenced fields)"
    }
  ],

  "motion": {
    "transition_durations_found": ["150ms", "0.1s", "0.14s", "0.15s", "0.18s", "220ms", "0.25s", "240ms", "260ms", "300ms"],
    "easing_functions": ["ease (default)", "cubic-bezier(0.4, 0, 0.2, 1)"],
    "duration_note": "10 distinct duration values for what are functionally ~3 interaction types (hover-lift, color/border swap, overlay fade) — no shared --duration-* tokens.",
    "keyframe_animations": ["pulse-dot (line 777) — likely a live/recording indicator", "float-note (line 783) — decorative"],
    "reduced_motion_support": "Present: @media (prefers-reduced-motion: reduce) at line 2076 sets transition: none — good accessibility practice, but only covers 2 selectors.",
    "hover_focus_active_states": "Hover states present on cards/buttons (transform + box-shadow lift pattern, e.g. 'transition: transform 260ms ease, box-shadow 260ms ease'). Explicit :focus/:focus-visible/outline rules found only 4 times in 3049 lines."
  },

  "icons_and_assets": {
    "system": "Inline <svg> per page (17 occurrences on index.html alone) — no icon font, no Lucide/Feather/FontAwesome/Material Icons library detected anywhere in CSS, JS, or HTML",
    "theme_aware_images": ".theme-img-light / .theme-img-dark pairs swapped via JS based on data-theme — used for at least one hero illustration",
    "favicon_logo": "Not captured in this pass (would require inspecting <link rel=icon> tags and /assets directory contents)"
  },

  "inconsistencies": [
    {
      "type": "duplicate-value-should-be-token",
      "description": "#0f578b appears 5 times as a literal hex with no variable; same pattern for #5a7a96 (4x), #10a36c (4x), #0d1d2f (4x).",
      "severity": "medium"
    },
    {
      "type": "conflicting-semantic-color",
      "description": "Two different greens used for 'success' (#059669 and #10a36c) and three different reds for 'error/danger' (#dc2626, #cf222e, #991b1b) with no apparent rule for which is used where.",
      "severity": "high"
    },
    {
      "type": "dark-mode-not-tokenized",
      "description": "[data-theme=\"dark\"] rules hardcode a parallel set of hex colors instead of redefining the existing --ink/--body/--paper/--mist custom properties. Adding a new component now requires manually writing both a light AND dark hex value by hand, with no single source of truth.",
      "severity": "high"
    },
    {
      "type": "unused-or-underused-token",
      "description": "--radius and --radius-sm exist in :root but are referenced only twice combined; the other ~15 border-radius declarations in the file hardcode their own values instead of using or extending these tokens.",
      "severity": "medium"
    },
    {
      "type": "no-spacing-scale",
      "description": "No --space-* custom properties exist anywhere; margin/padding/gap values are set ad hoc per component.",
      "severity": "medium"
    },
    {
      "type": "missing-focus-states",
      "description": "Only 4 explicit :focus/:focus-visible/outline declarations across 3049 lines and dozens of interactive elements (buttons, links, inputs). Most interactive elements rely entirely on browser default focus rings, which are inconsistent across browsers and frequently suppressed by other rules.",
      "severity": "high"
    },
    {
      "type": "duplicated-component-pattern",
      "description": "5 separate card classes (pilot-card, news-card, community-card, phase-card, pricing-card) with overlapping visual intent instead of one base .card with modifier classes.",
      "severity": "medium"
    },
    {
      "type": "inconsistent-naming-convention",
      "description": "Badge variants mix 'badge-green' / 'badge-release' / 'spec-badge-green' / 'news-badge badge-program' — no consistent BEM or utility naming rule for state modifiers.",
      "severity": "low"
    },
    {
      "type": "stale-data-risk",
      "description": "site.js hardcodes a SEARCH_INDEX array of 13 pages with manually duplicated title/keywords/excerpt. The site has 30 HTML pages; this index is already a manually-maintained, drift-prone duplicate of page content/metadata rather than generated from it.",
      "severity": "medium"
    },
    {
      "type": "no-design-token-layer-for-typography",
      "description": "~37 distinct font-size values and no named type-scale tokens (e.g. --text-sm/base/lg) — every heading/label size was hand-picked per component.",
      "severity": "medium"
    }
  ]
}
```
