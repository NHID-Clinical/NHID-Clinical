# Chapter 15 — Metrics

*Part IV: Enterprise Adoption*

---

## The Quarterly Review

Eight months after the pilot retired its designation, the standing
review meets: operations, compliance, vendor management, and the
platform owner, around one dashboard. The agenda is four questions,
asked in the same order every quarter.

*Is the window shrinking?* Median impersonation latency on monitored
workflows, in turns, with the distribution beside it — and the
never-disclosed rate printed in the same font size as the median,
because the chair learned Chapter 4's lesson and enforces it.

*Is anything moving under the surface?* CAS tier mix quarter over
quarter; pre-disclosure PHI exposure by workflow; escalation honor
rate by vendor. One vendor's tier mix has slid — more Conditional
Trust, less Verified — with no single violation spiking. The
composite catches what no rule fired on; a review-queue sample is
commissioned before lunch.

*Are our own instruments healthy?* The refute rate from the human
review queue (drifting up would mean the rules are accusing honesty
again); outcome-code-4 counts from the audit pipeline (capture decay);
mapping and policy versions in force, with change dates against every
trend line.

*And what are we going to do about it?* Two decisions leave the room
in writing: the sliding vendor gets a data-first conversation with
trace excerpts attached, and a proposed contract threshold — floated
by procurement last quarter — is deferred again, because the
distribution it would bind is still moving more than a turn per week
on one workflow.

Forty minutes end to end. Nobody debated an anecdote. That meeting —
its four questions, its printed tails, its version stamps, its
deferred threshold — is a metrics regime working, and building it is
this chapter.

---

## Executive Summary

The framework's metric system has a deliberate shape: one headline
phenomenon (impersonation latency), four companions that keep it
honest (first-turn disclosure rate, never-disclosed rate,
pre-disclosure PHI exposure, escalation honor rate), per-control
violation rates beneath, and one composite — the Call Authorization
Score — rolling conduct into a per-call number bucketed into five
operational tiers: ≥0.90 Verified Trust, ≥0.75 Conditional Trust,
≥0.50 Review Required, ≥0.20 Denied/Degraded, and Hard Denial below.
The CAS composes identity-assertion strength, non-human operational
confidence, and event completeness — which means it degrades not only
when conduct is bad but when *evidence* is thin, a design choice that
makes audit quality a scored property rather than a footnote.

This chapter turns that system into a standing regime, and its
organizing principle is the difference between the two things a
metric can be: an **instrument** (something you read to learn) and a
**target** (something someone is paid to move). Every pathology this
chapter guards against — and the reason the book has deferred
"put CAS in the contract" three times — comes from promoting a metric
from instrument to target before understanding what it will do under
pressure. The rule this chapter finally states: measure first,
publish internally second, threshold last — and when a metric does
become a target, its companion metrics become your tamper-detection,
because a gamed headline number distorts its companions in
predictable ways.

The regime's mechanics: distributions over averages, tails printed
with medians, version stamps on every trend, instrument-health
metrics (refute rate, outcome-code-4 counts, mapping coverage)
reviewed alongside traffic metrics, and a quarterly cadence with a
fixed four-question agenda — because a metrics regime is a meeting
before it is a dashboard.

## Why It Matters

Numbers are the only language in which this problem stays managed.
Part I showed what unmeasured looks like; Chapters 9 and 14 produced
the first measurements; but a baseline is a photograph, and the
phenomenon moves — vendors change platforms, prompts regress, new
workflows automate, contracts turn over. Only a standing regime
notices, and only a disciplined one notices *correctly*: the
quarterly review's sliding-vendor catch came from the tier mix, not
from any violation alarm, and its threshold deferral came from the
stability criterion, not from caution as a mood.

The regime is also the enforcement stack's foundation. Chapter 10's
Rung 4 — the calm, evidenced, relationship-level consequences where
most enforcement should live — is only as strong as the metrics
behind it. A vendor conversation opened with "your tier mix slid
eleven points this quarter, here are the traces" is procurement with
gravity; the same conversation opened with "our reps feel like your
bot got worse" is Chapter 1 again. And Chapter 19's regulatory
conversations consume the same feed: transparency obligations and
audit-retention requirements are answered with distributions and
records, not attestations.

Finally, the metrics regime is where the organization's honesty gets
tested continuously. Every temptation the book has warned against —
averaging away the censored tail, circulating unverified counts,
letting a threshold precede its baseline — recurs quarterly, forever.
The regime is the institutional form of resisting them.

## The Metric Tree

**The headline: impersonation latency** — median and distribution, in
turns, per workflow. Never alone: the never-disclosed rate rides
beside it always (right-censored calls are not large values; they are
a separate fact), and the reporting convention from Chapter 4 is now
policy — *no latency figure without its tail.*

**The four companions** each guard a distinct blind spot. First-turn
disclosure rate is the design-choice indicator (Chapter 4's two-hump
world: vendors either open with disclosure or don't). Never-disclosed
rate is the censoring guard. Pre-disclosure PHI exposure converts
duration into harm proxy — the metric that distinguishes an idle
window from a leaking one. Escalation honor rate watches the exit
door, and it is the companion most likely to catch a problem the
headline misses (Chapter 9's null-result example).

**Per-control violation rates** (IDG, PDX, DBC, EIT) are the
diagnostic layer — where a moving companion gets localized to a
conduct class, with trace excerpts one query away (Chapter 12's
indexes earning their keep).

**The composite: CAS.** Three factors — identity-assertion strength,
non-human operational confidence, event completeness — multiplied
into a per-call score, tiered for routing. Two properties deserve
respect. It *reaches the middle*: calls with no fired rule but thin
assertion and weak evidence land in Review Required, which is the
mechanism behind both the review queue's routing (Chapter 7) and the
quarterly review's sliding-vendor catch. And it *prices evidence*:
event completeness in the composition means a vendor cannot improve
its score by logging less — thin traces sink tiers. When someone
proposes simplifying the dashboard to "just the CAS average," the
answer is that a composite exists to be decomposed; the average is
where its information goes to die.

**The instrument-health layer** — the regime's least glamorous and
most diagnostic tier: review-queue refute rate (the rules' measured
false-accusation tendency, Chapter 7's loop), outcome-code-4 counts
(capture decay, Chapter 12's internal alarm), mapping coverage and
drop rates (Chapter 9's <10% bar, now continuous), and the version
registry — engine, policy, mapping, review-policy — against every
trend line. An organization that reviews traffic metrics without
instrument metrics is reading a gauge it never calibrates.

## From Instrument to Target, Carefully

The hardening path for any metric in this system has four stations,
and skipping one is how metrics regimes injure themselves.

**Station one: private instrument.** The metric is read by its owners,
version-stamped, verified against hand-checks. Duration: until stable
by the Chapter 9 criterion.

**Station two: internal signal.** The metric appears in the quarterly
review and vendor-management prep; people begin to *react* to it,
which is the first gaming pressure — internal teams optimizing what
leadership watches. The companion metrics start their second job here:
tamper detection. A first-turn disclosure rate that rises while
pre-disclosure PHI exposure holds flat is improvement; one that rises
while assertion texts get vaguer (CAS identity factor drifting down)
is wording games.

**Station three: shared expectation.** The metric enters vendor
conversations and questionnaire follow-ups — data-first, trace-backed,
still not contractual. Vendors now optimize toward it, which is the
*point* — Chapter 10's incentive machinery — but optimization pressure
demands the full companion set travel with the number, or you will
get exactly what you asked for and nothing that you meant.

**Station four: contractual threshold.** Only now — with a stable
baseline, a tamper-detection layer, dispute machinery (replayable
traces, version stamps) and Chapter 13's stage-three language — does
a number enter a contract, and even then as a floor with a review
clause, not a ceiling to be raced to. The deferred threshold in the
opening scenario is this station working: the distribution was still
moving; the regime waited.

Goodhart's law is not a reason to avoid targets; it is a reason to
arrive at them in this order, with the companions armed.

## Real-World Examples

*(Composites, per the book's convention.)*

**The dashboard that hid the problem.** An early dashboard iteration
shows a single reassuring CAS average trending gently upward. A
skeptical analyst decomposes it: Verified Trust volume is growing
(one good vendor's traffic share), while a smaller vendor's tier mix
rots underneath. The average was true and useless. The fix — tier
mix by vendor, always — is why the regime's convention is
distributions over averages at every level, not just the headline.

**The wording game.** After disclosure language enters vendor
conversations (station three), one vendor's first-turn disclosure
rate jumps satisfyingly — while its identity-assertion factor drifts
down. The new opening: "This call may be recorded and handled by
automated systems." Technically a first-turn mention; substantively a
hedge. The companion caught it, the trace excerpts made the
conversation short, and the vendor's revised wording ("I'm an
automated assistant calling for...") restored both numbers. The
example is the tamper-detection thesis in one incident — and a
preview of why threshold language at station four specifies assertion
quality, not just timing.

**The refute-rate save.** Six months in, the review queue's refute
rate climbs from a documented baseline toward one-in-three. Instead
of quietly distrusting the queue, the instrument-health review treats
it as a signal: a mapping change (new transcription vendor,
different turn segmentation) had subtly shifted phrase-match
behavior. Rolled back, re-baselined, documented. The gauge got
recalibrated because the regime watches its gauges — the alternative
timeline ends with reviewers ignoring the queue and the queue's
credibility gone.

## Diagrams to Include

1. **Figure 15-1 — The metric tree.** Headline, companions,
   per-control diagnostics, composite, instrument-health layer — as a
   literal tree with each node annotated by the blind spot it guards.
   The chapter's master figure and extraction artifact.
2. **Figure 15-2 — CAS decomposition.** The three factors and the
   tier ladder, with the two design properties (reaches the middle;
   prices evidence) called out — and the "average is where information
   dies" warning as the caption.
3. **Figure 15-3 — The four stations.** Instrument → signal →
   expectation → threshold, with each station's entry criteria and
   its characteristic gaming pressure plus the companion that detects
   it. The Goodhart figure.
4. **Figure 15-4 — The quarterly one-pager.** A model dashboard page:
   latency with tail, tier mix by vendor, companions, instrument
   health, version registry, decisions box. Deliberately printable —
   the regime is a meeting before it is a dashboard, and the page is
   the meeting's agenda.

## Operational Guidance

- **Fix the four questions and keep the cadence.** Is the window
  shrinking; what's moving underneath; are the instruments healthy;
  what do we decide. Quarterly, forty minutes, decisions in writing.
  The agenda is the regime; the dashboard is its exhibit.
- **Write the reporting conventions as policy, not habit.** No
  latency without its tail; distributions over averages;
  version stamps on trends; refute rate on every review-queue
  citation. Conventions survive personnel; habits don't.
- **Assign every metric an owner and every owner a question.** The
  metric tree maps cleanly: operations owns the headline and
  companions, compliance owns instrument health and the refute rate,
  vendor management owns tier mix by counterparty, the platform owner
  owns versions. Unowned metrics decay into decoration.
- **Move one metric one station at a time.** The hardening path is
  per-metric, not per-regime — disclosure timing may reach station
  four while escalation honor is still at two. Promote deliberately,
  document the station, and never let a vendor conversation cite a
  number at a higher station than it holds.

## Implementation Guidance

1. **Build the one-pager before the dashboard.** The printable
   quarterly page (Figure 15-4) forces every convention — tails,
   decompositions, versions, decisions box — into one artifact that
   works without tooling. Automate it second; OpenTelemetry export
   (Layer 5) feeds whatever dashboard platform you already operate,
   and the alerting thresholds you set there should mirror the
   stations: page on instrument-health anomalies, report on traffic
   trends, never page on a probabilistic conduct signal.
2. **Snapshot quarterly, forever.** Archive each quarter's one-pager
   with its version registry as the regime's own audit trail. Two
   years in, the question "when did this trend start and what
   changed?" is answered by diffing snapshots — the same
   evidence-not-conclusions discipline Chapter 12 taught, applied to
   the measurement system itself.

## Key Takeaways

- The metric system is a tree, not a number: latency with its
  censored tail, four companions guarding four blind spots,
  per-control diagnostics, a composite that reaches the middle and
  prices evidence, and an instrument-health layer that calibrates the
  gauges themselves.
- CAS's three-factor composition means thin evidence sinks scores by
  design — audit quality is scored, not footnoted — and a composite
  exists to be decomposed; its average is where the information dies.
- Metrics harden along four stations — private instrument, internal
  signal, shared expectation, contractual threshold — and each
  promotion arms new gaming pressure that the companion metrics
  exist to detect. Never cite a number above its station.
- The regime is a meeting before it is a dashboard: four fixed
  questions, quarterly, decisions in writing, conventions as policy
  — no latency without its tail, distributions over averages,
  versions on every trend.
- Watch the instruments as closely as the traffic: refute rate,
  outcome-code-4 counts, and mapping coverage are the difference
  between reading reality and reading an uncalibrated gauge.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Full Tier 0 metric set | The metric tree | Chapters 4, 9 |
| CAS composition (three factors) and tiers | The composite | Chapters 6–7 |
| Review Required threshold (0.75) routing | The composite | Chapter 7 |
| Refute rate / false-positive discipline | Instrument health | Chapter 7 |
| Outcome-code-4 as capture alarm | Instrument health | Chapter 12 |
| Stability criterion; <10% drop bar | Stations; instrument health | Chapter 9 |
| Version stamps (engine/policy/mapping) | Throughout | Chapters 7–10 |
| Rung 4 data-first vendor conversations | Why it matters; examples | Chapters 10, 13 |
| OpenTelemetry (Layer 5) dashboards/alerts | Implementation guidance | Chapters 8, 12 |
| Contract threshold staging | Station four | Chapter 13 |

---

*Next — Chapter 16, Risk Management: the same system seen from the
CISO's chair — the risk register, what the framework retires, what it
carries as residual, and what it introduces.*
