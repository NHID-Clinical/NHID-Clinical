"""
`nhid-agent` carried in a signed JWS — tests
============================================
The module's job is transport, and the tests are shaped around the one thing
that must never become true: that decoding a token is mistaken for verifying a
delegation. Every success case here ends by checking the decoded object still
has to go through `verify_extension`.
"""
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric import rsa

from src.agent_identity import AgentIdentityManager
from src.udap_agent_extension import (
    EXTENSION_KEY,
    build_extension,
    purposes_for_scope,
    verify_extension,
)
from src.udap_jws import (
    HL7_B2B_KEY,
    SUPPORTED_ALGORITHMS,
    JwsError,
    decode_extensions,
    encode_extensions,
    token_kid,
)

PROVIDER_NPI = "1234567890"
CALL_SID = "CA-jws-0001"


@pytest.fixture
def issued():
    """A real passport, its extension object, and the provider key."""
    m = AgentIdentityManager()
    prov_priv, prov_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(
        prov_priv, "agent-jws", agent_pub, ["eligibility", "claim_status"],
        call_sid=CALL_SID, provider_npi=PROVIDER_NPI,
    )
    passport = m.create_agent_passport(
        delegation, m.sign_delegation(prov_priv, delegation), agent_priv
    )
    hl7_b2b = {
        "version": "1",
        "subject_name": delegation.agent_id,
        "organization_id": "https://clinic.example.org",
        "purpose_of_use": purposes_for_scope(delegation.scope),
    }
    return m, passport, prov_pub, hl7_b2b, build_extension(passport)


@pytest.fixture
def ed_key():
    return Ed25519PrivateKey.generate()


# ── Round trip ────────────────────────────────────────────────────────────────

def test_a_token_round_trips_both_objects(issued, ed_key):
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    token = encode_extensions(hl7_b2b, nhid_agent, ed_key)
    back_b2b, back_agent, claims = decode_extensions(token, ed_key.public_key())
    assert back_b2b == hl7_b2b
    assert back_agent == nhid_agent
    assert "extensions" not in claims


def test_a_decoded_object_still_has_to_verify_against_the_passport(issued, ed_key):
    """The whole point of the ordering: the token is transport, the passport is
    the authority."""
    m, passport, prov_pub, hl7_b2b, nhid_agent = issued
    token = encode_extensions(hl7_b2b, nhid_agent, ed_key)
    _b2b, decoded_agent, _claims = decode_extensions(token, ed_key.public_key())
    result = verify_extension(decoded_agent, passport, prov_pub,
                              manager=m, call_sid=CALL_SID)
    assert result.valid


def test_a_perfectly_signed_token_carrying_a_tampered_object_is_caught(issued, ed_key):
    """A valid JWS signature means the token was assembled by the signer. It
    says nothing about whether the delegation inside is genuine — so a signer
    who edits the object produces a flawless token that still fails."""
    m, passport, prov_pub, hl7_b2b, nhid_agent = issued
    tampered = dict(nhid_agent, scope=["eligibility", "claim_status", "prior_auth"])
    token = encode_extensions(hl7_b2b, tampered, ed_key)
    _b2b, decoded_agent, _claims = decode_extensions(token, ed_key.public_key())

    # The token itself is beyond reproach.
    assert decoded_agent == tampered
    # The delegation is what settles it.
    result = verify_extension(decoded_agent, passport, prov_pub,
                              manager=m, call_sid=CALL_SID)
    assert not result.valid
    assert "scope" in result.reason


def test_extra_claims_survive_the_round_trip(issued, ed_key):
    """UDAP's authentication JWT needs iss/sub/aud/exp/jti; the module carries
    whatever the caller supplies without inventing any."""
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    token = encode_extensions(
        hl7_b2b, nhid_agent, ed_key,
        claims={"iss": "https://vendor.example.org", "sub": "vendor-client-id"},
    )
    _b2b, _agent, claims = decode_extensions(token, ed_key.public_key())
    assert claims["iss"] == "https://vendor.example.org"
    assert claims["sub"] == "vendor-client-id"


def test_rs256_is_supported_too(issued):
    """`alg` is a parameter because the right value is a question for the IG,
    not something this module decides."""
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = encode_extensions(hl7_b2b, nhid_agent, key, alg="RS256")
    back_b2b, back_agent, _ = decode_extensions(token, key.public_key(), alg="RS256")
    assert back_b2b == hl7_b2b and back_agent == nhid_agent


# ── Algorithm handling ────────────────────────────────────────────────────────

def test_none_is_not_an_accepted_algorithm(issued, ed_key):
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    assert "none" not in SUPPORTED_ALGORITHMS
    with pytest.raises(JwsError):
        encode_extensions(hl7_b2b, nhid_agent, ed_key, alg="none")
    with pytest.raises(JwsError):
        decode_extensions("x.y.z", ed_key.public_key(), alg="none")


def test_a_token_cannot_nominate_its_own_algorithm(issued, ed_key):
    """`algorithms` is pinned to what the caller expects, never read from the
    token's header, so a token signed with a different algorithm is refused
    rather than honoured."""
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = encode_extensions(hl7_b2b, nhid_agent, rsa_key, alg="RS256")
    with pytest.raises(JwsError):
        decode_extensions(token, rsa_key.public_key(), alg="EdDSA")


def test_the_wrong_key_does_not_verify(issued, ed_key):
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    token = encode_extensions(hl7_b2b, nhid_agent, ed_key)
    with pytest.raises(JwsError):
        decode_extensions(token, Ed25519PrivateKey.generate().public_key())


# ── kid ───────────────────────────────────────────────────────────────────────

def test_kid_travels_in_the_header(issued, ed_key):
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    token = encode_extensions(hl7_b2b, nhid_agent, ed_key, kid="2026-q4")
    assert token_kid(token) == "2026-q4"


def test_an_empty_kid_is_omitted_rather_than_sent_blank(issued, ed_key):
    """`kid: ""` would name a key called "empty string"."""
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    token = encode_extensions(hl7_b2b, nhid_agent, ed_key)
    assert token_kid(token) == ""
    import jwt
    assert "kid" not in jwt.get_unverified_header(token)


# ── Malformed input ───────────────────────────────────────────────────────────

def test_a_token_with_no_extensions_claim_is_refused(ed_key):
    import jwt
    token = jwt.encode({"iss": "someone"}, ed_key, algorithm="EdDSA")
    with pytest.raises(JwsError, match="no `extensions` object"):
        decode_extensions(token, ed_key.public_key())


@pytest.mark.parametrize("extensions", [
    {HL7_B2B_KEY: {"version": "1"}},                 # nhid-agent missing
    {EXTENSION_KEY: {"version": "1"}},               # hl7-b2b missing
    {HL7_B2B_KEY: "not an object", EXTENSION_KEY: {}},
    {HL7_B2B_KEY: {}, EXTENSION_KEY: ["not", "an", "object"]},
])
def test_a_half_populated_extensions_claim_is_refused(ed_key, extensions):
    import jwt
    token = jwt.encode({"extensions": extensions}, ed_key, algorithm="EdDSA")
    with pytest.raises(JwsError):
        decode_extensions(token, ed_key.public_key())


def test_supplying_extensions_directly_is_refused(issued, ed_key):
    """`extensions` is built from the two objects passed in; letting a caller
    also supply it would make which one wins a matter of dict ordering."""
    _m, _p, _pub, hl7_b2b, nhid_agent = issued
    with pytest.raises(JwsError, match="must not also be supplied"):
        encode_extensions(hl7_b2b, nhid_agent, ed_key,
                          claims={"extensions": {"anything": 1}})


@pytest.mark.parametrize("bad", ["not a dict", 42, None, ["a"]])
def test_non_object_extensions_are_refused_at_encode(ed_key, bad):
    with pytest.raises(JwsError):
        encode_extensions(bad, {"version": "1"}, ed_key)
    with pytest.raises(JwsError):
        encode_extensions({"version": "1"}, bad, ed_key)


def test_garbage_is_not_a_token(ed_key):
    with pytest.raises(JwsError):
        decode_extensions("this is not a jws", ed_key.public_key())
    with pytest.raises(JwsError):
        token_kid("this is not a jws")
