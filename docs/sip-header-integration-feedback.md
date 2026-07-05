# SIP Header Integration Feedback (v1.3 final)

This is a standards-feedback position paper, not an implementation spec.
NHID-Clinical is a behavioral and policy framework — it has no SIP stack, and
this document does not add one. It records where NHID-Clinical's controls would
benefit from signaling at the SIP/telephony layer, for the benefit of carriers,
SBCs, and platform vendors who do operate at that layer and might want to carry
disclosure state end-to-end.

## The gap this addresses

Today, IDG-01 disclosure happens entirely in-band: it is something an AI voice
agent *says* after the call connects. Nothing at the signaling layer indicates,
before the call is answered, that the calling (or called) party is an automated
agent. This means:

- A receiving system cannot pre-route or pre-flag AI-originated calls before
  audio starts.
- Bot-to-bot calls (see `docs/payer-initiated-calls.md` and
  `traces/nhid-trace-08-bot-to-bot-no-gate.md`) have no signaling-layer hint
  that both parties may be AI, before either side's in-band disclosure logic
  runs.
- `tests/trace_generator.py`'s bot-to-bot trace (line 355) already flags this
  as a known next step: *"Add counterparty_type detection to the ingress
  layer — identify AI callers from SIP headers or DNIS patterns"* — which
  presumes a header convention that does not yet exist.

## Relevant prior art

The IETF AgentID Protocol draft
(`draft-gudlab-agentid-protocol-00`) proposes a technical basis for carrying
agent identity tokens between AI systems; `traces/nhid-trace-08-bot-to-bot-no-gate.md`
already references it as "the technical basis for bot-to-bot identity tokens."
This document narrows that general proposal to one concrete ask relevant to
NHID-Clinical's domain: signaling *disclosure intent*, not full identity, at
call setup.

## Proposed convention (feedback, not a standard)

A custom SIP header, e.g. `Identity-Disclosure`, set by the originating party
at `INVITE` time:

```
Identity-Disclosure: ai-agent; disclosed=pending
```

- `ai-agent` — the originating party is an automated system, not a human.
- `disclosed=pending` — in-band IDG-01 disclosure has not yet occurred and
  will happen at call answer, consistent with NHID-Clinical's existing
  "disclose before data exchange" rule rather than replacing it.

This is explicitly **not** a substitute for in-band disclosure — a header can
be stripped, forged, or dropped by an intermediate carrier, so NHID-Clinical's
IDG-01 spoken-disclosure requirement remains the control of record. The header
is a *hint* that would let a receiving system's ingress layer pre-flag a call
for bot-to-bot policy evaluation before the policy engine ever sees a
transcript — closing the gap `trace_generator.py:355` already names, without
asking any platform to trust a header instead of verifying disclosure.

## Where this would need to go to become real

This is a position to raise with the IETF AgentID Protocol draft authors and/or
SIP carriers and SBC vendors directly — it is feedback for that standards
process, not something NHID-Clinical can unilaterally implement, since
NHID-Clinical operates at the application/policy layer (REST adapters
evaluating call transcripts after the fact) and has no presence in the SIP
signaling path itself. No code in this repository implements or depends on
this header; closing this item for v1.3 final means the position is written
down and ready to contribute to that external process, not that NHID-Clinical
ships SIP-layer functionality.
