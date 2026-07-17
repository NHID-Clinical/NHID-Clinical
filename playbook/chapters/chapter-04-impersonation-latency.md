# Chapter 4 — Impersonation Latency

*Part I: The Problem*

---

## Two Calls

Two calls arrive at the same payer queue, a few minutes apart, from agents
performing the same task: a claims-status inquiry on behalf of a provider
practice.

The first agent's opening turn: *"I am an automated assistant calling on
behalf of a healthcare organization — I'm following up on two claims for
Dr. Reyes's practice."* The representative knows, before any identifier is
spoken, what is on the line and whom it claims to act for. Turn one. Seconds
into the call.

The second agent opens with a greeting, confirms it has reached the right
department, passes the authentication questions, provides a member ID and two
dates of service, receives claim statuses, and asks a follow-up about a
denial code. At no point does it disclose. If the representative never asks —
and Chapter 1 explained why asking has stopped working — the call ends with
the payer never knowing. Nine turns, several minutes, one member's data.

Same task. Same technology. Possibly the same vendor platform. The entire
difference between these calls is a *duration*: how long the receiving
organization operated without knowing what it was talking to. The first call
held that window to a single turn. The second held it open for the whole
call — and no metric on any dashboard recorded the difference.

Part I has spent three chapters circling this window. This chapter puts a
ruler on it.

---

## Executive Summary

**Impersonation latency** is the measurable trust delay between an AI agent
initiating a call and the receiving organization verifying that the caller is
authorized to represent the claimed provider organization. Operationally, the
NHID-Clinical pilot kit measures it as
`Δt(interaction_start → identity_resolution)` — the elapsed time, and the
number of conversational turns, from the start of the interaction until the
first valid non-human disclosure is established.

Three properties make the concept useful rather than merely descriptive.
First, it is **per-call and objective**: every call has a latency value
(possibly infinite, for calls where disclosure never happens), extractable
from records organizations already keep. Second, it is **decomposable along
Chapter 3's three questions**: the measured core is disclosure latency (the
nature question), and the full window extends through representation and
authorization — which today go unresolved on essentially every call, since no
instrument exists to resolve them. Third, it has a **defined zero**: a call
that opens with disclosure in the first substantive sentence, before any
protected data moves, has driven the behavioral component of the window to
its floor — which is exactly what the framework's controls require and what
its conformance suite tests.

The chapter also states the measurement's honest boundary, promised in
Chapter 1's editorial review: latency is measured on *recorded traffic*
against *observable disclosure behavior*. It does not detect covert AI. A
never-disclosed call by a fully covert agent appears in the data as a human
call. The metric's power is managerial, not forensic — it makes the governed
population measurable and the ungoverned population estimable by difference,
and it gives vendors, payers, and regulators a shared number where none
existed.

## Why It Matters

Chapter 1 ended on "what is unmeasured cannot be managed." This chapter is
where that stops being a slogan.

A named, defined, per-call metric changes who can talk about the problem and
how. Before it, the conversation is anecdote ("we think we're getting bot
calls") versus denial ("our agents are compliant"), with no way to close the
gap. After it, a payer can baseline its own traffic in two to four weeks with
the Tier 0 kit, a vendor can be asked a precise question ("what is your
median disclosure latency in turns, and your never-disclosed rate?"), a
contract can carry a threshold, and a regulator can be shown a distribution
instead of a war story. Every later chapter that touches measurement,
enforcement, or procurement — 9, 10, 13, 15 — spends this chapter's currency.

The metric also disciplines the framework itself. NHID-Clinical's central
promise is not "we detect bad agents"; it is "conformant agents hold this
window to its floor, verifiably." A framework whose core claim is a
measurable quantity can be checked, which is what separates a baseline from
a brochure.

## Defining the Measurement

The definition again, with each phrase carrying weight:

> The measurable trust delay between an AI agent initiating a call and the
> receiving organization verifying that the caller is authorized to
> represent the claimed provider organization.

**"Measurable."** The unit is time *and* conversational turns. Turns matter
more than seconds in practice: a turn is where data moves. A thirty-second
hold contributes nothing to exposure; a single turn can carry a member ID,
a date of birth, and a claim number. The pilot kit reports both, and its
stability criterion for actionable data is expressed in turns (week-over-week
median within ±1 turn).

**"Trust delay."** Not processing delay, not hold time. The window during
which the receiving side is *operating on an unverified assumption* — usually
the default assumption, inherited from a century of telephony, that the
caller is a person. Everything exchanged inside the window is exchanged under
that assumption.

**"Verifying... authorized to represent."** The definition's full scope runs
through all three of Chapter 3's questions. In the framework's current state,
the parts are at different maturities, and honesty requires saying so
plainly:

- **Disclosure latency** — time to resolve the *nature* question via the
  agent's own valid non-human disclosure. This is what the Tier 0 kit
  measures today (`Δt(interaction_start → identity_resolution)`), because
  disclosure is observable in any transcript.
- **Verification latency** — time to resolve *representation* and
  *authorization*. On today's calls this component is effectively unbounded:
  the instruments to resolve it mid-call do not exist in production. Where
  NHID-Auth v2 is in play, an agent passport can be verified at call setup,
  collapsing this component toward zero as well — but that is reference-
  implementation reality, not deployed reality, and the book will not blur
  the two.

A useful shorthand the rest of the book uses: **the measured metric is
disclosure latency; the named problem is the whole window.** When a chapter
says "impersonation latency" about pilot data, it means the measured core.

**The zero point.** A conformant call under the framework's controls
discloses non-human identity in the first substantive sentence (IDG-01),
before any protected data moves (PDX-01). Latency: one turn, seconds,
pre-PHI. That floor is not aspirational — it is what the conformance suite
tests and what the deterministic policy engine enforces by refusing to route
anything before the disclosure gate clears. Zero-latency behavior is a
design choice available to every vendor today, at no technical cost. The
distance between an ecosystem's actual distribution and that floor is a
choice someone is making.

## The Companion Metrics

Latency alone can mislead; the pilot kit surrounds it with four companions,
and they should always travel together.

- **First-turn disclosure rate** — the fraction of calls at the floor. The
  single best headline number for a vendor or a traffic population.
- **Never-disclosed rate** — calls where no valid disclosure ever occurs;
  the latency is right-censored, not large. Averaging infinite values into a
  mean is how a bad distribution gets laundered into a plausible number —
  report this rate separately, always.
- **Pre-disclosure PHI exposure** — the count and type of sensitive fields
  requested *before* disclosure. This converts latency from a duration into
  a harm proxy: two calls with identical latency differ enormously if one
  spent the window on greetings and the other on member IDs.
- **Escalation honor rate** — requests for a human honored versus requested.
  Not a latency measure, but captured in the same pass and reported in the
  same pilot, because a long-latency agent that also traps callers away from
  humans compounds both failures.

Distributions, not averages, throughout. A traffic mix of many first-turn
disclosers and a minority of never-disclosers can present a comforting
median around a disturbing tail — and the tail is where the exposure lives.

## What the Metric Honestly Cannot See

Stated once, bluntly, so no later chapter has to hedge.

The measurement replays *recorded* calls against *observable* behavior. An
agent engineered for covertness — no disclosure, no tells, synthetic
presence artifacts — produces a transcript indistinguishable from a human
call, and enters the data as one. Therefore: the never-disclosed rate among
*identified-as-automated* calls is a floor, not a census; the true automated
share of traffic is not directly knowable from this data; and any claim that
"our measured latency covers our AI traffic" quietly assumes the covert
population is small, which is exactly what cannot be verified.

This is not a flaw to apologize for — it is the boundary between a
measurement framework and a detection fantasy. Chapter 3 established that
detection loses the arms race; the framework's answer is to make disclosure
cheap, verifiable, and expected, so that covertness becomes a deliberate,
policy-visible act rather than the ambient default. The metric measures the
governed world honestly and shrinks the ungoverned one by making governance
the path of least resistance. Claims beyond that are not on offer.

## Real-World Examples

**The distribution with two humps.** A payer runs the Tier 0 measurement on
one workflow's traffic and finds a bimodal shape: a cluster of calls
disclosing at turn one — vendors that made the design choice — and a long
tail disclosing never. Almost nothing in between. The lesson: latency is not
a skill that ecosystems improve gradually; it is a binary design decision
visible in the data. Procurement conversations change immediately — the ask
is not "improve," it is "move to the first hump."

**The turn that carried everything.** Two flagged calls show latency of
four turns each. Pre-disclosure PHI exposure shows one requested nothing in
those turns; the other collected member ID, date of birth, and claim number
by turn three. Identical latency, incomparable exposure — the example that
justifies never reporting the duration without the exposure companion.

**The vendor who asks to be measured.** A voice-AI vendor, ahead of a payer's
questionnaire, submits its own call payloads through the public adapter
routes and quotes its first-turn disclosure rate and CAS distribution in a
sales response. Nothing in the framework required this; the existence of the
metric made it a competitive move. This is the incentive inversion Chapter 2
called for — the honest agent finally has something to gain — and it costs
the payer nothing to have created it beyond asking for numbers.

## Diagrams to Include

1. **Figure 4-1 — The latency bar, formalized.** The same annotated timeline
   as Figure 1-3 (the nine-minute call), now with the measurement drawn in:
   `interaction_start` marker, `identity_resolution` marker, the Δt bracket
   labeled in turns and seconds, PHI events inside the window flagged as
   pre-disclosure exposure. Visual rhyme with Figure 1-3 is mandatory —
   brief both to the illustrator together.

2. **Figure 4-2 — Decomposing the window.** A horizontal bar split into the
   disclosure component (nature — measured today) and the verification
   component (representation + authorization — unbounded today, collapsible
   at call setup under NHID-Auth). The two components rendered in different
   maturity styles (solid vs. hatched), caption stating the
   measured-metric/named-problem distinction verbatim.

3. **Figure 4-3 — A latency distribution, honestly drawn.** A schematic
   histogram: first-turn spike, sparse middle, and a visually separated
   right-censored bar for never-disclosed (drawn *outside* the axis, not as
   a tall final bin). Caption: no real data — illustrative shape only; the
   two-hump pattern is what pilots should look for, not what any pilot has
   published.

4. **Figure 4-4 — Metric card.** A one-page reference card: definition,
   formula, units, the four companion metrics, the stability criterion
   (±1 turn week-over-week), and the honest-boundary statement. Designed to
   be photocopied out of the book into a pilot charter — this figure is the
   chapter's deliverable.

## Operational Guidance

- **Adopt the vocabulary before the tooling.** Start writing "impersonation
  latency," "first-turn disclosure," and "never-disclosed rate" into
  incident notes, vendor questions, and internal decks now. Shared language
  is the cheapest coordination technology in this book, and it requires no
  approval.
- **Ask vendors the four-number question.** Median disclosure latency in
  turns; first-turn disclosure rate; never-disclosed rate; what PHI, if any,
  their agents request before disclosing. A vendor who cannot answer has
  told you something; a vendor who answers well has just been handed a way
  to win your business. Both outcomes serve you.
- **Set no thresholds yet.** The temptation after naming a metric is to
  mandate a number. Resist it until you hold your own baseline (Chapter 9)
  — a threshold set before measurement is set by negotiation, and Chapter 15
  covers how thresholds harden into policy without inviting Goodhart
  gaming.
- **Report the tail, not the mean.** Whoever builds the first internal slide
  on this metric sets the organization's habits. Insist the never-disclosed
  rate appears beside any latency figure from the first slide onward.

## Implementation Guidance

1. **Dry-run the measurement pipeline now.** The pilot kit runs a
   no-data-needed check (`python docs/pilot-kit/measure_pilot.py --demo`).
   Having an engineer run it this week surfaces the environment and access
   questions months before the pilot needs them answered — and costs an
   afternoon.
2. **Audit your records for the two timestamps.** The metric needs
   `interaction_start` and enough transcript fidelity to locate a disclosure
   sentence and PHI requests per turn. Check whether your recording and
   transcription pipeline preserves turn boundaries and timestamps; if it
   collapses calls into unsegmented text, that is the gap to fix first, and
   it is a telephony-platform configuration question, not a framework one.

## Key Takeaways

- Impersonation latency names the window Part I has been describing: the
  trust delay between an agent initiating a call and the receiving
  organization verifying it — measurable per call, in seconds and in turns,
  from records organizations already keep.
- The measured core is disclosure latency (`Δt(interaction_start →
  identity_resolution)`); the full window extends through representation
  and authorization, which today go unresolved on essentially every call.
  Keep the measured metric and the named problem distinct.
- The metric has a defined floor — disclosure in the first substantive
  sentence, before any PHI — and the floor is a design choice available to
  every vendor today, which is what makes the ecosystem's distance from it
  a governance fact rather than a technical one.
- Latency never travels alone: first-turn disclosure rate, never-disclosed
  rate, pre-disclosure PHI exposure, and escalation honor rate complete the
  picture, and distributions — with the censored tail shown honestly —
  replace averages.
- The measurement sees recorded, observable behavior only. It does not
  detect covert agents, and the framework does not pretend otherwise; its
  strategy is to make disclosure the cheap default so covertness becomes a
  visible, deliberate act.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| `Δt(interaction_start → identity_resolution)` | Defining the measurement | Chapter 9 (pilot mechanics) |
| First-turn / never-disclosed / pre-disclosure PHI / escalation honor rate | Companion metrics | Chapter 15 |
| IDG-01, PDX-01 (the zero point) | Defining the measurement | Chapter 6 |
| Stability criterion (±1 turn) | Companion metrics; Figure 4-4 | Chapters 9, 15 |
| Tier 0 Shadow Pilot Kit | Throughout | Chapter 9 |
| NHID-Auth v2 (collapsing verification latency) | Decomposition | Chapter 11 |
| CAS distribution | The vendor who asks to be measured | Chapters 6, 15 |
| Public adapter routes | The vendor who asks to be measured | Chapter 13 |

---

*Next — Part II opens with Chapter 5, What is NHID-Clinical?: the framework
in full, and — just as carefully — what it deliberately is not.*
