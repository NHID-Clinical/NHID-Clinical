# NHID-Clinical — July 12 Execution Plan

**Prepared:** 2026-07-08 · **Deadline:** 2026-07-12 · **Budget:** $50 in credits, plan resets Thursday 2026-07-09
**Working branch:** `claude/nhid-clinical-july-deadline-che6r8` · **Owner decisions:** Bree

This plan is written to be handed directly to Claude Code sessions. Every task names the
skill(s) to load first, the change-control class, and the model tier to run it on.
Facts below were verified against the repo on 2026-07-08 (commands in each section).

---

## 0. Verified state of the repo (as of 2026-07-08)

| Fact | Evidence |
|---|---|
| Engine baseline reproduces exactly: IDG-01 100%/0 FP, PDX-01 100%/0 FP, DBC-01 **183/200 (91.5%) / 5 FP (3.9%)**, EIT-01 98.2%/2.4% | `python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv` — matches the 2026-07-04 skill baseline, so the engine/lexicon has NOT moved |
| Test invariant | 330 passed / 18 skipped (`grep UNIT_EXPECTED scripts/validate_ci.py`) — must be re-verified in any session before merging anything (`python scripts/validate_ci.py`) |
| Branch state | `claude/nhid-clinical-july-deadline-che6r8` is **~60 commits ahead of `main`** (93 files, +7,855 / −1,295) with **no open PR**. It carries: the entire `webplatform/` FastAPI demo layer (6 pages + API + its own test suite), site polish (for-payers, evidence-pack, shadow-eval), Pages-deploy hardening, PDF regeneration, and logo churn |
| `webplatform/` | Thin FastAPI layer over the real engine (no reimplemented policy logic), own SQLite DB, own tests via `python -m pytest webplatform/tests -q`. Not covered by the 330-count invariant (which counts `tests/` only) — confirm this in-session before merge |
| Open owner decision | **DBC-01 Tier C live vs eval-gated** (FP cost: CSV 3.9%, adversarial 11.4%, baseline 1.8%, v2_iso 0%). Owned by Bree; must NOT be resolved silently (change-control §8) |
| Website | Repo doubles as nhid-clinical.org via GitHub Pages (`CNAME`, `.nojekyll`). **Branch work is not live until merged to `main`** |
| Live API | AWS Lambda via SAM (`template.yaml`, `make deploy`); FastAPI alt on Railway |

---

## 1. Where Fable 5 fits this codebase

Fable 5 is the premium reasoning tier ($10/$50 per MTok — 2× Opus 4.8). In this repo it earns
its price in exactly three places, all of which are *judgment-heavy, evidence-gated* work
where a wrong call re-fights a settled battle:

1. **The DBC-01 semantic-ceiling campaign** (`nhid-dbc01-semantic-ceiling-campaign`) —
   characterizing the 17 residual misses, designing the LLM-judge second stage with its
   proof obligation (beat 91.5% detection at ≤3.9% FP), and writing the promotion case.
   This is the project's hardest live problem and the one place "more intelligence"
   directly converts to a result.
2. **Change-control-gated engine work** — anything touching `src/nhid_policy_engine_v1.py`
   where a mistake violates a §9.1 invariant (zero-FP bar, additive-only lexicons,
   atomic count propagation).
3. **Decision memos for Bree** — the Tier C gating memo (Section 4) where the framing of
   evidence determines a production decision.

Everything else in this plan (site work, webplatform polish, docs, CI plumbing, drift
sweeps) is well-specified execution and should run on cheaper models (Section 6).
Do **not** burn Fable 5 tokens on HTML edits or count-propagation bookkeeping.

---

## 2. Prioritized ship list (what realistically lands by July 12)

Ordered by genuine benefit to the project, not ease. Each item: skill(s) → gate → model.

### P0 — Land the stranded work (Days 1–2, Thu–Fri)

**P0.1 — Verify the branch green, open the PR, merge to `main`.**
~60 commits of finished work (webplatform, site polish, deploy hardening) are invisible
to the world until merged — the site serves from `main`. This is the single
highest-leverage action available.
- Steps: fresh env per `nhid-build-and-env` (venv, `pip install -r requirements.txt`,
  expect **330 passed / 18 skipped**, `validate_ci.py` → `CI PASS: 330 passed`); run
  `python -m pytest webplatform/tests -q` separately; re-run the confusion matrix
  (must stay 183/200 / 5 FP); then PR → review → merge.
- Skills: `nhid-build-and-env`, `nhid-change-control` (pre-commit checklist),
  `nhid-diagnostics-and-tooling`.
- Gate: test-count invariant + confusion-matrix no-regression. **Decision needed from
  Bree: merge approval** (Section 4).
- Model: Sonnet 5.

**P0.2 — README graphics teardown (brainstorm-gated).**
Strip or fence the current README visuals you dislike; replace nothing yet. All
replacements go through Section 5's brainstorm queue. Interim state: a clean, text-first
README that doesn't embarrass the project (badges + mermaid diagram stay — they're
generated, not "graphics").
- Skills: `nhid-docs-and-positioning` (drift-prone pages list, honest framing).
- Gate: doc-only. Model: Sonnet 5.

### P1 — Zero-touch hardening (Days 2–3)

**P1.1 — Nightly self-verification workflow.**
A scheduled GitHub Action (cron) that runs: `validate_ci.py`, the confusion matrix with
an assertion against the committed baseline numbers, the `nhid-gates.yml` determinism +
perf jobs, and a link check over the root `*.html` pages. Failure opens an issue
automatically. This is what makes "no manual intervention until governance updates"
true — drift (the repo's recurring meta-failure per `nhid-failure-archaeology`) gets
caught by a robot instead of a future session.
- Skills: `nhid-change-control` (this touches CI — classify carefully; do NOT alter the
  existing 330-count job), `nhid-diagnostics-and-tooling`.
- Gate: additive workflow only; existing `ci.yml` job names untouched.
- Model: Sonnet 5.

**P1.2 — Number-drift sweep + reconciliation.**
Per `nhid-docs-and-positioning`, grep `README.md`, `evidence-pack.html`, `simulator.html`
(and the new webplatform templates) for every published count/rate (330, 91.5, 98.2,
66 middleware tests…) and reconcile against the live invariants. Add the grep set to the
P1.1 nightly job so drift is detected, not just fixed once.
- Skills: `nhid-docs-and-positioning`, `nhid-failure-archaeology` (LIVE vs HISTORICAL —
  never "fix" a historical row).
- Gate: doc-only. Model: Sonnet 5 (Haiku 4.5 acceptable).

**P1.3 — Demo/API smoke monitor.**
Extend the nightly job (or a tiny scheduled Lambda ping) to hit `GET /health` and one
no-auth adapter route on the live API, plus the badge endpoint. Zero-touch means knowing
when the live demo dies before a payer does.
- Skills: `nhid-run-and-operate` (route table), `nhid-config-and-flags` (no secrets in CI;
  only no-auth routes).
- Model: Sonnet 5.

### P2 — The one capability bet that fits the window

**P2.1 — DBC-01 campaign, Phases 0–1 + eval-only LLM-judge prototype (option a).**
Phase 0 is already done (baseline reproduced 2026-07-08). Phase 1: pull the 17 missed
transcripts (IDs are in the confusion-matrix output) and classify each as
single-cue-implicit vs fully non-lexical. If mostly non-lexical (expected, per the settled
ceiling proof), prototype the judge **behind an eval-only flag** on DBC-01
`LOG_ONLY`-flagged turns, scored on the SAME disjoint-population confusion matrix.
- Hard fences (already settled — do not re-fight): no keyword broadening (142 TP/260 FP
  proof), no trimming top-3 phrases, no label-derived detector inputs, no judging by
  reading transcripts.
- Proof obligation before anything ships: **>91.5% detection at ≤3.9% FP on CSV-550, zero
  regression on IDG/PDX/EIT, reproduced by a committed script** — plus a stated latency/$
  budget per flagged turn.
- API cost note: judging ~200 flagged conversations is small — on Haiku 4.5 via the
  Batch API (50% off) this is well under $1 per full-corpus run; even Sonnet 5 judge runs
  are low single-digit dollars. The expensive part is the Claude Code session designing it,
  not the eval itself.
- Skills: `nhid-dbc01-semantic-ceiling-campaign` (the phases ARE the plan),
  `nhid-proof-and-analysis-toolkit` (recipes 1, 2), `nhid-validation-and-qa`,
  `nhid-research-methodology` (predict numbers before running).
- Gate: eval-only; going live is a **Bree decision** via the promotion protocol.
- Model: **Fable 5** for Phase 1 classification + judge design + results interpretation;
  Haiku 4.5 as the judge model inside the eval (it's a per-turn classifier — start cheap,
  escalate only if it can't meet the bar).

**P2.2 (stretch, only if P2.1 finishes early) — Frontier 3 quick win: publish signed
verification vectors** for NHID-Auth v2 so a third party can verify a passport offline.
Self-contained, no engine risk, strengthens the standards story.
- Skills: `nhid-research-frontier` (Frontier 3), `nhid-architecture-contract` (§9
  determinism invariant).
- Gate: additive; determinism gate must stay green. Model: Opus 4.8.

### Explicitly deferred (do NOT start before July 12)

- **Live in-call enforcement** (Frontier 2) — real research, not a 4-day ship.
- **Wiring `verify-passport` into the conformance path** — production-surface change
  requiring an owner decision and cross-surface (Lambda + FastAPI) edits.
- **Any lexicon expansion** — settled battle; the ceiling is proven.
- **Repo-root cleanup / de-duplicating the two runtime surfaces** — known weak point,
  but a refactor of this size days before a deadline violates the project's own
  change discipline.
- **All image generation** — brainstorm-gated (Section 5).

---

## 3. Skill → task map (which skill to invoke, when)

| Session task | Load FIRST | Load as needed |
|---|---|---|
| Any change at all | `nhid-change-control` | — |
| Env setup / running tests | `nhid-build-and-env` | `nhid-debugging-playbook` (symptoms 5, 6) |
| P0.1 merge verification | `nhid-diagnostics-and-tooling` | `nhid-validation-and-qa` |
| P1.1 / P1.3 CI + monitoring | `nhid-change-control` §4 | `nhid-run-and-operate`, `nhid-config-and-flags` |
| P1.2 drift sweep | `nhid-docs-and-positioning` | `nhid-failure-archaeology` (superseded numbers) |
| P2.1 DBC-01 campaign | `nhid-dbc01-semantic-ceiling-campaign` | `nhid-proof-and-analysis-toolkit`, `nhid-research-methodology`, `nhid-corpus-heuristic-mining` (only if a lexical candidate somehow appears) |
| Any anomaly / surprising number | `nhid-failure-archaeology` **before** investigating | `nhid-debugging-playbook` |
| Any public claim / README / archive edit | `nhid-docs-and-positioning` | `nhid-domain-reference` (canonical control names) |
| Understanding engine internals before touching them | `nhid-architecture-contract` | `nhid-domain-reference` |

Standing rules every session must obey (they exist because each was once violated):
scan `decision.violations`, never `reason_code`; DBC-01 stays `LOG_ONLY`; disclosure is
sticky; ATR-01 at 0% in replay is by design; test-count changes propagate atomically to
all five sites in one commit; supersede measurements, never delete; HISTORICAL archive
rows are frozen.

---

## 4. Gaps, blockers, and decisions Bree must make

| # | Decision | Blocks | Default if unanswered |
|---|---|---|---|
| D1 | **Merge the branch to `main`?** (makes webplatform + site polish live) | P0.1, and therefore everything the public sees by July 12 | Plan assumes YES after green verification |
| D2 | **DBC-01 Tier C: live / eval-only / flag-gated** — the open change-control §8 decision. Evidence: FP-on-compliant CSV 3.9%, adversarial 11.4%, baseline 1.8%, v2_iso 0% | Nothing ships either way, but it's the standing open item; the LLM-judge result (P2.1) may change the answer | Stays live (current state); no session may flip it silently |
| D3 | **Where does the $50 sit?** Claude Code subscription usage vs API credits are different pools. P2.1's judge eval spends *API* credits (trivial amounts); Claude Code sessions spend plan/credit budget | Budget math in Section 6 | Assumes one $50 pool; spend per Section 6 |
| D4 | **Webplatform deployment target** — it runs locally via `start.sh`; is it meant to be publicly hosted (Railway?) or demo-only? Public hosting adds an ops surface that conflicts with zero-touch | Scope of P1.3 monitoring | Demo-only (no new hosted surface before July 12) |
| D5 | **README interim state** — okay to ship text-first (no hero images) until the brainstorm rounds conclude? | P0.2 | YES — plan assumes stripping beats keeping disliked visuals |

Known gaps (not decisions, just be aware): the 18 integration tests only run with a live
server (start `uvicorn app:app --port 8000` first); `reportlab` isn't in requirements
(PDF regeneration needs it); `nhid_events.db` is committed and carries state — never trust
its contents; the external corpora (adversarial battery, v2_iso, baseline) referenced in
§2.5.1 are not in-repo, so only CSV-550 numbers can be re-verified by a fresh session.

---

## 5. Graphics — brainstorm queue (NOTHING generated until we ideate together)

Per the standing rule: **no image is generated or specified in this plan.** Every visual
touchpoint below is a brainstorm ticket. Existing disliked assets get *removed or fenced*
in P0.2; replacements happen only after a sketch-and-brainstorm round.

| # | Touchpoint | What it must communicate | Status |
|---|---|---|---|
| G1 | README hero / logo pair (`assets/logo-light.jpg` / `logo-dark.jpg`) | Instant read: "open behavioral baseline for AI voice agents in healthcare" — credible to a payer compliance officer, not startup-glossy | **[BRAINSTORM REQUIRED]** — current version disliked; branch already shows logo churn (3 delete/re-add cycles), which is itself evidence the direction was never settled |
| G2 | The three "3D render" WebPs + SVG fallbacks (nexus, trust-stack ziggurat, impersonation-vs-verified) | (a) the trust verification pathway, (b) the 5-layer stack, (c) the with/without-NHID contrast | **[BRAINSTORM REQUIRED]** — decide first whether the 3D-render aesthetic survives at all, or the whole family is replaced with one coherent diagram language |
| G3 | Conformance-badge SVGs (L1/L2/L3, `assets/badges/`) + the live badge endpoint's SVG | Tier at a glance; must NOT read as "certification" (positioning rule) | **[BRAINSTORM REQUIRED]** |
| G4 | Crypto call-binding sequence diagram (visuals memo #1 — most-requested by vendor engineers) | The full delegation → co-signature → verification → audit flow in one glance | **[BRAINSTORM REQUIRED]** — highest-value NEW visual; content spec already exists in `docs/visuals-and-graph-recommendations.md` |
| G5 | Trust & key-management diagram (memo #2) | Where trust originates; blast radius of a compromised node | **[BRAINSTORM REQUIRED]** |
| G6 | OAuth2 + NHID-Auth overlay (memo #3) | "You add NHID-Auth alongside OAuth2, not instead of it" | **[BRAINSTORM REQUIRED]** |
| G7 | FHIR AuditEvent 7-milestone timeline (memo #4) | Which AuditEvent fields map to which call milestone | **[BRAINSTORM REQUIRED]** |
| G8 | CAS distribution + shadow-pilot trend charts (memo #5–6) | Tier bands over a score histogram; 90-day trends | **[BRAINSTORM REQUIRED]** — and data-blocked: no pilot data exists; anything rendered must be labeled illustrative |
| G9 | Icon system (`icon-system.html`, `assets/icons/`) | One coherent icon language across site + webplatform | **[BRAINSTORM REQUIRED]** |
| G10 | Social/OG preview image + `brand-icon.png` | Link-unfurl credibility | **[BRAINSTORM REQUIRED]** |

Suggested brainstorm order when we ideate: **G1 → G2 (kill-or-keep) → G4** (the one new
diagram with real audience pull), then the rest post-deadline. Note memo #7 (vendor
maturity matrix) is deliberately a fillable table, not a graphic — no ticket needed.
`assets/images/3d-renders/PROMPTS.md` records how the current renders were made; treat it
as input to the brainstorm, not a template to re-run.

---

## 6. Model strategy for the $50 / 4-day window

Current per-MTok pricing (verified 2026-07-08): Fable 5 $10 in / $50 out · Opus 4.8
$5/$25 · Sonnet 5 $3/$15 (**intro $2/$10 through 2026-08-31**) · Haiku 4.5 $1/$5.
Batch API = 50% off everything.

| Phase | Model | Why |
|---|---|---|
| Planning / decision memos / DBC-01 campaign design & interpretation (P2.1) | **Fable 5**, effort `high` | The only work where top-tier judgment changes the outcome; cap at ~2 sessions |
| Engine-adjacent implementation, verification vectors (P2.2), anything change-control-gated | **Opus 4.8** | Strong enough for gated code work at half Fable's price |
| Site/webplatform edits, CI workflows, drift sweeps, docs, merge mechanics (P0.1–P1.3) | **Sonnet 5** | Intro pricing makes it the value-per-token king; these tasks are well-specified by the skills |
| Bulk/batch: LLM-judge classifier runs, link checks, drift greps | **Haiku 4.5 + Batch API** | Per-turn classification is a Haiku job; full-corpus judge run ≪ $1 |
| Image brainstorm sessions (post-plan, conversational) | Sonnet 5 for divergent idea rounds; one Fable 5 pass to converge on final art direction | Brainstorming is cheap talk; convergence is the judgment step |

Budget shape (rough, deliberately conservative): reserve **~$15–20 Fable-tier** for the
two P2.1 sessions and the Tier C memo, **~$20 Sonnet-tier** for the P0/P1 execution grind
(this is most of the session-hours but the cheapest tokens), **~$5 Opus-tier** for gated
code moments, **~$2 Haiku/Batch** for eval runs — leaving a ~$5–8 buffer for reruns.
Two cost disciplines: (1) start every session by loading only the skills in Section 3's
map — they exist precisely so a session doesn't re-derive context expensively; (2) never
re-investigate anything listed in `nhid-failure-archaeology` — that file is prepaid tokens.

Since the plan resets **Thursday July 9**: spend Wednesday on zero-cost prep (this plan,
brainstorm notes, Bree's D1–D5 answers), then run P0 Thursday, P1 Friday, P2 Saturday,
with Sunday July 12 held for merge fallout and the ship announcement only.

---

## 7. Definition of done — "zero-touch"

By end of July 12 the system is zero-touch when ALL of these hold:

- [ ] Branch merged; nhid-clinical.org serves the polished site from `main`
- [ ] CI green at 330/18 on `main`; nightly self-verification workflow live (invariant
      check + confusion-matrix baseline assertion + link check + API smoke) and failure
      auto-opens an issue
- [ ] Published numbers reconciled everywhere and covered by the nightly drift grep
- [ ] Live demo endpoints monitored; no credential or manual step required to keep the
      site, API, and badges serving
- [ ] DBC-01 judge result recorded (adopted-pending-decision, or documented retirement in
      the archive — either outcome is a valid "done" per `nhid-research-methodology`)
- [ ] The ONLY standing human tasks are governance-by-design ones: the DBC-01 review
      queue (deliberately human-in-the-loop — this is a feature, not a gap) and archive
      updates when decisions land

---

*Doc-only artifact. No engine, test, or lexicon changes accompany this file; the 330/18
invariant is unaffected. Supersede this plan in place if the July 12 scope changes —
don't delete it.*
