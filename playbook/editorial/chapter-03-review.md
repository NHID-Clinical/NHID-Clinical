# Editorial Review — Chapter 3: The Identity Problem

*Review pass following the first complete draft.*

## Overall assessment

The chapter delivers on the promise Chapter 2 made twice: it opens by
decomposing "who is calling?" into nature, representation, and authorization,
and it sustains that decomposition as the organizing device throughout. The
opening dispute scenario is the book's strongest so far — it dramatizes the
gap at the moment it costs the most (ninety days later, with every party
holding records and none holding the fact), and it seeds Chapter 12's
retention requirements concretely. "Why 'Just Detect the Bots' Fails Twice"
is the intellectual peak of Part I to date: the perfect-oracle thought
experiment converts Chapter 1's empirical observation into a structural
proof, and the burden-of-proof inversion gives Part II its architecture in
one paragraph.

## Critique

1. **The instrument survey risks reading as a rejection parade.** Five
   instruments in sequence, each found wanting, could sound dismissive. The
   draft guards against this ("right kind of tool, different question";
   STIR/SHAKEN as "real, deployed, and load-bearing") — preserve those guards
   in revision. The framework *builds on* Layer 1; the book must never sound
   like it is replacing it.
2. **"Knowledge became ambient" is asserted from operational experience.**
   The claim that NPIs are publicly searchable is verifiable (NPPES is a
   public registry — the framework's own materials note issuance ensures
   neither licensure nor credentialing). The claim that identifiers
   circulate through clearinghouses and remittance files is industry-obvious
   but uncited; keep it at the level of mechanism description, never attach
   an incident or a number.
3. **The chapter forward-references Chapter 11 heavily.** Four separate
   passages point at NHID-Auth. This is structural (the chapter's job is to
   define the hole that layer fills) but the drumbeat should be checked at
   the whole-manuscript pass — if Chapter 11 lands well, some pointers here
   can soften.
4. **"Settlement of language rather than of fact" — watch the register.**
   The opening's closing line is literary; it earns its place, but the
   chapter cannot afford a second flourish like it. None was added.

## Weak arguments identified

- **The human social engineer example proves scope, not capability.** It
  honestly concedes NHID-Clinical does not close the human entrance. A
  hostile reader could ask "then why bother?" The draft's answer —
  automation industrialized the gap; the framework closes the industrialized
  entrance — is correct but should be reinforced by Chapter 16's risk
  framing (residual risk, explicitly carried).
- **The claim that verification "gets easier as the ecosystem matures" while
  detection gets harder** is asymmetric reasoning stated without proof. It
  rests on the difference between cryptographic verification (cost flat,
  reliability high) and adversarial detection (arms race). Chapter 11 must
  substantiate it; a note has been left in the outline.

## Transitions

- **In:** honors Chapter 2's three-question promise verbatim. Verified.
- **Out:** hands Chapter 4 the "three questions on a clock" frame. Chapter 4
  must define impersonation latency against *identity resolution* as the
  pilot kit does (`Δt(interaction_start → identity_resolution)`), and should
  clarify how the measured quantity (disclosure) relates to the full
  three-question resolution (disclosure + verification) — the distinction
  this chapter has now made unavoidable.

## Diagram recommendations

- **Figure 3-2 (attestation matrix)** is the keeper — likely to be the most
  reproduced figure in Part I. The empty authorization column is the
  argument; do not let a designer fill it with decorative icons.
- **Figure 3-3** requires care: rendering Layer 0 as a void is editorially
  correct but must match the framework's own trust-stack diagram closely
  enough to be recognizable as a redrawing, not a revision.
- **Figure 3-4's inset** (the chain "lit" by delegations) is approved only
  as a dimmed preview labeled as Chapter 11 material — it must not explain
  mechanics this chapter hasn't earned.

## Verdict

Sound; the strongest chapter of Part I so far. Safe to build on. The
three-question vocabulary is now load-bearing for the whole book — Chapters
4, 6, 11, and 15 must use it consistently (nature / representation /
authorization, in that order, those words).
