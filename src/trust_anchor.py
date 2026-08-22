"""
Trust Anchor Resolution
=======================
Resolves a provider NPI to the Ed25519 public key that signs delegations for
that provider, so a verifier can check an agent passport without having been
handed the key out of band.

`src/agent_identity.py`'s `verify_passport(passport, provider_pub, ...)` takes
the provider public key as an argument. That is correct for the primitive, but
it means the caller must already possess the key — which is exactly what a
verifier on the other side of an organizational boundary does not have. This
module supplies the missing lookup and nothing more.

Scope, deliberately:

  * Resolution is a **local, deterministic lookup**. The core policy engine
    performs no network calls, so the only implementation here is a static
    in-memory mapping the deploying organization populates itself.
  * Failure is **explicit**. An unresolvable NPI returns `None` and the caller
    must treat that as a verification failure, never as a pass.
  * This is **not** a trust network, a registry, a directory service, or a
    certificate authority. It resolves keys the deployer already decided to
    trust.

The interface is shaped so a discovery-backed implementation (for example the
JWKS-style discovery discussed in `docs/nhid-auth-pki-and-oauth2-integration.md`
§1.8) can be added later by implementing `TrustAnchorResolver` elsewhere,
without changing policy-engine semantics. No such implementation exists today.
"""
from __future__ import annotations

import base64
from typing import Protocol, runtime_checkable

_NPI_LENGTH = 10


@runtime_checkable
class TrustAnchorResolver(Protocol):
    """Resolves a provider NPI to that provider's delegation-signing public key.

    Implementations MUST be deterministic for a given NPI within a single
    evaluation, and MUST return None rather than raising when an NPI is not
    trusted. Returning None is a decision ("this provider is not a trust
    anchor here"), not an error condition.
    """

    def resolve(self, npi: str) -> object | None:
        """Return an Ed25519PublicKey for `npi`, or None if not resolvable."""
        ...


class StaticTrustAnchorResolver:
    """Resolves NPIs against an in-memory mapping supplied at construction.

    This is the only resolver shipped with the project. The deploying
    organization decides which providers it trusts and supplies their public
    keys directly — typically exchanged during vendor onboarding and stored
    alongside the rest of that relationship's configuration.

    Keys are accepted as base64-encoded raw Ed25519 public keys, the same
    encoding `AgentIdentityManager.public_key_to_b64` produces, so a key can be
    round-tripped between issuing and verifying sides without conversion.
    """

    def __init__(self, anchors: dict[str, str] | None = None) -> None:
        """
        Args:
            anchors: mapping of provider NPI (10 digits) to base64 raw Ed25519
                public key. Malformed entries are rejected at construction
                rather than silently failing later at verification time.
        """
        self._keys: dict[str, object] = {}
        for npi, key_b64 in (anchors or {}).items():
            self.add(npi, key_b64)

    def add(self, npi: str, public_key_b64: str) -> None:
        """Register one provider's signing key. Raises ValueError if invalid."""
        if not isinstance(npi, str) or len(npi) != _NPI_LENGTH or not npi.isdigit():
            raise ValueError(f"invalid NPI '{npi}': must be exactly 10 digits")
        self._keys[npi] = _decode_public_key(public_key_b64)

    def resolve(self, npi: str) -> object | None:
        """Return the registered public key for `npi`, or None if not registered."""
        if not isinstance(npi, str):
            return None
        return self._keys.get(npi)

    def known_npis(self) -> frozenset[str]:
        """The NPIs this resolver will accept. Useful for diagnostics and tests."""
        return frozenset(self._keys)

    def __len__(self) -> int:
        return len(self._keys)


def _decode_public_key(public_key_b64: str) -> object:
    """Decode a base64 raw Ed25519 public key, raising ValueError if malformed."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(public_key_b64, str) or not public_key_b64:
        raise ValueError("public key must be a non-empty base64 string")
    try:
        raw = base64.b64decode(public_key_b64, validate=True)
        return Ed25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        raise ValueError(f"invalid Ed25519 public key: {exc}") from exc
