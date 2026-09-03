# NHID-Clinical — Audit of the 18 Skipped Tests

**Question.** What exactly are the 18 skipped tests, why are they skipped, and do
they cover core requirements or optional/integration-specific behaviour?

**Answer in one line.** All 18 live in one file, share one cause, and test the
**HTTP API boundary** — not the control logic, which is covered deterministically
elsewhere. Their absence is not a control-conformance gap, but it *is* a real
coverage gap, and one CI job is named for precisely the thing it does not run.

| | |
|---|---|
| **Commit** | `27ba28e` |
| **Measured** | 2026-09-03 |
| **Command** | `python -m pytest tests/ -q -rs` |

---

## 1. All 18 share one file and one cause

Every skip is in `tests/failure_injection_harness.py`, emitted by a single
marker at line 137:

```python
requires_server = pytest.mark.skipif(
    not _server_reachable(),
    reason=f"NHID FastAPI server not reachable at {BASE_URL}. "
            "Start the server to run integration tests.",
)
```

`BASE_URL` defaults to `http://127.0.0.1:8000` (overridable via `NHID_BASE_URL`).
The tests exercise two endpoints that **do exist in this repository**:
`POST /voice/process` and `GET /debug/replay/{session_id}`, both defined in
`app.py` (lines 258 and 266).

**The published phrase "18 skipped integration tests" is accurate.** There is no
second skip cause anywhere in the suite.

## 2. The file's full shape

`tests/failure_injection_harness.py` collects **39 tests: 21 pass, 18 skip.**

| Class | Tests | Runs offline? | What it covers |
|---|---|---|---|
| `TestPolicyEngineUnit` | **21** | **Yes — all pass** | IDG-01, PDX-01, DBC-01, EIT-01, ATR-01, bot-to-bot, `evaluate_all`, never-raises |
| `TestInputValidation` | 8 | No | HTTP input hardening |
| `TestChaosMode` | 4 | No | Fault-injection and correlation-id headers |
| `TestPolicyEnforcement` | 3 | No | Control enforcement *through* the HTTP path |
| `TestReplayDeterminism` | 3 | No | `/debug/replay` identity and idempotency |

This is the key structural fact: **the same five controls are tested twice** —
once against the engine directly (21 tests, always run) and once through the API
(3 tests, skipped). The control logic is not what goes untested.

## 3. Per-test disposition

### 3.1 `TestInputValidation` — 8 tests · HTTP input hardening

`test_empty_speech_result` · `test_whitespace_only_speech` ·
`test_null_bytes_injection` · `test_null_bytes_only` · `test_missing_callsid` ·
`test_missing_all_fields` · `test_empty_callsid` · `test_very_long_speech`

| | |
|---|---|
| **Requirement covered** | None of the five controls. API robustness against malformed and hostile payloads |
| **Dependency** | Running FastAPI server |
| **Core or optional** | **Core to the hosted API**, optional to the framework. An organisation using the engine as a library never touches this path |
| **Deterministic in CI?** | **Yes.** No network, no clock, no external service — just the app |
| **Conformance gap?** | **No** — no control is defined by this behaviour. **Coverage gap: yes** |

### 3.2 `TestChaosMode` — 4 tests · fault-injection headers

`test_chaos_null_bytes_empty_callsid` · `test_chaos_correlation_id_header` ·
`test_chaos_failure_injection_header` · `test_chaos_full_adversarial`

| | |
|---|---|
| **Requirement covered** | Correlation-id propagation and deliberate failure injection |
| **Dependency** | Running server with chaos headers enabled |
| **Core or optional** | **Optional.** A debugging and resilience affordance |
| **Deterministic in CI?** | Yes |
| **Conformance gap?** | **No** |

### 3.3 `TestPolicyEnforcement` — 3 tests · the ones that matter most

`test_idg01_violation_triggers_disclosure` (IDG-01) ·
`test_escalation_trigger_in_speech` (ATR-01) ·
`test_audit_trail_completeness` (ATR-01)

| | |
|---|---|
| **Requirement covered** | IDG-01 and ATR-01 **end-to-end** — that the API actually applies the engine and persists the audit trail |
| **Dependency** | Running server **and** the event database |
| **Core or optional** | **Core** |
| **Deterministic in CI?** | Yes, if the server and event DB are started |
| **Conformance gap?** | **Partially yes — the most significant of the four groups.** The engine's IDG-01/ATR-01 logic is covered by 21 offline tests, but *engine-correct is not the same as API-applies-engine*. Nothing in CI proves the deployed path invokes the engine or writes a complete audit record |

### 3.4 `TestReplayDeterminism` — 3 tests · replay endpoint

`test_replay_identity_normal_request` · `test_replay_idempotency_same_request_id` ·
`test_replay_empty_speech_determinism`

| | |
|---|---|
| **Requirement covered** | Determinism and idempotency **through `/debug/replay`** |
| **Dependency** | Running server; two tests also need the event DB |
| **Core or optional** | Determinism is core; **this endpoint** is optional |
| **Deterministic in CI?** | Yes |
| **Conformance gap?** | **No.** Determinism is asserted offline in 10 other test files. The endpoint's own behaviour is uncovered |

## 4. A finding this audit surfaced

`.github/workflows/nhid-gates.yml` defines a job named **"abuse + input
hardening"** whose only relevant step is:

```yaml
- name: run failure injection suite (unit tests only)
  run: pytest tests/failure_injection_harness.py -v --disable-warnings
```

It never starts a server. The step's own label is honest — *"(unit tests only)"* —
but **the job's name is not.** The 12 tests that actually constitute abuse and
input hardening (§3.1, §3.2) are exactly the 12 that skip. The job reports green
having run 21 policy-engine unit tests and zero abuse tests.

The other server-dependent job, `nightly-verify.yml`'s *"Live API smoke"*, points
at a **deployed** AWS API Gateway URL and checks `/health` plus one adapter route.
It does not run these 18 tests either.

**Neither is broken. Both are mislabelled relative to what a reader assumes.**

## 5. Could they run in CI?

**Yes — all 18, deterministically.** Two routes exist, and neither requires
network, external services, or a live deployment:

1. **Start the app as a CI step.** `app.py` is in the repository; CI already
   installs `requirements.txt` and another job already does
   `from main import app; TestClient(app)`.
2. **Refactor to `fastapi.testclient.TestClient`.** Hermetic, in-process, no
   port binding — the more robust option.

Three tests additionally need the event database seeded; that is a fixture
question, not an environmental one.

**No recommendation to act is made here.** The instruction was not to modify
tests to eliminate the skipped count, and §6 does not depend on doing so.

## 6. Recommended public reporting metric

The current published phrasing — *"987 passing · 18 skipped · 1005 total"* — is
**accurate but incomplete**: a reader cannot tell what the 18 are or why they do
not run, and the natural assumption ("optional extras") understates §3.3.

**Recommended:**

> **987 automated tests run on every change**, covering the five controls, the
> policy engine, and the conformance suite.
>
> A further **18 integration tests exercise the hosted HTTP API** — input
> hardening, fault injection, end-to-end policy enforcement, and the replay
> endpoint. They require a running server and **are not currently executed in
> CI**. The control logic they cross-check is separately covered by the 987.

**Rules this follows:**

- **Lead with the deterministic number.** 987 is what actually runs.
- **Never present 1005 as "tests that run."** 987 + 18 = 1005 is arithmetic, not
  coverage.
- **Say what the 18 are**, so "skipped" is not read as "optional extras". §3.3 is
  not an optional extra.
- **Do not claim end-to-end API conformance** until §3.3 runs somewhere.

## 7. Verdict

| Question | Answer |
|---|---|
| Are the 18 testing core requirements? | **Mostly no.** 15 of 18 cover the HTTP boundary and optional endpoints. **3 cover core end-to-end enforcement of IDG-01 and ATR-01** |
| Is the skip legitimate? | **Yes.** One honest cause, correctly reported, with no second hidden cause |
| Do they represent a conformance gap? | **Not for control logic** — covered by 987 tests including 21 in this same file. **Yes for the deployed API path**: nothing in CI proves the API applies the engine or writes a complete audit record |
| Can they run deterministically in CI? | **Yes, all 18** |
| Is the current public metric wrong? | **Not wrong — incomplete.** See §6 |

**The single most useful change** is not raising the number. It is running §3.3's
three tests somewhere in CI, so the claim "the API enforces the controls" has
evidence behind it, and renaming the "abuse + input hardening" job to match what
it executes.
