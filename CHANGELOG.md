# Changelog

## [Unreleased] - 2026-09

- **Beacon demonstration revived (ElevenLabs).** The post-call webhook reads ElevenLabs' real
  `{type, event_timestamp, data}` envelope (every real call was answered 400 before), ignores
  non-transcript event types, and is HMAC-authenticated (`ElevenLabs-Signature`, the official
  SDK's scheme and 30-minute tolerance; constant-time compare; fails closed on a missing secret).
  Turns are stamped call start + `time_in_call_secs`, so Impersonation Latency is measured in the
  call's own seconds, and missing timing is reported as not recorded rather than zero. Beacon's
  own words are checked for patient identifiers, because it is the caller. ElevenLabs' evaluation
  criteria and data collection are stored beside the engine's result as vendor self-evaluation
  and never read by the engine. The agent ID comes from `ELEVENLABS_AGENT_ID`
  (`ElevenLabsAgentId`), and the webhook secret from `ELEVENLABS_WEBHOOK_SECRET`
  (`ElevenLabsWebhookSecret`). The adapter moved out of `adapters/archive/`. The shadow-evaluation
  guide's demo section describes both lines accurately and is wired again. Setup:
  `docs/elevenlabs-demo.md`.
  Suite 2017 -> 2063 passed, 0 skipped (46 new tests, `tests/test_elevenlabs_postcall.py` and one
  in `tests/test_handler_input_hardening.py`), measured with the API running.
- **IDG-01: a disclosure counts only if it was heard.** Platforms commonly log the full scripted
  disclosure even when the counterparty barged in and playback stopped before "automated". The
  engine now reads two optional `healthcare_governance` fields, `disclosure_interrupted` and
  `disclosure_heard_text`: an interrupted disclosure is credited only when the part actually played
  states a non-human identity, and an interrupted disclosure with no heard text is not credited.
  New reason code `IDG01_DISCLOSURE_INTERRUPTED` (CRITICAL, `DISCLOSE_IDENTITY`); PDX-01 keeps
  protected data gated until a disclosure has been heard. The Twilio, Vapi and call-progress
  adapters accept `interrupted` / `heard_text` per turn and report `DISCLOSURE_INTERRUPTED`
  events. Callers that send neither field see no change.
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
