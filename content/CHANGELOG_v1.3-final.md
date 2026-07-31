# CHANGELOG — v1.3 final

Closeout of the six "v1.4 (Future Scope)" milestone items. Shipped as **v1.3 final** —
no version bump, no v1.4 branding anywhere in code, docs, or site. The milestone is
closed; the spec version stays 1.3.

## Milestone item 5 — Cryptographic agent identity binding (NHID-Auth)

`src/agent_identity.py` (26 tests, already passing) was a complete, unwired library.
Closed the gap instead of rebuilding it:

- **New route** `POST /v1/identity/verify-passport` in `functions/handler.py`, following
  the existing `_handle_*` dispatch pattern next to `/v1/conformance/check`. Accepts a
  passport and optional `required_scope`, calls `verify_passport()`.
- **Durable revocation** — added a `revoked_delegations` table to `nhid_event_store.py`
  (same shape as `events`/`conformance_results`, reusing `_run_sqlite_with_retry()`),
  replacing the in-memory revocation dict so revocation survives process restarts.
- `agents/beacon_system_prompt.md`'s IDG-02 line and `roadmap.html` updated to say this
  is wired into the conformance API, not just a standalone library.
- New `tests/test_identity_api.py` (7 tests).

## Milestone item 6 — Production failure mode handling (network jitter, partial failures)

- **New** `src/nhid_network_resilience.py` — `retry_with_backoff` decorator mirroring
  `nhid_event_store.py::_run_sqlite_with_retry`'s shape: bounded retries with jittered
  exponential backoff on transient `httpx` exceptions (timeout, connection drop) or
  transient HTTP status codes (5xx, 429). Non-transient errors (4xx other than 429,
  programming errors) propagate immediately.
- Applied to the two previously-unprotected outbound POSTs in `functions/handler.py`:
  `_verify_turnstile()` (Cloudflare Turnstile) and the outbound-call POST inside
  `_handle_demo_call()` (ElevenLabs).
- New `tests/test_network_resilience.py` (7 tests): success-after-N-retries,
  exhausted-retries raises, non-transient errors don't retry.
- `traces/nhid-trace-10-partial-failure-boundary-violation.md` cross-references the new
  module as the structural fix for infrastructure-level partial failures, distinct from
  the trace's original policy-decision (DBC-01 LOG_ONLY) partial-failure scenario.

## Milestone items 1–4 (already substantially complete; closed out / documented)

- **Item 1 — Live registry**: `registry.html` + `content/registry_entries.json`, seeded
  empty. Self-attestation, not certification — consistent with the existing
  non-overclaiming stance.
- **Item 2 — Multilingual disclosure**: Spanish and Mandarin disclosure-variant
  instructions added to `agents/beacon_system_prompt.md`'s prompt fence (Beacon's
  control surface, not Compass's — Compass is an FAQ widget, not a disclosure-bearing
  call).
- **Item 3 — Outbound call guidance**: `docs/payer-initiated-calls.md` — how
  IDG-01/PDX-01/DBC-01 apply when the call direction is reversed.
- **Item 4 — SIP header integration feedback**: `docs/sip-header-integration-feedback.md`
  — a standards-feedback position paper proposing an `Identity-Disclosure` SIP header
  convention.

## Site-wide: community channels consolidated to GitHub

Discord and Reddit are no longer used for NHID-Clinical community discussion or
support. Every link and textual mention across the site, news content, READMEs, docs,
and scripts was removed or replaced with the GitHub-based equivalent:

- Community discussion → `https://github.com/NHID-Clinical/NHID-Clinical/discussions`
- Bug reports / change requests → `https://github.com/NHID-Clinical/NHID-Clinical/issues`

`news.html` carries a new announcement card documenting the move; the older
"Community Channels Open" announcement was updated with a forward pointer rather than
deleted, preserving the historical record.

## Test count

284 passed / 18 skipped (Python conformance suite), 66 passing (TypeScript
middleware) — up from 270/18 before this closeout (+7 identity-API route tests,
+7 network-resilience tests). `scripts/validate_ci.py`, `.github/workflows/ci.yml`,
`README.md` badges/prose, `.github/CONTRIBUTING.md`, `agents/compass_system_prompt.md`,
and `docs/MASTER-KNOWLEDGE-ARCHIVE.md` all updated to the new count in the same pass.
