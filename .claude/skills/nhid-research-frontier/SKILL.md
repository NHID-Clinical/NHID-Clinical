---
name: nhid-research-frontier
description: >-
  Load when the question is where NHID-Clinical could advance the state of the art, or
  when scoping an ambitious/research-flavored feature (semantic detection, real-time
  in-call enforcement, cryptographic agent identity, or becoming an adopted standard).
  For each frontier it states why current SOTA falls short, the specific asset this repo
  already has, the first three concrete steps IN THIS REPO, and a falsifiable "you have a
  result when" milestone. Everything here is candidate/open — nothing is shipped. Load it
  for "what's the research bet", "could we do X live", "beyond state of the art",
  "publish/standardize this". Do NOT load it for shipping the current engine (that's
  change-control) or executing the DBC-01 campaign (that's the campaign skill).
---

# NHID-Clinical Research Frontier

Verified as of 2026-07-04. **Everything below is candidate/open — not shipped.** Do not cite any
of it as a capability (`nhid-docs-and-positioning`). Each frontier is a place where the repo's
existing assets could push past current practice.

## Frontier 1 — Semantic violation detection

- **Why SOTA falls short**: the field is split between brittle keyword lexicons (this repo's
  proven ceiling) and unvalidated "ask an LLM if it's deceptive" with no reproducible eval.
- **Our asset**: a 550-conversation labeled corpus (`fixtures/fabricate/`) + a reproducible
  disjoint-population confusion-matrix harness (`scripts/confusion_matrix.py`).
- **First 3 steps in-repo**: (1) prototype an LLM-judge behind an eval-only flag over
  DBC-01 `LOG_ONLY`-flagged turns; (2) run the SAME confusion matrix; (3) compare to the CSV
  baseline (DBC 91.5% / 3.9% FP).
- **Result when**: a semantic detector beats the lexicon on detection **without FP regression**,
  reproduced by a committed script. (Execution detail lives in
  `nhid-dbc01-semantic-ceiling-campaign` — don't duplicate its phases.)

## Frontier 2 — Live in-call enforcement

- **Why SOTA falls short**: conformance today is post-hoc transcript review; nothing intervenes
  during the call.
- **Our asset**: a deterministic engine that never raises + a per-turn call-progress adapter
  (`adapters/call_progress_adapter.py`) + the `POST /v1/webhooks/call-progress` route + TwiML
  fallback machinery.
- **First 3 steps in-repo**: (1) measure per-turn `evaluate_all` latency; (2) set a latency
  budget against the NOCF `l_max_ms` default (`grep L_MAX_MS_DEFAULT src/nhid_cas.py` — do not
  assume the number); (3) prototype an in-call gate on the call-progress path that emits a TwiML
  redirect on a CRITICAL.
- **Result when**: a harness test shows a violating call redirected **mid-call** with bounded
  added latency.

## Frontier 3 — Cryptographic agent identity

- **Why SOTA falls short**: caller-ID and "trust me" are the norm; there is no offline-verifiable
  proof that a calling agent is who it claims.
- **Our asset**: NHID-Auth v2 — Ed25519 passports, delegation chains
  (`MAX_DELEGATION_HOPS` in `src/agent_identity.py`), a revocation store, and a CI determinism
  gate (`identity_determinism` in `nhid-gates.yml`).
- **First 3 steps in-repo**: (1) wire `POST /v1/identity/verify-passport` into the conformance
  path so identity verification is part of the decision; (2) add SIP attestation binding per
  `docs/sip-header-integration-feedback.md`; (3) publish signed verification vectors.
- **Result when**: a third party can verify an agent passport **offline** from the published
  vectors, with no access to this repo.

## Frontier 4 — Becoming the recognized standard

- **Why SOTA falls short**: vendor self-attestation is fragmented and unauditable.
- **Our asset**: a machine-readable conformance suite
  (`conformance/nhid_conformance_test_suite_v1.yaml`), a public confusion-matrix methodology, and
  a NIST/CMS comment trail.
- **First 3 steps in-repo**: (1) version and publish the CTS YAML as a citable spec artifact;
  (2) get one external vendor through `POST /v1/pilot/enroll`; (3) map the five controls to NIST
  AI RMF functions in a table (honest mapping, no unverified claims — `nhid-docs-and-positioning`).
- **Result when**: an external implementation passes the CTS **without this repo's help**.

## Cross-cutting discipline

Every frontier result must clear the same bar as any other measurement: disjoint-population
evaluation, no label leakage, reproducible as command + corpus + expected output
(`nhid-validation-and-qa`, `nhid-proof-and-analysis-toolkit`). A frontier is not an excuse to
lower the evidence bar.

## When NOT to use this skill

- Executing the semantic-detection work concretely → `nhid-dbc01-semantic-ceiling-campaign`.
- The discipline for turning a bet into an accepted result → `nhid-research-methodology`.
- Shipping anything that results → `nhid-change-control`.
- Wording public claims about any of this → `nhid-docs-and-positioning`.
- Siblings: `nhid-debugging-playbook`, `nhid-failure-archaeology`,
  `nhid-architecture-contract`, `nhid-domain-reference`, `nhid-config-and-flags`,
  `nhid-build-and-env`, `nhid-run-and-operate`, `nhid-diagnostics-and-tooling`,
  `nhid-validation-and-qa`, `nhid-proof-and-analysis-toolkit`, `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- Corpus size: `wc -l fixtures/fabricate/conversations.csv` (≈551 incl. header → 550 conv).
- Call-progress asset: `grep -n "call-progress\|call_progress" functions/handler.py adapters/call_progress_adapter.py`.
- Identity asset: `grep -n "MAX_DELEGATION_HOPS\|Ed25519\|revok" src/agent_identity.py`; determinism gate `grep -n identity_determinism .github/workflows/nhid-gates.yml`.
- Latency budget: `grep -n "L_MAX_MS" src/nhid_cas.py`.
- CTS artifact: `conformance/nhid_conformance_test_suite_v1.yaml`; pilot route: `grep -n "pilot/enroll" functions/handler.py`.
