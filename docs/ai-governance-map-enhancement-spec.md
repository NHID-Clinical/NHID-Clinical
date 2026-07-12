# AI Governance Map — NHID-Clinical Enhancement Spec

Target: https://ai-governance-map.vercel.app/ (separate repo/deployment; this spec is
the implementable blueprint). Written 2026-07-05 to match the premium visual layer
shipped on nhid-clinical.org. Ethos preserved throughout: local-only, no tracking,
reference tool — NHID-Clinical remains an open voluntary proposal, never a product.

## 1. Visual language sync

- Palette: deep navy `#0F172A` base, teal `#14B8A6` accents, slate/silver text,
  sparing gold inlays — identical tokens to `assets/css/premium.css` on the site.
- Feature visuals: reuse the SAME asset set the site ships — the flat, self-contained
  diagrams in `assets/images/3d-svg/<name>.svg`. Copy the SVGs into the map's public/ dir;
  they are dependency-free.
- Alt/caption convention (verbatim pattern): "Illustrative 3D visualization of … —
  conceptual render for clarity." Never present a visual as a product diagram.

## 2. NHID-Clinical panel upgrade

- Header visual: `trust-stack.svg` (or `trust-stack-ziggurat.webp` when present) as
  a large feature image, framed with the site's `.premium-3d` treatment
  (12px radius, `#1e2a44` border, deep shadow).
- Body keeps the existing factual copy; append the standing disclaimer line:
  "Open voluntary proposal · NIST-2025-0035-0026 · CC BY 4.0 · not a product,
  not a certification."
- Primary link back: "Read the v1.3 specification →" (https://nhid-clinical.org/specification.html).

## 3. NEW module: Healthcare Voice Trust Stack Explorer

An interactive five-layer component (mirrors the homepage `#trust-stack` section so
users see one architecture in both places).

Layer data (id → label → mapped frameworks → deep link):

| id | Label | Maps to (show as chips) | Deep link |
|---|---|---|---|
| l1 | Network & Transport Foundation | CCM IVS/DSP transport controls; NIST AI RMF Govern | https://nhid-clinical.org/interoperability.html |
| l2 | Behavioral Disclosure (IDG-01 · PDX-01 · DBC-01 · EIT-01) | NIST AI RMF Measure/Manage; EU AI Act transparency Art. 50; ISO/IEC 42001 ops | https://nhid-clinical.org/simulator.html?scenario=idg-01 |
| l3 | Cryptographic Authorization (NHID-Auth v2) | CCM IAM; NIST SP 800-63 alignment notes | https://nhid-clinical.org/developers.html |
| l4 | Audit Ledger (ATR-01) | CCM LOG/AIS; NIST AI RMF Govern/Map documentation | https://nhid-clinical.org/evidence-pack.html |
| l5 | Observability & CAS | NIST AI RMF Measure; model-risk monitoring practices | https://nhid-clinical.org/simulator.html |

Behavior:
- Click/keyboard-select a layer → detail card slides in: what the layer does (2–3
  sentences, copy from the homepage stack section), mapped-framework chips, the
  known GAPS the proposal aims at (e.g. "no standard verification pathway today —
  impersonation latency effectively infinite"), and the deep link above.
- The simulator deep links WORK today: nhid-clinical.org/simulator.html accepts
  `?scenario=<name|control-id>` (`idg-01`, `dbc-01` → spoofed-identity; `pdx-01` →
  eligibility; `eit-01` → handoff; `atr-01` → prior-auth; or the scenario names
  `prior-auth|expedited|eligibility|handoff|spoofed-identity`).
- Accessibility: role=tablist/tab/tabpanel, focus-visible teal outline,
  prefers-reduced-motion disables the slide.

## 4. Globe / USA map enhancement

- Keep the existing rotatable globe/US map; add an OPTIONAL "healthcare voice"
  overlay toggle: a subtle heat tint labeled explicitly as **illustrative** —
  "Illustrative overlay: where impersonation-latency exposure concentrates
  (concept, not measured data)." Never present as real incident data.
- Premium detailing: darken ocean to `#0a0f1e`, teal graticule at 6% opacity,
  gold-tinted specular highlight.

## 5. Controls / Posture views

- Cards get a subtle 3D tilt on hover (framer-motion `rotateX/rotateY` ≤ 4°,
  spring stiffness ~150; disabled under prefers-reduced-motion).
- Tooltips: richer two-line pattern — line 1 the control name, line 2 the mapped
  NHID control(s) with a mini deep link.

## 6. Exports

- Report/PDF exports embed the same visuals (SVG rasterized at 2x) with the
  caption convention from §1, plus the standing disclaimer line from §2 in the
  footer of every exported page.

## 7. Bidirectional linking (copy, verbatim)

- Site → Map (already live on nhid-clinical.org buttons):
  "Explore Full Context in AI Governance Map" and, on regulatory pages,
  "See NHID v1.3 in full multi-framework context (including CCM, NIST, ISO, EU AI Act)".
- Map → Site: every NHID mention links contextually — controls to
  `/specification.html`, hands-on to `/simulator.html?scenario=…`, procurement to
  `/for-payers.html`, code to the GitHub repo.

## 8. Guardrails (non-negotiable)

- No product CTAs, pricing, signup, or certification language.
- Local-only/no-tracking ethos unchanged; no third-party analytics added.
- Every illustrative visual is captioned as such.

## Implementation note

If the map's repository is added to this session (`add_repo`), this spec can be
implemented directly; the asset files referenced in §1 already exist in this repo
under `assets/images/3d-svg/`.
