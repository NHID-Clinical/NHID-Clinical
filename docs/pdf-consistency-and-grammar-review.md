# PDF Consistency & Grammar Review

**Scope:** Mechanical consistency + grammar review of the 6 generated PDF artifacts in `specs/` and
`docs/assets/archive/`, checked against the canonical fact table in
`docs/MASTER-KNOWLEDGE-ARCHIVE.md` (the project's explicit source of truth, which is treated as
authoritative over these static PDF snapshots).

**Reviewer:** Automated review pass (Claude Code), 2026-06-20.

**Method:** Each PDF was read via the `Read` tool's PDF page-extraction support, sampling title
pages, executive-summary/TOC pages, and all pages referencing the 13 canonical facts below. Several
PDFs turned out to be short (2–5 pages) and were read in full rather than sampled. No PDF or other
repository file was edited as part of this review — see "Disposition" at the end.

---

## Top Summary

| PDF | Pages | Findings (hard violations) | Soft/style observations |
| :--- | :--- | :--- | :--- |
| `specs/NHID-Clinical-v1.3-Overview.pdf` | 3 | 0 | 1 (non-issue, noted for completeness) |
| `specs/NHID-Clinical-v1.3-Core-Specification.pdf` | 2 | 3 | 1 |
| `specs/NHID-Clinical-Operational-Blueprint-v1.3.pdf` | 2 | 0 | 0 |
| `specs/NHID-Clinical-Shadow-Evaluation-Guide.pdf` | 2 | 1 | 0 |
| `specs/NHID-Clinical-v2-Technical-Playbook.pdf` | 3 | 1 | 1 |
| `specs/NHID-Clinical-Knowledge-Archive.pdf` | 5 | 0 | 0 |
| `docs/assets/archive/NHID-Clinical-Master-Knowledge-Archive.pdf` (canonical, OCR-only check) | 72 | 1 (rendering only) | 0 |

**Total hard findings across all 6 spec PDFs: 5**
**Total rendering/OCR findings (canonical archive PDF): 1 (cosmetic footer glyph only)**

**Overall verdict:** No critical content errors that would mislead a reader about NHID-Clinical's
core architecture, formulas, or policy logic. All 6 spec PDFs correctly state the not-a-
standard/not-a-certification/not-a-regulatory-requirement disclaimer (fact 9), the correct CAS
expansion (fact 3, where stated), the correct FHIR R4-base-only conformance claim with no IHE BALP
overreach (fact 4), the correct 6-adapter count (fact 6, where stated), the correct policy-action
priority order (fact 8, where stated), the canonical "Impersonation Latency" term (fact 10, where
used), and accurate "no pilots yet" language (fact 12, where addressed). The issues found are
narrowly confined to: (a) two PDFs using the old/deprecated control-ID expansions for PDX-01 and/or
EIT-01 (facts 1–2), and (b) two PDFs hard-coding the stale, broken us-east-2 API base URL instead of
the current us-east-1 URL (fact 13). One unverified sub-claim (a "42 tests" figure for
`agent_identity.py`) was checked against the repo and confirmed stale (actual count: 26). No OCR
corruption, garbled text, or control-ID capitalization problems were found in any document; the only
rendering defect found anywhere is a cosmetic mis-encoded middle-dot character in the canonical
archive PDF's page footers (does not affect any factual content).

**Important caveat on fact 13 (API URL):** The "master archive is authoritative" convention does
**not** fully apply to this specific fact. `docs/MASTER-KNOWLEDGE-ARCHIVE.md` itself still contains
the stale `dc2ipcqs7k` / us-east-2 URL in 6 places (lines 666, 1088, 1432, 1710, 1721, 1899), and
`docs/v2-integration-guide.md` contains it in 2 places (lines 20 and 45 — note: the task brief
described this as "3 places," but only 2 were found on inspection; logged as a discrepancy in the
task brief itself, not a new repo issue). **Recommendation: fix the master archive markdown first**,
then regenerate the dependent PDFs — regenerating from the master archive today would not fix the
URL issue, since the master archive is itself stale on this one point.

---

## Findings Log

### Finding 1 — PDX-01 wrong expansion

- **File:** `specs/NHID-Clinical-v1.3-Core-Specification.pdf`
- **Page/section:** Page 1, "The Four Controls" summary box, PDX-01 card
- **Problematic text:** `"PDX-01 / PHI Data Exchange Gate"`
- **Why it's inconsistent:** Violates **canonical fact 1**. The correct name is "Pre-Data Exchange
  Gate," not "PHI Data Exchange Gate."
- **Recommended correction:** Change to "PDX-01 / Pre-Data Exchange Gate."
- **Authority note:** The master archive (`docs/MASTER-KNOWLEDGE-ARCHIVE.md`, §2.1) and source code
  are authoritative on this naming. This PDF is a static snapshot that predates the naming
  correction; it should be regenerated from `docs/MASTER-KNOWLEDGE-ARCHIVE.md` on the next rebuild
  rather than hand-edited PDF-side.

### Finding 2 — EIT-01 wrong expansion

- **File:** `specs/NHID-Clinical-v1.3-Core-Specification.pdf`
- **Page/section:** Page 1, "The Four Controls" summary box, EIT-01 card
- **Problematic text:** `"EIT-01 / Escalation & Intervention"`
- **Why it's inconsistent:** Violates **canonical fact 2**. The correct name is "Escalation
  Implementation Test." The master archive explicitly documents "Escalation & Intervention" as the
  deprecated/incorrect former name (it appears in the archive's own stale-claims correction table).
- **Recommended correction:** Change to "EIT-01 / Escalation Implementation Test."
- **Authority note:** Master archive / source code is authoritative; regenerate from
  `docs/MASTER-KNOWLEDGE-ARCHIVE.md` on next rebuild rather than hand-editing the PDF.

### Finding 3 — Stale (broken) API base URL

- **File:** `specs/NHID-Clinical-v1.3-Core-Specification.pdf`
- **Page/section:** Page 2, "Live Conformance API" section, "Base URL" box
- **Problematic text:** `"Base URL https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod"`
- **Why it's inconsistent:** Violates **canonical fact 13**. This us-east-2 stack is confirmed
  broken (returns 403 on all demo routes). The currently deployed, working stack is
  `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod`.
- **Recommended correction:** Replace with `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod`.
- **Authority note:** Master archive / source code should be authoritative here, but **caveat**: as
  of this review, `docs/MASTER-KNOWLEDGE-ARCHIVE.md` itself still contains the same stale us-east-2
  URL in 6 locations (see Top Summary caveat above). The markdown source must be corrected before
  this PDF can be correctly regenerated; do not hand-patch the PDF in isolation.

### Finding 4 — Unverified/stale per-file test count (soft, confirmed stale on inspection)

- **File:** `specs/NHID-Clinical-v1.3-Core-Specification.pdf`
- **Page/section:** Page 2, "NHID-Auth v2 — Cryptographic Agent Identity" box
- **Problematic text:** `"Reference implementation: src/agent_identity.py (42 dedicated tests)."`
- **Why it's inconsistent:** Related to **canonical fact 5** (test-count accuracy). This specific
  sub-claim was not in the original 13-fact list verbatim, so it was independently checked against
  the repository: `tests/test_identity.py` currently contains **26** test functions, matching the
  count given in `docs/MASTER-KNOWLEDGE-ARCHIVE.md` (`test_identity.py` | 26 | NHID-Auth v2,
  Ed25519, delegation chains). The PDF's "42" figure is stale.
- **Recommended correction:** Update to "26 dedicated tests" (or remove the specific count and
  reference the aggregate 270/336 totals instead, to reduce future drift risk).
- **Authority note:** Master archive / source code is authoritative; regenerate from
  `docs/MASTER-KNOWLEDGE-ARCHIVE.md` on next rebuild rather than hand-editing the PDF.

### Finding 5 — EIT-01 wrong expansion (second occurrence, different PDF)

- **File:** `specs/NHID-Clinical-Shadow-Evaluation-Guide.pdf`
- **Page/section:** Page 2, "The Four Controls You Are Observing" section, EIT-01 card
- **Problematic text:** `"EIT-01 — Escalation & Intervention"`
- **Why it's inconsistent:** Violates **canonical fact 2**, same defect as Finding 2 — "Escalation &
  Intervention" is the deprecated/incorrect name; correct name is "Escalation Implementation Test."
- **Recommended correction:** Change to "EIT-01 — Escalation Implementation Test."
- **Authority note:** Master archive / source code is authoritative; regenerate from
  `docs/MASTER-KNOWLEDGE-ARCHIVE.md` on next rebuild rather than hand-editing the PDF.
- **Note:** This PDF's PDX-01 reference (page 2, controls list) is listed by bare ID only (no
  expansion given on its own card), so it does not separately violate fact 1.

### Finding 6 — Stale (broken) API base URL (second occurrence, different PDF)

- **File:** `specs/NHID-Clinical-v2-Technical-Playbook.pdf`
- **Page/section:** Page 3, "Live API Quick Reference" / Base URL box
- **Problematic text:** `https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod`
- **Why it's inconsistent:** Violates **canonical fact 13**, same defect as Finding 3.
- **Recommended correction:** Replace with `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod`.
- **Authority note:** Same caveat as Finding 3 — the master archive markdown must be corrected first
  (it currently has the same stale URL in 6 places), then this PDF regenerated from it.

### Finding 7 (soft observation) — Potentially confusing juxtaposition of two different "test count" metrics

- **File:** `specs/NHID-Clinical-v2-Technical-Playbook.pdf`
- **Page/section:** Page 1, "Five-Layer Trust Stack" (Layer 2 box: "4 controls, 5 CTS tests") vs.
  same page's Tech Stack table ("18 deterministic CTS cases")
- **Problematic text:** "5 CTS tests" next to "18 deterministic CTS cases" with no clarifying
  language distinguishing the two metrics.
- **Why it's inconsistent:** Not a direct violation of any single canonical fact 1–13 as worded
  (both numbers are individually correct per the master archive — "5" = test categories, one per
  control; "18" = total YAML test cases), but the juxtaposition reads as an apparent internal
  contradiction to a reader without access to the master archive's clarifying context. Logged as a
  style/clarity issue adjacent to fact 5.
- **Recommended correction:** Clarify wording, e.g., "4 controls, 5 test categories / 18 CTS test
  cases," to avoid the appearance of contradiction.
- **Authority note:** Master archive / source code is authoritative; regenerate from
  `docs/MASTER-KNOWLEDGE-ARCHIVE.md` on next rebuild with clearer wording rather than hand-editing
  the PDF.

### Finding 8 (soft observation, non-issue) — Overview PDF line-wrap hyphenation

- **File:** `specs/NHID-Clinical-v1.3-Overview.pdf`
- **Page/section:** Page 1, "Public Brief: The Impersonation Latency" section
- **Problematic text:** Line-wrap hyphenation of "human-\noperated" at a column break.
- **Why it's flagged:** This is normal LaTeX/LuaTeX justified-text hyphenation, not OCR corruption or
  a real grammar defect. Logged only for completeness per the review's grammar/style-pass
  instructions; **no action needed**.
- **Recommended correction:** None.
- **Authority note:** N/A — not a defect.

### Finding 9 — Rendering-only defect in the canonical archive PDF (cosmetic, no content impact)

- **File:** `docs/assets/archive/NHID-Clinical-Master-Knowledge-Archive.pdf`
- **Page/section:** Footer of all 72 pages (`"NHID-Clinical · CC BY 4.0 · nhid-clinical.org"`)
- **Problematic text:** The middle-dot separator (`·`, U+00B7) in the footer renders as a replacement
  glyph followed by literal text `"b7"` (i.e., `"NHID-Clinical �b7 CC BY 4.0 �b7 nhid-clinical.org"`)
  — confirmed via text extraction to occur exactly 72 times, once per page, only in this footer
  string. The same `·` character renders correctly in the body text elsewhere in the document
  (e.g., the closing line on page 72), confirming this is isolated to the footer's font/encoding
  path and not general document corruption.
- **Why it's flagged:** This file IS the canonical source rendered to PDF, so per task scope it was
  checked only for rendering/OCR corruption, not content drift. This is a genuine — if purely
  cosmetic — PDF-rendering defect (font/encoding issue in the footer template), not a content error.
- **Recommended correction:** When next regenerating this PDF, check the footer template's font
  encoding for the middle-dot character (likely a font subset or encoding-table issue specific to
  the footer style, since body text using the same glyph renders correctly).
- **Authority note:** This is a rendering pipeline issue, not a markdown-source content issue — no
  change to `docs/MASTER-KNOWLEDGE-ARCHIVE.md` content is implied, only to the PDF build/footer
  styling step.

---

## Facts Confirmed Correct (no findings) — by PDF

To document review thoroughness, the following canonical facts were specifically checked and found
**correct** (no violation) in the indicated PDFs:

- **`NHID-Clinical-v1.3-Overview.pdf`**: Facts 9 and 10 are handled exemplarily — explicit "not an
  official standard," "not a certification," "strictly voluntary" language (fact 9), and correct,
  unaltered, prominent use of "Impersonation Latency" as a section header (fact 10). Facts 1–8, 11,
  13 do not arise in this PDF (out of scope at this document's level of abstraction) and so present
  no violation. Fact 12 (no false pilot/adoption claims) is also clean — language is consistently
  hypothetical/prospective.
- **`NHID-Clinical-v1.3-Core-Specification.pdf`**: Fact 4 (FHIR claim) is exactly correct — "no named
  Implementation Guide conformance (e.g. IHE BALP) is claimed." Fact 5 (270 tests) and fact 6 (6
  adapters) are correctly stated in the page-1 stat box. Fact 9 disclaimer present and correct
  (though omits "not a certification" specifically — a minor completeness gap, not a contradiction).
  Fact 11 (Ed25519, max 3 hops, call-SID nonce binding) correctly stated. Fact 12 clean (no pilot
  claims).
- **`NHID-Clinical-Operational-Blueprint-v1.3.pdf`**: Facts 1, 3, 4, 5, 6, 7, 8, 13 do not arise
  (out of scope for this 2-page rollout-process document). Fact 9 disclaimer present and correctly
  worded. Fact 11 (Ed25519 + NPI binding) correctly referenced. Fact 12 correctly stated ("No payer
  has piloted or adopted it yet — you would be among the first").
- **`NHID-Clinical-Shadow-Evaluation-Guide.pdf`**: Fact 1 (PDX-01) not separately mis-expanded (bare
  ID only). Facts 3, 4, 5, 6, 7, 8, 13 do not arise. Fact 9 disclaimer present and correct. Fact 12
  correctly and explicitly stated ("No payer has piloted or adopted it yet").
- **`NHID-Clinical-v2-Technical-Playbook.pdf`**: Fact 1 (PDX-01 — "Pre-Data Exchange Gate," correct).
  Fact 3 (CAS — "Call Authorization Score," correct, used twice). Fact 6 (6 adapters, all correctly
  named: VAPI, Twilio, Vonage, Retell, Amazon Connect, call-progress). Fact 7 (only the top-level
  `CAS = F_IAF × F_NOCF × ECF` composite is shown; the internal NOCF expansion with weights is not
  printed in this PDF, so the old-wrong-version risk does not arise here). Fact 8 (policy-action
  priority table is an exact match: 5 DENY_DATA > 4 ESCALATE_HUMAN > 3 DISCLOSE_IDENTITY > 2
  LOG_ONLY > 1 CONTINUE_AI, with correct trigger conditions). Fact 9 disclaimer correct. Fact 12
  clean (no pilot-adoption claims; "production conformance check" refers to an endpoint name, not a
  deployment-status claim).
- **`NHID-Clinical-Knowledge-Archive.pdf`**: Fact 1 (PDX-01 — "Pre-Data Exchange Gate," correct).
  Fact 2 (EIT-01 — "Escalation Implementation Test," correct — this PDF gets it right where the
  Core Specification and Shadow Evaluation Guide do not). Fact 4 (FHIR claim correct, including an
  explicit FAQ entry: "Does NHID-Clinical claim FHIR Implementation Guide conformance? No..."). Fact
  9 disclaimer correct, reinforced in FAQ. Fact 10 ("Impersonation Latency" defined verbatim and
  correctly, explicitly called "the canonical failure mode"). Fact 11 (Ed25519, max 3 hops, call-SID
  nonce binding correct; "monotonic scope narrowing" and NPI regex format are omitted rather than
  contradicted). Fact 12 clean.
- **`docs/assets/archive/NHID-Clinical-Master-Knowledge-Archive.pdf`**: Out of scope for content
  checks per task instructions (this PDF IS the canonical source). Content was not compared against
  the fact table; only rendering/OCR fidelity was checked (see Finding 9). The A_nocf/NOCF formula
  block, `_DBC_IMPERSONATION_PHRASES` and `_ESCALATION_TRIGGERS` code blocks, JSON examples, curl
  commands, YAML CTS templates, AWS SAM snippet, and repository tree all rendered correctly with no
  truncation or misalignment, confirming the PDF build pipeline preserves code/table fidelity well
  apart from the footer glyph issue.

No control-ID capitalization problems (e.g., "Pdx-01," "EIT 01") were found in any of the 6 spec
PDFs or the canonical archive PDF — IDG-01, PDX-01, DBC-01, EIT-01, and ATR-01 are consistently
rendered in all-caps with the hyphenated two-digit format throughout. No missing-space word-run
artifacts, broken hyphenation (beyond normal justified-text wrapping), or garbled/replacement
characters were found in any spec PDF (all are vector-native PDF output — LaTeX/LuaTeX or
ReportLab-generated — not scanned/OCR'd documents, so this class of defect is largely inapplicable
except for the one footer-glyph issue in the canonical archive PDF).

---

## Bonus Finding (non-PDF, explicitly requested in task scope)

### Bonus 1 — Stale API base URL in `docs/v2-integration-guide.md`

- **File:** `docs/v2-integration-guide.md` (not a PDF — same staleness family as Findings 3 and 6)
- **Locations:** Line 20 (`curl` example) and line 45 (`NHID = "https://dc2ipcqs7k..."` Python
  variable assignment).
- **Problematic text:** `https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod` (both
  locations).
- **Why it's inconsistent:** Violates **canonical fact 13** — same broken us-east-2 stack issue.
- **Recommended correction:** Replace both occurrences with
  `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod`.
- **Discrepancy note:** The task brief stated this file has the stale URL "in 3 places." On direct
  inspection (`grep -n "dc2ipcqs7k" docs/v2-integration-guide.md`), only **2** occurrences were
  found (lines 20 and 45). This is logged as a minor inaccuracy in the task brief itself, not a new
  finding about the repository — flagging for transparency in case a third occurrence exists in a
  revision not visible at review time, or the brief's count was simply off by one.
- **Authority note:** This is a markdown doc, not a PDF, so it is technically out of this review's
  PDF-editing restriction — however, per task instructions, no repository file other than this new
  report was edited. This finding is logged for a maintainer to fix directly in
  `docs/v2-integration-guide.md`.

### Bonus 2 — Stale API base URL in `docs/MASTER-KNOWLEDGE-ARCHIVE.md` itself (discovered during review)

- **File:** `docs/MASTER-KNOWLEDGE-ARCHIVE.md` (the canonical source of truth itself)
- **Locations:** Lines 666, 1088, 1432, 1710, 1721, 1899 (6 occurrences, confirmed via
  `grep -n "dc2ipcqs7k"`).
- **Problematic text:** `https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod` (all 6
  locations, in various contexts: a "Base URL" field, three `curl` examples, an `<img>` badge URL,
  and a Python `API_BASE` variable assignment).
- **Why it's flagged:** This is the one canonical fact (13) where the master archive is **not**
  currently authoritative — it has the same staleness as the PDFs derived from it. This materially
  affects the "regenerate from the master archive" recommendation given throughout this report for
  fact-13 findings: regenerating today would simply reproduce the stale URL.
- **Recommended correction:** Update all 6 occurrences in `docs/MASTER-KNOWLEDGE-ARCHIVE.md` to
  `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod`, then regenerate dependent PDFs
  (Core Specification, Technical Playbook) and `docs/v2-integration-guide.md`.
- **Authority note:** Not corrected as part of this task (task scope is read-only review +
  creation of this one report file; editing `docs/MASTER-KNOWLEDGE-ARCHIVE.md` is out of scope here
  and should be done as a separate, deliberate documentation fix).

### Bonus 3 — Stale control-ID expansions in `README.md` (discovered during review)

- **File:** `README.md`
- **Locations:** Line 124 (`| **PDX-01** | PHI Data Exchange Gate | ... |`) and line 126
  (`| **EIT-01** | Escalation & Intervention | ... |`).
- **Why it's flagged:** Same defects as Findings 1, 2, and 5 (canonical facts 1 and 2), found by
  chance while cross-checking adapter/test counts in the repo. Not a PDF, so out of primary task
  scope, but logged here since it is the same family of staleness and a maintainer fixing the PDFs
  will likely want to fix the top-level README at the same time.
- **Recommended correction:** Change "PHI Data Exchange Gate" → "Pre-Data Exchange Gate"; change
  "Escalation & Intervention" → "Escalation Implementation Test."
- **Authority note:** Not corrected as part of this task (out of scope — README.md is not one of
  the 6 PDFs and not the one markdown file this task was scoped to create/edit).

---

## Disposition

Per task scope, **no PDF files were modified**, and **no repository file other than this new report
(`docs/pdf-consistency-and-grammar-review.md`) was created or edited**. All corrections listed above
are recommendations only. The project convention — confirmed accurate for 12 of the 13 canonical
facts — is that `docs/MASTER-KNOWLEDGE-ARCHIVE.md` and the source code are authoritative, and that
stale PDFs should be regenerated from the master archive at the next rebuild rather than hand-edited
PDF-side. The one exception is fact 13 (API base URL), where the master archive itself needs a
direct content fix first (see Bonus Finding 2) before regeneration will produce correct PDFs.
