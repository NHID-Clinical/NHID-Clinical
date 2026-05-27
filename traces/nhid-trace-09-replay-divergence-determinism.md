NHID-Clinical • EXEC → PERSIST → replay-integrity-violation

session: NHID-TRACE-09-446CCAF4
context: B2B eligibility call / replay_mode=cached / external_calls_cached=false (misconfigured)

---

event stream (append-only)

t=00:00  INGEST     REPLAY REQUEST: session_id=REPLAY-001, replay_mode=cached
t=00:00  VALIDATE   external_calls_cached=false (misconfiguration)
t=00:00  STATE      Event stream loaded from store: 7 events
t=00:00  EXEC       LLM call made during replay (external_calls_cached=false)
t=00:00  EXEC       LLM returned different completion than original session
t=00:00  PERSIST    Replay result differs from original — divergence detected
t=00:00  PERSIST    ATR-01 violation: replay_integrity=FAIL

---

replay attempt (deterministic)

input: identical event stream
constraints: no external calls
result: FAIL

---

failure observation

Replay with external_calls_cached=false caused an LLM re-invocation that produced a different completion than the original session, breaking deterministic audit reconstruction.

---

implication

- Replay divergence means post-incident audit reconstruction is unreliable — you cannot prove what the AI said during the original call.
- This is the most dangerous replay failure mode in healthcare voice AI: silent divergence that looks like a successful replay.
- The canonical constraint (no external calls during replay) must be enforced as a hard schema rule, not a convention.

---

classification

state machine: REPLAY → DIVERGENCE_DETECTED
event store: CORRUPTED — replay result written over original event stream
failure coverage: Divergence detected; ATR-01 violation recorded
replay integrity: FAIL — LLM re-invocation produced non-identical output

---

next iteration

- Enforce external_calls_cached=true as a hard requirement when replay_mode=cached (JSON Schema if/then constraint).
- Add a replay integrity hash to the original event record — SHA-256 of the canonical output payload.
- Implement a replay divergence alert that triggers when replay output hash does not match original.

---

NHID-Clinical is mapping where deterministic orchestration breaks in real-world healthcare voice AI systems.
