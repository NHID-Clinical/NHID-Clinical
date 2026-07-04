---
name: nhid-docs-and-positioning
description: >-
  Load when you write or edit any NHID-Clinical document or public claim — the master
  archive, a devlog, the README, website pages, or anything stating what the project can
  do. Load it before updating docs/MASTER-KNOWLEDGE-ARCHIVE.md, before publishing a
  detection number, or before wording a capability/positioning statement. It gives the
  archive's structure, the LIVE-vs-HISTORICAL rule, supersede-don't-delete, the house
  style (honest framing, no unverified regulatory claims, canonical control names), and
  the reproducibility bar for external claims. Trigger phrases: "update the archive",
  "write a devlog", "positioning", "is this claim ok", "can we say we're certified",
  "which control name is right".
---

# NHID-Clinical Docs & Positioning

Verified as of 2026-07-04. The archive is the memory of the project; the website is a public
claim surface. Both drift. Your job is to keep them honest and consistent.

## Docs of record

| Doc | Role |
|---|---|
| `docs/MASTER-KNOWLEDGE-ARCHIVE.md` | The knowledge base. Sections `## 1`–`## 23` + Changelog. |
| `docs/nhid-clinical-technical-specification.md` | **Authoritative for control names & definitions.** |
| `conformance/nhid_conformance_test_suite_v1.yaml` | Machine-readable ground truth for expected behavior. |
| `docs/dbc01-human-review-sop.md` | The human-review SOP. |
| `docs/devlog_YYYY-MM-DD_*.md` | Dated journals of significant work (e.g. `devlog_2026-07-02_eval-repair.md`). |

Archive top-level map (verify with `grep -nE "^## " docs/MASTER-KNOWLEDGE-ARCHIVE.md`): 1
Executive Vision · 2 Core Framework (incl. §2.5 eval loop, §2.5.1 v1.1 repair) · 3 Governance ·
4 Identity & Trust · 5 Agent Verification · 6 Technical Architecture · 7 Roadmap · 8 Coding &
Development · 9 Claude Code / LLM Tasking (incl. §9.1 invariants) · 10–18 content/positioning ·
19 Decisions Made · 20 Future Work · 21 Templates · 22 FAQ · 23 Source Appendix (incl. §23.3
test-file index) · Changelog.

## LIVE vs HISTORICAL (the #1 doc error)

- **LIVE** content states the *current* invariant (e.g. "the suite is 330 passed"). Update it
  when the truth changes.
- **HISTORICAL** content is a frozen record — the changelog, the test-count progression ladder
  (284→294→303→306→327→330), a past measurement. **Never edit a historical row to the new
  value.** A row that says "294" is a fact about the past. Recurring drift came exactly from
  "fixing" these. If unsure, treat it as historical.

## Supersede, don't delete

When a measurement is invalidated, annotate it "superseded by §X" and add the replacement; keep
the old text. **Canonical example**: §2.5's per-rule rates (DBC 0.5%, EIT 94.7%) are marked
superseded and §2.5.1 carries the corrected v1.1 numbers. History is evidence.

## House style

- **Honest framing.** Engine detection numbers are *measurements against synthetic corpora*, not
  conformance or certification. Keep a "documented, not masked" limits section where relevant.
- **No unverified regulatory claims.** Incidents: an unverified NIST CAISI claim was removed
  (commit `23c7c56`); a MACPAC date was corrected (`d807aa9`). Verify any regulatory/standards
  reference before stating it (`git show 23c7c56 --stat`).
- **Canonical control names** (from the spec — do not paraphrase):
  - IDG-01 = **Identity Disclosure Gate**
  - PDX-01 = **Pre-Data Exchange Gate** (NOT "PHI Data Exchange Gate")
  - DBC-01 = **Deceptive Behavior Check**
  - EIT-01 = **Escalation Implementation Test** (NOT "Escalation and Intervention")
  - ATR-01 = Audit Trail Requirements

## External positioning

- **Novel vs known**: what's distinctive is *deterministic behavioral conformance testing* plus
  a *reproducible disjoint-population confusion-matrix methodology*. Generic "our AI discloses it's
  an AI" is not novel — don't lead with it.
- **Reproducibility bar for any published number**: it must be reproducible as
  **command + corpus + expected output** (e.g. `scripts/confusion_matrix.py fixtures/fabricate/...`
  → the §2.5.1 table). If you can't give that triple, don't publish the number.
- **Never** claim certification, accreditation, or that a vendor is "NHID-certified" — this is a
  voluntary baseline, not an accreditation body.

## Website drift watch

The repo doubles as `nhid-clinical.org` (root `*.html`). Pages most prone to stale numbers:
`README.md` (badges + prose), `evidence-pack.html`, `simulator.html`. After any count or rate
change, grep these for the old number and reconcile (this is a recurring maintenance cost).

## When NOT to use this skill

- The mechanics/gates of a change → `nhid-change-control`.
- What counts as valid evidence → `nhid-validation-and-qa`.
- The history behind a superseded number → `nhid-failure-archaeology`.
- Domain definitions to cite → `nhid-domain-reference`.
- Siblings: `nhid-debugging-playbook`, `nhid-architecture-contract`,
  `nhid-config-and-flags`, `nhid-build-and-env`, `nhid-run-and-operate`,
  `nhid-diagnostics-and-tooling`, `nhid-dbc01-semantic-ceiling-campaign`,
  `nhid-proof-and-analysis-toolkit`, `nhid-research-frontier`, `nhid-research-methodology`,
  `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- Archive map: `grep -nE "^## " docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
- Superseded example: `grep -n "superseded\|2.5.1" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
- Control names: `grep -nE "Identity Disclosure Gate|Pre-Data Exchange|Deceptive Behavior|Escalation Implementation" docs/nhid-clinical-technical-specification.md`.
- Reconciliation incidents: `git show 23c7c56 --stat` and `git show d807aa9 --stat`.
- Drift-prone pages: `grep -rn "330\|91.5\|passing" README.md evidence-pack.html simulator.html | head`.
