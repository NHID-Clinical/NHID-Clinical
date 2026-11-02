"""
VER-01 call verification, run inside DLG-01 (opt-in).

VER-01 is not a sixth control (CLAUDE.md §3; the proposal's §4 says the same).
It is a further question DLG-01 asks when a deployment sets
``DelegationContext.require_call_verification``: was *this call* verified, by
the payer, for the delegation the agent presented? The engine performs no I/O,
so the payer's verifier (``src.call_verification``) runs first and its result
arrives in ``session["call_verification"]``.

Off by default: every existing DLG-01 test, conformance result and pinned
baseline is unchanged.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from src.call_verification import EXCEPTION, NOT_ASSESSABLE, PASS, UNKNOWN  # noqa: E402
from src.nhid_policy_engine_v1 import (  # noqa: E402
    DelegationContext,
    PolicyAction,
    evaluate_all,
    evaluate_dlg01,
)
from test_call_verification import World  # noqa: E402
from test_dlg01_delegated_authority import (  # noqa: E402,F401
    agent_keys,
    ctx,
    event,
    make_passport,
    manager,
    provider_keys,
    resolver,
    session,
)


def verification(result=PASS, delegation_id=None, reason_code=None):
    return {"result": result, "reason_code": reason_code, "delegation_id": delegation_id,
            "token_ref": "tok-ref", "redeemed_at": None, "binding_checks": {}}


@pytest.fixture
def passport(manager, provider_keys, agent_keys):
    return make_passport(manager, provider_keys, agent_keys, ["eligibility"])


def _dlg(passport, manager, resolver, call_verification="absent", **flags):
    extra = {} if call_verification == "absent" else {"call_verification": call_verification}
    return evaluate_dlg01(session(passport, manager, **extra), event(), ctx(resolver, **flags))


def test_off_by_default_a_failed_verification_is_ignored(passport, manager, resolver):
    decision, result = _dlg(passport, manager, resolver, verification(EXCEPTION))
    assert decision.action == PolicyAction.CONTINUE_AI
    assert decision.reason_code == "DLG01_DELEGATION_VERIFIED" and result.verified


def test_a_pass_for_this_delegation_continues(passport, manager, resolver):
    leaf = passport.delegation.delegation_id
    decision, result = _dlg(passport, manager, resolver, verification(PASS, leaf),
                            require_call_verification=True)
    assert decision.action == PolicyAction.CONTINUE_AI
    assert decision.reason_code == "DLG01_DELEGATION_VERIFIED" and result.verified


def test_a_missing_result_denies(passport, manager, resolver):
    decision, result = _dlg(passport, manager, resolver, require_call_verification=True)
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_CALL_NOT_VERIFIED" and not result.verified


@pytest.mark.parametrize("outcome", [EXCEPTION, UNKNOWN, NOT_ASSESSABLE])
def test_anything_but_pass_denies(passport, manager, resolver, outcome):
    leaf = passport.delegation.delegation_id
    decision, _ = _dlg(passport, manager, resolver,
                       verification(outcome, leaf, "TOKEN_ALREADY_REDEEMED"),
                       require_call_verification=True)
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_CALL_VERIFICATION_FAILED"
    assert decision.violations[0].rule_id == "DLG-01"


def test_a_pass_for_another_delegation_denies(passport, manager, resolver):
    decision, _ = _dlg(passport, manager, resolver, verification(PASS, "some-other-delegation"),
                       require_call_verification=True)
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_CALL_VERIFICATION_MISMATCH"


def test_no_passport_denies_because_a_call_token_is_bound_to_a_delegation(manager, resolver):
    decision, _ = evaluate_dlg01(session(None, manager, call_verification=verification()),
                                 event(), ctx(resolver, require_call_verification=True))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_NO_DELEGATION_PRESENTED"


def test_a_failed_delegation_is_reported_before_the_call_is_considered(
        manager, provider_keys, agent_keys, resolver):
    expired = make_passport(manager, provider_keys, agent_keys, ["eligibility"], ttl=-1)
    decision, _ = _dlg(expired, manager, resolver,
                       verification(PASS, expired.delegation.delegation_id),
                       require_call_verification=True)
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


# ── End to end: the prototype's real issue and redeem feed the engine ────────

def _engine_with_service(world, redeemed):
    context = DelegationContext(resolver=world.anchors, require_call_verification=True)
    sess = session(world.passport, world.m, call_verification=redeemed.to_trace_field())
    return evaluate_all(sess, event(call_sid="CA-1"), delegation=context)


def test_a_real_redemption_lets_the_engine_continue():
    world = World()
    handle = world.issue().dtmf_handle
    redeemed = world.redeem(handle)
    assert redeemed.result == PASS
    decision = _engine_with_service(world, redeemed)
    assert decision.action == PolicyAction.CONTINUE_AI


def test_a_replayed_redemption_makes_the_engine_deny():
    world = World()
    handle = world.issue().dtmf_handle
    assert world.redeem(handle).result == PASS
    replay = world.redeem(handle, call_sid="CA-2")
    assert replay.result != PASS
    decision = _engine_with_service(world, replay)
    assert decision.action == PolicyAction.DENY_DATA
    assert "DLG01_CALL_VERIFICATION_FAILED" in decision.reason_code
