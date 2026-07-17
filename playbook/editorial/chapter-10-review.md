# Editorial Review — Chapter 10: Policy Enforcement

*Review pass following the first complete draft.*

## Overall assessment

The chapter closes the book's oldest open loop — the successor to
disconnect-on-detect, promised in Chapter 1 — and closes it with the right
shape: a ladder whose cardinal rule (disclose-when-prompted rejoins the
workflow penalty-free) makes the incentive inversion concrete. Replaying
the Chapter 1 call *under policy*, with both branches handled, is the
book's best scenario-craft to date: the forked ending shows the honest
path is operationally smoother, which no amount of argument could. The
asymmetry principle (wrongly punishing honest agents costs more than
wrongly permitting deceptive ones) is stated with executive-grade clarity
and consistently governs the design — the chapter passes its own test.

## Critique

1. **The ladder is the author's synthesis, not a framework artifact.**
   The rungs are built from real framework components (actions, reason
   codes, SOP routing, CAS thresholds, callback practice), but the
   five-rung structure itself is this book's contribution. That is the
   playbook doing its job — but one sentence should say so ("the
   framework supplies the mechanisms; the ladder is this book's
   recommended arrangement of them"), or readers will search the spec for
   rung numbers. **Queued — attribution class.**
2. **The prompt-that-became-a-norm example projects vendor adaptation.**
   The mechanism is sound (vendors optimize openings against known
   receiving behavior — the mirror of Chapter 2's incentive gradient) but
   "within a quarter, disclosure rises measurably" narrates an outcome no
   pilot has produced. Label as the *expected* dynamic, per the standing
   rule. Queued — integrity class.
3. **The receiving-side obligations expand PDX-01 again** (Chapter 6's
   review flagged the same). The draft is now building a consistent
   doctrine (receiving-side conduct as incentive structure) across three
   chapters; the consistency pass should decide whether this doctrine
   deserves its own named sidebar rather than repeated marginal
   extensions of a control's reading.
4. **Rung 4 as "where enforcement should live for the first year"** is
   strong, correct advice delivered in one clause — it may deserve
   promotion to the executive summary, since it is the chapter's single
   most consequential recommendation for sequencing.

## Weak arguments identified

- **The claim that managed termination "teaches more than a dropped
  call"** is asserted via the trace argument; fine. But the callback
  path's operational cost (staffing verified-callback handling) is never
  priced. One honest clause queued: the callback rung trades handle time
  for auditability and market signal.
- **"Moves markets more than any in-call banner"** — directionally
  defensible, rhetorically confident, unevidenced. Soften to "moves
  vendor behavior at least as much." Queued.

## Transitions

- **In:** enforcement argued from baseline data, exactly as Chapter 9
  set up. Verified.
- **Out:** the handoff to Chapter 11 is precise — enforcement can *gate
  around* unanswered authorization questions but not answer them.
  Chapter 11 owes: the substantiation of Chapter 3's
  verification-gets-easier claim, and the truthful-unauthorized-agent
  resolution.

## Diagram recommendations

- **Figure 10-1** joins the extraction genre (fourth card). The margin
  annotations for the two deliberate absences are essential — they are
  the ladder's philosophy.
- **Figure 10-2** must visually favor the honest branch (shorter,
  fewer nodes) — the diagram *is* the incentive argument.
- **Figure 10-3** extending 7-3 across two chapters is good bookcraft;
  commission as one evolving figure.

## Verdict

Sound, with two queued labeling fixes (ladder attribution, projected
example) and two softening edits. The book's central promise — a
workable successor to disconnect-on-detect — is now delivered; remaining
chapters build outward from a complete core.
