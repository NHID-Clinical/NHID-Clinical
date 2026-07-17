# Chapter 9 — Shadow Evaluations

*Part III: Implementation*

---

## The Meeting Where Nothing Was Promised

A director of payer operations convenes four people: a call-center
supervisor, a data engineer, a compliance analyst, and herself. The agenda
is one line — *measure the AI-caller situation on our own traffic* — and
she opens with the constraint that makes the meeting short:

"We are not changing anything. No vendor gets contacted. No call gets
handled differently. No policy is proposed. We pull records of calls that
already happened, we run them through a measurement tool, and in a month
we know our own numbers instead of our own anecdotes."

The data engineer asks what everyone asks: what do we have to build? The
answer — map existing call logs into a twelve-field-per-turn capture
format, then run a script — reshapes the meeting. This is not a project.
It is a query, a mapping exercise, and a report. The compliance analyst
asks what the output is; the answer is a short internal report with five
numbers and a violations table. The supervisor asks what happens to
vendors who look bad in the data; the answer is *nothing happens to
anyone* — that is what "shadow" means, and it is why this pilot needs no
one's permission but their own.

Four weeks later the organization knows its median impersonation latency,
its never-disclosed rate, and its top three control violations by
workflow. It has spent no political capital, changed no call, and made no
enemy. Everything in the rest of Part III begins from the numbers this
chapter produces.

---

## Executive Summary

A shadow evaluation — Tier 0 in the framework's integration ladder — is an
observe-only measurement of NHID-Clinical's metrics against an
organization's own historical or parallel call traffic. No vendor changes,
no live enforcement, no production risk. The framework packages it as the
Tier 0 Shadow Pilot Kit: a minimal per-turn capture schema, a measurement
script that replays captured turns through the real policy engine, a
report generator, and a report template — designed to yield usable data in
two to four weeks.

The kit measures: **impersonation latency** (`Δt(interaction_start →
identity_resolution)`, in time and turns), **first-turn disclosure rate**,
**never-disclosed rate**, **pre-disclosure PHI exposure**, **escalation
honor rate**, **per-control violations** (IDG-01, PDX-01, DBC-01, EIT-01),
and the **CAS distribution** across trust tiers. The pilot plan is
staged: weeks one and two, capture 500–2,000 calls from one workflow and
run the baseline; week three, analyze and hand-verify a sample of flagged
calls; week four, write up and decide.

The kit carries its limits on its face, and this chapter keeps them there.
ATR-01 cannot be exercised from transcript replay — audit envelopes are
synthesized by construction, and audit conformance is a Tier 1+ question.
DBC-01's voice-artifact tier requires forensics flags most capture stacks
don't produce; text heuristics still run. And the data is actionable only
when it meets stated thresholds: at least 500 calls from at least two
weeks of one workflow's traffic, under 10% dropped for unmappable fields,
flagged calls verified by hand with the observed false-positive rate
documented, and week-over-week median latency stable within one turn.
Below those bars, the honest move is to extend the capture window — a
small or noisy sample overstates whatever it happens to contain.

## Why It Matters

The shadow evaluation is the framework's entire theory of adoption
compressed into one artifact. Part I argued the problem is invisible
because nothing measures it; Part II defined the instruments; this is the
step where an organization points the instruments at itself — and it is
deliberately engineered to require no trust in anyone. Not in the
framework's claims (you run the measurement), not in vendors'
self-reports (you replay their actual calls), not in this book (your
traffic, your numbers).

Its observe-only character is not timidity; it is sequencing discipline.
Every consequential decision downstream — enforcement thresholds (Chapter
10), contract language (Chapter 13), CAS targets (Chapter 15) — is only
defensible *from a baseline*. Organizations that skip to enforcement
negotiate their thresholds against vendor pushback instead of against
their own data, and lose. Organizations that pilot first walk into those
conversations holding a distribution.

There is also an asymmetry worth naming for executives: the pilot's cost
is bounded and small (one part-time engineer, a few analyst-days, four
weeks), while its downside is essentially the null result — *our traffic
shows little automated calling and high disclosure* — which is itself
worth knowing and worth documenting. Few governance initiatives offer a
first step this cheap with an information payoff this certain.

## The Kit, Component by Component

**The capture schema** is deliberately flat — twelve-ish fields per turn,
fillable from ordinary call logs: timestamps, speaker role, speech text,
disclosure timestamp and assertion text where present, PHI-accessed
flags, artifact flags if available, and the escalation request/honor
pair. Flatness is a kindness to data engineers; the measurement script
owns the translation into the engine's nested contract (Chapter 8's
governance block), including the rules that trip up hand-rolled
attempts — the disclosure timestamp is *sticky* (once set, carried to
every later turn), agent turns default their assertion text to their own
speech, and escalation honor maps to the session-level path-availability
the engine actually reads. The kit's documentation is blunt: do not feed
flat records to the engine yourself; the behavioral controls read the
nested block, and flat fields are silently ignored.

**The measurement script** replays every captured turn through the real
policy engine — the same deterministic evaluator the conformance API
runs — and computes the full metric set per call and in aggregate. It
ships with a no-data demo mode (`--demo`) that verifies the environment
in minutes, which is why Chapter 4's implementation guidance had you run
it weeks ago.

**The report generator and template** turn per-call results into the
internal document the pilot actually exists to produce: metrics up front,
CAS tier distribution, top violations per workflow, hand-verification
results including the observed false-positive rate, and a recommendations
section the template forces you to fill in — because a pilot that ends
without a decision recommendation was a measurement, not a pilot.

## Running It Well: the Four Weeks

**Weeks 1–2 — capture and baseline.** Choose *one* workflow — prior
authorization, claims status, or billing — and pull 500–2,000 calls.
One workflow, not a cross-section: violations and latency differ by
workflow, and a mixed sample blurs exactly the contrast that makes
results actionable. Map a sample first, validate against the schema,
then bulk-map; run the baseline early enough to catch mapping problems
while the window can still be extended.

**Week 3 — analyze, then verify by hand.** Read the CAS tier distribution
and the top-three violations. Then do the step that separates credible
pilots from slideware: pull 10–20 flagged calls and read them, confirming
the violations are real before drawing conclusions. Expect some false
positives — Chapter 7 explained why they are structural — and *document
the rate you observe rather than assuming zero*. The hand-check is also
where the organization's intuitions get calibrated: reading five actual
never-disclosed calls teaches the problem better than any distribution
chart.

**Week 4 — decide and write.** The template's decision menu is the honest
one: proceed toward Tier 1 (wire post-call checking into the live
pipeline), open vendor conversations armed with the data, expand the
sample to another workflow, or stop — recorded with reasons. Meeting the
good-enough bars is what licenses the decision; missing them licenses
only "extend the window."

**What shadow data cannot say.** Three reminders that belong in every
pilot report's caveats section, verbatim if need be. The sample measures
*observable disclosure behavior on recorded traffic* — covert agents
appear as humans (Chapter 4's boundary). ATR-01 results are synthesized
by construction and say nothing about any vendor's real audit pipeline.
And pilot numbers are measurements of your traffic, not conformance
certifications of anyone — the kit's own documentation forbids the
certification reading, and so should your report.

## Real-World Examples

**The workflow contrast.** A composite of the pattern the kit is built to
surface: prior-auth calls show materially longer latency and more
pre-disclosure PHI requests than claims-status calls — the higher-stakes
workflow attracts the more aggressive automation. The single-workflow
rule made the contrast visible; a blended sample would have averaged it
away. The vendor conversation that follows is specific: "on prior auth,
your agents request member IDs before disclosing; here are the turns."

**The mapping failure caught early.** A data engineer maps
`disclosure_timestamp` per-turn but not sticky; every post-disclosure
turn looks undisclosed, and the first baseline run shows an absurd 100%
IDG-01 violation rate. The week-1 validation sample catches it in an
hour. The example earns its place because this class of error — flat
thinking about stateful fields — is the kit's documented number-one trap,
and because an *absurd* result caught early is the pilot working as
designed: implausible numbers are mapping bugs until proven otherwise.

**The null result that wasn't null.** A pilot finds low automated-call
volume and high first-turn disclosure in its sample — and a 9% escalation
dishonor rate concentrated in one vendor's traffic. The headline metric
was reassuring; the companion metric found the problem. Running the full
metric set even when the marquee number looks fine is the lesson, and it
is Chapter 4's "latency never travels alone" made operational.

## Diagrams to Include

1. **Figure 9-1 — Shadow data flow.** Call logs → flat capture records →
   mapping layer (sticky rules annotated) → policy engine replay →
   per-call results → report. One dotted line separating "your existing
   systems" from "kit components." The figure should make visually
   obvious that live traffic is never touched.
2. **Figure 9-2 — The four-week plan.** A timeline with the two decision
   diamonds: end of week 1 (mapping valid? if not, fix before scaling)
   and end of week 4 (good-enough bars met? if not, extend window). The
   bars listed beside the second diamond.
3. **Figure 9-3 — Good-enough criteria card.** The four thresholds
   (≥500 calls/one workflow/≥2 weeks; <10% dropped; flags hand-verified
   with FP rate documented; median stable ±1 turn) as a checklist card —
   the book's third extraction artifact, designed to be stapled to a
   pilot charter.
4. **Figure 9-4 — What shadow mode can and cannot see.** Two columns over
   the metric set: measured directly vs. synthesized/unavailable (ATR-01
   envelopes, Tier A artifacts without forensics flags, covert agents).
   The honest-boundary figure, repeated deliberately from Chapter 4's
   card in pilot-specific form.

## Operational Guidance

- **Charter it as a measurement, not an initiative.** One page: workflow,
  window, sample target, the four good-enough bars, the decision menu,
  and the sentence "no vendor or call-handling changes result from this
  pilot." That sentence is what makes approval easy and participation
  honest.
- **Keep the vendor list out of the first report's headline.** The
  pilot's product is a traffic baseline, not a scoreboard. Per-vendor
  breakdowns belong in the appendix and in Chapter 13's conversations —
  leading with them turns a measurement into an accusation before the
  false-positive review has even been socialized.
- **Put the compliance analyst in the hand-verification loop from day
  one.** The person who will later defend the data should be the person
  who read the flagged calls. Borrowed credibility does not survive
  hostile questions; earned credibility does.
- **Schedule the week-4 decision meeting when you charter.** Pilots
  without a pre-scheduled decision date produce reports that circulate
  unread. The calendar invite is the governance mechanism.

## Implementation Guidance

1. **Validate ten records before mapping ten thousand.** Schema-validate a
   hand-built sample, run it through the measurement script, and read the
   per-call output against the source calls. Every hour here saves a
   week-3 discovery that the baseline is artifact.
2. **Version the mapping code and freeze it for the window.** The mapping
   layer is where every subtle bias lives (what counts as PHI-accessed,
   how turns are segmented). Changing it mid-window makes week-over-week
   stability uninterpretable — the same discipline Chapter 7 demanded for
   review-policy versions, applied to the pilot's own tooling.

## Key Takeaways

- A shadow evaluation replays your own recorded call traffic through the
  real policy engine, observe-only: no vendor changes, no live
  enforcement, no production risk — and produces the baseline every
  downstream decision in this book depends on.
- The kit is three small artifacts — a flat capture schema, a measurement
  script that owns the tricky mapping into the engine's contract, and a
  report generator/template — engineered for a four-week, one-workflow
  pilot of 500–2,000 calls.
- Actionability has stated bars: sample size and duration, mapping
  coverage, hand-verified flags with a documented false-positive rate,
  and week-over-week stability. Miss a bar and the honest move is
  extending the window, not softening the claim.
- Shadow data measures observable disclosure behavior; it synthesizes
  ATR-01, usually lacks voice-artifact flags, and cannot see covert
  agents. Pilot numbers are measurements, never certifications — put the
  caveats in the report verbatim.
- The pilot's design is political as much as technical: bounded cost,
  no enemies made, a decision forced at week four, and numbers that
  replace anecdotes in every argument that follows.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Tier 0 Shadow Pilot Kit (schema, script, template) | Throughout | — (this chapter) |
| Sticky disclosure mapping / nested governance block | The kit; mapping failure example | Chapter 8 |
| Full Tier 0 metric set | Executive summary | Chapters 4, 15 |
| CAS tier distribution | Week 3 | Chapter 15 |
| Good-enough criteria | Running it well; Figure 9-3 | Chapter 14 |
| ATR-01 synthesis limit; Tier A availability | What shadow data cannot say | Chapters 6, 12 |
| Measurements-not-certifications rule | Throughout | Chapters 14, 18 |
| Integration ladder (Tier 0 → 1) | Week 4 decision menu | Chapter 13 |

---

*Next — Chapter 10, Policy Enforcement: what changes when you stop only
watching — graduated responses, the deterministic decision path, and the
retirement of disconnect-on-detect.*
