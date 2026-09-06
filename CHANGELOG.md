# Changelog

## [Unreleased] - 2026-09

- **Dual-licensed the repository.** Code is Apache-2.0 (`LICENSE`); specification and documentation
  prose stay CC BY 4.0 (`LICENSE-DOCS`); `NOTICE` states which tree each covers. The repository was
  previously CC BY 4.0 throughout, including every Python file — a licence Creative Commons advises
  against applying to software, with no patent grant and no warranty disclaimer written for code.
- **Evidence Diagram System.** Published figures are generated from the engine and the committed
  corpora rather than drawn; CI fails when a figure stops matching its source
  (`scripts/build_evidence_visuals.py --check`). The legacy external-asset visual layer was retired
  and `docs/visual-system.md` is normative. Retired files are unreferenced but not deleted.
- **Added `docs/payer-brief.md`** — a two-page brief for payer provider-services and
  payment-integrity leads, offering impersonation-latency measurement as an offline batch on
  de-identified transcripts. No hosted scoring endpoint exists or is planned: call audio is PHI.
- **Fixed `nightly-verify.yml`** (issue #385). A default shallow checkout made
  `tests/test_control_set_completeness.py` skip, reporting 1147 against a published 1148 — and the
  failing step was short-circuiting the three guards beneath it, so the nightly had been verifying
  less than it claimed. Added `fetch-depth: 0`, matching `ci.yml`.
- **Documentation consistency pass.** `MASTER-KNOWLEDGE-ARCHIVE.md` and `project-state.md` had
  drifted (nine current-state claims still said `987` against a suite of 1148) because neither was
  in `scripts/check_number_drift.py`'s surface list. Both are now covered, and the archive keeps a
  single canonical current-state block instead of nine restatements.
- **Withdrew the CAS trend API from the roadmap** and corrected a CAS-based value proposition in
  the archive: CAS was demoted to a research component in 2026-08 and `docs/claim-boundaries.md`
  prohibits surfacing it publicly.

## [v2.0] - 2026-06
- NHID-Auth v2 released: Ed25519 provider-signed agent passports, NPI binding, scoped delegation chains (max 3 hops), per-agent/per-delegation revocation, call-SID nonce binding
- ElevenLabs Conversational AI agent "Beacon" deployed (agent_4001krn32nmwe5t8mqzgee0w84rj) — outbound claim status caller, voice Eryn, Gemini 2.5 Flash
- ElevenLabs CTS runner: ATR-01 timestamp fix (per-message time_in_call_secs), EIT-01 persona fix (named human), credit-aware NOT_EXECUTED reporting
- Canonical agent prompt versioned at agents/beacon_system_prompt.md
- v2 fully open under CC BY 4.0 *(the code was relicensed Apache-2.0 in 2026-09; see Unreleased)*

## [v1.3] - 2026-06
- NPI validator + NHID-CAS scoring; 173 tests total
## [v1.2] - 2026-05
- Conformance test suite (18 YAML cases), failure traces
## [v1.1] - 2026-04
- Policy engine (IDG-01, DBC-01, EIT-01, ATR-01, CTS-05)
## [v1.0] - 2026-04
- Initial schema and specification; NIST-2025-0035-0026
