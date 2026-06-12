# NHID-Clinical — 5-Minute Vendor Quickstart

Zero install. Zero signup. Working conformance result in under a minute, full integration in 5.

The API is hosted — **you POST to it; there is nothing to subscribe to, buy, or host**.

## Step 1 — One curl, instant result (30 seconds)

```bash
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/adapters/vapi/check \
  -H "Content-Type: application/json" \
  -d @tests/demo_scenarios/vapi_noncompliant.json | python3 -m json.tool
```

You get back the conformance verdict, the violated controls, and a CAS score:

```json
{
  "conformant": false,
  "action": "DENY_DATA",
  "violations": [
    { "rule_id": "IDG-01", "severity": "critical" },
    { "rule_id": "PDX-01", "severity": "critical" }
  ],
  "cas": { "score": 0.0, "tier": "Denied / Degraded", "badge_eligible": null }
}
```

## Step 2 — Send your own call (2 minutes)

Replace the demo file with a real transcript from your platform. Native formats
are accepted directly — no conversion needed:

| Your platform | Endpoint |
| :--- | :--- |
| VAPI | `POST /v1/adapters/vapi/check` |
| Twilio | `POST /v1/adapters/twilio/check` |
| Vonage | `POST /v1/adapters/vonage/check` |
| Retell AI | `POST /v1/adapters/retell/check` |
| Amazon Connect | `POST /v1/adapters/connect/check` |
| Anything else | `POST /v1/demo/check` (raw NHID event) |

## Step 3 — Wire it into your call-completion webhook (2 minutes)

Point your platform's end-of-call webhook at the adapter route for your vendor.
Example for Retell: in the Retell dashboard, set the `call_analyzed` webhook URL to
your own backend, then forward the payload:

```python
import requests

def on_call_analyzed(retell_payload):
    result = requests.post(
        "https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/adapters/retell/check",
        json=retell_payload,
        timeout=10,
    ).json()
    if not result["conformant"]:
        alert_compliance_team(result["violations"])
    log_cas_score(result["cas"]["score"])
```

## Step 4 — Optional: turn-by-turn evaluation during the call

For near-real-time checks, POST each conversation turn to the call-progress webhook.
You maintain `session_state` between turns; the API is stateless:

```bash
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/webhooks/call-progress \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "call_001", "turn_index": 3,
    "speaker": "user", "text": "what is the member id?",
    "session_state": {"turn_count": 3, "disclosure_timestamp": null, "escalation_available": true}
  }'
```

## Step 5 — Production: add an API key

`POST /v1/conformance/check` with an `x-api-key` header gives you the production
rate-limit tier (50k req/month). Request a key at contact@nhid-clinical.org.

---

Next steps: [v2 staged integration guide](v2-integration-guide.md) ·
[Shadow pilot program](https://nhid-clinical.org/for-payers.html)

NHID-Clinical is a voluntary open proposal (CC BY 4.0). Not an accredited standard.
Not a regulatory requirement.
