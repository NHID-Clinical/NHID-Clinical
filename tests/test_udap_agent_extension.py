"""
The `nhid-agent` extension object — and the invariant that makes it safe
=======================================================================
The object this module builds travels in a token request, next to UDAP's
`hl7-b2b`. Anything travelling in a token request will eventually be read by
something that trusts token requests, so the load-bearing property is not
that it round-trips. It is this:

    No value in the object is believed on its own. The passport is verified
    first; then every field must agree with what the signature covers.

Most of the tests below are therefore not round-trip tests. They tamper with
one field at a time while leaving the passport's signature perfectly valid,
and require the verifier to notice. A field that can disagree with its
passport and still pass would make the object worse than nothing — it would
launder an unsigned claim through something that looks cryptographic.

The second group covers the purpose-of-use cross-check, which exists for the
inconsistency UDAP cannot currently detect: a token request asserting a
purpose the provider never delegated authority for.
"""
import time

import pytest

from src.agent_identity import (
    AgentIdentityManager,
    AgentPassport,
    ERR_CHAIN_NARROWING,
    ERR_CHAIN_TOO_LONG,
    ERR_EXPIRED,
    ERR_INVALID_SIG,
    ERR_NONCE_MISMATCH,
    ERR_REVOKED,
    MAX_CHAIN_DEPTH,
)
from src.udap_agent_extension import (
    ERR_EXTENSION_MALFORMED,
    ERR_EXTENSION_MISMATCH,
    ERR_PURPOSE_UNSUPPORTED,
    EXTENSION_KEY,
    EXTENSION_VERSION,
    NPI_NAMING_SYSTEM,
    PURPOSE_OF_USE_SYSTEM,
    SCOPE_PURPOSE_OF_USE,
    build_extension,
    check_purpose_of_use,
    key_fingerprint,
    npi_to_uri,
    purpose_of_use_to_uri,
    purposes_for_scope,
    scopes_for_purpose,
    verify_extension,
)

# Synthetic throughout. `1234567890` is the value UDAP uses in its own
# worked format example and the value the rest of this repository's fixtures
# use; the call SIDs are not real call identifiers. The engine only
# format-validates an NPI, so nothing here needs — or may have — a live one.
NPI = "1234567890"
CALL_SID = "CA-SYNTHETIC-0001"


@pytest.fixture
def issued():
    """A provider key, an agent key, and one verifiable passport."""
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(
        prov_priv, "agent-frontdesk-01", agent_pub,
        scope=["eligibility", "claim_status"],
        call_sid=CALL_SID, provider_npi=NPI,
    )
    passport = m.create_agent_passport(
        delegation, m.sign_delegation(prov_priv, delegation), agent_priv
    )
    return m, prov_priv, prov_pub, passport


def _chain(m, provider_priv, hops):
    """Issue a delegation chain. hops = [(agent_id, scope, npi), ...]."""
    passports, signer = [], provider_priv
    for agent_id, scope, npi in hops:
        agent_priv, agent_pub = m.generate_agent_keys()
        d = m.create_delegation(signer, agent_id, agent_pub, scope=scope,
                                provider_npi=npi)
        passports.append(
            m.create_agent_passport(d, m.sign_delegation(signer, d), agent_priv)
        )
        signer = agent_priv
    return passports


# ── The object says what the delegation says ──────────────────────────────────

def test_a_built_object_verifies_against_its_own_passport(issued):
    m, _, prov_pub, passport = issued
    ext = build_extension(passport)
    result = verify_extension(ext, passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert result.valid, result.reason
    assert result.provider_npi == NPI


def test_every_field_is_derived_from_the_delegation(issued):
    """
    The invariant the whole design rests on: `build_extension` takes the
    passport and nothing else. If a caller-supplied argument is ever added,
    that argument cannot be checked against a signature, and this test is
    the place that should start failing.
    """
    import inspect
    params = list(inspect.signature(build_extension).parameters)
    assert params == ["passport"], (
        "build_extension grew an argument that no signature covers; see the "
        "purpose-of-use note in the module docstring before allowing one"
    )


def test_the_object_carries_what_udap_has_no_slot_for(issued):
    _, _, _, passport = issued
    ext = build_extension(passport)
    d = passport.delegation
    assert ext["version"] == EXTENSION_VERSION
    assert ext["agent_id"] == d.agent_id
    assert ext["delegation_id"] == d.delegation_id
    assert ext["scope"] == list(d.scope)
    assert ext["expires_at"] == d.expires_at
    assert ext["call_sid"] == CALL_SID
    assert ext["agent_key_fingerprint"] == key_fingerprint(d.agent_public_key_b64)


def test_the_npi_uses_udaps_own_identifier_format(issued):
    """
    UDAP §5.2.1.3's worked example is
    `urn:oid:2.16.840.1.113883.4.6#1234567890`. A payer matching on this
    string will not tolerate a near miss, so it is pinned byte for byte.
    """
    _, _, _, passport = issued
    assert build_extension(passport)["provider_npi"] == (
        f"urn:oid:2.16.840.1.113883.4.6#{NPI}"
    )
    assert NPI_NAMING_SYSTEM == "urn:oid:2.16.840.1.113883.4.6"
    assert npi_to_uri("1234567890") == "urn:oid:2.16.840.1.113883.4.6#1234567890"


def test_an_absent_npi_is_absent_not_an_empty_uri():
    """`urn:oid:...#` with nothing after the hash would read as an assertion."""
    m = AgentIdentityManager()
    prov_priv, _ = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(prov_priv, "agent-x", agent_pub,
                            scope=["eligibility"])
    passport = m.create_agent_passport(
        d, m.sign_delegation(prov_priv, d), agent_priv
    )
    assert "provider_npi" not in build_extension(passport)


def test_a_malformed_npi_cannot_be_rendered():
    with pytest.raises(ValueError):
        npi_to_uri("12345")
    with pytest.raises(ValueError):
        npi_to_uri("")


# ── Tamper matrix: the passport stays valid, the object lies ──────────────────

@pytest.mark.parametrize("field,value", [
    ("provider_npi", f"{NPI_NAMING_SYSTEM}#9999999999"),
    ("scope", ["eligibility", "claim_status", "prior_auth"]),
    ("call_sid", "CA-SYNTHETIC-9999"),
    ("delegation_id", "00000000-0000-0000-0000-000000000000"),
    ("agent_id", "agent-somebody-else"),
    ("agent_key_fingerprint", "sha256:" + "0" * 64),
])
def test_a_field_that_disagrees_with_the_signature_fails(issued, field, value):
    m, _, prov_pub, passport = issued
    tampered = dict(build_extension(passport))
    tampered[field] = value
    result = verify_extension(tampered, passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert not result.valid, f"{field} was altered and the verifier accepted it"
    assert ERR_EXTENSION_MISMATCH in result.reason
    assert field in result.reason


def test_a_later_expiry_cannot_be_claimed(issued):
    """
    Separated from the parametrized cases because it is the tamper with a
    motive: extending `expires_at` is how a reader of this object would be
    told a dead delegation is live.
    """
    m, _, prov_pub, passport = issued
    ext = build_extension(passport)
    tampered = dict(ext, expires_at=ext["expires_at"] + 86_400)
    result = verify_extension(tampered, passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert not result.valid
    assert ERR_EXTENSION_MISMATCH in result.reason
    assert "expires_at" in result.reason


def test_a_field_cannot_be_dropped_to_avoid_scrutiny(issued):
    m, _, prov_pub, passport = issued
    thinned = dict(build_extension(passport))
    del thinned["provider_npi"]
    result = verify_extension(thinned, passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert not result.valid
    assert "provider_npi is missing" in result.reason


def test_an_unknown_field_does_not_ride_along(issued):
    m, _, prov_pub, passport = issued
    padded = dict(build_extension(passport), subject_role="attending")
    result = verify_extension(padded, passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert not result.valid
    assert "subject_role" in result.reason


def test_purpose_of_use_cannot_be_smuggled_into_this_object(issued):
    """
    `hl7-b2b` carries purpose of use; `nhid-agent` deliberately does not,
    because a copy here would be the one field no signature covers. An
    object presenting one is rejected rather than quietly tolerated.
    """
    m, _, prov_pub, passport = issued
    padded = dict(build_extension(passport),
                  purpose_of_use=[purpose_of_use_to_uri("COVAUTH")])
    result = verify_extension(padded, passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert not result.valid
    assert "purpose_of_use" in result.reason


def test_a_wrong_version_is_named_as_malformed_not_as_a_mismatch(issued):
    m, _, prov_pub, passport = issued
    result = verify_extension(dict(build_extension(passport), version=1),
                              passport, prov_pub, manager=m, call_sid=CALL_SID)
    assert not result.valid
    assert ERR_EXTENSION_MALFORMED in result.reason


def test_something_that_is_not_an_object_is_refused(issued):
    m, _, prov_pub, passport = issued
    result = verify_extension(["nhid-agent"], passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert not result.valid
    assert ERR_EXTENSION_MALFORMED in result.reason


# ── The passport is checked first, and its reason survives ───────────────────

def test_a_revoked_delegation_fails_with_the_passports_own_reason(issued):
    m, _, prov_pub, passport = issued
    ext = build_extension(passport)
    m.revoke_delegation(passport.delegation.delegation_id)
    result = verify_extension(ext, passport, prov_pub, manager=m,
                              call_sid=CALL_SID)
    assert not result.valid
    assert result.reason == ERR_REVOKED


def test_a_revoked_agent_fails(issued):
    m, _, prov_pub, passport = issued
    ext = build_extension(passport)
    m.revoke_agent(passport.delegation.agent_id)
    assert verify_extension(ext, passport, prov_pub, manager=m,
                            call_sid=CALL_SID).reason == ERR_REVOKED


def test_an_expired_delegation_fails(issued):
    m, prov_priv, prov_pub, _ = issued
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(prov_priv, "agent-stale", agent_pub,
                            scope=["eligibility"], ttl_seconds=-1,
                            provider_npi=NPI)
    passport = m.create_agent_passport(
        d, m.sign_delegation(prov_priv, d), agent_priv
    )
    result = verify_extension(build_extension(passport), passport, prov_pub,
                              manager=m)
    assert not result.valid
    assert ERR_EXPIRED in result.reason


def test_a_bad_passport_is_reported_before_the_object_is_even_compared(issued):
    """
    Order of checks, pinned. Here the passport is expired *and* the object
    has been tampered with, so both checks would fire. The reason returned
    must be the expiry.

    Why it matters: `build_extension` is called on the passport to produce
    the comparison baseline. Running that before verification would have the
    module deriving a trusted-looking object out of an untrusted credential,
    and would report "a field does not match" for a credential whose real
    problem is that it is dead.
    """
    m, prov_priv, prov_pub, _ = issued
    agent_priv, agent_pub = m.generate_agent_keys()
    d = m.create_delegation(prov_priv, "agent-stale", agent_pub,
                            scope=["eligibility"], ttl_seconds=-1,
                            provider_npi=NPI)
    passport = m.create_agent_passport(
        d, m.sign_delegation(prov_priv, d), agent_priv
    )
    tampered = dict(build_extension(passport), agent_id="agent-someone-else")
    result = verify_extension(tampered, passport, prov_pub, manager=m)
    assert not result.valid
    assert ERR_EXPIRED in result.reason, (
        "the object's mismatch was reported ahead of the passport's expiry; "
        "the passport must be verified first"
    )
    assert ERR_EXTENSION_MISMATCH not in result.reason


def test_a_passport_replayed_onto_a_different_call_fails(issued):
    """A faithful object over a replayed passport is still a replay."""
    m, _, prov_pub, passport = issued
    result = verify_extension(build_extension(passport), passport, prov_pub,
                              manager=m, call_sid="CA-SYNTHETIC-0002")
    assert not result.valid
    assert result.reason == ERR_NONCE_MISMATCH


def test_the_wrong_provider_key_fails(issued):
    m, _, _, passport = issued
    _, other_pub = m.generate_agent_keys()
    result = verify_extension(build_extension(passport), passport, other_pub,
                              manager=m, call_sid=CALL_SID)
    assert not result.valid
    assert result.reason == ERR_INVALID_SIG


# ── Chains ────────────────────────────────────────────────────────────────────

def test_a_chain_describes_the_last_agent_under_the_root_provider(issued):
    m, prov_priv, prov_pub, _ = issued
    chain = _chain(m, prov_priv, [
        ("agent-platform", ["eligibility", "claim_status"], NPI),
        ("agent-subvendor", ["eligibility"], ""),
    ])
    ext = build_extension(chain)
    assert ext["agent_id"] == "agent-subvendor"
    assert ext["scope"] == ["eligibility"]
    assert ext["provider_npi"] == f"{NPI_NAMING_SYSTEM}#{NPI}"
    assert ext["delegation_chain_depth"] == 2
    result = verify_extension(ext, chain, prov_pub, manager=m)
    assert result.valid, result.reason


def test_a_chain_past_the_depth_limit_fails(issued):
    m, prov_priv, prov_pub, _ = issued
    hops = [(f"agent-{i}", ["eligibility"], NPI if i == 0 else "")
            for i in range(MAX_CHAIN_DEPTH + 1)]
    chain = _chain(m, prov_priv, hops)
    result = verify_extension(build_extension(chain[:MAX_CHAIN_DEPTH]), chain,
                              prov_pub, manager=m)
    assert not result.valid
    assert ERR_CHAIN_TOO_LONG in result.reason


def test_a_hop_that_widens_scope_fails(issued):
    m, prov_priv, prov_pub, _ = issued
    chain = _chain(m, prov_priv, [
        ("agent-platform", ["eligibility"], NPI),
        ("agent-greedy", ["eligibility", "prior_auth"], ""),
    ])
    result = verify_extension(build_extension(chain), chain, prov_pub,
                              manager=m)
    assert not result.valid
    assert ERR_CHAIN_NARROWING in result.reason


def test_an_empty_chain_describes_no_agent(issued):
    _, _, _, _ = issued
    with pytest.raises(ValueError):
        build_extension([])


def test_a_single_passport_carries_no_chain_depth(issued):
    _, _, _, passport = issued
    assert "delegation_chain_depth" not in build_extension(passport)


# ── Purpose of use: real codes only, and the cross-check ─────────────────────

def test_every_mapped_code_is_one_verified_in_the_hl7_value_set():
    """
    Pinned deliberately. These five codes were read out of HL7 Terminology
    v7.4.0 (ValueSet PurposeOfUse v3.1.0, CodeSystem v3-ActReason v4.0.0).
    A sixth appearing here without that check is how an invented code would
    reach a payer's token request.
    """
    verified = {"ELIGVER", "ELIGDTRM", "COVAUTH", "HPAYMT", "CLMATTCH"}
    assert set(SCOPE_PURPOSE_OF_USE.values()) <= verified


def test_the_purpose_code_system_is_the_one_udap_uses():
    assert PURPOSE_OF_USE_SYSTEM == "urn:oid:2.16.840.1.113883.5.8"
    assert purpose_of_use_to_uri("TREAT") == (
        "urn:oid:2.16.840.1.113883.5.8#TREAT"
    )


def test_an_unmapped_scope_yields_nothing_rather_than_a_guess():
    assert purposes_for_scope(["something_nobody_mapped"]) == []
    assert purposes_for_scope([]) == []


def test_a_mapped_scope_yields_its_verified_code():
    assert purposes_for_scope(["eligibility"]) == [
        purpose_of_use_to_uri("ELIGVER")
    ]
    assert purposes_for_scope(["prior_auth"]) == [
        purpose_of_use_to_uri("COVAUTH")
    ]


def test_several_scopes_can_share_one_purpose():
    assert scopes_for_purpose(purpose_of_use_to_uri("HPAYMT")) == [
        "billing", "claim_status", "claim_status_inquiry", "claims_inquiry"
    ]


def test_a_purpose_the_delegation_supports_is_consistent(issued):
    m, _, prov_pub, passport = issued
    verified = verify_extension(build_extension(passport), passport, prov_pub,
                                manager=m, call_sid=CALL_SID)
    b2b = {"purpose_of_use": purposes_for_scope(passport.delegation.scope)}
    assert check_purpose_of_use(b2b, verified.scope).valid


def test_a_purpose_the_provider_never_delegated_is_caught(issued):
    """
    The inconsistency UDAP cannot see today: the token request claims prior
    authorization, the delegation covers eligibility and claim status. This
    is the case the whole extension exists to make visible.
    """
    m, _, prov_pub, passport = issued
    verified = verify_extension(build_extension(passport), passport, prov_pub,
                                manager=m, call_sid=CALL_SID)
    b2b = {"purpose_of_use": [purpose_of_use_to_uri("COVAUTH")]}
    result = check_purpose_of_use(b2b, verified.scope)
    assert not result.valid
    assert ERR_PURPOSE_UNSUPPORTED in result.reason
    assert "prior_auth" in result.reason


def test_an_unmappable_purpose_is_reported_unassessed_not_approved(issued):
    """
    `TREAT` is a real purpose with no counterpart in our scope vocabulary.
    Saying so is honest; silently passing it would imply a judgement this
    module has no basis for.
    """
    m, _, prov_pub, passport = issued
    verified = verify_extension(build_extension(passport), passport, prov_pub,
                                manager=m, call_sid=CALL_SID)
    result = check_purpose_of_use(
        {"purpose_of_use": [purpose_of_use_to_uri("TREAT")]}, verified.scope
    )
    assert result.valid
    assert "not assessable" in result.reason
    assert "TREAT" in result.reason


def test_no_asserted_purpose_is_vacuously_consistent(issued):
    m, _, prov_pub, passport = issued
    verified = verify_extension(build_extension(passport), passport, prov_pub,
                                manager=m, call_sid=CALL_SID)
    assert check_purpose_of_use({}, verified.scope).valid


def test_a_purpose_array_of_the_wrong_shape_is_refused():
    result = check_purpose_of_use({"purpose_of_use": "TREAT"}, ["eligibility"])
    assert not result.valid
    assert ERR_EXTENSION_MALFORMED in result.reason


# ── What this is published as ────────────────────────────────────────────────

def test_the_extension_key_sits_beside_hl7_b2b_not_inside_it():
    """
    UDAP's `extensions` claim is a flat object keyed by extension name, and
    its own text permits additional objects "to use together with" `hl7-b2b`.
    Nesting ours inside theirs would change their object's shape, which is
    not what that permission grants.
    """
    assert EXTENSION_KEY == "nhid-agent"
    assert EXTENSION_VERSION == "1", (
        "hl7-b2b's own version is the string \"1\"; matching it keeps the two "
        "objects readable by the same code"
    )
