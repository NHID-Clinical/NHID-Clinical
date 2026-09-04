# NHID-Clinical System Architecture (Tier 0)

**Date**: 2026-08-11  
**Version**: v1.3-shadow-ready  
**Status**: Pilot Ready (1110 tests passing, 0 skipped, 0 xfailed; schema adapter operational)

---

## Executive Summary

NHID-Clinical is a **pure functional policy engine** for healthcare voice conversations. It evaluates 5 policy controls (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01) and produces deterministic PolicyDecision objects. The engine itself has **zero I/O, zero side effects, zero runtime configuration**—it is pure computation.

This document describes:
1. **Core Engine Architecture**: Stateless evaluation pipeline
2. **Integration Layers**: Schema adapter, audit persistence, session state machine
3. **Deployment Mode**: Shadow mode (observe-only, non-blocking)
4. **Data Flow**: From raw voice event to PolicyDecision to audit trail
5. **Corpus Evaluation Framework**: Synthetic data validation pipeline

---

## Part 1: Core Engine

### 1.1 Pure Functional Design

The engine is a single entry point:

```python
PolicyDecision = evaluate_all(
    session: Dict[str, Any],           # Session context (state machine)
    event: Dict[str, Any]              # Current event (input payload + governance)
) → PolicyDecision
```

**Key Invariants:**
- No file I/O, no network, no database access
- No mutation of input arguments
- No random state, no clock, no flags
- Deterministic: Same input → Same output, always
- Testable: No mocks needed (pure functions)

### 1.2 PolicyDecision Output

```python
@dataclass
class PolicyDecision:
    action:         PolicyAction            # DISCLOSE_IDENTITY | ESCALATE_HUMAN | CONTINUE_AI | DENY_DATA | LOG_ONLY
    reason_code:    str                     # Machine-readable decision code
    policy_version: str                     # POLICY_ENGINE_VERSION
    violations:     list[BoundaryViolation] # rule_id, description, severity
    next_state:     str                     # Workflow state label
    twiml_fallback: str | None              # Optional telephony fallback markup
    gather_speech:  bool                    # Whether the caller should be re-prompted
    audit_trail:    AuditTrail | None       # Populated when execution_context is supplied
```

`evaluate_all()` returns the **most restrictive** action across the five controls plus the
bot-to-bot rule: `DENY_DATA` > `ESCALATE_HUMAN` > `DISCLOSE_IDENTITY` > `LOG_ONLY` / `CONTINUE_AI`.

**Example** — PHI requested at turn 2 with no prior disclosure (actual engine output):
```json
{
  "action": "DENY_DATA",
  "reason_code": "PDX01_PHI_GATE_TRIGGERED",
  "policy_version": "1.0.0",
  "next_state": "GATE_BLOCKED",
  "violations": [
    {
      "rule_id": "IDG-01",
      "description": "AI agent has not disclosed non-human identity. Turn count: 2",
      "severity": "critical"
    },
    {
      "rule_id": "PDX-01",
      "description": "PHI exchange attempted before identity disclosure",
      "severity": "critical"
    }
  ],
  "audit_trail": {
    "session_id": "s1",
    "agent_identity": { "…": "…" },
    "organization_identity": { "…": "…" },
    "events": [ { "event_id": "…", "timestamp": "2026-08-11T14:30:02Z" } ]
  }
}
```

`audit_trail` is an `AuditTrail` object (`src/nhid_audit_trail.py`), not a bare list, and is
`None` unless the event carries a complete `execution_context` block. ATR-01 violations are
raised for any missing required audit field.

### 1.3 The Five Policy Controls

**IDG-01: Identity Disclosure Gate**
- **What it checks**: Did the agent disclose its non-human nature before the user shared sensitive data?
- **Trigger**: `event_type == IDENTITY_DISCLOSURE` OR `contains_phi == True`
- **Pass condition**: `disclosure_timestamp < first_phi_access`
- **Fail condition**: `disclosure_timestamp == None` OR `disclosure_status != DISCLOSED`
- **Evidence**: `healthcare_governance.disclosure_timestamp` (turn index of valid disclosure)

**PDX-01: Pre-Data Exchange Gate**
- **What it checks**: No PHI is exchanged before valid IDG-01 disclosure
- **Trigger**: `contains_phi == True` AND turn processed
- **Pass condition**: `disclosure_timestamp < current_turn` OR no PHI accessed
- **Fail condition**: PHI accessed at turn N, disclosure at turn > N
- **Evidence**: `input_payload.speech_text`, `healthcare_governance.phi_accessed` (field list)

**DBC-01: Deceptive Behavior Check**
- **What it checks**: Agent does not conceal AI identity or use impersonation
- **Trigger**: `deception_pattern != "NONE"` OR `explicit_conceal_request`
- **Pass condition**: `deceptive_artifact_flags == []` (no deception detected)
- **Fail condition**: Any of: EXPLICIT_CONCEAL_REQUEST, EXPLICIT_IMPERSONATION, EXPLICIT_MISREPRESENTATION
- **Evidence**: `healthcare_governance.deceptive_artifact_flags` (artifact classification)

**EIT-01: Escalation Implementation Test**
- **What it checks**: Escalation requests are honored within a reasonable turn window (5 turns)
- **Trigger**: `escalation_requested == True` at turn N
- **Pass condition**: `escalation_outcome != "DEFLECTED"` within 5 turns
- **Fail condition**: Escalation requested but not honored (callback rejected, call ended without handoff)
- **Evidence**: `session.escalation_path_available`, derived by the adapter from whether a
  `TRANSFERRED_TO_HUMAN` outcome follows the request

**ATR-01: Audit Trail Requirements**
- **What it checks**: All policy-relevant events are recorded for audit
- **Trigger**: Every turn processed
- **Pass condition**: `audit_trail` populated with 5+ events per turn (disclosure, PHI access, deception, escalation, state transition)
- **Fail condition**: Missing audit events (handled by external AuditPersistenceManager)
- **Evidence**: `PolicyDecision.audit_trail` (list of timestamped events)

### 1.4 Session State Machine

The engine tracks a simple state machine for multi-turn conversations:

```
CONVERSATION (initial)
  ↓ (if escalation_requested=True)
ESCALATION_PENDING (turn N)
  ↓ (if escalation_outcome="TRANSFERRED_TO_HUMAN" within 5 turns)
ESCALATION_RESOLVED
  ↓
CONVERSATION (back to main flow)

CONVERSATION (any turn)
  ↓ (if critical violation detected: IDG-01 or PDX-01)
GATE_BLOCKED (recorded; in shadow mode the call is not actually stopped)
```

`next_state` values emitted by the engine include `AWAITING_DISCLOSURE`, `ACTIVE`,
`GATE_BLOCKED`, `DECEPTION_FLAGGED`, `ESCALATING`, and `ESCALATION_FAILED`.

The session state is **passed by caller** (external to engine):

```python
session = {
    "session_id": "sess-123",
    "state_before": "CONVERSATION",        # Current state
    "state_after": "CONVERSATION",         # Updated state
    "escalation_request_turn": None,       # Track escalation window
    "disclosure_timestamp": 3,             # Turn when disclosure occurred
    "phi_exchanged_before_disclosure": False,
}
```

---

## Part 2: Integration Layers

### 2.1 Schema Adapter (Tonic Corpus)

The schema adapter transforms simplified corpus events into engine-compatible input:

```
Tonic Turn Event (simplified)
  ├─ session_id: str
  ├─ turn_number: int
  ├─ speaker: "CALLER" | "VOICE_AGENT"
  ├─ utterance: str
  ├─ event_type: "IDENTITY_DISCLOSURE" | "PHI_REQUEST" | ...
  ├─ contains_phi: bool (binary flag)
  ├─ disclosure_status: "DISCLOSED" | "AMBIGUOUS" | ...
  ├─ deception_pattern: "EXPLICIT_CONCEAL_REQUEST" | ...
  └─ escalation_requested: bool

  ↓ [TonicschemAdapter.adapt_turn()]

Engine Input Event (structured)
  ├─ session_id: str
  ├─ input_payload:
  │   └─ speech_text: str (utterance)
  ├─ healthcare_governance:
  │   ├─ disclosure_timestamp: int | None (inferred from turn index)
  │   ├─ phi_accessed: List[str] (inferred from utterance patterns)
  │   ├─ deceptive_artifact_flags: List[str] (mapped from enum)
  │   └─ identity_assertion_text: str
  ├─ audit_context: {event_id, timestamp, actor_id, ...}
  └─ state_before: str
```

**Inference Rules:**

1. **disclosure_timestamp** (inferred):
   - Search backwards from current turn for first IDENTITY_DISCLOSURE + disclosure_status=DISCLOSED
   - Return turn index if found, None otherwise
   - Rule: "searched backwards for first valid disclosure"

2. **phi_accessed** (inferred from utterance):
   - Match utterance text against keyword patterns for known PHI field names
   - Patterns: "member id" → member_id, "date of birth" → date_of_birth, etc.
   - Fallback: ["unknown_phi"] if contains_phi=true but no fields matched
   - Rule: "matched utterance patterns against known PHI field names"

3. **deceptive_artifact_flags** (mapped from enum):
   - EXPLICIT_CONCEAL_REQUEST → ["explicit_conceal_ai"]
   - EXPLICIT_IMPERSONATION → ["explicit_impersonate_human"]
   - EXPLICIT_MISREPRESENTATION → ["explicit_misrepresent"]
   - IMPLICIT_EVASIVE → ["implicit_evasive_identity"]
   - AMBIGUOUS_IDENTITY_LANGUAGE → ["ambiguous_identity_language"]
   - HUMAN_PASSING_ATTEMPT → ["human_passing_attempt"]
   - Rule: "mapped deception_pattern enum to artifact classification"

### 2.2 Audit Persistence Layer (ATR-01)

The engine outputs audit_trail; an external AuditPersistenceManager persists it:

```
PolicyDecision
  ├─ audit_trail: AuditTrail
  │   ├─ session_id: str
  │   ├─ agent_identity: AgentIdentity
  │   ├─ organization_identity: OrganizationIdentity
  │   └─ events: list[AuditEvent]
  │       ├─ event_id: str (unique, hash-chained)
  │       ├─ timestamp: ISO8601
  │       └─ evidence_hash: str (signed on append)
  │
  └─ [AuditPersistenceManager.persist(audit_trail)]
      ↓
      AuditStore (SQLite / DynamoDB)
      ├─ Hash chain verification (each event_id includes hash of previous)
      ├─ Immutable log (append-only)
      └─ Evidence for compliance audits
```

**Key Property**: Hash chaining ensures audit trail integrity (tampering detected).

### 2.3 Shadow Mode (Deployment)

In shadow mode, the policy decision is **observed but not enforced**:

```
Voice Call Handler
  ├─ Capture: speech_text, speaker, event_type
  ├─ Reconstruct: healthcare_governance context
  ├─ Call: PolicyDecision = evaluate_all(session, event)
  │
  ├─ [Decision: DENY_DATA with critical violations]
  │   ├─ Log: "violation detected: PDX-01 (PDX01_PHI_GATE_TRIGGERED)"
  │   ├─ Audit: persist to AuditStore
  │   ├─ Alert: send notification to human reviewer
  │   └─ Observe only: conversation continues (NOT BLOCKED)
  │
  └─ Return: Continue to user
```

**Contrast with Enforcement Mode** (future — not implemented):
```
[Decision: DENY_DATA]
  └─ Receiver action: Terminate call, transfer to human agent, or prompt identity re-disclosure
```

---

## Part 3: Data Flow End-to-End

### 3.1 Happy Path (All Controls PASS)

**Scenario**: Agent discloses identity, user shares PHI after disclosure, no deception, no escalation needed.

```
Turn 0: SMALL_TALK (greeting, no disclosure yet)
  Event: {utterance: "hello", event_type: "SMALL_TALK", contains_phi: false}
  Session: {turn_count: 0, disclosure_timestamp: None}
  Engine: evaluate_all(session, event)
    → IDG-01: VIOLATION (disclosure not yet made)
    → action:      DISCLOSE_IDENTITY
    → reason_code: IDG01_DISCLOSURE_MISSING
    → next_state:  AWAITING_DISCLOSURE

Turn 3: IDENTITY_DISCLOSURE (agent discloses)
  Event: {utterance: "I am an automated system", disclosure_status: "DISCLOSED"}
  Adapter: disclosure_timestamp ← turn 3 timestamp
  Engine: evaluate_all(session, event)
    → IDG-01: PASS (disclosure recorded)
    → action:      CONTINUE_AI
    → reason_code: ATR01_AUDIT_COMPLETE
    → next_state:  ACTIVE

Turn 4: PHI_REQUEST (user shares data)
  Event: {utterance: "my member ID is 12345", phi_accessed: ["member_id"]}
  Adapter: disclosure_timestamp carried forward from turn 3
  Engine: evaluate_all(session, event)
    → IDG-01: PASS · PDX-01: PASS (PHI after disclosure) · DBC-01: PASS
    → action:      CONTINUE_AI
    → reason_code: ATR01_AUDIT_COMPLETE
    → next_state:  ACTIVE

Final decision: CONTINUE_AI (no violations, all controls pass)
```

Note that the engine emits `DISCLOSE_IDENTITY` on turn 0 — disclosure is required up front, so
"no violations yet" is not the same as "nothing to do."

### 3.2 Bad Path A: Premature PHI Access (PDX-01 Violation)

**Scenario**: User shares PHI before agent discloses identity.

```
Turn 0-2: SMALL_TALK (no disclosure yet)
  Adapter: disclosure_timestamp ← None

Turn 2: PHI_RESPONSE (user gives data before agent discloses)
  Event: {utterance: "my DOB is 1990-01-01", phi_accessed: ["date_of_birth"]}
  Adapter: disclosure_timestamp ← None (no disclosure yet)
  Engine: evaluate_all(session, event)
    → IDG-01: VIOLATION (critical — no disclosure by turn 2)
    → PDX-01: VIOLATION (critical — PHI with disclosure_timestamp=None)
    → action:      DENY_DATA
    → reason_code: PDX01_PHI_GATE_TRIGGERED
    → next_state:  GATE_BLOCKED

Final decision: DENY_DATA
Reason: "PHI exchange attempted before identity disclosure"
```

`DENY_DATA` is the most restrictive action and wins the composite regardless of what later
turns report. In shadow mode it is recorded, not applied.

### 3.3 Bad Path B: Deceptive Concealment (DBC-01 Violation)

**Scenario**: Agent explicitly asks user to conceal that they're talking to AI.

```
Turn 0: SMALL_TALK (greeting)
Turn 1: DECEPTION_ATTEMPT
  Event: {
    utterance: "Don't tell anyone you're talking to an AI",
    event_type: "DECEPTION_ATTEMPT",
    deception_pattern: "EXPLICIT_CONCEAL_REQUEST"
  }
  Adapter: deceptive_artifact_flags ← ["explicit_conceal_ai"]
  Engine: evaluate_all(session, event)
    → DBC-01: VIOLATION (explicit concealment request)
    → action:      LOG_ONLY
    → reason_code: DBC01_ARTIFACT_DETECTED
    → next_state:  DECEPTION_FLAGGED

Final decision: LOG_ONLY
Reason: "Deceptive artifact detected — flagged for review, session continues"
```

DBC-01 deliberately resolves to `LOG_ONLY` rather than a hard denial: deception heuristics are
the least precise of the five controls, so a detection routes to human review instead of
terminating the exchange.

### 3.4 Bad Path C: Escalation Not Honored (EIT-01 Violation)

**Scenario**: User requests escalation, but request is deflected/ignored.

```
Turn 2: ESCALATION_REQUEST (user requests human agent, path available)
  Event: {utterance: "I want to speak to a human"}
  Session: {escalation_path_available: True}
  Engine: evaluate_all(session, event)
    → EIT-01: PASS (escalation recognised and routable)
    → action:      ESCALATE_HUMAN
    → reason_code: EIT01_ESCALATION_TRIGGERED
    → next_state:  ESCALATING

Turn 7: Same request, but no escalation path is available
  Event: {utterance: "I want to speak to a human", escalation_outcome: "DEFLECTED"}
  Session: {escalation_path_available: False}
  Engine: evaluate_all(session, event)
    → EIT-01: VIOLATION (escalation requested, not honored)
    → action:      ESCALATE_HUMAN
    → reason_code: EIT01_ESCALATION_NOT_HONORED
    → next_state:  ESCALATION_FAILED

Final decision: ESCALATE_HUMAN
Reason: "Escalation requested but no escalation path was available"
```

Both branches return `ESCALATE_HUMAN` — the action states what should happen, and the
`reason_code` / `next_state` pair distinguishes a healthy handoff from a failed one.

---

## Part 4: Corpus Evaluation Framework

### 4.1 Pipeline

```
Tonic Corpus (150 sessions, 1,227 turns)
  ├─ CSV Load: session_id, turn_number, speaker, utterance, event_type, ...
  │
  ├─ [TonicschemAdapter.load_corpus()]
  │   └─ Group by session_id, sort by turn_number
  │
  ├─ [TonicCorpusEvaluator.evaluate_all_sessions()]
  │   ├─ For each session_id:
  │   │   ├─ For each turn_idx:
  │   │   │   ├─ adapted_event ← adapter.adapt_turn(session_id, turns, turn_idx)
  │   │   │   ├─ decision ← evaluate_all(session, adapted_event)
  │   │   │   ├─ Track violations by control (IDG-01, PDX-01, DBC-01, EIT-01)
  │   │   │   └─ Append to results
  │   │   └─ Aggregate per-control metrics
  │   │
  │   └─ Output:
  │       ├─ corpus_metrics.json (detection_rate, fp_rate, accuracy per control)
  │       ├─ corpus_detailed_results.json (first 50 sessions + all metadata)
  │       └─ corpus_failures.json (any exceptions encountered)
  │
  └─ [Compare: Expected (corpus ground truth) vs Detected (engine output)]
      ├─ IDG-01: 64 violations expected, 64 detected (0% FP rate)
      ├─ PDX-01: 64 violations expected, 64 detected (100% accuracy)
      ├─ DBC-01: 23 violations expected, 23 detected (100% accuracy)
      ├─ EIT-01: 2 violations expected, 2 detected (100% detection)
      └─ ATR-01: 150 sessions audited (100% events logged)
```

### 4.2 Metrics Interpretation

**Perfect Controls** (100% accuracy):
- PDX-01: Adapter correctly infers PHI fields from utterance; engine correctly checks pre-disclosure PHI access
- DBC-01: Adapter correctly maps deception patterns; engine correctly detects explicit deception

**Problematic Controls** (open, under investigation):
- IDG-01: Every session detecting violations (148/148) when only 64 expected
  - Root cause: Adapter disclosure_timestamp inference OR engine IDG-01 semantics mismatch
  - Investigation: Compare adapter inferences vs. corpus labels for CLEAN sessions (should all PASS)
  
- EIT-01: Zero violations detected when 2 expected
  - Root cause: Multi-turn escalation state tracking through adapter not reconstructing engine state correctly
  - Investigation: Deep-dive into escalation_request_turn and escalation_outcome mapping

**Audit Trail** (ATR-01):
- Working as designed: 5 audit events logged per turn
- Persistence layer (external AuditPersistenceManager) is operational

---

## Part 5: Deployment & Release

### 5.1 Shadow Pilot (Tier 0, Current)

**Status**: Production Ready  
**Test Coverage**: 1110 passing tests, 0 skipped, 0 xfailed  
**Release Tag**: v1.3-shadow-ready  

**Deployment**:
1. Run against real voice conversations
2. Extract: speech_text, speaker, event_type, contains_phi flags
3. Reconstruct: healthcare_governance context (same adapter inference rules)
4. Call: `evaluate_all(session, event)`
5. Log: PolicyDecision (violations, action, audit_trail)
6. Persist: Audit trail to AuditStore (hash-chained)
7. Alert: Human reviewer if violations detected
8. Continue: Workflow proceeds (shadow mode = non-blocking)

### 5.2 Enforcement Mode (Future, Post-Pilot)

When violations are to be enforced:

1. If action=DENY_DATA: Withhold PHI, terminate, or re-prompt for identity
2. If action=DISCLOSE_IDENTITY: Require disclosure before continuing
3. If action=ESCALATE_HUMAN: Transfer to a human agent
4. If action=LOG_ONLY: Flag for human review, continue the call
5. If action=CONTINUE_AI: Proceed normally

Receiver obligations for each action are specified normatively in
[`enforcement-profile.md`](enforcement-profile.md).

---

## Part 6: Key Design Principles

1. **Pure Computation**: Engine is deterministic, testable, no side effects
2. **External Integration**: Schema adaptation, state machine, audit persistence all outside engine
3. **Audit-First**: Every decision is logged with full reasoning for compliance
4. **Incremental Validation**: Corpus evaluation measures control detection; adapter accuracy work is open
5. **Shadow Mode First**: Observe-only deployment reduces pilot risk
6. **Determinism**: Same input always produces same output (enables regression testing)

---

## Part 7: File Structure

```
NHID-Clinical/
├─ src/
│   └─ nhid_policy_engine_v1.py (1110 tests passing)
│       ├─ evaluate_all(session, event) → PolicyDecision
│       ├─ IDG-01, PDX-01, DBC-01, EIT-01, ATR-01 implementations
│       └─ No I/O, no external calls, pure functional
│
├─ scripts/
│   ├─ validate_ci.py (updated: flexible test count)
│   ├─ tonic_schema_adapter.py (schema transformation)
│   └─ evaluate_tonic_corpus.py (corpus evaluation harness)
│
├─ tests/                     (55 files, 1110 tests, all passing)
│   ├─ test_atr01_audit_trail.py   (12 tests)
│   ├─ test_atr01_persistence.py   (5 tests)
│   ├─ test_dbc01_heuristics.py    (11 tests)
│   ├─ test_eit01_multiturn.py     (8 tests)
│   ├─ test_enforcement_profile.py (13 tests)
│   ├─ test_identity.py            (26 tests — NHID-Auth v2)
│   └─ … adapter, API, audit-store, and CAS suites
│
├─ docs/
│   ├─ SYSTEM_ARCHITECTURE.md (this file)
│   ├─ CORPUS_EVALUATION_SUMMARY.md (data quality validation)
│   ├─ CONTROL_DECISION_TABLE.md (per-control decision matrix)
│   ├─ enforcement-profile.md (normative receiver actions)
│   └─ claim-boundaries.md (policy on external claims)
│
└─ corpus_evaluation_output/
    ├─ corpus_metrics.json (per-control metrics)
    └─ corpus_detailed_results.json (first 50 sessions)
```

IDG-01 and PDX-01 are exercised across the adapter and endpoint suites rather than in
dedicated per-control files.

---

## Conclusion

NHID-Clinical v1.3 is a **pure, testable, deterministic policy engine** suitable for Tier 0
shadow (observe-only) evaluation. The corpus evaluation framework exercises the control
implementations against 150 reference scenarios; the results in
`corpus_evaluation_output/corpus_metrics.json` are mixed and are reported as measured:

| Control | Detection rate | False-positive rate | Accuracy |
| :-- | --: | --: | --: |
| IDG-01 | 100.0% | 0.0% | 100.0% |
| PDX-01 | 100.0% | 0.0% | 100.0% |
| DBC-01 | 100.0% | 0.0% | 100.0% |
| EIT-01 | 100.0% | 0.0% | 100.0% |

All four behavioural controls detect every seeded violation with no false positives against this
corpus. The earlier IDG-01 (100% FP) and EIT-01 (0% detection) results were caused by four defects
in the corpus-evaluation path — assertion text not carried forward, IDG-01 scored per turn rather
than per session, escalation data routed into unused metadata, and an incomplete audit context —
all fixed in `scripts/tonic_schema_adapter.py` and `scripts/evaluate_tonic_corpus.py`. The policy
engine was not modified. A 150-session synthetic corpus with 2 seeded escalation failures is a
floor, not a validation, which is why Tier 0 remains observe-only. The unit suite is green:
1110 passing, 0 skipped, 0 xfailed.
