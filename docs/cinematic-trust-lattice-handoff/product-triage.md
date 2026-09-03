# Product Triage and Implementation Priorities

## Decision frame

The requested direction is a full visual-system redesign. The correct sequence is **foundation → public flagship → reusable documents/evidence → simulator → governance map**. The project should not start by restyling every route independently or by replacing working interactions with mockup-shaped code.

## Do now

| Work | Why now | Readiness | Deliverable |
|---|---|---|---|
| Create global Cinematic Trust Lattice tokens and shared CSS | Establishes the reusable system and allows controlled migration. | High | `assets/css/cinematic-trust-lattice.css` with dark/light tokens, focus, typography, layout and reduced-motion rules. |
| Build accessible header, button, status and document primitives | These appear across nearly every route and eliminate page-level drift. | High | Shared semantic markup/classes and small progressive-enhancement JS. |
| Implement the production Trust Lattice SVG | The visual direction requires a unique, accessible brand asset. | High | Editable `assets/diagrams/trust-lattice.svg` plus text/list fallback. |
| Migrate homepage | The homepage establishes the flagship impression and contains core entry points. | High | Public hero, evidence rail, control architecture, open/operated comparison, source-based metric behavior. |
| Migrate Framework, For Payers, Shadow Evaluation Guide and Evidence Pack | These form the highest-value public evaluation journey. | High | Four route treatments based on previews 01–04. |
| Repair design-system accessibility globally | The new high-impact treatment must not reduce usability. | High | Visible focus, status labels, reduced motion, responsive layout and semantic alternatives. |

## Next

| Work | Why after foundation | Prerequisite |
|---|---|---|
| Specification and Regulatory Alignment redesign | Strong documentation shell requires tokens, TOC primitives and evidence blocks. | Document shell and content audit. |
| Technical Stack, Interoperability and Developer Portal redesign | These reuse technical diagrams, code blocks and evidence patterns. | Trust Lattice SVG and document/code components. |
| Roadmap, News, About and Community redesign | These need the public ecosystem shell but are not the critical evaluation path. | Header / public page primitives. |
| Simulator visual migration | Highest interaction and accessibility risk; do it after shared status and state primitives are stable. | Existing module behavior mapping and keyboard/non-timed alternatives. |
| Screenshot visual regression workflow | Supports iterative parity with approved references. | First route migration complete. |

## Strategic decisions required before implementation expands

| Item | Why it needs a product decision | Default position for this handoff |
|---|---|---|
| TrustLayer platform claims and hierarchy | Public visual distinction can alter commercial interpretation. | Preserve current wording and links; do not invent platform capability. |
| AI Governance Map repository / deployment ownership | It is currently separately deployed and may have a distinct codebase. | Implement its visual system only in its source project once identified. |
| Dynamic homepage metrics | Hard-coded passing-test counts become stale. | Use source/release metadata or phrase them as dated snapshots with source. |
| Community route behavior | Public URL previously showed a route-health issue in review. | Verify desired canonical route / redirect before redesign. |
| Simulator timing and scoring adaptations | Accessible non-timed modes may have assessment implications. | Add as an explicit learning alternative after confirming scoring rules. |
| Production asset pipeline | Lattice SVG, motion and responsive imagery need a stable source / optimization process. | Prefer editable SVG with graceful fallback. |

## Already addressed / do not regress

| Existing asset or capability | How the redesign should treat it |
|---|---|
| Existing public open-framework positioning | Promote it visually without changing legal or product scope language. |
| Existing dark-mode preference stored in the browser | Extend token coverage; keep existing persistence behavior. |
| Existing documentation, controls and reference artifacts | Make them easier to read and discover; do not rewrite content as part of the visual migration. |
| Existing Zero Latency modules | Treat them as real learning interactions; apply the operational visual shell without moving logic into presentation. |
| Existing open-source / GitHub path | Continue to expose public artifacts and contribution routes. |

## Explicitly out of scope

The following must not be bundled into the visual redesign without a separate request: policy or legal review, changing the control specification, claiming certification/compliance approval, building a new hosted platform, migrating static pages to a new framework, adding user authentication, modifying conformance results, changing simulator scoring, processing real PHI, adding analytics tracking, or redesigning an unverified external product.

## Design-quality risks

| Risk | Prevention |
|---|---|
| The system becomes “cyberpunk AI” rather than healthcare governance | Keep the dark visual zone limited to heroes, simulator and trace panels; use quiet evidence surfaces for reading. |
| Screenshots become the actual interface | Build all production hierarchy in semantic HTML/CSS/SVG. |
| Claims become stronger through visual language | Keep boundary labels visible and source every dynamic/evidence assertion. |
| The simulator becomes visually intense but inaccessible | Pair all temporal/color/drag interactions with keyboard, text and learning alternatives. |
| Route-by-route CSS forks | Require shared `ctl-*` / `zls-*` primitives and review selectors before merging. |
| The map looks disconnected | Reuse token roles, header/rules and status vocabulary, but preserve its analytic application purpose. |
