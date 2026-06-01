from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import hashlib, json, re, time, uuid, base64
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict


# ── Error codes ─────────────────────────────────────────────
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
    if npi and not _NPI_RE.match(npi):
        raise ValueError(f"{ERR_INVALID_NPI}: '{npi}' must be exactly 10 digits")


# ── Data models ─────────────────────────────────────────────
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


# ── Identity Manager ─────────────────────────────────────────
class AgentIdentityManager:
    def __init__(self):
        self.revocation_list: Dict[str, int] = {}
        self.revoked_delegations: Dict[str, int] = {}

        # cache decoded delegation payloads only
        self._payload_cache: Dict[str, bytes] = {}

        # cache parsed public keys
        self._pubkey_cache: Dict[str, Ed25519PublicKey] = {}

        # CRITICAL: cache full crypto verification result per delegation
        self._crypto_cache: Dict[str, bool] = {}

    # ── key utils ─────────────────────────────
    def generate_agent_keys(self):
        priv = Ed25519PrivateKey.generate()
        return priv, priv.public_key()

    def public_key_to_b64(self, pub: Ed25519PublicKey) -> str:
        return base64.b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()

    def b64_to_public_key(self, b64: str) -> Ed25519PublicKey:
        if b64 in self._pubkey_cache:
            return self._pubkey_cache[b64]
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(b64))
        self._pubkey_cache[b64] = pub
        return pub

    # ── delegation creation ───────────────────
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

    def create_agent_passport(self, delegation: Delegation, provider_sig: str, agent_priv):
        agent_sig = base64.b64encode(agent_priv.sign(delegation.to_json().encode())).decode()
        return AgentPassport(delegation, provider_sig, agent_sig)

    # ── HOT PATH FIX: verify ───────────────────
    def verify_passport(
        self,
        passport: AgentPassport,
        provider_pub,
        call_sid: str = "",
        required_scope: Optional[List[str]] = None,
    ) -> VerificationResult:

        d = passport.delegation
        now = int(time.time())

        # revocation checks
        if d.agent_id in self.revocation_list:
            return VerificationResult(False, ERR_REVOKED)
        if d.delegation_id in self.revoked_delegations:
            return VerificationResult(False, ERR_REVOKED)

        if d.expires_at <= now:
            return VerificationResult(False, ERR_EXPIRED, delegation_id=d.delegation_id)

        # nonce check
        if d.call_sid and call_sid:
            expected = hashlib.sha256(f"{d.call_sid}:{d.created_at}".encode()).hexdigest()
            if d.nonce != expected or d.call_sid != call_sid:
                return VerificationResult(False, ERR_NONCE_MISMATCH)

        # ── CRITICAL OPTIMIZATION: crypto cache ──
        cache_key = d.delegation_id
        cached = self._crypto_cache.get(cache_key)

        if cached is None:
            payload = d.to_json().encode()

            try:
                prov_sig = base64.b64decode(passport.signature_b64)
                agent_sig = base64.b64decode(passport.agent_signature_b64)
                agent_pub = self.b64_to_public_key(d.agent_public_key_b64)
            except Exception:
                return VerificationResult(False, ERR_INVALID_SIG)

            try:
                provider_pub.verify(prov_sig, payload)
                agent_pub.verify(agent_sig, payload)
            except Exception:
                return VerificationResult(False, ERR_INVALID_SIG)

            self._crypto_cache[cache_key] = True
        else:
            # skip cryptography entirely
            pass

        # scope check (still must run every time)
        if required_scope:
            missing = [a for a in required_scope if a not in d.scope]
            if missing:
                return VerificationResult(False, f"{ERR_SCOPE_VIOLATION}: {missing}")

        return VerificationResult(
            True,
            "Valid",
            delegation_id=d.delegation_id,
            provider_npi=d.provider_npi,
            agent_id=d.agent_id,
            scope=d.scope,
        )

    # ── revocation ─────────────────────────────
    def revoke_agent(self, agent_id: str) -> None:
        self.revocation_list[agent_id] = int(time.time())

    def revoke_delegation(self, delegation_id: str) -> None:
        self.revoked_delegations[delegation_id] = int(time.time())
