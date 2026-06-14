# Call-Progress Webhook

**Endpoint:** `POST /v1/webhooks/call-progress`  
**Auth:** None (no API key required)  
**Latency target:** ≤ 200 ms  

The call-progress webhook enables turn-by-turn conformance evaluation during a live call. Instead of evaluating after the call ends, your voice platform fires a webhook on each conversation turn and receives an immediate action recommendation.

---

## Architecture

```
Voice platform (VAPI / Twilio)
    │
    │  POST /v1/webhooks/call-progress  (one request per turn)
    ▼
NHID-Clinical API
    │  evaluate_all(session_state, event)
    │  < 200 ms
    ▼
Action response  →  voice platform acts (continue / inject disclosure / escalate / deny)
    │
    │  session_state sent back on next turn
    ▼
Next turn...
```

**Key design point:** The NHID-Clinical API is **stateless on this path** — it does not write to a database on call-progress requests. Your platform owns session state and must echo it back on every subsequent turn. This keeps latency low and requires no session management on the server side.

---

## Request Format

```json
{
  "session_id":    "vapi-call-001",
  "turn_index":    3,
  "speaker":       "agent",
  "text":          "What is the member ID on file?",
  "session_state": {
    "turn_count":            3,
    "disclosure_timestamp":  null,
    "escalation_available":  true
  }
}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `session_id` | string | yes | Unique identifier for the call session |
| `turn_index` | integer | yes | 0-based index of the current conversation turn |
| `speaker` | string | yes | `"agent"` or `"caller"` |
| `text` | string | yes | Transcribed text of the current turn |
| `session_state.turn_count` | integer | yes | Total completed turns so far |
| `session_state.disclosure_timestamp` | float or null | yes | Unix timestamp of first valid AI disclosure, or `null` if not yet disclosed |
| `session_state.escalation_available` | boolean | yes | Whether a human escalation path has been communicated |

---

## Response Format

```json
{
  "action":     "DENY_DATA",
  "violations": [
    { "rule_id": "IDG-01", "severity": "critical", "detail": "No prior disclosure" },
    { "rule_id": "PDX-01", "severity": "critical", "detail": "PHI requested before disclosure" }
  ],
  "session_state": {
    "turn_count":           3,
    "disclosure_timestamp": null,
    "escalation_available": true
  }
}
```

| Field | Values | Description |
| :--- | :--- | :--- |
| `action` | `ALLOW`, `WARN`, `DENY_DATA`, `ESCALATE`, `TERMINATE` | Recommended action for this turn |
| `violations` | array | Zero or more violations, each with `rule_id`, `severity`, `detail` |
| `session_state` | object | Echo of the session state — store this and send it on the next turn |

---

## Multi-Turn Example

The following shows a 4-turn session where IDG-01 fires on turn 3 (PHI requested before disclosure).

**Turn 1 — Greeting (no violation)**

```bash
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/webhooks/call-progress \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-001", "turn_index": 0, "speaker": "agent",
    "text": "Hello, this is Beacon. I am an AI assistant calling on behalf of Lakeside Medical.",
    "session_state": {"turn_count": 0, "disclosure_timestamp": null, "escalation_available": true}
  }'
# → action: ALLOW, disclosure_timestamp set to current time
```

**Turn 2 — Caller responds (no violation)**

```bash
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/webhooks/call-progress \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-001", "turn_index": 1, "speaker": "caller",
    "text": "Yes, go ahead.",
    "session_state": {"turn_count": 1, "disclosure_timestamp": 1718000000.0, "escalation_available": true}
  }'
# → action: ALLOW
```

**Turn 3 — PHI request before disclosure (if no disclosure yet)**

```bash
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/webhooks/call-progress \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-002", "turn_index": 2, "speaker": "agent",
    "text": "What is the member ID on file?",
    "session_state": {"turn_count": 2, "disclosure_timestamp": null, "escalation_available": true}
  }'
# → action: DENY_DATA, IDG-01 + PDX-01 violations
```

---

## VAPI Integration

In VAPI, configure a server URL hook to fire on every conversation turn:

```json
{
  "server": {
    "url": "https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/webhooks/call-progress",
    "timeoutSeconds": 1
  }
}
```

Map VAPI turn fields to the NHID-Clinical format:

```python
# adapters/call_progress_adapter.py handles this mapping automatically
from adapters.call_progress_adapter import to_nhid_turn

nhid_payload = to_nhid_turn(vapi_turn_payload)
```

---

## Twilio Integration

Twilio Voice fires a status callback on each utterance completion when using Gather + partial results. Map the Twilio format:

```python
nhid_payload = {
    "session_id":    call_sid,
    "turn_index":    utterance_index,
    "speaker":       "agent" if direction == "outbound" else "caller",
    "text":          speech_result,
    "session_state": session_state_dict,   # your app maintains this
}
```

---

## Related

- `adapters/call_progress_adapter.py` — webhook payload → `(session, event)` mapping  
- `functions/handler.py` — `/v1/webhooks/call-progress` route  
- `tests/test_call_progress_webhook.py` — 8 test cases  
- `docs/5-minute-quickstart.md` — Step 4 shows how to wire the webhook in VAPI
