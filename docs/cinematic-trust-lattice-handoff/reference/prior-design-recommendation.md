# NHID Clinical Design Direction Recommendation

**Prepared by Manus AI**
**Scope:** NHID Clinical public site, Zero Latency simulator, AI Governance Map, and selected open-source touchpoints.
**Decision:** Adopt **Design (1), “Estilo de IA Ética,” as the shared parent direction**, adapted to NHID Clinical’s existing navy/teal visual equity. Preserve and refine the existing simulator as a deliberate **OpenCode Terminal Mono** subtheme. Use **Utilitarian** only for operational mechanics and **Vertical Whiteboard Timeline** only as a very limited pattern for optional guided onboarding.

## Executive recommendation

NHID Clinical should present itself as a **transparent, evidence-first healthcare AI governance framework**, not as a generic generative-AI product, a playful learning brand, or an institutional certification body. That position is already explicit in the public site’s disclaimers and scope statements: it is practitioner-led, voluntary, open, and not a certification or regulatory requirement.[1] The best fit among the supplied concepts is therefore **Design (1), “Estilo de IA Ética.”** Its core strengths—plain-language trust, legible structure, restrained motion, flat color, diagrams that explain rather than decorate, and a light/dark-ready system—match NHID’s mix of evidence packs, policy pages, formal specification, pilot material, and audience breadth.

Do **not** apply one visual style indiscriminately across the ecosystem. The Zero Latency simulator is a task-focused, scenario-based training environment that already uses a coherent dark terminal-console language, semantic status colors, forensic data cards, progress tracking, and keyboard-relevant interactions.[2] That experience is well served by **Design (10), “OpenCode Terminal Mono,”** but only as a contained application mode. Conversely, the AI Governance Map’s cross-framework dashboard, risk heatmap, filter controls, and maturity scoring need a bright, high-scanability data-product shell, derived from the parent system rather than either a terminal screen or a hand-drawn whiteboard.[3]

> **Design principle:** “Clinical governance clarity, not AI spectacle.”

| Recommended design role | Selected concept | How to use it | What to avoid |
|---|---|---|---|
| **Parent brand and public site** | **Design (1) — Estilo de IA Ética** | Adapt its calm, open, diagram-led, accessible system to NHID’s navy/teal brand. | Copying its Google-like palette literally or introducing generic AI shimmer/marketing copy. |
| **Simulator and conformance tools** | **Design (10) — OpenCode Terminal Mono** | Retain the existing console feel for training, traces, stateful tasks and evaluation records. | Making the public evidence and payer pages dark, mono-only or terminal-like. |
| **Dashboard mechanics** | **Design (2) — Utilitarian, selectively** | Borrow functional status encoding, crisp grids, compact tables, and explicit pass/fail markers. | Full industrial styling, pure black/white, all-monospace long-form text, or safety-yellow as a brand color. |
| **Sequential guide mechanic** | **Design (8) — Vertical Whiteboard Timeline, selectively** | Borrow only the vertical sequence and numbered-step logic for an optional guided pilot/evaluation flow. | Permanent Marker typography, doodle art, irregular borders, whiteboard frames, or hard shadows on formal pages. |

## Recommended ecosystem architecture

The shared system should use a **common semantic foundation** while adjusting density and surface treatment by task. Public pages should make formal content comfortable to read; technical pages should reveal code and evidence progressively; the simulator should stay operational and stateful; and the map should prioritize control discovery. These distinctions preserve a recognizable NHID identity without pretending that a policy document, a live compliance scenario, and a risk dashboard should look identical.

| Layer | Public framework and resources | Simulator | AI Governance Map |
|---|---|---|---|
| **Tone** | Clear, modest, evidence-led, clinically credible | Focused, operational, training-oriented | Analytic, exploratory, control-oriented |
| **Surface** | Light neutral base with restrained dark mode | Warm charcoal / navy console | High-contrast light application workspace |
| **Typography** | Readable sans serif for prose; mono only for code, IDs and trace fields | Mono display and data labels; sans option for instructions if needed | Sans for dense labels and controls; mono for codes only |
| **Navigation** | Simplified grouped navigation, page-local table of contents | Compact persistent module strip and session state | Persistent sidebar plus filter/search state |
| **Status language** | Text label plus color plus icon or pattern | High-salience labeled states: nominal, warning, deny, pass | Color-coded risk with a textual severity label and accessible legend |
| **Data display** | Evidence tables, diagrams, concise callouts, expandable source blocks | Telemetry cards, gate states, timed scenarios, trace cards | Heatmap, crosswalk tables, filters, profile panels and export states |

## Page-by-page design mapping

The public homepage describes both an open framework and an optional production platform, with several audiences, diagrams, controls, an evidence pathway and a simulator entry point.[1] The shared site should lead with ethical-AI clarity while providing increasingly technical treatments deeper in the journey.

| Page or group | Recommended direction | Specific page treatment |
|---|---|---|
| **Home — nhid-clinical.org** | Design (1) parent system | Keep the existing deep-navy/teal, diagram-led identity. Simplify the mega-navigation on first load; use one clear framework CTA and one platform CTA. Put the voluntary/not-certification boundary in a consistent quiet legal-status band rather than repeating it visually in every section. |
| **News and About** | Design (1) parent system | Use editorial cards with date, artifact type, source/repository link and short factual summary. Avoid the Notebook Tabs look; it is too lifestyle/editorial for governance credibility. The current site’s independent/practitioner-led status needs understated typography and clear source links.[4] |
| **Roadmap** | Design (1) + Utilitarian milestone mechanics | Use a horizontal or vertical roadmap with explicit status labels—shipped, in discovery, seeking evaluation partners, not committed. Avoid promising language and distinguish proposal commitments from product plans. |
| **Community** | Design (1), but repair the route first | The supplied `community.html` URL returns a 404. Redirect it to the consolidated GitHub Discussions page or build a simple community hub that points there; do not leave an orphaned navigation destination.[5] |
| **For Payers** | Design (1) in a procurement-ready variant | Increase type size, use outcome-first sections, add an explicit “what changes / what does not change” comparison, and treat the shadow-evaluation process as a calm decision workflow. Keep metrics and benefits evidence-based, not promotional. |
| **Shadow Evaluation Guide** | Design (1) + a restrained stepper based on Design (8) | Use a vertical 90-day sequence with numbered stages, but retain the parent typography, clean diagrams and formal cards. The page already uses a three-month structure and is a strong candidate for progressive disclosure and printable checklists.[6] |
| **Evidence Pack** | Design (1) + Utilitarian evidence components | Use a clear evidence hierarchy: claim, scope, data/source, trace, limitation, and next action. For synthetic traces, add visible “synthetic example” labeling above code blocks. Treat pass/fail states as labeled data states, not only colored badges. |
| **Regulatory Alignment** | Design (1) formal-document mode | Use an alignment matrix with a disclaimer strip that differentiates “mapped to,” “informed by,” and “certified against.” Regulatory material should have the least decorative layout of the public site. |
| **Technical Stack** | Design (1) + diagram/data cards | Use a clean five-layer architecture drawing that links each layer to standards, role, artifact and proof. The existing five-layer table is a good source model for the content.[7] |
| **Specification** | Design (1) documentation mode | Add a sticky on-page table of contents, RFC-keyword styling, version/status metadata, relationship diagrams, and an accessible rules table. Preserve optimal prose width and never apply mono body text to normative paragraphs. |
| **Developers and Interoperability** | Design (1) shell + Design (10) code panels | Use light documentation surfaces for prose and code/trace “islands” with the terminal data treatment. This supports quick starts, JSON traces, adapters and API calls without forcing developers to read every page in a dark terminal theme.[8] |
| **Simulator entry and modules 1–4** | Design (10) retained and refined | Keep its dark console, strong session bar, cards and semantic states. Improve task accessibility: always pair drag-and-drop with move buttons (already partly present in Module 4), show a non-timed alternate path for the five-second exercise, and make result explanations as prominent as scores. |
| **Simulator knowledge base, dashboard and completion record** | Design (10) + Design (2) information mechanics | Keep the console surface, but use clearer sans-serif body text where reading exceeds a paragraph. Use dense, explicit metric rows, an accessible audit trail and visible “training record, not certification” status on the record page. |
| **AI Governance Map** | Design (1) application extension + Utilitarian mechanics | Use the current light dashboard structure. Normalize its cards, filters and heatmap under NHID’s palette, strengthen legibility of risk colors, and add a persistent text/pattern severity legend. Do not transplant the simulator terminal presentation. |
| **GitHub repository** | Design (1) identity in docs | Create a shared documentation cover/README visual identity, then use the same color and status vocabulary as the site. Keep the repository itself developer-native and unembellished. |

## Practical design tokens

The following initial token set applies the chosen ethical-AI direction without copying its template palette or weakening the visual equity already present in the public site and simulator.

| Token group | Recommendation | Rationale |
|---|---|---|
| **Public ink** | `#102033` | A deep navy that reads as clinical and technical without using pure black. |
| **Primary action** | `#1769AA` | Reserved for links, primary actions and active navigation; test in all final contexts. |
| **Trust accent** | `#08756A` | Use for verified, disclosed, complete and normal system states. |
| **Alert states** | `#B42318` fail, `#9A6700` caution, `#1769AA` information | Use with an icon, label and text; never color alone. |
| **Light surface** | `#F7F9FC` with `#FFFFFF` content panels | Keeps documents and evidence readable while retaining depth through borders, not shadows. |
| **Dark technical surface** | `#101A22` with warm off-white text | Preserves simulator character and offers a sensible terminal-adjacent contrast base. |
| **Body type** | Source Sans 3 or Inter, 16–18px, 1.55–1.65 line-height | Supports extended policy, guide and evidence reading. |
| **Code/data type** | IBM Plex Mono or a legible monospace, 0.875–0.95rem | Restrict to JSON, API fields, control codes, timestamps and console labels. |
| **Focus treatment** | 3px solid focus outline with 2px offset; test each theme | WCAG calls for focus indicators with sufficient area and contrast; use a visible system-wide style rather than gentle shadows.[9] |
| **Corners and elevation** | 6–8px radius; 1px borders; near-zero shadow | Communicates precision and avoids both skeuomorphic softness and hostile brutalism. |

## Guardrails

The following exclusions are as important as the recommendation itself. Do not use decorative gradients, AI-generated visual noise, shield-icon overuse, fake “certified” badges, human-like agent illustrations, or animated data particles to manufacture credibility. Do not apply handwritten fonts, retro UI frames, neon palettes, fake operating-system chrome, or full neumorphism to any page that carries health, compliance, payer, procurement or regulatory information.

Accessibility should be designed into the parent system, not applied afterward. W3C’s current guidance says normal text needs at least a 4.5:1 contrast ratio, and it explains that focus appearance needs a sufficiently large visible indicator with a minimum 3:1 change of contrast in its qualifying area.[10][9] For the simulator in particular, each time-based, drag-and-drop or color-coded interaction should offer an equivalent keyboard-operable path and a non-color explanation of its state.

## Priority implementation order

| Priority | Workstream | First outcome |
|---:|---|---|
| 1 | **Shared tokens and component primitives** | One accessible color/typography/status system used by public site, docs and map. |
| 2 | **Public-site shell** | Simplified navigation, page templates for framework/resources/docs, and a unified legal-status pattern. |
| 3 | **Payer/evidence conversion templates** | A consistent evidence hierarchy, guide stepper and decision-support cards. |
| 4 | **Simulator accessibility refinement** | Keyboard alternatives, non-timed learning path, explicit status labels and improved readable instructional type. |
| 5 | **Governance Map normalization** | Align dashboard cards, severity legend, filters, tables and export UI to the parent system. |
| 6 | **Route and content hygiene** | Repair `community.html`; review pages that have minimal presentation or duplicate announcements. |

## References

[1]: https://nhid-clinical.org/ "NHID-Clinical — homepage"
[2]: https://nhid-clinical.github.io/Simulator/index.html "Zero Latency — NHID Clinical Simulator"
[3]: https://ai-governance-map.vercel.app/ "AI Governance Map v2"
[4]: https://nhid-clinical.org/about.html "About NHID-Clinical"
[5]: https://nhid-clinical.org/community.html "NHID Clinical Community route"
[6]: https://nhid-clinical.org/shadow-evaluation-guide.html "Shadow Evaluation Guide"
[7]: https://nhid-clinical.org/technical-stack.html "Technical Stack"
[8]: https://nhid-clinical.org/developers.html "Developer Guide" and https://nhid-clinical.org/interoperability.html "Interoperability Demo"
[9]: https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html "Understanding SC 2.4.13: Focus Appearance — W3C"
[10]: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html "Understanding SC 1.4.3: Contrast (Minimum) — W3C"
