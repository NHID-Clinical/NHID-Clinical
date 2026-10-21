"""
The call-binding experiment, under CI
=====================================
`experiments/call_bind/run.py` is the runnable demonstration; this is the same
matrix as a test, so the thirteen failure modes cannot quietly stop being
refused.

The assertion that matters is the permissive one. A case that denies with an
unexpected reason code is a diagnosis regression worth knowing about; a case
that *permits* is the bug the experiment exists to catch, so it is asserted
first and named loudly.

Four of the cases were live defects found by audit on 2026-10-21 — a chain
replayed onto another call, a chain narrowed to the empty scope, and the two
possession-proof cases, which no code could detect at all. They are pinned here
rather than only in the unit tests because the unit tests check a function and
this checks the decision a receiving organization would actually make.
"""
import pytest

from experiments.call_bind.run import (
    CASES,
    LATENCY_BUDGET_MS,
    evaluate,
    measure_latency,
    run_matrix,
)

# Run the matrix once for the whole module: each case mints fresh Ed25519 keys,
# and there is no reason to pay for that per assertion.
_ROWS = run_matrix()
_BY_NUMBER = {case.number: (case, outcome) for case, outcome in _ROWS}


def test_the_matrix_covers_every_declared_case():
    assert len(_ROWS) == len(CASES)
    assert {c.number for c in CASES} == set(range(len(CASES)))


@pytest.mark.parametrize("number", sorted(c.number for c in CASES if not c.expect_permitted))
def test_every_failure_mode_is_refused(number):
    """The permissive-failure assertion. One PERMIT here is the whole bug."""
    case, outcome = _BY_NUMBER[number]
    assert not outcome.permitted, (
        f"case {case.number} ({case.name}) was PERMITTED — "
        f"{outcome.action}/{outcome.reason_code}: {outcome.detail}"
    )


@pytest.mark.parametrize("number", sorted(c.number for c in CASES if c.expect_diagnosis))
def test_every_case_is_correctly_diagnosed(number):
    """Refusing for the wrong reason is still a defect: an operator reading the
    audit trail has to be able to tell a forged signature from a replay."""
    case, outcome = _BY_NUMBER[number]
    assert outcome.diagnosis == case.expect_diagnosis, (
        f"case {case.number} ({case.name}) diagnosed {outcome.diagnosis!r}, "
        f"expected {case.expect_diagnosis!r}"
    )


def test_the_correctly_formed_call_is_permitted():
    """A gate that denies everything is not a gate. Without this the matrix
    above could be satisfied by refusing all traffic."""
    case, outcome = _BY_NUMBER[0]
    assert case.expect_permitted
    assert outcome.permitted, (
        f"the happy path was denied: {outcome.action}/{outcome.reason_code}: "
        f"{outcome.detail}"
    )


# ── The four cases that were live defects ─────────────────────────────────────

def test_a_chain_replayed_onto_another_call_is_refused():
    """`validate_chain` passed no call_sid to any hop, so a chain minted for
    one call verified on any other — while the single-passport form of the
    identical attack was correctly refused."""
    _case, outcome = _BY_NUMBER[8]
    assert not outcome.permitted
    assert "ERR_NONCE_MISMATCH" in outcome.detail


def test_a_chain_narrowed_to_empty_scope_is_refused():
    """The empty set is a subset of every set, so this passed narrowing, and a
    `constrains_scope` requiring a non-empty scope then skipped the gate —
    making a sub-delegation that surrendered everything outrank its parent."""
    _case, outcome = _BY_NUMBER[9]
    assert not outcome.permitted
    assert outcome.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"


def test_presenting_captured_bytes_without_the_key_is_refused():
    """The passport's own agent signature covers static data, so possession at
    presentation was unprovable until a verifier challenge existed."""
    _case, outcome = _BY_NUMBER[12]
    assert not outcome.permitted
    assert "ERR_PROOF_MISSING" in outcome.detail


def test_a_stale_proof_is_refused():
    _case, outcome = _BY_NUMBER[13]
    assert not outcome.permitted
    assert "ERR_PROOF_STALE" in outcome.detail


# ── Latency ───────────────────────────────────────────────────────────────────

def test_verification_fits_inside_call_setup():
    """Measured on the accepting path, which is the slow one — a denial
    short-circuits, so the permitted call is what a caller waits through."""
    latency = measure_latency(repeats=20)
    assert latency["p95"] < LATENCY_BUDGET_MS, (
        f"p95 {latency['p95']:.2f}ms exceeds the {LATENCY_BUDGET_MS:.0f}ms budget"
    )


def test_the_experiment_reports_its_own_verdict():
    """`evaluate()` is what `run.py` and this module share; if it disagreed
    with the assertions above, the runnable experiment and CI could diverge."""
    failures, rows, latency = evaluate()
    assert failures == [], "; ".join(failures)
    assert len(rows) == len(CASES)
    assert latency["n"] > 0
