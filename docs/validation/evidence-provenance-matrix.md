# Evidence Provenance Matrix — what each source is allowed to prove

**Status:** validation reference (load-bearing) · **Added:** 2026-10-14 · CC BY 4.0

> The single most important document in `docs/validation/`. NHID-Clinical's
> credibility rests on never letting a weaker form of evidence borrow the
> authority of a stronger one. This matrix fixes, for every kind of evidence we
> can produce, exactly **what it establishes and what it does not** — so a
> reviewer can always see how far a given claim is entitled to reach, and so no
> artifact on the site, in a deck, or in an evidence pack ever overstates.
>
> Pairs with [`../claim-boundaries.md`](../claim-boundaries.md). Where the two
> touch, claim-boundaries wins.

---

## The ladder, weakest to strongest

Evidence about NHID-Clinical comes in seven tiers. Each tier proves strictly
more than the one below it, and **nothing may be described in the language of a
tier above the one that produced it.**

| # | Evidence tier | What it IS | What it proves | What it does **not** prove |
| :-: | :-- | :-- | :-- | :-- |
| 1 | **Framework capability** | The controls exist, are specified, and run deterministically | That the engine *can* evaluate a given behaviour and emit a verdict + reason code | Nothing about real agents, real calls, accuracy on real data, or adoption |
| 2 | **Automated tests** | The unit/conformance suite passing in CI | That the implementation behaves as specified on inputs we wrote | Nothing about real-world detection rates — these inputs are authored to pass |
| 3 | **Synthetic-corpus results** | Measured detection/FP over `tests/evaluation_corpus_v1.json` | A research measurement of detection behaviour on a small, hand-authored, PHI-free corpus, with stated denominators | Real-world accuracy, generalization, or that the corpus resembles production traffic |
| 4 | **Consented volunteer audio** | Scripted calls by consenting adults using fictional identities over a real audio channel | That the pipeline handles real speech, noise, interruptions, and timing — on *acted* scenarios | That real healthcare agents behave this way, or any clinical/production validity |
| 5 | **Public-dataset results** | Measured results on a documented external dataset (e.g. INSURE-Dial) | Detection behaviour on third-party data, under that dataset's license and known limits | Production validity, unless the dataset itself is production-derived and licensed as such |
| 6 | **Authorized healthcare pilot** | Observe-only evaluation of a real organization's own call traces under a signed BAA/DPA | Behaviour on real provider→payer traffic for that organization, within the pilot's scope | Generalization beyond that organization; certification; endorsement |
| 7 | **Production deployment** | NHID evaluating live traffic in a deployed system | Real operational behaviour at scale | Certification, regulatory approval, or that NHID is required |

**Today, NHID-Clinical has evidence at tiers 1–3 only.** Tiers 4–7 are not yet
established. Any public statement must be written at tier 3 or below until a
higher tier actually exists, and must name the tier it rests on.

---

## Forbidden cross-tier moves (the ways this goes wrong)

- A **test passing** (tier 2) described as "detects X in healthcare calls"
  (tier 5/6). Tests prove conformance to spec, not field accuracy.
- A **synthetic detection rate** (tier 3) quoted without its denominator or the
  word "synthetic," so a reader hears tier 5/6.
- A **volunteer call** (tier 4) shown as evidence of "deployment" or
  "healthcare use" (tier 6/7). Acted ≠ real.
- A **public-dataset number** (tier 5) presented as NHID's production accuracy
  (tier 7).
- Any **payload hash or audit record** presented as proof that a run *actually
  happened* or that a result is *true* — a hash proves integrity of a submitted
  artifact, nothing about whether the underlying call occurred or what it
  showed. (This is already enforced in the pilot registry; it is restated here
  because it is the most tempting overclaim.)

---

## Required labelling

Wherever a result appears — site, dashboard, deck, evidence pack, README — it
carries, in plain sight:

1. **Its tier** (1–7 above), in words a non-engineer understands.
2. **Its data classification** — `synthetic`, `de-identified`, or
   `production-derived` — matching the `data_classification` field now carried
   on every pilot run. Default and assumption is `synthetic`.
3. **Its denominator and date**, for any rate.
4. **One limitation sentence** naming the nearest thing it is *not*.

If any of the four is missing, the result is not ready to show.

---

## What this means for the current artifacts

- The homepage evaluation walkthrough is **tier 1** (framework capability,
  illustrative) and is already labelled as engine output from a fixture, not a
  real call. Correct.
- The corpus detection report (`docs/EVALUATION_CORPUS_REPORT_v1.md`) is
  **tier 3** and already states "a research measurement of one small
  hand-authored corpus … not a conformance claim, a certification, an
  assurance score, or independent validation." Correct — keep that sentence.
- An INSURE-Dial result, once produced, is **tier 5** and must be reported as
  "measured on the INSURE-Dial benchmark (third-party data)," never as NHID's
  accuracy.
- A volunteer-call result is **tier 4** and must say "scripted, consented
  volunteers using fictional identities — not real healthcare traffic."

No artifact in this repository currently claims a tier it has not reached. The
job of this matrix is to keep it that way as new evidence arrives.
