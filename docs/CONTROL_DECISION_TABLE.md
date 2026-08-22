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
| **What it Checks** | Is there a valid identity disclosure (status=DISCLOSED) before the first PHI access? |
| **Pass Condition** | `disclosure_timestamp < first_phi_turn` (disclosure occurred before PHI) |
| **Fail Condition** | `disclosure_timestamp == None` OR `disclosure_status != "DISCLOSED"` OR `disclosure_timestamp >= first_phi_turn` |
| **Decision/Evidence** | Stored in `healthcare_governance.disclosure_timestamp` (turn index of valid disclosure) |
| **Limitation** | Relies on corpus `disclosure_status` field; does not validate quality of disclosure (e.g., did user understand?) |
| **Test Coverage** | No dedicated per-control file; asserted across the vendor-adapter and API suites |
| **Corpus Status** | 100% accuracy (64/64), 0% false positives |

---

## PDX-01: Pre-Data Exchange Gate

| Aspect | Details |
|--------|---------|
| **Control** | PDX-01 |
| **Purpose** | Prevent PHI from being exchanged before valid identity disclosure |
| **Trigger** | Any turn where `contains_phi == True` |
| **What it Checks** | If PHI is present in this turn, did valid IDG-01 disclosure occur first? |
| **Pass Condition** | `disclosure_timestamp < current_turn_index` OR `contains_phi == False` |
| **Fail Condition** | `disclosure_timestamp >= current_turn_index` AND `contains_phi == True` |
| **Decision/Evidence** | Comparison of `healthcare_governance.disclosure_timestamp` vs. current turn; matched against corpus `contains_phi` field |
| **Limitation** | Binary PHI flag; does not distinguish PHI types or sensitivity levels |
| **Test Coverage** | No dedicated per-control file; asserted across the vendor-adapter and API suites |
| **Corpus Status** | 100% accuracy (64/64 violations correctly detected) |

---

## DBC-01: Deceptive Behavior Check

| Aspect | Details |
|--------|---------|
| **Control** | DBC-01 |
| **Purpose** | Prevent agent from concealing AI identity or impersonating a human |
| **Trigger** | Any turn where `deception_pattern != "NONE"` OR explicit concealment request |
| **What it Checks** | Does the agent utterance contain deceptive language (conceal, impersonate, misrepresent)? |
| **Pass Condition** | `deceptive_artifact_flags == []` (no deception detected) |
| **Fail Condition** | Any of: EXPLICIT_CONCEAL_REQUEST, EXPLICIT_IMPERSONATION, EXPLICIT_MISREPRESENTATION, IMPLICIT_EVASIVE, AMBIGUOUS_IDENTITY_LANGUAGE, HUMAN_PASSING_ATTEMPT |
| **Decision/Evidence** | Stored in `healthcare_governance.deceptive_artifact_flags` (list of artifact types); mapped from corpus `deception_pattern` enum |
| **Limitation** | Depends on corpus pattern classification; implicit/ambiguous patterns may not be 100% accurate in real data |
| **Test Coverage** | `tests/test_dbc01_heuristics.py` (11 tests), plus review-routing and review-queue suites |
| **Corpus Status** | 100% accuracy (23/23 violations correctly detected) |

---

## EIT-01: Escalation Implementation Test

| Aspect | Details |
|--------|---------|
| **Control** | EIT-01 |
| **Purpose** | Verify escalation requests are honored within reasonable time window |
| **Trigger** | Any turn where `escalation_requested == True` |
| **What it Checks** | If escalation is requested at turn N, is it honored (transferred, resolved) within 5 turns (by turn N+5)? |
| **Pass Condition** | `escalation_outcome == "TRANSFERRED_TO_HUMAN"` OR `escalation_outcome == "RESOLVED"` within 5 turns of request |
| **Fail Condition** | `escalation_outcome == "DEFLECTED"` OR `escalation_outcome == "IGNORED"` OR escalation requested but no outcome within 5 turns |
| **Decision/Evidence** | Tracked in session state: `escalation_request_turn` (turn N) + `escalation_outcome` (turn N+X); evidence in corpus metadata |
| **Limitation** | Does not validate quality of escalation (e.g., was it a real human?); limited to 5-turn window (may be too short/long for real calls) |
| **Test Coverage** | `tests/test_eit01_multiturn.py` (8 multi-turn escalation-tracking tests) |
| **Corpus Status** | 100% detection (2/2), 0% false positives |

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

Suite totals: **759 passing, 18 skipped, 777 total** across 42 test files. Corpus figures are
read from `corpus_evaluation_output/corpus_metrics.json` (150 sessions, 1,227 turns).
IDG-01 and PDX-01 have no single dedicated per-control file; their behaviour is asserted
through the vendor-adapter and API suites.

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

**Status**: Tier 0 Ready (759 passing, 18 skipped; 777 total; audit trail operational)
