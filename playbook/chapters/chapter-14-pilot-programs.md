# Chapter 14 — Pilot Programs

*Part IV: Enterprise Adoption*

---

## The Kickoff That Almost Went Wrong

*The following pilot narrative is a composite, assembled from the
framework's pilot-kit design and the failure modes it was built to
avoid — not an account of any specific organization.*

The kickoff meeting for a payer's first NHID-Clinical pilot draws
fourteen people, which is the first warning sign. The sponsoring VP
opens with a slide titled "AI Caller Compliance Program — Phase 1," and
the room begins doing what rooms do to programs: legal wants vendor
notification letters reviewed, procurement wants the pilot tied to a
sourcing decision, one director wants real-time blocking "since we're
building it anyway," and someone asks whether the pilot will "certify"
their current vendors.

The operations director who actually read the pilot kit interrupts
politely with three sentences that save the quarter. "This is a Tier 0
shadow evaluation: observe-only, on our own historical logs, no vendor
contact, no call handling changes — so most of this room is getting an
FYI, not a work assignment. It produces measurements of our traffic,
not certifications of anyone. And it ends in four weeks with a written
decision about what, if anything, we do next."

The meeting shrinks to five people — sponsor, operations lead, data
engineer, compliance analyst, and a call-center supervisor — which is
the size the work actually has. A year on, this
organization runs conformance checking on live traffic with contract
exhibits at two vendors. Asked what made it work, the operations
director gives the answer this chapter exists to generalize: "We
refused to let the pilot be a program until it had earned it with
data."

---

## Executive Summary

A pilot program is the organizational vehicle that carries the Tier 0
shadow evaluation (Chapter 9) into enterprise decision-making — and,
when its data licenses it, forward through the staged expansions: wider
workflows, live post-call monitoring (Tier 1), vendor engagement, and
eventually the 90-day observe-only shadow-partner arrangement the
framework's materials describe for working directly with cooperative
counterparties. The framework's own adoption theory is embedded in the
pilot's shape: start small (one workflow, 500–2,000 calls, four weeks),
impose nothing, measure honestly against stated good-enough bars, and
let every expansion be licensed by the previous phase's data rather
than by enthusiasm.

This chapter supplies what the kit deliberately doesn't: the
organizational wrapper. The right team (five roles, not fourteen
seats), the right charter (one page, with the no-changes sentence and
a pre-scheduled decision date), the phase-gate structure (each phase
ends in a written go/expand/hold/stop decision), the socialization
sequence (results travel to compliance and procurement *after*
hand-verification, with false-positive rates attached), and the
boundary discipline — pilots produce measurements, never
certifications; per-vendor results are appendix material until
verified; and a pilot that misses its good-enough bars extends its
window rather than softening its claims.

The chapter also names the four ways healthcare pilots die —
scope inflation at kickoff, the certification misreading, the
skipped-verification credibility collapse, and the report that
circulates without a decision — and builds the program structure
specifically against them.

## Why It Matters

The gap between a successful shadow evaluation and a changed
organization is entirely organizational, and it is where most
governance initiatives actually fail. The kit is designed to yield
honest numbers from four weeks of work; it cannot guarantee that anyone
acts on them, that the numbers survive their first hostile meeting, or
that the pilot isn't strangled at kickoff by the program apparatus of a
company that has forgotten how to do small things. Enterprise adoption
is a sequence of earned expansions, and the pilot program is the
mechanism that does the earning.

There is also an external reason this chapter matters now: the
framework itself is at the stage where shadow-evaluation partners are
its named next step — the ecosystem's production evidence is limited,
and the organizations that run disciplined early pilots are not just
informing their own decisions but generating the first real-world
evidence base the whole field will argue from. Pilot discipline is,
for the moment, a public good.

## The Program Structure

**Five roles.** Sponsor (owns the decision the pilot informs, and the
calendar invite for it); operations lead (owns the charter and the
boundary discipline); data engineer (owns capture, mapping, and the
mapping-version freeze); compliance analyst (owns hand-verification
and the false-positive record — the person who will defend the data
must be the person who read the calls); floor liaison (the supervisor
who explains what the flagged calls actually were). Everyone else is
informed, not assigned.

**One-page charter.** Workflow and window; sample target; the four
good-enough bars quoted verbatim; the decision menu (advance to
Tier 1 / open vendor conversations / expand sample / stop, with
reasons); the decision date; and the two sentences that do the
political work — *no vendor or call-handling changes result from this
pilot* and *pilot numbers are measurements of our own traffic, not
conformance certifications of any party.*

**Phase gates, each ending in writing.** Phase one is Chapter 9's four
weeks, gated by the good-enough bars. Phase two — only if licensed —
expands along exactly one axis at a time: another workflow, *or* a
longer window, *or* Tier 1 live post-call monitoring on the already-
measured workflow. One axis, because attribution dies when two things
change at once. Phase three is vendor engagement with verified data
(the Chapter 13 questionnaire-and-exhibit machinery), and phase four
is the standing program — at which point Chapter 15's metrics regime
and Chapter 17's governance take over and the "pilot" designation
retires. The 90-day shadow-partner arrangement — observing a
cooperative vendor's traffic with their participation, still
observe-only — slots in wherever a counterparty's willingness makes
it available, and is the highest-value phase-three form because both
sides see the same evidence.

**The socialization sequence.** Results move outward in verified
form only: hand-check first, false-positive rate documented, then
compliance, then procurement, then — as decisions, not data dumps —
vendors. The report template's structure (metrics, tier distribution,
top violations, verification results, recommendation) is the traveling
document; the raw per-vendor appendix stays home until phase three.

## The Four Deaths, and Their Preventions

**Death by kickoff.** The fourteen-person meeting, the "Phase 1"
slide, the real-time-blocking rider. Prevention: the charter's
no-changes sentence, the five-role cast, and the Tier 0 framing —
observe-only is not a limitation to apologize for but the design that
makes the pilot unstoppable, because there is nothing in it for
anyone to veto.

**Death by certification misreading.** Someone — a vendor in a
renewal, an executive in a board deck — describes pilot results as
vendors "passing" or "failing" NHID-Clinical. The kit's own language
forbids this, and the misreading is not cosmetic: a "certification"
claim imports legal and reputational weight the measurements cannot
carry, and its collapse takes the pilot's real findings with it.
Prevention: the charter sentence, repeated in every report footer,
and a sponsor briefed to correct the misreading *personally* the
first time it appears.

**Death by unverified flags.** The pilot's most dangerous week is the
one where the first violation table exists but no one has read the
underlying calls. Numbers escape, a vendor is named in a meeting, the
false positives surface later — and the pilot's credibility dies
retroactively, taking the true positives with it. Chapter 7 explained
why false positives are structural; the prevention is sequence:
verification before circulation, rate documented, every table
footnoted with it.

**Death by undecided report.** The report circulates, is praised, and
nothing happens; six months later the effort is remembered as "that
study." Prevention is the pre-scheduled decision meeting with the
sponsor's name on it, and a decision menu on the charter so "decide"
has a bounded meaning. A pilot that ends in a documented *stop* —
with reasons — is a success; a pilot that ends in silence is a
failure regardless of its findings.

## Real-World Examples

*(All composites, per the chapter's opening note.)*

**The expansion that waited.** Phase-one data shows prior-auth calls
with materially worse disclosure behavior than claims-status calls.
The temptation is immediate: expand to all workflows and go to
vendors now. The operations lead holds the one-axis rule — phase two
extends the prior-auth window to six weeks first, and the stability
check (median within one turn, week over week) turns out to matter:
weeks four and five include a vendor's platform migration that
temporarily degrades disclosure. Data with that anomaly *averaged in*
would have overstated the case; caught as instability, it becomes a
dated annotation and the vendor conversation, when it comes, is
unimpeachable.

**The stop that was a success.** A regional payer's pilot finds low
automation on the measured workflow and strong disclosure among what
exists. The decision meeting records *stop, revisit in twelve months
or on volume signal* — with the capture pipeline and mapping code
archived and the disposition flags left running as the early-warning
system. Cost: a few analyst-weeks. Asset: a baseline, a rehearsed
measurement capability, and a governance record that the question was
asked and answered. This ending is underrated, and this book insists
it be available.

**The partner pilot.** A payer and a cooperative voice-AI vendor run
the shadow arrangement together on the vendor's traffic: same
observe-only rules, both parties seeing the same replay results. The
vendor fixes two conformance regressions before any contract
language exists; the payer's eventual exhibit thresholds are set from
jointly-witnessed data and sign without dispute. The example is the
adoption thesis in miniature — evidence shared beats evidence
brandished — and it is the configuration the framework's
shadow-partner language is designed for.

## Diagrams to Include

1. **Figure 14-1 — The phase-gate map.** Four phases with their
   gates, each gate labeled with its licensing evidence (good-enough
   bars; stability; verified data) and its written-decision
   requirement. The one-axis rule annotated on the phase-two
   expansion arrows.
2. **Figure 14-2 — The five-role cast.** Roles with their owned
   artifacts (charter, mapping versions, false-positive record,
   decision calendar) — and, drawn deliberately outside the boundary,
   the informed-not-assigned crowd from the kickoff.
3. **Figure 14-3 — The four deaths.** A quadrant of the failure
   modes, each with its prevention mechanism from the program
   structure. Designed as the pre-kickoff briefing slide.
4. **Figure 14-4 — The socialization sequence.** Results flowing
   outward through verification → compliance → procurement → vendors,
   with the false-positive rate attached at the first arrow and the
   per-vendor appendix held until the last. The figure that prevents
   death number three.

## Operational Guidance

- **Size the kickoff to the work.** Five roles assigned, everyone
  else informed in writing. If your organization cannot hold a
  five-person pilot, that fact is itself governance information —
  Chapter 17's structures exist partly to create protected space for
  small, evidence-producing efforts.
- **Put both boundary sentences in every artifact.** No-changes and
  measurements-not-certifications, in the charter, the report footer,
  and the sponsor's talking points. Boundary discipline is cheap at
  the start and unbuyable after the first misreading circulates.
- **Treat the stop outcome as first-class.** Write it into the
  decision menu with dignity — *stop, with reasons, with revisit
  criteria* — and the pilot stops being a career bet, which is
  exactly what makes honest findings safe to report.
- **Offer the partner configuration early.** If any vendor
  relationship is warm enough for the joint shadow arrangement, take
  it — jointly-witnessed evidence collapses the adversarial framings
  that consume most of phase three, and the vendor's early fixes are
  adoption's cheapest wins.

## Implementation Guidance

1. **Archive the pilot as a capability, not a report.** Whatever the
   decision, preserve the mapping code (versioned), the charter
   template, the verification procedure, and the baseline numbers as
   a package. The second pilot — another workflow, another year,
   another regulation — should cost half the first; organizations
   that keep only the PDF pay full price every time.
2. **Feed the framework's evidence base as your data allows.** The
   ecosystem's production evidence is limited, and the framework's
   materials actively seek shadow-evaluation partners. Where policy
   permits, share de-identified, aggregate findings — metric
   distributions, not calls — through the project's channels. Early
   pilots are writing the literature the field will cite; write
   yours down.

## Key Takeaways

- The pilot program is the organizational wrapper that turns the
  four-week shadow evaluation into earned, staged expansion: phase
  gates with written decisions, one expansion axis at a time, and
  every advance licensed by the previous phase's data.
- Structure is five roles and a one-page charter carrying the two
  boundary sentences — no changes result, and measurements are not
  certifications — with the decision meeting scheduled before the
  data exists.
- The four deaths — kickoff inflation, certification misreading,
  unverified flags, undecided reports — are all preventable by
  design, and the prevention mechanisms cost almost nothing at
  charter time.
- A documented stop is a successful pilot outcome; an undecided
  report is a failure regardless of findings. Archive the capability
  either way.
- Early disciplined pilots are generating the field's first
  real-world evidence; the partner configuration — joint, observe-
  only, same evidence on both screens — is the strongest form, and
  sharing aggregate findings is a contribution the ecosystem
  currently needs more than it needs advocacy.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Tier 0 Shadow Pilot Kit; good-enough bars | Program structure | Chapter 9 |
| 90-day shadow-partner arrangement | Phases; the partner pilot | Chapter 18 |
| Measurements-not-certifications rule | Boundary discipline | Chapters 9, 18 |
| False-positive verification discipline | The four deaths | Chapter 7 |
| Stability criterion (±1 turn) | The expansion that waited | Chapters 9, 15 |
| Tier 1 progression | Phase gates | Chapter 13 |
| Questionnaire and contract stages | Phase three | Chapter 13 |
| Framework maturity (partners sought) | Why it matters | Chapters 5, 18 |

---

*Next — Chapter 15, Metrics: the standing measurement regime — the
metric tree, CAS as an operational instrument, thresholds that
survive contact with Goodhart, and dashboards someone actually
owns.*
