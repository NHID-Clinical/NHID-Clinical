# Experiment: binding an agent delegation to the live call

**Status:** local mechanism experiment · **Added:** 2026-10-21 · CC BY 4.0

> This answers one question and no others: **can a receiving organization take a
> delegation credential, verify it offline, and bind it to the call actually in
> progress — before protected data is requested?**
>
> It runs entirely locally on synthetic credentials. It is **tier 4** on
> [`../../docs/validation/evidence-provenance-matrix.md`](../../docs/validation/evidence-provenance-matrix.md):
> a mechanism demonstration, not a pilot, not a deployment, and not independent
> validation.

## Run it

```bash
python experiments/call_bind/run.py --report
```

`tests/test_call_bind_experiment.py` runs the same matrix under pytest, so CI
keeps it honest without needing the script.

## The one inversion that matters

Today the only call identifier in the pipeline is `event["session_id"]`, which
the integrator supplies (`src/nhid_policy_engine_v1.py`, `evaluate_dlg01`). An
agent that supplies both the credential and the call identifier it should be
checked against is not being checked.

So in this experiment **the receiver takes the call identifier from its own
side** — standing in for the payer's telephony platform, which knows the call
id because it is a party to the call — and passes that to verification. The
credential never gets to say which call it is on.

## What it exercises

| # | Case | Expected |
| --: | :-- | :-- |
| 0 | correctly scoped, call-bound, possession proved | permitted |
| 1 | no credential presented | denied |
| 2 | expired delegation | denied |
| 3 | durably revoked delegation | denied |
| 4 | protected-data request outside delegated scope | denied |
| 5 | forged provider signature | denied |
| 6 | forged agent signature | denied |
| 7 | valid credential replayed on a different call | denied |
| 8 | replayed as a 2-hop chain on a different call | denied |
| 9 | chain narrowed to the empty scope | denied |
| 10 | NPI with no trust anchor | denied |
| 11 | delegation naming no provider | denied |
| 12 | challenged, no presentation proof | denied |
| 13 | challenged, stale presentation proof | denied |

Cases 8, 9, 12 and 13 exist because they were live defects, found by audit on
2026-10-21 and closed in the same change. They are in the matrix so a
regression shows up as a *permitted* call, which is the only form of this bug
that matters.

Reason codes **group by design** — two forged-signature cases both diagnose
`ERR_INVALID_SIG`, and that is correct, not a loss of resolution. The matrix
asserts each case is diagnosed with the error it should be, not that all
thirteen strings differ.

## Acceptance criteria

1. Every denial case denies. A single permitted row fails the experiment.
2. Every case carries its expected diagnosis.
3. Added verification latency stays within budget (see `run.py`), because this
   sits in front of a human waiting on a live line.

## What it establishes, and what it does not

**Establishes:** offline verification plus receiver-sourced call binding is
mechanically sound, correctly refuses all thirteen failure modes, and costs
little enough to sit in call setup.

**Does not establish:** that a credential can reach a payer's verifier at all.
That is a transport question, and it is unanswered — see below. It also says
nothing about trust establishment at scale, real-caller behaviour, acoustic
robustness, or payer willingness.

## Transport: one arm tested, one arm blocked

**Arm 1 — webhook payload (tested here).** The credential travels in the
call-start webhook the existing adapters already receive
(`adapters/twilio_adapter.py`, `vapi_adapter.py`, `retell_adapter.py`,
`call_progress_adapter.py`). This is the architecture's natural seam: those
adapters are the only place a call and an HTTP request already meet.

**Arm 2 — SIP header (not tested, blocked).** Carrying the credential in a SIP
header such as `Call-Info` would reach a payer whose platform is SIP-native,
but whether intermediate carriers preserve a custom header is an empirical
question about real networks, and answering it needs a carrier path this
project does not have. **It is recorded as unanswered, not as solved.** No
claim here depends on it.

## The thing no experiment closes

Nothing in this directory gets a payer or vendor to agree to *receive* a
credential at call setup. Until one does, this layer solves a problem no
counterparty has committed to accepting. That is the project's largest open
risk and it is not a software problem.
