# NHID-Clinical: The Operational Playbook for Trusted AI Voice Agents in Healthcare

**Working manuscript — drafted chapter by chapter, with an editorial review after each chapter.**

This playbook is an operational guide, not a specification, standards document,
or research paper. It explains why NHID-Clinical exists, the operational problem
it solves, how healthcare organizations implement it, and why it matters before
regulations require it. The register it aims for is that of O'Reilly and
Microsoft Press titles, NIST implementation guides, and enterprise architecture
guides.

All technical claims in the manuscript are grounded in the NHID-Clinical
reference materials in this repository — the v1.3 specification, the
[Executive Brief](../docs/executive-brief.md), the
[Tier 0 Shadow Pilot Kit](../docs/pilot-kit/README.md), and the reference
implementation. Where the framework's own materials describe something as
immature, in progress, or not yet proven, the manuscript says so.

## Audience

Healthcare executives · AI governance leaders · compliance teams · payer and
provider organizations · healthcare CIOs and CISOs · voice AI vendors · health
IT architects · regulators and standards organizations.

## Structure of every chapter

Each chapter opens with a real-world scenario, then provides: an executive
summary, why it matters, real-world examples, diagrams to include (described in
text), operational guidance, implementation guidance, key takeaways, and
references to NHID-Clinical concepts.

## Manuscript status

| # | Chapter | Part | Status |
| :- | :-- | :-- | :-- |
| 1 | My Story: Working in Healthcare Operations | I — The Problem | **Merged** (PR #327: [chapter](chapters/chapter-01-my-story.md) · [review](editorial/chapter-01-review.md)) |
| 2 | The Rise of AI Voice Agents | I — The Problem | **Merged** (PR #328: [chapter](chapters/chapter-02-the-rise-of-ai-voice-agents.md) · [review](editorial/chapter-02-review.md)) |
| 3 | The Identity Problem | I — The Problem | **Drafted** ([chapter](chapters/chapter-03-the-identity-problem.md) · [review](editorial/chapter-03-review.md)) |
| 4 | Impersonation Latency | I — The Problem | **Drafted** ([chapter](chapters/chapter-04-impersonation-latency.md) · [review](editorial/chapter-04-review.md)) |
| 5 | What is NHID-Clinical? | II — The Framework | **Drafted** ([chapter](chapters/chapter-05-what-is-nhid-clinical.md) · [review](editorial/chapter-05-review.md)) |
| 6 | The Five Core Controls | II — The Framework | **Drafted** ([chapter](chapters/chapter-06-the-five-core-controls.md) · [review](editorial/chapter-06-review.md)) |
| 7 | Behavioral Governance | II — The Framework | **Drafted** ([chapter](chapters/chapter-07-behavioral-governance.md) · [review](editorial/chapter-07-review.md)) |
| 8 | Operational Architecture | II — The Framework | **Drafted** ([chapter](chapters/chapter-08-operational-architecture.md) · [review](editorial/chapter-08-review.md)) |
| 9 | Shadow Evaluations | III — Implementation | **Drafted** ([chapter](chapters/chapter-09-shadow-evaluations.md) · [review](editorial/chapter-09-review.md)) |
| 10 | Policy Enforcement | III — Implementation | **Drafted** ([chapter](chapters/chapter-10-policy-enforcement.md) · [review](editorial/chapter-10-review.md)) |
| 11 | Authorization | III — Implementation | **Drafted** ([chapter](chapters/chapter-11-authorization.md) · [review](editorial/chapter-11-review.md)) |
| 12 | Audit Trails | III — Implementation | **Drafted** ([chapter](chapters/chapter-12-audit-trails.md) · [review](editorial/chapter-12-review.md)) |
| 13 | Integration with Existing Healthcare Systems | III — Implementation | **Drafted** ([chapter](chapters/chapter-13-integration-with-existing-healthcare-systems.md) · [review](editorial/chapter-13-review.md)) |
| 14 | Pilot Programs | IV — Enterprise Adoption | **Drafted** ([chapter](chapters/chapter-14-pilot-programs.md) · [review](editorial/chapter-14-review.md)) |
| 15 | Metrics | IV — Enterprise Adoption | **Drafted** ([chapter](chapters/chapter-15-metrics.md) · [review](editorial/chapter-15-review.md)) |
| 16 | Risk Management | IV — Enterprise Adoption | **Drafted** ([chapter](chapters/chapter-16-risk-management.md) · [review](editorial/chapter-16-review.md)) |
| 17 | Governance | IV — Enterprise Adoption | **Drafted** ([chapter](chapters/chapter-17-governance.md) · [review](editorial/chapter-17-review.md)) |
| 18 | Industry Adoption | V — The Future | **Drafted** ([chapter](chapters/chapter-18-industry-adoption.md) · [review](editorial/chapter-18-review.md)) |
| 19 | Standards Alignment | V — The Future | **Drafted** ([chapter](chapters/chapter-19-standards-alignment.md) · [review](editorial/chapter-19-review.md)) |
| 20 | The Future of Trusted AI Communication | V — The Future | **Drafted** ([chapter](chapters/chapter-20-the-future-of-trusted-ai-communication.md) · [review](editorial/chapter-20-review.md)) |

## Next editorial milestone

All twenty chapters are drafted with per-chapter reviews. The next
milestone is the **whole-manuscript consistency pass** against the
accumulated queue (collected in the
[Chapter 20 review](editorial/chapter-20-review.md), "Whole-manuscript
notes"): front-matter items (no-legal-advice disclaimer, the
framework-mechanisms vs. book-synthesis convention, the extraction-card
list), the composite/anticipated labeling retrofit, the
invented-precision sweep, claim-strength verb verification against the
framework's source materials, and the paired figure commissions. After
that: front matter, then external readers (payer operations, voice-AI
vendor engineering, compliance audit).

## Directory layout

```
playbook/
├── README.md            # This file — outline and status tracker
├── chapters/            # Manuscript chapters, one Markdown file each
└── editorial/           # Post-draft editorial reviews, one per chapter
```
