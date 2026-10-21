"""
DLG-01 Delegated Authority Gate — regression tests
==================================================
Covers the wiring of src/agent_identity.py's authenticated delegation into the
deterministic policy path, and the delegated scope constraining PDX-01.

The controlling property throughout: DLG-01 is opt-in. Every test that omits a
DelegationContext asserts the engine behaves exactly as it did before the
control existed.
"""
import time

import pytest

from src.agent_identity import AgentIdentityManager
from src.nhid_policy_engine_v1 import (
    DelegationContext,
    PolicyAction,
    ViolationSeverity,
    evaluate_all,
    evaluate_dlg01,
    evaluate_pdx01,
)
from src.trust_anchor import StaticTrustAnchorResolver

PROVIDER_NPI = "1234567890"
OTHER_NPI = "9876543210"
CALL_SID = "CA-test-0001"


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def manager():
    return AgentIdentityManager()


@pytest.fixture
def provider_keys(manager):
    return manager.generate_agent_keys()


@pytest.fixture
def agent_keys(manager):
    return manager.generate_agent_keys()


@pytest.fixture
def resolver(manager, provider_keys):
    _, provider_pub = provider_keys
    return StaticTrustAnchorResolver(
        {PROVIDER_NPI: manager.public_key_to_b64(provider_pub)}
    )


def make_passport(
    manager,
    provider_keys,
    agent_keys,
    scope,
    npi=PROVIDER_NPI,
    ttl=3600,
    call_sid=CALL_SID,
):
    provider_priv, _ = provider_keys
    _, agent_pub = agent_keys
    delegation = manager.create_delegation(
        provider_priv,
        "voice-agent-001",
        agent_pub,
        scope=scope,
        ttl_seconds=ttl,
        call_sid=call_sid,
        provider_npi=npi,
    )
    sig = manager.sign_delegation(provider_priv, delegation)
    agent_priv, _ = agent_keys
    return manager.create_agent_passport(delegation, sig, agent_priv)


def session(passport=None, manager=None, **extra):
    s = {"turn_count": 1, "escalation_path_available": True}
    if passport is not None:
        s["agent_passport"] = passport
    if manager is not None:
        s["identity_manager"] = manager
    s.update(extra)
    return s


def event(speech="", phi_accessed=None, disclosed=True, call_sid=CALL_SID):
    """A fully-formed event.

    ATR-01's required audit fields are all populated deliberately: an
    incomplete event makes ATR-01 emit LOG_ONLY, which outranks CONTINUE_AI in
    the composite and would mask the DLG-01/PDX-01 outcome under test.
    """
    return {
        "event_id": "e-1",
        "session_id": call_sid,
        "request_id": "req-1",
        "timestamp": "2026-08-21T10:00:00.000Z",
        "event_type": "POLICY",
        "actor_id": "agent-001",
        "state_before": "ACTIVE",
        "state_after": "ACTIVE",
        "counterparty_type": "human_operator",
        "replay_mode": "live",
        "external_calls_cached": False,
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0.0",
        },
        "input_payload": {"speech_text": speech},
        "healthcare_governance": {
            "disclosure_timestamp": "2026-08-21T09:59:55.000Z" if disclosed else None,
            "identity_assertion_text": "I am an automated system",
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": phi_accessed or [],
        },
    }


def ctx(resolver, **kw):
    return DelegationContext(resolver=resolver, **kw)


# ── 1. Opt-in behavior — the non-negotiable property ───────────────────────

def test_absent_context_does_not_evaluate_delegation():
    decision, result = evaluate_dlg01(session(), event(), None)
    assert decision.action == PolicyAction.CONTINUE_AI
    assert decision.reason_code == "DLG01_NOT_EVALUATED"
    assert result.evaluated is False
    assert result.constrains_scope is False


def test_absent_context_leaves_evaluate_all_unchanged():
    ev = event(speech="can I get the member id", disclosed=True)
    assert evaluate_all(session(), ev).action == PolicyAction.CONTINUE_AI


def test_absent_delegation_with_optin_disabled_is_permitted(resolver):
    decision, result = evaluate_dlg01(session(), event(), ctx(resolver))
    assert decision.action == PolicyAction.CONTINUE_AI
    assert decision.reason_code == "DLG01_NO_DELEGATION_PRESENTED"
    assert result.evaluated is True and result.verified is False


def test_absent_delegation_with_requirement_enabled_denies(resolver):
    decision, _ = evaluate_dlg01(
        session(), event(), ctx(resolver, require_delegation=True)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_NO_DELEGATION_PRESENTED"
    assert decision.violations[0].rule_id == "DLG-01"


# ── 2. Verification outcomes ───────────────────────────────────────────────

def test_valid_delegation_verifies(manager, provider_keys, agent_keys, resolver):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, result = evaluate_dlg01(
        session(p, manager), event(), ctx(resolver)
    )
    assert decision.action == PolicyAction.CONTINUE_AI
    assert decision.reason_code == "DLG01_DELEGATION_VERIFIED"
    assert result.verified is True
    assert result.scope == frozenset({"eligibility"})
    assert result.provider_npi == PROVIDER_NPI


def test_expired_delegation_denies(manager, provider_keys, agent_keys, resolver):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"], ttl=-1)
    decision, result = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"
    assert "expired" in result.reason.lower()


def test_invalid_provider_signature_denies(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    other_priv, _ = manager.generate_agent_keys()
    p.signature_b64 = manager.sign_delegation(other_priv, p.delegation)
    decision, _ = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


def test_invalid_agent_signature_denies(manager, provider_keys, agent_keys, resolver):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    impostor_priv, _ = manager.generate_agent_keys()
    p.agent_signature_b64 = manager.sign_delegation(impostor_priv, p.delegation)
    decision, _ = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


def test_unknown_npi_has_no_trust_anchor(manager, provider_keys, agent_keys, resolver):
    """A well-formed delegation from an unanchored provider is still refused."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"], npi=OTHER_NPI)
    decision, result = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_TRUST_ANCHOR_UNRESOLVED"
    assert result.provider_npi == OTHER_NPI


def test_wrong_call_sid_denies(manager, provider_keys, agent_keys, resolver):
    """A passport minted for one call must not be replayed onto another."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, _ = evaluate_dlg01(
        session(p, manager), event(call_sid="CA-different-call"), ctx(resolver)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


def test_revoked_agent_denies(manager, provider_keys, agent_keys, resolver):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    manager.revoke_agent(p.delegation.agent_id)
    decision, result = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert "revoked" in result.reason.lower()


def test_revoked_delegation_denies(manager, provider_keys, agent_keys, resolver):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    manager.revoke_delegation(p.delegation.delegation_id)
    decision, result = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert "revoked" in result.reason.lower()


def test_require_call_binding_denies_an_unbound_delegation(
    manager, provider_keys, agent_keys, resolver
):
    """An unbound delegation authorizes any call until it expires.

    `verify_passport` skips the binding check when either side's call_sid is
    empty, which is right for the primitive — a delegation that names no call
    asserts no call. But it means a deployment relying on call binding gets no
    signal when a credential simply does not carry one. This makes that a
    deployment choice instead of a silent default.
    """
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"], call_sid="")
    decision, result = evaluate_dlg01(
        session(p, manager), event(), ctx(resolver, require_call_binding=True)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_NO_CALL_BINDING"
    assert result.verified is False


def test_require_call_binding_permits_a_bound_delegation(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, result = evaluate_dlg01(
        session(p, manager), event(), ctx(resolver, require_call_binding=True)
    )
    assert decision.action == PolicyAction.CONTINUE_AI
    assert result.verified is True


def test_an_unbound_delegation_is_permitted_by_default(
    manager, provider_keys, agent_keys, resolver
):
    """Opt-in: the requirement must not change behaviour for anyone who did
    not ask for it."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"], call_sid="")
    decision, _ = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.CONTINUE_AI


def test_require_call_binding_looks_at_the_leaf_not_the_root(
    manager, provider_keys, agent_keys, resolver
):
    """The leaf is the agent that makes the request, so it is the hop whose
    binding decides. A chain whose child is unbound fails the requirement even
    though its root is bound."""
    chain = build_chain(
        manager, provider_keys, agent_keys, ["eligibility"], ["eligibility"],
    )
    assert chain[0].delegation.call_sid == CALL_SID
    assert chain[1].delegation.call_sid == ""
    decision, _ = evaluate_dlg01(
        session(chain, manager), event(), ctx(resolver, require_call_binding=True)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_NO_CALL_BINDING"


def test_durable_revocation_is_honoured(manager, provider_keys, agent_keys, resolver):
    """A revocation recorded outside this process must reach the control.

    `AgentIdentityManager`'s own revocation lists are per-process and empty on a
    fresh instance, which is exactly what DLG-01 constructs when a session
    supplies no manager. The project's durable store
    (`nhid_event_store.record_revocation`) was consulted only by the HTTP verify
    route, so a delegation revoked through the API still passed the policy gate.
    The engine performs no I/O, so the check arrives as an injected callable.
    """
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    revoked = {p.delegation.delegation_id}
    decision, result = evaluate_dlg01(
        session(p, manager),
        event(),
        ctx(resolver, revocation_checker=lambda did: did in revoked),
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_REVOKED"
    assert result.verified is False


def test_a_revocation_checker_that_revokes_nothing_permits(
    manager, provider_keys, agent_keys, resolver
):
    """The hook must not deny by merely being present."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, result = evaluate_dlg01(
        session(p, manager), event(), ctx(resolver, revocation_checker=lambda did: False)
    )
    assert decision.action == PolicyAction.CONTINUE_AI
    assert result.verified is True


def test_a_revoked_hop_anywhere_in_a_chain_denies(
    manager, provider_keys, agent_keys, resolver
):
    """Revoking the root must invalidate everything descended from it."""
    chain = build_chain(
        manager, provider_keys, agent_keys, ["eligibility"], ["eligibility"],
    )
    root_id = chain[0].delegation.delegation_id
    decision, _ = evaluate_dlg01(
        session(chain, manager),
        event(),
        ctx(resolver, revocation_checker=lambda did: did == root_id),
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_REVOKED"


def test_malformed_passport_denies_rather_than_raising(resolver):
    decision, result = evaluate_dlg01(
        session({"not": "a passport"}), event(), ctx(resolver)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_MALFORMED_PASSPORT"
    assert result.verified is False


def test_passport_accepted_as_plain_dict(manager, provider_keys, agent_keys, resolver):
    """Adapters carry JSON, not Python objects."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    as_dict = {
        "delegation": p.delegation.__dict__.copy(),
        "signature_b64": p.signature_b64,
        "agent_signature_b64": p.agent_signature_b64,
    }
    decision, result = evaluate_dlg01(session(as_dict, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.CONTINUE_AI
    assert result.verified is True


# ── 3. Delegation chains ───────────────────────────────────────────────────

def build_chain(
    manager, provider_keys, agent_keys, parent_scope, child_scope,
    child_call_sid="",
):
    """Two hops. The child is call-unbound by default, which is the realistic
    shape: a provider issues the root for a call and the vendor sub-delegates
    without re-stating the call. `child_call_sid` exists so a test can bind the
    child too and assert the binding is enforced per hop.
    """
    parent = make_passport(manager, provider_keys, agent_keys, parent_scope)
    agent_priv, _ = agent_keys
    sub_priv, sub_pub = manager.generate_agent_keys()
    child_delegation = manager.create_delegation(
        agent_priv, "sub-agent-001", sub_pub,
        scope=child_scope, ttl_seconds=3600, provider_npi=PROVIDER_NPI,
        call_sid=child_call_sid,
    )
    child_sig = manager.sign_delegation(agent_priv, child_delegation)
    child = manager.create_agent_passport(child_delegation, child_sig, sub_priv)
    return [parent, child]


def test_narrowed_child_scope_is_accepted(
    manager, provider_keys, agent_keys, resolver
):
    chain = build_chain(
        manager, provider_keys, agent_keys,
        ["eligibility", "claim_status"], ["eligibility"],
    )
    decision, result = evaluate_dlg01(session(chain, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.CONTINUE_AI
    assert result.scope == frozenset({"eligibility"})


def test_child_scope_wider_than_parent_denies(
    manager, provider_keys, agent_keys, resolver
):
    """Monotonic narrowing: a sub-delegation cannot grant what it was not given."""
    chain = build_chain(
        manager, provider_keys, agent_keys,
        ["eligibility"], ["eligibility", "claim_status"],
    )
    decision, result = evaluate_dlg01(session(chain, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert "claim_status" in result.reason


def test_a_chain_bound_to_another_call_is_denied(
    manager, provider_keys, agent_keys, resolver
):
    """Call binding must survive sub-delegation.

    `test_wrong_call_sid_denies` pins this for a single passport, and that was
    the whole of the coverage: every other chain test here presents the chain on
    the call it was issued for. `validate_chain` passed no call_sid to any hop,
    so a chain minted for one call verified on any other — the single-passport
    gate was simply absent one level down.
    """
    chain = build_chain(
        manager, provider_keys, agent_keys, ["eligibility"], ["eligibility"],
    )
    decision, _ = evaluate_dlg01(
        session(chain, manager), event(call_sid="CA-different-call"), ctx(resolver)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


def test_a_call_bound_child_is_checked_against_the_live_call(
    manager, provider_keys, agent_keys, resolver
):
    """Binding is enforced per hop, not only at the root."""
    chain = build_chain(
        manager, provider_keys, agent_keys, ["eligibility"], ["eligibility"],
        child_call_sid="CA-some-other-call",
    )
    decision, _ = evaluate_dlg01(session(chain, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


def test_an_unbound_child_rides_the_roots_binding(
    manager, provider_keys, agent_keys, resolver
):
    """The realistic shape must keep working: a child carrying no call_sid
    asserts no call of its own, so the root's binding is what governs."""
    chain = build_chain(
        manager, provider_keys, agent_keys, ["eligibility"], ["eligibility"],
    )
    decision, result = evaluate_dlg01(
        session(chain, manager), event(), ctx(resolver)
    )
    assert decision.action == PolicyAction.CONTINUE_AI
    assert result.verified is True


def test_a_chain_narrowed_to_empty_scope_authorizes_nothing(
    manager, provider_keys, agent_keys, resolver
):
    """Giving away all scope must not buy more authority than holding some.

    The empty set is a subset of every set, so `issubset` admits a hop that
    narrows to nothing — and a `constrains_scope` that required a non-empty
    scope then read that as "no scope to enforce". A sub-delegation that
    surrendered its whole grant therefore outranked its own parent: the root's
    `billing` grant denies a member-ID request, and the chain permitted it.
    """
    chain = build_chain(manager, provider_keys, agent_keys, ["billing"], [])
    ev = event(speech="can you confirm the member id number")
    decision = evaluate_all(session(chain, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"


# ── 4. Delegated scope gates PDX-01 — the product behavior ─────────────────

def test_in_scope_phi_request_is_permitted(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    ev = event(speech="can you confirm the member id and date of birth")
    decision = evaluate_all(session(p, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.CONTINUE_AI


def test_out_of_scope_phi_request_is_denied(
    manager, provider_keys, agent_keys, resolver
):
    """The headline case: authorized for eligibility, asked for claims history."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    ev = event(speech="what is the claim number on that")
    decision = evaluate_all(session(p, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"
    violation = next(v for v in decision.violations if v.rule_id == "PDX-01")
    assert violation.severity == ViolationSeverity.CRITICAL
    # The decision must explain itself well enough to audit without replay.
    assert "eligibility" in violation.description
    assert "claim_number" in violation.description
    assert PROVIDER_NPI in violation.description


def test_out_of_scope_request_permitted_when_scope_enforcement_disabled(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    ev = event(speech="what is the claim number on that")
    decision = evaluate_all(
        session(p, manager), ev, ctx(resolver, enforce_scope=False)
    )
    assert decision.action == PolicyAction.CONTINUE_AI


def test_broader_scope_permits_the_same_request(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["claim_status"])
    ev = event(speech="what is the claim number on that")
    decision = evaluate_all(session(p, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.CONTINUE_AI


def test_phi_accessed_fields_are_scope_checked_not_only_speech(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    ev = event(speech="just checking on that", phi_accessed=["prior_auth_number"])
    decision = evaluate_all(session(p, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"


def test_empty_scope_authorizes_nothing(manager, provider_keys, agent_keys, resolver):
    """A delegation granting nothing authorizes nothing.

    This test previously asserted the opposite — `constrains_scope is False` —
    while its own docstring said an empty grant "neither can be read as
    authorizing everything". The code did read it that way: PDX-01's scope gate
    was skipped, so an empty grant permitted every protected-data field. The
    docstring was right and the assertion was wrong.
    """
    p = make_passport(manager, provider_keys, agent_keys, [])
    _, result = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert result.verified is True
    assert result.constrains_scope is True

    decision = evaluate_all(
        session(p, manager),
        event(speech="can you confirm the member id number"),
        ctx(resolver),
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"


def test_unknown_scope_string_authorizes_nothing(
    manager, provider_keys, agent_keys, resolver
):
    """An unrecognized grant must never widen authority."""
    p = make_passport(manager, provider_keys, agent_keys, ["some_future_workflow"])
    ev = event(speech="can you confirm the member id")
    decision = evaluate_all(session(p, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"


def test_expired_scope_cannot_authorize(manager, provider_keys, agent_keys, resolver):
    """An expired delegation contributes no scope, so DLG-01 denies outright."""
    p = make_passport(manager, provider_keys, agent_keys, ["claim_status"], ttl=-1)
    ev = event(speech="what is the claim number on that")
    decision = evaluate_all(session(p, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


def test_multi_hop_narrowed_scope_gates_pdx01(
    manager, provider_keys, agent_keys, resolver
):
    """Enforcement follows the narrowest link in the chain, not the root grant."""
    chain = build_chain(
        manager, provider_keys, agent_keys,
        ["eligibility", "claim_status"], ["eligibility"],
    )
    ev = event(speech="what is the claim number on that")
    decision = evaluate_all(session(chain, manager), ev, ctx(resolver))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"


def test_disclosure_failure_outranks_scope_failure(
    manager, provider_keys, agent_keys, resolver
):
    """An undisclosed agent asking out of scope is reported as the disclosure
    failure — the more fundamental breach — not the scope one."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    ev = event(speech="what is the claim number", disclosed=False)
    decision = evaluate_pdx01(session(p, manager), ev, None)
    assert decision.reason_code == "PDX01_PHI_GATE_TRIGGERED"


# ── 5. PDX-01 behavior is unchanged when delegation is absent ──────────────

@pytest.mark.parametrize(
    "speech,phi,disclosed,expected",
    [
        ("what is the claim number", None, True, "PDX01_GATE_CLEARED"),
        ("what is the claim number", None, False, "PDX01_PHI_GATE_TRIGGERED"),
        ("good morning", None, True, "PDX01_NO_PHI_REQUESTED"),
        ("good morning", ["claim_number"], False, "PDX01_PHI_GATE_TRIGGERED"),
    ],
)
def test_pdx01_unchanged_without_delegation(speech, phi, disclosed, expected):
    ev = event(speech=speech, phi_accessed=phi, disclosed=disclosed)
    assert evaluate_pdx01(session(), ev).reason_code == expected


def test_determinism_across_repeated_evaluation(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    ev = event(speech="what is the claim number on that")
    results = {
        evaluate_all(session(p, manager), ev, ctx(resolver)).reason_code
        for _ in range(5)
    }
    assert results == {"PDX01_SCOPE_NOT_AUTHORIZED"}


# ── 6. NPI check digit (opt-in) ────────────────────────────────────────────

def test_require_npi_check_digit_denies_a_bad_check_digit(
    manager, provider_keys, agent_keys, resolver
):
    """PROVIDER_NPI here is 1234567890 — UDAP's published example, and not
    Luhn-valid. With the check on, it is rejected before any key is resolved."""
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, result = evaluate_dlg01(
        session(p, manager), event(), ctx(resolver, require_npi_check_digit=True)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_INVALID_NPI"
    assert result.verified is False


def test_require_npi_check_digit_permits_a_valid_one(manager, agent_keys):
    """1234567893 is 1234567890 carrying its correct check digit."""
    valid_npi = "1234567893"
    provider_priv, provider_pub = manager.generate_agent_keys()
    anchors = StaticTrustAnchorResolver(
        {valid_npi: manager.public_key_to_b64(provider_pub)}
    )
    p = make_passport(
        manager, (provider_priv, provider_pub), agent_keys, ["eligibility"],
        npi=valid_npi,
    )
    decision, result = evaluate_dlg01(
        session(p, manager), event(), ctx(anchors, require_npi_check_digit=True)
    )
    assert decision.action == PolicyAction.CONTINUE_AI
    assert result.verified is True


def test_the_check_digit_requirement_is_off_by_default(
    manager, provider_keys, agent_keys, resolver
):
    decision, _ = evaluate_dlg01(
        session(make_passport(manager, provider_keys, agent_keys, ["eligibility"]),
                manager),
        event(),
        ctx(resolver),
    )
    assert decision.action == PolicyAction.CONTINUE_AI


# ── 7. Proof of possession through the control (opt-in) ────────────────────

def test_require_possession_proof_denies_when_no_proof_is_answered(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, _ = evaluate_dlg01(
        session(p, manager, verifier_nonce="challenge-abc"),
        event(),
        ctx(resolver, require_possession_proof=True),
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_VERIFICATION_FAILED"


def test_require_possession_proof_accepts_the_agents_answer(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    agent_priv, _ = agent_keys
    nonce = "challenge-abc"
    proof = manager.create_presentation_proof(agent_priv, p.delegation, nonce)
    decision, result = evaluate_dlg01(
        session(p, manager, verifier_nonce=nonce, presentation_proof=proof),
        event(),
        ctx(resolver, require_possession_proof=True),
    )
    assert decision.action == PolicyAction.CONTINUE_AI
    assert result.verified is True


def test_a_proof_as_a_plain_dict_is_accepted(
    manager, provider_keys, agent_keys, resolver
):
    """Adapters carry JSON, not Python objects — same reason
    `test_passport_accepted_as_plain_dict` exists."""
    from dataclasses import asdict

    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    agent_priv, _ = agent_keys
    nonce = "challenge-abc"
    proof = manager.create_presentation_proof(agent_priv, p.delegation, nonce)
    decision, _ = evaluate_dlg01(
        session(p, manager, verifier_nonce=nonce,
                presentation_proof=asdict(proof)),
        event(),
        ctx(resolver, require_possession_proof=True),
    )
    assert decision.action == PolicyAction.CONTINUE_AI


def test_a_malformed_proof_denies_rather_than_raising(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, _ = evaluate_dlg01(
        session(p, manager, verifier_nonce="challenge-abc",
                presentation_proof={"garbage": True}),
        event(),
        ctx(resolver, require_possession_proof=True),
    )
    assert decision.action == PolicyAction.DENY_DATA


def test_requiring_a_proof_without_issuing_a_challenge_denies(
    manager, provider_keys, agent_keys, resolver
):
    """Fail closed on misconfiguration.

    A deployment that asks for proof of possession but never issues a nonce
    would otherwise get no check at all — which is precisely how a security
    requirement becomes decorative, and the shape of three of the defects this
    change set exists to fix.
    """
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, result = evaluate_dlg01(
        session(p, manager), event(), ctx(resolver, require_possession_proof=True)
    )
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "DLG01_NO_CHALLENGE_ISSUED"
    assert result.verified is False


def test_possession_proof_is_off_by_default(
    manager, provider_keys, agent_keys, resolver
):
    p = make_passport(manager, provider_keys, agent_keys, ["eligibility"])
    decision, _ = evaluate_dlg01(session(p, manager), event(), ctx(resolver))
    assert decision.action == PolicyAction.CONTINUE_AI
