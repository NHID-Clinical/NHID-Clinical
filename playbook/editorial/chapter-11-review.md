# Editorial Review — Chapter 11: Authorization

*Review pass following the first complete draft.*

## Overall assessment

The chapter pays every debt registered against it: the
truthful-unauthorized-agent scenario is resolved in the opening (with the
right emphasis — truth became *checkable*, the agent's honesty was never
the variable), and Chapter 3's verification-vs-detection asymmetry is
substantiated structurally (flat-cost signature checking vs. adversarial
generation). The two-keys-two-questions device successfully compresses
the trust architecture's most confusing material, and the maturity
honesty is the best in the book — "a working trust primitive, not
deployed trust infrastructure" carries the framework's own candor
forward at the layer where overclaiming would be most tempting and most
damaging.

## Critique

1. **Density.** This is the book's most technically loaded chapter —
   keys, chains, TTLs, nonces, custody, discovery, retention — and the
   walked-through section runs long even with aggressive compression.
   The consistency pass should test whether JWKS/registry material can
   thin further (it is Chapter 18's subject) — currently one paragraph,
   probably the floor. No cut queued; flagged for reader testing.
2. **"Revocation propagates immediately" in the opening scenario
   idealizes the reference implementation**, whose revocation state is
   in-memory and process-local. The chapter corrects this honestly two
   sections later (production guidance: sub-second visibility as SLA),
   but the scenario narrates the *production* behavior. Add a clause to
   the scenario ("an organization operating the... layer" → as
   production-hardened per the migration path) or a footnote. **Queued —
   integrity class, the chapter's only one.**
3. **The compromised-middle example's contrast** ("authorized anything,
   against any payer, indefinitely") slightly overstates the
   knowledge-based world — breached identifiers still faced per-payer
   authentication rituals. The point (unscoped vs. scoped compromise)
   survives precise wording. Softening queued.
4. **The bot-to-bot gap is deferred with a table row but no prose.**
   Chapter 3 and the payer-initiated materials made mutual verification
   an open question; this chapter verifies one direction and should say
   in one sentence that mutual (bidirectional) passport exchange is the
   documented open gap. Queued — one sentence before the production
   section.

## Weak arguments identified

- **"Nobody's front office learns cryptography"** — true for verification
  flow, but providers *do* acquire key-custody obligations (root key
  management), which is an administrative burden the chapter defers to
  custodianship options without pricing for small practices. Chapter 18
  (adoption) should carry the small-provider question; noted in its
  brief.
- **The offboarding example assumes practices operate delegation
  hygiene reliably** — the chapter's own advice (wire into contract
  lifecycle) is the mitigation, and honestly framed as necessary rather
  than automatic. Acceptable.

## Transitions

- **In:** picks up Rung 3's "gate around what you cannot answer" and
  answers it. Verified.
- **Out:** the retention preview creates the cleanest chapter seam in
  Part III — Chapter 12 opens holding the evidence-not-verdicts
  principle already motivated. Verified.

## Diagram recommendations

- **Figure 11-1** completes the 3-4 pairing — commission together, same
  layout, per the standing brief.
- **Figure 11-3's** empty human lane is the chapter's burden-shifting
  argument in visual form; instruct the illustrator not to decorate it
  away.
- **Figure 11-4's** failure matrix is the anti-conflation artifact —
  vendor-facing, extraction-worthy.

## Verdict

Sound; one integrity fix (revocation idealization in the scenario), one
added sentence (bot-to-bot open gap), two softenings. The book's
technical apex chapter holds the honesty line. Chapter 12 inherits a
motivated reader and the retention set.
