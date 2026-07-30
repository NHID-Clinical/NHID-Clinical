# NHID-Clinical Metrics & Observability v1.0

**Date**: 2026-07-30  
**Status**: ✓ FINAL — Lightweight metrics for pilot operations  
**Version**: 1.0  
**Target Audience**: Ops team, pilot customers, compliance  

---

## Executive Summary

NHID-Clinical v1.1 will emit lightweight observability metrics to enable:
1. **Operational Monitoring**: Detect latency regressions, throughput changes
2. **Pilot Success Metrics**: Measure false-positive rate, false-negative rate, rule adherence
3. **Compliance Tracking**: Count violations, escalations, PHI access patterns
4. **Incident Investigation**: Correlate requests → decisions → outcomes

**Collection Method**: CloudWatch Metrics (AWS-native) with JSON audit log export for deep analysis  
**Dashboard**: Basic pilot dashboard (5–10 key metrics)  
**Alerting**: Thresholds for operational anomalies  

---

## Key Metrics

### 1. Policy Engine Performance

| Metric | Definition | Threshold (Alert) | Purpose |
|--------|-----------|---|---|
| `nhid.policy_engine.requests` | Requests evaluated (count) | N/A | Throughput tracking |
| `nhid.policy_engine.latency_ms` | Time to evaluate all rules (p50, p95, p99) | p95 > 500ms | Latency regression detection |
| `nhid.policy_engine.errors` | Evaluation exceptions (count) | > 0 per day | Crash detection |
| `nhid.policy_engine.cache_hits` | Cached results (count) | N/A | Performance optimization tracking |

**Implementation**:
```python
import time
import cloudwatch

def evaluate_all(session, event):
    start = time.perf_counter()
    try:
        decision = policy_engine(session, event)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Emit metrics
        cloudwatch.put_metric_data(
            MetricName="nhid.policy_engine.latency_ms",
            Value=elapsed_ms,
            Unit="Milliseconds"
        )
        cloudwatch.put_metric_data(
            MetricName="nhid.policy_engine.requests",
            Value=1,
            Unit="Count"
        )
        
        return decision
    except Exception as e:
        cloudwatch.put_metric_data(
            MetricName="nhid.policy_engine.errors",
            Value=1,
            Unit="Count"
        )
        raise
```

### 2. Governance Decision Distribution

| Metric | Definition | Threshold (Alert) | Purpose |
|--------|-----------|---|---|
| `nhid.decisions.allow_data` | ALLOW_DATA actions (count) | N/A | Baseline authorization rate |
| `nhid.decisions.deny_data` | DENY_DATA actions (count) | > 20% of total | Possible false-positive spike |
| `nhid.decisions.escalate` | ESCALATE actions (count) | N/A | Escalation path utilization |
| `nhid.decisions.conformant_rate` | Percentage of conformant (pass all rules) | < 70% | Possible rule drift |

**Implementation**:
```python
def evaluate_all(session, event):
    decision = policy_engine(session, event)
    
    action_name = decision.action.value.lower()
    cloudwatch.put_metric_data(
        MetricName=f"nhid.decisions.{action_name}",
        Value=1,
        Unit="Count"
    )
    
    if decision.is_conformant():
        cloudwatch.put_metric_data(
            MetricName="nhid.decisions.conformant",
            Value=1,
            Unit="Count"
        )
    else:
        cloudwatch.put_metric_data(
            MetricName="nhid.decisions.nonconformant",
            Value=1,
            Unit="Count"
        )
    
    return decision
```

### 3. Rule-Level Violation Detection

| Metric | Definition | Threshold (Alert) | Purpose |
|--------|-----------|---|---|
| `nhid.violations.idg01.count` | IDG-01 violations detected | N/A | Disclosure compliance |
| `nhid.violations.pdx01.count` | PDX-01 violations detected | N/A | Timing compliance |
| `nhid.violations.dbc01.count` | DBC-01 violations detected | > 5 per day | Deception detection |
| `nhid.violations.eit01.count` | EIT-01 violations detected | > 2 per day | Escalation compliance |
| `nhid.violations.atr01.count` | ATR-01 violations detected | N/A | Audit trail (v1.2) |

**Implementation**:
```python
def evaluate_all(session, event):
    decision = policy_engine(session, event)
    
    for violation in decision.violations:
        rule_id = violation.rule_id.lower()
        cloudwatch.put_metric_data(
            MetricName=f"nhid.violations.{rule_id}.count",
            Value=1,
            Unit="Count"
        )
    
    return decision
```

### 4. PHI Access Compliance

| Metric | Definition | Threshold (Alert) | Purpose |
|--------|-----------|---|---|
| `nhid.phi.access_requests` | PHI field requests (count) | N/A | Access pattern baseline |
| `nhid.phi.access_granted` | PHI actually transmitted (count) | N/A | Governance compliance |
| `nhid.phi.access_blocked` | PHI denied by governance (count) | N/A | False-denial tracking |
| `nhid.phi.member_id_requests` | Specifically member ID requests | N/A | Sensitive data tracking |

**Implementation**:
```python
def evaluate_all(session, event):
    decision = policy_engine(session, event)
    
    # Count PHI requested
    phi_requested = event.get("healthcare_governance", {}).get("phi_requested", [])
    if phi_requested:
        cloudwatch.put_metric_data(
            MetricName="nhid.phi.access_requests",
            Value=len(phi_requested),
            Unit="Count"
        )
    
    # Count PHI granted or blocked
    if decision.action == PolicyAction.ALLOW_DATA:
        phi_accessed = event.get("healthcare_governance", {}).get("phi_accessed", [])
        cloudwatch.put_metric_data(
            MetricName="nhid.phi.access_granted",
            Value=len(phi_accessed),
            Unit="Count"
        )
    elif decision.action == PolicyAction.DENY_DATA:
        cloudwatch.put_metric_data(
            MetricName="nhid.phi.access_blocked",
            Value=1,
            Unit="Count"
        )
    
    return decision
```

### 5. Escalation Tracking

| Metric | Definition | Threshold (Alert) | Purpose |
|--------|-----------|---|---|
| `nhid.escalations.requested` | Callers requested escalation (count) | N/A | Escalation rate |
| `nhid.escalations.honored` | Escalation granted (count) | N/A | Compliance check |
| `nhid.escalations.deflected` | Escalation deflected (count) | > 1 per day | EIT-01 violation rate |
| `nhid.escalations.denied` | Escalation denied (count) | > 1 per day | EIT-01 violation rate |
| `nhid.escalations.honor_rate` | Percentage honored / requested | < 90% | Escalation quality SLA |

**Implementation**:
```python
def evaluate_all(session, event):
    decision = policy_engine(session, event)
    
    escalation_log = event.get("healthcare_governance", {}).get("escalation_log", {})
    if escalation_log.get("escalation_requested"):
        cloudwatch.put_metric_data(
            MetricName="nhid.escalations.requested",
            Value=1,
            Unit="Count"
        )
        
        outcome = escalation_log.get("escalation_outcome")
        if outcome == "honored":
            cloudwatch.put_metric_data(
                MetricName="nhid.escalations.honored",
                Value=1,
                Unit="Count"
            )
        elif outcome in ["deflected", "denied"]:
            cloudwatch.put_metric_data(
                MetricName=f"nhid.escalations.{outcome}",
                Value=1,
                Unit="Count"
            )
    
    return decision
```

### 6. Pilot Success Metrics

| Metric | Definition | Pilot Target | Purpose |
|--------|-----------|---|---|
| `nhid.pilot.false_positive_rate` | % DENY_DATA when should be ALLOW | < 0.1% | Minimize customer friction |
| `nhid.pilot.false_negative_rate` | % ALLOW_DATA when should be DENY | < 5% | Minimize compliance risk |
| `nhid.pilot.rule_accuracy` | Violations correctly detected | > 85% | Governance effectiveness |
| `nhid.pilot.conformant_pass_rate` | Compliant calls pass all rules | = 100% | Rule correctness |

**Calculation (Post-Hoc Analysis)**:
```python
def calculate_pilot_metrics(evaluation_corpus, live_decisions):
    """
    Compare evaluation corpus expected results vs. live engine decisions.
    Run daily during pilot to track metrics.
    """
    false_positives = 0  # Expected ALLOW, got DENY
    false_negatives = 0  # Expected DENY, got ALLOW
    correct = 0
    total = 0
    
    for scenario in evaluation_corpus:
        expected_violations = set(scenario["expected_violations"])
        
        # Get live decision for this scenario
        live_decision = live_decisions.get(scenario["scenario_id"])
        live_violations = {v.rule_id for v in live_decision.violations}
        
        if expected_violations and not live_violations:
            false_negatives += 1  # Missed a violation
        elif not expected_violations and live_violations:
            false_positives += 1  # Spurious violation
        else:
            correct += 1
        
        total += 1
    
    fpr = false_positives / total if total else 0
    fnr = false_negatives / total if total else 0
    accuracy = correct / total if total else 0
    
    return {
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "accuracy": accuracy
    }
```

---

## Observability Dashboard (Pilot Operations)

### Dashboard Layout: NHID-Clinical Pilot Operations (Week 1–4)

**Row 1: Engine Health**
```
┌─────────────────────────────────────────────────────────────┐
│ Requests (24h)    │ Latency p95 (ms)  │ Errors (24h)      │
│ 1,250             │ 187               │ 0                 │
└─────────────────────────────────────────────────────────────┘
```

**Row 2: Decision Distribution**
```
┌────────────────────────────────────────────────────────────────┐
│ ALLOW (68%)  │ DENY (22%)  │ ESCALATE (10%)  │ Conformant %   │
│ 850 calls    │ 275 calls   │ 125 calls       │ 68%            │
└────────────────────────────────────────────────────────────────┘
```

**Row 3: Rule Violations (24h counts)**
```
┌────────────────────────────────────────────────────────────────┐
│ IDG-01  │ PDX-01  │ DBC-01  │ EIT-01  │ ATR-01  │ Total        │
│ 85      │ 62      │ 18      │ 3       │ 0       │ 168          │
└────────────────────────────────────────────────────────────────┘
```

**Row 4: Escalation Quality**
```
┌────────────────────────────────────────────────────────────────┐
│ Escalations Requested (24h): 125                               │
│   ├─ Honored: 115 (92%)  ✓                                    │
│   ├─ Deflected: 8 (6%)   ⚠ (alert threshold: >2)            │
│   └─ Denied: 2 (2%)      ⚠ (alert threshold: >2)            │
└────────────────────────────────────────────────────────────────┘
```

**Row 5: PHI Access**
```
┌────────────────────────────────────────────────────────────────┐
│ PHI Requested: 850   │ PHI Granted: 578   │ PHI Blocked: 272  │
│ (100%)               │ (68%)              │ (32%)             │
└────────────────────────────────────────────────────────────────┘
```

---

## Alert Thresholds (Pilot Operations)

### Critical Alerts (Page On-Call)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Engine error rate | > 0 per 6h | Investigate crash, roll back if needed |
| Latency p95 | > 500ms | Check CPU/memory, optimize hot path |
| Conformant rate drops | < 70% (baseline) | Rule regression or data quality issue |
| IDG-01 violations spike | > 200% 24h average | Possible bot disclosure regression |

### Warning Alerts (Notify Ops)

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Escalation honor rate | < 90% | Monitor EIT-01 compliance |
| False-positive rate | > 0.2% | Review pilot customer feedback |
| Deny rate increases | > 30% (baseline ~22%) | Possible rule drift |

### Informational Alerts (Log Only)

| Condition | Threshold | Purpose |
|-----------|-----------|---------|
| Daily violation summary | End of day | Trend analysis |
| PHI access patterns | Hourly | Baseline establishment |

---

## Data Collection & Export

### Real-Time Collection (CloudWatch)

```yaml
# AWS CloudWatch Metrics Configuration
CloudWatch Namespace: "NHID-Clinical"
Collection Frequency: Per request (latency metrics), per minute (aggregates)
Retention: 15 months
Export: Daily to S3 for long-term analysis
```

**CloudWatch CLI Query Examples**:
```bash
# Get latency p95 for last 24 hours
aws cloudwatch get-metric-statistics \
  --namespace NHID-Clinical \
  --metric-name nhid.policy_engine.latency_ms \
  --dimensions Name=Statistic,Value=p95 \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600

# Get violation counts by rule
aws cloudwatch get-metric-statistics \
  --namespace NHID-Clinical \
  --metric-name nhid.violations.idg01.count \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400
```

### Audit Log Export (Deep Analysis)

```json
// S3 location: s3://nhid-audit-logs/{date}/audit_events.jsonl
// Daily export of all governance decisions and rule violations
// Used for: false-positive analysis, rule calibration, compliance reporting

Example lines:
{"audit_event_id": "evt_...", "event_type": "GOVERNANCE_DECISION", "conformant": true, "violations": []}
{"audit_event_id": "evt_...", "event_type": "GOVERNANCE_DECISION", "conformant": false, "violations": [{"rule_id": "IDG-01", ...}]}
...
```

---

## Pilot Reporting (Weekly)

### Weekly Governance Report (To Pilot Customer)

```markdown
# NHID-Clinical Weekly Operations Report
**Week Ending**: 2026-08-06

## Summary
- Requests processed: 1,250
- Conformant rate: 68%
- Escalations honored: 92%
- False-positive incidents: 0
- Latency p95: 187ms

## Rule Compliance
- IDG-01 (Disclosure): 85 violations detected ✓
- PDX-01 (Timing): 62 violations detected ✓
- DBC-01 (Deception): 18 violations detected ✓
- EIT-01 (Escalation): 3 violations detected ✓

## Incidents
- None

## Recommendations
- Continue monitoring escalation deflection rate (2 incidents)
- Baseline establishment complete; metrics stable

## Next Week Focus
- Monitor false-negative rate (false denials)
- Continue metric collection for final report
```

---

## Implementation Roadmap

### v1.1 (Current)
- ✓ Define metrics schema
- ✓ Implement CloudWatch metric emission
- ✓ Create pilot dashboard
- ✓ Document alert thresholds

### v1.2 (Phase 2)
- ✓ Add custom metric aggregations (false-positive rate calculation)
- ✓ Implement automated weekly reporting
- ✓ Integrate with customer notification (SNS)
- ✓ Build historical trend analysis

### v2.0 (Future)
- ✓ Advanced anomaly detection (ML-based)
- ✓ Real-time compliance alerting
- ✓ Multi-tenant metric isolation

---

## Specification Status

**Version**: 1.0 (Pilot-grade)  
**Effective Date**: 2026-07-30  
**Target Deployment**: Pilot week 1  
**Next Review**: End of pilot (4 weeks)  

**Recommendation**: Collect baseline metrics for 1 week before pilot customer exposure to establish normal ranges.

