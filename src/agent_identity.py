"""
NHID-Clinical v1.4 — Cryptographic Agent Identity & Delegation Layer

Solves the core impersonation problem: any AI with web access can look up a
real provider NPI from NPPES in seconds. This module makes that insufficient.
A valid passport requires a cryptographic signature from the provider's private
key — something public NPI data cannot produce.

End-to-end payer verification flow:
    manager = AgentIdentityManager()
    prov_priv, prov_pub = manager.generate_agent_keys()
    agent_priv, agent_pub = manager.generate_agent_keys()
    delegation = manager.create_delegation(
        prov_priv, "agent-001", agent_pub,
        scope=["eligibility", "claim_status"],
        provider_npi="1234567890",
    )
    sig = manager.sign_delegation(prov_priv, delegation)
    passport = manager.create_agent_passport(delegation, sig, agent_priv)
    result = manager.verify_passport(passport, prov_pub)
    # result.valid is True; result.provider_npi == "1234567890"

HIPAA-safe: no PHI stored here. Pairs with NHID v1.3 PHI state machine and
call-bound nonces.
"""
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import hashlib, json, re, time, uuid, base64
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict

# ── Error codes ──────────────────────────────────────────────────────────�[...]

ERR_EXPIRED = "ERR_EXPIRED"
ERR_REVOKED = "ERR_REVOKED"
ERR_INVALID_SIG = "ERR_INVALID_SIG"
ERR_NONCE_MISMATCH = "ERR_NONCE_MISMATCH"
ERR_SCOPE_VIOLATION = "ERR_SCOPE_VIOLATION"
ERR_INVALID_NPI = "ERR_INVALID_NPI"
ERR_CHAIN_NARROWING = "ERR_CHAIN_NARROWING"
ERR_CHAIN_TOO_LONG = "ERR_CHAIN_TOO_LONG"

MAX_CHAIN_DEPTH = 3

_NPI_RE = re.compile(r'^\d{10}$')


def _validate_npi(npi: str) -> None:
    """Raise ValueError if npi is non-empty and not a valid 10-digit NPI."""
    if npi and not _NPI_RE.match(npi):
        raise ValueError(f"{ERR_INVALID_NPI}: '{npi}' must be exactly 10 digits")


# ── Data model ──────────────────────────────────────────────────────────��[...]

@dataclass
class Delegation:
    provider_npi: str
    agent_id: str
    agent_public_key_b64: str
    scope: List[str]
    expires_at: int
    created_at: int
    delegation_id: str
    call_sid: str = ""
    nonce: str = ""

    def to_json(self) -> str:
        # sort_keys ensures deterministic byte sequence regardless of Python runtime
        return json.dumps(asdict(self), sort_keys=True, separators=(',', ':'))

    @classmethod
    def from_json(cls, data: str):
        d = json.loads(data)
        d.setdefault("call_sid", "")
        d.setdefault("nonce", "")
        return cls(**d)


@dataclass
class AgentPassport:
    delegation: Delegation
    signature_b64: str
    agent_signature_b64: str


@dataclass
class VerificationResult:
    valid: bool
    reason: str
    delegation_id: Optional[str] = None
    provider_npi: Optional[str] = None
    agent_id: Optional[str] = None
    scope: Optional[List[str]] = None


# ── Identity manager ────────────────────────────────────────────────────────��[...]

class AgentIdentityManager:
    def __init__(self):
        # agent_id → revoked_at: revokes ALL delegations for an agent
        self.revocation_list: Dict[str, int] = {}
        # delegation_id → revoked_at: revokes one specific delegation
        self.revoked_delegations: Dict[str, int] = {}

    def generate_agent_keys(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
        priv = Ed25519PrivateKey.generate()
        return priv, priv.public_key()

    def public_key_to_b64(self, pub: Ed25519PublicKey) -> str:
        return base64.b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()

    def b64_to_public_key(self, b64: str) -> Ed25519PublicKey:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(b64))

    def create_delegation(
        self,
        provider_priv,
        agent_id: str,
        agent_pub,
        scope: List[str],
        ttl_seconds: int = 86400,
        call_sid: str = "",
        provider_npi: str = "",
    ) -> Delegation:
        """
        Issue a delegation from provider to agent.

        provider_npi binds this delegation to a specific NPI. Any caller can
        provide a real NPI from NPPES — only the holder of the provider's private
        key can produce a valid signature over a delegation containing that NPI.
        """
        _validate_npi(provider_npi)
        now = int(time.time())
        nonce = hashlib.sha256(f"{call_sid}:{now}".encode()).hexdigest() if call_sid else ""
        return Delegation(
            provider_npi=provider_npi,
            agent_id=agent_id,
            agent_public_key_b64=self.public_key_to_b64(agent_pub),
            scope=scope,
            expires_at=now + ttl_seconds,
            created_at=now,
            delegation_id=str(uuid.uuid4()),
            call_sid=call_sid,
            nonce=nonce,
        )

    def sign_delegation(self, provider_priv, delegation: Delegation) -> str:
        return base64.b64encode(provider_priv.sign(delegation.to_json().encode())).decode()

    def create_agent_passport(
        self, delegation: Delegation, provider_sig: str, agent_priv
    ) -> AgentPassport:
        agent_sig = base64.b64encode(agent_priv.sign(delegation.to_json().encode())).decode()
        return AgentPassport(
            delegation=delegation,
            signature_b64=provider_sig,
            agent_signature_b64=agent_sig,
        )

    def verify_passport(
        self,
        passport: AgentPassport,
        provider_pub,
        call_sid: str = "",
        required_scope: Optional[List[str]] = None,
    ) -> VerificationResult:
        """
        Verify a passport is authentic, unexpired, unrevoked, call-bound (if
        call_sid given), and in-scope (if required_scope given).

        A valid public NPI alone cannot produce a valid signature here — the
        provider's private key is required. This is what makes NPI impersonation
        impossible when payers enforce this check.
        """
        d = passport.delegation

        if d.agent_id in self.revocation_list:
            return VerificationResult(False, ERR_REVOKED)
        if d.delegation_id in self.revoked_delegations:
            return VerificationResult(False, ERR_REVOKED)

        if d.expires_at <= int(time.time()):
            return VerificationResult(False, ERR_EXPIRED, delegation_id=d.delegation_id)

        if d.call_sid and call_sid:
            expected = hashlib.sha256(f"{d.call_sid}:{d.created_at}".encode()).hexdigest()
            if d.nonce != expected or d.call_sid != call_sid:
                return VerificationResult(False, ERR_NONCE_MISMATCH)

        try:
            payload = d.to_json().encode()
            provider_pub.verify(base64.b64decode(passport.signature_b64), payload)
            agent_pub = self.b64_to_public_key(d.agent_public_key_b64)
            agent_pub.verify(base64.b64decode(passport.agent_signature_b64), payload)
        except Exception:
            return VerificationResult(False, ERR_INVALID_SIG)

        if required_scope:
            missing = [a for a in required_scope if a not in d.scope]
            if missing:
                return VerificationResult(False, f"{ERR_SCOPE_VIOLATION}: {missing}")

        return VerificationResult(
            True, "Valid",
            delegation_id=d.delegation_id,
            provider_npi=d.provider_npi,
            agent_id=d.agent_id,
            scope=d.scope,
        )

    def revoke_agent(self, agent_id: str) -> None:
        """Revoke all delegations for an agent."""
        self.revocation_list[agent_id] = int(time.time())

    def revoke_delegation(self, delegation_id: str) -> None:
        """Revoke one specific delegation, leaving other delegations for the same agent valid."""
        self.revoked_delegations[delegation_id] = int(time.time())

    def validate_chain(
        self,
        passports: List[AgentPassport],
        provider_pub,
    ) -> VerificationResult:
        """
        Validate a delegation chain (up to MAX_CHAIN_DEPTH hops).

        Rules:
          - First link is verified against the root provider public key.
          - Each subsequent link is verified against the previous link's agent key.
          - Scope must narrow at each hop (monotonic narrowing).
            No sub-delegate can grant actions beyond what they received.

        This prevents privilege escalation in multi-agent workflows: an EHR delegates
        to an orchestrator which delegates to a voice agent — the voice agent cannot
        claim more scope than the orchestrator was given.
        """
        if not passports:
            return VerificationResult(False, "Empty chain")
        if len(passports) > MAX_CHAIN_DEPTH:
            return VerificationResult(False, f"{ERR_CHAIN_TOO_LONG}: max {MAX_CHAIN_DEPTH}")

        result = self.verify_passport(passports[0], provider_pub)
        if not result.valid:
            return result

        current_scope = set(passports[0].delegation.scope)

        for i, passport in enumerate(passports[1:], start=1):
            prev_agent_pub = self.b64_to_public_key(passports[i - 1].delegation.agent_public_key_b64)
            result = self.verify_passport(passport, prev_agent_pub)
            if not result.valid:
                return result
            next_scope = set(passport.delegation.scope)
            if not next_scope.issubset(current_scope):
                escalated = sorted(next_scope - current_scope)
                return VerificationResult(False, f"{ERR_CHAIN_NARROWING}: {escalated} not in parent scope")
            current_scope = next_scope

        last = passports[-1].delegation
        return VerificationResult(
            True, "Valid chain",
            delegation_id=last.delegation_id,
            provider_npi=passports[0].delegation.provider_npi,
            agent_id=last.agent_id,
            scope=sorted(current_scope),
        )
