# Twilio scripted inbound demo line — setup

This is infrastructure for the **website demo feature** (the scripted
compliant/non-compliant call you can dial in to from `demo.html`), not part
of the NHID-Clinical governance framework itself.

Provisioning the actual phone number is a manual step in the Twilio Console —
it is not managed by `template.yaml` / CloudFormation, because Twilio doesn't
expose phone number purchase via SAM/CFN resources.

## One-time setup

1. In the [Twilio Console](https://console.twilio.com/), buy a phone number
   (Phone Numbers → Buy a number). Voice capability is required; SMS is used
   only for the optional starter-pack-link feature (see "Starter-pack SMS"
   below), which is off unless Twilio messaging credentials are configured.
2. Deploy this repo's stack (`make deploy` on macOS/Linux, or `.\deploy.ps1` on
   Windows PowerShell) and note the API Gateway base URL from the `ApiBaseUrl`
   stack output (both print it at the end of a successful deploy).
3. On the purchased number's configuration page, under **Voice & Fax →
   A call comes in**, set:
   - Webhook: `https://<api-id>.execute-api.<region>.amazonaws.com/prod/v1/webhooks/twilio-demo/voice`
   - HTTP method: `POST`
4. Save. No Twilio Auth Token or API key needs to be stored in this repo or
   in `template.yaml` for this feature — the webhook endpoint has no
   authentication, matching the rest of the public demo routes
   (`/v1/demo/check`, etc.).
5. Update the phone number shown on `demo.html` (`#demo-phone-number`) to the
   number you purchased.

## How a call flows

1. Caller dials in → Twilio POSTs form-encoded `CallSid`/`Digits` fields to
   the webhook above.
2. `functions/twilio_demo_handler.py` plays a menu (press 1 for the
   compliant scenario, 2 for the non-compliant one), then advances one
   scripted turn per request, auto-redirecting itself via TwiML
   `<Redirect>` until the script (`functions/demo_scripts.py`) is exhausted.
   When a scenario finishes, instead of hanging up the caller hears an
   end-of-demo menu: press 1 to hear the other scenario (replayed under the
   same `CallSid` via `demo_status_store.reset_session`), or press 2 (or
   stay silent) to end the demo. When SMS is configured (see below), the menu
   also offers press 3 to text the caller a starter-pack link.

## Starter-pack SMS (optional)

The end-of-demo menu offers a "press 3 to get the starter pack link by text"
option **only when** Twilio messaging is configured. The IVR keypress is the
opt-in, and the link is texted to the caller's own number (`From`).

This requires:
- A Twilio number (or Messaging Service) registered for US A2P 10DLC messaging.
- Three deploy parameters: `TwilioAccountSid`, `TwilioAuthToken`, `TwilioSmsFrom`
  (plus optional `StarterPackUrl`, which defaults to the shadow-evaluation
  guide). Pass them via `make deploy` / `.\deploy.ps1`.

When any of the three are unset, the SMS option is simply not spoken, so the
demo line works unchanged before registration is complete. Sending lives in
`functions/twilio_sms.py` (`sms_enabled()` / `send_sms()`); the texted body
includes the carrier-required `STOP`/`HELP` and rate-disclosure language.
3. Every turn is evaluated through the same `adapters/call_progress_adapter.py`
   + `src/nhid_policy_engine_v1.py` pipeline production traffic uses — only
   the scripted speech is fake.
4. Each turn's decision is written to a DynamoDB table
   (`DemoCallStatusTable` in `template.yaml`) keyed by `CallSid`, with a
   1-hour TTL so sessions self-clean. It's also mirrored under a fixed key
   (`_latest_demo_call`) so anyone watching `demo.html` sees live status for
   whichever call is currently in progress, without needing to know their
   own `CallSid`.
5. `demo.html` polls `GET /v1/demo/call-status?session_id=latest` every ~2s
   and renders the live pass/fail state via `NHIDDemoStatus.render()` in
   `site.js`.

## Cost

Twilio voice minutes for inbound calls to the demo number. No AI/LLM usage —
the call content is fully scripted and deterministic, so there is no
per-call variance or ElevenLabs/LLM cost for this feature (unlike the Beacon
outbound demo).
