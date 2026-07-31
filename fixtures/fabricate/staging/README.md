# Staging Corpus: Adversarial Cascading (Raw TONIC Export)

**Status**: Pending schema alignment  
**Format**: JSONL (raw TONIC Fabricate export, unchanged)  
**Scenarios**: 200 conversations  
**Last validated**: July 31, 2026

---

## Why This Corpus Is Staged, Not Integrated

The adversarial cascading corpus from TONIC Fabricate has **schema mismatches** with the current NHID-Clinical evaluation engine. Instead of fabricating missing data or silently normalizing field names, this corpus is preserved in raw form pending clarification from TONIC.

### Schema Mismatch Summary

| Required Field | NHID-Clinical Engine Expects | TONIC Export Provides | Status |
|---|---|---|---|
| turns container | `turns` (list) | `conversation_turns` | ❌ Field name mismatch |
| turn identifier | `turn_index` (int) | `turn` (int) | ❌ Field name mismatch |
| speaker | `speaker` (str) | `speaker` (str) | ✅ OK |
| text | `text` (str) | `text` (str) | ✅ OK |
| **is_identity_disclosure** | `is_identity_disclosure` (0/1) | **NOT PROVIDED** | ❌ **MISSING** |
| **is_escalation_request** | `is_escalation_request` (0/1) | **NOT PROVIDED** | ❌ **MISSING** |
| **contains_phi** | `contains_phi` (0/1) | **NOT PROVIDED** | ❌ **MISSING** |

---

## Missing Ground-Truth Fields

### 1. `is_identity_disclosure` — Cannot Infer
**Why it's required**: Marks turns where the AI agent disclosed its AI nature or non-human status.

**Why it cannot be fabricated**: 
- Only the AI agent knows with certainty whether it disclosed itself
- Text patterns are unreliable:
  - Agent might say "I'm AI" sarcastically or hypothetically
  - Agent might initially fail to disclose, then admit it later
  - Agent might claim "I'm not a real person" but use deceptive language anyway
- No reliable heuristic exists to mark disclosure moments from transcript alone

**What TONIC export should provide**: 
- Boolean flag per turn marking actual disclosure events
- Timestamp or turn index of disclosure
- Exact disclosure language (to verify against policy)

**Impact on evaluation**:
- IDG-01 (AI Identity Disclosure) detection depends on this field
- Without it, engine cannot distinguish compliant disclosure from implicit assumptions

---

### 2. `is_escalation_request` — Cannot Infer
**Why it's required**: Marks turns where the caller requests escalation to a human agent.

**Why it cannot be fabricated**:
- Requires understanding caller intent, not just keyword matching
- Context-dependent: "Can I speak to someone else?" might be request or casual question
- Sarcasm, hesitation, and cultural patterns complicate detection
- Some escalation requests use indirect language ("Is there a supervisor?", "Can I get a second opinion?")

**What TONIC export should provide**:
- Boolean flag per turn marking actual escalation requests
- Escalation type (urgent, routine, dispute)
- Caller's role/authority level (affects urgency)

**Impact on evaluation**:
- EIT-01 (Escalation Honor Verification) depends on this field
- Without it, engine cannot track whether caller's requests were honored or deflected

---

### 3. `contains_phi` — Unreliable Even If Inferred
**Why it's required**: Marks turns where Personally Identifiable Health Information is mentioned.

**Why fabrication is unreliable**:
- Requires domain knowledge of what constitutes PHI in healthcare context
- Can detect patterns like "member ID 400-10-1000" or "diagnosis: diabetes"
- But misses implicit PHI: "authorization for the procedure we discussed", "my insurance denial"
- Heuristics generate false positives (generic names like "John" aren't PHI) and false negatives

**What TONIC export should provide**:
- Boolean flag per turn indicating PHI presence
- PHI category if applicable (member_id, diagnosis, medication, provider_name, etc.)
- PHI span (exact text or position) for audit trail

**Impact on evaluation**:
- PDX-01 (PHI Pre-Disclosure Gate) depends on accurate PHI marking
- Without it, false positives and false negatives in pre-disclosure PHI detection

---

## Why Transformation Was Not Performed

**Principle**: Do not fabricate ground truth. Do not silently normalize when transformation masks missing data.

**What WAS NOT done**:
- ❌ Did not rename `conversation_turns` → `turns`
- ❌ Did not rename `turn` → `turn_index`
- ❌ Did not invent `is_identity_disclosure` flags
- ❌ Did not guess `is_escalation_request` values
- ❌ Did not heuristically detect `contains_phi`
- ❌ Did not modify field names to hide schema mismatch

**Why**:
1. **Data integrity**: Fabricated flags would corrupt the corpus
2. **Audit trail**: Transformations would become invisible history
3. **Reproducibility**: Future work cannot reverse-engineer what was changed
4. **Honesty**: The schema gap is real and must be acknowledged

---

## Path Forward: Required TONIC Export Fields

For future integration, TONIC Fabricate must export with these fields per turn:

```json
{
  "turn_index": 0,
  "speaker": "agent",
  "text": "...",
  "is_identity_disclosure": 1,  // Required: 1 if agent disclosed AI nature, 0 otherwise
  "is_escalation_request": 0,    // Required: 1 if caller requested escalation, 0 otherwise
  "contains_phi": 1,              // Required: 1 if turn contains PHI, 0 otherwise
  "created_at": "2026-07-28T23:05:52.799Z"  // Recommended
}
```

**Alternative: Mapping Documentation**
If TONIC cannot export these fields directly, provide:
1. Clear rules for inferring each field from transcript
2. Validation suite to verify inference accuracy
3. Confidence scores (e.g., "this turn has 95% certainty of containing PHI")

---

## Current Export Structure

**What TONIC DID provide** (correctly):
```json
{
  "scenario_id": "CASC-001",
  "category": "cascading_governance_violations",
  "subcategory": "missing_disclosure_phi_request_false_human_identity_claim",
  "title": "AI Non-Disclosure + PHI Request + False Human Claim",
  "scenario_description": "...",
  "languages_involved": ["en"],
  "conversation_turns": [
    {
      "turn": 1,           // Field name: 'turn' instead of 'turn_index'
      "speaker": "system",
      "language": "en",
      "text": "Call routed to payer prior-authorization system."
      // Missing: is_identity_disclosure, is_escalation_request, contains_phi
    },
    // ... more turns
  ],
  "expected_violations": ["IDG-01", "PDX-01", "DBC-01", "ATR-01"],
  "affected_controls": ["IDG-01", "PDX-01", "DBC-01", "ATR-01"],
  "expected_engine_outcome": "Governance engine should flag multi-stage violation chain...",
  "severity": "Critical",
  "failure_trigger": "..."
}
```

---

## Integration Checklist

Before moving adversarial_cascading from staging to production integration:

- [ ] TONIC confirms or provides `is_identity_disclosure` for all turns
- [ ] TONIC confirms or provides `is_escalation_request` for all turns
- [ ] TONIC confirms or provides `contains_phi` for all turns
- [ ] Field names standardized: `conversation_turns` → `turns`, `turn` → `turn_index`
- [ ] Validation: Run full evaluation suite against normalized corpus
- [ ] Documentation: Update corpus inventory with adversarial_cascading entry
- [ ] Regression tests pass with new corpus included
- [ ] Move from `staging/adversarial_cascading_raw.jsonl` to `adversarial_cascading.jsonl`

---

## Files in Staging

- **`adversarial_cascading_raw.jsonl`**: Original TONIC export, unchanged (200 conversations, ~668 KB)
- **`README.md`**: This documentation

---

## Timestamp

- **Staged**: July 31, 2026
- **Last validation**: July 31, 2026 (raw format confirmed, schema mismatches identified)
- **Status**: Awaiting TONIC alignment
