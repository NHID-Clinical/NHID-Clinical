# Grok Realtime bridge — the gate between a voice model and its actions

*Reference implementation, 2026-10-25. Not deployed anywhere. Not a product, not a
certification, not evidence that any call has been governed.*

## The one fact that shapes the design

xAI's Realtime API delivers a tool call the model makes **during** a spoken response
*after* the audio for that response (docs.x.ai, *Avoid Audio Overlap During Tool
Calls*: "the server delivers all audio deltas first, then the function call events
alongside `response.done`"). A tool the model is told to call "before asking for
data" therefore cannot stop the model from asking; by the time the call arrives, the
words are out.

So the bridge does not try to gate speech with a tool. It:

1. **speaks the disclosure itself**, with `force_message` and `interruptible: false`,
   before the model says a word;
2. **gates every tool call** (data lookups, transfer, end-call) through
   `functions.handler.gate_turn` before executing it, and executes nothing the gate
   denies;
3. **checks speech after the fact**: a completed model turn is run through the gate
   and recorded. A DENY there is a finding and a corrective disclosure, never a
   prevention. The doc says so, and so does the audit row (`spoken_after_the_fact`).

The prompt is advisory. Enforcement lives in the relay loop, and the model is never
trusted about whether disclosure happened: that flag is set only when the bridge
observes the disclosure's own spoken turn complete without the representative
talking over it.

## Orientation

The canonical scenario (`docs/canonical-threat-model.md`): the Grok agent is the
**caller**, acting for a provider; the party on the line is the payer's
representative. The caller transcript is what the representative said; the agent's
planned utterance or tool call is what the gate judges. An agent that *answers*
inbound calls as the payer would reverse the roles and is out of scope for this
bridge.

## What runs where

| Piece | File | Role |
| :-- | :-- | :-- |
| Gate | `functions/handler.py` `gate_turn(params)` | The route's whole logic as a pure function, so the bridge runs exactly what `POST /v1/gate/turn` runs, in process, no HTTP. New optional inputs: `actor_id`, `escalation_outcome`. New output: `evidence_hash`. |
| Adapter | `adapters/grok_realtime_adapter.py` | Pure. Remembers the call (`GrokCallState`), parses `response.function_call_arguments.done`, builds gate parameters and outbound items (`force_message`, `function_call_output`, `session.update`). No detection. |
| Bridge | `src/grok_realtime_bridge.py` | The relay loop, enforcement, fail-closed rule, audit JSONL, and a runner. Transport and call control are injected; tests use fakes. |
| Probe | `scripts/grok_realtime_probe.mjs` | Observer only. Plays the representative against a console-published agent and prints transcript and tool calls. Enforces nothing. |
| Tests | `tests/test_grok_realtime_bridge.py`, `tests/fixtures/grok_realtime/` | Synthetic event streams replayed through the bridge. |

## Decisions and what the bridge does with them

| Gate action | Bridge |
| :-- | :-- |
| `DENY_DATA` | tool blocked; `function_call_output {status: blocked, …}`; bridge speaks `say_instead` |
| `DISCLOSE_IDENTITY` | tool blocked; bridge speaks the disclosure |
| `ESCALATE_HUMAN` | tool blocked; **the bridge** calls `refer`; outcome recorded as `honored` / `not_honored` and carried on the next gate call so EIT-01 sees it. A failed transfer ends the call after one gate call records `EIT01_ESCALATION_NOT_HONORED`. |
| `CONTINUE_AI` / `LOG_ONLY` | tool executed if the deployment registered an executor; result returned; `response.create` |
| gate raised, timed out (300 ms), non-200, empty body, unknown action | treated as `DENY_DATA`, reason `GATE_UNAVAILABLE` (a bridge code, not an engine code); three in a row end the call |

Fail-closed rule, stated once: proceed only if the gate returned HTTP 200, `action`
in {`CONTINUE_AI`, `LOG_ONLY`} and `allowed` is true. Anything else is a deny.

## What changed in the shared code, and why

`adapters/call_progress_adapter.py` now sets `actor_id`, `replay_mode: "live"` and
`external_calls_cached: false`. These are three of the fields ATR-01 requires. Without
them every turn through the webhook and the gate came back `LOG_ONLY /
ATR01_AUDIT_FIELDS_MISSING`, and the engine never built a signed audit trail for a live
call. With them a clean post-disclosure turn is `CONTINUE_AI / ATR01_AUDIT_COMPLETE`
and the gate returns the trail's `evidence_hash`. No test asserted the old reason code
on these routes; the change is visible in the gate's response and nowhere else.

## Audit

One JSON line per decision in `logs/grok_bridge_audit.jsonl` (gitignored):
`timestamp, session_id, actor_id, turn_index, event_type, tool, intent, disclosed,
action, reason_code, violations[], policy_version, evidence_hash, gate_status,
gate_failed, latency_ms, enforcement`. No transcript text. PHI appears as the engine's
field names only. `evidence_hash` is the engine's HMAC over the ATR-01 record; it is
recomputable across restarts only when `AUDIT_SECRET_KEY_B64` is set, otherwise the
engine signs with a per-process key.

## Running it

```bash
pip install websockets                      # deliberately not in requirements.txt
export XAI_API_KEY=...                      # read from the environment, never printed
python -m src.grok_realtime_bridge --agent-id agent_...      # a console-published agent
python -m src.grok_realtime_bridge --call-id <sip call id>   # a SIP leg (see unverified)
```

```bash
npm install ws
XAI_API_KEY=... node scripts/grok_realtime_probe.mjs agent_... "Claims department, how can I help?"
```

The runner is a transcript-and-tools client. It drops audio frames; it is for proving
the gate, not for carrying a call's media.

## Unverified, as of 2026-10-25

- The `?agent_id=` connection form comes from the console's example, not the public
  docs. The protocol on the socket is the documented one.
- Whether a console-published agent's **built-in** `transfer_call` / `end_call` surface
  to a WebSocket client as `response.function_call_arguments.done`. If they execute
  inside xAI, no client code can block them; the bridge then needs those tools declared
  as its own function tools in `session.update` instead.
- The SIP call-control routes (`/v1/realtime/calls/{id}/refer`, `/hangup`) and the
  `realtime.call.incoming` webhook. `HttpCallControl` implements the URL shape and
  treats any failure as `not_honored`. The webhook receiver is not written.
- Whether output audio can be held until the transcript is gated, and at what latency.

## Open for the maintainer

1. Caller or answerer: this bridge assumes the agent **places** the call.
2. The console's "NHID-Clinical connector": what it targets and how it authenticates.
3. Whether the number is xAI-hosted or a SIP trunk with a webhook you control.
4. DLG-01: opt-in and not wired here. Requiring a passport means verifying it via
   `/v2/identity/verify-passport` with the SIP call id and passing a `DelegationContext`.
5. `evaluate_all` also runs the supplemental bot-to-bot rule, which can return
   `DENY_DATA` when `counterparty_type` is `ai_agent`. The gate sets `human_operator`,
   so it is inert here. Whether the rule should exist beside "exactly five controls" is
   a maintainer question, not a bridge one.
6. `POST /v1/gate/turn` is open (no API key). In-process use needs none; a networked
   bridge should have one.
7. `AUDIT_SECRET_KEY_B64` in the deployment, so evidence hashes verify across restarts.
8. Retention and redaction for `identity_assertion_text` in the DBC-01 review queue and
   the event store's text columns; raw utterances may contain PHI. Unchanged here.
