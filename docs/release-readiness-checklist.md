# NHID-Clinical — Release Readiness Checklist

**Status:** release-preparation tracker · **Added:** 2026-07-18 · CC BY 4.0

> Gate for a credible public **v1 documentation** release while preserving
> technical honesty. Status marks reflect the state at the time of writing;
> `[x]` = done, `[~]` = in progress / partial, `[ ]` = not yet. This
> checklist governs the *documentation* release, not a production-software
> release — the reference implementation's maturity limits are disclosed, not
> resolved, by this gate.

---

## Documentation

- [x] **Positioning reviewed** — [docs/positioning.md](positioning.md); the
  two-layer model (governance/accountability + non-human-actor
  identity/delegation) survived a skeptical three-reviewer pass (NIST AI RMF
  contributor, healthcare security architect, identity/security engineer) and
  the resulting seven precision corrections are applied.
- [x] **Terminology aligned** — [docs/terminology.md](terminology.md);
  preferred vs. deprecated terms fixed ("non-human actor"/"AI-operated" over
  "autonomous"; "operational AI governance framework"; verifier-checked scope,
  not "structurally enforced").
- [x] **Claims bounded** — [docs/claim-boundaries.md](claim-boundaries.md);
  claims-to-make vs. claims-to-avoid, maturity-boundary table, PHI deployment
  caveat, standards posture.
- [x] **README aligned** — opens with the operational-governance category and
  the model-boundary clarifier; includes "What NHID is / is not" and "Composes
  with — does not replace"; EU AI Act reference softened to "designed to
  support the transparency obligations described in Article 50."
- [x] **Scope boundary published** —
  [docs/scope-boundary-fairness-clinical.md](scope-boundary-fairness-clinical.md)
  (model fairness, clinical safety, and quality explicitly out of scope).
- [x] **EU AI Act wording reconciled (public-facing)** — the only strong
  "compliant with Article 50" self-claim was the README banner, now "designed
  to support the transparency obligations described in EU AI Act Article 50."
  A repo-wide sweep confirms the website HTML carries **no** equivalent
  self-claim: its EU AI Act references are tool descriptions ("maturity radar
  for tracking compliance across frameworks"), "sits alongside," and mapping
  language — all preserved as-is. The manuscript retains an *analytical*
  discussion of the claim (Ch. 19), intentionally left untouched as
  out-of-scope manuscript content.

## Technical

- [x] **Specification versioned** — v1.3 core specification present
  ([docs/nhid-clinical-technical-specification.md](nhid-clinical-technical-specification.md)),
  plus NHID-Auth v2 reference.
- [x] **Conformance suite documented** — deterministic policy engine +
  18-case CTS; same inputs → identical outputs; runnable against the reference
  implementation.
- [x] **Reference implementation status disclosed** — maturity table in
  [claim-boundaries.md](claim-boundaries.md): governance layer is an
  implementable reference framework; the identity/delegation layer is a
  reference *primitive* (in-memory revocation, demo-grade key custody), not
  deployed infrastructure.
- [ ] **Second independent implementation** — does not exist. This is the
  single gating deficiency for a *standards-track* (as opposed to
  documentation) claim; not required for a v1 documentation release, but the
  headline open item beyond it.

## Adoption

- [x] **Implementation guidance available** — the playbook (Parts III–IV) and
  the observe-only [Tier 0 Shadow Pilot Kit](pilot-kit/README.md); the
  [Executive Brief](executive-brief.md) and
  [vendor trust questionnaire](vendor-trust-questionnaire.md) are the
  evaluation entry points.
- [x] **Maturity limitations disclosed** — production-scale evidence is
  limited; the recommended first step is a shadow pilot on the adopter's own
  traffic, stated consistently across README, positioning, and claim
  boundaries.
- [x] **Security gaps documented** — in-memory revocation; unspecified key
  custody/rotation lifecycle; no trust registry (NPI → public key resolution);
  no federation/multi-hop propagation automation; trust-root bootstrapping
  unsolved at scale; audit artifacts may carry PHI and their protection is the
  deploying organization's responsibility.

## Release packaging (playbook artifact)

- [x] **Reproducible build pipeline committed** — `playbook/build/`
  (`build_pdf.py` → `render_pdf.py` → `validate_pdf.py`), wired to
  `make playbook-pdf` / `make playbook-validate`. Portable paths, portable
  Chromium resolution, stamped PDF metadata, structural validation gate. Output
  goes to git-ignored `playbook/dist/`.
- [x] **Licensing metadata defined** — CC BY 4.0 in the artifact front matter
  (© 2026 Brianna Nicole Baynard; public byline "Brianna Baynard";
  NIST-2025-0035-0026 disclaimer) and stamped into the PDF document properties
  (Title/Author/Subject/Keywords/Creator) from a single source of truth.
- [ ] **Final PDF generated / committed / published** — **intentionally held.**
  Blocked until the deferred positioning-alignment pass (title/subtitle +
  Chapter 5) lands. Deferred publish steps: flip the `SUBTITLE` constant and
  re-render/validate; add a `!specs/…playbook.pdf` gitignore exception and
  commit the PDF to `specs/`; add a CHANGELOG entry; optionally add a
  `specs/index.html` download card and/or a git tag + GitHub Release. See
  [`playbook/build/README.md`](../playbook/build/README.md).

## Known open items carried into release (disclosed, not resolved)

1. Second independent conformance-passing implementation.
2. Registry / trust-resolution model (NPI → public key).
3. Revocation and key-lifecycle specification (durable, sub-second-visibility).
4. Federation patterns composable with SPIFFE/OAuth-style stacks.
5. EU AI Act wording reconciliation in website HTML and manuscript.
6. Deferred positioning-alignment pass for the playbook title and Chapter 5.

---

CC BY 4.0 · Brianna Baynard · NIST-2025-0035-0026 — a public comment, not a
NIST endorsement, adoption, or certification.
