"""
Trust anchor resolution — regression tests
==========================================
The resolver decides which provider organizations this deployment will accept
delegations from. Its failure mode matters more than its success mode: an
unresolvable NPI must return None so DLG-01 denies, never raise past the
policy engine and never fall through to a permissive default.
"""
import pytest

from src.agent_identity import AgentIdentityManager
from src.agent_identity import AgentIdentityManager, _validate_npi, npi_check_digit_valid
from src.trust_anchor import StaticTrustAnchorResolver, TrustAnchorResolver

NPI_A = "1234567890"
NPI_B = "9876543210"


@pytest.fixture
def manager():
    return AgentIdentityManager()


@pytest.fixture
def key_b64(manager):
    _, pub = manager.generate_agent_keys()
    return manager.public_key_to_b64(pub)


def test_registered_npi_resolves(key_b64):
    resolver = StaticTrustAnchorResolver({NPI_A: key_b64})
    assert resolver.resolve(NPI_A) is not None


def test_unregistered_npi_returns_none(key_b64):
    resolver = StaticTrustAnchorResolver({NPI_A: key_b64})
    assert resolver.resolve(NPI_B) is None


def test_empty_resolver_trusts_nobody():
    resolver = StaticTrustAnchorResolver()
    assert resolver.resolve(NPI_A) is None
    assert len(resolver) == 0


def test_resolved_key_round_trips_a_signature(manager):
    """The resolved key must actually verify what the provider signed."""
    priv, pub = manager.generate_agent_keys()
    resolver = StaticTrustAnchorResolver({NPI_A: manager.public_key_to_b64(pub)})
    _, agent_pub = manager.generate_agent_keys()
    delegation = manager.create_delegation(
        priv, "agent-1", agent_pub, scope=["eligibility"], provider_npi=NPI_A
    )
    signature = manager.sign_delegation(priv, delegation)
    import base64

    resolver.resolve(NPI_A).verify(
        base64.b64decode(signature), delegation.to_json().encode()
    )


def test_mismatched_key_does_not_verify(manager):
    """A resolver holding the wrong key for an NPI must fail verification."""
    import base64

    from cryptography.exceptions import InvalidSignature

    real_priv, _ = manager.generate_agent_keys()
    _, wrong_pub = manager.generate_agent_keys()
    resolver = StaticTrustAnchorResolver({NPI_A: manager.public_key_to_b64(wrong_pub)})
    _, agent_pub = manager.generate_agent_keys()
    delegation = manager.create_delegation(
        real_priv, "agent-1", agent_pub, scope=["eligibility"], provider_npi=NPI_A
    )
    signature = manager.sign_delegation(real_priv, delegation)
    with pytest.raises(InvalidSignature):
        resolver.resolve(NPI_A).verify(
            base64.b64decode(signature), delegation.to_json().encode()
        )


# ── Input validation — malformed anchors are rejected at construction ──────

@pytest.mark.parametrize("bad_npi", ["123", "abcdefghij", "12345678901", "", "12345 6789"])
def test_malformed_npi_rejected(bad_npi, key_b64):
    with pytest.raises(ValueError, match="invalid NPI"):
        StaticTrustAnchorResolver({bad_npi: key_b64})


@pytest.mark.parametrize("bad_key", ["", "not-base64!!", "c2hvcnQ="])
def test_malformed_key_rejected(bad_key):
    with pytest.raises(ValueError):
        StaticTrustAnchorResolver({NPI_A: bad_key})


def test_non_string_npi_resolves_to_none(key_b64):
    resolver = StaticTrustAnchorResolver({NPI_A: key_b64})
    assert resolver.resolve(None) is None
    assert resolver.resolve(1234567890) is None


def test_add_registers_incrementally(key_b64):
    resolver = StaticTrustAnchorResolver()
    resolver.add(NPI_A, key_b64)
    assert resolver.known_npis() == frozenset({NPI_A})
    assert len(resolver) == 1


def test_static_resolver_satisfies_the_protocol(key_b64):
    """A future discovery-backed resolver must be substitutable for this one."""
    assert isinstance(StaticTrustAnchorResolver({NPI_A: key_b64}), TrustAnchorResolver)


def test_resolution_is_deterministic(key_b64):
    resolver = StaticTrustAnchorResolver({NPI_A: key_b64})
    assert resolver.resolve(NPI_A) is resolver.resolve(NPI_A)


# ── NPI check digit (opt-in) ──────────────────────────────────────────────────

@pytest.mark.parametrize("npi,expected", [
    ("1234567893", True),    # 1234567890 with the correct check digit
    ("1679576722", True),
    ("1234567890", False),   # UDAP's worked example; not Luhn-valid
    ("9999999999", False),
    ("123456789", False),    # too short
    ("12345678934", False),  # too long
    ("abcdefghij", False),
    ("", False),
])
def test_npi_check_digit_valid(npi, expected):
    assert npi_check_digit_valid(npi) is expected


def test_check_digit_validation_is_off_by_default():
    """The project's own synthetic NPI (1234567890, 108 occurrences) is not
    Luhn-valid, and it is UDAP's published example. Turning the check on
    globally would reject it, so it is a deployment opt-in."""
    _validate_npi("1234567890")                      # no raise
    with pytest.raises(ValueError):
        _validate_npi("1234567890", check_digit=True)


def test_an_empty_npi_passes_either_way():
    """A sub-delegation names no provider; the check must not invent one."""
    _validate_npi("")
    _validate_npi("", check_digit=True)


# ── Key rotation via kid ──────────────────────────────────────────────────────

def test_two_keys_for_one_provider_resolve_by_kid():
    """The rotation window: both keys registered, each delegation naming its own."""
    m = AgentIdentityManager()
    _, old_pub = m.generate_agent_keys()
    _, new_pub = m.generate_agent_keys()
    r = StaticTrustAnchorResolver()
    r.add(NPI_A, m.public_key_to_b64(old_pub), kid="2026-q3")
    r.add(NPI_A, m.public_key_to_b64(new_pub), kid="2026-q4")

    assert r.resolve(NPI_A, "2026-q3") is not None
    assert r.resolve(NPI_A, "2026-q4") is not None
    assert r.resolve(NPI_A, "2026-q3") is not r.resolve(NPI_A, "2026-q4")
    assert r.known_npis() == frozenset({NPI_A})


def test_a_named_kid_falls_back_to_an_unlabelled_key():
    """A deployer holding one key for a provider has named the key for that
    provider; a signer that starts labelling must not break them."""
    m = AgentIdentityManager()
    _, pub = m.generate_agent_keys()
    r = StaticTrustAnchorResolver({NPI_A: m.public_key_to_b64(pub)})
    assert r.resolve(NPI_A, "some-new-kid") is not None
    assert r.resolve(NPI_A) is not None


def test_strict_kid_enforcement_is_available():
    """Register no unlabelled key and an unknown kid resolves to nothing."""
    m = AgentIdentityManager()
    _, pub = m.generate_agent_keys()
    r = StaticTrustAnchorResolver()
    r.add(NPI_A, m.public_key_to_b64(pub), kid="2026-q4")
    assert r.resolve(NPI_A, "2026-q4") is not None
    assert r.resolve(NPI_A, "retired-key") is None
    assert r.resolve(NPI_A) is None


def test_a_rotated_key_is_distinguishable_from_a_forgery():
    """The gap kid closes.

    Without a key identifier, a delegation signed by a provider's retired key
    and a delegation signed by an attacker both fail as ERR_INVALID_SIG, and
    the verifier cannot tell which it is looking at. With one, the retired key
    is simply not a registered anchor — an unresolvable kid, not a bad
    signature.
    """
    m = AgentIdentityManager()
    retired_priv, retired_pub = m.generate_agent_keys()
    _, current_pub = m.generate_agent_keys()
    r = StaticTrustAnchorResolver()
    r.add(NPI_A, m.public_key_to_b64(current_pub), kid="current")

    assert r.resolve(NPI_A, "retired") is None
    assert r.resolve(NPI_A, "current") is not None
