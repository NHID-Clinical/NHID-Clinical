---
name: nhid-failure-archaeology
description: >-
  Load BEFORE you start investigating any anomaly, "bug", or surprising number in the
  NHID-Clinical repo — many of them are already-settled battles with a documented root
  cause, and re-fighting them wastes a session. This is the chronicle: every major
  investigation, dead end, rejected fix, and revert as symptom → root cause → evidence →
  status. Load it when you see low or suspiciously-high detection rates, a 0.0% control,
  a CI count mismatch, a "we should add more keywords" impulse, an FP you think is a bug,
  or a stale branch. It tells you what is decided and must not be reopened, and which
  numbers are superseded. Trigger phrases: "why is DBC-01 low", "should we expand the
  lexicon", "ATR-01 is 0%", "the old rates say", "is this already known".
---

# NHID-Clinical Failure Archaeology

Verified as of 2026-07-04. Before you re-investigate anything, **grep here first**:
`grep -rn "<symptom keyword>" docs/MASTER-KNOWLEDGE-ARCHIVE.md` and read the surrounding
section. Most "bugs" in this repo are settled.

## Usage protocol

1. Search the archive (`docs/MASTER-KNOWLEDGE-ARCHIVE.md`) for your symptom.
2. Match it against the settled-battles table below.
3. If it is settled: do NOT reopen it. Read the status. If you believe the settlement is
   wrong, that is a research question — see `nhid-research-methodology`, not a bug fix.
4. If it is genuinely new: proceed, but record it the same way (symptom → root cause →
   evidence → status) when you close it.

## Settled battles (do not re-fight)

| # | Symptom | Root cause | Evidence | Status |
|---|---|---|---|---|
| 1 | DBC-01 & EIT-01 = **0 detections** in the synthetic eval loop | Harness wiring: `build_session/build_event` didn't thread `escalation_path_available` and nest `deceptive_artifact_flags` under `healthcare_governance`. NOT an engine defect. | archive §2.5; regression tests `test_dbc01_detected_not_zero`, `test_eit01_detected_not_zero` | **FIXED** (284→294) |
| 2 | DBC-01 real-corpus detection **0.5%** | Naturalistic language ≠ verbatim lexicon phrases | archive §2.5; Fabricate run | **SUPERSEDED** by #6 (number was also distorted) |
| 3 | "Should we keep expanding the DBC-01 phrase list?" | Substring matching has a **proven ceiling**: broad keywords = 142 TP / 260 FP; negation-filtered = 106 / 153. Both net-negative. | archive §2.5; `scripts/mine_heuristic_candidate.py`; §9.1 #7 zero-FP bar | **SETTLED — no more keyword broadening** |
| 4 | ATR-01 real-corpus detection **0.0%** | Untestable in transcript replay: corpus lacks field-level signal AND `build_event()` hardcodes audit fields. No conversational corpus can exercise ATR-01. | archive §2.5; correct path = `tests/failure_injection_harness.py` + CTS `ATR-01-FAIL-MISSING` | **SETTLED — eval-path limitation, not a heuristic gap** |
| 5 | Residual implicit DBC-01 misses ("we-language", ownership framing) | Implicit impersonation is non-lexical; more phrase code is brittle | archive §2.5; routed to `docs/dbc01-human-review-sop.md`, code-enforced via `should_route_to_review` + `dbc01_review_queue` + `scripts/resolve_dbc01_review.py` | **SETTLED — human-in-the-loop, formalized** (306→327) |
| 6 | Earlier per-rule rates (DBC 0.5–2.5%, EIT 94.7%) were **untrustworthy** | **Three distinct causes, one real**: (a) adapter blanked `identity_assertion_text` on caller turns → IDG-01 fired every post-disclosure turn; (b) **label leakage** — `escalation_path_available = not eit01_violation` wired ground truth into the detector (EIT ~95% was meaningless); (c) genuine gap — no mid-call implied-humanity scan | archive §2.5.1; `docs/devlog_2026-07-02_eval-repair.md`; `scripts/confusion_matrix.py` | **SETTLED — supersedes §2.5.** Corrected: DBC 87–98%, EIT ~98% |
| 7 | EIT-01 escalation semantics ambiguous | Needed a decision among three semantics | archive §2.5.1 | **SETTLED — caller-anchored ask-again** (honored-anywhere 43–60%, after-last-ask 43% adversarial, caller-anchored ~98%; ISO FP 17.1%→5.7%) |
| 8 | DBC-01 Tier C carries ~4–11% FP on compliant speech | High-recall implied-humanity has irreducible precision cost concentrated in 3 phrases (`our team` 344/2, `i'll personally` 40/2, `my team` 30/2) | archive §2.5.1 | **DECISION: keep lexicon as-is.** OPEN sub-question: Tier C live vs eval-gated (owner **Bree**) |
| 9 | FHIR Bundle entries missing `fullUrl` | Emitter omitted per-entry `fullUrl` | commit `6c42198` + regression test | **FIXED** |
| 10 | Beacon consent-refusal transfer path broken | Broken transfer routing on consent refusal | commit `aca79f2` (#269) | **FIXED** |
| 11 | Compass widget stuck in call mode | Legacy widget bundle; needed `convai-widget-embed` | commit `1f63fea` (#297) | **FIXED** |
| 12 | FHIR-validation CI flaky | CI depended on external `tx.fhir.org` | commits `70caabc`/`b04099d`/`501f907` | **FIXED — external dependency removed** |

## Superseded numbers — do not cite as current

- Archive **§2.5** per-rule rates (DBC 0.5%, EIT 94.7%, PDX 58.6%) are **superseded by §2.5.1**.
  Always cite §2.5.1 for current detection numbers, and prefer re-running
  `scripts/confusion_matrix.py` (see `nhid-diagnostics-and-tooling`).

## Development-arc chronology (for orientation)

Single long-lived branch → ~60 numbered PRs to `main`. Rough ladder by test count:
v1.3 final (**284**) → synthetic eval loop (**294**, silent-zero bug `3f91845`) → Fabricate
adapter saga (**303→306**, DBC 0.5%→2.5%) → DBC-01 human-review pivot (**327**, `35713a8`,
`db9907b`) → v1.1 eval repair (**330**, `ed097f4`). Verify any hash with
`git show --stat <hash>`.

## The meta-pattern: recurring fact-drift

Stale test counts, control names, dead URLs, and unverified regulatory claims repeatedly
drifted out of sync (e.g. an unverified NIST CAISI claim was removed; a MACPAC date corrected).
This recurrence is *why* archive §9.1 invariant #5 (atomic count propagation) exists. Treat any
number that appears in more than one file as drift-prone.

## Dead / abandoned work

- Branch **`backup-local-work-1781661162`** (frozen ~2026-06-17): an orphaned local backup.
  Its unique content includes an **abandoned GitHub-Actions deploy workflow** (`deploy.yml`
  added then immediately reverted) and a Beacon-outbound-strip that was later reversed on
  mainline. It is not lost work — the mainline re-landed the good parts. Do not resurrect the
  deploy experiment without an owner decision.

## When NOT to use this skill

- Actively triaging a live failure (symptom → fix now) → `nhid-debugging-playbook`.
- The rules for making the fix → `nhid-change-control`.
- Why the system is shaped this way (design, not history) → `nhid-architecture-contract`.
- How to run the measurement tools → `nhid-diagnostics-and-tooling`.
- Siblings: `nhid-domain-reference`, `nhid-config-and-flags`, `nhid-build-and-env`,
  `nhid-run-and-operate`, `nhid-validation-and-qa`, `nhid-docs-and-positioning`,
  `nhid-dbc01-semantic-ceiling-campaign`, `nhid-proof-and-analysis-toolkit`,
  `nhid-research-frontier`, `nhid-research-methodology`, `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- Settled battles source: `docs/MASTER-KNOWLEDGE-ARCHIVE.md` §2.5 and §2.5.1 — read both.
- Verify any commit: `git show --stat <hash>` (e.g. `ed097f4`, `db9907b`, `35713a8`).
- Dead branch: `git log --oneline backup-local-work-1781661162 2>/dev/null | head` (may be pruned).
- Ceiling numbers: `grep -n "142\|260\|ceiling" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
