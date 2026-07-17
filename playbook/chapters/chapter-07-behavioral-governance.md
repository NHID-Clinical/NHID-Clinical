# Chapter 7 — Behavioral Governance

*Part II: The Framework*

---

## The Flag That Wasn't

*The scene below is a constructed illustration of a real, measured
phenomenon — the false-positive economics that follow are the project's
actual evaluation-corpus data; the specific analyst and call are not a
reported incident.*

A compliance analyst opens the morning review queue. Overnight, a call has
been flagged for DBC-01 review: an AI agent, mid-way through a claims call,
said — *"I can connect you with a human claims specialist if you'd
prefer."*

Read it again. The sentence contains "human." It discusses the agent's
status by implication. A keyword detector hungry enough would flag it — and
a policy naïve enough would treat the flag as a deception finding against a
vendor. But the sentence is the *opposite* of deception: it is an agent
correctly offering the escalation path EIT-01 requires. Punishing it would
be the disconnect-on-detect mistake reborn inside the framework built to
kill it — penalizing exactly the conduct the controls exist to encourage.

The analyst's queue exists because NHID-Clinical's designers ran into this
sentence — and hundreds like it — with data. When they tested broadening
the deceptive-phrase detector against their 550-conversation evaluation
corpus, every candidate expansion produced more false positives than true
positives, and the false positives were overwhelmingly agents *correctly
disclosing* or *correctly offering escalation*. The lexical distance
between honesty and impersonation is smaller than a phrase list can
resolve.

What do you do when your deterministic instrument has a measured ceiling?
That question — and the framework's answer to it — is what this chapter is
about, because the answer defines what "behavioral governance" actually
means in practice.

---

## Executive Summary

Behavioral governance is the framework's core wager: govern what agents
*do* on calls — observable, testable conduct — rather than what they *are*
(models, vendors, architectures). The wager buys three properties. Conduct
is checkable from call records without access to anyone's model. Conduct
rules survive technology change — every future voice stack still either
discloses first or doesn't. And conduct rules can be enforced
deterministically: the reference policy engine evaluates every turn against
explicit rules, with versioned policies, machine-readable reason codes, and
the invariant that identical inputs yield identical decisions.

But deterministic conduct-checking has an honest boundary, and the
framework's handling of that boundary is its most instructive governance
design. Where rules are crisp (disclosure present? timestamp before PHI?
escalation honored?), the engine decides alone. Where meaning is ambiguous
(is this sentence impersonation or a correct escalation offer?), the
framework refuses to let the machine guess: the deterministic layer stays
deliberately narrow — expansion candidates are rejected unless they carry
zero measured false-positive risk — flags become non-blocking log entries
rather than call-stopping verdicts, and a documented human-review standard
operating procedure catches what the rules cannot. The routing is itself
rule-based: DBC-01 violations route to review (major for phrase matches,
critical for artifact flags), and any call whose CAS falls below the
Conditional Trust threshold (0.75) joins the queue — the composite score
reaching the ambiguous middle a phrase list cannot.

The result is a two-layer governance architecture — deterministic where
certainty is possible, human where judgment is required, with the boundary
between them *measured rather than assumed*. That pattern, more than any
individual control, is what other AI governance domains can take from this
framework.

## Why It Matters

Every organization deploying or receiving AI agents eventually faces the
governance-design question this chapter answers: which decisions may
automation make alone, and which require a person? Most answer it by
intuition, then discover the boundary is wrong in one of two expensive
directions. Automate too much judgment and you get false accusations at
machine scale — vendors flagged for honesty, trust destroyed, the
framework's legitimacy spent on noise. Automate too little and the review
queue drowns, reviewers rubber-stamp, and governance becomes theater.

NHID-Clinical's answer is worth studying because the boundary was *placed
empirically*: candidate rules were tested against a corpus, their error
economics measured, and the expansion rejected on data. "We measured where
our rules stop being trustworthy, and posted a human there" is a governance
sentence most AI oversight programs cannot yet say about any of their
automated checks — and the pattern is portable far beyond voice calls.

For the practitioner audience, the chapter also carries the operational
payload: what routes to review, what explicitly does not, and what
reviewers actually do — the difference between a review queue that works
and one that decays.

## Determinism as a Governance Property

Chapter 5 introduced determinism as disputability; here is the full
argument.

The reference policy engine is a rule evaluator, not a model. Its decisions
carry an action from a closed set (disclose, escalate, block, route,
error), a reason code from a documented vocabulary (`DISCLOSURE_GATE`,
`HUMAN_ESCALATION`, `MISSING_INPUT`, `SESSION_BLOCKED`...), and a policy
version stamp. Three governance consequences follow.

**Decisions are explainable by construction.** Every outcome names its
rule. There is no "the model felt suspicious" — there is `reason_code:
DISCLOSURE_GATE, policy_version: nhid_policy_v1`. Auditors, vendors, and
regulators receive the same explanation, verbatim.

**Decisions are replayable.** Same inputs, identical outputs — enforced by
the project's own invariant tests, and documented as a canonical failure
class when violated (the replay-divergence trace). A disputed verdict is
re-run, not re-argued. Chapter 10 builds enforcement on this property.

**Policy change becomes visible change.** Because behavior is fully
determined by versioned rules, changing governance means shipping a new
policy version — a diffable, reviewable, announceable event. Contrast
governing with a modelled classifier, where behavior drifts with retraining
and no one can say precisely what changed. Chapter 17 makes policy
versioning a governance-committee artifact for exactly this reason.

The cost of determinism is the ceiling: rules only decide what rules can
express. Which brings us to where the framework meets its own limit.

## The Measured Ceiling

The deceptive-phrase check inside DBC-01 is a substring match against a
deliberately short list. The temptation to broaden it is permanent — every
reviewed impersonation suggests a new phrase. The framework's designers did
the experiment instead, mining candidate expansions from a
550-conversation corpus:

- Broad keywords ("human," "person," "real"): 142 new true positives —
  and 260 new false positives.
- Negation-filtered variants (excluding "not a human," "AI system," and
  similar): 106 true positives — and 153 false positives.

Both candidates *accuse more honest agents than they catch deceptive
ones*, and the accused conduct is disclosure and escalation offers — the
exact behaviors the framework rewards. The project's response is codified
as an invariant: heuristic candidates merge only with zero measured
false-positive risk. The phrase list stays narrow *on evidence*, and the
gap it leaves is named rather than papered over: residual implicit
impersonation is a known human-review area, not a solved detection
problem.

Two design consequences follow, and both are easy to miss:

**Ambiguous flags don't block calls.** The phrase-match path is
non-blocking by design — a log-for-review action, not a call-stopping
verdict. The deterministic layer never spends its enforcement authority on
its lowest-confidence signals. Artifact flags (Tier A) — high-confidence
when present — are treated as critical; phrase matches (Tier B) are major
and reviewable. Confidence and consequence stay proportional.

**The composite score catches what no single rule fires on.** A call can
trip no rule and still feel wrong in aggregate — thin identity assertion,
low operational confidence, incomplete events. That is what CAS is *for*:
below 0.75, the call routes to review regardless of rule silence. The
score reaches the middle ground; the rules keep the edges.

## The Human Layer, Specified

The framework's human review is not a suggestion box; it is a standard
operating procedure with routing rules, and the rules are worth restating
in operational language.

**Routes to review:** any DBC-01 violation in a decision (phrase match →
major; artifact flag → critical); any call scoring below Conditional
Trust (CAS < 0.75); critical artifact findings, included for queue
completeness even though their detection confidence is not in question.

**Explicitly does not route:** clean calls (`CONTINUE_AI`, no violations) —
re-flagging every clean call "defeats the purpose and trains reviewers to
ignore the queue," in the SOP's own words — and conversational mentions of
"human"/"person" that match no phrase and don't depress the CAS. The
negative list is as much a part of the design as the positive one: review
queues die of dilution, and the SOP defends the queue's signal density
explicitly.

**What reviewers produce** is a disposition with consequences — confirm
(the flag was real; feeds vendor conversations and, in aggregate,
threshold decisions), refute (false positive; feeds the measurement that
keeps the phrase list honest), or escalate (pattern-level concern; exits
the per-call process into Chapter 17's governance). The refute path
deserves emphasis: every refuted flag is a data point in the same
false-positive economics that set the ceiling, which means the human layer
continuously re-audits the boundary's placement. The two layers supervise
each other.

## Real-World Examples

*(Composite illustrations built around the framework's measured
false-positive data, except the counter-example, which is a familiar
review-queue failure pattern rather than an observed case.)*

**The flag that wasn't (resolved).** The opening sentence, dispositioned:
refuted in under a minute by a reviewer reading one line of context, logged
as a false positive, no vendor contact. Cost of the two-layer design: one
minute of analyst time. Cost of the one-layer alternative — an automated
deception finding mailed to a vendor about their most conformant behavior:
unrecoverable.

**The quiet composite.** A call trips nothing: disclosure present (thin),
no phrase match, no artifacts. CAS lands at 0.68 — Review Required. The
reviewer finds the disclosure sentence was "I'm your virtual assistant for
today's call" — arguably ambiguous to an elderly caller's ear, never
claiming humanity but never saying *automated* either. Disposition:
confirmed as weak disclosure; vendor asked to sharpen wording. No rule
could have written itself around "arguably ambiguous to an elderly
caller's ear" — which is the entire case for the composite score routing
to a person.

**The queue that decayed (counter-example).** An organization outside the
framework builds its own review process and routes *every* AI-suspected
call to it. Volume is immediate; reviewers develop the exact habituation
the SOP warns about; six weeks in, mean review depth is seconds and the
queue is a formality. The negative routing list is the lesson: a review
layer is a scarce instrument, and what you keep *out* of it determines
whether it works.

## Diagrams to Include

1. **Figure 7-1 — Two layers, one boundary.** The deterministic layer
   (rules, reason codes, versions) and the human layer (SOP, dispositions)
   with the boundary between them drawn as a *measured* line, annotated
   with the corpus numbers (142/260, 106/153). The chapter's thesis as one
   image.
2. **Figure 7-2 — Review routing decision tree.** Exactly the SOP's logic:
   DBC-01 violation? → severity; CAS < 0.75? → queue; clean → never. Include
   the does-not-route branch visibly — the negative space is the design.
3. **Figure 7-3 — Confidence/consequence proportionality.** Signal types
   (artifact flag, phrase match, composite score, clean) plotted against
   response (critical review, major review, review, none), showing the
   monotonic relationship. Simple, and the pattern other domains can copy.
4. **Figure 7-4 — The supervision loop.** Rules flag → humans disposition →
   refutations feed false-positive measurement → measurement gates rule
   changes → versioned policy ships. A closed loop; label it as the
   framework's actual answer to "who watches the detector?"

## Operational Guidance

- **Staff the queue for minutes-per-item, then defend its density.** The
  SOP's routing yields a queue where most items deserve real attention.
  Every stakeholder who asks to "also route X to review" is proposing to
  dilute it; require them to bring error economics, as the framework did.
- **Adopt the three dispositions verbatim.** Confirm / refute / escalate,
  each with a defined consequence. A review queue whose outputs go nowhere
  is habituation on a schedule.
- **Track your refute rate as a first-class metric.** It is your measured
  false-positive rate, your early warning of rule drift, and your evidence
  in any vendor dispute. The pilot kit already asks you to document it
  rather than assume zero.
- **Resist the phrase-list request.** Someone in your organization will ask
  why the deception detector "misses so much" and propose keywords. The
  corpus numbers are the answer, and they generalize: broadening
  low-precision text rules against honest-agent traffic manufactures
  accusations. Put the numbers in the deck before the request arrives.

## Implementation Guidance

1. **Wire severity to routing, not to blocking.** When implementing against
   the engine's outputs, map phrase-match findings to queue entries and
   artifact findings to priority queue entries — and let calls complete.
   Blocking on Tier B signals reintroduces disconnect-on-detect with extra
   steps.
2. **Version your own review policy like the engine versions its rules.**
   Your routing thresholds (the 0.75 line, severity mappings) will change
   with your baseline data. Stamp queue entries with the review-policy
   version that routed them, or your refute-rate trends become
   uninterpretable across changes.

## Key Takeaways

- Behavioral governance means governing observable conduct with explicit,
  versioned, deterministic rules — explainable by reason code, replayable
  by construction, and changed only by visible policy-version events.
- Deterministic checking has a ceiling, and the framework *measured* its
  location: every tested expansion of the deception phrase list produced
  more false accusations than detections, with honest disclosure and
  escalation offers as the primary casualties.
- The response is architectural, not apologetic: low-confidence signals
  are non-blocking by design, a composite score (CAS < 0.75) reaches the
  ambiguity no rule fires on, and a specified human-review SOP — with an
  explicit does-not-route list — catches the remainder.
- The two layers supervise each other: refuted flags feed the
  false-positive measurement that gates every future rule change. Zero
  measured false-positive risk is the merge bar.
- The portable lesson for AI governance generally: place the
  automation/judgment boundary with data, keep machine consequence
  proportional to machine confidence, and defend the human queue's signal
  density as an asset.

## NHID-Clinical Concepts Referenced

| Concept | Where referenced here | Formal treatment |
| :-- | :-- | :-- |
| Policy engine actions, reason codes, versions | Determinism as governance | Chapters 8, 10 |
| Replay-divergence invariant (trace 09) | Decisions are replayable | Chapter 12 |
| DBC-01 Tier A/B, phrase-list corpus data | The measured ceiling | — (this chapter) |
| Zero-false-positive merge invariant | The measured ceiling | Chapter 17 |
| LOG_ONLY / non-blocking review routing | The measured ceiling | Chapter 10 |
| CAS < 0.75 Review Required threshold | The human layer | Chapter 15 |
| DBC-01 Human-Review SOP | The human layer, specified | Chapter 17 |

---

*Next — Chapter 8, Operational Architecture: where all of this actually
runs — the engine, the event schema, the adapters, the API, and the trust
stack as deployed components in a real call path.*
