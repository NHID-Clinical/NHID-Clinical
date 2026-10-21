"""
An internal error must not relax the gate
=========================================
`_internal_error_decision` is what every control returns when something inside
it raises unexpectedly. It returned `LOG_ONLY`, which is **priority 2** in the
enforcement ladder — above only `CONTINUE_AI`:

    DENY_DATA 5 > ESCALATE_HUMAN 4 > DISCLOSE_IDENTITY 3 > LOG_ONLY 2 > CONTINUE_AI 1

`evaluate_all` takes the most restrictive decision across the controls, so a
control that faulted contributed nothing and the composite became whatever the
remaining controls happened to say. Enforcement therefore degraded *silently*:
injecting a fault into PDX-01's helper turned a request for a member ID with no
disclosure from

    DENY_DATA / PDX01_PHI_GATE_TRIGGERED        (protected data refused)

into

    DISCLOSE_IDENTITY / IDG01_DISCLOSURE_MISSING  (agent asked to disclose)

Asking the agent to disclose does not stop the data exchange. Worse, the
composite reason code named IDG-01, so nothing in the decision indicated that
the PHI gate had failed at all — an operator reading the audit record would see
a disclosure finding, not a broken control.

The docstring called `LOG_ONLY` "a safe decision". For a gate standing in front
of protected health information, safe has to mean the patient's safety rather
than the call's. It now denies.

Checked before changing it: the Fabricate, voice-stress and governance corpora
report zero internal errors, so no pinned baseline moves — `check_baseline.py`
still prints DBC-01 183/200 with 5 FP and voice-stress false positives stay
0/95.
"""
from unittest.mock import patch

import pytest

import src.nhid_policy_engine_v1 as engine
from src.nhid_policy_engine_v1 import PolicyAction, evaluate_all

CONTROL_HELPERS = {
    # helper -> the control whose evaluation depends on it
    "_speech_contains_phi_request": "PDX-01",
    "_asserts_nonhuman_identity": "IDG-01",
    "_assertion_implies_human": "DBC-01",
}


def _boom(*_args, **_kwargs):
    raise RuntimeError("injected fault inside the control")


def _event(speech="what is the member id number", disclosed=False,
           assertion=None, phi=("member_id",)):
    return {
        "event_id": "e-fail-closed",
        "timestamp": "2026-10-21T10:00:00.000Z",
        "session_id": "CA-fail-closed",
        "request_id": "r-fail-closed",
        "event_type": "POLICY",
        "actor_id": "agent",
        "counterparty_type": "human_operator",
        "state_before": "ACTIVE",
        "state_after": "ACTIVE",
        "replay_mode": "live",
        "external_calls_cached": False,
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "healthcare_governance": {
            "disclosure_timestamp": "2026-10-21T09:59:00.000Z" if disclosed else None,
            "identity_assertion_text": assertion,
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": list(phi),
        },
        "input_payload": {"speech_text": speech, "raw_form_fields": None},
    }


SESSION = {"turn_count": 1, "escalation_path_available": True,
           "counterparty_type": "human_operator"}


def test_the_internal_error_decision_denies():
    decision = engine._internal_error_decision("unit test")
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "INTERNAL_POLICY_ERROR"


def test_a_fault_is_still_distinguishable_from_a_real_violation():
    """Both deny, so the reason code has to carry the difference — otherwise a
    broken control and a caught attack look identical in the audit record."""
    fault = engine._internal_error_decision("unit test")
    real = evaluate_all(SESSION, _event())
    assert fault.action == real.action == PolicyAction.DENY_DATA
    assert fault.reason_code == "INTERNAL_POLICY_ERROR"
    assert real.reason_code != "INTERNAL_POLICY_ERROR"
    assert any(v.rule_id == "ATR-01" for v in fault.violations), (
        "a fault must still be recorded against the audit control"
    )


def test_the_baseline_case_denies_without_any_fault():
    """The control. Without it, every test below could pass by always denying."""
    decision = evaluate_all(SESSION, _event())
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_PHI_GATE_TRIGGERED"


@pytest.mark.parametrize("helper,control", sorted(CONTROL_HELPERS.items()))
def test_a_fault_inside_a_control_still_denies(helper, control):
    with patch.object(engine, helper, _boom):
        decision = evaluate_all(SESSION, _event())
    assert decision.action == PolicyAction.DENY_DATA, (
        f"a fault in {control} relaxed the composite to {decision.action.name}"
    )


def test_a_fault_in_the_phi_gate_does_not_downgrade_to_disclose_identity():
    """The exact regression: DENY_DATA became DISCLOSE_IDENTITY, which does not
    stop protected data being exchanged."""
    with patch.object(engine, "_speech_contains_phi_request", _boom):
        decision = evaluate_all(SESSION, _event())
    assert decision.action != PolicyAction.DISCLOSE_IDENTITY
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "INTERNAL_POLICY_ERROR"


def test_a_fault_denies_even_when_no_other_control_objects():
    """Disclosure recorded and honest, so PDX-01's scope gate is the only thing
    between the caller and the data. A fault there used to leave nothing."""
    event = _event(disclosed=True, assertion="I am an automated assistant")
    with patch.object(engine, "_speech_contains_phi_request", _boom):
        decision = evaluate_all(SESSION, event)
    assert decision.action == PolicyAction.DENY_DATA


@pytest.mark.parametrize("control_fn", [
    "evaluate_idg01", "evaluate_pdx01", "evaluate_dbc01",
    "evaluate_eit01", "evaluate_atr01",
])
def test_a_control_replaced_wholesale_still_denies(control_fn):
    """Belt and braces: if an evaluator raises before its own handler runs,
    `evaluate_all`'s outer handler is what answers, and it must also deny."""
    with patch.object(engine, control_fn, _boom):
        decision = evaluate_all(SESSION, _event())
    assert decision.action == PolicyAction.DENY_DATA


def test_log_only_is_still_reachable_for_its_real_purpose():
    """The fix must not remove LOG_ONLY from the ladder — it is a legitimate
    outcome for an incomplete audit record, just not for a crashed control."""
    assert PolicyAction.LOG_ONLY in set(PolicyAction)
    # An event missing ATR-01's required fields is the genuine LOG_ONLY case.
    sparse = _event()
    del sparse["request_id"]
    decision = engine.evaluate_atr01(SESSION, sparse)
    assert decision.action == PolicyAction.LOG_ONLY
