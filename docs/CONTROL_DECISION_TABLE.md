# NHID-Clinical Control Decision Table (Tier 0)

**Quick Reference**: Decision logic for each of the 5 policy controls.  
**Note**: PolicyAction values (CONTINUE_AI, DENY_DATA, DISCLOSE_IDENTITY, LOG_ONLY, ESCALATE_HUMAN) are defined in [`docs/enforcement-profile.md`](enforcement-profile.md) — the normative specification.

---

## IDG-01: Identity Disclosure Gate

| Aspect | Details |
|--------|---------|
| **Control** | IDG-01 |
| **Purpose** | Ensure agent discloses non-human identity before sensitive interaction |
| **Trigger** | Any turn where `event_type == IDENTITY_DISCLOSURE` OR `contains_phi == True` |
| **What it Checks** | Is there a valid identity disclosure before the first PHI access, and does the disclosure actually disclose? |
| **Pass Condition** | `disclosure_timestamp` set, `identity_assertion_text` non-empty, and (on the disclosing turn) the assertion neither introduces a human persona without stating a non-human identity nor denies being automated |
| **Fail Condition** | `IDG01_DISCLOSURE_MISSING` (no timestamp) · `IDG01_ASSERTION_TEXT_MISSING` (empty assertion) · `IDG01_DISCLOSURE_CONTRADICTED` (persona claim, implied humanity, impersonation phrase, or denial of automated identity, with no non-human identity stated) |
| **Decision/Evidence** | Stored in `healthcare_governance.disclosure_timestamp` (turn index of valid disclosure) |
| **Limitation** | Judges disclosure *content* only for contradiction, not for adequacy. A bare organisational name ("claims system") is not flagged — the evaluation corpus labels that a violation and the structurally identical "authorization system" compliant, so no rule separates them. Does not verify the counterparty understood. Content checks apply only to the disclosing turn, which requires a harness that sets `disclosure_established_prior`; absent it the check does not run. |
| **Test Coverage** | `tests/test_engine_disclosure_hardening.py`, `tests/test_adversarial_hardening.py`; also asserted across the vendor-adapter and API suites |
| **Corpus Status** | Fabricate 70/70 (0 FP/127). Governance Evaluation Corpus 6/8 (75.0%) |

---

## PDX-01: Pre-Data Exchange Gate

| Aspect | Details |
|--------|---------|
| **Control** | PDX-01 |
| **Purpose** | Prevent PHI from being exchanged before valid identity disclosure |
| **Trigger** | Any turn where `contains_phi == True` |
| **What it Checks** | If protected data is requested or supplied in this turn, did disclosure occur on an *earlier* turn? |
| **Pass Condition** | No protected-data exchange, OR disclosure was established on a prior turn |
| **Fail Condition** | `PDX01_PHI_GATE_TRIGGERED` (exchange with no disclosure at all) · `PDX01_DISCLOSURE_NOT_SEQUENCED` (exchange in the same turn as the initial disclosure) · `PDX01_SCOPE_NOT_AUTHORIZED` (request outside a verified DLG-01 delegation scope) |
| **Decision/Evidence** | Comparison of `healthcare_governance.disclosure_timestamp` vs. current turn; matched against corpus `contains_phi` field |
| **Limitation** | Detection is lexical plus one structural rule (a subject word followed by a digit-bearing token), so a paraphrase outside the phrase map is missed. Sequencing needs a harness that sets `disclosure_established_prior`; absent it, same-turn exchange is not flagged. |
| **Test Coverage** | `tests/test_engine_disclosure_hardening.py`, `tests/test_adversarial_hardening.py`; also asserted across the vendor-adapter and API suites |
| **Corpus Status** | Fabricate 41/41 (0 FP/127). Governance Evaluation Corpus 6/6 (100.0%) |

---

## DBC-01: Deceptive Behavior Check

| Aspect | Details |
|--------|---------|
| **Control** | DBC-01 |
| **Purpose** | Prevent agent from concealing AI identity or impersonating a human |
| **Trigger** | Any turn where `deception_pattern != "NONE"` OR explicit concealment request |
| **What it Checks** | Does the agent utterance contain deceptive language (conceal, impersonate, misrepresent)? |
| **Pass Condition** | `deceptive_artifact_flags == []` (no deception detected) |
| **Fail Condition** | Tier A — any `deceptive_artifact_flags` entry (EXPLICIT_CONCEAL_REQUEST, EXPLICIT_IMPERSONATION, EXPLICIT_MISREPRESENTATION, IMPLICIT_EVASIVE, AMBIGUOUS_IDENTITY_LANGUAGE, HUMAN_PASSING_ATTEMPT). Tier B — an impersonation phrase in the identity assertion, including first-person licensed-clinical role claims ("I'm a nurse reviewer"). Tier C — corpus-mined implied-humanity cues ("our team", "I'll personally"); weak disfluency cues require two or more |
| **Decision/Evidence** | Stored in `healthcare_governance.deceptive_artifact_flags` (list of artifact types); mapped from corpus `deception_pattern` enum |
| **Limitation** | Depends on corpus pattern classification; implicit/ambiguous patterns may not be 100% accurate in real data. Tier C is inferential and stays active even when the same assertion discloses — suppressing it after a disclosure was tried and cost four real Fabricate detections, because disclosing once and then passing as staff is a pattern that corpus labels deceptive. Third-person clinical references ("a nurse reviewer will look at this") are deliberately not matched. |
| **Test Coverage** | `tests/test_dbc01_heuristics.py` (11 tests), plus review-routing and review-queue suites |
| **Corpus Status** | Fabricate 183/200 (91.5%, 5 FP/127) — the least precise of the controls. Governance Evaluation Corpus 9/9 (100.0%) |

---

## EIT-01: Escalation Implementation Test

| Aspect | Details |
|--------|---------|
| **Control** | EIT-01 |
| **Purpose** | Verify escalation requests are honored within reasonable time window |
| **Trigger** | Any turn where `escalation_requested == True` |
| **What it Checks** | If escalation is requested at turn N, is it honored (transferred, resolved) within 5 turns (by turn N+5)? |
| **Pass Condition** | No escalation requested, OR an escalation path is available, OR fulfilment is recorded — an `escalation_timestamp` together with an honoring `escalation_outcome` (`honored`, `completed`, `transferred`, `connected`, `fulfilled`) |
| **Fail Condition** | `escalation_outcome == "DEFLECTED"` OR `escalation_outcome == "IGNORED"` OR escalation requested but no outcome within 5 turns |
| **Decision/Evidence** | Tracked in session state: `escalation_request_turn` (turn N) + `escalation_outcome` (turn N+X); evidence in corpus metadata |
| **Limitation** | Does not validate quality of escalation (e.g., was it a real human?); limited to 5-turn window. Escalation requests are detected by keyword, so the agent's own confirmation line ("connecting you to a supervisor") matches as a request — recorded fulfilment is what prevents that reading as a failure. An honoring outcome with no timestamp is a claim, not a record, and does not clear the control. |
| **Test Coverage** | `tests/test_eit01_multiturn.py` (8 multi-turn escalation-tracking tests) |
| **Corpus Status** | Fabricate 169/171 (5 FP/127). Governance Evaluation Corpus 8/8 (100.0%), 0 false positives |

---

## ATR-01: Audit Trail Requirements

| Aspect | Details |
|--------|---------|
| **Control** | ATR-01 |
| **Purpose** | Ensure all policy-relevant events are persisted for compliance audit |
| **Trigger** | Every turn processed |
| **What it Checks** | Are audit events being logged for identity disclosure, PHI access, deception detection, escalation, policy violations? |
| **Pass Condition** | `audit_trail` populated with ≥5 events per turn; events include: event_type, turn_index, timestamp, control, status |
| **Fail Condition** | `audit_trail` missing events OR events not persisted to AuditStore (handled by external AuditPersistenceManager) |
| **Decision/Evidence** | Stored in `PolicyDecision.audit_trail` (an `AuditTrail` object holding `events: list[AuditEvent]`); persisted via hash-chained append-only log |
| **Limitation** | Persistence is outside engine (external responsibility); engine cannot enforce persistence failure detection |
| **Test Coverage** | `tests/test_atr01_audit_trail.py` (12 tests) + `tests/test_atr01_persistence.py` (5 tests) |
| **Corpus Status** | 100% operational (5 events/turn logged for all 150 sessions; persistence tested separately) |

---

## Decision Logic Summary

### When All Controls PASS

```
Action: CONTINUE_AI
Meaning: Conversation can proceed. Agent disclosed identity, no premature PHI, no deception, escalations handled.
Audit: 25+ events recorded per session.
```

### When Some Controls FAIL

```
Critical violations (IDG-01 or PDX-01):
  Action: DENY_DATA (or DISCLOSE_IDENTITY if IDG-01 failure)
  Meaning: Terminate PHI exchange / transfer to human / re-prompt disclosure.
  
Other violations (DBC-01, EIT-01):
  Action: LOG_ONLY
  Meaning: Flag for human review; offer guidance; conversation may proceed depending on risk tolerance.
  
Audit violations (ATR-01):
  Action: LOG_ONLY
  Meaning: Conversation proceeds, but missing audit events are flagged and escalated to audit team.
```

### Decision Matrix

| IDG-01 | PDX-01 | DBC-01 | EIT-01 | ATR-01 | Final Action |
|--------|--------|--------|--------|--------|---------------------|
| PASS   | PASS   | PASS   | PASS   | ✓      | **CONTINUE_AI**     |
| PASS   | PASS   | PASS   | FAIL   | ✓      | **ESCALATE_HUMAN**  |
| PASS   | PASS   | FAIL   | PASS   | ✓      | **LOG_ONLY**        |
| PASS   | FAIL   | —      | —      | ✓      | **DENY_DATA**       |
| FAIL   | —      | —      | —      | ✓      | **DISCLOSE_IDENTITY** |
| PASS   | PASS   | PASS   | PASS   | ✗      | **LOG_ONLY** (audit gap) |

---

## Shadow Mode Behavior

In Tier 0 shadow pilot, **all actions are observed but not enforced**:

| Engine Decision | Shadow Mode Behavior |
|-----------------|----------------------|
| CONTINUE_AI | Conversation proceeds normally; audit logged |
| LOG_ONLY | Conversation proceeds; violation flagged for human review; alert sent |
| DENY_DATA | Conversation proceeds; critical violation logged; human reviewer notified; call may be monitored |
| DISCLOSE_IDENTITY | Conversation proceeds; identity disclosure requirement logged; human reviewer notified |
| ESCALATE_HUMAN | Conversation proceeds; escalation request flagged; human reviewer notified |

**Enforcement Mode** (future) will actually terminate/transfer based on decision.

---

## Test Coverage Summary

| Control | Dedicated test file(s) | Corpus expectation | Corpus result |
|---------|------------------------|--------------------|---------------|
| IDG-01 | *(covered across adapter + endpoint suites)* | 64 violations | 64 detected — 0% FP rate, 100% accuracy |
| PDX-01 | *(covered across adapter + endpoint suites)* | 64 violations | 64 detected — 0% FP rate, 100% accuracy |
| DBC-01 | `test_dbc01_heuristics.py` (11) | 23 violations | 23 detected — 0% FP rate, 100% accuracy |
| EIT-01 | `test_eit01_multiturn.py` (8) | 2 violations | 2 detected — 100% detection, 100% accuracy |
| ATR-01 | `test_atr01_audit_trail.py` (12), `test_atr01_persistence.py` (5) | 150 sessions | Audit trail operational across all sessions |

Suite totals: **1049 passing, 0 skipped, 0 xfailed** across 55 test files. The per-control
figures in *this* table are read from `corpus_evaluation_output/corpus_metrics.json`
(Tonic, 150 sessions, 1,227 turns).

**Three corpora are measured in this project and their figures are not interchangeable:**

| Corpus | Size | Produced by | Reported in |
| :--- | :--- | :--- | :--- |
| Fabricate | 550 conversations (127 compliant) | `scripts/check_baseline.py` — CI-gated | `evidence-pack.html` |
| Tonic | 150 sessions, 1,227 turns | `scripts/evaluate_tonic_corpus.py` | `docs/CORPUS_EVALUATION_SUMMARY.md` |
| Governance Evaluation | 25 scenarios, 55 turns | `scripts/eval_corpus.py` | `docs/EVALUATION_CORPUS_REPORT_v1.md` |

A fourth, `tests/adversarial_corpus_v1.json` (40 scenarios), measures resistance to
evasion rather than detection rate; see `scripts/redteam_corpus.py`. IDG-01 and PDX-01 now
have dedicated regression files (`test_engine_disclosure_hardening.py`,
`test_adversarial_hardening.py`) alongside the vendor-adapter and API suites.

---

## Open Work

1. **Corpus Baseline**: Use perfected metrics as regression testing baseline
   - Add nightly corpus evaluation to CI pipeline
   - Alert on accuracy drift (e.g., if PDX-01 drops below 95%)

2. **ML-based Deception Detection**: Improve DBC-01 from pattern matching to NLP
   - Current: Keyword patterns + enum mapping
   - Future: Train on real deceptive behavior corpus

3. **Millisecond-precision PHI Timing**: Upgrade PDX-01 to subsecond gates
   - Current: Turn-level granularity
   - Future: Word-level or phrase-level PHI detection

---

**Status**: Tier 0 Ready (1049 passing, 0 skipped, 0 xfailed; audit trail operational)
