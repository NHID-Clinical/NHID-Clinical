# NHID-Clinical Playbook — Proposed Structure

**What this is.** A proposed table of contents for the canonical Playbook, with
the source of each section named. This is the structure, not the writing.

**Why it exists.** The website and the Playbook have different jobs. The site
explains, orients, demonstrates, and directs. The Playbook is the deep reference:
comprehensive, saveable, redistributable, and the single home for material that
today is scattered across seven PDFs and a long tail of thin routes.

**Governing rule.** Nothing enters the Playbook that is not in
`docs/claims-register.md` as `VERIFIED` or explicitly labelled. Anything unknown
is written as unknown.

| | |
|---|---|
| **Commit** | `27ba28e` |
| **Inputs** | `project-state.md`, `claims-register.md`, `ia-disposition.md` |

---

## Format decision

**One generated document, not a new PDF set.** The repository already has
`scripts/generate_pdfs.py` producing seven PDFs, and `check_number_drift.py` now
reads their text (`aaad25a`). The Playbook should join that pipeline — Markdown
source, generated artifact, guarded figures — rather than becoming an eighth
hand-maintained file. **The seven existing PDFs are candidates for absorption**,
which would shrink the surface the guard must watch.

That absorption is not decided here. It needs a pass over each PDF's content.

---

## Proposed contents

### Part I — Understand

| § | Section | Source | Notes |
|---|---|---|---|
| 1 | What NHID-Clinical is | `index.html`, `about.html` | Open, implementation-oriented governance and evaluation framework for non-human actors in healthcare interactions |
| 2 | The problem | `index.html` problem section | Impersonation latency defined plainly. **Do not** assert it is "effectively infinite" — no evidence supports that |
| 3 | Scope and non-scope | `specification.html`, `faq.html` | B2B provider–payer administrative voice. Explicit non-scope is as important as scope |
| 4 | Maturity and status | `project-state.md` §8 | Verbatim from the repository, including every UNKNOWN |
| 5 | What this is not | `claims-register.md` §C | Not a certification, accreditation, regulatory endorsement, or production deployment |

### Part II — The framework

| § | Section | Source |
|---|---|---|
| 6 | The five canonical controls | `framework/controls.html`, `specification.html` |
| 7 | DLG-01, the opt-in extension | `framework/controls.html` — evaluated only when configured; otherwise `DLG01_NOT_EVALUATED` |
| 8 | Terminology | `faq.html`, glossary material |
| 9 | Architecture | `technical-stack.html` + **the one canonical five-layer diagram** |
| 10 | What compliant disclosure sounds like | **`script-examples.html`** — 748 words, currently orphaned |

§10 is the section the current site most conspicuously lacks a home for: the
normative text *states* the disclosure requirement, and this is the only material
that *illustrates* it.

### Part III — Evaluate

| § | Section | Source |
|---|---|---|
| 11 | The shadow evaluation model | `shadow-evaluation-guide.html` + `for-payers.html` merged |
| 12 | Getting started | Smallest useful path. **No mandatory duration** |
| 13 | Data handling and obligations | Observe-only; privacy, security, contractual and recording-consent obligations remain the organisation's |
| 14 | Reading the results | TP / TN / FP / FN / `NOT_EVALUATED`, coverage, per-control, reason codes |
| 15 | Longitudinal evaluation | **Optional.** Presented as a deeper stage, never the entry point |

### Part IV — Evidence

| § | Section | Source |
|---|---|---|
| 16 | The four evidence bodies | `project-state.md` §5 — never merged into one number |
| 17 | Fabricate baseline | 550 conversations / 127 compliant; disjoint populations |
| 18 | Governance Evaluation Corpus | 25 scenarios / 55 turns / 29 of 32 detected. Research measurement, not conformance |
| 19 | Adversarial corpus | 40 scenarios; evasion resistance |
| 20 | Conformance suite | Implementation tests, distinct from detection quality |
| 21 | **What the evidence does not establish** | `project-state.md` §8 + `skipped-test-audit.md` §7–9 |
| 22 | Known limitations | ATR-01 unmeasurable in the Fabricate corpus; DBC-01 and PDX-01 coverage gaps; reference implementation not load-tested |

§21 must include the finding from `skipped-test-audit.md`: **1020 tests run
deterministically, including the HTTP API tests that previously did not run at
all**. The three covering end-to-end IDG-01 and ATR-01 enforcement now pass, so
§21 can state that the API applies the engine and writes a complete audit record
— a claim that was not available before. It must also carry the other half:
**no divergences remain** — both contracts were resolved (§8), so the suite
executes every test it collects.

### Part V — Implement

| § | Section | Source |
|---|---|---|
| 23 | Reference implementation | `framework/reference-implementation.html`, `developers.html` |
| 24 | Event schema and traces | `developers.html` |
| 25 | Adapters | `interoperability.html` — five with hosted routes, one routeless. Table from `project-state.md` §4 |
| 26 | Hosted API | `developers.html` |
| 27 | Conformance testing | `framework/conformance-suite.html` |
| 28 | NHID-Auth | `framework/nhid-auth.html` + `identity-layer.html` (retired route). **Reference implementation, early testing, no production issuers** |

### Part VI — Context and governance

| § | Section | Source |
|---|---|---|
| 29 | Regulatory context | **The four `alignment/*` stubs consolidated** (195 words across four routes) + the homepage table. Every mapping cited, dated, scoped, with a non-legal-advice statement |
| 30 | Governance and contribution | `community.html` — GitHub Discussions and Issues |
| 31 | The Implementation Registry | `registry.html` — self-attested, not certification. Submission via GitHub |
| 32 | Roadmap and open questions | `roadmap.html` |
| 33 | Claim boundaries | `docs/claim-boundaries.md` + `claims-register.md` classification scheme |

§29 is where the mission's instruction to centralise regulatory mapping is
satisfied. Substance for all three instruments is verified
(`claims-register.md` D1–D3); **AB 2905's 1 Jan 2025 effective date is not**, and
the section must mark it so until someone confirms it.

---

## What this structure deliberately does not do

- **It does not create a marketing document.** Every section maps to existing
  verified material or is explicitly marked unknown.
- **It does not resolve the seven existing PDFs.** Absorbing them is proposed,
  not decided.
- **It does not fill gaps.** Where the repository is silent — deployments,
  adopters, independent audit, load behaviour — the Playbook says so.

## Open questions

1. **Absorb the seven PDFs, or keep them alongside?** Absorbing shrinks the
   guarded surface; keeping them preserves existing download links.
2. **One document or a set?** One is more coherent and more redistributable; a
   set is easier to navigate. Recommendation: one, with a linked contents page.
3. **Does the Playbook version with the spec (v1.3) or independently?** Versioning
   with the spec keeps a single number; independent versioning lets it be
   corrected without implying a spec change.
