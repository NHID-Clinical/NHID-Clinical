# NHID-Clinical Fabricate Evaluation Corpora

Synthetic healthcare call transcripts for testing the NHID-Clinical governance framework across five compliance controls (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01).

## Corpora Inventory

### 1. Baseline CSV Corpus (Original Fabricate v1.0)
**Files**: `conversations.csv`, `turns.csv`  
**Format**: Two-table relational CSV export  
**Size**: 550 conversations, ~2,200 turns  
**Purpose**: Baseline detection rate validation via `scripts/check_baseline.py`  
**Status**: ✅ Production (Phase 6A)

**Expected Baseline** (as of July 31, 2026):
```
IDG-01:  70/70 (100%)  — AI identity disclosure detection
PDX-01:  41/41 (100%)  — Pre-disclosure PHI gate
DBC-01: 183/200 (91.5%) — Deceptive behavior detection (voice artifacts)
EIT-01: 169/171 (98.8%) — Escalation honor verification
```

---

### 2. Shadow Pilot Corpus (NEW — July 31, 2026)
**File**: `shadow_pilot.jsonl`  
**Format**: JSONL (newline-delimited JSON, minimal-event-schema)  
**Size**: 60 conversations, 301 turns  
**Purpose**: Tier 0 internal shadow pilot data extraction and CAS measurement  
**Status**: ✅ Production-ready (Phase 6A+)

**Schema Compatibility**: ✅ FULLY COMPATIBLE
- All required fields present: turn_index, speaker, text, is_identity_disclosure, is_escalation_request, contains_phi
- expected_violations: dict { control: 0/1 }
- No transformation needed

**Coverage by Control**:
| Control | Count | Ratio | Type |
|---------|-------|-------|------|
| IDG-01 | 21 | 35% | Realistic disclosure variations |
| PDX-01 | 15 | 25% | Edge-case timing boundaries |
| DBC-01 | 11 | 18% | Borderline identity assertions |
| EIT-01 | 8 | 13% | Escalation handling patterns |
| ATR-01 | 44 | 73% | Standard audit trail scenarios |

**Compliance Distribution**:
- 16 compliant conversations (26.7%)
- 44 violating conversations (73.3%)
- 25 multi-rule scenarios (41.7%)

**Key Characteristics**:
- 26.7% compliant baseline mirrors realistic payer call data
- Average 5.0 turns/conversation (tighter scenarios)
- Includes language switching (English/Spanish mid-call)
- CAS scores (0-100) and risk bands included for each call
- Metadata: caller_role, agent_type, emotional_state, scenario_type, impersonation_latency_ms

**Validation Status**: ✅ 100% schema-compatible, zero transformation required

**Usage**:
```bash
# Tier 0 pilot measurement
python docs/pilot-kit/measure_pilot.py \
  --corpus fixtures/fabricate/shadow_pilot.jsonl \
  --output pilot_results.json
```

---

### 3. Adversarial Cascading Corpus (STAGED — Pending Schema Alignment)
**File**: `staging/adversarial_cascading_raw.jsonl`  
**Format**: JSONL (raw TONIC Fabricate export, UNCHANGED)  
**Size**: 200 conversations, 1,313 turns  
**Purpose**: Stress testing edge cases and cascading violation patterns (future)  
**Status**: ⏳ Staging (schema alignment required before production)

**Schema Compatibility**: ⚠️ REQUIRES ALIGNMENT
| Field | TONIC Export | Engine Expects | Status |
|-------|--------------|----------------|--------|
| turns container | `conversation_turns` | `turns` | ❌ Mismatch |
| turn identifier | `turn` | `turn_index` | ❌ Mismatch |
| identity disclosure | **NOT PROVIDED** | `is_identity_disclosure` | ❌ Missing |
| escalation request | **NOT PROVIDED** | `is_escalation_request` | ❌ Missing |
| PHI flag | **NOT PROVIDED** | `contains_phi` | ❌ Missing |

**Coverage by Control** (declared in corpus):
| Control | Count | Ratio |
|---------|-------|-------|
| IDG-01 | 148 | 74% |
| PDX-01 | 129 | 65% |
| DBC-01 | 63 | 31% |
| EIT-01 | 52 | 26% |
| ATR-01 | 133 | 67% |

**Key Issue**: 
- 200 scenarios expect DBC-01 and ATR-01 violations to be detected
- Required ground-truth fields (`is_identity_disclosure`, `is_escalation_request`, `contains_phi`) are not provided
- These fields **cannot be reliably fabricated** from transcript text alone
- No transformation was applied to preserve data integrity

**Why Not Integrated Yet**:
See `staging/README.md` for detailed explanation:
- `is_identity_disclosure` — Cannot infer; only AI knows if it disclosed
- `is_escalation_request` — Cannot infer; requires understanding caller intent
- `contains_phi` — Unreliable if inferred; requires domain knowledge and manual validation

**Path Forward**:
1. Request TONIC export with all required fields
2. OR: Provide mapping documentation + validation rules for field inference
3. Once aligned: Move to `adversarial_cascading.jsonl` and add to production corpus
4. Update baseline expectations if needed

**Note**: The raw export is preserved unchanged in staging to maintain data integrity and enable future alignment work.

---

## Corpus Selection Guide

| Task | Corpus | Why |
|------|--------|-----|
| Verify baseline unchanged | CSV (550 convs) | Frozen baseline via check_baseline.py |
| Run Tier 0 shadow pilot | Shadow Pilot (60 convs) | Fully compatible, includes CAS scores |
| Combined regression suite | CSV + Shadow (610 convs) | Current production-ready evaluation |
| Stress test edge cases (future) | Adversarial (staging) | Awaiting schema alignment |

---

## Integration Status

### Production Corpora (Integrated)
- ✅ CSV Fabricate (550 conversations) — active, baseline locked
- ✅ Shadow Pilot JSONL (60 conversations) — active, ready for Tier 0

### Staging Corpora (Pending Work)
- ⏳ Adversarial Cascading JSONL (200 conversations, raw) — awaiting TONIC schema clarification

**Total Current Corpus**: 610 conversations (550 CSV + 60 Shadow JSONL)  
**Total With Staging**: 810 conversations (adds 200 Adversarial pending alignment)

---

## Testing

### Run All Production Evaluation Suites
```bash
# 1. Baseline validation (existing CSV)
python scripts/check_baseline.py

# 2. Unit test suite (includes synthetic evaluation)
pytest tests/ -k synthetic_eval

# 3. Shadow pilot evaluation
python docs/pilot-kit/measure_pilot.py \
  --corpus fixtures/fabricate/shadow_pilot.jsonl \
  --output pilot_results.json
```

### Future: When Adversarial Corpus Is Aligned
```bash
# Evaluate combined corpus
python -c "
from adapters.fabricate_adapter import convert_csv, convert_jsonl
from src.synthetic_eval_loop import compute_detection_rates

# Production corpora
csv = convert_csv('fixtures/fabricate/conversations.csv', 'fixtures/fabricate/turns.csv')
shadow = convert_jsonl('fixtures/fabricate/shadow_pilot.jsonl')

# Staging corpus (when ready)
# adversarial = convert_jsonl('fixtures/fabricate/adversarial_cascading.jsonl')

print('CSV Baseline:', compute_detection_rates(csv))
print('Shadow Pilot:', compute_detection_rates(shadow))
# print('Adversarial:', compute_detection_rates(adversarial))
"
```

---

## Metadata & Attribution

**Shadow Pilot Corpus**:
- Source: TONIC Fabricate v1.1 (July 2026)
- Scenarios: Healthcare call simulation, Tier 0 pilot patterns
- Format: Minimal-event-schema for pilot measurement
- Validation: July 31, 2026 (100% schema-compatible)

**Adversarial Cascading Corpus** (Staging):
- Source: TONIC Fabricate v1.0 (July 2026)
- Scenarios: Cascading governance violations, edge-case stress testing
- Format: Raw TONIC export (pending alignment)
- Status: Staged July 31, 2026 (schema mismatches documented)

**CSV Baseline Corpus**:
- Source: Fabricate v1.0 (CSV format)
- Scenarios: 550 balanced healthcare call patterns
- Format: Relational CSV (conversations.csv + turns.csv)
- Status: Production since Phase 6A

All scenarios are synthetic and created for governance research and validation purposes.

---

## Contact & Support

- Shadow Pilot questions: See `docs/pilot-kit/README.md`
- Adversarial Cascading alignment: See `staging/README.md`
- Baseline validation: See `scripts/check_baseline.py`

---

**Last Updated**: July 31, 2026  
**Maintenance**: Phase 6A+ (ongoing)  
**Status**: 610 conversations in production; 200 in staging pending schema alignment
