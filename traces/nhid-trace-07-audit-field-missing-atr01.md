NHID-Clinical • POLICY → PERSIST → audit-gap

session: NHID-TRACE-07-01322645
context: B2B claim status call / pipeline_version missing from execution_context
generated: 2026-05-26T17:37:26.575+00:00

---

event stream (append-only)

t=00:00  INGEST     POST /voice/process — turn_count=1
t=00:00  VALIDATE   SpeechResult='checking claim status'
t=00:00  STATE      Session reconstructed: disclosure confirmed
t=00:00  POLICY     ATR-01: execution_context.pipeline_version=null
t=00:00  POLICY     ATR-01: AUDIT_FIELDS_MISSING violation
t=00:00  EXEC       Pipeline continues — ATR-01 does not block execution
t=00:00  PERSIST    Event written with ATR-01 violation in boundary_violations[]

---

replay attempt (deterministic)

input: identical event stream
constraints: no external calls
result: PASS

---

failure observation

The execution_context.pipeline_version field was null, making it impossible to reconstruct which pipeline version processed this call during a post-incident audit.

---

implication

- Missing pipeline_version breaks cross-incident correlation — you cannot identify whether multiple failures share a common pipeline version.
- ATR-01 violations do not halt execution, creating a silent audit gap that accumulates across sessions.
- Procurement and compliance reviewers require complete provenance chains; a missing pipeline_version fails an enterprise audit review.

---

classification

state machine: DISCLOSED → DISCLOSED (no state change, ATR-01 is non-blocking)
event store: INCOMPLETE — execution_context.pipeline_version missing from event record
failure coverage: ATR-01 detected; LOG_ONLY action; pipeline_version gap recorded
replay integrity: DEGRADED — provenance chain incomplete for this event

---

next iteration

- Add execution_context validation to the server startup check — fail fast if pipeline_version is not configured.
- Implement an ATR-01 compliance score across sessions: % of events with complete execution_context.
- Alert on ATR-01 violation rate exceeding 0% — any audit field missing is a governance regression.

---

NHID-Clinical is mapping where deterministic orchestration breaks in real-world healthcare voice AI systems.
