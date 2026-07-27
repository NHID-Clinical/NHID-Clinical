# PolicyAction Authority Consolidation Plan

**Purpose:** designate one authoritative `PolicyAction` vocabulary and retire the divergent
copies — a prerequisite for Chapter 10 (Enforcement Profile) to reference "PolicyAction"
unambiguously. **This document changes no runtime behavior.** It records the current state and a
behavior-preserving migration sequence.

## Current state (verified by import audit)

| Module | Vocabulary | Live consumers | Verdict |
| :--- | :--- | :--- | :--- |
| **`src/nhid_policy_engine_v1.py`** | `DISCLOSE_IDENTITY, ESCALATE_HUMAN, DENY_DATA, CONTINUE_AI, LOG_ONLY` | CTS runner, all adapters + their tests, `functions/handler.py` (live Lambda), Twilio/ElevenLabs handlers, `webplatform/nhid_bridge.py`, `synthetic_eval_loop`, pilot kit | **Authoritative.** It is the vocabulary the Conformance Test Suite asserts via `expected_policy_action`. |
| `nhid_policy.py` (root) | `DISCLOSE, ESCALATE, BLOCK, ROUTE_LLM, ERROR` | `app.py`, `scripts/test_runner.py` | **Deprecate.** Divergent vocabulary. |
| `src/nhid_policy.py` | *(byte-identical duplicate of root `nhid_policy.py`)* | — (import-compatible dup) | **Delete the redundant copy** — two identical files is pure liability. |
| `src/voice_policy.py` | own `DisclosureState` / decision model | `nhid_api_endpoints.py` (live via `main:app`), its own tests | **Decide & document** (see Step 4). |

**Live-path note:** the uvicorn entrypoint (`Procfile → main:app`) mounts *both* the legacy
`app.py` engine (root `nhid_policy`) *and* `nhid_api_endpoints` (`voice_policy`), while the AWS
Lambda path (`template.yaml → functions.handler`) uses the authoritative v1 engine. Three action
vocabularies are therefore live simultaneously. This is pre-existing debt that the Enforcement
Profile work surfaces; it does not originate here.

## Target end-state

Exactly one importable `PolicyAction` (the five values from `src/nhid_policy_engine_v1.py`) on
every live path. `tests/test_enforcement_profile.py::test_policyaction_vocabulary_is_exactly_the_five_values`
is the standing guard against regression.

## Migration sequence (each step behavior-preserving; run full suite + guards after each)

0. **(this release — done)** Pin the authoritative enum with a vocabulary-stability test. Publish
   Chapter 10 naming `src/nhid_policy_engine_v1.PolicyAction` as authoritative. *No code moved.*
1. **De-duplicate the identical pair.** Make `src/nhid_policy.py` re-export from root
   `nhid_policy.py` (or vice-versa) so there is a single definition; confirm `app.py` and
   `scripts/test_runner.py` imports still resolve. Byte-identical duplication is removed with zero
   semantic change.
2. **Adapter, not rewrite, for the legacy vocabulary.** Add an explicit, deprecated mapping from
   the legacy actions to the authoritative ones (`BLOCK→DENY_DATA`, `ESCALATE→ESCALATE_HUMAN`,
   `DISCLOSE→DISCLOSE_IDENTITY`, `ROUTE_LLM→CONTINUE_AI`, `ERROR→LOG_ONLY`) so `app.py` can emit the
   authoritative vocabulary without touching control logic. Mark the legacy enum `@deprecated`.
3. **Migrate `app.py`** to consume `evaluate_all` (preferred) or the Step-2 adapter. Decide whether
   `app.py`'s class-based `NHIDPolicyEngine` is still a needed surface or a legacy demo that can be
   retired behind the v1 engine.
4. **Resolve `voice_policy.py`.** Maintainer decision required: is `nhid_api_endpoints.py` a live
   conformance surface or a legacy/demo path? Then either (a) map its decisions onto the
   authoritative `PolicyAction` and document the relationship, or (b) explicitly scope it as a
   non-normative transcript-chunk pre-filter that is **not** the conformance engine.
5. **Remove the legacy vocabulary** once no live path imports it; ship as a minor release with a
   deprecation note. The vocabulary-stability test continues to guard the single definition.

## Timing

The Chapter 10 documentation and the vocabulary-stability test (Step 0) ship now and are
independent of Steps 1–5. Steps 1–2 (de-dup + adapter) are low-risk and SHOULD precede publishing
Chapter 10 as fully normative, so "maps to `PolicyAction`" resolves to a single definition.
Steps 3–5 touch live entrypoints and MUST each be verified against the full suite + guards; they
are sequenced after this spec-maturity release.
