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
| 1 | My Story: Working in Healthcare Operations | I — The Problem | **Merged** (PR #327: [chapter](chapters/chapter-01-my-story.md) · [editorial review](editorial/chapter-01-review.md)) |
| 2 | The Rise of AI Voice Agents | I — The Problem | **Drafted** ([chapter](chapters/chapter-02-the-rise-of-ai-voice-agents.md) · [editorial review](editorial/chapter-02-review.md)) |
| 3 | The Identity Problem | I — The Problem | Not started |
| 4 | Impersonation Latency | I — The Problem | Not started |
| 5 | What is NHID-Clinical? | II — The Framework | Not started |
| 6 | The Five Core Controls | II — The Framework | Not started |
| 7 | Behavioral Governance | II — The Framework | Not started |
| 8 | Operational Architecture | II — The Framework | Not started |
| 9 | Shadow Evaluations | III — Implementation | Not started |
| 10 | Policy Enforcement | III — Implementation | Not started |
| 11 | Authorization | III — Implementation | Not started |
| 12 | Audit Trails | III — Implementation | Not started |
| 13 | Integration with Existing Healthcare Systems | III — Implementation | Not started |
| 14 | Pilot Programs | IV — Enterprise Adoption | Not started |
| 15 | Metrics | IV — Enterprise Adoption | Not started |
| 16 | Risk Management | IV — Enterprise Adoption | Not started |
| 17 | Governance | IV — Enterprise Adoption | Not started |
| 18 | Industry Adoption | V — The Future | Not started |
| 19 | Standards Alignment | V — The Future | Not started |
| 20 | The Future of Trusted AI Communication | V — The Future | Not started |

## Directory layout

```
playbook/
├── README.md            # This file — outline and status tracker
├── chapters/            # Manuscript chapters, one Markdown file each
└── editorial/           # Post-draft editorial reviews, one per chapter
```
