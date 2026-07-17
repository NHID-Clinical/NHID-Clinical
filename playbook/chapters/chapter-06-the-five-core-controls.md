# Chapter 6 — The Five Core Controls

*Part II: The Framework*

---

## Replaying the Call

Take Chapter 1's nine-minute call — member ID, provider name, dates of
service, all exchanged before the representative's question — and run it, as
the conformance suite would, against five checks.

Did the caller disclose non-human identity before any PHI moved? No —
disclosure never happened. *IDG-01: fail.* Did protected data move before
identity was established? Yes, from the third turn. *PDX-01: fail.* Did the
caller present synthetic human-presence cues — the half-beat pause of
someone glancing at a screen, the hurried front-office warmth — or deflect a
direct human-status question? Both. *DBC-01: fail.* When the representative
needed the interaction to change course, was there a working path to a
human? The question never even applies cleanly — the caller *was* the
automation, and the only escalation available was a hang-up. *EIT-01: fail.*
And afterward, did any machine-readable record exist from which this
paragraph could have been reconstructed? Chapter 1 already answered that.
*ATR-01: fail.*

Five checks, five failures — and notice what the checks did *not* need:
no voice forensics, no model inspection, no detection oracle. Every verdict
came from observable conduct on the call. That is the design philosophy of
the entire control set, and this chapter walks through it one control at a
time.

---

## Executive Summary

NHID-Clinical v1.3 defines four behavioral controls plus an audit
requirement — five controls in all, each observable on a real call and
checkable against a machine-readable trace:

| Control | Name | Requirement |
| :-- | :-- | :-- |
| **IDG-01** | Identity Disclosure Gate | Disclose non-human identity before any PHI exchange |
| **PDX-01** | Pre-Data Exchange Gate | No protected data until identity is disclosed |
| **DBC-01** | Deceptive Behavior Check | No synthetic human-presence artifacts; no false human-status claims |
| **EIT-01** | Escalation Implementation Test | A clear human handoff path, honored on request |
| **ATR-01** | Audit Trail | Every call produces a machine-readable trace |

The controls are evaluated by a deterministic engine — same inputs,
identical outputs — against an eighteen-case conformance test suite, and
summarized per call by the Call Authorization Score (CAS), bucketed into
five trust tiers from Verified Trust (≥0.90) down to Hard Denial. The
framework's canonical failure traces give each control a documented
violation anatomy, and this chapter uses them the way case law uses cases.

Two design decisions explain the set's shape. The controls govern *conduct*,
not *content* — nothing here evaluates whether the agent's answers were
good, only whether its behavior was honest, sequenced, escapable, and
recorded. And the controls are *pairwise deliberate*: IDG-01 and PDX-01 are
two sides of one gate (disclose before data; no data before disclosure),
DBC-01 guards the gate against being satisfied deceptively, EIT-01
requires a working exit when conduct fails anyway, and ATR-01 makes all
of it provable after the fact.

## Why It Matters

For a payer or provider, the five controls are the answer to "what exactly
do we require of an AI caller?" — stated at a granularity that fits in a
contract clause, a vendor questionnaire, and an automated check, all three
from the same text. For a vendor, they are the answer to "what does
conformant behavior mean, concretely, turn by turn?" — with a public test
suite to verify against before any customer asks. For both, the controls'
observability is the point: every requirement can be checked from the call
itself and its trace, which means disagreements are about evidence, not
interpretation.

The controls also operationalize Part I's arguments. IDG-01 and PDX-01 are
impersonation latency's floor (Chapter 4's zero point). DBC-01 is Chapter
1's perverse incentive, inverted — deception becomes the violation, not the
winning strategy. EIT-01 answers the call-floor reality that some
interactions must reach a person. ATR-01 is the "disconnect with no
aftermath" anecdote made impossible.

## The Controls, One at a Time

### IDG-01 — Identity Disclosure Gate

**The requirement.** The agent discloses that it is an automated, non-human
system before any protected health information is exchanged in either
direction — in its first substantive sentence, not after rapport is built.
The reference policy engine's own disclosure line shows the expected shape:
*"I am an automated assistant calling on behalf of a healthcare
organization."* Plain words, first turn, no euphemism ("virtual assistant"
ambiguity, "digital team member" coyness) doing the work of avoidance.

**Violation anatomy.** The canonical late-disclosure trace shows the common
real-world failure: an agent that *does* disclose — at turn six, after
identifiers have already moved. Late disclosure fails IDG-01 even though
disclosure eventually occurred; the gate is positional, not eventual. The
direction extension matters too: on payer-initiated calls, the payer's
agent owes the same first-sentence disclosure to whoever answers — including
another AI. Failing to disclose to a machine "because no human was on the
line" is the impersonation-latency failure, not an exemption from it.

**How it's tested.** From the trace: is a disclosure timestamp set, is the
assertion text present, and does the timestamp precede all PHI events? The
engine enforces the gate structurally — in the reference state machine,
nothing routes to task handling until the disclosure state clears.

### PDX-01 — Pre-Data Exchange Gate

**The requirement.** No protected data moves — requested *or* accepted —
until identity disclosure is established. PDX-01 is IDG-01's enforcement
shadow: IDG-01 says what must happen first; PDX-01 says what must not
happen until then.

**Why both exist.** Because the failure modes differ. An agent can violate
IDG-01 by never disclosing; it violates PDX-01 the moment a member ID is
requested pre-disclosure — even if disclosure arrives a turn later. Keeping
them separate lets measurement distinguish "discloses late" from "collects
data early," which the pre-disclosure PHI exposure metric (Chapter 4)
depends on. On the receiving side, this book reads PDX-01's principle as
extending to the payer's own conduct — representatives should not
*volunteer* protected data to an undisclosed caller — as an operational
practice this playbook recommends, not a behavior the conformance test
suite evaluates; the CTS scores the calling agent, not the receiving
party. And in the bot-to-bot case, PDX-01 is the block: the documented
policy decision for an undisclosed AI counterparty halts data exchange
until that counterparty's identity is established.

**How it's tested.** Per-turn PHI flags in the trace, checked against the
sticky disclosure timestamp: any PHI event earlier than disclosure is a
violation, enumerable by field.

### DBC-01 — Deceptive Behavior Check

**The requirement.** Two prohibitions. No synthetic human-presence
artifacts — engineered breathing, typing sounds, performed hesitation, the
theater of embodiment Chapter 1 described. And no explicit human-status
claims — asked "am I speaking with a person?", the agent must answer
truthfully, never deflect into Chapter 1's "I'm calling from the provider's
office."

**The two-tier reality.** Detection of the two prohibitions differs in
kind, and the framework is candid about it. Artifact detection (Tier A)
relies on voice-forensics flags the capturing stack may or may not produce
— flagged violations are treated as critical precisely because the signal,
when present, is high-confidence. Text-level checking (Tier B) runs on
transcripts against a deliberately narrow phrase list — narrow because the
project *measured* what broadening costs: candidate expansions on its
550-conversation evaluation corpus produced more false positives than true
positives, the false positives being agents *correctly* disclosing or
offering human escalation. Lexically, "I can connect you with a human" and
impersonation live too close together for substring matching. The residual
ambiguity routes to human review by design — Chapter 7's whole subject.

**How it's tested.** Artifact flags copied per-turn into the trace's
governance block; phrase checks against speech text; explicit human-claims
as hard violations.

### EIT-01 — Escalation Implementation Test

**The requirement.** A clear path to a human, honored when requested. Two
words carry the weight. *Implementation*: a disclosed escalation option that
doesn't function — the agent says "transferring you" and loops — fails; the
test is of the path, not the promise. *Honored*: acknowledgment must be
immediate, and if no transfer is actually configured, the conformant
behavior is saying so plainly and offering an alternative contact path —
honesty about a missing path beats theater around a fake one.

**Violation anatomy.** The canonical trace is the missing escalation path:
the request recognized, the handoff nonexistent. The reference engine
treats escalation keywords ("human," "representative," "supervisor"...) as
an immediate route change — escalation outranks task completion in the
state machine, which is the design stance in miniature.

**How it's tested.** Escalation-requested and escalation-honored fields per
call; a request explicitly not honored is the failure condition.

### ATR-01 — Audit Trail

**The requirement.** Every call produces a machine-readable trace —
per-turn events with the governance block (disclosure timestamp, assertion
text, PHI flags, artifact flags, escalation fields) that every other
control's verification reads from. ATR-01 is deliberately listed with, not
after, the behavioral four: without it they are unverifiable assertions;
with it they are checkable facts. It is also the control that cannot be
faked retroactively — Chapter 3's dispute turns entirely on whether this
record exists.

**The honest limit.** In shadow evaluation, audit envelopes are synthesized
from transcripts by construction — real ATR-01 conformance is assessed only
against a live event pipeline (Tier 1+). The pilot kit says this itself;
the book repeats it wherever pilot data is discussed.

### CAS — the roll-up

The Call Authorization Score compresses a call's conformance into one
number, composed from identity-assertion, non-human operational confidence,
and event-completeness factors, and bucketed: **≥0.90 Verified Trust ·
≥0.75 Conditional Trust · ≥0.50 Review Required · ≥0.20 Denied/Degraded ·
below, Hard Denial.** The tiers are operational instructions, not grades —
Review Required routes to a human queue; the score's purpose is triage, and
Chapter 15 governs its use as a metric before anyone is tempted to make it
a target.

## Real-World Examples

*(Constructed illustrations of how the controls score a call, not
reported incidents.)*

**The eventually-honest agent.** An agent discloses cleanly — at turn five,
after collecting a member ID "to route your call efficiently." Under a
disclosure-mandate-only regime it might pass; under the paired gates it
fails both IDG-01 (positional) and PDX-01 (one PHI field pre-disclosure),
and the trace shows exactly which field, at which turn. The pairing exists
for this agent.

**The polite wall.** An agent handles a frustrated biller's "just get me a
person" with perfect courtesy — acknowledging, apologizing, and continuing
the workflow. No transfer, no honest admission that none exists. EIT-01
fails on *honored*, and the example shows why the control tests
implementation: everything the agent *said* was pleasant and none of it was
a path.

**The clean call.** First-sentence disclosure, no PHI until after, no
artifacts, escalation offered though unused, complete trace, CAS in
Verified Trust. Worth an example because it is unremarkable: nothing about
conformance degrades the transaction, and the whole exchange runs seconds
longer than a non-conformant equivalent. The controls' cost profile is one
sentence and a logging obligation — a fact procurement conversations should
open with.

## Diagrams to Include

1. **Figure 6-1 — The conformance flow.** The framework's own flowchart,
   redrawn for print: call start → IDG-01 gate → deny/allow paths → EIT-01
   branch → ATR-01 seal. The one diagram every implementer will pin up;
   fidelity to the reference flow matters more than elegance.
2. **Figure 6-2 — Five controls, one call timeline.** A conformant call's
   turns with each control's jurisdiction shaded: IDG/PDX at the front
   edge, DBC spanning the whole call, EIT event-triggered, ATR underneath
   throughout. Shows the controls as *when*, not just *what*.
3. **Figure 6-3 — Violation anatomy cards.** One compact card per control:
   requirement, canonical trace reference, what the evaluator reads from
   the trace. The chapter's extraction artifact.
4. **Figure 6-4 — CAS tier ladder.** The five tiers with thresholds and
   their operational meanings (proceed / proceed with note / human review /
   deny-degrade / hard denial). Must render tiers as *routing instructions*,
   not a report card.

## Operational Guidance

- **Adopt the control IDs into your own vocabulary.** "IDG-01 violation"
  is a precise, portable fact; "the bot didn't identify itself" is a
  complaint. Incident notes, vendor emails, and contract exhibits should
  use the IDs — they are the interoperable unit of this whole framework.
- **Write vendor expectations as the five rows.** The controls table is
  already contract-exhibit-shaped. Requiring rows 1–4 as conduct and row 5
  as an artifact deliverable is a complete, minimal first position — CAS
  thresholds can wait for your own baseline (Chapters 14–15).
- **Train the floor on the receiving-side half.** PDX-01 reads on the
  exchange: representatives need one new habit — don't volunteer protected
  data to an undisclosed caller — and one new disposition — record
  disclosure status. This is the operational successor to
  disconnect-on-detect, pending Chapter 10's full policy.
- **Use the traces as training material.** The canonical failure traces are
  short, concrete, and free; a one-hour session walking operations and
  compliance staff through traces 04–08 teaches the control set better
  than any slide deck.

## Implementation Guidance

1. **Run the CTS against a synthetic call first.** Take one of the demo
   scenarios, break it deliberately (strip the disclosure, add a
   pre-disclosure PHI request), and watch the verdict change. Determinism
   makes this a reliable learning loop: same edit, same verdict, every
   time.
2. **Map your existing call records to the trace's governance block.** The
   five controls read from a handful of fields — disclosure timestamp,
   assertion text, per-turn PHI flags, artifact flags, escalation pair.
   Whatever your stack calls these, the mapping exercise (formalized by
   the pilot kit's capture schema) is the real integration work, and it
   can start from historical logs today.

## Key Takeaways

- Five controls, all conduct-observable: disclose first (IDG-01), no data
  before disclosure (PDX-01), no deception (DBC-01), real escalation
  (EIT-01), machine-readable trace (ATR-01) — evaluated deterministically
  and rolled into a per-call CAS with five operational trust tiers.
- The set is pairwise deliberate: IDG/PDX are one gate seen from both
  sides, DBC guards the gate's honesty, EIT guarantees the exit, ATR makes
  everything provable. Removing any one reopens a documented failure trace.
- The controls govern conduct, not content — an agent's answer quality is
  explicitly out of scope, and conformance claims must not be laundered
  into quality claims.
- DBC-01's two tiers encode a measured honesty: text heuristics stay
  narrow because broadening them was tested and produced more false
  accusations than detections; the ambiguous middle routes to human review
  by design.
- Conformance is cheap by construction — one sentence, a sequencing rule,
  and a logging obligation — which is what makes requiring it reasonable.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Canonical failure traces (04–08) | Violation anatomies | Chapter 12 |
| Deterministic engine, state machine | IDG/EIT testing | Chapters 8, 10 |
| CAS composition and tiers | The roll-up; Figure 6-4 | Chapter 15 |
| DBC-01 Tier A/B, phrase-list ceiling | DBC-01 | Chapter 7 |
| Payer-initiated / bot-to-bot extension | IDG/PDX direction notes | Chapters 10–11 |
| Pilot-kit capture schema | Implementation guidance | Chapter 9 |
| ATR-01 shadow-mode limit | ATR-01 | Chapters 9, 12 |

---

*Next — Chapter 7, Behavioral Governance: why the framework governs conduct
deterministically, where deterministic checking honestly ends, and how the
human-review layer is built to catch what phrase lists cannot.*
