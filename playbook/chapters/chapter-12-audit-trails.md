# Chapter 12 — Audit Trails

*Part III: Implementation*

---

## The Afternoon Dispute

Run Chapter 3's ninety-day dispute one final time — same orthopedic
group, same assertion that calls were made in its name, same
compliance officer. But this payer has spent Part III building what the
book has described, and the difference announces itself in her first
query.

She pulls the calls by provider NPI. For each one she retrieves: the
per-turn trace, showing exactly when disclosure occurred (or didn't) and
which PHI fields moved before it; the FHIR AuditEvent bundle, whose
milestones read like a story told in codes — session start, identity
disclosure with the first two hundred characters of the assertion text
preserved, authorization verification naming the NPI; and, for the calls
where a passport was presented, the full cryptographic evidence set —
the passport itself, the provider key as it existed at call time, the
verification result, the call-SID match.

Three calls carried valid delegations traceable to the group's own root
key — the group's billing vendor, authorized eight months ago, a fact
the group's practice manager confirms with one internal email. Two
calls carried no passport at all and disclosed at turn one as automated,
CAS in Review Required; the traces show the representative gated data
correctly. The dispute doesn't settle — it *resolves*, with each party
learning something true: the group, that its own vendor makes more calls
than it realized; the payer, that its gating held.

Total elapsed time: one afternoon. The difference between this
afternoon and Chapter 3's "unable to substantiate" is not better
investigators. It is that this time, the facts were *recorded in a form
built to answer questions* — which is the entire subject of this
chapter.

---

## Executive Summary

ATR-01 — every call produces a machine-readable trace — is the control
that converts the other four from assertions into checkable facts. This
chapter treats the audit layer as three nested artifacts and one
discipline.

**The per-turn trace** (the event schema's records, accumulated) is the
primary evidence: input payloads, the healthcare-governance block
(disclosure timestamp and assertion text, per-turn PHI flags, artifact
flags), escalation fields, session state transitions, and every policy
decision with its action, reason code, and policy version. Determinism
makes the trace *replayable* — the same trace re-evaluated yields the
same verdicts, which is what makes stored evidence disputable in the
constructive sense (Chapter 10's due process).

**The FHIR R4 AuditEvent bundle** renders conformance milestones in
healthcare's native audit vocabulary: one AuditEvent per milestone
(session start, identity disclosure, authorization verification, and
their siblings), typed with standard DICOM/FHIR audit codes, carrying
outcome codes that distinguish success, partial capture, and violation
— disclosure confirmed (0), timestamp-without-assertion-text (4),
never disclosed (8). The bundle exists so audit evidence lands in
systems compliance teams already operate, with the scope claim stated
exactly: validated against the FHIR R4 base specification — no named
implementation-guide conformance claimed.

**The cryptographic evidence set** (Chapter 11's retention preview,
formalized): for passport-bearing calls, retain the full passport, the
verifying key material as it existed at call time, the verification
result with scope checked, and the call-SID match — never a bare
`verified: true`.

**The discipline** is retention-by-question: store what future
questions need, in the form questions arrive — by NPI, by call, by
vendor, by control. Retention *duration* is deliberately deferred to
each organization's existing audit-log policy for comparable
administrative records; the framework sets the *contents*, not the
calendar.

## Why It Matters

Every earlier chapter's promises are drawn against this chapter's
account. Enforcement's due process (Chapter 10) is only as real as the
replayable trace behind each reason code. Authorization's
dispute-resolution power (Chapter 11) is only as real as the evidence
set retained. The metrics (Chapters 4, 15) are only as trustworthy as
the events they aggregate. And the regulatory mappings (Chapter 19) —
audit retention, transparency evidence, human-review documentation —
terminate here, in whether the records exist and can be produced.

Audit is also the layer with the least forgiving deadline. Controls can
be adopted incrementally and policies revised; evidence not captured at
call time is gone. The opening afternoon and Chapter 3's ninety days
differ by decisions made *months before either dispute arrived* — which
is why Chapter 8's implementation guidance ordered the spine before the
dashboard, and why this chapter's guidance is disproportionately about
what to decide now rather than what to buy later.

There is a subtler institutional payoff. Machine-readable audit changes
*who can ask questions*. When call conduct lives in per-turn records
with control-coded violations, the compliance analyst queries it like
any dataset — no more requesting call recordings and listening at 1.5×
speed. Questions get cheaper; cheap questions get asked; asked
questions surface problems while they are small. The audit layer's
quiet product is an organization that interrogates its own AI traffic
as routinely as its claims data.

## The Trace: Evidence at Turn Granularity

Everything the behavioral controls assert is positional — disclosure
*before* PHI, data *after* identity, escalation honored *when
requested* — so evidence must preserve position: the trace is per-turn
or it is insufficient. Chapter 8 covered the schema as contract; here
it matters as *record*: the disclosure timestamp's stickiness (state,
not event), assertion text preserved verbatim (the difference between
proving "a disclosure occurred" and proving *what was actually said* —
the quiet-composite example in Chapter 7 turned entirely on wording),
PHI flags enumerated per field per turn (the pre-disclosure exposure
metric's raw material), and every policy decision stamped with action,
reason code, and policy version (the enforcement audit trail inside
the call audit trail).

Two trace disciplines earn their keep in disputes. **Completeness is a
tested property** — the framework's canonical traces include the
missing-audit-field failure, and the CAS's event-completeness factor
means thin records *depress the trust score by construction*: an
incomplete trace is not a neutral gap but a scored deficiency. And
**call-SID binding threads everything** — turns to calls, calls to
bundles, delegations to calls; the missing-binding trace documents what
its absence costs: evidence that cannot be attached to the call it
describes.

## The FHIR Bundle: Speaking Compliance's Language

The emitter's design question was never "how should audit data look?"
— it was "where do healthcare compliance teams already look?" The
answer is FHIR R4, and the bundle maps conformance milestones onto
AuditEvent with standard typing: application-activity codes for
session lifecycle, security-alert typing for the disclosure milestone,
user-authentication typing for authorization verification, agents
modeling the three parties (the AI caller as requestor, the payer
system as destination, the provider organization on-behalf-of when an
NPI is supplied — carried with the standard US NPI system identifier).

The outcome codes deserve an implementer's attention because they
encode the framework's honesty at the record level: the disclosure
milestone distinguishes *confirmed* (timestamp and assertion text
both present), *partially captured* (timestamp without text — a
pipeline deficiency worth its own alert), and *violated* (no
disclosure before data). An audit record that can say "our capture was
incomplete" distinctly from "the agent misbehaved" prevents the
worst audit failure mode: pipeline gaps laundered into vendor
accusations.

The scope statement is repeated wherever the bundle is discussed, and
this book repeats it too: validated against the FHIR R4 base
specification only; no conformance to any named implementation guide
is claimed or implied. Compliance readers will ask; the answer is on
the record.

## The Discipline: Retain for the Question

The retention set for a disputed call (Chapter 11's preview, now the
canonical statement): (1) the full per-turn trace; (2) the FHIR bundle;
(3) for passport calls — the passport itself, (4) the verifying key
material *as of call time* (keys rotate; yesterday's verification is
only reconstructible with yesterday's key), (5) the verification
result including which scope was checked against which action, and
(6) the call-SID match. Six items, and the principle behind them:
**retain evidence, not conclusions.** Conclusions ("verified,"
"conformant," a CAS number) are recomputable from evidence; evidence
is not recoverable from conclusions. Every storage decision that
compresses records toward verdicts is borrowing against a future
dispute.

Duration stays with your existing audit-retention policy for
comparable administrative call records — a regulatory and contractual
question the framework explicitly declines to answer for you. What the
framework does answer is *queryability*: disputes arrive by provider
(NPI), incidents by call (SID), vendor management by traffic slice,
compliance by control ID. If those four access paths are not indexed,
the records exist without being able to answer anything on a deadline.

## Real-World Examples

**The pipeline gap that looked like a violation.** A vendor's calls
begin showing disclosure-timestamp-without-assertion-text — outcome
code 4, not 8. An organization without the distinction would have
opened a vendor conversation about disclosure failures; the trace
shows disclosures occurring and a transcription-field mapping dropping
the text. The fix is internal, the vendor never wrongly accused —
Chapter 7's false-accusation economics, prevented this time by a
record format that separates capture quality from conduct.

**The replay that settled the threshold argument.** A quarter after
an enforcement rollout, a vendor disputes a month of Review-Required
routings. The organization replays the month's traces against both
the current and prior policy versions, demonstrating the routings
followed the published threshold — and, incidentally, producing the
first useful dataset on how the threshold behaves at scale. The
dispute cost an afternoon of compute; the version stamps and stored
traces are why it wasn't a negotiation.

**The audit that improved the vendor.** A payer shares, with a
cooperative vendor, the FHIR bundles for the vendor's own degraded
calls — evidence-grade, milestone-coded, no interpretation attached.
The vendor's engineers localize their regression (a prompt change had
moved disclosure two turns later) in a day, because the evidence was
positional. Sharing audit *with* counterparties, rather than
brandishing it *at* them, is the coordination-failure framing's
audit-layer expression — and it only works with records precise
enough to debug from.

## Diagrams to Include

1. **Figure 12-1 — Three artifacts, one call.** A single call rendered
   as its per-turn trace (timeline), its FHIR bundle (milestone
   cards with type/outcome codes), and its cryptographic evidence set
   (the six-item checklist) — with the call-SID drawn as the thread
   through all three. The chapter's master figure.
2. **Figure 12-2 — Outcome-code semantics.** The disclosure
   milestone's three outcomes (0 / 4 / 8) as a decision tree
   separating *capture deficiency* from *conduct violation* — the
   figure that prevents pipeline gaps becoming accusations.
3. **Figure 12-3 — The retention set card.** The six items with their
   "what question it answers" annotations, plus the
   evidence-not-conclusions principle as the card's footer. Extraction
   artifact; pairs with Chapter 11's integration decisions.
4. **Figure 12-4 — The two disputes.** Chapter 3's ninety-day dispute
   and this chapter's afternoon dispute as parallel timelines — same
   question, same parties, the difference annotated at each step by
   which artifact answered it. The book's before/after in one image.

## Operational Guidance

- **Adopt the evidence-not-conclusions principle as written policy.**
  One sentence in your audit standard — "conformance conclusions are
  retained with, never instead of, the records they derive from" —
  settles a hundred future storage-cost arguments in advance.
- **Alert on outcome code 4 as an *internal* signal.** Partial capture
  is your pipeline degrading, and it silently erodes every metric
  downstream. Treat it as an ops page, not a compliance finding.
- **Index the four access paths on day one** — NPI, call-SID, vendor,
  control ID. Retrofitting indexes under a live dispute is the audit
  version of rebuilding the plane in flight.
- **Practice production.** Once a quarter, pull a random call and
  assemble its full evidence set end-to-end, timed. The drill (the
  audit twin of Chapter 3's dispute tabletop) finds the broken link —
  the unexported key history, the bundle that didn't emit — while it
  costs an hour instead of a dispute.

## Implementation Guidance

1. **Wire the FHIR path into your existing audit infrastructure, not
   beside it.** The bundle's entire purpose is landing where
   compliance already looks; an NHID-only audit silo re-creates the
   visibility gap the emitter exists to close. If your organization
   operates a FHIR-capable store, the integration is ingestion; if
   not, the bundles archive as documents until it does.
2. **Snapshot verification context at call time.** The retention
   set's hardest item in practice is (4) — key material as of call
   time. Store the key (or the JWKS document) alongside the
   verification result at the moment of verification; reconstructing
   it later against rotated keys ranges from painful to impossible.
   This is a one-line design decision at integration and a forensic
   dead-end afterward.

## Key Takeaways

- ATR-01 is the control the others cash out through: per-turn traces
  preserve the *position* every behavioral claim depends on, policy
  decisions ride in the record with action, reason code, and version,
  and determinism makes the whole corpus replayable.
- The FHIR AuditEvent bundle translates conformance milestones into
  compliance's native vocabulary — with outcome codes that
  distinguish capture deficiencies from conduct violations, and a
  scope claim (R4 base specification only) stated wherever the bundle
  is.
- Retain evidence, not conclusions: the six-item set for disputed
  calls — trace, bundle, passport, call-time key material,
  verification result, call-SID match — with duration governed by
  your existing audit policy and queryability governed by four
  indexes (NPI, SID, vendor, control).
- Audit's deadline is unforgiving: evidence not captured at call time
  is gone, so the layer's decisions front-load — spine before
  dashboard, snapshots at verification time, indexes on day one.
- Machine-readable audit changes who can ask questions and how often;
  its mature form is an organization that interrogates its AI call
  traffic as routinely as its claims data — and can hand a
  counterparty debugging-grade evidence instead of accusations.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| ATR-01; audit-field failure trace | The trace | Chapter 6 |
| Event schema, governance block, call-SID thread | The trace | Chapter 8 |
| CAS event-completeness factor | The trace | Chapter 15 |
| FHIR AuditEvent milestones, outcome codes | The bundle | — (this chapter) |
| R4-base-only scope claim | The bundle | Chapter 19 |
| Six-item dispute retention set | The discipline | Chapter 11 |
| Replay / policy versions in dispute | Examples | Chapters 7, 10 |
| OpenTelemetry export | (Layer 5, deferred) | Chapter 15 |

---

*Next — Chapter 13, Integration with Existing Healthcare Systems: the
connective tissue — platform adapters, the tier ladder, contract
language, and the seams where the framework meets the systems you
already run.*
