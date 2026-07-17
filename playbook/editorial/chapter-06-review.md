# Editorial Review — Chapter 6: The Five Core Controls

*Review pass following the first complete draft.*

## Overall assessment

The chapter clears the depth bar the Chapter 5 review set: this is the third
appearance of the controls table but the first appearance of violation
anatomy, per-control test mechanics, and the traces-as-case-law device —
which is the chapter's best structural idea and should carry into Chapter
12. Opening by replaying Chapter 1's call through all five checks is the
strongest possible entry: it converts four chapters of narrative into a
worked conformance evaluation in three paragraphs, and the observation that
no detection oracle was needed lands the design philosophy before it is
stated.

## Critique

1. **Per-control sections are asymmetric.** IDG-01 and DBC-01 get full
   treatments; PDX-01 leans on IDG-01; EIT-01 and ATR-01 run shorter. The
   asymmetry roughly tracks real complexity, but EIT-01's *implementation
   vs. promise* distinction deserves its polite-wall example inside the
   section rather than only in Real-World Examples. Minor restructure
   queued.
2. **The engine's disclosure sentence is quoted as "the expected shape."**
   Correct per the reference implementation, but the framework does not
   mandate exact wording — the copyedit must ensure no reader takes the
   quoted sentence as required text. Add "one conformant form of words"
   framing at revision.
3. **Receiving-side PDX-01 obligations ("representatives should not
   volunteer data") extend the control's stated scope.** The extension is a
   reasonable operational reading (the control reads on the exchange) but
   the draft should not imply the CTS tests receiving-side conduct — it
   does not. One clarifying clause queued.
4. **CAS composition is named but not derived.** Deliberate — Chapter 15
   owns the metric — but the chapter now makes the third forward promise to
   Chapter 15 (tiers, Goodhart, composition). Chapter 15 is accumulating
   debt; flagged to its brief.

## Weak arguments identified

- **"Conformance costs one sentence and a logging obligation"** slightly
  undersells ATR-01 for vendors without event pipelines — the logging
  obligation is the integration work. The clean-call example's framing
  ("cost profile") is fine for the receiving-side reader; Chapter 13 must
  give the vendor-side effort honestly (the tier ladder already does:
  15 minutes / 2 hours / 1 day).
- **Traces cited by number (04–08)** assumes the reader has repository
  access. Acceptable for this book's audience; the bibliography should
  list trace titles, not just numbers.

## Transitions

- **In:** the replay device connects Part I to Part II mechanically —
  verified.
- **Out:** DBC-01's two-tier honesty section is a deliberately incomplete
  account that Chapter 7 must finish (the measured false-positive data, the
  review SOP, LOG_ONLY). The handoff is explicit. Verified.

## Diagram recommendations

- **Figure 6-1** must be drawn from the framework's actual conformance
  flowchart — implementers will diff it against the source.
- **Figure 6-2 (controls as jurisdictions on a timeline)** is the chapter's
  original visual contribution — prioritize it.
- **Figure 6-4's** routing-not-grades framing is essential; a designer's
  instinct will be gold/silver/bronze. Resist.

## Verdict

Sound; clears the repetition risk. Three minor revisions queued (EIT
example placement, disclosure-wording framing, receiving-side clarifier).
Chapter 15's accumulated obligations formally noted in its brief.
