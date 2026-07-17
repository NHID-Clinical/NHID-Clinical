# NHID-Clinical Playbook — Manuscript Consistency Audit

**Scope:** All twenty chapters (first complete draft, merged to `main`),
audited against six editorial priorities: claim strength, invented
precision, regulatory language, framework-vs-book separation, early-chapter
alignment, and technical accuracy. **This is an audit, not a revision** —
no chapter text was changed. Evidence for each finding comes from
whole-manuscript sweeps (certainty-verb search, regulatory-verb search,
numeral search, first-person search, label-coverage scan) plus the twenty
per-chapter editorial reviews.

**Protected elements (per the audit charter, verified untouched and not
challenged by any finding):** the origin story and TRICARE operational
experience; the impersonation latency concept; the five controls; the
governance philosophy; the practical implementation focus.

---

## 1. Executive Summary of Manuscript Health

The manuscript is in strong first-draft health. Its claim discipline is
unusually good for a governance book — the honesty posture is not
decorative but structural (the covert-agent boundary in Chapter 4, the
reference-vs-production line in Chapter 11, the residual column in Chapter
16, the mapped-not-certified treatment in Chapter 19). The certainty-verb
sweep and regulatory-verb sweep both came back essentially clean: no
instance of "certified," "compliant," or "required by" is used in the
book's own voice about the framework; every occurrence either quotes the
framework's own stated claim, enforces the mapped-not-certified
discipline, or appears as dialogue. No first-person leaks exist outside
the two chapters (1 and 20) where the author's voice is by design.

The manuscript has **one systemic weakness and one critical technical
finding**, plus a tail of localized fixes:

- **Systemic:** the composite/anticipated labeling convention was
  established at Chapter 14 and applied consistently from there forward,
  but Chapters 2–13 predate it. Their real-world examples — roughly
  eighteen passages — are constructed composites or anticipated dynamics
  narrated in the register of observed cases. Nothing in them is
  deceptive in intent (each was flagged in its own chapter review), but
  until the labels are retrofitted, a reader can mistake illustration for
  evidence. This is the audit's largest single work item and it is
  mechanical: apply Chapter 14's double-lock pattern (section-head note
  plus per-example markers) backward.
- **Critical technical:** Chapter 11's opening scenario narrates
  production-grade revocation behavior ("revocation … propagates to
  verification immediately") in a scene framed as present capability,
  while the reference implementation's revocation state is in-memory and
  process-local — a limitation the same chapter states plainly two
  sections later. One clause fixes it; unfixed, it is the manuscript's
  only place where a reader could infer a capability that does not exist.

Approximate finding counts: **2 Critical, 14 Important, 12 Editorial**
(the composite-label retrofit is counted once as Critical though it spans
twelve chapters). No finding requires structural rewriting, chapter
reordering, or removal of any protected element. The severity profile is
what a disciplined first draft should produce: the load-bearing claims
are sound; the fixes are framing, labeling, and precision.

## 2. Consistency Findings, by Audit Priority

### 2.1 Claim Strength Audit

The four-class scheme maps onto the manuscript as follows.

**A. Demonstrated (repository-supported) — verified sound.** The corpus
false-positive data (550 conversations; 142/260 and 106/153
true/false-positive counts) traces to `docs/dbc01-human-review-sop.md`.
CAS tier thresholds (0.90/0.75/0.50/0.20), pilot good-enough bars (≥500
calls, <10% dropped, ±1-turn stability), the sticky-disclosure mapping,
the five-state engine and its reason codes, Ed25519 parameters, the
3-hop/monotonic-narrowing chain rules, FHIR milestone typing and outcome
codes (0/4/8), and the tier-ladder efforts (15 min / ~2 hr / ~1 day) all
trace to their source artifacts. These may keep their unhedged register.

**B. Composite (book synthesis) — sound but under-attributed.** The
enforcement ladder (Ch. 10), four-station metric hardening (Ch. 15), four
pilot deaths (Ch. 14), seam map (Ch. 13), four-column register (Ch. 16),
three-eras arc (Ch. 20), three-questions decomposition naming (Ch. 3),
and the quarterly four-question agenda (Ch. 15) are the book's
arrangements of real framework mechanisms. Each needs its one-sentence
attribution ("the framework supplies the mechanisms; this arrangement is
this book's recommendation") plus the front-matter convention (§4).

**C. Anticipated dynamics — present, mostly labeled late.** The vendor
self-check adoption dynamic (Chs. 4, 13, 18), the RFP line-item, the
custodial-MSO pattern, prompt-driven vendor adaptation (Ch. 10), and the
regulatory-window argument are correctly reasoned from structure but only
Chapters 14+ label them. Retrofit required (see 2.5 / change log).

**D. Speculative — three instances, all tolerable if owned.**
"Verification gets easier as the ecosystem matures" (Chs. 3, 11 — now
substantiated structurally in Ch. 11; add the cross-reference in Ch. 3);
"there is no equilibrium called wait-and-see" (Ch. 20 — the book's honest
extrapolation, flagged in its review as knowingly owned); "cheap
questions get asked" (Ch. 12 — a culture prediction kept subjunctive).
No action beyond what the reviews queued.

**Certainty-verb sweep results:** 15 hits for
prevents/guarantees/ensures-class verbs; 12 are legitimate (referring to
figures preventing misreadings, or structural properties that do hold —
e.g., monotonic narrowing). Three need softening: Ch. 6/20 "EIT-01
guarantees an exit / the human path EIT-01 guarantees" → the control
*requires* a working path; a control cannot guarantee its own
implementation. Ch. 8 "determinism guarantees the same inputs score
identically" → true only *at matching engine versions* (already queued in
Ch. 8's review). Ch. 14 "The kit guarantees that four weeks of work
yields honest numbers" → "is designed to yield."

### 2.2 Invented Precision Sweep

The numeral sweep distinguished three populations:

**Repository-sourced numbers (keep, no change):** all Demonstrated-class
figures listed in 2.1A, plus the 330-test count (kept under Ch. 5's
"snapshot" framing), the 18-case CTS suite, 30–90-day rotation windows,
and the 200-character FHIR assertion-text excerpt.

**Origin-story numbers (protected, keep):** Chapter 1's nine-minute call
is autobiographical recollection, hedged correctly on first use ("eight
or nine minutes"). It stays.

**Invented precision (fix — six instances):**

| Location | Number | Disposition |
| :-- | :-- | :-- |
| Ch. 9, null-result example | "a 9% escalation dishonor rate" | Remove the figure: "a measurable escalation-dishonor rate concentrated in one vendor's traffic." Composite examples must not mint statistics. |
| Ch. 13, renewal example | "one redline round" | "minimal negotiation." |
| Ch. 14, opening composite | "Fourteen months later" | "A year on." |
| Ch. 15, quarterly scenario | "slid eleven points" | "slid materially quarter over quarter." |
| Ch. 15, scenario + guidance | "Forty minutes end to end" / "forty minutes" | Keep only if the composite label is carried at the scenario head (it is); otherwise "under an hour." Single standard: scenario texture may keep round durations under an explicit composite label; examples posing as findings may not. |
| Ch. 20, closing scenario | "six minutes instead of nine" | "minutes shorter than the call it replays" — or keep the mirror only with an explicit composite note at the scenario head. The mirrored nine invites quotation as a measured result. |

(Ch. 9's "100% IDG-01 violation rate" is retained deliberately — it
illustrates an *absurd* artifact caught by validation, and absurdity is
its point. Ch. 18's "two hundred small practices" is composite texture
inside a labeled section; acceptable, noted for the single-standard
sweep.)

**Rule to encode in front matter:** hypothetical numbers appear only
inside labeled composites, only as texture (never as findings), and every
unlabeled number must trace to a repository artifact or be converted into
a measurement recommendation.

### 2.3 Regulatory Language Review

**Result: clean, with two hardening items.** The sweep found no
prohibited verb in the book's own voice. Specifically verified:

- **EU AI Act Art. 50** — the framework's own materials state
  "Compliant with EU AI Act Art. 50"; the book (Ch. 19) correctly
  *attributes* that claim to the framework, treats it as the framework's
  strongest stated claim, and instructs adopters to add their own
  counsel-scoped row. Nowhere does the book assert Act compliance in its
  own voice. **Keep exactly this structure.**
- **NIST** — every mention of NIST-2025-0035-0026 carries the
  public-comment-not-endorsement caption; RMF language is "mapped to Map
  and Measure," with Ch. 19 correctly noting Manage/Govern fall to the
  adopter.
- **ISO/IEC 42001** — "aligns with Annex A controls"; no certification
  implication.
- **FHIR** — the R4-base-specification-only scope claim is reproduced in
  both Ch. 12 and Ch. 19; no implementation-guide conformance implied.
- **STIR/SHAKEN** — consistently "assumed, not replaced," with carrier
  integration marked as planned future work (matches the technical
  specification's own status line).
- **OAuth2/OIDC** — described as coexisting transport authorization;
  no claim that NHID-Auth replaces or extends the standards themselves.

Hardening items: (a) the **verb-fidelity verification** flagged as a
standing item in Ch. 19's review remains open — at copyedit, check every
alignment verb against the source document row by row; this audit
spot-verified the seven listed above but a full pass belongs with
copyedit. (b) **HIPAA** appears descriptively twice (Chs. 2, 13 — scope
descriptions and the BAA pointer); both are accurate at the level
written, but both should be inside the blast radius of the front-matter
no-legal-advice disclaimer, and Ch. 13's BAA paragraph should
explicitly defer applicability analysis to counsel (its review already
queued this).

### 2.4 Framework vs. Book Synthesis

The separation exists in substance — the concept-reference tables at
every chapter's end distinguish "formal treatment" locations, and the
reviews tracked attribution — but it is **not yet visible to a reader**,
because the convention lives in the editorial files, not the manuscript.
Required: (a) the front-matter convention (§4, item 2); (b) one
attribution sentence at first use of each synthesis artifact listed in
2.1B; (c) the figure captions for Figures 10-1, 15-3, 14-3, 16-1, and
20-1 carry the same tag, since figures travel without their chapters.

Inventory decision for the audit: the **three-questions decomposition**
(nature/representation/authorization) is classed as book synthesis *in
its naming* — the underlying mechanisms (IDG/DBC for nature, NPI
anchoring for representation, delegation for authorization) are framework
content, but the triad vocabulary is the book's. The attribution sentence
in Ch. 3 should say precisely that, because the vocabulary is likely to
propagate and its provenance should be traceable.

### 2.5 Early Chapter Alignment (Chapters 1–4)

- **Chapter 1 (origin story vs. industry claims):** the memoir voice is
  correctly scoped — generalizations are framed as observed experience,
  with one exception queued since its own review: "the overwhelming
  majority of payer–provider calls are administrative and repetitive"
  should carry the "in my experience" anchor explicitly. The origin
  story itself needs no evidence upgrade; it needs a front-matter note
  (§4, item 5) distinguishing the one lived narrative from the labeled
  composites elsewhere — that contrast *protects* the origin story's
  authenticity.
- **Chapter 2 (growth claims):** adoption-growth language is
  experience-and-structure-scoped ("within months," incentive analysis)
  and contains no market statistics — verified. One precision fix: "this
  is not a thought experiment — it is the documented gap" (re trace 08)
  — accurate that the gap is documented, but the trace is a canonical
  failure trace in the framework's library, not a field-observed
  production incident; add "documented in the framework's trace library
  as a canonical failure shape." The three examples need composite
  labels.
- **Chapter 3 (trust stack):** instrument survey verified against the
  stack table (layers, roles, Layer 0 label). Add the forward
  cross-reference for the verification-asymmetry claim (substantiated in
  Ch. 11). Examples need labels.
- **Chapter 4 (latency definitions and boundaries):** the definition,
  formula, companions, and honest-boundary statement are verified
  against the pilot kit. Two items stand from its review: the "vendor
  who asks to be measured" example must be marked anticipated (or moved
  to Ch. 18, which now houses that dynamic — recommend marking here and
  cross-referencing); the bimodal-distribution example needs "may find"
  framing in prose, matching its figure caption. Add the queued
  completion-rate clause to the zero-cost claim.

### 2.6 Technical Accuracy Review

Verified accurate against the repository: the policy engine's states,
actions, reason codes, fail-closed transitions, and LLM placement
(ROUTE_LLM reachable only post-disclosure — Ch. 8 matches
`nhid_policy.py`); the delegation object model, chain rules, and error
vocabulary (Ch. 11 matches `agent_identity` documentation); the FHIR
milestone/outcome mapping (Ch. 12 matches the mapping doc); pilot
mechanics (Ch. 9 matches the kit); DBC-01 tiers and review routing
(Ch. 7 matches the SOP).

Findings, in the reference/production/roadmap frame:

1. **Critical — Ch. 11 opening scenario** narrates immediate revocation
   propagation as present behavior. Reference implementation: in-memory,
   process-local. Fix: one clause framing the scenario's organization as
   operating the *production-hardened* layer per the migration path, or
   a scenario-head note. (Queued in Ch. 11's review; elevated here
   because it is the manuscript's only capability overstatement.)
2. **Important — Ch. 8** three precision scopes queued in its review:
   parity "at matching versions"; "no new critical-path dependencies"
   scoped to the post-call topology; "possibly forever" reframed as
   "monitoring remains valuable after enforcement exists."
3. **Important — Chs. 6/10** the receiving-side PDX-01 reading
   (representatives not volunteering PHI) is book doctrine layered on
   the control; both reviews queued clarifiers that the CTS does not
   test receiving-side conduct. Ch. 17's consolidation is the right
   home; the two clarifying clauses close it.
4. **Important — Chs. 11/16 alignment** the knowledge-based-world
   counterfactual ("authorized anything, against any payer,
   indefinitely") overstates in both places; per-payer authentication
   rituals still existed. Align both passages on "unscoped vs. scoped
   compromise."
5. **Editorial — Ch. 6** the engine's disclosure sentence must be framed
   as "one conformant form of words," not required text (queued).

Roadmap items (registry, mutual bot-to-bot verification, carrier
integration) are consistently marked future work everywhere they appear
— verified across Chs. 11, 18, 19, 20. No finding.

## 3. Required Edits, Grouped by Priority

### Critical (capability or evidence misreading possible; fix before any external reader)

| # | Chapter | Issue | Recommended correction | Reason |
| :- | :- | :-- | :-- | :-- |
| C1 | 11 | Opening scenario narrates production-grade revocation propagation as present capability | Add clause framing the scenario as the production-hardened deployment per the documented migration path | Reference implementation's revocation is in-memory; the manuscript must never imply unbuilt capability |
| C2 | 2–13 | Composite/anticipated examples unlabeled (≈18 passages; label coverage begins at Ch. 14) | Retrofit Ch. 14's double-lock pattern: scenario/example-section note + per-example markers | Readers can mistake illustration for case evidence; the book's credibility strategy requires the distinction to be visible, not editorial-file-only |

### Important (accuracy, precision, and attribution; fix in the same revision pass)

| # | Chapter | Issue | Recommended correction | Reason |
| :- | :- | :-- | :-- | :-- |
| I1 | 9 | Invented statistic ("9% escalation dishonor") | Remove figure; qualitative phrasing | Composites must not mint statistics |
| I2 | 15 | Invented precision ("eleven points") | "slid materially" | Same rule |
| I3 | 13 | Invented precision ("one redline round") | "minimal negotiation" | Same rule |
| I4 | 14 | Invented precision ("fourteen months later") | "a year on" | Implies an unsupported typical timeline |
| I5 | 20 | Mirrored precision ("six minutes instead of nine") | "minutes shorter," or explicit composite note at scenario head | The mirror invites quotation as a measured result |
| I6 | 6, 20 | "EIT-01 guarantees an exit" | "requires a working exit" | A control mandates; implementation delivers |
| I7 | 8, 14 | "determinism guarantees…" (unversioned); "the kit guarantees…" | Add "at matching versions"; "is designed to yield" | Precision of guarantee claims |
| I8 | 8 | Critical-path claim unscoped; "possibly forever" | Scope to post-call topology; reframe monitoring's permanence | In-call topology *is* a call-path dependency |
| I9 | 2 | Trace-08 framing ("not a thought experiment") | "documented in the framework's trace library as a canonical failure shape" | A canonical trace is not a field incident |
| I10 | 4 | Vendor self-check example unlabeled; bimodal example framing; zero-cost claim | Mark anticipated (cross-ref Ch. 18); "may find"; add completion-rate clause pointing to Ch. 10 | Integrity items from its own review, confirmed |
| I11 | 6, 10 | Receiving-side PDX-01 reading presented adjacent to CTS-tested scope | Add clarifiers: CTS does not test receiving-side conduct; doctrine is consolidated in Ch. 17 | Framework-vs-book precision on a control's reading |
| I12 | 11, 16 | Overstated knowledge-based-world counterfactual (two aligned passages) | "unscoped vs. scoped compromise" phrasing in both | Per-payer rituals existed; overstatement is unnecessary to the point |
| I13 | 10, 13, 15, 16, 17, 20 | Book-synthesis artifacts (ladder, stations, deaths, seam map, register, eras, three-questions naming) lack attribution sentences | One sentence at first use each + figure-caption tags | Framework-vs-book separation must be reader-visible |
| I14 | 13, 18 | BAA/insurance liability adjacency | Defer applicability to counsel explicitly; soften custodial-insurance sentence | No-legal-advice line |

### Editorial (quality; fix opportunistically or at copyedit)

| # | Chapter | Issue | Recommended correction | Reason |
| :- | :- | :-- | :-- | :-- |
| E1 | 1 | "Overwhelming majority" generalization; "caller ontology" phrasing; disclosure-guidance bullet buried | Anchor to experience; plainer phrase; promote bullet | Queued in Ch. 1 review |
| E2 | 3 | Verification-asymmetry forward reference | Add cross-ref to Ch. 11 | Substantiation now exists |
| E3 | 5 | "At the time of writing" sweep for maturity numbers (330 tests, v1.3, live API) | Apply book-wide | Aging claims |
| E4 | 7 | Corpus provenance clause (evaluation corpus, not production); Figure 7-4 caption ("operational loop, not automated feedback"); soften "predictable"→"detectable" (15) | As queued | Precision |
| E5 | 8 | Incident example's "no meeting required" | "became an infrastructure ticket" | Composite tidiness |
| E6 | 10 | "Moves markets more than any in-call banner"; prompt-norm example outcome | "at least as much"; mark anticipated | Queued softenings |
| E7 | 12 | Breach-ending inoculation clause in opening; Figure 12-4 caption caveat | As queued | Tidiness objection |
| E8 | 14 | "Nothing… to veto" overstatement; partner example friction beat | Soften; add friction | Queued |
| E9 | 15 | Composite-triage clause ("the composite routes to review; it does not acquit") | Add | Closes an over-reading |
| E10 | 16 | Transformed-column expansion (cost asymmetry in risk terms); register-title advice promotion | As queued | Strength items |
| E11 | 17 | Governs-vs-operates second beat; boundary-register back-references | As queued | Consolidation clarity |
| E12 | 18, 19 | "Would look like" mood; procurement aphorism; free-option scoping; "as of this writing" hedge on the specification-gap claim; RFP model-language caveat | As queued | Tone/scope calibration |

## 4. Suggested Front Matter Additions

1. **"How to read the evidence in this book"** — the four-class
   convention (Demonstrated / Composite / Anticipated / Speculative),
   the labeling promise, and the numbers rule from §2.2. One page; it is
   the contract every finding above enforces.
2. **"The framework and this book"** — the synthesis convention:
   mechanisms belong to NHID-Clinical (controls, schema, engine, CTS,
   CAS, NHID-Auth, pilot kit); arrangements are this book's (ladder,
   stations, deaths, seam map, register columns, eras, three-questions
   vocabulary), offered as recommended practice, not specification.
3. **Disclaimers block** — not legal advice; not regulatory guidance;
   the framework is a voluntary open baseline, not a standard,
   certification, or requirement (reproduce the framework's own
   language); claims about framework maturity are snapshots as of
   writing — adopt by version from current materials.
4. **Extraction-card index** — the twelve photocopiable one-pagers
   (Figures 4-4, 5-1, 6-3, 9-3, 10-1, 12-3, 13-1, 14-3, 15-1, 16-1,
   17-1, 19-1), listed as a deliberate genre with their honest-boundary
   text declared irremovable.
5. **"About the opening story"** — one paragraph stating that Chapter 1
   (and its return in Chapter 20) is the author's lived TRICARE
   operations experience, and that all other narrated scenarios are
   labeled composites or anticipated dynamics. This is the note that
   makes the labeling regime protect, rather than dilute, the origin
   story.
6. **Terminology reference** — control IDs, CAS tiers, the metric set,
   and the three-questions vocabulary with its provenance note.

## 5. Publication Readiness Assessment

**Verdict: strong, publishable-track first draft — not yet ready for
external circulation; ready after one focused revision cycle.**

- **Technically defensible:** yes, with one Critical capability-framing
  fix (C1). Every mechanism description checked against the repository
  matched; the reference/production/roadmap distinction holds everywhere
  else.
- **Internally consistent:** yes at the level of doctrine and
  vocabulary (three-questions triad, control IDs, boundary sentences,
  and receiving-side doctrine all verified consistent); the visible
  framework-vs-book separation (I13) is the remaining consistency debt.
- **Honest about evidence levels:** structurally yes — the honest-
  boundary passages are the book's spine — but the labeling regime that
  proves it to a reader begins at Chapter 14. C2 closes that gap and is
  the gating item for the "honest about evidence" claim.
- **Audience-suitable:** executive, governance, audit, and implementer
  readers each have chapters written to their genre (verified in the
  Part IV translations); the front-matter additions are what orient
  each audience to which chapters are theirs.

**Recommended sequence to publication readiness:** (1) apply C1–C2 and
the Important set in one revision pass (estimated as sentence-level work
throughout — no rewrites); (2) draft front matter per §4; (3) run the
row-by-row alignment-verb verification with copyedit; (4) commission the
figure program (the four paired sets flagged across reviews); (5) then
external readers — one payer operations lead, one voice-AI vendor
engineer, one compliance auditor — before any wider circulation. The
do-not-change list survives this entire program untouched: nothing in
the audit requires diluting the origin story, the latency concept, the
controls, the governance philosophy, or the implementation focus.
