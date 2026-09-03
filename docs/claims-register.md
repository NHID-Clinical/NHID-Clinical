# NHID-Clinical — Public Claims Register

**Purpose.** Every claim the public site makes, with the exact words used, where
they appear, how the claim was checked, and what the check found.

This is a register, not a summary. A claim is listed whether it passed or failed,
so that "we checked and it was fine" is recorded as an outcome rather than as
silence. Where the repository cannot settle a claim, the verdict is **UNKNOWN**
and the claim is not repaired by inference.

| | |
|---|---|
| **Commit** | `aaad25a3d9b9005502470faaa4d05af3d6b7722d` (`aaad25a`) |
| **Measured** | 2026-09-03 |
| **Scope** | 44 published pages in `_site/`, excluding redirect stubs, the Search Console verification file, and `svg-preview.html` |
| **Extraction** | Systematic, not spot-check. Eight regex families (numeric, capability, maturity, regulatory, adoption, prohibited vocabulary) applied to the `<main>` text of every page with scripts and styles stripped |
| **Yield** | 360 hits → **221 distinct claim sentences** across 36 pages |

## Method column — what each value means

| Method | Meaning |
|---|---|
| `engine` | Read from the reference engine's source |
| `constant` | Read from a source-of-truth constant (`check_baseline.py`, `validate_ci.py`) |
| `measured` | Produced by running the code (`pytest`, `eval_corpus.py`) |
| `filesystem` | Established by what exists in the repository (adapter modules, routes) |
| `cross-page` | Compared against another published page's wording |
| `browser` | Rendered and inspected in a headless browser |
| `web-search` | Checked against authoritative domains by search; establishes substance, **not** that a specific URL resolves |
| `pdf-text` | Extracted from a PDF with `pdfminer.six` |
| `none-available` | No source in the repository can settle it |

## Verdict column

`VERIFIED` · `CONTRADICTED` · `UNSUPPORTED` (no evidence either way) ·
`HISTORICAL` (true when written, dated as such) · `UNKNOWN`

---

## A. Numeric claims

| # | Verbatim | Page(s) | Method | Verdict |
|---|---|---|---|---|
| A1 | "The reference implementation includes **987 passing tests** to ensure deterministic policy evaluation." | `faq.html` | `measured` + `constant` | **VERIFIED** — `pytest` reports 987 passed; `UNIT_PUBLISHED = 987` |
| A2 | "5 controls · **987 passing tests** · machine-readable traces · open implementation" | `index.html` | `measured` | **VERIFIED** |
| A3 | "18 skipped · **1005 total**, in the open repo" | `index.html` | `measured` | **VERIFIED** — 987 + 18 = 1005 |
| A4 | "IDG-01 (Identity Disclosure Gate) **70/70 100.0%** … 0/127 0.0%" | `evidence-pack.html` | `constant` | **VERIFIED** — matches `EXPECTED` in `check_baseline.py` |
| A5 | "PDX-01 (Pre-Data Exchange Gate) **41/41 100.0%** … 0/127 0.0%" | `evidence-pack.html` | `constant` | **VERIFIED** |
| A6 | "DBC-01 (Deceptive Behavior Check) **183/200 91.5%** … 5/127 3.9%" | `evidence-pack.html` | `constant` | **VERIFIED** |
| A7 | "EIT-01 (Escalation Implementation Test) **169/171 98.8%** … 5/127 3.9%" | `evidence-pack.html` | `constant` | **VERIFIED** |
| A8 | "**550 conversations**, of which **127** are labelled `scenario_type=compliant`" | `evidence-pack.html` | `constant` | **VERIFIED** |
| A9 | "ATR-01 is not listed because **this corpus cannot measure it**." | `evidence-pack.html` | `constant` | **VERIFIED** — and correctly framed as a structural limitation, not a score of zero |
| A10 | "full suite at **306 passing**"; "**284 passing** Python tests"; "**198 passing** conformance tests" | `news.html` | `cross-page` | **HISTORICAL** — inside entries dated June 2026. Correct as history; must not be updated |
| A11 | "**847 passing unit tests** in the reference implementation" | `specs/NHID-Clinical-v1.3-Overview.pdf` | `pdf-text` | **CONTRADICTED → FIXED `aaad25a`.** Survived four reconciliations (847→851→920→924→987) because the drift guard read text files only. All seven PDFs regenerated; guard now reads PDF text |
| A12 | "Original **4 controls** (IDG-01, PDX-01, DBC-01, EIT-01) — Superseded" | `specs/NHID-Clinical-Knowledge-Archive.pdf` | `pdf-text` | **HISTORICAL** — a row in the version-history table. A substring search flags it; reading the context does not. Leave as written |

**No latency or performance claims** (`<5 seconds`, `~2 minutes`, `>30% reduction`)
were found on any published page. Earlier audits reported these; they are not
present at this commit.

---

## B. Adoption and maturity claims — the highest-risk category

| # | Verbatim | Page(s) | Method | Verdict |
|---|---|---|---|---|
| B1 | "**Start a pilot →**" | **10 pages** — `index` `faq` `developers` `specification` `evidence-pack` `interoperability` `roadmap` `script-examples` `implementation-review` `specs/index` | `cross-page` | **CONTRADICTED.** `news.html` says "Still early — **no production pilots yet**." `shadow-evaluation-guide.html` says "**This is not a pilot program.**" `index.html` says "no production-scale deployment." Ten pages invite the reader to start a thing the site elsewhere says does not exist and is not a pilot |
| B2 | "Development status: TrustLayer is **being built with design partners** and is not yet generally available." | 6 pages | `none-available` | **UNSUPPORTED.** Nothing in the repository evidences any design partner. "Design partners" reads as committed counterparties. Not repaired here — needs your answer on whether any exist |
| B3 | "It is a **90 day engagement** whose technical core is a **2–4 week measurement sprint**" | `community.html` | `cross-page` | **CONTRADICTED.** `shadow-evaluation-guide.html` is structured Month 1 / Month 2 / Month 3 *and* says "not a pilot program"; `for-payers.html` uses a 2–4 week sprint. Three durations and two names for one activity |
| B4 | "Interested in becoming a **pilot partner**?" | `for-payers.html` | `none-available` | **UNSUPPORTED** — same basis as B1/B2 |
| B5 | "Working reference implementation; **no production-scale deployment**." | `index.html` | `filesystem` | **VERIFIED** — consistent with §8 of `project-state.md` |
| B6 | "Still early — **no production pilots yet**." | `news.html` | `filesystem` | **VERIFIED** |
| B7 | "**This is not a pilot program.**" | `shadow-evaluation-guide.html` | `filesystem` | **VERIFIED** as a statement — but see B1: it contradicts the site's own primary call to action |
| B8 | "Screens and outputs on this page are **illustrative, not live product data**." | 5 pages | `browser` | **VERIFIED** — correctly labels the `platform/*` figures |

---

## C. Prohibited vocabulary — every occurrence checked in context

72 hits. **Every one is a disclaimer, not a claim.** Recorded so this is not
re-audited.

| # | Verbatim | Page(s) | Method | Verdict |
|---|---|---|---|---|
| C1 | "It is **not an accredited standard, a certification, or a regulatory compliance guarantee**." | 6 pages | `cross-page` | **VERIFIED** — disclaimer |
| C2 | "NHID-Clinical is a voluntary open framework — **not an accredited standard, certification, or regulatory requirement**." | 5 pages | `cross-page` | **VERIFIED** — disclaimer |
| C3 | "**Mapped, not certified.**" | `index.html` | `cross-page` | **VERIFIED** — disclaimer |
| C4 | "simulation **fully compliant**" | `gov-sim.html` | `browser` | **VERIFIED in context** — page is labelled "Synthetic data only. Illustrative — not a compliance tool"; the string means all six simulated rules passed. Page is orphaned and unpublished |
| C5 | "**zero vendor changes, zero production risk**" | `for-payers.html` | `cross-page` | **CONTRADICTED → FIXED.** Observe-only is not risk-free. Now: no vendor changes, observe-only, does not sit in the call path, and the organisation's obligations still apply |
| C6 | "**Open for production use** under the open license." | `roadmap.html` | `cross-page` | **CONTRADICTED → FIXED.** Sat two lines from "early testing only" while `index.html` called the same work "documented but not yet solved" |

**No occurrence** of "the standard", "industry standard", "HIPAA compliant" as a
property of the framework, "guaranteed reduction", or "eliminates risk" was found
as an assertion at this commit.

---

## D. Regulatory references

88 hits across the site. All are **mapping or context statements**, none assert
endorsement or compliance.

| # | Verbatim | Page(s) | Method | Verdict |
|---|---|---|---|---|
| D1 | "Covered automatic dialing-announcing devices must tell the called person when a prerecorded message uses an artificial voice." — California AB 2905 / Cal. Pub. Util. Code §2874, **from 1 Jan 2025** | `index.html` | `web-search` | **VERIFIED — upgraded from partial on 2026-09-03.** AB 2905 (2023–2024 Reg. Sess.) amends Pub. Util. Code §2874 and was **chaptered as Chapter 316, Statutes of 2024**. The amendments are **effective 1 January 2025**, which closes the one item this register previously left open. Operative requirement confirmed: the unrecorded, natural-voice announcement must "inform the person called if the prerecorded message uses an artificial voice." The statute defines "artificial voice" as a voice generated or significantly altered using artificial intelligence |
| D1a | AB 2905 caveat: "Does not govern every conversational AI call, and is not healthcare-specific." | `index.html` | `web-search` | **VERIFIED and correctly scoped — do not broaden.** The statute reaches **automatic dialing-announcing devices delivering prerecorded messages**. It is not a general AI voice-agent disclosure law, and nothing on the site may present it as one |
| D2 | "AI-generated voices fall within the TCPA's existing restrictions on artificial or prerecorded voice calls." — FCC 24-17, **from 8 Feb 2024** | `index.html` | `web-search` | **VERIFIED.** FCC 24-17 adopted 2 Feb 2024, **released 8 Feb 2024** — the published date is the release date and is correct. **What it establishes:** a *declaratory ruling* that the TCPA's existing "artificial or prerecorded voice" term already encompasses AI-generated voices, so such calls need prior express consent. **What it does not establish:** it creates no new rule, no disclosure standard, and no obligation specific to AI. It interprets a statute that already existed |
| D2a | FCC 24-17 caveat: "Does not create a disclosure standard for provider–payer administrative calls." | `index.html` | `web-search` | **VERIFIED and important.** The ruling addresses outbound calls **to consumers**. NHID-Clinical's scope is B2B provider–payer administrative calls. The caveat correctly prevents the over-reading |
| D3 | "People must be informed when they are interacting directly with an AI system, unless that is obvious in the circumstances." — EU AI Act **Art. 50(1)**, **from 2 Aug 2026** | `index.html` | `web-search` | **VERIFIED, and made paragraph-specific on 2026-09-03.** Regulation (EU) 2024/1689 Art. 50(1) obliges providers to design AI systems intended to interact directly with natural persons so that those persons are informed they are interacting with an AI system, unless obvious to a reasonably well-informed, observant and circumspect person in the circumstances. It applies **from 2 August 2026** and was **not deferred** by the 2026 Digital Omnibus. **The site previously cited "Article 50" in the round; it now cites Art. 50(1)**, so the date attaches to the paragraph it is actually true of — see D3b |
| D3a | EU AI Act caveat: "Does not specify how disclosure is verified, scoped, or evidenced on a call." | `index.html` | `web-search` | **VERIFIED** — Art. 50(1) states the obligation, not a verification or evidencing method |
| D3b | **New.** "Article 50(2), on machine-readable marking of synthetic content, is a separate obligation on a separate timetable and is not what NHID-Clinical addresses." | `index.html` | `web-search` | **VERIFIED — this is the flattening the audit was asked to remove.** Art. 50(2) requires providers of generative AI systems to mark synthetic audio/image/video/text in a machine-readable, detectable format. The **Digital Omnibus on AI — Regulation (EU) 2026/1744, published in the OJ 24 July 2026, in force 27 July 2026** — grants a **four-month grace period** for generative systems **already placed on the market before 2 August 2026**, moving their marking deadline to **2 December 2026**; systems placed on the market on or after 2 August 2026 get no grace period. NHID-Clinical implements neither watermarking nor content marking, so 50(2) is **out of scope** and its timetable must not be merged into the 50(1) row |

> **The Article 50 timing question, resolved.** The concern raised was that
> "Article 50 … from 2 August 2026" flattens an Article whose paragraphs no
> longer share one date. That concern is **correct as to the Article and not as
> to the claim**: the 2 August 2026 date is accurate for **50(1)**, the paragraph
> the site is actually describing, and the Digital Omnibus left 50(1) alone. The
> fix was therefore **not** to change the date but to **name the paragraph**, and
> to record 50(2)'s separate December 2026 transitional timing as expressly out
> of scope (D3b). No other Article 50 obligation is claimed anywhere on the site.

> **What could not be done, and why it matters.** The instruction was to *open*
> the three URLs. **All three are blocked by this environment's egress proxy**
> (`leginfo.legislature.ca.gov`, `docs.fcc.gov`, `eur-lex.europa.eu`), so no URL
> was fetched. The verification above is by **web search against authoritative
> and specialist-practitioner domains**, which establishes what each instrument
> says but **cannot confirm that the specific cited URL resolves**.
>
> Two of the three exact URLs did appear as live search results
> (`docs.fcc.gov/public/attachments/FCC-24-17A1.pdf` exactly; the leginfo bill_id
> `202320240AB2905` under sibling views). The EUR-Lex ELI form
> (`eli/reg/2024/1689/oj`) did not appear, though a different EUR-Lex URL for the
> same regulation did. **A person on an unrestricted network should still click
> all three once** — that is the only item left in D1–D3, and it is a link-rot
> check, not a substance check. The substance of all three is now verified.

| D4 | "three different instruments with different scopes and triggers, **not one uniform rule**" | `index.html` | `cross-page` | **VERIFIED** — load-bearing framing; AB 2905 concerns dialing-announcing devices and prerecorded messages and should not be generalised |
| D5 | "NHID-Clinical does not make any system legally compliant" / "nothing on this page is legal advice" | `index.html` | `cross-page` | **VERIFIED** — disclaimer |

---

## E. Capability claims

| # | Verbatim | Page(s) | Method | Verdict |
|---|---|---|---|---|
| E1 | "Bland.ai and Retell AI adapters are **planned**." | `interoperability.html` | `filesystem` | **CONTRADICTED → FIXED.** `adapters/retell_adapter.py` exists and `/v1/adapters/retell/check` is live; `developers.html` listed it as available. The site understated the repository |
| E2 | Five adapters wired to live routes (twilio, vapi, vonage, retell, connect) | `interoperability.html`, `developers.html` | `filesystem` | **VERIFIED** — matches `adapters/` and the route table |
| E3 | "DLG-01 is evaluated only when a deployment configures delegated authority; absent a delegation it returns `DLG01_NOT_EVALUATED` and changes nothing." | `index.html` | `engine` | **VERIFIED** |
| E4 | "**FHIR R4 AuditEvent** — Audit records in a standard healthcare schema" | `index.html` | `measured` | **VERIFIED** — CI runs a FHIR R4 AuditEvent validation job |
| E5 | "Deterministic engine — Same inputs produce the same decision, every time" | `index.html` | `measured` | **VERIFIED** — determinism is covered by the suite |
| E6 | Homepage engine output: `DENY_DATA` / `PDX01_PHI_GATE_TRIGGERED` / `GATE_BLOCKED` | `index.html` | `measured` | **VERIFIED** — pinned to the live engine by `tests/test_homepage_evidence_accuracy.py` |

---

## F. Open items requiring a human decision

Not defects. Questions the repository cannot answer.

| # | Question | Why it needs you |
|---|---|---|
| F1 | ~~Do design partners exist?~~ **Answered: no.** The six "being built with design partners" claims are unsupported and must not be represented. Disposition retires five of the six pages carrying them; the surviving `platform/index.html` must drop the phrase | Resolved — action pending in the IA pass |
| F2 | ~~Pilot or not a pilot, and how long?~~ **Answered.** Present it as an **observe-only shadow evaluation / pilot framework**, never as current production deployment. **No mandatory 30/60/90-day duration.** The initial evaluation is small and observe-only; longitudinal evaluation is optional. Production call flow is unchanged throughout | Resolved — action pending in the IA pass |
| F3 | ~~Should the three statute URLs be opened?~~ **Answered: yes, and substance is now fully verified.** AB 2905's 1 Jan 2025 effective date is **confirmed** (Chapter 316, Statutes of 2024 — D1), and Art. 50 is now paragraph-specific (D3/D3b). **The URLs themselves remain unopened** — all three hosts are egress-blocked here. Outstanding is a **link-rot check only**: click all three once on an unrestricted network | A person on an open network |
| F4 | ~~Should `script-examples.html` return to navigation?~~ **Answered: yes.** Practitioner-useful material directly supporting the disclosure and impersonation-latency concept. Final placement decided in the IA pass | Resolved — placement pending |

---

## G. External research — classification, not citation

Recorded because the mission requires distinguishing evidence classes.

A search for healthcare voice-agent adoption returned **seven results, all
vendors selling voice agents** (Rasa, Prosper AI, VocalLabs, Droidal,
CallSphere). Under this project's rules that is **vendor-reported**, not verified,
and none of it is usable as market validation.

One figure — "Tier 3 adoption rose from 4% to 19% of surveyed health systems" —
was attributed by a vendor blog to KLAS Research. KLAS covers this area
independently, but **the underlying report was not read**, so the figure is
classified **UNVERIFIED** and is not repeated as fact anywhere.

The durable observation is not a statistic: **the market conversation is almost
entirely sellers describing their own products.** That is an argument for why an
independent evaluation framework is needed. It is an argument, not evidence, and
must be written as one.

---

> **Do not add this file to `WATCHED` in `scripts/check_number_drift.py`.** The
> register quotes superseded figures verbatim — "847 passing unit tests",
> "306 passing", "198 passing conformance tests" — because a register that
> paraphrases the claim it is recording is useless for checking. The guard uses
> an explicit 20-surface list rather than a glob over `docs/`, so these quotations
> are safe today. Adding this file to that list would make the guard fail on its
> own audit trail. The same applies to `docs/project-state.md`.

*Maintenance: a claim changes category only when its evidence changes. Add new
claims as they are published; do not delete resolved rows — a fixed contradiction
is part of the record.*
