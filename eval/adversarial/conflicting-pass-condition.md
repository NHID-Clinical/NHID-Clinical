# Control decision table (TEST FIXTURE, ALTERED COPY)

## PDX-01: Pre-Data Exchange Gate

| Field | Value |
|---|---|
| **Control** | PDX-01 |
| **Pass Condition** | Protected-data exchange is permitted on the disclosing turn, provided disclosure is completed before the turn ends |
| **Fail Condition** | `PDX01_PHI_GATE_TRIGGERED` only when disclosure never occurs during the call |
