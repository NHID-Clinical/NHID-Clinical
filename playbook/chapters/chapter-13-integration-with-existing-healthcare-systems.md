# Chapter 13 — Integration with Existing Healthcare Systems

*Part III: Implementation*

---

## The Integration Engineer's Week

*The engineer and her week below are a composite, constructed to walk
through what integration actually involves — not an account of a
specific payer's project.*

Monday morning, a platform engineer at a payer receives the ticket that
Part III has been building toward: *integrate NHID-Clinical conformance
checking with our production call stack.* She has read the architecture
chapter, so she starts where it told her to — the inventory. By noon she
has the list of what the framework must touch: the telephony platform
(their contact-center stack emits end-of-call webhooks), the vendor
ecosystem (three known voice-AI vendors on two platforms, per the
Chapter 2 inventory homework), the provider-enrollment system (Chapter
3's homework — it has an owner now), the compliance team's audit store
(FHIR-capable, as it happens), and procurement's contract-renewal
calendar.

By Wednesday she has the post-call topology live in staging: the
end-of-call webhook forwards native payloads to the matching adapter
route; verdict, CAS, and violations store beside the call record; the
FHIR bundle flows to the audit store. Thursday is the CTS parity replay
and the runbook. Friday she writes the part nobody assigned her but the
book insisted on: a one-page seam map — every system the integration
touches, who owns it, and which chapter's discipline governs it. The
seam map is this book's recommended practice for organizing integration
work, not an artifact NHID-Clinical itself specifies.

Her retro note to the architect is the chapter in one line: "The code
was the easy week. Everything that matters now is seams — vendors,
contracts, enrollment, audit — and none of those are tickets I can
close alone."

---

## Executive Summary

Integration is where the framework stops being a system you run and
becomes a property of systems you already run. This chapter maps the
seams, in four groups.

**Telephony and voice platforms.** The adapters accept native payloads
from VAPI, Twilio, Vonage, Retell, and Amazon Connect — integration
means forwarding webhooks you already emit, not converting formats. The
staged ladder governs effort honestly: Tier 0 (a transcript and `curl`,
fifteen minutes) for evaluation; Tier 1 (~two hours) wires the
end-of-call webhook for continuous post-call checking; Tier 2 (~a day)
adds cryptographic identity via the reference library. Each rung is
independently useful; stopping is legitimate at every one.

**Identity and security infrastructure.** The two-check pattern from
Chapter 11: OAuth2/OIDC continues to govern API transport exactly as
your existing identity providers configure it — none of them need to
know NHID-Auth exists — while passports ride the request body and are
verified in application code, never by the identity provider. NHID
context can be copied into JWTs as private-namespace claims for
logging convenience, but the copies are never the authorization. The
enrollment-system seam receives the verified NPI and answers
legitimacy; the KMS/HSM seam holds keys.

**Audit and compliance systems.** FHIR bundles ingest into existing
FHIR-capable stores (or archive as documents until one exists);
OpenTelemetry export lands conformance signals in existing
observability; retention follows your existing administrative-records
policy per Chapter 12.

**The paper seams.** Contracts and procurement are integration
surfaces too: the framework's vendor trust questionnaire structures
diligence; a business associate agreement template exists among the
framework's materials for engagements where call data flows to a
processing party; and the five controls translate directly into
contract-exhibit conduct language, with pilot-derived thresholds
arriving later (Chapters 14–15).

The chapter's thesis: every seam has an existing owner, and
integration succeeds by meeting each owner inside their own system —
their webhook format, their audit store, their contract template —
rather than asking anyone to adopt a parallel stack.

## Why It Matters

Healthcare IT's graveyard is full of governance systems that worked
perfectly beside the systems they were meant to govern. The pattern
repeats because integration effort is misestimated in a specific
direction: the *technical* connections are smaller than expected (this
framework's entire Tier 1 is one webhook forward), while the
*organizational* connections — who owns enrollment lookups, whose
audit store ingests, which contract cycle carries the new exhibit —
are larger. This chapter exists to invert the reader's estimate before
the project plan is written.

The seam inventory also determines the adoption ceiling. An
organization that integrates only the technical seams gets monitoring
— valuable, and Chapter 10 said to live there awhile. But enforcement
credibility (Rung 4 runs on contracts), authorization (runs on
enrollment and key custody), and dispute power (runs on audit
ingestion) each require a paper or organizational seam crossed. The
integration engineer's Friday map — seams, owners, disciplines — is
the honest statement of how much of the framework an organization has
actually adopted.

## The Technical Seams

**Meet the platform at its webhook.** The Tier 1 pattern is
deliberately anticlimactic: the voice platform fires its call-completed
event (each platform's native flavor — end-of-call report, call
analyzed, status callback); your handler forwards the payload to the
matching adapter route; you store the returned CAS score and
conformance flag and alert on non-conformance. Ten lines of code in
the integration guide's own example. Add the turn-by-turn webhook
route only when Chapter 10's sequencing licenses in-call enforcement.
The engineering discipline that matters is Chapter 8's: prove CTS
parity in *your* deployment before trusting either topology, and pin
engine versions so parity claims mean something.

**Keep the identity layers separate on purpose.** The integration
error Chapter 11 warned against — conflating client authentication
with caller authorization — is prevented architecturally by keeping
verification in the policy-evaluation path and transport auth at the
gateway, so a future change to one cannot silently weaken the other.
Your Auth0, Okta, Entra ID, or Cognito configuration is untouched
except, optionally, for custom-claim copies; do not attempt to make
the identity provider verify delegation signatures — that is
application-layer work by design.

**Let audit land where audit lives.** The FHIR seam's success
condition is negative: no new place for compliance to look. Similarly
for observability — conformance metrics belong on the same dashboards
and alert routes as the rest of call-infrastructure health, which is
what the OpenTelemetry layer is for.

**Respect the enrollment seam's authority.** The verified NPI goes to
your provider directory for the legitimacy check the cryptographic
layer deliberately does not make. Integration here is usually a lookup
service call — the hard part, as Chapter 3 predicted, is governance:
an owner, an SLA, and an agreed answer format for "active and enrolled
with us."

## The Paper Seams

**The questionnaire before the contract.** The framework's vendor
trust questionnaire gives diligence a structure that matches the
controls: how does the agent disclose, what does it do pre-disclosure,
how is escalation implemented, what traces are produced, what
delegation can be presented. Send it before renewal cycles, not
during — answers arriving without deadline pressure are more honest,
and they tell you which vendors will find contract language easy.

**Contract language in three stages.** Stage one, conduct: the five
controls as exhibit text — disclose before PHI, no data before
disclosure, no deception, honored escalation, traces delivered. This
requires no baseline and no negotiation about numbers. Stage two,
evidence: trace delivery formats, audit cooperation, dispute replay
terms (Chapter 10's due-process clauses, made bilateral). Stage
three, thresholds: CAS floors and latency expectations — only after
your pilot data exists (Chapter 14) and only with the Goodhart
cautions Chapter 15 supplies. Organizations that start at stage three
negotiate blind; those that start at stage one are requiring only what
any honest vendor can sign today.

**The BAA question belongs to counsel, with one observation.** This book
does not offer legal advice, and whether business-associate machinery
applies to a given conformance-checking arrangement is a determination
for the adopting organization's own counsel, based on its specific data
flows. Where conformance checking involves a party processing call data
containing PHI, that machinery may apply, and the framework's materials
include a BAA template as a starting artifact for counsel to work from —
not a substitute for that review. This book adds only the operational
note: self-hosting the engine (Chapter 8's option) changes the data-flow
question entirely, and is the resolution worth raising with counsel where
the seam gets contentious.

## Real-World Examples

*(Composite illustrations; "the vendor who was already conformant" is an
anticipated dynamic the public routes make possible, not a documented
case.)*

**The vendor who was already conformant (anticipated dynamic).** A payer
sends the questionnaire to its three known vendors. One returns it
same-week with trace samples attached — its platform, it turns out, had
built against the public adapter routes months earlier for its own QA.
Nothing has been reported at this scale yet; the public routes make the
scenario possible, not documented. The contract exhibit that follows is
a formality. The example's point: the open reference implementation
means vendor-side integration can precede any payer's request, and
procurement's job becomes *discovering* conformance as often as
demanding it.

**The audit store that wasn't.** A mid-size payer's compliance
"system" turns out to be a shared drive and an EHR module that
cannot ingest arbitrary FHIR bundles. Integration stalls — until the
team applies the archive-as-documents fallback and a quarterly manual
review, recording a debt ticket against the audit-platform roadmap.
Imperfect, honest, and vastly better than the alternative discovered
in most such organizations: waiting for the perfect audit platform
while capturing nothing.

**The renewal that carried the exhibit.** An operations lead times
the stage-one conduct exhibit to a vendor's scheduled renewal rather
than opening a special negotiation. The vendor signs without
escalation — the exhibit asks only for behavior the vendor's
marketing already claims. Sixty days later the first trace deliveries
arrive and the relationship has an evidence channel it never had.
Total additional negotiation cost: minimal. Contract seams cross
cheapest when they ride existing paper cycles.

## Diagrams to Include

1. **Figure 13-1 — The seam map.** The integration engineer's Friday
   artifact, generalized: your call stack at center; technical seams
   (platform webhooks, identity, enrollment, audit, observability)
   and paper seams (questionnaire, contract exhibits, BAA) radiating,
   each labeled with its owner role and governing chapter. The
   chapter's master figure and its extraction artifact.
2. **Figure 13-2 — The tier ladder with effort honest.** Tier 0/1/2
   with the guide's own estimates (15 minutes / ~2 hours / ~1 day),
   what each yields, and the "stop here if" legitimacy notes. Answers
   the executive question "how big is this?" with the framework's own
   numbers.
3. **Figure 13-3 — The two-check integration.** Chapter 11's Figure
   11-4 specialized to deployment: gateway (token) and policy path
   (passport) drawn inside a real request lifecycle, with the
   identity-provider box explicitly marked "unchanged."
4. **Figure 13-4 — Contract language in three stages.** Conduct →
   evidence → thresholds, annotated with what each stage requires
   (nothing / trace formats / your own baseline) and what it gets
   you. The procurement-facing figure.

## Operational Guidance

- **Build the seam map before the project plan.** One page, every
  seam, every owner, every governing discipline. Projects scoped from
  the seam map estimate honestly; projects scoped from the code
  estimate a week and deliver a quarter.
- **Ride existing cycles.** Contract exhibits at renewals,
  questionnaire ahead of diligence windows, audit ingestion with the
  audit platform's release train. The framework's adoption cost is
  mostly coordination; coordination is cheapest inside rhythms that
  already exist.
- **Let vendors integrate first when they offer.** The public routes
  mean a vendor can self-check before you ask. Treat volunteered
  conformance evidence as the gift it is — verify it with your own
  replay, then say yes quickly. Adoption accelerates on the supply
  side when early movers are visibly rewarded (Chapter 18's
  mechanics).
- **Escalate seam disputes to the right table.** Data-flow and BAA
  questions go to counsel with the self-hosting option in hand;
  enrollment-seam ownership goes to whoever owns provider data
  governance; neither belongs in the engineering standup where they
  will otherwise die.

## Implementation Guidance

1. **One workflow, one vendor, end to end, before breadth.** Wire
   Tier 1 for a single workflow's traffic and a single cooperative
   vendor; run it a month; assemble one call's full evidence set
   (Chapter 12's drill) from the live pipeline. Every seam defect
   surfaces at depth-one scale, where it costs a meeting instead of a
   program reset.
2. **Version the seam map with the deployment.** Seams change —
   platforms swap, audit stores mature, contracts renew. The map from
   the engineer's Friday is a living document; stale seam maps
   mis-scope every subsequent phase. Review it quarterly alongside
   Chapter 12's production drill.

## Key Takeaways

- Integration is seams, not systems: platform webhooks, identity
  layers kept deliberately separate, enrollment lookups, audit and
  observability ingestion, and the paper seams — questionnaire,
  contract exhibits, BAA — each with an existing owner to meet
  in their own system.
- The tier ladder keeps effort honest — fifteen minutes to evaluate,
  hours to monitor continuously, a day for cryptographic identity —
  and every rung is a legitimate stopping point.
- Technical seams are smaller than expected; organizational and
  paper seams are larger. Scope from the seam map, ride existing
  cycles, and measure adoption by seams crossed, not code deployed.
- Contract language arrives in three stages — conduct (sign today),
  evidence (trace delivery and replay terms), thresholds (only after
  your own baseline) — and the two-check identity pattern leaves
  your identity providers untouched by design.
- The open reference implementation makes integration bidirectional:
  vendors can conform before being asked, and procurement's job
  includes discovering and rewarding it.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Adapters; adapter routes | Technical seams | Chapter 8 |
| Tier 0/1/2 integration ladder | Throughout | Chapters 5, 9, 11 |
| Two-check pattern; private-namespace claims | Identity seams | Chapter 11 |
| Enrollment-system seam | Technical seams | Chapters 3, 11 |
| FHIR ingestion; OTel export | Audit seams | Chapter 12 |
| Vendor trust questionnaire | Paper seams | Chapters 2, 14 |
| BAA template | Paper seams | — |
| CTS parity replay; version pinning | Technical seams | Chapters 8, 10 |
| Public CAS badge / vendor self-check | Examples | Chapter 18 |

---

*Part III complete. Next — Part IV opens with Chapter 14, Pilot
Programs: scaling the shadow evaluation into an organizational
program — partners, phases, decision gates, and what pilots can and
cannot prove.*
