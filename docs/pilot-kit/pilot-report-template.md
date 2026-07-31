# NHID-Clinical Tier 0 Shadow Pilot Report

**Organization:**
**Workflow:** Prior Auth / Claims Status / Billing
**Sample size:** X calls
**Date range:**
**Prepared by / date:**

> Measurements from a shadow pilot against this organization's own call
> traffic using the NHID-Clinical Tier 0 kit. NHID-Clinical is a voluntary
> open baseline (CC BY 4.0) — these are measurements, not certifications.

## Key metrics

| Metric | Value |
| :--- | :--- |
| Median Impersonation Latency | X seconds / X turns |
| First-turn disclosure rate | XX% |
| Never-disclosed rate | XX% |
| Calls with pre-disclosure PHI | XX% |
| Escalation honor rate | XX% |
| Average CAS | 0.XX |

## CAS trust-tier distribution

| Tier | Threshold | Calls | % |
| :--- | :--- | ---: | ---: |
| Verified Trust | ≥ 0.90 | | |
| Conditional Trust | ≥ 0.75 | | |
| Review Required | ≥ 0.50 | | |
| Denied / Degraded | ≥ 0.20 | | |
| Hard Denial | < 0.20 | | |

## Top violations

| Control | Name | Calls affected | % |
| :--- | :--- | ---: | ---: |
| IDG-01 | Identity Disclosure Gate | | |
| PDX-01 | Pre-Data Exchange Gate | | |
| DBC-01 | Deceptive Behavior Check | | |
| EIT-01 | Escalation Implementation Test | | |

## Data quality

- Calls dropped for unmappable/missing fields: X (X%)
- Flagged calls hand-reviewed: X · confirmed: X · false positives: X
- Known gaps (e.g. no voice-forensics flags → DBC-01 Tier A not assessed):

## Observations

-

## Recommendations

-

---

Generated with `docs/pilot-kit/measure_pilot.py` and
`tools/pilot_report_generator.py`.
