# Ida on ElevenLabs — setup for the demonstration line

This is infrastructure for the **website demonstration** in the shadow-evaluation
guide (`shadow-evaluation-guide.html#demo`), not part of the NHID-Clinical
governance framework. It is a demonstration of the NHID controls on a live call,
with a fictional practice and a fictional patient. It is not a certification of
the agent, and nothing here establishes that any production call is governed.

## What happens on a call

Ida is an ElevenLabs agent that **places** a call to a payer's provider line on
behalf of an unnamed, fictional dental practice and asks for a
claim status. That is the canonical scenario (`docs/canonical-threat-model.md`):
the agent is the caller, the person who answers plays the payer's representative,
and the patient is not on the call.

1. **The disclosure is the first message**, configured in ElevenLabs and spoken
   word for word, so it does not depend on the model remembering it.
2. **Mid-call, before any patient identifier**, the agent's prompt tells it to call
   the `nhid_gate` webhook tool, which is `POST /v1/ida/gate`. That route is
   Ida's signer: it gets her per-call delegation from the fictional practice,
   answers the payer gate's challenge with her key, and presents both, with the
   sentence, to `POST /v1/gate/turn`. The payer side checks the passport in
   DLG-01 against its own trust anchors, and the engine answers
   `allowed: true` or `false` for the sentence. A timeout counts as "no". How
   the proof works, and what it does and does not establish:
   [`reference-agent.md`](reference-agent.md).
3. **After the call**, ElevenLabs posts the transcript to
   `POST /v1/webhooks/elevenlabs/postcall`. The handler verifies the HMAC
   signature, evaluates every turn with the NHID-Clinical engine, and writes the
   result to the demo status store, which the guide's panel reads.
4. **ElevenLabs' own grades** (the agent's evaluation criteria and data
   collection) are stored beside the engine's result and labelled "vendor
   self-evaluation (ElevenLabs), not NHID evidence". The engine never reads them.

The prompt is an instruction to the model, not a guarantee. Step 3 is what shows
whether the call followed it.

## Setup

Three parts, in this order, because the first produces the values the deploy needs.

### Part A — ElevenLabs

1. **Agents → Create agent → Blank**, named `Ida`.
2. **First message** and **System prompt**: copy them from
   `agents/ida_system_prompt.md` (the `first_message` and `prompt` blocks).
   That file is the source of truth; `scripts/sync_agent_config.py --agent ida`
   pushes it to the agent once the agent ID is in the environment.
3. **Analysis → Evaluation criteria**: one per control (IDG-01, PDX-01, DBC-01,
   EIT-01), in plain words. **Data collection**: `disclosure_heard`,
   `human_requested`, `transfer_completed` (booleans). These become the vendor
   column on the site.
4. **Tools → System tools**: End call, and Transfer to number pointed at a phone
   you control (not a personal number).
5. **Settings → Webhooks → Post-call webhook**:
   `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod/v1/webhooks/elevenlabs/postcall`,
   with **HMAC authentication** on. Copy the secret when it is shown; it is not
   shown again.
6. **Phone Numbers → Import from Twilio**: the Twilio Account SID and Auth Token,
   then pick the number and assign Ida to it.

Three values come out of this: the agent ID, the webhook secret, and the phone
number ID. Put them in your shell as environment variables, never in a file, a
commit, or a chat message:

```
ELEVENLABS_AGENT_ID
ELEVENLABS_WEBHOOK_SECRET
ELEVENLABS_PHONE_NUMBER_ID
```

`ELEVENLABS_API_KEY` is the fourth, for placing outbound calls.

### Part B — deploy

macOS/Linux (`make` reads environment variables, and the `sam deploy` line is not
echoed, so the values stay off the screen):

```
make deploy
```

Windows PowerShell (the four ElevenLabs parameters default to the same
environment variables):

```
.\scripts\deploy.ps1 -CloudflareTurnstileSecret $env:CLOUDFLARE_TURNSTILE_SECRET
```

Each value maps to a `NoEcho` parameter in `template.yaml` and from there to the
Lambda environment:

| Environment variable | Template parameter | Unset means |
| :-- | :-- | :-- |
| `ELEVENLABS_API_KEY` | `ElevenLabsApiKey` | `/v1/demo/call` answers 503 |
| `ELEVENLABS_PHONE_NUMBER_ID` | `ElevenLabsPhoneNumberId` | `/v1/demo/call` answers 503 |
| `ELEVENLABS_AGENT_ID` | `ElevenLabsAgentId` | `/v1/demo/call` answers 503 |
| `ELEVENLABS_WEBHOOK_SECRET` | `ElevenLabsWebhookSecret` | every post-call request is refused (401) |
| `NHID_TRUST_ANCHORS` | `NhidTrustAnchors` | a presented passport is answered 503, never passed |
| `IDA_AGENT_KEY_B64` | `IdaAgentKeyB64` | `/v1/ida/gate` answers 503 |
| `IDA_PRACTICE_KEY_B64` | `IdaPracticeKeyB64` | `/v1/ida/gate` answers 503 |

The last three come from `python scripts/ida_demo_credentials.py`, which mints
demonstration keys for a fictional practice and prints them as `KEY=value`
lines. Put them in the shell or the secret store, never in a file or a commit.
`python scripts/ida_demo_credentials.py --selftest` runs one gated turn
in-process with fresh keys.

`/v1/demo/call` checks its configuration before the CAPTCHA or the rate limiter,
so an unconfigured service costs nothing and makes no network call.

### Part C — the gate tool (after the deploy)

**Tools → Add tool → Webhook**:

| Field | Value |
| :-- | :-- |
| Name | `nhid_gate` |
| Method | `POST` |
| URL | `https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod/v1/ida/gate` |
| Timeout | 5 seconds (a slow or failed check counts as "no") |
| `session_id` | dynamic variable `system__conversation_id` |
| `turn` (string, required) | the exact sentence the agent is about to say |
| `heard` (string) | what the representative just said |
| `disclosed` (boolean, required) | true if the representative has heard and acknowledged that the caller is an AI |

The route takes the same keys as a query string or a JSON body, and `disclosed`
accepts a JSON boolean or the strings `true`/`false`.

## The post-call webhook

### Authentication

The `ElevenLabs-Signature` header is `t=<unix seconds>,v0=<hex>`. The signed
message is `<t>.<raw request body>` and the digest is HMAC-SHA256 with the webhook
secret. A timestamp older than 30 minutes is refused. That scheme and tolerance
are taken from the official `elevenlabs` Python SDK
(`webhooks_custom.WebhooksClient.construct_event`, v2.75.0), not inferred. The
comparison here is constant-time; the SDK's is not.

Missing header, bad signature, stale timestamp, or no secret configured: **401,
and nothing is written.** Before this, anyone could POST a fabricated call and
have it shown on the public site as the latest result.

### The envelope

```
{"type": "post_call_transcription", "event_timestamp": <unix>,
 "data": {"agent_id", "conversation_id", "transcript": [...],
          "metadata": {"start_time_unix_secs", "call_duration_secs", ...},
          "analysis": {"evaluation_criteria_results", "data_collection_results", ...}}}
```

Only `post_call_transcription` is evaluated. `post_call_audio`,
`call_initiation_failure` and any other type get `200 {"ignored": "<type>"}`, so
ElevenLabs does not retry them or disable the webhook. That holds for an audio
event larger than the 2 MB parse cap too: its type is read from the start of the
signed body and it is acknowledged without being parsed. Leaving "Send audio data"
off avoids sending them at all. The adapter
(`adapters/elevenlabs_postcall_adapter.py`) still reads the older flat shape.

### Timing

Every transcript message carries `time_in_call_secs`. Each turn is stamped
**call start + time_in_call_secs**, where call start is
`metadata.start_time_unix_secs`, or, when that is missing,
`event_timestamp − call_duration_secs`. The fallback is an estimate: ElevenLabs
sends the webhook after its post-call analysis, so it places the start no earlier
than the true one.

Impersonation Latency in seconds is the `time_in_call_secs` of the disclosure
turn: the offset from connect, which is the definition
(IL = t(disclosure) − t(connect)), and does not depend on the start estimate. The
turn form is the disclosure turn's position. An interrupted disclosure was not
heard and does not count. Missing timing is reported as **not recorded, never as
zero**.

The band shown beside it is `src/pilot_measure.classify_disclosure_band`, which is
reporting only and never gates a decision:

| Band | Meaning |
| :-- | :-- |
| `pass` | disclosed on the first turn, before any data request |
| `delayed` | disclosed within 10 s, before any patient data |
| `late` | disclosed after 10 s, before any patient data |
| `critical` | patient data before disclosure, or no disclosure |

There is one seconds threshold in the specification (10 s,
`DISCLOSURE_DELAY_SECONDS`). A finer split, such as a 10–15 s band, would be a
new threshold and needs a recorded decision before it is added.

### The calling agent's own words

The call-progress adapter was written for an agent that **receives** calls, so it
looked for patient identifiers only in what the human said. Ida is the caller:
it is the one that says the member ID. The post-call handler gives agent turns the
same orientation `/v1/gate/turn` does, so Ida speaking an identifier before the
disclosure is a PDX-01 finding.

## Checking a deploy

```
B=https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod
curl -sS "$B/health"
curl -sS -X POST "$B/v1/gate/turn" -H 'Content-Type: application/json' \
  -d '{"session_id":"check-1","turn":"The member ID is RVD-204-7731.","disclosed":false}'
#   expect "action": "DENY_DATA", "allowed": false
curl -sS -X POST "$B/v1/gate/turn" -H 'Content-Type: application/json' \
  -d '{"session_id":"check-1","turn":"The member ID is RVD-204-7731.","disclosed":true}'
#   expect "allowed": true
curl -sS -X POST "$B/v1/ida/gate" -H 'Content-Type: application/json' \
  -d '{"session_id":"check-2","turn":"The member ID is RVD-204-7731 and the claim number is 9921-0417.","disclosed":true}'
#   expect "allowed": true, "delegation_checked": true
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$B/v1/webhooks/elevenlabs/postcall" \
  -H 'Content-Type: application/json' -d '{}'
#   expect 401
```

## What this does not establish

- That Ida follows its prompt. The post-call evaluation is what checks it.
- That ElevenLabs' grades are right. They are the vendor grading its own agent,
  shown for comparison.
- Anything about a real patient or a real payer. All data is fictional.
- Identity or authority in the real world. Through `/v1/ida/gate` the gate
  checks a passport signed by a fictional practice whose demonstration key the
  same deployment holds. That shows the mechanism end to end; it does not show
  that any real organisation authorised Ida (`docs/reference-agent.md`,
  `docs/canonical-threat-model.md`).
