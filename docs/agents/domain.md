# Domain docs

How the engineering skills should read this repo's domain documentation before exploring the code. This repo is **single-context**.

## Before exploring, read these

- **`CLAUDE.md`**: the canonical scenario, the five controls and the stage rules. It overrides everything below.
- **`docs/terminology.md`**: the glossary. It is the controlled vocabulary for the specification, code and docs, with preferred and deprecated terms.
- **`docs/canonical-threat-model.md`**: who is who on the call, and the conflicts already recorded.
- **`docs/MASTER-KNOWLEDGE-ARCHIVE.md` §19 "Decisions Made"**: this repo's decision records, in place of `docs/adr/`. §9.1 lists the non-negotiable invariants.
- **`docs/claim-boundaries.md`**: before writing anything a reader outside the repo will see.

## Where new terms and decisions go

- **A new term** goes in a row in `docs/terminology.md`. Do not create a root `GLOSSARY.md`.
- **A new decision** goes in a new numbered `### 19.n` entry in `docs/MASTER-KNOWLEDGE-ARCHIVE.md`, dated, with what was decided and why. Do not create `docs/adr/`.
- **New top-level `docs/*.md` files** must be registered in `docs/source-registry.json`. Subfolders such as this one are not indexed.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis or a test name), use the term as `docs/terminology.md` defines it. Don't drift to synonyms it marks as deprecated, and never name a composite score, tier or badge: they are withdrawn.

If the concept you need isn't in the glossary, that's a signal. Either you're inventing language the project doesn't use (reconsider), or there's a real gap (note it for `/domain-modeling`).

## Flag conflicts with recorded decisions

If your output contradicts a §19 decision, a §9.1 invariant or the canonical threat model, say so explicitly rather than silently overriding it:

> _Contradicts §19.6 (CAS demotion), but worth reopening because…_
