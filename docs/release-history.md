# NHID-Clinical — release history

Moved here from the public site on 2026-09-04. `news.html` was a standalone
route maintained to hold a changelog, and a changelog is something people check
rather than a destination they arrive at, so it did not survive the destination
test in `ia-disposition.md` §4.3. The entries themselves are a dated record and
are preserved verbatim below.

**Two entries carry statements that are no longer true.** They are annotated
rather than edited, because silently rewriting a dated announcement falsifies
the record — the annotation is the correction.

| Entry | Issue |
|---|---|
| *Pilot Partners Sought* | Announced active recruitment of pilot organisations. **No design partners, pilot partners, customers or deployments exist**, and none may be represented as existing |
| *NHID-Clinical v1.3 Published* | Says the proposal "suggests four behavioral expectations". v1.3 defines **five** controls: IDG-01, PDX-01, DBC-01, EIT-01 (the four deterministic behavioral controls) and ATR-01 (audit and evidence) |

---

## Corpus Evaluation Path Corrected — IDG-01 and EIT-01
*August 2026 · Release*

The first run of the 150-session synthetic corpus evaluation reported IDG-01 at a 100% false-positive rate and EIT-01 at 0% detection. Those numbers were real, but they measured defects in the corpus-evaluation path rather than in the policy engine, which was not modified.

A corpus result of 100% describes a 150-session synthetic dataset with two seeded escalation failures. It is a floor, not a validation, and Tier 0 remains observe-only.

[Review the Evidence Pack](/evidence-pack.html)

## Why Identity Is the Missing Layer of Responsible AI
*July 2026 · Commentary*

Independent commentary on Impersonation Latency and the five NHID-Clinical controls, mapped to NIST AI RMF, ISO/IEC 42001, and HIPAA.

[Read the commentary](/identity-layer.html)

## DBC-01 Coverage Expanded from Real-Corpus Mining
*June 2026 · Release*

Detection of DBC-01 (Deceptive Behavior Claim) against real conversational phrasing — measured on the Fabricate Battle-Test Corpus (550 real-world voice AI conversations) — was 0.5% prior to this update. Mining the corpus for missed phrasing patterns and additively expanding the heuristic phrase list raised that to 2.5%.

Superseded. These figures were accurate when published. The corpus baseline was revised on 2026‑07‑31 after the Phase 4 fixes (artifact isolation, escalation honor patterns), and detection is now measured per conversation rather than per turn. Current figures are on the [Evidence Pack](/evidence-pack.html), computed by scripts/confusion_matrix.py . This entry is left unedited as a historical record.

[Evidence Pack](/evidence-pack.html)

## Community Channels Consolidated to GitHub
*June 2026 · Community*

Discord and Reddit are no longer used for NHID-Clinical community discussion. All community activity — questions, implementation experiences, and proposal feedback — now happens in GitHub Discussions on the main repository.

[Join the Discussion](https://github.com/NHID-Clinical/NHID-Clinical/discussions)

## v1.3 Final — Milestone Closeout
*June 2026 · Release*

Six previously-open items are closed out under the existing v1.3 spec version — no version bump, no v1.4 branding. Shipped this cycle:

[Implementation Registry](/registry.html) · [View the Registry](/registry.html) · [Developers & Artifacts](/developers.html)

## v1.3 Reference Implementation Live
*June 2026 · Release*

The reference implementation is now fully operational. Key deliverables shipped this cycle:

Still early — no production pilots yet. Actively seeking first shadow evaluation partners.

[Developers & Artifacts](/developers.html)

## NHID-Clinical v1.3 Published
*May 2026 · Release*
> **Correction.** "Four behavioral expectations" undercounts the control set.
> v1.3 defines five controls; four are behavioral and ATR-01 is the audit and
> evidence control. See `specification.html`.

v1.3 is the first public release of this open proposal. It suggests four behavioral expectations for AI voice agents in healthcare payer–provider administrative calls, focused on early disclosure of automated status.

[About the proposal](/about.html) · [Download PDF](/specs/NHID-Clinical-v1.3-Overview.pdf)

## Pilot Partners Sought
*May 2026 · Open Proposal*
> **Superseded.** This announced active recruitment. There are no pilot
> partners, design partners, customers or deployments, and NHID-Clinical is
> not currently recruiting. The shadow evaluation remains available to run
> independently; nothing about it involves joining a programme.

We are actively seeking payer and provider organizations to run a 90-day shadow evaluation — observe-only, non-intercepting, no vendor changes. Observe incoming AI voice calls against the v1.3 behavioral baseline and help shape the standard before v2 ships.

[Start a Shadow Evaluation](/for-payers.html)

## Submitted to NIST
*January 2026 · Open Proposal*

NHID-Clinical was submitted as a public comment to NIST docket NIST-2025-0035 (AI-agent security). Comment ID: NIST-2025-0035-0026. This is a public comment — not a regulatory filing or endorsement. The RFI drew 932 public comments in total before the period closed in March 2026.

[View on Regulations.gov](https://www.regulations.gov/comment/NIST-2025-0035-0026)

## Community Channels Open
*May 2026 · Community*

NHID-Clinical community discussion channels are now open. Join to ask questions about this proposal, share implementation experiences, and contribute to future versions. (Update, June 2026: community discussion has since moved to GitHub Discussions — see the June 2026 announcement above.)

[Join the discussion on GitHub](https://github.com/NHID-Clinical/NHID-Clinical/discussions)
