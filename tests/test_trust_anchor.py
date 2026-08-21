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
