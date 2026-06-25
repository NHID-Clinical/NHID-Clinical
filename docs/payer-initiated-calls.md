# Payer-Initiated Calls — Policy Extension Guide (v1.3 final)

NHID-Clinical's controls (IDG-01, PDX-01, DBC-01, EIT-01, ATR-01) were specified
and tested against one call direction: a **provider's** AI voice agent calling
**outbound to a payer** (the shape Beacon — the reference implementation —
demonstrates). This document extends the same controls to the reverse direction:
a **payer's** AI voice agent calling **outbound to a provider** — e.g. to
request additional documentation, confirm eligibility, or follow up on a prior
authorization. It is a policy-extension guide, not new code; nothing here
changes the policy engine, the event schema, or the conformance test suite.

## Why this needed writing down

`traces/nhid-trace-08-bot-to-bot-no-gate.md` documents the gap this guide closes:
NHID-Clinical v1.3's controls were written assuming the counterparty answering
the call is a human. When a payer deploys its own AI agent to call a provider's
office, and that office *also* answers with an AI agent, IDG-01 as specified
only describes one direction of disclosure — it does not say what the payer's
agent itself must do when it is the caller, nor what either side must do when
both parties are AI.

## The four controls, payer-initiated

**IDG-01 — Identity Disclosure Gate.** Applies identically regardless of which
side initiates. The payer's agent must disclose, in its first substantive
sentence, that it is an automated, non-human AI system — before requesting or
referencing any PHI. If the provider's office answers with its own AI agent
(bot-to-bot), the payer's agent must complete IDG-01 disclosure to whichever
party answers, AI or human, with no exception for AI-to-AI calls. Failing to
disclose to an AI counterparty under the theory that "no human was on the line"
is the **Impersonation Latency** failure mode, not an exemption from it.

**PDX-01 — Pre-Data Exchange Gate.** Unchanged in substance: the payer's agent
must not request or accept PHI (member ID, date of birth, diagnosis codes, prior
auth numbers) until IDG-01 disclosure is confirmed by the counterparty —
confirmed, not merely sent. If the called party is itself an undisclosed AI
agent, PDX-01 blocks data exchange until that counterparty's identity is
established, per the `BOT2BOT_UNDISCLOSED_AGENT` policy decision in the trace
above.

**DBC-01 — Deceptive Behavior Check.** Unchanged: no synthetic human-presence
artifacts, no implied licensure, never deny being an AI when asked — applies to
the payer's agent exactly as it applies to a provider's agent.

**EIT-01 — Escalation Implementation Test.** When the provider's office (human
or AI) requests a human, the payer's agent must acknowledge immediately and
either execute a real transfer or say plainly that none is configured and offer
an alternative contact path — the same rule Beacon implements for inbound
escalation requests, applied symmetrically to outbound calls.

## Bot-to-bot identity verification (the open gap)

NHID-Clinical v1.3 does not fully specify how two AI agents (a payer's outbound
agent and a provider's office's inbound or outbound agent) should verify each
other's identity beyond IDG-01 spoken disclosure. NHID-Auth v2
(`src/agent_identity.py`) already provides the building block — an Ed25519
agent passport with NPI binding and delegation-chain scope — but it is
currently used as a one-way disclosure ("Beacon discloses its own credential
when asked"), not as a mutual, machine-verifiable handshake between two
deployed agents before either exchanges PHI. Closing that gap fully is out of
scope for this pass; the recommended next step is to extend the
`POST /v1/identity/verify-passport` route (see
[v2-integration-guide.md](v2-integration-guide.md)) to a mutual exchange where
both sides present a passport before PDX-01 clears, rather than just answering
"who are you" when asked.

## Implementation note for payers building an outbound agent

If you are building or evaluating a payer-side outbound AI voice agent against
NHID-Clinical, run it through the existing conformance test suite exactly as a
provider-side agent would (`/v1/conformance/check` or the matching vendor
adapter route) — the suite does not currently take call direction as an input,
because the four controls above apply the same way regardless of who placed
the call. There is no separate "outbound" CTS profile to opt into; pass the
same transcript format as documented in the
[5-minute quickstart](5-minute-quickstart.md).
