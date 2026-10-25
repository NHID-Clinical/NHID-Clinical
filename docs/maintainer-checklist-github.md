# Maintainer checklist: GitHub repository settings

These are settings only the repository owner can change. Nothing here is
reachable from a pull request, so this file is the hand-off. Tick each item in
the GitHub UI; the file itself does not need updating when you do.

## NHID-Clinical/NHID-Clinical

- [ ] **Social preview** (Settings → General → Social preview): upload
      `assets/og/default.png` (1200×630). It is the same image every published
      page declares as `og:image`.
- [ ] **About** (the gear beside the description on the repository home):
      description *"Open policy-and-evidence layer for AI agents calling payers:
      disclosure before data, evidence per call. Not a standard, a certification
      or a product."*; website `https://nhid-clinical.org`; tick *Releases* and
      untick *Packages* and *Deployments* if they are empty.
- [ ] **Topics** (same dialog), at most ten:
      `healthcare`, `ai-governance`, `voice-ai`, `hipaa`, `conformance-testing`,
      `prior-authorization`, `healthcare-interoperability`, `fhir`, `audit-trail`,
      `reference-implementation`.
- [ ] **Default branch protection**: require the four CI legs (Ubuntu 3.11,
      Ubuntu 3.14, Windows 3.12, the gates workflow) before merging. The guards
      only help if they can block.

## NHID-Clinical/NHID-Clinical-SaaS and NHID-Clinical/Simulator

- [ ] Each repository has a **license file** and the same split as this one
      where it applies (Apache-2.0 for code, CC BY 4.0 for prose).
- [ ] Each has a one-line **description** that says what it is and what it is
      not, in the words `README.md` here uses for it: the SaaS repository is the
      commercial platform with *zero deployments, zero pilots*; the Simulator is
      a learning tool, *not the framework, not the product, and not a
      certification*.
- [ ] Each has a **social preview** image.

## Organization

- [ ] The organization profile README is this repository's README because the
      repository shares the account name. Either accept that or create a
      `.github` repository with a short `profile/README.md`; do not duplicate the
      controls table there.
