# Chapter 8 — Operational Architecture

*Part II: The Framework*

---

## The Whiteboard Question

An enterprise architect at a regional payer has been handed Chapters 5
through 7 and a marker. Her security lead, her telephony manager, and a
skeptical platform engineer are looking at a whiteboard on which she has
drawn exactly one thing: a phone.

"Show me where this actually runs."

It is the correct first question, and it has a precise answer — more
precise than most governance frameworks can give, because this one ships
its components as code. By the end of the session her whiteboard holds:
the existing call path (carrier, telephony platform, agent or
representative) drawn unchanged; a conformance evaluation service that
receives call events and returns verdicts; two insertion points for it —
during the call, turn by turn, or at call end; an event schema flowing into
an audit store; and, dotted, an identity-verification path for the
cryptographic layer. Nothing on the board replaced anything that was there
before. Everything new consumed records the call path already produces.

That whiteboard is this chapter.

---

## Executive Summary

NHID-Clinical's runtime architecture is small by design: a deterministic
policy engine evaluating machine-readable call events against versioned
rules, fronted by a conformance API, fed by vendor-platform adapters, and
draining into healthcare-native audit output. The five-layer trust stack
places it among existing infrastructure: carrier number authentication
(STIR/SHAKEN, RFC 8224) below as Layer 1 — assumed, not replaced; the
behavioral baseline as Layer 2; the NHID-Auth cryptographic layer as Layer
3; FHIR R4 AuditEvent as Layer 4; OpenTelemetry export as Layer 5. Layer 0
is the NPI gap the stack exists to span.

The chapter walks the architecture in the order data flows: the **event
schema** (the per-turn trace contract every component reads and writes, with
its nested healthcare-governance block); the **policy engine** (a five-state
machine — INIT, DISCLOSURE, ROUTE, ESCALATE, BLOCKED — whose transitions
enforce the controls structurally: nothing routes before disclosure clears,
escalation preempts everything, failure states fail closed); the
**adapters** (native payload translation for VAPI, Twilio, Vonage, Retell,
and Amazon Connect, so conformance checking meets platforms where they
are); the **API surface** (demo, adapter, turn-by-turn webhook, CTS, and
authenticated production routes); and the **audit spine** (event store, FHIR
emitter, OpenTelemetry).

Two integration topologies cover practice: **post-call evaluation** (an
end-of-call webhook forwards the platform's payload; verdict and CAS are
stored — monitoring-grade, two hours of work) and **in-call evaluation**
(the turn-by-turn webhook route, where verdicts can shape the live call —
enforcement-grade, Chapter 10's subject). Both run against the hosted
reference API or a self-hosted engine; determinism makes the two
deployment choices verdict-identical.

## Why It Matters

Governance that cannot state its runtime footprint gets vetoed by
platform teams — reasonably. This chapter exists so the architect can
answer the three veto questions concretely. *What does it touch?* Call
event data the telephony platform already emits; no model access, no audio
pipeline changes, no new carrier relationships. *What can it break?* In
post-call topology, nothing on the call path — it is a consumer of
webhooks; in in-call topology, exactly what you wire it to influence, which
is a policy choice made in Chapter 10, not an architectural inevitability.
*What does it cost to try?* The reference API's demo routes take a
transcript and `curl`.

The architecture also matters for what it refuses to centralize. The
framework does not stand between organizations and their calls, does not
require a shared broker, and does not demand real-time dependence on
anyone's hosted service — self-hosting the engine yields identical
verdicts by the determinism property. For risk-averse healthcare
infrastructure teams, "adoptable without new critical-path dependencies"
is the difference between a pilot this quarter and a steering-committee
graveyard.

## The Event Schema: the Contract Everything Reads

Every component in the architecture communicates through one artifact: the
per-turn call event, defined by a published JSON Schema. A turn's event
carries the input payload (speech text and call metadata) and the nested
**healthcare-governance block** — disclosure timestamp, identity assertion
text, per-turn PHI flags, deceptive-artifact flags — plus session-level
facts like escalation path availability and call-SID binding.

Three properties of the schema do architectural work. It is **per-turn**,
because the controls are positional — IDG-01 and PDX-01 are claims about
*order*, and order lives at turn granularity. The governance block is
**nested deliberately** — the engine reads the nested structure, and flat
fields are ignored, which is why the pilot kit ships an explicit mapping
layer from its deliberately flat capture schema (easy to fill from logs)
into the engine contract, with rules like the *sticky* disclosure
timestamp: once set, carried forward to every later turn, because
disclosure is a state, not an event that expires. And it is
**vendor-neutral** — the schema is the normalization target the adapters
translate into, which is what keeps the engine at one implementation
rather than five.

The session's call-SID binding is the schema's quiet load-bearing member:
it ties turns into calls, calls into audit envelopes, and — at Layer 3 —
delegations into specific calls. The canonical failure trace for a missing
call-SID exists because without the binding, every downstream layer's
claims detach from the call they describe.

## The Policy Engine: a State Machine, Not a Judgment

The reference engine is compact enough to read in one sitting, and its
architecture *is* its policy. A session moves through five states — INIT,
DISCLOSURE, ROUTE, ESCALATE, BLOCKED — and every turn's evaluation returns
one action from a closed set (DISCLOSE, ESCALATE, BLOCK, ROUTE_LLM, ERROR)
with its reason code and policy version.

The transitions encode the controls structurally rather than as
after-the-fact checks:

- **An undisclosed session can do exactly one thing: disclose.** Until the
  disclosure state clears, evaluation returns the DISCLOSE action
  (`DISCLOSURE_GATE`) — task content cannot route. IDG-01/PDX-01 are not
  policies the engine *checks*; they are paths the state machine *lacks*.
- **Escalation preempts.** Any turn containing an escalation keyword
  ("human," "representative," "supervisor"...) routes to ESCALATE
  (`HUMAN_ESCALATION`) from any active state — EIT-01 as a transition that
  outranks task completion.
- **Failure fails closed.** Empty input blocks (`MISSING_INPUT`); a blocked
  session stays blocked (`SESSION_BLOCKED`); an unrecognized state is an
  error to BLOCKED (`INVALID_SESSION_STATE`), never a fall-through to task
  handling. The safety default is silence, not improvisation.
- **Only a disclosed, validly-stated session reaches ROUTE_LLM** — the
  action that hands the turn to whatever conversational intelligence the
  deployment uses. The governance layer wraps the model; it never consults
  it.

That last line is the architecture's deepest decision, stated in Chapter 7
as philosophy and visible here as topology: the LLM sits *behind* the
policy engine as a routed destination, never beside it as a co-decider.
Disclosure, escalation, and blocking are decided by rules the model cannot
override, weight, or phrase its way around.

## Adapters and the API Surface

The adapters answer the question every vendor integration begins with:
"in whose format?" Native payloads from VAPI, Twilio, Vonage, Retell, and
Amazon Connect are accepted on per-platform routes
(`/v1/adapters/{platform}/check`) and translated into the event schema —
no format conversion demanded of the integrator. The route inventory maps
cleanly onto adoption stages: open **demo and adapter routes** (no key) for
evaluation and vendor self-checks; the **turn-by-turn webhook**
(`/v1/webhooks/call-progress`) for in-call evaluation; the **CTS route**
for running the conformance suite; an **authenticated production route**
for real conformance checking; and public **CAS badge** rendering for
vendors who choose visibility (Chapter 18's subject).

Hosted versus self-hosted is a deployment decision, not a trust decision:
the engine is public reference code, and determinism guarantees the same
inputs score identically in either topology. Organizations with data-
residency constraints run the engine inside their boundary and lose
nothing but the convenience of someone else's uptime.

## The Audit Spine and the Stack Above

Every evaluation drains into the audit path: the event store retains the
per-turn record; the FHIR emitter renders conformance milestones as an R4
AuditEvent bundle — session start, identity disclosure, authorization
verification, and the rest of Chapter 12's milestone inventory — so results
land in systems healthcare audit teams already operate; OpenTelemetry
export (Layer 5) carries the same facts into enterprise observability,
where SRE dashboards and alerting live. One evaluation, three renderings:
operational (JSON verdict), compliance-native (FHIR), observability-native
(OTel). The architecture's bet is that governance data no one can see in
their existing tools is governance data no one uses.

Below everything, Layer 1: STIR/SHAKEN is assumed as pre-existing carrier
infrastructure — the framework's scope begins where number authentication
ends, and its own specification marks carrier integration as planned
future work, not a present dependency. The stack composes with telephony
reality; it does not re-litigate it.

## Real-World Examples

**The two-hour integration.** A platform engineer wires the post-call
topology exactly as the integration guide sketches: the voice platform's
end-of-call webhook forwards its native payload to the matching adapter
route; the response's CAS score and conformance flag are stored beside the
call record; an alert fires on non-conformance. No call-path change, no
new failure mode on live traffic — if the conformance service is down,
calls proceed and evaluation backfills. This is the topology every
organization should run first, and for monitoring purposes, possibly
forever.

**The self-hosting decision.** A payer's security review balks at posting
call events, even de-identified, to an external API. Resolution: clone the
reference implementation, run the engine internally, verify parity by
replaying the CTS suite and comparing verdicts byte-for-byte with the
hosted API's. Determinism converts "do we trust their service?" into "do
these two deployments agree?" — a checkable question. The review closes.

**The state machine explains an incident.** A vendor disputes a BLOCK on a
live pilot call, claiming the agent "was about to disclose." The trace
shows turn one: empty speech payload (a platform hiccup), action BLOCK,
reason `MISSING_INPUT`; turn two arrived on a blocked session
(`SESSION_BLOCKED`). The dispute dissolves into an infrastructure fix —
retry empty-payload turns — and both sides learned the fail-closed
behavior from the reason codes alone. No meeting required.

## Diagrams to Include

1. **Figure 8-1 — The reference architecture.** The whiteboard, formalized:
   call path unchanged across the top (carrier → telephony platform →
   agent/representative); conformance service beside it with the two
   insertion points (turn-by-turn, end-of-call); event schema as the
   labeled contract on every arrow; audit spine (event store → FHIR → OTel)
   draining down; NHID-Auth verification dotted at call setup. The book's
   master technical figure — every later implementation chapter references
   it.
2. **Figure 8-2 — The engine state machine.** Five states, transitions
   labeled with actions and reason codes, fail-closed edges visually
   distinct (heavy, terminating in BLOCKED). Drawn from the reference
   engine, not idealized.
3. **Figure 8-3 — Two topologies.** Post-call and in-call side by side,
   annotated with grade (monitoring vs. enforcement), effort (hours vs.
   project), and blast radius (none vs. policy-defined). The figure that
   lets an architect choose in one glance.
4. **Figure 8-4 — The trust stack as deployment.** The five layers redrawn
   with *operators* attached: carriers (L1), your organization or vendor
   (L2–3), your audit systems (L4), your observability stack (L5). The
   stack as org chart, resolving who runs what.

## Operational Guidance

- **Start post-call, everywhere, always.** The monitoring topology carries
  no call-path risk and produces every metric Part III needs. In-call
  enforcement is a *later* policy decision (Chapter 10) that should be made
  while already holding months of post-call data.
- **Treat the event schema as the procurement artifact.** When asking
  vendors "can you support this?", the precise question is: can your
  platform emit, per turn, the governance-block fields? The schema is a
  one-page technical exhibit; platform answers to it are checkable.
- **Put the reason codes in your runbooks.** The closed vocabulary
  (`DISCLOSURE_GATE`, `HUMAN_ESCALATION`, `MISSING_INPUT`...) is the
  operational language of every incident this system will ever surface.
  Ops teams who learn five reason codes can triage without escalating to
  whoever owns the framework relationship.
- **Decide hosted-vs-self-hosted on operations, not trust.** Determinism
  makes verdict parity checkable; the real decision inputs are data
  residency, uptime ownership, and patching. Write the decision down
  either way — Chapter 17 will want it.

## Implementation Guidance

1. **Prove parity before relying on either deployment.** Whichever
   topology you choose, replay the 18-case CTS suite through it and
   archive the verdicts as your baseline. This is an afternoon, and it
   converts "the framework says" into "our deployment demonstrates" for
   every conversation that follows.
2. **Wire the audit spine before the dashboard.** The temptation is to
   ship the CAS dashboard first — visible, demo-friendly. Resist: the FHIR
   and event-store paths are what make every number on that dashboard
   reconstructible later, and retrofitting audit under a live dashboard is
   how numbers end up unexplainable. Spine first, glass second.

## Key Takeaways

- The architecture is deliberately small: one event schema as universal
  contract, one deterministic state-machine engine, adapters for the five
  major voice platforms, an API surface graded from open demo routes to
  authenticated production checks, and an audit spine rendering every
  evaluation three ways (JSON, FHIR, OpenTelemetry).
- The controls are enforced structurally: an undisclosed session has no
  path to task handling, escalation preempts every state, and all failure
  modes terminate in BLOCKED. The LLM sits behind the policy engine as a
  routed destination — governance wraps the model and never consults it.
- Two topologies cover adoption: post-call (monitoring-grade, hours of
  work, zero call-path risk — start here) and in-call (enforcement-grade,
  a policy decision before an engineering one).
- Nothing is replaced and nothing new is centralized: STIR/SHAKEN is
  assumed below, existing audit and observability systems receive above,
  and self-hosting yields identical verdicts by determinism.
- The stack's each layer has an operator, and naming them (carrier, your
  org, your audit team, your SREs) is how architecture review actually
  closes.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Event schema, governance block, sticky disclosure | The contract | Chapters 9, 12 |
| Call-SID binding (trace 03) | The contract | Chapters 11–12 |
| Engine states, actions, reason codes | The state machine | Chapter 10 |
| Adapters (VAPI, Twilio, Vonage, Retell, Connect) | Adapters and API | Chapter 13 |
| Turn-by-turn webhook vs. end-of-call routes | Topologies | Chapters 10, 13 |
| FHIR AuditEvent emitter, OpenTelemetry | Audit spine | Chapter 12 |
| STIR/SHAKEN as Layer 1, integration as future work | The stack | Chapter 19 |
| CTS replay for deployment parity | Implementation guidance | Chapters 9–10 |

---

*Part II complete. Next — Part III opens with Chapter 9, Shadow
Evaluations: the observe-only pilot that turns everything defined so far
into measurements of your own traffic, in two to four weeks, without
changing a single live call.*
