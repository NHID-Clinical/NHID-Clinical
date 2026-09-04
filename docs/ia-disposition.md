# NHID-Clinical — Information Architecture Disposition

> **Revised 2026-09-03. The target changed; the measurements did not.**
> Parts 1–3 below were written to answer *"which pages duplicate each other?"*
> Their measurements stand and are not repeated. But **45 → 30 was an audit
> finding, not a goal**, and it was reached with the wrong test for keeping a
> page: *"is this content unique?"* Uniqueness is the right test for rejecting a
> merge-as-deduplication. It is not what earns a route.
>
> **Part 4 supersedes the disposition.** The objective is a substantially smaller
> public website, and the test is now *"does this have a distinct job in one of
> the five mission journeys, and is it a place a reader would arrive at?"*
> Target: **11 core pages**, plus two flagged decisions. See §4.

**Purpose.** A page-by-page decision record for the website consolidation: what
is kept, merged, moved to the Playbook, moved to GitHub, or retired — with the
measurement behind each call.

No files have been moved. This is the proposal, with its evidence.

*(Original framing: "the final page count is an outcome of this table, not a
target set in advance." That was right about not reverse-engineering evidence to
hit a number, and wrong about the objective — see the banner above and §4.)*

| | |
|---|---|
| **Commit** | `6e81bcb` |
| **Measured** | 2026-09-03 |
| **Baseline** | `docs/project-state.md` §7 |

---

> **Executed 2026-09-04.** Part 4's disposition is no longer a proposal — the
> consolidation is done. **45 published routes → 11**, with a redirect for every
> retired one. `platform/` and `news.html` were retired on the approved
> decisions; the roadmap page was merged into NHID-Auth rather than relabelled,
> so the site now has **no roadmap** — writing one is new work, not a rename.
> What actually happened, including two defects the execution surfaced, is in
> the commit history and in `conformance-run-record.md`.

## 1. The duplication measurement — and what it overturns

Both external audits asserted that several page pairs "overlap heavily" and
should be merged as duplicates. That was tested rather than accepted.

**Method.** For every pair of published pages over 60 words, the set of distinct
6-word sequences in each page's `<main>` text was compared. Overlap is reported
as shared sequences ÷ the smaller page's sequences. Scripts, styles and chrome
were stripped.

**Result: of 35 pages compared, only 11 pairs exceed 12% overlap, and every one
of them is inside `platform/`.**

| Pair | Overlap |
|---|---|
| `platform/evidence-center` ↔ `platform/trust-gateway` | 25% |
| `platform/continuous-conformance` ↔ `platform/trust-gateway` | 25% |
| `platform/agent-registry` ↔ `platform/trust-gateway` | 25% |
| `platform/index` ↔ `platform/trust-gateway` | 22% |
| `platform/continuous-conformance` ↔ `platform/evidence-center` | 18% |
| `platform/agent-registry` ↔ `platform/continuous-conformance` | 18% |
| …5 further `platform/` pairs | 13–16% |

### The pairs the audits named are not duplicates

| Pair | Claimed | **Measured** |
|---|---|---|
| `for-payers` ↔ `shadow-evaluation-guide` | "overlap heavily", "duplicates" | **2%** — 13 shared sequences of 1,156 words |
| `about` ↔ `index` | "merge, repetitive" | **1%** — 3 shared sequences |
| `technical-stack` ↔ `index` | "repeats the same architecture" | **0%** — 0 shared sequences |
| `evidence-pack` ↔ `platform/evidence-center` | similar names | **0%** |
| `developers` ↔ `interoperability` | "merge" | **7%** |

**This changes the recommendation.** `for-payers` and `shadow-evaluation-guide`
are not duplicated text — they are **contradictory** text (see
`claims-register.md` B1/B3: pilot vs "not a pilot", 90-day vs 2–4 week). Merging
them is *reconciliation*, not deduplication, and a careless merge would discard
~1,150 words of distinct content while leaving the contradiction unresolved.

Likewise `technical-stack` ↔ `index` share **no text at all**. What repeats
between them is the *five-layer visual*, rendered differently on each. That is a
diagram problem, not a content problem, and merging the pages would not fix it.

---

## 2. Disposition — decided

Everything here follows from measurement and does not depend on an open question.

### 2.1 Retire from the site, keep in the repository

| Page | Words | Basis |
|---|---|---|
| `platform/trust-gateway.html` | 287 | 22–25% overlap with four sibling pages |
| `platform/evidence-center.html` | 467 | 13–25% overlap with four siblings |
| `platform/agent-registry.html` | 446 | 14–25% overlap with four siblings |
| `platform/continuous-conformance.html` | 393 | 16–25% overlap with four siblings |
| `platform/enterprise.html` | 441 | 15% overlap; describes an unbuilt offering |

**Collapse six `platform/` pages (2,617 words) into one.** They describe a
concept-stage offering with no production deployments, and they repeat each other
more than any other group on the site. `platform/index.html` (583 words) survives
as the single page, rewritten to absorb what is distinct in the other five.

This also removes five of the six pages carrying *"being built with design
partners"* (`claims-register.md` B2), which is unsupported.

| Page | Words | Basis |
|---|---|---|
| `identity-layer.html` | 47 | Stub. Content belongs in `framework/nhid-auth.html` |
| `implementation-review.html` | 78 | Stub **and orphan** |
| `alignment/stir-shaken.html` | 50 | Stub **and orphan** |
| `alignment/cms-0057-f.html` | 61 | Stub **and orphan** |
| `alignment/nist-ai-agent-standards.html` | 47 | Stub **and orphan** |
| `alignment/vendor-evidence-pack.html` | 37 | Stub **and orphan** |
| `gov-sim.html` | 91 | Orphan; already unlinked. Retire from build |
| `svg-preview.html` | 312 | Dev artifact, never public |

The four `alignment/*` stubs total 195 words across four routes. Their subject
matter — regulatory mapping — belongs in one section of the Playbook with
citations and applicability notes, per the mission's instruction to centralise
regulatory context.

### 2.2 Restore to navigation

| Page | Words | Basis |
|---|---|---|
| `script-examples.html` | 748 | **Orphan with real content.** Sixth-largest page. Concrete disclosure phrasing and the patterns that create impersonation latency. Practitioner-grade material no visitor can reach |
| `specs/index.html` | 326 | **Orphan.** The PDF download index. There is currently no downloads page in navigation while PDFs are linked ad-hoc from six pages |

### 2.3 Keep as-is

| Page | Words | Basis |
|---|---|---|
| `index.html` | 1,956 | Largest page; 0–1% overlap with everything |
| `evidence-pack.html` | 1,231 | 0% overlap with `platform/evidence-center`; carries the verified corpus table |
| `developers.html` | 994 | 7% overlap with `interoperability` — below the merge threshold |
| `framework/*` (6 pages) | 2,913 | No pair above threshold |
| `specification.html` | 734 | Normative text |
| `faq.html` | 679 | 1% overlap with `index` |
| `roadmap.html` | 527 | Distinct |
| `news.html` | 824 | Dated historical record — see `claims-register.md` A10 |
| `about.html` | 405 | 1% overlap with `index`. Merging is a *narrative* choice, not a dedup one |
| `privacy.html`, `sms-opt-in.html` | 425 | Legal/operational necessity |

### 2.4 Fix in place, do not move

| Page | Issue | Action |
|---|---|---|
| `technical-stack.html` | 155 words carrying the five-layer visual 4× | Content problem is the **visual**, not the page. One canonical diagram; this page becomes its home |
| `registry.html` | 173 words; empty-state renders correctly but only because the fetch 404'd until `aaad25a` | Keep. Now that `content/` is published, decide the submission workflow (GitHub issue template) |

---

## 3. The evaluation journey — decided 2026-09-03

Previously blocked. The decisions:

> Present NHID-Clinical as an **observe-only shadow evaluation / pilot
> framework**, never as a current production deployment. **No mandatory
> 30/60/90-day duration.** The initial evaluation is small and observe-only;
> longitudinal evaluation is optional if useful. The production call flow is
> unchanged throughout.

This resolves `claims-register.md` B1/B3 and settles four pages.

| Page | Words | Disposition |
|---|---|---|
| `shadow-evaluation-guide.html` | 540 | **Becomes the single evaluation destination.** Absorbs what is distinct in `for-payers`. Month 1 / Month 2 / Month 3 structure is **removed** — no mandatory duration. "This is not a pilot program" is removed: it is a pilot *framework*, observe-only |
| `for-payers.html` | 616 | **Merged in.** At 2% textual overlap this is a genuine merge, not a dedup — its payer-specific framing is content the destination does not have |
| `community.html` | 280 | **Keep**, minus its duration claim. "90 day engagement … 2–4 week measurement sprint" is removed. Community is GitHub Discussions and Issues |
| `demo.html` | 235 | **Retire.** With one evaluation destination and `script-examples.html` restored, a separate demo route has no distinct job |

**Wording that must not survive the merge**, per the decision and the register:

- Any mandatory duration — "90 day", "30 days", "Month 1/2/3", "2–4 week sprint"
  as a *requirement* rather than an illustration.
- "This is not a pilot program" — it is a pilot framework; the distinction the
  site needs is observe-only vs production, not pilot vs not-pilot.
- "zero production risk" (already fixed) and any successor phrasing.
- Anything implying current production deployment.

**"Start a pilot →" (10 pages, register B1)** is not banned by this decision, but
it must lead to the observe-only framing rather than imply an existing programme
with named participants. The 10 instances need one consistent destination and
label. Recommended: **"Run a shadow evaluation →"** — it describes the action, is
already the homepage's primary CTA, and cannot be read as joining a cohort.

### 3.1 `platform/` and the design-partner claim

**Decision: no design partners exist.** All six *"TrustLayer is being built with
design partners"* claims are unsupported and must not be represented.

§2.1 already retires five of the six pages carrying that phrase. The surviving
`platform/index.html` **must drop it**, and must not replace it with any other
adoption, customer, pilot, or external-validation claim. The honest framing is
concept-stage with no production deployments.

### 3.2 `script-examples.html`

**Decision: return it to the public information architecture.** 748 words of
practitioner-useful disclosure phrasing, directly supporting the
impersonation-latency concept.

**Placement:** under the framework, adjacent to the controls — it is the concrete
answer to "what does compliant disclosure actually sound like?", which the
normative text states and does not illustrate. Not under evaluation: it is
reference material, not a procedure.

## 4. Resulting shape

**45 pages are published today** (the count in `project-state.md` §7 said 44;
45 is correct and includes the Search Console verification file).

**15 pages leave the site.** §2.1 retires 13 — five `platform/`, six stubs, one
dev artifact (`svg-preview.html`), one orphaned simulator (`gov-sim.html`). §3
retires `demo.html` and folds `for-payers.html` into the evaluation destination.

**45 → 30.** §2.1 retires 13; §3 retires `demo.html` and merges `for-payers.html`
into `shadow-evaluation-guide.html` (−2 more). Nothing is now blocked.

The two orphans in §2.2 return to navigation without changing the count — they
are already published, merely unreachable.

**Words retired vs relocated:**

| | Words |
|---|---|
| `platform/` — 5 pages retired, `index` survives | 2,034 |
| Stubs, dev artifact, orphaned simulator | 723 |
| `demo.html` retired | 235 |
| `for-payers.html` — **merged, not deleted** | 616 |
| **Leaving the site as routes** | **3,608** |
| **Genuinely retired content** | **~2,992** (the 616 relocates) |

Of that, the ~2,034 `platform/` words are the only genuinely *duplicated* text on
the site (13–25% mutual overlap). The 723 stub words are not duplicated — they
are too thin to justify a route, and their subject matter relocates to the
Playbook rather than disappearing. **This is consolidation, not deletion** — the
mission's distinction.

---

## 5. What this table does not decide

- **Navigation labels and hierarchy.** Disposition says which pages exist, not
  what the menu calls them.
- **The canonical visual system.** §2.4 identifies the diagram problem but does
  not design the fix.
- **The Playbook's contents.** Its structure is proposed in
  `docs/playbook-structure.md`; the writing is a separate pass.

## 6. Open — still unknown, not filled in

- **AB 2905's 1 Jan 2025 effective date** (`claims-register.md` D1) is the only
  regulatory figure not verified. The statute's substance is confirmed; the date
  is not.
- **The three statute URLs have still not been opened** — all three hosts are
  egress-blocked from this environment. Substance was verified by search against
  authoritative domains, which is not the same thing.


---

# Part 4 — Revised disposition: consolidation, not deduplication

## 4.1 What the first pass got wrong

Part 1 measured **textual** overlap: shared 6-word sequences. It proved the
external audits wrong about which pages duplicate each other, and that finding
holds. But it was then used for a second job it cannot do — deciding what stays
— and it silently answered a different question than the one that matters.

Two pages can share **0% of their 6-word sequences and still be the same page**.
Textual overlap cannot see that, and two examples in this repository prove it:

| Pair | Textual | **Topical** | What it means |
|---|---|---|---|
| `for-payers` ↔ `shadow-evaluation-guide` | 2% | **0.27** | Same subject, different sentences |
| `roadmap` ↔ `framework/nhid-auth` | below threshold | **0.17** | Both are the NHID-Auth v2 page |

**Topical similarity** here is cosine over TF-IDF term signatures across the 34
pages with enough text to compare, computed the same day.

## 4.2 The actual diagnosis: fragmented, not duplicated

The topical scan is the useful result, and it is **not** the one that was
expected. Outside `platform/`, the highest topical similarity on the whole site
is **0.36** (`faq` ↔ `specification`), and nearly every pair sits between 0.05
and 0.28.

**The site is not redundant. It is fragmented** — many small pages each doing one
narrow job, so that answering a single question means visiting four routes.
Fragmentation and duplication call for opposite remedies:

- Duplication is fixed by **deleting** the copy. Little is lost.
- Fragmentation is fixed by **assembling** the pieces. Nothing is lost — and
  low overlap is what makes the assembly *safe*, because the pieces do not
  collide.

This is why the revised target can be far smaller than 30 while preserving
substantive information: **13,594 words are retained across 11 pages.** The
consolidation deletes routes, not content.

## 4.3 The test a page must now pass

A standalone route must satisfy **all three**:

1. **Destination** — it is a place a reader deliberately arrives at, in one of
   the five mission journeys: *understand, evaluate, implement, validate, adopt*.
2. **Completeness** — a reader who lands there gets a whole answer, not a
   fragment that sends them onward.
3. **Citability** — someone would plausibly link to or bookmark it by itself.

A page that fails any one of these is **content, not a destination** — it becomes
a section. Being unique does not exempt it. Neither does being good.

## 4.4 The 11 core pages

| # | Canonical page | Journey | Absorbs | Words |
|---|---|---|---|---|
| 1 | `index.html` | Understand | `about.html`, `technical-stack.html`, `framework/index.html` | ~2,600 |
| 2 | `specification.html` | Understand (normative) | `framework/controls.html` | 1,508 |
| 3 | `shadow-evaluation-guide.html` | **Evaluate** | `for-payers.html`, `script-examples.html`, `demo.html` | 2,150 |
| 4 | `developers.html` | **Implement** | `framework/reference-implementation.html`, `interoperability.html`, `registry.html` | 2,029 |
| 5 | `evidence-pack.html` | **Validate** | `framework/conformance-suite.html` | 1,624 |
| 6 | `regulatory-alignment.html` | Validate | the four `alignment/*` stubs | 569 |
| 7 | `framework/nhid-auth.html` | Adopt (what's next) | `roadmap.html` | 984 |
| 8 | `faq.html` | Understand | `community.html` | 959 |
| 9 | `specs/index.html` | All | *(becomes the Playbook download surface in Phase C)* | 326 |
| 10 | `privacy.html` | Legal | — | 293 |
| 11 | `sms-opt-in.html` | Legal / operational | — | 132 |

### Why each merge, specifically

- **`framework/index.html` is a hub, not a page.** Its distinctive terms are
  *catalog, mapping, browse, read* — it is navigation wearing a page's clothes.
  On an 11-page site, a hub between the reader and four destinations is pure
  overhead. Its links redistribute; little text needs absorbing.
- **`framework/controls.html` into `specification.html`.** The five controls
  *are* the specification. Splitting the normative text from the controls it
  defines is the fragmentation in its purest form.
- **`for-payers` + `script-examples` + `demo` into the evaluation guide.**
  Part 3 already established that `for-payers` is a genuine merge. Adding
  `script-examples` (748 words of concrete disclosure phrasing, currently an
  orphan no visitor can reach) turns the guide from instructions into
  instructions *with the actual words to say*. `demo.html` (235 words) is a
  pointer to a phone line — a section, not a route.
- **`interoperability` + `reference-implementation` + `registry` into
  `developers.html`.** All three are the implementer's journey.
  `interoperability` is literally adapter payload shapes. **`registry.html` is
  173 words and currently lists nothing** — an empty room is worse as a
  destination than as a "get listed" section.
- **`roadmap.html` into `framework/nhid-auth.html`** — see the defect in §4.6.
- **`community.html` into `faq.html`.** 280 words of pure signposting to GitHub.
  Its own topical similarity to `about` is 0.05: it is not a subject, it is a
  set of links.

### What moves to the Playbook rather than the site

Per the mission's instruction to centralise regulatory context, the **detailed**
mapping tables move into the Playbook (Phase C), leaving `regulatory-alignment.html`
as the short public summary that links to it:

| Content | From | To |
|---|---|---|
| Full instrument-by-instrument mapping with citations and applicability | `regulatory-alignment.html` + four `alignment/*` stubs | Playbook, regulatory section |
| ATR-01 traceability matrix and evidence-validation report (2,139 words, two `docs/*.html` routes) | `docs/ATR-01-*.html` | Playbook, evidence section |
| Conformance case-by-case detail | `framework/conformance-suite.html` | Playbook; summary stays on `evidence-pack.html` |

## 4.5 Two decisions that are yours, not the audit's

Neither is answerable from repository evidence. Both are marked **UNKNOWN**
rather than decided.

**1. `platform/` — does TrustLayer keep a public presence at all?**
Six pages, 2,679 words, describing a **concept-stage offering with no production
deployments and — per your decision — no design partners.** Part 2 already
collapses six pages into one. The open question is whether that one survives.
Against the test in §4.3 it fails *completeness*: there is no product to
evaluate, implement, or validate. The honest alternatives are a section on
`index.html` or `framework/nhid-auth.html` saying what is planned, or keeping one
page. **This is a commercial decision and I have not made it.**

**2. `news.html` — a website page, or GitHub Releases?**
825 words, ten dated entries, a legitimate historical record (register A10) that
must not be silently rewritten. But a changelog is a thing readers *check*, not a
destination they arrive at. Moving it to GitHub Releases preserves it verbatim,
removes a route, and puts it where the commits are. It also contains a
**"Pilot Partners Sought"** entry that needs reconciling with the
no-design-partners decision either way.

Resolved as: **11 core pages**, or **12–13** if both flagged items stay.

## 4.6 Two defects this pass surfaced

Neither is an IA question; both are factual and were found while reading the
pages rather than counting them.

**`specification.html` omits PDX-01 entirely.** *(This entry corrected within
the hour of first writing it. The first diagnosis — "a stale heading" — was
wrong, and wrong in the dangerous direction: it implied the fix was to change
"Four" to "Five", which would have left the control missing while making the
page assert otherwise.)*

The page at `/specification.html`, titled *NHID-Clinical v1.3 Specification* and
linked from navigation as *Specification (v1.3)*, names exactly four control IDs:

| Surface | Control IDs named |
|---|---|
| `specification.html` | IDG-01, DBC-01, EIT-01, ATR-01 — **no PDX-01** |
| `framework/controls.html` | all five, plus DLG-01 |
| `index.html` | all five, plus DLG-01 |
| `specs/…Core-Specification.pdf` | all five |

It says *"The proposal suggests four behaviors"* and closes with *"Why These
Four"*. **The page is internally consistent and externally wrong.** The heading
is correct *for the page*; the page is incomplete *for the framework*.

**PDX-01 is the Pre-Data Exchange Gate** — no PHI, member ID, NPI, DOB or claim
number until IDG-01 disclosure is confirmed. In a healthcare framework it is
plausibly the most consequential of the five, it is enforced by the engine, and
it is baselined at 41/41 with zero false positives. It is absent from the
document a reader would treat as authoritative.

**The canonical PDF is the correct artifact and disagrees with the page.**
`specs/NHID-Clinical-v1.3-Core-Specification.pdf` carries PDX-01 in its control
cards. So the fix is **reconciliation against an existing source, not new
normative drafting** — the text exists and does not need inventing.

**A second, milder inconsistency inside that PDF.** Its overview says
*"defines **four** deterministic behavioral controls"* while the metric row
immediately below reads *"**5** Controls"* under the heading *"The Five
Controls"*. Unlike the page, this one is **defensible rather than wrong**: the
four are the *behavioral* controls (IDG-01, PDX-01, DBC-01, EIT-01) and ATR-01 is
labelled in the same document as the *"fifth canonical control"* — an audit
control, not a behavioural one. It reads as a contradiction and should be
disambiguated, but nothing is missing.

**Note the two "fours" are different sets.** The PDF's four is IDG/PDX/DBC/EIT.
The website's four is IDG/DBC/EIT/ATR. The page did not inherit the PDF's
behavioural-vs-audit distinction; it dropped the PHI gate.

**Also affected:** `specs/NHID-Clinical-Operational-Blueprint-v1.3.pdf` contains
no mention of PDX-01 at all.

**Not fixed in this pass, deliberately.** This is normative text, and the
standing instruction is that an exception to audit-only work gets flagged and
waits. It is one decision away: **approve sourcing the PDX-01 section from the
canonical PDF into `specification.html`, and re-titling "Why These Four".** No
wording needs to be authored. Merging `framework/controls.html` into
`specification.html` (§4.4) would also resolve it, which is an argument for that
merge independent of page count.

**`roadmap.html` is not a roadmap.** Navigation labels it *Roadmap*; its `<h1>`
is *"NHID-Auth v2: Cryptographic Agent Identity"*, and its content is a v2
technical deep-dive — credentials, revocation, the passport flow — which is also
what `framework/nhid-auth.html` covers. A reader clicking "Roadmap" to learn
what is planned gets a protocol description instead. Merging the two fixes both
the mislabel and the split subject, but note the consequence: **after the merge
the site has no roadmap.** If a forward-looking page is wanted, it has to be
written, not relabelled.

## 4.7 Count

| | Routes |
|---|---|
| Published today | 45 |
| First pass (Part 2, superseded) | 30 |
| **Revised target** | **11** core, 12–13 with both flagged items |
| Words retained | **13,594** |
| Routes retired outright (stubs, orphans, dev artifacts) | 9 |

The reduction comes almost entirely from **merging destinations, not discarding
content**. Of the routes removed, only ~673 words are retired outright, and all
of that is stubs, orphans and dev artifacts.

