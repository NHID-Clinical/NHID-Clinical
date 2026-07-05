---
name: nhid-config-and-flags
description: >-
  Load when you need to know a configuration value, environment variable, threshold
  constant, or default in the NHID-Clinical repo, or when adding a new config axis. Load
  it before changing a CAS threshold, wiring a new env var, setting up a deploy, or
  debugging behavior that depends on a default (e.g. auth failing, the review threshold,
  demo rate limits). It is the catalog: every axis, its value, its defining file, whether
  it is production or experimental, and whether an env override exists. Trigger phrases:
  "what's the default for", "which env var controls", "CAS threshold", "where is X
  configured", "add a config flag", "NHID_API_KEY / NHID_JWT_SECRET / NHID_EVENT_DB".
---

# NHID-Clinical Config & Flags

Verified as of 2026-07-04. **Rule**: verify a value against its defining file before you rely
on it — the greps are in Provenance. Several "config" values are compile-time constants with NO
env override.

## Threshold constants (compile-time; NO env override)

Defined in `src/nhid_cas.py:9-12`:

| Constant | Value | Meaning |
|---|---|---|
| `CAS_VERIFIED_TRUST` | `0.90` | ≥ → "Verified Trust" / L2 badge |
| `CAS_CONDITIONAL_TRUST` | `0.75` | ≥ → "Conditional Trust" / L1; **< 0.75 is the human-review threshold** |
| `CAS_REVIEW_REQUIRED` | `0.50` | ≥ → "Review Required" |
| `CAS_DENIED_DEGRADED` | `0.20` | ≥ → "Denied / Degraded"; below → Hard Denial |

These are imported across modules (`_tier_for_cas`, `dbc01_review_routing`). Changing one is an
**engine-behavior** change — route through `nhid-change-control`. There is no env var for them.

## Version constants (compile-time)

`src/nhid_policy_engine_v1.py:25-27`: `NHID_SPEC_VERSION = "1.3"`,
`POLICY_ENGINE_VERSION = "1.0.0"`, `NHID_SCHEMA_VERSION = "1.0"`. Auth: `MAX_DELEGATION_HOPS = 3`
in `src/agent_identity.py`. `main.py` FastAPI app version is `1.4.0` (a different thing).

## Environment variables (by surface)

| Env var | Default | Surface | Notes |
|---|---|---|---|
| `NHID_API_KEY` | (unset) | FastAPI `main.py` | `X-API-Key` gate |
| `NHID_JWT_SECRET` | `nhid-dev-secret` | auth | **INSECURE DEFAULT — override in any real deploy** |
| `NHID_AUTH_DB` | `nhid_auth.db` | `nhid_attest.py`, `nhid_payer.py` | separate DB from events |
| `NHID_BASE_URL` | `http://127.0.0.1:8000` | test harness | where `failure_injection_harness.py` points |
| `NHID_EVENT_DB` | `nhid_events.db` | event store / harness | |
| `NHID_TIMEOUT` | `10` | harness | request timeout seconds |
| `OPENAI_API_KEY` | (unset) | `llm.py` | lazy-init client |
| `CLOUDFLARE_TURNSTILE_SECRET` | (unset) | demo | website demo only (fenced) |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_PHONE_NUMBER_ID` | (unset) | demo/agent | |
| `STARTER_PACK_URL` | (unset) | demo | |
| Twilio (`ACCOUNT_SID`/`AUTH_TOKEN`/`SMS_FROM` envs), DynamoDB table envs | (unset) | demo | forwarded via Makefile SAM `--parameter-overrides` |

## Flag-like knobs

| Knob | Where | Value |
|---|---|---|
| `UNIT_EXPECTED` | `scripts/validate_ci.py:3` | `330` (the test-count invariant) |
| `INTEGRATION_EXPECTED` | `scripts/validate_ci.py:4` | `18` (allowed skip count) |
| Demo rate caps | `functions/handler.py` (~lines 34-36) | window `3600`s, IP limit `5`, phone limit `3` |
| pytest `python_files` | `pytest.ini` | includes `test_*.py` and `*_harness.py` |
| pytest `addopts` | `pytest.ini` | `--ignore=tests/demo` (demo suite excluded by default) |
| `asyncio_mode` | `pytest.ini` | `strict` |

## DB paths

- `nhid_events.db` — repo-root SQLite (`nhid_event_store.py`, `DB_PATH`). **It is committed to
  the tree** and can carry state between runs; tests monkeypatch `DB_PATH` to a tmp file.
- `nhid_auth.db` — separate auth DB (`NHID_AUTH_DB`).

## How to add a config axis (checklist)

- [ ] Decide: compile-time constant (like CAS thresholds) or env var (like `NHID_API_KEY`)?
- [ ] Define it in ONE place; read it via a single accessor if env-based.
- [ ] Provide a safe default; if the default is insecure (like `NHID_JWT_SECRET`), document the
      override requirement in code and in `nhid-run-and-operate`.
- [ ] Add it to this catalog and to `.github/CONTRIBUTING.md` if operators need it.
- [ ] If it changes engine behavior or is a threshold, route through `nhid-change-control`.
- [ ] Add a re-verification grep to Provenance below.

## When NOT to use this skill

- What the CAS score/tiers *mean* → `nhid-domain-reference`.
- The rules for changing a threshold → `nhid-change-control`.
- Standing up the environment → `nhid-build-and-env`.
- Running a surface that uses these vars → `nhid-run-and-operate`.
- Siblings: `nhid-debugging-playbook`, `nhid-failure-archaeology`,
  `nhid-architecture-contract`, `nhid-diagnostics-and-tooling`, `nhid-validation-and-qa`,
  `nhid-docs-and-positioning`, `nhid-dbc01-semantic-ceiling-campaign`,
  `nhid-proof-and-analysis-toolkit`, `nhid-research-frontier`, `nhid-research-methodology`,
  `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- CAS thresholds: `grep -nE "CAS_(VERIFIED|CONDITIONAL|REVIEW|DENIED)" src/nhid_cas.py`.
- Versions: `grep -nE "VERSION|MAX_DELEGATION_HOPS" src/nhid_policy_engine_v1.py src/agent_identity.py`.
- Env vars: `grep -rn "os.environ\|getenv" main.py functions/handler.py nhid_attest.py nhid_payer.py tests/failure_injection_harness.py llm.py`.
- Test-count knobs: `grep -nE "UNIT_EXPECTED|INTEGRATION_EXPECTED" scripts/validate_ci.py`.
- Demo caps: `grep -nE "RATE_LIMIT|_DEMO_CALL" functions/handler.py`.
- pytest knobs: `cat pytest.ini`.
