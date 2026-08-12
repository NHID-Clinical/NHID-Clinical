# NHID-Clinical Tonic Corpus Evaluation Summary

**Date**: 2026-08-11  
**Evaluated Corpus**: Tonic Fabricate Synthetic Evaluation (150 sessions, 1,227 turns)  
**Engine Status**: Tier 0 Pilot Ready (656 tests passing, 18 skipped; 674 total)  
**Corpus Integration Status**: Schema mapping required

---

## Executive Summary

The Tonic synthetic evaluation corpus is well-designed, comprehensive, and ready for use as a reference dataset. However, direct evaluation against the current NHID-Clinical policy engine requires a schema adapter—the corpus uses a simplified turn-level event format while the engine expects healthcare system governance context fields.

**Recommendation**: The schema adapter development is now prioritized. The engine is ready for shadow pilots based on 656 passing tests and verified control implementations.

---

## Corpus Inventory (PHASE 1)

### Session Structure
- **Total sessions**: 150 (exact count matching allocation table)
- **Total turns**: 1,227 (8.2 avg turns/session, range 4-10)
- **Session ID format**: SESS-0001 through SESS-0150
- **Scenario ID format**: SCN-[CONTROL]-[SUBTYPE]-[INDEX]-[SERIAL]

### Control Allocation (Verified)
| Control | Sessions | % | Purpose |
|---------|----------|---|---------|
| Clean (baseline) | 45 | 30% | Positive control cases + escalation handling |
| IDG-01 (Identity) | 30 | 20% | Disclosure timing, clarity, repeated disclosure |
| PDX-01 (PHI Gate) | 30 | 20% | PHI sequencing relative to disclosure |
| EIT-01 (Escalation) | 25 | 17% | Multi-turn escalation tracking, deflection |
| DBC-01 (Deception) | 20 | 13% | Explicit/implicit deception patterns |
| **Total** | **150** | **100%** | |

### Decision Distribution
| Decision | Count | % |
|----------|-------|---|
| AUTHORIZED (all PASS) | 73 | 48.7% |
| BLOCKED (critical violations) | 47 | 31.3% |
| REVIEW (implicit/minor violations) | 30 | 20.0% |

### Violation Patterns
| Pattern | Count | Examples |
|---------|-------|----------|
| PASS (no violations) | 73 | Compliant disclosures, proper PHI sequencing |
| Single violations | 30 | IDG-01 only, PDX-01 only, DBC-01 only, EIT-01 only |
| Double violations | 31 | IDG+PDX (23), IDG+DBC (8) |
| Triple violations | 16 | IDG+PDX+EIT (10), IDG+PDX+DBC (4), DBC+IDG+EIT (2) |

### Event Type Coverage
| Event Type | Count | % | Purpose |
|-----------|-------|---|---------|
| SMALL_TALK | 339 | 27.6% | Greeting/context |
| CLOSING | 294 | 24.0% | Call termination |
| IDENTITY_DISCLOSURE | 140 | 11.4% | IDG-01 testing |
| PHI_REQUEST | 139 | 11.3% | PDX-01 testing |
| PHI_RESPONSE | 139 | 11.3% | PHI exchange completion |
| ESCALATION_REQUEST | 42 | 3.4% | EIT-01 testing |
| ESCALATION_OUTCOME | 38 | 3.1% | Escalation resolution |
| DECEPTION_ATTEMPT | 10 | 0.8% | DBC-01 explicit |
| DECEPTION_EVASION | 23 | 1.9% | DBC-01 implicit |
| IDENTITY_QUESTION | 27 | 2.2% | DBC-01 follow-up |
| PII_EXCHANGE | 36 | 2.9% | Non-PHI personal data |

---

## Data Quality Validation (PHASE 2)

### Integrity Checks
✅ **Chronological ordering**: 100% valid (all timestamps strictly increasing within sessions)  
✅ **Unique identifiers**: 150 session IDs, 1,227 turn IDs (no collisions)  
✅ **Required fields**: All present (speaker, utterance, event_type, metadata flags)  
✅ **Semantic consistency**: All violation patterns match allocation table predictions  
✅ **Turn counts**: All sessions have 4-10 turns (matches spec, n=150)  

### Field Coverage
- `speaker`: 100% populated (CALLER or VOICE_AGENT)
- `utterance`: 100% populated, 20-300 char range
- `event_type`: 100% valid (all recognized types)
- `contains_phi`: 100% flagged correctly
- `contains_pii`: 100% flagged correctly
- `disclosure_status`: Properly set (DISCLOSED, NOT_DISCLOSED, AMBIGUOUS, LATE, REPEATED, N/A)
- `escalation_requested`: Correctly tracked (boolean)
- `escalation_outcome`: Proper resolution metadata
- `deception_pattern`: Comprehensive taxonomy (EXPLICIT_*, IMPLICIT_*, AMBIGUOUS_*, etc.)

### Ground Truth Labels
✅ **IDG-01 expected**: 64 violations (VIOLATION), 84 pass (PASS), 2 N/A  
✅ **PDX-01 expected**: 64 violations, 71 pass, 15 N/A  
✅ **DBC-01 expected**: 23 violations, 17 pass, 110 N/A  
✅ **EIT-01 expected**: 12 violations, 26 pass, 112 N/A  
✅ **ATR-01 expected**: All sessions have audit event turn indices  

---

## Schema Mapping Analysis (PHASE 3)

### Current Engine Input Schema
```python
# Expected by policy engine (from tests and audit trail):
session = {
    "session_id": str,
    "turns_so_far": list[dict],           # Prior turn context
    "current_turn_index": int,
    # Healthcare governance context (required):
    "healthcare_governance": {
        "disclosure_timestamp": int | None,
        "phi_accessed": list[str],        # Field names (member_id, dob, etc.)
        "deceptive_artifact_flags": list[str],
        # ... more fields
    },
    # Audit context (required for ATR-01):
    "event_id": str,
    "timestamp": str,
    "session_id": str,
    # ... more audit fields
}

event = {
    "input_payload": {
        "speech_text": str,               # Utterance text
    },
    "healthcare_governance": {...},
    "state_before": str,                 # State machine context
    # ... more fields
}
```

### Corpus Event Schema
```python
# Provided by Tonic corpus:
turn = {
    "session_id": str,
    "scenario_id": str,
    "turn_number": int,
    "timestamp": str,                    # ISO8601
    "speaker": str,                      # CALLER | VOICE_AGENT
    "utterance": str,                    # Dialogue text
    "event_type": str,                   # SMALL_TALK | IDENTITY_DISCLOSURE | ...
    "contains_phi": bool,                # Simplified flag
    "contains_pii": bool,                # Simplified flag
    "disclosure_status": str,            # DISCLOSED | NOT_DISCLOSED | ...
    "escalation_requested": bool,
    "escalation_outcome": str,           # TRANSFERRED_TO_HUMAN | RESOLVED | ...
    "deception_pattern": str,            # EXPLICIT_CONCEAL_REQUEST | ...
}
```

### Mapping Gap Analysis

| Engine Requirement | Corpus Provides | Adapter Needed |
|------------------|----------------|---|
| healthcare_governance.disclosure_timestamp | disclosure_status (qualitative) | ✅ Parse turn index from event_type |
| phi_accessed (field list) | contains_phi (boolean) | ✅ Infer from utterance + event_type |
| deceptive_artifact_flags (list) | deception_pattern (string) | ✅ Map pattern enum to flags |
| state_before (FSM context) | None | ✅ Derive from conversation flow |
| event_id, timestamp, session_id (audit) | All present in corpus | ✅ Pass through directly |
| speech_text (utterance) | utterance field | ✅ Direct mapping |

**Gap Severity**: Medium. All required information exists in corpus, but requires transformation/inference layer.

---

## Corpus Use Cases

### ✅ Now (Pre-Pilot, Tier 0)
1. **Reference specification validation**: Corpus documents all 5 controls end-to-end
2. **Scenario documentation**: Each session is a documented test case with ground truth
3. **Compliance evidence**: Demonstrates testing breadth (150 sessions across control buckets)
4. **Manual review**: QA/compliance staff can hand-verify sample transcripts

### 🔄 Open
1. **Adapter accuracy**: Resolve the IDG-01 false-positive and EIT-01 non-detection results below
2. **Regression testing**: Automated nightly runs to catch accuracy drift
3. **Control coverage matrix**: Verify all subtype scenarios remain passing

---

## Measured Results

The schema adapter (`scripts/tonic_schema_adapter.py`) and evaluation harness
(`scripts/evaluate_tonic_corpus.py`) are implemented, and the corpus has been evaluated.
The figures below are read directly from `corpus_evaluation_output/corpus_metrics.json`
(run 2026-08-11), not estimated:

| Control | In scope | Expected | Detected | Detection rate | FP rate | Accuracy |
| :-- | --: | --: | --: | --: | --: | --: |
| IDG-01 | 148 | 64 | 148 | 100.0% | 100.0% | 43.2% |
| PDX-01 | 135 | 64 | 64 | 100.0% | 0.0% | 100.0% |
| DBC-01 | 40 | 23 | 23 | 100.0% | 0.0% | 100.0% |
| EIT-01 | 40 | 2 | 0 | 0.0% | 0.0% | 95.0% |

**Read these honestly.** PDX-01 and DBC-01 are accurate against this corpus. IDG-01 flags every
in-scope session — it catches all 64 seeded violations but also all 84 clean ones, so its
precision here is unusable pending adapter or semantics work. EIT-01 missed both seeded
escalation failures. These are open defects in the corpus-evaluation path, not in the unit
suite, and they are a direct reason Tier 0 remains observe-only.

---

## Integration Status

### Complete
- ✅ 656 passing unit tests (18 skipped; 674 total)
- ✅ 8 EIT-01 multi-turn regression tests
- ✅ 5 ATR-01 persistence integration tests
- ✅ External audit persistence layer
- ✅ Corpus inventory and data quality validation
- ✅ Schema adapter (turn event → engine event)
- ✅ Corpus evaluation harness and per-control detection rates

### Open
- [ ] Root-cause IDG-01's 100% false-positive rate against this corpus
- [ ] Root-cause EIT-01's 0% detection rate against this corpus
- [ ] Add nightly corpus regression run

### Future candidates (not scheduled)
- [ ] ML-based implicit deception detection
- [ ] NLP disclosure quality scoring
- [ ] Millisecond-precision PHI timing gates
- [ ] Multi-channel support (chat, email, async)
- [ ] Escalation path verification

---

## Key Findings

### ✅ What Works Now
1. **Corpus quality**: Well-structured, comprehensive, ground-truth validated
2. **Engine reliability**: 656 passing / 18 skipped, deterministic, pure design preserved
3. **Control coverage**: All 5 controls represented across 150 scenarios
4. **Audit trail**: ATR-01 external persistence operational
5. **Multi-turn detection**: EIT-01 escalation tracking verified in the unit suite across 5-turn gaps
6. **Evaluation path**: Schema adapter and corpus harness implemented and runnable

### ⚠️ What Needs Work
1. **IDG-01 precision**: 100% false-positive rate against this corpus — unresolved
2. **EIT-01 corpus detection**: 0/2 seeded escalation failures detected — unresolved
3. **Regression automation**: No nightly corpus run wired into CI yet

### ℹ️ Reference Notes
- Tonic Fabricate corpus aligns well with NHID-Clinical v1.3 spec
- Scenarios test both happy paths and complex violation combinations
- Ground truth labels are detailed and explainable (see expected_reason fields)
- Audit event indices properly documented for ATR-01 verification

---

## Conclusion

**Tier 0 Shadow Pilot**: ✅ **Suitable for observe-only evaluation**
- Unit suite green: 656 passing, 18 skipped, 674 total
- External audit persistence operational and tested
- Pure design constraints maintained — `evaluate_all()` still performs no I/O
- Tier 0 is shadow mode: decisions are recorded, never enforced

**Corpus Evaluation**: ⚠️ **Implemented, results mixed**
- Adapter and harness are built and have been run against all 150 sessions
- PDX-01 and DBC-01 are accurate; IDG-01 and EIT-01 are not, and remain open
- The corpus is a reference dataset, not a conformance claim

**Next Action**: Run the Tier 0 shadow pilot against the 674-test baseline while the IDG-01
and EIT-01 corpus-path defects are investigated. Neither defect blocks observe-only use,
because nothing is enforced in shadow mode — but neither should be described as resolved.
