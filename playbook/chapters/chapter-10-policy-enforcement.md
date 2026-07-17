# Chapter 10 — Policy Enforcement

*Part III: Implementation*

---

## The Same Call, Under Policy

One more time, Chapter 1's call — but now it arrives at an organization
that has done everything this book has described so far: a baseline from
its shadow pilot, the conformance service wired in-call on the
turn-by-turn webhook, and a written enforcement policy.

Turn one: the caller opens warmly and asks about two claims. No
disclosure. The policy engine returns its verdict for an undisclosed
session — the only action available from that state is DISCLOSE, reason
`DISCLOSURE_GATE` — and the representative's screen shows a quiet banner:
*undisclosed automated-pattern caller; do not volunteer member data;
disclosure prompt available.* The representative reads the standard line:
"Before we continue — is this an automated or AI-assisted call? We
support those; they just have different verification steps."

Two futures fork here, and the policy handles both. In one, the caller
answers honestly — "Yes, this is an automated assistant calling for
Dr. Reyes's office" — and the call *continues*: disclosure logged,
latency recorded at two turns, PHI exchange proceeds under the normal
workflow, CAS lands in Conditional Trust, nobody hangs up on anybody. In
the other, the caller deflects — "I'm calling from the provider's
office" — and the policy's next rung engages: no protected data moves
(the PDX-01 obligation is now the *representative's* procedure too), the
caller is offered a callback through the provider's verified number on
file, and the call ends with a disposition code and a complete trace
instead of a shrug.

Neither future involved detecting anything. The policy never asked "is
this a bot?" — it asked "has disclosure occurred?", a question with a
knowable answer. And the honest agent got a *better* outcome than the
deflecting one, which is the entire moral inversion Chapter 1 demanded:
eight chapters later, the incentive gradient finally points the right
way.

---

## Executive Summary

Enforcement is where measurement acquires consequences, and this chapter
is deliberate about what kind. NHID-Clinical enforcement is **graduated,
deterministic, and disclosure-anchored**: responses scale from logging,
through routing and data-gating, to blocking — driven by the policy
engine's closed action set (DISCLOSE, ESCALATE, BLOCK, ROUTE_LLM, ERROR)
and reason codes, never by anyone's hunch about whether a voice sounds
synthetic. The chapter replaces disconnect-on-detect — the procedure
Chapter 1 dismantled — with its successor: a written enforcement ladder in
which honest disclosure always yields a better outcome than concealment,
undisclosed sessions are data-gated rather than terminated, escalation
preempts everything, and every enforcement event produces a trace.

Three design principles govern. **Consequence follows confidence**
(Chapter 7's proportionality, now with teeth): deterministic findings
(no disclosure before PHI request; explicit human-status denial) can
gate data in-call; probabilistic signals (phrase matches, low composite
scores) route to review and *never* block on their own. **Enforcement is
due process, not accusation**: because the engine is deterministic and
versioned, every enforcement event carries a replayable justification —
a vendor disputing a verdict re-runs the inputs, and policy changes ship
as visible version events. **The receiving side is bound too**: the
policy obligates representatives (don't volunteer PHI to undisclosed
callers; honor the disclosure-prompt script; never punish a disclosed
call for being disclosed) because Chapter 1 proved that receiving-side
behavior *is* the incentive structure vendors optimize against.

Enforcement placement is a topology-and-policy pairing: post-call
enforcement (vendor scorecards, contractual consequences, review queues)
runs on the monitoring topology everyone already has; in-call enforcement
(banners, data-gating, guided callbacks) requires the turn-by-turn
webhook and should arrive only after months of post-call data has set the
thresholds.

## Why It Matters

An unenforced baseline decays into wallpaper; an over-enforced one
recreates the disconnect regime with better paperwork. The narrow path
between them is what this chapter maps, and the stakes are asymmetric in
a way executives should hear plainly: enforcement mistakes against
*honest* agents are the expensive ones. A deceptive caller wrongly allowed
to complete one call costs one call's exposure, caught later by review
and audit. An honest vendor wrongly blocked, accused, or disadvantaged
learns — and teaches its market — that disclosure costs business, which
re-manufactures the concealment equilibrium the whole framework exists to
break. Every rung of the ladder below is shaped by that asymmetry.

Enforcement is also where the framework's coordination-failure framing
(Chapter 2) pays its dividend. Because the policy is written against
*conduct* rather than *identity*, it needs no bot-detection capability,
no vendor blacklist, and no accusation to function — an organization can
publish its enforcement ladder openly, hand it to every counterparty,
and improve its own incentive landscape unilaterally. Protocol, not
punishment.

## The Enforcement Ladder

Five rungs, each with its trigger class, its action, and its record.

**Rung 0 — Log.** Trigger: everything. Every evaluated call produces its
trace and CAS regardless of outcome. Not properly enforcement, but the
rung everything else stands on: consequences without records are
Chapter 1's oral tradition again.

**Rung 1 — Route to review.** Trigger: probabilistic signals — DBC-01
phrase matches (major), artifact flags (critical), CAS below Conditional
Trust (0.75). Action: queue per the Chapter 7 SOP; the call itself
proceeds. This rung exists precisely so the next ones don't fire on
low-confidence evidence — it is the pressure-relief valve that keeps the
ladder honest.

**Rung 2 — Prompt and gate.** Trigger: deterministic in-call state — an
undisclosed session requesting or approaching PHI. Action: the
representative's disclosure prompt; PHI withheld until disclosure occurs
(`DISCLOSURE_GATE` is now floor procedure, not just engine state). A
session that discloses at the prompt *rejoins the normal workflow with no
penalty* — the ladder's most important single rule, italicized on
purpose.

**Rung 3 — Managed termination.** Trigger: deterministic refusal —
explicit human-status denial when asked directly (a hard DBC-01
violation), or continued PHI-seeking through a maintained gate. Action:
no data, a verified-callback offer through the provider's number on
file, courteous close, full trace, disposition code. Note what this rung
is not: it is not a hang-up. The callback offer keeps a legitimate-but-
misconfigured agent's *task* completable through a channel that
re-anchors identity, so even the ladder's hardest routine rung leaves a
door open to the legitimate.

**Rung 4 — Relationship consequences.** Trigger: patterns, not calls —
persistent never-disclosure from a vendor's traffic, repeated confirmed
violations, escalation dishonor rates. Action: the post-call machinery —
vendor scorecards, contract remedies (Chapter 13's language), pilot-data
-armed procurement conversations. This rung runs entirely on the
monitoring topology and is where most organizations' enforcement should
*live* for their first year: it is calm, evidenced, reversible, and it
moves markets more than any in-call banner.

Two absences from the ladder are deliberate. There is no
detected-as-synthetic rung — voice suspicion is not a trigger anywhere,
because Chapter 3 established detection cannot carry enforcement weight.
And there is no automatic call-kill: even ERROR states fail closed to
BLOCKED (no further data) rather than to disconnection, because the
trace of a gated call teaches more than the silence after a dropped one.

## Determinism as Due Process

Chapter 7 made the governance argument; enforcement is where it becomes
protection — for both sides.

Every enforcement event above Rung 0 carries: the policy version that
fired, the reason code, the triggering state, and the trace to replay it
against. A vendor who believes Rung 3 fired wrongly does not open a
he-said-she-said; they replay the trace against the published engine
version and either reproduce the verdict or expose a real divergence —
and the framework treats replay divergence as a named, canonical failure
of the *system*, not the vendor. Enforcement thresholds (the 0.75 review
line, gate timing, prompt scripts) are policy-version content: changing
them is a diffable, announceable event with an effective date, which is
what allows counterparties to conform *in advance* rather than discover
the rules by tripping them.

Write this into the enforcement charter directly: **no consequence
without a reason code; no reason code without a replayable trace; no
policy change without a version and a date.** Three clauses, and the
difference between enforcement and caprice.

## Real-World Examples

**The prompt that became a norm.** An organization deploys Rung 2 and
finds — the pattern its pilot data predicts — that most undisclosed
agents *disclose immediately when prompted*: their operators never chose
concealment; they simply optimized openings for task completion because
nothing ever asked otherwise. Within a quarter, first-turn disclosure in
that organization's inbound traffic rises measurably: vendors adapt
openings to the known prompt. A single receiving-side script, applied
consistently, moved vendor behavior without one contract change — the
unilateral-improvement claim, cashed.

**The block that wasn't a block.** A biller's legitimate agent hits Rung
3 repeatedly over two days — it is misconfigured to deflect the
human-status question with its "office" script. The managed termination's
callback path keeps claims flowing (degraded, human-handled) while the
disposition codes accumulate; the Rung 4 conversation with the vendor is
one email with three trace excerpts; the fix ships in a week. Under
disconnect-on-detect, the same fortnight would have been dropped calls,
mutual suspicion, and no artifact anyone could act on.

**The threshold set from the wrong side.** A counter-example: an
organization skips its pilot and sets an in-call CAS gate by intuition.
The gate fires constantly on a mapping artifact (thin identity-assertion
text from one platform's payload format), gating conformant vendors'
calls for a week before anyone checks the reason codes. Everything about
the failure was preventable by sequence: post-call data first, gates
after. The example exists because someone in every reader's organization
will propose skipping to Rung 2 "since the machinery's already there."

## Diagrams to Include

1. **Figure 10-1 — The enforcement ladder.** Five rungs with trigger
   class, action, and record columns; deterministic vs. probabilistic
   triggers color-coded; the two deliberate absences (no
   suspicion-trigger, no auto-kill) annotated in the margin. The
   chapter's extraction artifact.
2. **Figure 10-2 — The forked call.** The opening scenario as a sequence
   diagram: one call, the disclosure prompt, two branches (honest →
   normal workflow; deflection → gate → callback → trace). Visual proof
   that the honest branch is shorter and smoother.
3. **Figure 10-3 — Consequence/confidence alignment.** Chapter 7's
   Figure 7-3 extended with the enforcement rungs as the consequence
   axis — one figure now spanning governance and enforcement, showing no
   probabilistic signal reaches a blocking consequence.
4. **Figure 10-4 — Due-process anatomy of one enforcement event.** A
   single Rung 3 event exploded: policy version, reason code, state,
   trace pointer, replay path, dispute route. The vendor-facing figure —
   design it to be shown *to* counterparties.

## Operational Guidance

- **Publish your ladder.** Send the enforcement policy to counterparties
  before it takes effect, with its version and date. Surprise is the
  enemy of the incentive effect: vendors can only optimize toward rules
  they can read.
- **Script the prompt, and script it warmly.** The disclosure prompt is
  the single highest-leverage sentence in your enforcement stack. It
  must communicate that automated calls are *supported* — "we support
  those; they just have different verification steps" — or it becomes a
  threat, and threats teach concealment.
- **Meter the gap between rungs 1 and 2.** Run Rung 1 (review routing)
  for at least a full quarter before activating Rung 2 in-call. The
  review queue's confirmed/refuted ratio is your evidence that
  deterministic triggers are firing on reality rather than mapping
  artifacts — the wrong-side-threshold example is what skipping this
  looks like.
- **Never let a disclosed call fare worse than a concealed one.** Audit
  for it explicitly: compare handle time, completion rate, and callback
  imposition between disclosed-at-turn-one calls and
  never-flagged calls quarterly. If disclosure is being punished
  anywhere in your operation — even informally, even by one team's
  habit — your enforcement stack is training the market against you.

## Implementation Guidance

1. **Encode the ladder as configuration reviewed like code.** Rung
   thresholds, prompt scripts, gate behavior, and callback rules belong
   in versioned configuration with change review — the policy-version
   discipline extended to your own overlay. Stamp every enforcement
   event with both versions (engine's and yours).
2. **Build the dispute path before the first Rung 3 fires.** A mailbox,
   a trace-export procedure (Chapter 12's bundle), and a committed
   response time. The first vendor dispute sets the tone for every one
   that follows; meeting it with a replayable trace and a named policy
   version is how enforcement earns the legitimacy it spends.

## Key Takeaways

- Enforcement is graduated (log → review → prompt-and-gate → managed
  termination → relationship consequences), deterministic in its
  triggers, and disclosure-anchored — no rung fires on suspicion, and
  no rung is a bare hang-up.
- The asymmetry rules the design: wrongly punishing honest agents costs
  more than wrongly permitting deceptive ones, because it re-teaches the
  market concealment. A session that discloses when prompted rejoins the
  workflow penalty-free — the ladder's cardinal rule.
- Consequence follows confidence: deterministic findings can gate data;
  probabilistic signals only ever route to review. Chapter 7's
  proportionality, given teeth.
- Determinism is due process: no consequence without a reason code, no
  reason code without a replayable trace, no policy change without a
  version and a date — protections that run in both directions.
- Sequence is strategy: live on post-call enforcement (Rung 4) first,
  set in-call gates from your own baseline months later, and publish
  the ladder so counterparties can conform in advance. Receiving-side
  conduct is part of the policy, because it is the incentive structure.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Engine actions, states, reason codes | Throughout | Chapter 8 |
| DISCLOSURE_GATE as floor procedure | Rung 2 | Chapters 6, 8 |
| Non-blocking probabilistic signals (LOG_ONLY) | Rung 1; Figure 10-3 | Chapter 7 |
| CAS 0.75 review threshold | Rung 1 | Chapters 7, 15 |
| Hard DBC-01 (human-status denial) | Rung 3 | Chapter 6 |
| Replay / determinism (trace 09) | Due process | Chapters 7–8, 12 |
| Fail-closed design | Ladder absences | Chapter 8 |
| Payer-initiated symmetry | Receiving-side obligations | Chapters 2, 6 |
| Vendor scorecards / contract remedies | Rung 4 | Chapters 13, 15 |

---

*Next — Chapter 11, Authorization: the cryptographic layer that answers
the questions enforcement can only gate around — who delegated this
agent, with what scope, and for which call.*
