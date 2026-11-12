# Changelog

## [Unreleased] - 2026-09 to 2026-11

- **Wording and records brought in line with the claim boundaries, 2026-11-12 (#470).** The news
  entry no longer says a shadow evaluation helps "shape the standard"; it says "framework"
  (`feed.xml`, `docs/release-history.md`). The FAQ defines Impersonation Latency as
  `docs/terminology.md` does, the time from call start to the agent's disclosure, where it had
  said the time until the person "realizes"; the JSON-LD copy matches. The evidence pack's
  "System behavior guarantees" section is now "Tested engine properties" on the page, in the
  cards that link to it, in the site search index and in the Evidence Pack PDF's source; the four
  properties and their text are unchanged. The archived Evidence Pack PDF in `specs/archive/` is a
  snapshot and was not rebuilt, so it keeps the old heading. The `community.html` redirect pointed at a missing
  FAQ anchor and now goes to `/about.html#community`; `docs/ia-disposition.md` lists the same
  three redirect targets as `scripts/ia/redirects.txt`. The FAQ hero says fifteen questions, the
  README heading says four paths, and the maintainer line states the degree as in progress and
  lists every credential. The author's `sameAs` adds her personal GitHub profile. Handoff docs
  and the PowerShell module point at the current AI Governance Map and repository URLs. No
  control semantics, baseline, stage or published count changed (2525).
- **Home page: the AI caller supplies the patient's identifiers, not the payer (#469).** The hero
  had the agent ask the payer to "confirm the member ID on claim 48213", which ran the call
  backwards. The agent now states the member ID and claim number itself; the fixture and page
  are regenerated from the engine and the chips are unchanged. `tests/test_call_direction.py`
  catches "can/could you confirm the member ID / date of birth / NPI" and reads the generated
  hero script. The adversarial corpus's ordinary-call control case had the same line and was
  reworded, still with no violations.
- **Site: device theme, icon set, hero call played in order (#468).** With no stored choice the
  site follows the device's colour scheme, and only the reader's own click on the toggle is
  remembered. `favicon.ico`, the touch and maskable icons and a web manifest are rendered from
  `assets/brand/favicon.svg` by `scripts/seo/build_icons.cjs`. The hero transcript arrives turn
  by turn; it is complete in the HTML and reduced motion skips the animation. No wording, claims
  or control semantics changed.
- **Robot to robot: the payer's own AI answers the caller-agent's call (#467).** The canonical
  direction is unchanged: the caller-agent places the call and the controls judge it. `gate_turn`
  takes `counterparty` `human_operator` or `ai_agent`. `src/agent_to_agent.py` adds a
  deterministic reference payer AI that releases a claim status only when the gate allowed the
  turn and verified the caller's delegation; `nhid agent-to-agent` runs seven offline scenarios.
  `docs/agent-to-agent-calls.md` names the canonical direction first. Offline only; no payer runs
  it. No control semantics, baseline or control count changed. Suite 2509 -> 2525 passed.
- **Calling-agent orientation, production-readiness decisions, buyer CTA, ACC-01 inside PDX-01,
  consented-recordings scorer (#466).** The gate and the post-call replay orient a calling
  agent's turns through one module (`src/call_replay.py`), with no behaviour change.
  `docs/production-readiness.md` records the seven open decisions between NHID-Auth v2 and
  production use; none is closed and nothing is called production ready. Every published page
  offers "Request a shadow pilot", a prefilled email with nothing stored, and
  `POST /v1/pilot/enroll` now answers `not_recorded` where it had answered "enrolled" while
  storing nothing. ACC-01 record-level access is a prototype check inside PDX-01, off unless
  `DelegationContext.require_record_access` is set, and not a control of its own; it reproduces
  its 20 fixtures. `nhid audio-robustness --audio-dir` scores consented volunteer recordings
  (tier 4); real speech is still not measured. Suite 2457 -> 2509 passed.

- **Records brought up to date, 2026-10-30.** The privacy policy now says that ElevenLabs places
  and answers the demonstration calls over Twilio, records and transcribes them, and keeps the
  recording and transcript until deleted; that NHID-Clinical keeps only per-call results without
  the phone number or transcript; and that the demonstration uses fictional details only. Its
  summary no longer says data is "never" shared. `docs/project-state.md` re-measured at `0ef59fc`
  (2065 passed with the API running, 2044 passed and 21 skipped without it, 87 test files) with a
  §14 state-change entry for #407–#435.

- **ElevenLabs demonstration revived; the agent is renamed Ida.** The post-call webhook reads ElevenLabs' real
  `{type, event_timestamp, data}` envelope (every real call was answered 400 before), ignores
  non-transcript event types, and is HMAC-authenticated (`ElevenLabs-Signature`, the official
  SDK's scheme and 30-minute tolerance; constant-time compare; fails closed on a missing secret).
  Turns are stamped call start + `time_in_call_secs`, so Impersonation Latency is measured in the
  call's own seconds, and missing timing is reported as not recorded rather than zero. Ida's
  own words are checked for patient identifiers, because it is the caller. ElevenLabs' evaluation
  criteria and data collection are stored beside the engine's result as vendor self-evaluation
  and never read by the engine. The agent ID comes from `ELEVENLABS_AGENT_ID`
  (`ElevenLabsAgentId`), and the webhook secret from `ELEVENLABS_WEBHOOK_SECRET`
  (`ElevenLabsWebhookSecret`). The adapter moved out of `adapters/archive/`. The shadow-evaluation
  guide's demo section describes both lines accurately and is wired again. Setup:
  `docs/elevenlabs-demo.md`. The agent was called Beacon, a name a real behavioral-health company
  used, and it now calls for an unnamed demonstration dental practice, because its old
  fictional practice name belonged to real dental offices (`agents/ida_system_prompt.md`).
  Suite 2017 -> 2065 passed, 0 skipped (48 new tests, `tests/test_elevenlabs_postcall.py` and one
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
