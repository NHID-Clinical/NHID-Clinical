# Editorial Review — Chapter 8: Operational Architecture

*Review pass following the first complete draft.*

## Overall assessment

The chapter honors Chapter 7's out-transition instruction: it stays
architectural and does not re-argue governance philosophy — the one
philosophical beat it keeps ("the LLM sits behind the policy engine, never
beside it") is earned because here it is *topology*, visible in the state
machine. The whiteboard framing holds the chapter to the practitioner
question throughout, and the three veto questions (touch/break/cost) give
platform-team readers exactly the triage they run in real reviews. The
state-machine section is the technical high point: presenting IDG-01/PDX-01
as "paths the state machine lacks" rather than checks is both accurate to
the reference code and the clearest statement of enforcement-by-construction
in the book.

## Critique

1. **Fidelity to the reference implementation is a double-edged asset.**
   The chapter describes the actual engine (five states, closed action set,
   specific reason codes). If the implementation evolves, these pages age
   faster than the conceptual chapters. Mitigation queued: an "as
   implemented at v1.3" clause at the state-machine section head, matching
   the maturity-snapshot discipline from Chapter 5.
2. **The incident example resolves suspiciously cleanly** ("no meeting
   required"). Real disputes have more friction. The example's *point* —
   reason codes turn disputes into lookups — survives a more honest last
   beat; soften to "the dispute became an infrastructure ticket." Queued.
3. **"Possibly forever" (on staying post-call)** is a real position but
   sits in tension with Chapter 10's enforcement subject. The draft means
   "monitoring topology remains valuable even after enforcement exists" —
   say that, or readers may take it as advice against ever enforcing.
   Queued.
4. **Layer 5 (OpenTelemetry) gets one paragraph.** Proportionate to its
   role, but the observability audience is real; Chapter 15 should pick up
   the dashboard/alerting thread the audit-spine section opens.

## Weak arguments identified

- **"Adoptable without new critical-path dependencies" is true only of the
  post-call topology.** The in-call topology *is* a call-path dependency.
  The draft's framing mostly respects this (blast radius "policy-defined")
  but the Why It Matters section's blanket claim should be scoped to the
  recommended starting topology. Queued — accuracy matter.
- **Verdict parity between hosted and self-hosted** assumes identical
  engine versions, which determinism alone does not guarantee. Add
  "at matching versions" to the parity claims. Queued — small but real.

## Transitions

- **In:** picks up exactly where 7 left off (where does it run). Verified.
- **Out:** Part II → Part III seam lands on the right note — everything
  defined, nothing yet measured on the reader's own traffic. Chapter 9
  owes a mechanics-first treatment; the concepts are all now in place.

## Diagram recommendations

- **Figure 8-1** is the master figure; commission it first and let 8-2/8-3
  reuse its visual vocabulary. Every arrow must carry the schema label —
  the one-contract point is the architecture.
- **Figure 8-2** must be drawn from the reference engine's actual
  transitions; an idealized state machine here would be worse than none.
- **Figure 8-4 (stack as org chart)** is the chapter's original
  contribution — operators attached to layers resolves the "who runs
  what" ambiguity that stalls architecture reviews.

## Verdict

Sound. Four precision fixes queued (version clause, incident softening,
"possibly forever" scoping, parity versioning) — all sentence-level. Part
II is complete and internally consistent; the framework is fully described
and the book can now turn to implementation.
