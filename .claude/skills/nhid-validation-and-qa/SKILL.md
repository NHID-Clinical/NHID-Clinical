---
name: nhid-validation-and-qa
description: >-
  Load when you need to know what counts as EVIDENCE in NHID-Clinical, whether a result
  is acceptable, or how to add/modify a test correctly. Load it before claiming a change
  works, before adding a test, before trusting a detection number, or when reviewing
  someone's "it passed" claim. It defines the evidence bar (disjoint populations, one
  mechanism explains all observations, label leakage is the cardinal sin), the golden
  inventory (the 330-test suite, the 18 CTS cases, the corpora), and the test-adding
  procedure. Trigger phrases: "is this good enough", "how do I add a test", "what's the
  acceptance bar", "is this evidence valid", "did we prove it".
---

# NHID-Clinical Validation & QA

Verified as of 2026-07-04. Detection numbers here are **engine measurements against synthetic
corpora — NOT conformance or certification claims.** Never upgrade a measurement to a
certification claim (see `nhid-docs-and-positioning`).

## The evidence bar

1. **Disjoint populations.** Detection is measured over conversations that declare the
   violation; false positives over the disjoint `scenario_type == "compliant"` set. A number
   that mixes them is invalid. (Tool: `scripts/confusion_matrix.py`, see `nhid-diagnostics-and-tooling`.)
2. **One mechanism must explain ALL observations, including negatives.** Exemplar: the v1.1
   repair separated three causes and the label-leakage hypothesis explained BOTH why EIT looked
   perfect AND why de-leaking it didn't crater it (~98% held). A hypothesis that only explains
   the positives is not accepted.
3. **Label leakage is the cardinal sin.** *Label leakage* = any detector input that is derived
   from the ground-truth label. Historical instance: the adapter set
   `escalation_path_available = not eit01_violation`, feeding the answer into the detector; the
   resulting ~95–100% EIT "detection" was meaningless. Before trusting any eval, trace every
   detector input to its source (see `nhid-proof-and-analysis-toolkit` recipe 2).
4. **Zero-FP bar for lexicon additions.** A new phrase must add zero false positives on the
   corpus. Vet with `scripts/mine_heuristic_candidate.py` (procedure: `nhid-corpus-heuristic-mining`).
5. **Superseded, never deleted.** An invalidated number is annotated superseded with a pointer,
   not removed (archive §2.5 → §2.5.1). See `nhid-change-control`.

## The golden inventory

| Asset | What / where |
|---|---|
| Unit suite | **330 passed / 18 skipped** — per-file index in archive **§23.3** (verify the section number: `grep -n "23.3" docs/MASTER-KNOWLEDGE-ARCHIVE.md`). |
| CTS cases | 18 machine-readable cases in `conformance/nhid_conformance_test_suite_v1.yaml` (IDG/PDX/DBC/EIT/ATR + EDGE + BOT-TO-BOT), each with `expected_policy_action` / `expected_reason_code` / `expected_violations`. |
| Corpora | **In-repo**: `fixtures/fabricate/{conversations.csv,turns.csv}` (550 conv). **External** (referenced in §2.5.1, not committed): `nhid_v2_iso_corpus`, `nhid_adversarial_battery`, `nhid_baseline_corpus`. Only claim numbers for corpora you can actually run. |
| Integration | 18 skipped tests = `tests/failure_injection_harness.py`; the only path that exercises ATR-01. |

## How to add a test

1. Place it under `tests/` in a `test_*.py` file (or a `*_harness.py` for server-dependent
   integration tests — those will skip without a live server).
2. Run `python -m pytest tests/ -q` and confirm the delta you expect.
3. If the passing count changed, do **atomic count-propagation** — the full checklist lives in
   `nhid-change-control` (validate_ci.py, ci.yml job name, CONTRIBUTING, README, archive live
   rows). Do not update historical archive rows.
4. Confirm `python3 scripts/validate_ci.py` prints the new `CI PASS: N passed`.

## When a test itself encoded a bug: rewrite in place

If a test asserts behavior that *was* the bug, rewrite the assertion in place and mark it with a
`v1.1 CONTRACT CHANGE`-style comment; keep the net method count stable so no propagation is
needed. **Precedent**: the v1.1 repair rewrote 3 tests in `tests/test_fabricate_adapter.py`
(`TestEscalationPathAvailable` → `TestEscalationOutcome`, and the sticky-disclosure test) —
net count 0. Verify: `grep -n "CONTRACT CHANGE" tests/test_fabricate_adapter.py`.

## When NOT to use this skill

- How to run the measuring tools → `nhid-diagnostics-and-tooling`.
- The rules/gates for a change → `nhid-change-control`.
- The analysis methods themselves → `nhid-proof-and-analysis-toolkit`.
- Phrase-vetting decision → `nhid-corpus-heuristic-mining`.
- Docs/claims discipline → `nhid-docs-and-positioning`.
- Siblings: `nhid-debugging-playbook`, `nhid-failure-archaeology`,
  `nhid-architecture-contract`, `nhid-domain-reference`, `nhid-config-and-flags`,
  `nhid-build-and-env`, `nhid-run-and-operate`, `nhid-dbc01-semantic-ceiling-campaign`,
  `nhid-research-frontier`, `nhid-research-methodology`.

## Provenance and maintenance

- Suite counts: `python -m pytest tests/ -q | tail -1`; `grep UNIT_EXPECTED scripts/validate_ci.py`.
- Test index section: `grep -n "23.3\|test file" docs/MASTER-KNOWLEDGE-ARCHIVE.md`.
- CTS cases: `grep -c "test_id\|- id" conformance/nhid_conformance_test_suite_v1.yaml`.
- Contract-change precedent: `grep -n "CONTRACT CHANGE" tests/test_fabricate_adapter.py`.
