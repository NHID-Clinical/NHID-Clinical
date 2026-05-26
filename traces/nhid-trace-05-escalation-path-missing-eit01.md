NHID-Clinical • POLICY → EXEC → escalation-failure

session: NHID-TRACE-05-3A0A9EAD
context: B2B eligibility call / human requests transfer / escalation_path_available=false
generated: 2026-05-26T17:37:26.575+00:00

---

event stream (append-only)

t=00:00  INGEST     POST /voice/process — SpeechResult='I need to speak with a human'
t=00:00  VALIDATE   SpeechResult normalized: 'i need to speak with a human'
t=00:00  STATE      Session: disclosure confirmed, escalation_path_available=false
t=00:00  POLICY     EIT-01: escalation trigger detected in speech
t=00:00  POLICY     EIT-01: escalation_path_available=false — violation
t=00:00  POLICY     Decision: ESCALATE_HUMAN / EIT01_NO_ESCALATION_PATH
t=00:00  EXEC       TwiML: 'unable to transfer at this time' message rendered
t=00:00  PERSIST    1 boundary_violation: EIT-01 (critical)

---

replay attempt (deterministic)

input: identical event stream
constraints: no external calls
result: PASS

---

failure observation

Human operator explicitly requested escalation but the AI system had no functioning transfer path, stranding the caller and violating the NHID-Clinical safe-failover requirement.

---

implication

- An escalation path that exists in configuration but is not tested in production is functionally equivalent to no escalation path.
- The EIT-01 violation must be surfaced to operational dashboards immediately — a blocked escalation is a patient/member safety risk.
- The TwiML fallback message must include an alternative contact method (callback number, hours) when transfer fails.

---

classification

state machine: DISCLOSED → ESCALATION_FAILED
event store: Complete — EIT-01 critical violation recorded
failure coverage: EIT-01 detected; ESCALATE_HUMAN action returned with fallback TwiML
replay integrity: PASS

---

next iteration

- Add an escalation path health check to the server startup validation.
- Implement a circuit-breaker pattern for escalation path availability.
- Update TwiML fallback message to include a direct callback number when transfer is unavailable.

---

NHID-Clinical is mapping where deterministic orchestration breaks in real-world healthcare voice AI systems.
