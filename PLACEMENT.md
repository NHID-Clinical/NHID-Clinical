# Public reference bundle — NHID-Clinical

Verified, self-contained additions for the **public** `NHID-Clinical` repo
(the open reference / proposal). These files have **zero** dependencies on the
private SaaS code (no FastAPI, no Postgres, no billing, no telephony) — they
import nothing but Python's `typing` and `pytest`.

## What's here

| File | Drop into public repo at | Tests |
|---|---|---|
| `src/voice_policy.py` | `src/voice_policy.py` | — (the deterministic engine) |
| `tests/test_voice_policy.py` | `tests/test_voice_policy.py` | 32 written → **47 collected** (parametrized) |

After adding, the public repo's `python -m pytest tests/ -v` will run its
existing identity tests **plus** these 47 — all passing, still no live server
required.

## What was deliberately LEFT OUT (stays private, paid-tier asset)

- `TestVoiceWebhookPlanGate` — the L2+ monetization gate (12 tests)
- `TestVoiceIncoming` / `TestVoiceTranscript` — hosted SaaS endpoint internals (18 tests)

These are physically coupled to the private SaaS app (FastAPI + Postgres + billing)
and cannot run standalone, so they remain only in `NHID-Clinical-SaaS`.

## Safe way to publish (nothing is auto-pushed)

From a fresh clone of the **public** repo:

```bash
git clone https://github.com/NHID-Clinical/NHID-Clinical.git
cd NHID-Clinical
# copy the two files from this bundle into place:
#   src/voice_policy.py
#   tests/test_voice_policy.py
python -m pytest tests/ -v        # confirm everything passes
git add src/voice_policy.py tests/test_voice_policy.py
git commit -m "Add deterministic voice policy engine + conformance tests"
git push origin main
```
