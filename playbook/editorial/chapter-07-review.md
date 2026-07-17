# Editorial Review — Chapter 7: Behavioral Governance

*Review pass following the first complete draft.*

## Overall assessment

The strongest chapter of Part II so far, and arguably the book's most
generalizable. The opening flag-that-wasn't is the ideal scenario: small,
true to the corpus data, and it makes the reader *feel* the false-positive
problem before seeing the numbers. The chapter's thesis — the
automation/judgment boundary placed empirically, with the two layers
supervising each other — elevates what could have been an SOP walkthrough
into a governance pattern with reach beyond voice calls. The corpus numbers
(142/260, 106/153) are the book's first hard data and are deployed exactly
where hard data belongs: at the load-bearing joint.

## Critique

1. **The corpus needs one sentence of provenance.** The numbers come from
   the project's measured evaluation corpus (550 conversations, mined via
   the project's own tooling). The draft says this but should make
   unmistakable that it is an *evaluation corpus*, not production traffic —
   a hostile reader must not be allowed to think production false-positive
   rates are being claimed. Clarifying clause queued.
2. **"The two layers supervise each other" slightly overstates the loop's
   automation.** Refutations feed measurement; measurement gates merges —
   but the loop runs through humans deciding, not a closed control system.
   The Figure 7-4 caption should say "operational loop, not automated
   feedback." Queued.
3. **The decayed-queue counter-example is invented as a composite.** It
   states a well-known review-queue failure mode and is framed as "an
   organization outside the framework" — acceptable as an illustrative
   composite, but per the Chapter 4 precedent it should be marked ("a
   familiar pattern") rather than narrated as a specific observed case.
   Queued — same integrity class as Chapter 4's vendor example.
4. **The quiet-composite example attributes a CAS value (0.68) to an
   invented call.** Fine as illustration; ensure the framing ("lands at")
   cannot be read as real pilot data. The chapter's other numbers are
   real; proximity demands care.

## Weak arguments identified

- **The claim that this boundary-placement pattern is rare** ("a governance
  sentence most AI oversight programs cannot yet say") is a judgment about
  the industry, unsupported by citation. It is hedged ("most... yet") and
  probably true, but it is the chapter's only sentence about organizations
  the author hasn't observed. Consider softening to "few programs can say."
- **Non-blocking design is presented as pure virtue.** The cost — a
  genuinely deceptive call completes before review catches it — is implied
  but never priced. One honest sentence queued: the design accepts
  detection latency on its lowest-confidence signals in exchange for not
  punishing honesty; Chapter 16 should carry it as a residual risk.

## Transitions

- **In:** picks up DBC-01's deliberately incomplete account from Chapter 6
  exactly. Verified.
- **Out:** hands Chapter 8 the deployed-components question. Chapter 8
  should resist re-explaining governance rationale and stay architectural —
  this chapter has done the why; that one owes the where.

## Diagram recommendations

- **Figure 7-2** must include the does-not-route branch at full visual
  weight — the negative space is the design, per the chapter's own words.
- **Figure 7-3** is the portable artifact; consider promoting it to the
  book's introduction as a preview of method.
- **Figure 7-4** caption fix queued (see critique 2).

## Verdict

Sound and strong. Three integrity-adjacent framing fixes queued (corpus
provenance, composite labeling, invented-CAS framing) — none structural.
The residual-risk sentence is added to Chapter 16's brief.
