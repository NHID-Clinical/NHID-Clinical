---
name: nhid-build-and-env
description: >-
  Load when you need to set up, build, or reproduce the NHID-Clinical environment from
  scratch, or when the test suite won't run / gives the wrong count / the 18 integration
  tests behave unexpectedly. Load it on a fresh clone, when `pytest` errors on import,
  when `scripts/validate_ci.py` fails, when you need the FHIR/middleware/Java toolchains,
  or before a deploy. It is the from-zero runbook with the known traps (reportlab,
  middleware, Java, the committed DB). Trigger phrases: "set up the repo", "run the
  tests", "330 passed", "18 skipped", "recreate the env", "how do I build/deploy this".
---

# NHID-Clinical Build & Environment

Verified as of 2026-07-04. Python **3.11**. The suite must report exactly **330 passed /
18 skipped**.

## From zero to green (copy-paste)

```bash
cd /home/user/NHID-Clinical
python3 -m venv .venv && source .venv/bin/activate      # Python 3.11
pip install -r requirements.txt
python -m pytest tests/ -q                                # expect: 330 passed, 18 skipped
python scripts/validate_ci.py                             # expect: CI PASS: 330 passed
```

`requirements.txt` pins: fastapi, httpx, pytest, pytest-asyncio, pydantic, uvicorn,
python-multipart, pyyaml, jsonschema, cryptography, openai, python-dotenv, PyJWT.

## Why 18 tests skip (this is correct)

The 18 skips are `tests/failure_injection_harness.py` — integration tests that need a live
FastAPI server. To run them, start the server in another shell FIRST:

```bash
uvicorn app:app --reload --port 8000          # exact command from the harness docstring
# then, in the venv:
python -m pytest tests/failure_injection_harness.py -v
```

The harness points at `NHID_BASE_URL` (default `http://127.0.0.1:8000`) and hits
`/voice/process` and `/debug/replay/...`. `scripts/validate_ci.py` treats a skip count of `0`
or `18` as OK; any other skip count FAILS.

## Known traps

| Trap | What happens | Fix |
|---|---|---|
| `reportlab` missing | `scripts/generate_pdfs.py` fails; it is NOT in `requirements.txt` | `pip install reportlab` only if you need PDF generation |
| `middleware/` is separate | It is a Node/TypeScript package (~66 TS tests), not covered by pytest | `cd middleware && npm install && npm test` |
| FHIR CI gate | `.github/workflows/nhid-gates.yml` `fhir_validation` needs Java 17 + `validator_cli.jar` | only needed for that gate; skip locally unless testing FHIR |
| Committed `nhid_events.db` | A real SQLite file is committed at repo root and can carry state | tests monkeypatch `DB_PATH` to tmp; don't rely on the committed DB's contents |
| `asyncio_mode = strict` | async tests need explicit markers | already configured in `pytest.ini` |
| `*_harness.py` collected | `pytest.ini` `python_files` includes `*_harness.py` | expected; that's how the 18 get collected |
| `tests/demo` excluded | `addopts = --ignore=tests/demo` | run demo tests separately (see Makefile target) |

## Deploy paths

- **AWS SAM** (primary): `template.yaml` + `Makefile` (`make build`, `make deploy`; SAM
  `--parameter-overrides` forward Turnstile/ElevenLabs/Twilio env). This deploys the Lambda
  handler (`functions/handler.py`).
- **Railway** (alt): `Procfile` + `railway.toml` run the FastAPI app.

## Sanity check before you trust the env

```bash
python -c "import fastapi, cryptography, jwt, yaml, jsonschema; print('deps ok')"
python -m pytest tests/ --co -q | tail -1     # collection count (currently 348 collected)
python scripts/validate_ci.py                 # CI PASS: 330 passed
```

## When NOT to use this skill

- A test fails for a *logic* reason (silent-zero, leakage, routing) → `nhid-debugging-playbook`.
- Config values / env var meanings → `nhid-config-and-flags`.
- Operating a running server / the review queue → `nhid-run-and-operate`.
- Adding a test or the count-propagation rules → `nhid-validation-and-qa` / `nhid-change-control`.
- Siblings: `nhid-failure-archaeology`, `nhid-architecture-contract`, `nhid-domain-reference`,
  `nhid-diagnostics-and-tooling`, `nhid-docs-and-positioning`,
  `nhid-dbc01-semantic-ceiling-campaign`, `nhid-proof-and-analysis-toolkit`,
  `nhid-research-frontier`, `nhid-research-methodology`, `nhid-corpus-heuristic-mining`.

## Provenance and maintenance

- Expected counts: `grep -nE "UNIT_EXPECTED|INTEGRATION_EXPECTED" scripts/validate_ci.py`.
- Live verification: `python -m pytest tests/ -q | tail -1` and `python scripts/validate_ci.py`.
- Server command: `sed -n '1,25p' tests/failure_injection_harness.py`.
- Deps: `cat requirements.txt`. Deploy: `cat Makefile template.yaml Procfile 2>/dev/null | head`.
- If the counts differ from 330/18 when you read this, trust the suite and update this file.
