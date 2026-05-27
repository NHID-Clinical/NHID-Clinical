NHID-Clinical • INGEST → VALIDATE → session-binding-failure

session: NHID-TRACE-03-4E875E34
context: B2B payer-provider voice call / inbound webhook / missing Twilio field

---

event stream (append-only)

t=00:00  INGEST     Received POST /voice/process — form-urlencoded
t=00:00  VALIDATE   CallSid field: absent (not present in request body)
t=00:00  VALIDATE   Validation failed: VALIDATION_MISSING_CALLSID
t=00:00  VALIDATE   Early exit: cannot bind session without identifier

---

replay attempt (deterministic)

input: identical event stream
constraints: no external calls
result: N/A

---

failure observation

Request without a CallSid cannot be bound to a session, making the event unreplayable and breaking idempotency guarantees from the first pipeline stage.

---

implication

- Without session_id, no event record can be written — ATR-01 audit completeness is structurally impossible.
- Malformed Twilio webhook configurations (missing CallSid) are silent in production without explicit validation at ingress.
- The 400 response must carry a structured error body so upstream systems can distinguish session binding failures from policy rejections.

---

classification

state machine: N/A — no session created
event store: INCOMPLETE — no event written (no session_id available)
failure coverage: Validation failure detected at VALIDATE stage, 400 returned
replay integrity: N/A — no session to replay

---

next iteration

- Log missing-CallSid failures to a separate dead-letter queue with request timestamp and source IP.
- Add CallSid validation as the first check in the VALIDATE stage before any other processing.
- Return a structured JSON error body with error code VALIDATION_MISSING_CALLSID on 400 responses.

---

NHID-Clinical is mapping where deterministic orchestration breaks in real-world healthcare voice AI systems.
