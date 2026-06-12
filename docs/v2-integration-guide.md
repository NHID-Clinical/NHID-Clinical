# NHID-Clinical — Staged Integration Guide (Tier 0 → Tier 2)

v2's cryptographic identity layer is powerful but it is **not the on-ramp**.
Integration is a ladder — each tier is independently useful, and you can stop
at any rung.

| Tier | Time | What you get | What you need |
| :--- | :--- | :--- | :--- |
| **0** | 15 min | Conformance verdict + CAS score per call | A transcript and `curl` |
| **1** | ~2 hr | Automated per-call checks in your pipeline | An end-of-call webhook |
| **2** | ~1 day | Cryptographic agent identity (NPI-bound) | `pip install cryptography` |

---

## Tier 0 — Paste a payload (15 minutes)

No keys, no code changes. POST any call transcript to the hosted API:

```bash
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/demo/check \
  -H "Content-Type: application/json" \
  -d @your_call_event.json | python3 -m json.tool
```

Native VAPI, Twilio, Vonage, Retell, and Amazon Connect payloads are accepted
on the `/v1/adapters/*/check` routes — no format conversion required.
See the [5-minute quickstart](5-minute-quickstart.md).

**Stop here if:** you just want to audit how your current agent behaves.

---

## Tier 1 — Wire into your call pipeline (~2 hours)

Add one HTTP call to your existing end-of-call handler:

1. Your voice platform fires its call-completed webhook (VAPI `end-of-call-report`,
   Retell `call_analyzed`, Twilio `StatusCallback`, …).
2. Your backend forwards the payload to the matching NHID adapter route.
3. You store `result["cas"]["score"]` and alert on `result["conformant"] == false`.

```python
import requests

NHID = "https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod"

def on_call_complete(vendor_payload):
    result = requests.post(f"{NHID}/v1/adapters/vapi/check",
                           json=vendor_payload, timeout=10).json()
    db.save_cas(call_id=vendor_payload["call"]["id"],
                score=result["cas"]["score"],
                conformant=result["conformant"])
```

Optionally add the turn-by-turn `/v1/webhooks/call-progress` route for in-call
checks (see quickstart Step 4).

**Stop here if:** you want continuous compliance monitoring without key management.

---

## Tier 2 — Cryptographic agent identity (~1 day)

v2 adds *authorization*: provider-signed agent credentials with NPI binding,
scoped delegation (max 3 hops), per-agent revocation, and call-SID nonce
binding. The whole flow is ~50 lines using `src/agent_identity.py`:

```python
from src.agent_identity import AgentIdentityManager

m = AgentIdentityManager()

# 1. Provider org generates its root keypair (one time; store private key in KMS/HSM)
provider_priv, provider_pub = m.generate_agent_keys()
agent_priv, agent_pub = m.generate_agent_keys()

# 2. Issue a scoped, NPI-bound delegation for the AI agent and sign it
delegation = m.create_delegation(
    provider_priv,
    agent_id="agent_beacon_001",
    agent_pub=agent_pub,
    scope=["claim_status_inquiry"],
    provider_npi="1234567890",
)
signature = m.sign_delegation(provider_priv, delegation)
passport = m.create_agent_passport(delegation, signature, agent_priv)

# 3. Payer side: verify the passport on every inbound call
result = m.verify_passport(passport, provider_pub)
assert result.valid
```

Run the working example end to end:

```bash
pip install cryptography
python examples/issue_and_verify.py
python -m pytest tests/test_identity.py -v   # 28 tests
```

The full concept reference (delegation chains, revocation, nonce binding) is at
[nhid-clinical.org/roadmap.html](https://nhid-clinical.org/roadmap.html).

---

NHID-Clinical is a voluntary open proposal (CC BY 4.0). Not an accredited
standard. Not a regulatory requirement.
