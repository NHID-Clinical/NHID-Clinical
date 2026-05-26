NHID-Clinical • INGEST → VALIDATE → sanitization-failure

session: NHID-TRACE-02-8EE06DFE
context: B2B payer-provider voice call / eligibility check / adversarial input
generated: 2026-05-26T17:37:26.575+00:00

---

event stream (append-only)

t=00:00  INGEST     Received POST /voice/process — form-urlencoded
t=00:00  INGEST     SpeechResult='\x00\x00\x00check claim status'
t=00:00  VALIDATE   Null byte detection: 3 null bytes found at positions 0-2
t=00:00  VALIDATE   Sanitization: null bytes stripped → 'check claim status'
t=00:00  POLICY     IDG-01 evaluated on sanitized text: disclosure_timestamp=null
t=00:00  POLICY     Decision: DISCLOSE_IDENTITY / IDG01_DISCLOSURE_MISSING
t=00:00  EXEC       TwiML fallback rendered
t=00:00  PERSIST    Event written with sanitized input_payload.speech_text

---

replay attempt (deterministic)

input: identical event stream
constraints: no external calls
result: PASS

---

failure observation

Null bytes in SpeechResult were not sanitized before policy evaluation, causing the policy engine to receive a string with embedded control characters that could produce inconsistent pattern matching.

---

implication

- Null byte injection is a known attack vector against string-handling pipelines in healthcare data contexts.
- Unsanitized null bytes can cause silent truncation in C-based string libraries, producing different behavior across STT/TTS vendors.
- The event record must store the sanitized text, not the raw injection payload, to preserve audit integrity.

---

classification

state machine: UNKNOWN → AWAITING_DISCLOSURE (session created from sanitized input)
event store: Complete — sanitized speech_text stored in event record
failure coverage: Input sanitization applied before policy evaluation
replay integrity: PASS — sanitization is deterministic for identical input

---

next iteration

- Add null byte and control character stripping to the VALIDATE stage normalization function.
- Log the presence of null bytes as a boundary_violation with severity=minor for forensic awareness.
- Include null-byte injection in the canonical red-team test suite for all pipeline deployments.

---

NHID-Clinical is mapping where deterministic orchestration breaks in real-world healthcare voice AI systems.
