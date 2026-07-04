---
name: nhid-debugging-playbook
description: >
  Symptom-to-triage runbook for NHID-Clinical's known failure modes. Load this when a
  policy-engine control (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01) reports 0 detections or
  suspiciously perfect detections in the synthetic eval loop; when IDG-01 fires on every
  caller turn; when ATR-01 shows 0% in transcript replay; when CI fails on the 330-test
  count invariant; when 18 tests skip unexpectedly; when human-review routing looks wrong;
  or when two CAS scores disagree for the same event. Each symptom has a first check, a
  discriminating experiment, and the real incident it comes from. NOT for adding new
  detection phrases (use nhid-corpus-heuristic-mining) or for executing count bumps
  (see nhid-change-control).
---

# NHID-Clinical Debugging Playbook

This repo is a healthcare voice-AI governance framework: a deterministic policy engine
(`src/nhid_policy_engine_v1.py`) evaluates conversation events against five controls, a
synthetic eval loop replays transcript corpora through it, and an AWS Lambda handler
(`functions/handler.py`) serves it in production. Every symptom below has actually
happened here. Check the wiring before you suspect the engine — the engine is pure,
deterministic, and heavily tested; the adapters and harnesses around it are where the
bugs have lived.

Run everything from the repo root (`/home/user/NHID-Clinical`), Python 3.11.

## Jargon, defined once

| Term | Meaning |
|---|---|
| Control | One of five governance rules the engine checks per event: IDG-01 (Identity Disclosure Gate), PDX-01 (Pre-Data Exchange Gate), DBC-01 (Deceptive Behavior Check), EIT-01 (Escalation Implementation Test), ATR-01 (Audit Trail). |
| `evaluate_all` | `src/nhid_policy_engine_v1.py:728` — runs all six evaluators (five controls + bot-to-bot), merges ALL violations, picks ONE dominant action/reason_code by priority. |
| Eval loop | `src/synthetic_eval_loop.py` — `build_session()` (:80) and `build_event()` (:92) convert a "turn" dict into the session/event shapes `evaluate_all` expects, then replay whole conversations. |
| Fabricate adapter | `adapters/fabricate_adapter.py` — converts the Tonic Fabricate corpus (`fixtures/fabricate/conversations.csv`, 550 conversations, 127 compliant + `turns.csv`) into eval-loop turns. |
| CAS | Call Authorization Score, 0.0–1.0. Two implementations exist (see symptom 8). Tiers from `_tier_for_cas` in `src/nhid_cas.py:45`: ≥0.90 Verified Trust, ≥0.75 Conditional Trust, ≥0.50 Review Required, ≥0.20 Denied/Degraded, else Hard Denial. |
| Label leakage | Ground-truth labels wired into detector input — the detector "detects" its own answer key. This repo shipped one (see symptom 3). |
| PHI | Protected Health Information (US HIPAA term) — patient data the PDX-01 gate blocks before identity disclosure. |

## Core triage table

| # | Symptom | First check | Discriminating experiment | Story |
|---|---|---|---|---|
| 1 | A control silently reports 0 detections in eval | Session/event wiring in `build_session`/`build_event` — NOT the engine | Feed one hand-built violating event straight to `evaluate_all()` | The 284→294 silent-zero bug (commit `3f91845`) |
| 2 | IDG-01 fires on every caller turn | Is `identity_assertion_text` blanked on caller turns? Disclosure must be sticky | Grep decisions for `IDG01_ASSERTION_TEXT_MISSING` only on `speaker != "agent"` turns | v1.1 eval repair (commit `ed097f4`) |
| 3 | Detection rate looks too good (~95%+) | Adapter code for ground-truth columns feeding detector inputs | Shuffle/invert the label column; if the rate follows the label, it is leakage | EIT-01 ~95% was meaningless: `escalation_path_available` derived from the `eit01_violation` label |
| 4 | ATR-01 shows 0% in replay | Nothing — this is by design, not a bug | Run `tests/failure_injection_harness.py` + CTS case `ATR-01-FAIL-MISSING` instead | Settled: replay synthesizes complete audit envelopes, so ATR-01 is untestable from transcripts |
| 5 | CI fails on test-count drift | Did you add/remove tests without the atomic propagation checklist? | `python3 scripts/validate_ci.py` locally | Count drift kept recurring → archive §9.1 invariant; full protocol in nhid-change-control |
| 6 | 18 tests skip | Is a server running at 127.0.0.1:8000? | Start `uvicorn app:app --reload --port 8000`, re-run harness | 18 skips = `failure_injection_harness.py` integration tests; expected when no server |
| 7 | Routing decision seems wrong | Are you reading `decision.reason_code`? Scan `decision.violations` instead | Build an event violating two controls; reason_code shows only the dominant one | `evaluate_all` overwrites reason_code with the dominant-priority rule |
| 8 | Two CAS scores differ for the same call | Which implementation produced each? They measure different things | Compare keys: handler returns `"score"`, `compute_cas` returns `"cas"` | `functions/handler.py:_policy_cas` is a bucketed disclosure CAS; `src/nhid_cas.compute_cas` is telemetry NOCF |

Details for each row follow. All line numbers and counts verified against the repo as of
2026-07-04.

## 1. A control silently reports 0 detections in eval

**Story.** When the synthetic eval loop first shipped (v1.3, 284 tests), DBC-01 and
EIT-01 both reported 0.0% detection. The engine was fine. `build_session`/`build_event`
simply didn't thread two fields from the turn dict into the shapes `evaluate_all` reads:

- `escalation_path_available` lives on the **session**, defaults `True` — a turn that
  sets it `False` must have it carried through, or EIT-01 never sees the failure.
- `deceptive_artifact_flags` must be nested **inside** `event["healthcare_governance"]`,
  not top-level — DBC-01 Tier A reads only the nested spot.

Fix landed as commit `3f91845` ("Fix DBC-01/EIT-01 silently returning 0 detections in
synthetic eval loop"), bumping the suite 284→294 with sentinel tests
`test_dbc01_detected_not_zero` / `test_eit01_detected_not_zero` in
`tests/test_synthetic_eval_loop.py`.

**First check — wiring, never the engine.** Confirm both classic spots:

```bash
grep -n "escalation_path_available\|deceptive_artifact_flags" src/synthetic_eval_loop.py
```

Expect `escalation_path_available` in `build_session()` and `deceptive_artifact_flags`
inside the `healthcare_governance` block of `build_event()`.

**Discriminating experiment.** Bypass the loop entirely — hand-build one violating
session/event and call the engine directly:

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, "src")
from nhid_policy_engine_v1 import evaluate_all
session = {"turn_count": 1, "escalation_path_available": False, "counterparty_type": "human_operator"}
event = {
    "event_id": "e1", "timestamp": "t", "session_id": "s1", "request_id": "r1",
    "event_type": "POLICY", "actor_id": "a1", "counterparty_type": "human_operator",
    "state_before": "ACTIVE", "state_after": "ACTIVE",
    "healthcare_governance": {
        "disclosure_timestamp": "t0", "identity_assertion_text": "I am an AI assistant",
        "deceptive_artifact_flags": ["synthetic_background_noise"],
        "escalation_timestamp": None, "escalation_outcome": None, "phi_accessed": [],
    },
    "input_payload": {"speech_text": "I need to speak to a human person"},
    "execution_context": {"pipeline_version": "1.0.0", "policy_engine_version": "1.0.0", "nhid_schema_version": "1.0"},
}
d = evaluate_all(session, event)
print([ (v.rule_id, v.severity.value) for v in d.violations ])
EOF
```

If the direct call detects (expect DBC-01 critical and EIT-01 critical here) but your
harness reports zero, the bug is in your harness's session/event construction. If the
direct call also misses, only then read the evaluator. Also run the sentinels:

```bash
python3 -m pytest tests/test_synthetic_eval_loop.py -q -k "not_zero"
```

## 2. IDG-01 fires on every caller turn

**Story.** Pre-v1.1, the Fabricate adapter blanked `identity_assertion_text` on caller
turns. IDG-01's pass condition (engine `:132`) requires a non-empty assertion alongside
`disclosure_timestamp`; blank assertion → MAJOR `IDG01_ASSERTION_TEXT_MISSING`. Result:
every post-disclosure caller turn "violated" IDG-01, inflating rates. A disclosure made
once does not expire when the caller speaks.

**Fix contract (sticky disclosure).** `adapters/fabricate_adapter.py:build_turn` (:167):
agent turns carry the agent's own words as `identity_assertion_text`; caller turns carry
the STICKY disclosure assertion (the agent's original disclosure line);
`disclosure_timestamp` is sticky from the first turn where `is_identity_disclosure` is
truthy.

**First check.**

```bash
sed -n '167,200p' adapters/fabricate_adapter.py
```

Confirm the caller branch uses `disclosure_assertion_text`, not `""`.

**Discriminating experiment.** If you're writing a new adapter, count
`IDG01_ASSERTION_TEXT_MISSING` per speaker. Any occurrence on a caller turn AFTER a
disclosure turn in the same conversation is the sticky-disclosure bug, not a real
violation. Baseline sanity: IDG-01 on the shipped corpus is exactly 70/70 with 0 FP
(see the reproducible run under symptom 3) — if your run shows IDG-01 FPs on compliant
conversations, suspect your wiring first.

## 3. A detection rate looks too good — suspect label leakage

**Story.** Pre-v1.1, the adapter derived `session["escalation_path_available"]` from the
corpus's ground-truth `eit01_violation` column. The label under test drove the detector
input, so EIT-01's ~95% "detection rate" was circular and meaningless. (Two other causes
compounded it: the IDG-01 blanking above, and a genuine gap — no mid-call implied-humanity
scan, fixed by DBC-01 Tier C.) The v1.1 repair (commit `ed097f4`) derives escalation
honor from the transcript itself: `_annotate_escalation_outcomes` (:121) uses
caller-anchored ask-again windows and `ESCALATION_HONOR_PATTERNS` (:77, performative
handoffs only). The corrected, meaningful rates: DBC-01 87–98%, EIT-01 ~98% depending on
corpus.

**First check.** In whatever adapter produced the number, grep for ground-truth columns
(`*_violation`) feeding any field the engine reads:

```bash
grep -n "eit01_violation\|dbc01_violation\|idg01_violation\|pdx01_violation" adapters/*.py
```

Legitimate uses populate `expected_violations` (the answer key) ONLY. Any use that sets
a session/event field is leakage.

**Discriminating experiment.** Invert or shuffle the label column in a copy of
`conversations.csv` and re-run. A real detector's rate is unchanged (it never saw the
label); a leaky one's rate tracks the label. The honest measurement command:

```bash
python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv
```

Expected on the shipped 550-conversation corpus (verified 2026-07-04): IDG-01 70/70
100%/0 FP; PDX-01 41/41 100%/0 FP; DBC-01 183/200 91.5%/3.9% FP; EIT-01 168/171
98.2%/2.4% FP. Detection and FP are measured on disjoint populations (FP only over the
127 `scenario_type == "compliant"` conversations). 100% with 0 FP on a text heuristic is
plausible for narrow gates (IDG/PDX) but demands leakage checks for phrase-matching
controls (DBC/EIT). Do NOT respond to a low rate by adding phrases — that decision
procedure belongs to the `nhid-corpus-heuristic-mining` skill (zero-FP bar,
`scripts/mine_heuristic_candidate.py`).

## 4. ATR-01 shows 0% in replay — untestable by design

**Story.** ATR-01 requires 11 audit fields plus `execution_context` on every event
(engine `:610`). But `build_event()` synthesizes a complete audit envelope for every
replayed turn — that is its job — so no conversational corpus can ever exercise ATR-01.
Degrading envelopes based on the label would be tautological detection. Settled: the
adapter drops ATR-01 from `expected_violations` and reports the exclusion count to
stderr (`adapters/fabricate_adapter.py:213` area, "ATR-01 (untestable in replay)").

**First check.** Is the 0% coming from a transcript-replay path? Then it is expected.
Do not "fix" it.

**Discriminating experiment — test ATR-01 where it is testable:**

```bash
# Terminal 1: start the server (exact command from the harness docstring)
uvicorn app:app --reload --port 8000

# Terminal 2: run the failure-injection harness (18 integration tests)
python3 -m pytest tests/failure_injection_harness.py -v
```

Plus the machine-readable conformance case `ATR-01-FAIL-MISSING` in
`conformance/nhid_conformance_test_suite_v1.yaml` (:404). If those pass, ATR-01
enforcement is healthy regardless of what replay says.

## 5. CI fails on test-count drift

**Story.** The suite invariant is 330 passed / 18 skipped (348 collected).
`scripts/validate_ci.py` hardcodes `UNIT_EXPECTED = 330` and `INTEGRATION_EXPECTED = 18`
and fails on ANY drift — including tests you added that pass. The count is also
hardcoded in the `.github/workflows/ci.yml` job name ("Unit invariant: 330 passed"),
`.github/CONTRIBUTING.md`, README badges/text, and live rows of
`docs/MASTER-KNOWLEDGE-ARCHIVE.md` (historical rows there must NOT be touched). Drift
kept recurring, which is why archive §9.1 makes atomic count propagation a
non-negotiable invariant.

**First check.**

```bash
python3 scripts/validate_ci.py
```

Read which count moved. If you intentionally added/removed tests, you must bump every
hardcoded location in ONE commit — the full atomic propagation checklist and change
protocol live in the **nhid-change-control** skill; do not improvise it here.

**Discriminating experiment.** Distinguish "my new test broke the count" (validate_ci
says `expected 330 passed, got 331`) from "an existing test regressed" (`N failed`).
The first is a bookkeeping task for nhid-change-control; the second is a real bug —
bisect it, don't touch the counts.

## 6. 18 tests skip

**Story / design.** `pytest.ini` collects `*_harness.py` as tests.
`tests/failure_injection_harness.py` holds 18 integration tests marked
`skipif` server-not-reachable (harness `:137`). No server at `NHID_BASE_URL`
(default `http://127.0.0.1:8000`) → exactly 18 skips. `validate_ci.py` accepts skip
counts of 0 or 18 only; any other number is a failure.

**First check.** Is anything listening?

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/ || echo "no server"
```

**Discriminating experiment.** Start the server with the exact command from the harness
docstring, then re-run:

```bash
uvicorn app:app --reload --port 8000        # note: app:app, NOT main:app
python3 -m pytest tests/failure_injection_harness.py -v
```

Env overrides: `NHID_BASE_URL`, `NHID_EVENT_DB` (default `nhid_events.db`),
`NHID_TIMEOUT` (default 10s). If skips are some number other than 0 or 18, a harness
test was added/removed — that is a count-drift problem; go to symptom 5.

## 7. A routing decision seems wrong — scan violations, not reason_code

**Story / design.** `evaluate_all` (engine `:728`) runs all six evaluators and merges
ALL violations into one `PolicyDecision`, but sets `action`/`reason_code` from the single
dominant decision by priority: `DENY_DATA=5 > ESCALATE_HUMAN=4 > DISCLOSE_IDENTITY=3 >
LOG_ONLY=2 > CONTINUE_AI=1`. A DBC-01 hit (always `LOG_ONLY` — non-blocking by design;
the human-review queue closes that gap) is invisible in `reason_code` whenever any
higher-priority control also fired. Consumers that key off `reason_code` silently drop
violations.

The correct pattern is what `src/dbc01_review_routing.should_route_to_review` (:40)
does: filter `decision.violations` by `rule_id`, never inspect `reason_code`. Routing
rules there: DBC-01 CRITICAL → `DBC01_ARTIFACT_DETECTED`; DBC-01 MAJOR →
`DBC01_IMPERSONATION_PHRASE_DETECTED`; else `cas["score"] < 0.75` →
`CAS_REVIEW_REQUIRED`.

**First check.** Grep the suspect consumer for `reason_code`:

```bash
grep -rn "reason_code" --include="*.py" functions/ src/ | grep -v nhid_policy_engine_v1
```

Any branch on `decision.reason_code` to decide per-control handling is the bug.

**Discriminating experiment.** Build one event that violates two controls at once
(e.g. the snippet in symptom 1 — DBC-01 artifact + EIT-01 no-path). Print both:

- `decision.reason_code` → one code (the ESCALATE_HUMAN-dominant EIT code).
- `[v.rule_id for v in decision.violations]` → both `DBC-01` and `EIT-01`.

If your consumer only reacts to the first, it has the reason_code bug. Note the queue
is idempotent: `dbc01_review_queue` has `UNIQUE(session_id, event_id, request_id)` with
`ON CONFLICT DO NOTHING`, and dispositions are one-way pending→resolved via
`scripts/resolve_dbc01_review.py` (`confirmed_impersonation` | `false_positive`).

## 8. The two CAS implementations give different scores

**Story / design.** This is expected — they answer different questions and only share
the tier ladder (`_tier_for_cas`, imported by the handler from `src/nhid_cas.py`):

| | `src/nhid_cas.compute_cas` (:51) | `functions/handler.py:_policy_cas` (:617) |
|---|---|---|
| Question | Full telemetry trust score | Disclosure-level score from one policy decision |
| Formula | `CAS = F_IAF × F_NOCF × ECF`, F_NOCF from NOCF telemetry (competence/reliability/risk; risk weights 0.40/0.35/0.25 must sum to 1) | Same multiplication, but F_NOCF **bucketed by critical-violation count**: 0→0.90, 1→0.50, ≥2→0.25 |
| F_IAF | Caller-supplied verification bool | 0.0 iff IDG-01 or PDX-01 has a CRITICAL violation, else 1.0 |
| ECF | Audit-field completeness over `REQUIRED_FIELDS_V1` (12 fields) | Fraction of 4 core event fields present |
| Result key | `"cas"` | `"score"` |
| Consumer | Telemetry/scoring analyses | `should_route_to_review` (reads `cas["score"]`) and API responses |

Any-zero-zeroes-it holds for both (multiplicative).

**First check.** Identify which produced each number by its dict key: `"cas"` =
`compute_cas`, `"score"` = `_policy_cas`. If you're comparing a `"cas"` to a `"score"`,
you're comparing different instruments — stop.

**Discriminating experiment.** Same event, both paths: a decision with exactly one
non-identity CRITICAL violation and a complete event gives `_policy_cas` = 1.0 × 0.50 ×
1.0 = 0.50 ("Review Required") regardless of call quality, while `compute_cas` on clean
telemetry can still be ≥0.90. Divergence in that direction is by design. If both claim
to be the SAME implementation and still differ, check `ECF` inputs first (missing audit
fields), then `F_IAF`.

## When NOT to use this skill

| Your task | Use instead |
|---|---|
| Low real-corpus rate on a text heuristic; deciding whether to expand a phrase list, change approach, or add human review | **nhid-corpus-heuristic-mining** (existing) |
| Executing a test-count bump, lexicon edit, or any change touching §9.1 invariants | **nhid-change-control** |
| Wanting the full history of past incidents and why decisions settled the way they did | **nhid-failure-archaeology** |
| Understanding module boundaries, layering, and API contracts | **nhid-architecture-contract** |
| Learning what the controls, CAS, or HIPAA/PHI terms mean from scratch | **nhid-domain-reference** |
| Environment variables, feature flags, demo caps, constants | **nhid-config-and-flags** |
| Installing deps, Python/Java setup, CI pipeline mechanics | **nhid-build-and-env** |
| Starting/deploying the server, Lambda, adapters in normal operation | **nhid-run-and-operate** |
| General diagnostic tooling beyond these eight failure modes | **nhid-diagnostics-and-tooling** |
| Test-writing standards and QA gates | **nhid-validation-and-qa** |
| Docs, website, external claims | **nhid-docs-and-positioning** |
| The DBC-01 semantic-ceiling problem itself (Tier C live-vs-eval decision, non-lexical misses) | **nhid-dbc01-semantic-ceiling-campaign** |
| Proving/measuring things rigorously (confusion matrices as methodology, stats) | **nhid-proof-and-analysis-toolkit** |
| Open research questions | **nhid-research-frontier** / **nhid-research-methodology** |

This skill is only for: "something is misbehaving right now and matches (or rhymes with)
one of the eight symptoms above."

## Provenance and maintenance

All facts verified against the repo on 2026-07-04. Re-verify before trusting:

- Engine line anchors and reason codes: `grep -n "def evaluate_\|EIT01_\|DBC01_\|IDG01_" src/nhid_policy_engine_v1.py`
- Wiring spots: `grep -n "escalation_path_available\|deceptive_artifact_flags" src/synthetic_eval_loop.py` (build_session :80, build_event :92)
- Count invariant: `grep -n "EXPECTED" scripts/validate_ci.py` (330/18) and `python3 -m pytest tests/ -q --co | tail -1` (348 collected)
- Harness server command and skip behavior: `sed -n '1,30p' tests/failure_injection_harness.py`
- Sticky disclosure + de-leak contract: `sed -n '1,60p' adapters/fabricate_adapter.py`
- Routing threshold and trigger names: `sed -n '40,55p' src/dbc01_review_routing.py`
- CAS constants/tiers and the bucketed handler variant: `sed -n '9,12p;45,57p' src/nhid_cas.py` and `sed -n '617,655p' functions/handler.py`
- Corpus rates (deterministic, ~1 min): `python3 scripts/confusion_matrix.py fixtures/fabricate/conversations.csv fixtures/fabricate/turns.csv`
- Story commits: `git log --oneline --all | grep -E "3f91845|ed097f4|35713a8"`
