# Chapter 17 — Governance

*Part IV: Enterprise Adoption*

---

## The Champion Leaves

Eighteen months into a successful deployment, the operations director
who carried this program from pilot charter to standing regime — the
person who read the flagged calls, held the one-axis rule, corrected
the first certification misreading personally — accepts a job at
another payer.

What happens next is the truest audit of governance the program will
ever receive. In one version of the story, the quarterly review meets
anyway, because its four questions belong to a committee, not a
person; the enforcement thresholds hold, because they live in
versioned configuration with a change process; the review queue's
refute rate is watched, because instrument health has an owner by
role; and the framework-version upgrade that lands two months later is
evaluated by the same written process that evaluated the last one. In
the other version, the dashboard goes stale, a well-meaning manager
"tunes" the phrase list without reading Chapter 7, a vendor's
certification claim goes uncorrected, and eighteen months of earned
discipline evaporates into the institutional memory of "that thing
Sam used to run."

Everything in this book so far has been about building the machine.
This chapter is about making the machine survive its builders —
which is what governance actually means.

---

## Executive Summary

Governance for this program is four structures and three disciplines.

**The structures.** A **decision body** — typically a standing AI
communications governance committee, or an existing AI governance or
model-risk committee carrying this as a charter item — that owns the
policies, thresholds, and the quarterly review's decision authority.
An **operating ownership map** — every artifact this book created
(charter templates, enforcement configuration, mapping code, the
metric one-pager, the risk register entry, the seam map) assigned to
a *role*, never a person. The **review operation** — Chapter 7's
human-review SOP as a staffed, measured, standing function with its
dispositions feeding both vendor management and rule-change
decisions. And an **external interface** — who speaks for the
program to vendors, counterparties, auditors, and (eventually)
regulators, with the boundary sentences (measurements, not
certifications; mapped, not certified) as controlled language.

**The disciplines.** **Version governance**: the deterministic
engine's property that policy change is visible change (Chapter 7)
becomes an obligation — every policy, threshold, mapping, and
framework-version change is proposed, reviewed, dated, announced,
and stamped, with the zero-false-positive merge invariant as the
model for how change bars should be written. **Evidence-based
change**: the same standard the framework applied to its own phrase
list — bring error economics, not anecdotes — applied to every
proposed tuning of thresholds, routing, or enforcement rungs.
**Succession by artifact**: the program's knowledge lives in its
written instruments (the charters, conventions, playbooks, and this
book's extraction cards), reviewed on a calendar, so that the
champion's departure is an org-chart event rather than a program
event.

The chapter also settles a doctrine the book has been building
piecemeal: **receiving-side conduct governance** — the disclosure
prompt scripts, the don't-volunteer-PHI rule, the
never-punish-disclosure audit — collected into one owned policy,
because Chapters 1, 6, and 10 each established a piece of the truth
that your own floor's behavior is the incentive structure vendors
optimize against.

## Why It Matters

Every mechanism in this book eventually reduces to a decision
someone must have the authority to make: what threshold routes to
review, which vendor conversation escalates, whether the framework
upgrade ships, what the press-facing sentence says. Programs fail at
these joints not for lack of good options but for lack of a named
decider — or worse, for having the decision made by whoever showed
up with the strongest opinion, which is how a phrase list gets
"tuned" into a false-accusation machine by someone who never saw the
corpus numbers.

Governance is also what makes the program's *external* posture
durable. The boundary sentences that protect the program —
measurements not certifications, mapped not certified, voluntary
baseline not standard — are exactly the sentences most likely to be
eroded by enthusiastic retelling in sales decks, board updates, and
conference panels. Controlled language survives only where someone
owns it. The framework's own materials model this discipline
relentlessly (every overclaim pre-empted in its own documentation);
an adopting organization needs an owner for the same hygiene.

And governance is the answer to the register's last column: Chapter
16 assigned owners and review dates; this chapter is where owners
get authority, calendars, and successors.

## The Decision Body

**Charter it narrow.** The committee owns: the enforcement policy and
its thresholds (Chapter 10's ladder configuration); metric-station
promotions (Chapter 15 — a number entering vendor conversations or
contracts is a committee act); framework-version adoption (Chapter
5's adopt-by-version, exercised); review-SOP changes and the merge
bar for any detection-rule expansion; the boundary-language register;
and the annual tabletop's findings. It explicitly does *not* own
call-by-call operations (the floor's), vendor negotiations
(procurement's, informed by the data), or the audit store
(compliance's) — a governance committee that operates things governs
nothing.

**Compose it from the roles that already own artifacts.** The
five pilot roles matured: sponsor-executive (chair), operations
lead, compliance/audit, platform owner, vendor management — plus
counsel on call for the paper seams. Rotate people; preserve seats.

**Make its rhythm the program's heartbeat.** The quarterly metrics
review (Chapter 15's four questions) is the standing agenda;
decisions leave in writing with effective dates; the annual cycle
adds the tabletop (Chapter 16), the register refresh, the artifact
review (below), and the framework-version horizon scan.

## Version Governance, End to End

The program runs on five versioned things — the framework release,
the engine, the policy/threshold configuration, the mapping code,
and the review SOP — and one rule covers them all: **no change
without a proposal, an evidence standard, an effective date, and a
stamp.**

The framework's own change discipline is the model worth copying
into local policy. Its detection-rule bar — candidates merge only
with zero measured false-positive risk — is a *written, testable
standard* that converts an argument ("I think this phrase is
suspicious") into a measurement obligation. Local change bars should
be written the same way: a threshold change proposal must state the
distribution it was derived from and the stations affected; a
mapping change must re-run the parity replay and re-baseline; an
enforcement-rung activation must show the preceding rung's
confirmed/refuted data (Chapter 10's metering).

Framework upgrades get the fullest treatment, because they arrive
from outside: diff the release against the adopted version; classify
changes (schema, controls, scoring, tooling); re-run the CTS parity
suite; re-baseline any metric whose computation changed — with the
change date annotated on every affected trend (Chapter 15's version
registry absorbing it); and adopt by explicit committee decision
with a rollback point. An organization that cannot say which
framework version it is running has quietly returned to adopting by
pointer — the thing Chapter 5 warned was ungovernable.

## The Review Operation and the Floor Policy

Two standing operations need permanent governance homes.

**The review queue** (Chapter 7's SOP) graduates from pilot-era
procedure to a staffed function with a service standard: queue
latency, disposition rates, and the refute rate reported to the
committee as instrument health. Its governance risks are drift
(reviewers developing local doctrine that diverges from the SOP —
countered by periodic calibration sessions on shared samples) and
dilution (Chapter 7's warning — every "just also route X" proposal
comes to the committee with error economics or not at all).

**The receiving-side conduct policy** — assembled here from its
scattered pieces into one owned document: the disclosure prompt
script and its warm framing (Chapter 10); the don't-volunteer-PHI
floor rule (Chapter 6's PDX-01 reading); the disposition flags
(Chapter 1's homework, still running as the early-warning layer);
and the quarterly never-punish-disclosure audit (Chapter 10's
comparison of disclosed vs. concealed call outcomes). It is owned by
operations, reviewed by the committee, and trained like any other
floor procedure — because it *is* one, and because it is the half
of the incentive structure the organization controls unilaterally.

## Real-World Examples

*(Composites, per the book's convention.)*

**The tuning that got stopped.** A new operations manager, six weeks
in, proposes adding a dozen "obvious" phrases to the deception
detector after reading a frustrating transcript. The proposal
process — not a person — stops it: the change bar requires measured
false-positive economics, the corpus numbers get re-presented, and
the manager's real problem (a vendor's evasive-but-unmatched
deflection style) routes correctly into the review queue's
escalation path and a Rung 4 conversation. The system absorbed
exactly the well-meaning pressure that destroys ungoverned
detection rules — and the manager, given the evidence standard,
became its advocate.

**The upgrade that would have silently moved a metric.** A framework
release adjusts scoring behavior. The upgrade process's re-baseline
step catches that quarter-over-quarter CAS tier mixes would shift
for computation reasons, not conduct reasons; the trend lines get
their annotation before the dashboard moves; the vendor whose mix
"dropped" is never wrongly called. The counterfactual — an
unannotated shift triggering a Rung 4 conversation over a software
change — is the quiet catastrophe version governance exists to
prevent.

**The successor's first week.** The departing director's replacement
inherits: the committee charter, the artifact map with owners, the
one-pager archive with version registry, the extraction cards
pinned above the desk they now occupy, and a calendar that already
contains the next review, tabletop, and register refresh. Their
first committee meeting requires no archaeology. The program's
knowledge was never in anyone's head; that was the point.

## Diagrams to Include

1. **Figure 17-1 — The governance map.** The decision body at
   center with its owned decisions; the four operating functions
   (floor, review queue, platform, TPRM) around it with their owned
   artifacts; the external interface with its controlled language.
   Roles throughout, no names. The chapter's extraction artifact.
2. **Figure 17-2 — The version-governance pipeline.** The five
   versioned things flowing through propose → evidence → decide →
   date → stamp, with the framework-upgrade lane drawn in full
   (diff, classify, parity, re-baseline, adopt). The figure the
   platform owner pins up.
3. **Figure 17-3 — The annual rhythm.** Quarterly reviews, the
   annual tabletop, register refresh, artifact review, and horizon
   scan on one calendar wheel — governance as cadence, not
   crisis response.
4. **Figure 17-4 — Two successions.** The opening scenario's fork as
   a paired timeline: program-by-artifact vs. program-by-person,
   diverging at the departure date. The chapter's argument in one
   image, and the slide that sells governance budget.

## Operational Guidance

- **Prefer the existing committee with a new charter item over a
  new committee.** If an AI governance, model-risk, or data
  governance body exists, this program is a charter amendment and a
  standing agenda slot — Chapter 13's ride-existing-rails logic
  applied to decision rights. Stand up a dedicated body only where
  nothing suitable exists.
- **Write the boundary-language register this week.** One page:
  the sentences the organization says about this program
  (measurements not certifications; mapped not certified; voluntary
  baseline; the framework's own status columns) and the sentences
  it does not. Circulate to everyone who presents externally. This
  is the cheapest governance artifact in the book and the one that
  prevents the most expensive class of error.
- **Calibrate the reviewers quarterly.** Shared-sample sessions
  where all reviewers disposition the same calls, with divergence
  discussed against the SOP. Review quality is a governed property,
  not an assumed one — and the calibration session is where SOP
  ambiguities surface while they are cheap.
- **Rehearse succession before you need it.** Once a year, have the
  artifact map's owners each answer one question in writing: "could
  your successor run this from the documents?" Every "mostly" is a
  documentation ticket. The champion's departure should be the
  audit you already passed.

## Implementation Guidance

1. **Encode decision rights where the decisions execute.** The
   committee's authority over thresholds and versions should be
   enforced by the systems themselves — change-review requirements
   on the enforcement configuration repository, deployment gates
   requiring the parity replay, dashboard annotations drawn from
   the version registry. Governance that lives only in a charter
   document is advisory; governance encoded in the change pipeline
   is real.
2. **Archive committee decisions as the program's case law.** Each
   written decision (with its evidence, date, and dissents if any)
   joins a searchable record. Two years in, the answer to "why is
   the threshold 0.75 here when the framework default suggested
   review at that line?" should be a retrievable decision, not a
   shrug — the same evidence-not-conclusions discipline (Chapter
   12), applied to the program's own choices.

## Key Takeaways

- Governance is four structures — a narrowly-chartered decision
  body, an ownership map by role, the review operation as a
  standing function, and a controlled external interface — plus
  three disciplines: version governance, evidence-based change,
  and succession by artifact.
- The change rule covers all five versioned things: no change
  without a proposal, an evidence standard, an effective date, and
  a stamp. The framework's own zero-false-positive merge bar is the
  template for writing local change bars as testable standards.
- Framework upgrades are governed events: diff, classify, parity
  replay, re-baseline with annotated trends, explicit adoption
  decision. Adopting by pointer is ungovernable; version drift is
  how vendors get wrongly accused by software changes.
- Receiving-side conduct — prompts, PHI discipline, disposition
  flags, the never-punish-disclosure audit — is one owned policy,
  because your floor's behavior is the half of the incentive
  structure you control completely.
- The program's knowledge lives in artifacts on a review calendar,
  not in champions. The departure of the person who built it is
  governance's true audit — design to pass it.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Policy versioning as visible change | Version governance | Chapters 7–8, 10 |
| Zero-false-positive merge invariant | Change bars | Chapter 7 |
| Human-review SOP; calibration; dilution warning | Review operation | Chapter 7 |
| CTS parity replay on upgrade | Version governance | Chapters 8, 13 |
| Metric stations; version registry | Committee decisions | Chapter 15 |
| Enforcement-rung metering | Change bars | Chapter 10 |
| Receiving-side doctrine (consolidated) | Floor policy | Chapters 1, 6, 10 |
| Boundary language (measurements/mapped/voluntary) | External interface | Chapters 5, 9, 19 |
| Risk-register owners and review dates | Why it matters | Chapter 16 |

---

*Part IV complete. Next — Part V opens with Chapter 18, Industry
Adoption: beyond one organization — network effects, who moves
first, and how a voluntary baseline spreads.*
