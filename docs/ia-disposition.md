# NHID-Clinical — Information Architecture Disposition

**Purpose.** A page-by-page decision record for the website consolidation: what
is kept, merged, moved to the Playbook, moved to GitHub, or retired — with the
measurement behind each call.

The final page count is an outcome of this table, not a target set in advance.
No files have been moved. This is the proposal, with its evidence.

| | |
|---|---|
| **Commit** | `6e81bcb` |
| **Measured** | 2026-09-03 |
| **Baseline** | `docs/project-state.md` §7 |

---

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
