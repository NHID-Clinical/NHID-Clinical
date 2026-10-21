import pytest
import time
from src.agent_identity import (
    AgentIdentityManager,
    ERR_EXPIRED, ERR_REVOKED, ERR_INVALID_SIG,
    ERR_NONCE_MISMATCH, ERR_SCOPE_VIOLATION, ERR_INVALID_NPI,
    ERR_CHAIN_NARROWING, ERR_CHAIN_TOO_LONG, MAX_CHAIN_DEPTH,
    ERR_PROOF_MISSING, ERR_PROOF_MISMATCH, ERR_PROOF_STALE,
    MAX_PROOF_AGE_SECONDS, new_verifier_nonce,
    DELEGATION_FORMAT_VERSION, ERR_UNSUPPORTED_VERSION, Delegation,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_passport(m, agent_id="agent-x", scope=None, ttl=86400,
                   npi="", call_sid="", provider_priv=None, provider_pub=None):
    if scope is None:
        scope = ["eligibility"]
    if provider_priv is None:
        provider_priv, provider_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(provider_priv, agent_id, agent_pub, scope,
                            ttl_seconds=ttl, call_sid=call_sid, provider_npi=npi)
    sig = m.sign_delegation(provider_priv, d)
    passport = m.create_agent_passport(d, sig, agent_priv)
    return passport, provider_pub, agent_priv, agent_pub


# ── Existing tests (unchanged) ────────────────────────────────────────────────

def test_key_generation():
    m = AgentIdentityManager()
    priv, pub = m.generate_agent_keys()
    assert priv is not None

def test_delegation_creation():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-1", agent_pub, ["eligibility"])
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    result = m.verify_passport(passport, prov_pub)
    assert result.valid
    assert result.agent_id == "agent-1"

def test_expired():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-2", agent_pub, ["eligibility"], ttl_seconds=0)
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    result = m.verify_passport(passport, prov_pub)
    assert not result.valid
    assert "expired" in result.reason.lower()

def test_revoked():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-3", agent_pub, ["eligibility"])
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    m.revoke_agent("agent-3")
    result = m.verify_passport(passport, prov_pub)
    assert not result.valid
    assert "revoked" in result.reason.lower()

def test_nonce_binds_to_call_sid():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-4", agent_pub, ["eligibility"], call_sid="CA123")
    assert delegation.nonce != ""
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    assert m.verify_passport(passport, prov_pub, call_sid="CA123").valid
    assert not m.verify_passport(passport, prov_pub, call_sid="CA999").valid

def test_no_nonce_without_call_sid():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(prov_priv, "agent-5", agent_pub, ["eligibility"])
    assert delegation.nonce == ""
    sig = m.sign_delegation(prov_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    assert m.verify_passport(passport, prov_pub).valid


# ── NPI binding ───────────────────────────────────────────────────────────────

def test_provider_npi_bound_in_result():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, npi="1234567890")
    result = m.verify_passport(passport, prov_pub)
    assert result.valid
    assert result.provider_npi == "1234567890"

def test_invalid_npi_nine_digits_rejected():
    m = AgentIdentityManager()
    prov_priv, _ = m.generate_agent_keys()
    _, agent_pub = m.generate_agent_keys()
    with pytest.raises(ValueError, match=ERR_INVALID_NPI):
        m.create_delegation(prov_priv, "a", agent_pub, ["eligibility"], provider_npi="123456789")

def test_invalid_npi_letters_rejected():
    m = AgentIdentityManager()
    prov_priv, _ = m.generate_agent_keys()
    _, agent_pub = m.generate_agent_keys()
    with pytest.raises(ValueError, match=ERR_INVALID_NPI):
        m.create_delegation(prov_priv, "a", agent_pub, ["eligibility"], provider_npi="12345ABCDE")

def test_empty_npi_is_valid():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, npi="")
    assert m.verify_passport(passport, prov_pub).valid

def test_ten_digit_npi_accepted():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, npi="9876543210")
    assert m.verify_passport(passport, prov_pub).valid


# ── Canonical / deterministic signing ────────────────────────────────────────

def test_canonical_json_is_deterministic():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    _, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(prov_priv, "agent-det", agent_pub, ["eligibility"])
    assert d.to_json() == d.to_json()

def test_tampered_provider_signature_rejected():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m)
    # flip one byte in provider sig
    raw = list(passport.signature_b64)
    raw[10] = 'A' if raw[10] != 'A' else 'B'
    passport.signature_b64 = "".join(raw)
    result = m.verify_passport(passport, prov_pub)
    assert not result.valid
    assert result.reason == ERR_INVALID_SIG


# ── Scope enforcement ─────────────────────────────────────────────────────────

def test_required_scope_subset_passes():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, scope=["eligibility", "claim_status"])
    result = m.verify_passport(passport, prov_pub, required_scope=["eligibility"])
    assert result.valid

def test_required_scope_exact_match_passes():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, scope=["eligibility"])
    result = m.verify_passport(passport, prov_pub, required_scope=["eligibility"])
    assert result.valid

def test_required_scope_exceeds_delegation_fails():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, scope=["eligibility"])
    result = m.verify_passport(passport, prov_pub, required_scope=["prior_auth"])
    assert not result.valid
    assert ERR_SCOPE_VIOLATION in result.reason

def test_empty_scope_delegation_valid():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, scope=[])
    assert m.verify_passport(passport, prov_pub).valid

def test_empty_scope_fails_any_required_scope():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, scope=[])
    result = m.verify_passport(passport, prov_pub, required_scope=["eligibility"])
    assert not result.valid


# ── Delegation-level revocation ───────────────────────────────────────────────

def test_revoke_delegation_by_id():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, agent_id="shared-agent")
    m.revoke_delegation(passport.delegation.delegation_id)
    result = m.verify_passport(passport, prov_pub)
    assert not result.valid
    assert result.reason == ERR_REVOKED

def test_revoke_one_delegation_leaves_others_valid():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    passport1, _, _, _ = _make_passport(m, agent_id="shared-agent",
                                        provider_priv=prov_priv, provider_pub=prov_pub)
    passport2, _, _, _ = _make_passport(m, agent_id="shared-agent",
                                        provider_priv=prov_priv, provider_pub=prov_pub)
    m.revoke_delegation(passport1.delegation.delegation_id)
    assert not m.verify_passport(passport1, prov_pub).valid
    assert m.verify_passport(passport2, prov_pub).valid


# ── Chain validation ──────────────────────────────────────────────────────────

def test_chain_single_hop_valid():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, npi="1234567890")
    result = m.validate_chain([passport], prov_pub)
    assert result.valid
    assert result.provider_npi == "1234567890"

def test_chain_two_hops_valid():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    mid_priv, mid_pub = m.generate_agent_keys()
    leaf_priv, leaf_pub = m.generate_agent_keys()

    d1 = m.create_delegation(prov_priv, "mid-agent", mid_pub,
                             scope=["eligibility", "claim_status"], provider_npi="1234567890")
    sig1 = m.sign_delegation(prov_priv, d1)
    p1 = m.create_agent_passport(d1, sig1, mid_priv)

    d2 = m.create_delegation(mid_priv, "leaf-agent", leaf_pub,
                             scope=["eligibility"])
    sig2 = m.sign_delegation(mid_priv, d2)
    p2 = m.create_agent_passport(d2, sig2, leaf_priv)

    result = m.validate_chain([p1, p2], prov_pub)
    assert result.valid
    assert result.provider_npi == "1234567890"
    assert result.agent_id == "leaf-agent"

def test_chain_scope_escalation_rejected():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    mid_priv, mid_pub = m.generate_agent_keys()
    leaf_priv, leaf_pub = m.generate_agent_keys()

    d1 = m.create_delegation(prov_priv, "mid-agent", mid_pub,
                             scope=["eligibility"], provider_npi="1234567890")
    sig1 = m.sign_delegation(prov_priv, d1)
    p1 = m.create_agent_passport(d1, sig1, mid_priv)

    # leaf tries to claim prior_auth which mid-agent was never granted
    d2 = m.create_delegation(mid_priv, "leaf-agent", leaf_pub, scope=["prior_auth"])
    sig2 = m.sign_delegation(mid_priv, d2)
    p2 = m.create_agent_passport(d2, sig2, leaf_priv)

    result = m.validate_chain([p1, p2], prov_pub)
    assert not result.valid
    assert ERR_CHAIN_NARROWING in result.reason

def test_chain_too_long_rejected():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()

    passports = []
    current_priv = prov_priv
    for i in range(MAX_CHAIN_DEPTH + 1):
        next_priv, next_pub = m.generate_agent_keys()
        d = m.create_delegation(
            current_priv, f"agent-{i}", next_pub, scope=["eligibility"],
            provider_npi="1234567890" if i == 0 else "",
        )
        sig = m.sign_delegation(current_priv, d)
        passports.append(m.create_agent_passport(d, sig, next_priv))
        current_priv = next_priv

    result = m.validate_chain(passports, prov_pub)
    assert not result.valid
    assert ERR_CHAIN_TOO_LONG in result.reason

def test_chain_expired_link_rejected():
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    mid_priv, mid_pub = m.generate_agent_keys()
    leaf_priv, leaf_pub = m.generate_agent_keys()

    d1 = m.create_delegation(prov_priv, "mid-agent", mid_pub,
                             scope=["eligibility"], ttl_seconds=0,
                             provider_npi="1234567890")
    sig1 = m.sign_delegation(prov_priv, d1)
    p1 = m.create_agent_passport(d1, sig1, mid_priv)

    d2 = m.create_delegation(mid_priv, "leaf-agent", leaf_pub, scope=["eligibility"])
    sig2 = m.sign_delegation(mid_priv, d2)
    p2 = m.create_agent_passport(d2, sig2, leaf_priv)

    result = m.validate_chain([p1, p2], prov_pub)
    assert not result.valid
    assert result.reason == ERR_EXPIRED


# ── Performance ───────────────────────────────────────────────────────────────

def test_1000_verifications_under_500ms():
    import sys
    # Linux (CI): Ed25519 via OpenSSL is fast — 500ms is realistic.
    # Windows: same OpenSSL but slower syscall overhead — use 2000ms to avoid flakes.
    limit_ms = 2000 if sys.platform == "win32" else 500
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m)
    start = time.perf_counter()
    for _ in range(1000):
        m.verify_passport(passport, prov_pub)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < limit_ms, f"1000 verifications took {elapsed_ms:.1f}ms (limit: {limit_ms}ms)"


# ── A delegation that names no provider ───────────────────────────────────────

def test_a_lone_passport_naming_no_provider_is_not_valid():
    """`require_npi` exists because a passport presented alone is claiming
    provider authority on its own.

    `_validate_npi` only runs when the NPI is truthy, so an empty one is
    accepted at issuance — correct for a sub-delegation, which inherits its
    root's provider. But a lone passport that names nobody verified as valid
    and reported `provider_npi: ""`, which the hosted verify route returned to
    callers as a pass.
    """
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _make_passport(m, scope=["eligibility"])
    assert passport.delegation.provider_npi == ""
    assert m.verify_passport(passport, prov_pub).valid
    strict = m.verify_passport(passport, prov_pub, require_npi=True)
    assert not strict.valid
    assert ERR_INVALID_NPI in strict.reason


def test_a_chain_hop_is_not_required_to_name_a_provider():
    """Only the root anchors to an NPI; hops inherit it. `validate_chain` must
    keep accepting a child that names no provider."""
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    mid_priv, mid_pub = m.generate_agent_keys()
    leaf_priv, leaf_pub = m.generate_agent_keys()

    d1 = m.create_delegation(prov_priv, "mid-agent", mid_pub,
                             scope=["eligibility"], provider_npi="1234567890")
    p1 = m.create_agent_passport(d1, m.sign_delegation(prov_priv, d1), mid_priv)
    d2 = m.create_delegation(mid_priv, "leaf-agent", leaf_pub, scope=["eligibility"])
    p2 = m.create_agent_passport(d2, m.sign_delegation(mid_priv, d2), leaf_priv)

    assert d2.provider_npi == ""
    result = m.validate_chain([p1, p2], prov_pub)
    assert result.valid
    assert result.provider_npi == "1234567890"


def test_a_root_that_names_no_provider_fails_chain_validation():
    """The root is the hop that claims provider authority, so it must name one."""
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    mid_priv, mid_pub = m.generate_agent_keys()
    leaf_priv, leaf_pub = m.generate_agent_keys()

    d1 = m.create_delegation(prov_priv, "mid-agent", mid_pub, scope=["eligibility"])
    p1 = m.create_agent_passport(d1, m.sign_delegation(prov_priv, d1), mid_priv)
    d2 = m.create_delegation(mid_priv, "leaf-agent", leaf_pub, scope=["eligibility"])
    p2 = m.create_agent_passport(d2, m.sign_delegation(mid_priv, d2), leaf_priv)

    result = m.validate_chain([p1, p2], prov_pub)
    assert not result.valid
    assert ERR_INVALID_NPI in result.reason


# ── Proof of possession at presentation ───────────────────────────────────────

def _bound_passport(m, npi="1234567890", call_sid="CA-pop-0001"):
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(prov_priv, "agent-pop", agent_pub, ["eligibility"],
                            call_sid=call_sid, provider_npi=npi)
    passport = m.create_agent_passport(d, m.sign_delegation(prov_priv, d), agent_priv)
    return passport, prov_pub, agent_priv, d


def test_a_captured_passport_cannot_answer_a_challenge():
    """The defect this closes.

    `agent_signature_b64` covers the delegation JSON — the same bytes the
    provider signed — so it is a static artifact. Anyone who captures the
    passport holds something that verifies. Under a challenge they must also
    hold the agent private key, which a captured passport does not contain.
    """
    m = AgentIdentityManager()
    passport, prov_pub, _, delegation = _bound_passport(m)
    nonce = new_verifier_nonce()

    thief_priv, _ = m.generate_agent_keys()
    forged = m.create_presentation_proof(thief_priv, delegation, nonce)

    result = m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001",
                               verifier_nonce=nonce, proof=forged)
    assert not result.valid
    assert ERR_PROOF_MISMATCH in result.reason

    # ...while the passport itself is untouched and still verifies unchallenged.
    assert m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001").valid


def test_a_correct_proof_verifies():
    m = AgentIdentityManager()
    passport, prov_pub, agent_priv, delegation = _bound_passport(m)
    nonce = new_verifier_nonce()
    proof = m.create_presentation_proof(agent_priv, delegation, nonce)
    assert m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001",
                             verifier_nonce=nonce, proof=proof).valid


def test_a_challenge_without_a_proof_is_refused():
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _bound_passport(m)
    result = m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001",
                               verifier_nonce=new_verifier_nonce())
    assert not result.valid
    assert ERR_PROOF_MISSING in result.reason


def test_a_proof_for_a_different_challenge_is_refused():
    """A proof captured from an earlier exchange answers the wrong nonce."""
    m = AgentIdentityManager()
    passport, prov_pub, agent_priv, delegation = _bound_passport(m)
    earlier = m.create_presentation_proof(agent_priv, delegation,
                                          new_verifier_nonce())
    result = m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001",
                               verifier_nonce=new_verifier_nonce(), proof=earlier)
    assert not result.valid
    assert ERR_PROOF_MISMATCH in result.reason


def test_a_proof_naming_another_delegation_is_refused():
    m = AgentIdentityManager()
    passport, prov_pub, agent_priv, delegation = _bound_passport(m)
    nonce = new_verifier_nonce()
    proof = m.create_presentation_proof(agent_priv, delegation, nonce)
    proof.delegation_id = "some-other-delegation"
    result = m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001",
                               verifier_nonce=nonce, proof=proof)
    assert not result.valid
    assert ERR_PROOF_MISMATCH in result.reason


@pytest.mark.parametrize("offset", [MAX_PROOF_AGE_SECONDS + 60,
                                    -(MAX_PROOF_AGE_SECONDS + 60)])
def test_a_stale_or_future_dated_proof_is_refused(offset):
    """Bounded in both directions: a clock skewed forward must not mint a proof
    that stays acceptable indefinitely."""
    m = AgentIdentityManager()
    passport, prov_pub, agent_priv, delegation = _bound_passport(m)
    nonce = new_verifier_nonce()
    proof = m.create_presentation_proof(agent_priv, delegation, nonce)
    proof.issued_at -= offset
    result = m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001",
                               verifier_nonce=nonce, proof=proof)
    assert not result.valid
    assert ERR_PROOF_STALE in result.reason


def test_a_tampered_proof_payload_is_refused():
    """The signature covers the nonce, so editing it invalidates the proof."""
    m = AgentIdentityManager()
    passport, prov_pub, agent_priv, delegation = _bound_passport(m)
    nonce = new_verifier_nonce()
    proof = m.create_presentation_proof(agent_priv, delegation, nonce)
    proof.verifier_nonce = nonce  # unchanged
    proof.issued_at += 1          # but the timestamp is signed too
    result = m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001",
                               verifier_nonce=nonce, proof=proof)
    assert not result.valid
    assert ERR_PROOF_MISMATCH in result.reason


def test_omitting_a_challenge_leaves_behaviour_unchanged():
    """Opt-in: every existing caller passes no nonce and must be unaffected."""
    m = AgentIdentityManager()
    passport, prov_pub, _, _ = _bound_passport(m)
    assert m.verify_passport(passport, prov_pub, call_sid="CA-pop-0001").valid


def test_a_proof_needs_a_nonce_to_exist():
    m = AgentIdentityManager()
    _, _, agent_priv, delegation = _bound_passport(m)
    with pytest.raises(ValueError):
        m.create_presentation_proof(agent_priv, delegation, "")


def test_a_chain_proves_possession_at_the_leaf():
    """The leaf agent is the one presenting, so the leaf key answers."""
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    mid_priv, mid_pub = m.generate_agent_keys()
    leaf_priv, leaf_pub = m.generate_agent_keys()

    d1 = m.create_delegation(prov_priv, "mid", mid_pub, scope=["eligibility"],
                             provider_npi="1234567890")
    p1 = m.create_agent_passport(d1, m.sign_delegation(prov_priv, d1), mid_priv)
    d2 = m.create_delegation(mid_priv, "leaf", leaf_pub, scope=["eligibility"])
    p2 = m.create_agent_passport(d2, m.sign_delegation(mid_priv, d2), leaf_priv)

    nonce = new_verifier_nonce()
    assert m.validate_chain([p1, p2], prov_pub, verifier_nonce=nonce,
                            proof=m.create_presentation_proof(leaf_priv, d2, nonce)).valid

    # The intermediate's key is not the one presenting.
    bad = m.create_presentation_proof(mid_priv, d2, nonce)
    assert not m.validate_chain([p1, p2], prov_pub, verifier_nonce=nonce,
                                proof=bad).valid


# ── Delegation format version ─────────────────────────────────────────────────

def test_a_delegation_carries_the_format_version():
    m = AgentIdentityManager()
    _, _, _, d = _bound_passport(m)
    assert d.nhid_auth_version == DELEGATION_FORMAT_VERSION
    assert '"nhid_auth_version":"2"' in d.to_json()


def test_an_unknown_format_version_is_refused_as_a_version_not_a_forgery():
    """A verifier meeting a shape it does not understand must say so, rather
    than fail a signature check and report what looks like tampering."""
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(prov_priv, "agent-v", agent_pub, ["eligibility"],
                            provider_npi="1234567890")
    d.nhid_auth_version = "99"
    passport = m.create_agent_passport(d, m.sign_delegation(prov_priv, d), agent_priv)

    result = m.verify_passport(passport, prov_pub)
    assert not result.valid
    assert ERR_UNSUPPORTED_VERSION in result.reason
    assert ERR_INVALID_SIG not in result.reason


def test_from_json_defaults_the_new_fields():
    """A payload written before kid and the version field existed still loads."""
    legacy = ('{"provider_npi":"1234567890","agent_id":"a","agent_public_key_b64":"x",'
              '"scope":["eligibility"],"expires_at":1,"created_at":1,'
              '"delegation_id":"d1"}')
    d = Delegation.from_json(legacy)
    assert d.kid == ""
    assert d.nhid_auth_version == DELEGATION_FORMAT_VERSION
    assert d.call_sid == "" and d.nonce == ""


def test_kid_is_inside_the_signed_payload():
    """An attacker who could edit kid would choose which key verifies them."""
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(prov_priv, "agent-k", agent_pub, ["eligibility"],
                            provider_npi="1234567890", kid="2026-q4")
    passport = m.create_agent_passport(d, m.sign_delegation(prov_priv, d), agent_priv)
    assert m.verify_passport(passport, prov_pub).valid

    passport.delegation.kid = "2026-q3"
    assert not m.verify_passport(passport, prov_pub).valid
