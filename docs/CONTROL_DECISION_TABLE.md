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
| **Test Coverage** | 60 unit tests (disclosure timing, AMBIGUOUS status, repeated disclosure) |
| **Corpus Status** | 100% false positive rate (investigating in Phase 5) |

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
| **Test Coverage** | 80 unit tests (premature PHI, repeated PHI, mixed event types) |
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
| **Test Coverage** | 40 unit tests (explicit conceal, impersonation, evasion, subtle language) |
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
| **Test Coverage** | 40 unit tests (8 multi-turn regression tests for escalation tracking across conversation gaps) |
| **Corpus Status** | 0% detection rate (2/2 violations missed; Phase 5 investigation needed) |

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
| **Decision/Evidence** | Stored in `PolicyDecision.audit_trail` (list of timestamped AuditEvent objects); persisted via hash-chained append-only log |
| **Limitation** | Persistence is outside engine (external responsibility); engine cannot enforce persistence failure detection |
| **Test Coverage** | 40 unit tests (5 integration tests for external audit persistence with SQLite/DynamoDB) |
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

| Control | Unit Tests | Integration Tests | Multi-turn | Corpus Sessions | Status |
|---------|------------|-------------------|-----------|-----------------|--------|
| IDG-01 | 60 | 2 | 3 | 64 expected | ✓ Tests pass, 100% FP in corpus |
| PDX-01 | 80 | 3 | 2 | 64 expected | ✓ Tests pass, 100% accuracy in corpus |
| DBC-01 | 40 | 2 | 0 | 23 expected | ✓ Tests pass, 100% accuracy in corpus |
| EIT-01 | 40 | 8 | 8 | 2 expected | ✓ Tests pass, 0% detection in corpus |
| ATR-01 | 40 | 5 | 0 | 150 sessions | ✓ Tests pass, operational in corpus |
| **Total** | **260** | **20** | **13** | **150** | **656 passing** (674 total) |

---

## Next Steps (Phase 5)

1. **IDG-01 Accuracy**: Root cause 100% false positive rate
   - Audit: Compare adapter inferences for CLEAN sessions (should all PASS)
   - Hypothesis: disclosure_timestamp inference too aggressive OR engine IDG-01 semantics mismatch

2. **EIT-01 Accuracy**: Root cause 0% detection rate
   - Audit: Deep-dive into escalation_request_turn state tracking
   - Hypothesis: Multi-turn escalation state not reconstructed correctly through adapter

3. **Corpus Baseline**: Use perfected metrics as regression testing baseline
   - Add nightly corpus evaluation to CI pipeline
   - Alert on accuracy drift (e.g., if PDX-01 drops below 95%)

4. **ML-based Deception Detection**: Improve DBC-01 from pattern matching to NLP
   - Current: Keyword patterns + enum mapping
   - Future: Train on real deceptive behavior corpus

5. **Millisecond-precision PHI Timing**: Upgrade PDX-01 to subsecond gates
   - Current: Turn-level granularity
   - Future: Word-level or phrase-level PHI detection

---

**Status**: Tier 0 Ready (656 passing, 18 skipped; 674 total; audit trail operational)
