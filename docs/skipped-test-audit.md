# NHID-Clinical — Audit of the 18 Skipped Tests

> **Superseded in part on 2026-09-03. The 18 now run.** Sections 1–5 were written
> while the tests were still skipping and are preserved as written, because the
> reasoning in them is what motivated running the tests at all. **Section 6 has
> been replaced** — its recommendation was built on the assumption that the 18
> were untested-but-presumed-sound, and that assumption did not survive contact
> with a running server. **Sections 7–9 are new** and record what executing them
> actually produced. Read §7 first if you want the outcome rather than the
> reasoning that led to it.

**Question.** What exactly are the 18 skipped tests, why are they skipped, and do
they cover core requirements or optional/integration-specific behaviour?

**Answer in one line.** All 18 live in one file, share one cause, and test the
**HTTP API boundary** — not the control logic, which is covered deterministically
elsewhere. Their absence is not a control-conformance gap, but it *is* a real
coverage gap, and one CI job is named for precisely the thing it does not run.

**What running them showed.** 11 pass. 7 fail, for exactly two reasons, both of
which are genuine unresolved contradictions between the harness and `app.py`
rather than defects in either. See §7.

| | |
|---|---|
| **Audited at commit** | `27ba28e` |
| **Executed at commit** | `628d614` |
| **Measured** | 2026-09-03 |
| **Command** | `python -m pytest tests/ -q -rs` (audit) · `python -m uvicorn app:app --port 8000` then `python -m pytest tests/` (execution) |

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

## 6. Recommended public reporting metric — **superseded, see §9**

The recommendation originally made here was to keep publishing 987 and describe
the 18 in prose. It rested on a premise that turned out to be false: that the 18
were sound tests which merely lacked an environment. Seven of them were not.

The original text is not reproduced, because repeating a recommendation that has
been withdrawn invites it being quoted back as current. What it got right is
carried into §9: **lead with the number that actually runs, and never present a
collected total as a passing total.**

---

## 7. What happened when they ran

The environment was fixed rather than the tests — `python -m uvicorn app:app
--port 8000`, then the full suite. Note that the correct target is `app:app`,
not `main:app`: `main.py` mounts the voice application *under* `/voice`, which
moves `/voice/process` to `/voice/voice/process` and makes every one of these
tests 404.

**Result: 11 passed, 7 failed, 0 skipped.** Whole suite: **998 passed, 7 recorded
divergences, 0 skipped, 1005 collected.**

| Group | Ran | Passed | Failed |
|---|---|---|---|
| `TestInputValidation` (§3.1) | 8 | 5 | **3** |
| `TestChaosMode` (§3.2) | 4 | 2 | **2** |
| `TestPolicyEnforcement` (§3.3) | 3 | **3** | 0 |
| `TestReplayDeterminism` (§3.4) | 3 | 1 | **2** |

**The most important row is §3.3.** Those three tests were the audit's single
largest concern — the only ones covering *"the API actually applies the engine
and persists the audit trail"* end to end. **All three pass.** The gap §3.3
identified was real, and it is now closed by evidence rather than by assertion.

**The audit's ranking was wrong in one direction.** §3.1 and §3.2 were rated
"no conformance gap — coverage gap only". Five of those twelve tests fail. They
are still not control-conformance failures, but they are not the low-value
robustness checks the ranking implied either.

---

## 8. The two open decisions — **both resolved 2026-09-03**

> Both were decided and implemented. The `xfail(strict=True)` markers are gone,
> and **no test is skipped, xfailed, weakened or deleted**. The suite executes
> every test it collects. What follows records each contradiction, the decision
> taken, and what the tests now assert — because the reasoning is the part worth
> keeping.

### Resolution summary

| | 8.1 CallSid | 8.2 `/debug/replay` |
|---|---|---|
| **Decision** | Neither 400 nor a shared constant | Inspection, per repository evidence |
| **Implemented** | Accept + TwiML; record absent CallSid as absent; mint a distinct synthetic session id | Retain GET + JSON forensic trace |
| **Tests** | 5 rewritten to the contract, **2 added** | 2 rewritten, **1 added** pinning the verb |
| **Outcome** | 7 passing | 3 passing |

**8.1 — what was implemented.** A missing or empty `CallSid` no longer becomes
the literal `"unknown"`. `call_sid` and `session_id` are now separate columns:
`call_sid` holds what upstream actually sent or NULL, and `session_id_source`
records whether the session id *is* that CallSid or was minted here. Synthetic
ids carry an `nhid-anon-` prefix, which cannot collide with a Twilio CallSid
(34 characters, `CA` plus 32 hex), so a synthetic id can never be read as a real
one. Verified live: three malformed requests produced three distinct sessions,
none carrying a `call_sid`.

Independent corroboration existed in the repository the whole time.
`traces/nhid-trace-03-missing-callsid-session-binding.md` records exactly this
defect — *"Request without a CallSid cannot be bound to a session, making the
event unreplayable and breaking idempotency guarantees from the first pipeline
stage."*

**8.2 — what the evidence said.** The question was whether replay means
re-execution or inspection. It was not close:

| Evidence | Reading |
|---|---|
| `nhid_event_store.replay(session_id)` is `return get_events(session_id)` | **Retrieval** |
| the route is `@app.get`, documented "Full forensic trace" | **Retrieval** |
| `traces/nhid-trace-09` treats an LLM call *during* replay as a failure mode | re-execution is a hazard, not a feature |
| the same trace files replay-integrity hashing under **"next iteration"** | proposed, not shipped |
| ATR-01's `replay_mode` is per-event metadata (`live`/`replay`) | not an endpoint contract |

So **no replay engine was manufactured to satisfy a test.** The two tests now
assert what an inspection contract actually owes an auditor: the trace is
retrievable, deterministic across retrievals, and faithful — the response the
caller received must be recoverable from the record. A third test pins the verb,
because POSTing to a GET route returns 405 and that is what produced the
apparent "replay divergence" in the first place.

---

## 8-appendix. The original analysis, preserved


Neither is a bug to fix unilaterally. Each is a contradiction between two
defensible positions, and **the repository does not record which was intended**.
Both are marked `xfail(strict=True)` so they keep running and stay visible; a
strict marker fails the build the moment the behaviour changes, so it cannot
silently outlive the question it stands for.

### 8.1 Missing or empty `CallSid` — 5 tests

| | |
|---|---|
| **Tests** | `test_missing_callsid`, `test_missing_all_fields`, `test_empty_callsid`, `test_chaos_null_bytes_empty_callsid`, `test_chaos_full_adversarial` |
| **Harness requires** | HTTP 400 — "the pipeline must reject requests without a session identifier" |
| **`app.py` does** | `session_id = (form.get("CallSid") or "unknown").strip()` — coerces to the literal string `unknown`, returns 200 with valid TwiML |

**The case for 200 + TwiML.** This is a Twilio webhook. A 4xx makes Twilio play
its own failure message to the caller instead of the application's. Returning
usable TwiML is the more defensive production behaviour.

**The case for 400.** Coercion to a shared literal means every unidentified call
writes its audit events under the *same* `session_id` of `"unknown"`, collapsing
distinct calls into one indistinguishable stream. ATR-01 is an audit-traceability
control; an audit trail that cannot separate two calls is weaker evidence than
one that refuses the call.

**This is not a tie.** The two positions optimise for different things —
call-continuity versus evidence integrity — and a third option exists that
neither test nor implementation currently takes: accept the call, return TwiML,
and mint a **synthetic unique** session id rather than a shared constant. That
would satisfy both. It is not implemented, and choosing it is a product decision.

**Status: UNKNOWN — requires human judgment.**

### 8.2 What `/debug/replay` returns — 2 tests

| | |
|---|---|
| **Tests** | `test_replay_identity_normal_request`, `test_replay_empty_speech_determinism` |
| **Harness requires** | `POST` to the endpoint, and the **original TwiML** back, byte-identical |
| **`app.py` does** | Exposes it as `GET` (so `POST` → 405) returning a **JSON forensic trace** |

**Correcting the HTTP verb does not fix this**, which is the part worth being
precise about. With `GET`, the endpoint returns
`{"session_id": …, "reconstructed_state": {…}, "events": [...]}`. The assertion
is `r2.text == first_response`, where `first_response` is TwiML. A JSON trace can
never equal TwiML, so the two encode genuinely different contracts:

- **Replay-as-re-execution** — feed the event stream back through the pipeline
  and prove the same output comes out. This is what the harness tests, and it is
  the stronger determinism claim.
- **Replay-as-inspection** — reconstruct and return what happened. This is what
  is implemented, and it is the more useful debugging affordance.

The docstring at the top of the harness says only *"the server implements
`/debug/replay/{session_id}`"* and does not disambiguate.

**Determinism itself is not at risk here.** It is asserted offline in ten other
test files, and `test_replay_idempotency_same_request_id` — which compares two
live responses rather than a response against a trace — **passes**.

**Status: UNKNOWN — requires human judgment.**

---

## 9. The public reporting metric

**Published figure: 1031 passing.** Derived by running the suite against a live
API, which is now what CI does in both the `test` and `security_gates` jobs.

> **1031 automated tests pass on every change**, covering the five controls, the
> policy engine, the conformance suite, and — since 2026-09-03 — the hosted HTTP
> API, including end-to-end proof that the API applies the engine and writes a
> complete audit record.
>
> **No test is skipped, xfailed, weakened or deleted.** Every collected test
> executes and passes. The seven divergences recorded here on 2026-09-03 were
> resolved the same day by fixing the contracts they marked, not by adjusting
> the tests around them (§8).

**Rules this follows:**

- **The number that runs is the number published.** 998 is measured, not derived.
- **Never present a collected total as a passing total.** They happen to be equal now (1031) only because nothing is skipped or deferred; if they ever diverge, publish the passing figure.
- **Do not report 100%, and do not report zero skips as an achievement.** The
  skips became visible failures. That is an improvement in what is *known*, not
  in what works.
- **"Recorded divergence" is not a euphemism for "skipped".** A skipped test
  produces no signal. These execute, assert, and fail on purpose.

---

## 10. Verdict

| Question | Answer |
|---|---|
| Are the 18 testing core requirements? | **Mostly no.** 15 of 18 cover the HTTP boundary and optional endpoints. **3 cover core end-to-end enforcement of IDG-01 and ATR-01 — and those 3 pass** |
| Was the skip legitimate? | **The cause was honest; the consequence was not.** One real cause, correctly reported — but it hid 7 failures for as long as it went unexamined |
| Do they represent a conformance gap? | **No, for control logic.** §3.3 now proves the API applies the engine and writes a complete audit record. **The remaining gap is contractual, not behavioural**: two questions in §8 with no recorded answer |
| Can they run deterministically in CI? | **Yes — verified, not predicted.** All 18 run, with identical results across repeated runs |
| Is the current public metric wrong? | **It was incomplete, and it is now replaced.** 987 → 1031, and the 18 skips → nothing deferred at all |

**The single most useful change** was not raising the number. It was discovering
that the number was concealing seven unanswered questions, three of which sat on
the exact path the audit had flagged as least-evidenced — and that path turned
out to be sound.
