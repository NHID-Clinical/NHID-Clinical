"""NHID-Clinical v1.4 - Cryptographic Agent Identity Layer"""
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import json, time, base64
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict

@dataclass
class Delegation:
    provider_npi: str
    agent_id: str
    agent_public_key_b64: str
    scope: List[str]
    expires_at: int
    created_at: int
    delegation_id: str
    def to_json(self) -> str: return json.dumps(asdict(self))
    @classmethod
    def from_json(cls, data: str): return cls(**json.loads(data))

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

class AgentIdentityManager:
    def __init__(self):
        self.revocation_list: Dict[str, int] = {}
    def generate_agent_keys(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
        priv = Ed25519PrivateKey.generate()
        return priv, priv.public_key()
    def public_key_to_b64(self, pub: Ed25519PublicKey) -> str:
        return base64.b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    def b64_to_public_key(self, b64: str) -> Ed25519PublicKey:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(b64))
    def create_delegation(self, provider_priv, agent_id, agent_pub, scope, ttl_seconds=86400):
        now = int(time.time())
        return Delegation(
            provider_npi="TODO", agent_id=agent_id,
            agent_public_key_b64=self.public_key_to_b64(agent_pub),
            scope=scope, expires_at=now+ttl_seconds,
            created_at=now, delegation_id=f"del_{agent_id}_{now}"
        )
    def sign_delegation(self, provider_priv, delegation):
        return base64.b64encode(provider_priv.sign(delegation.to_json().encode())).decode()
    def create_agent_passport(self, delegation, provider_sig, agent_priv):
        agent_sig = base64.b64encode(agent_priv.sign(delegation.to_json().encode())).decode()
        return AgentPassport(delegation=delegation, signature_b64=provider_sig, agent_signature_b64=agent_sig)
    def verify_passport(self, passport, provider_pub):
        d = passport.delegation
        if d.agent_id in self.revocation_list:
            return VerificationResult(False, f"Agent {d.agent_id} revoked")
        if d.expires_at <= int(time.time()):
            return VerificationResult(False, "Expired", delegation_id=d.delegation_id)
        try:
            provider_pub.verify(base64.b64decode(passport.signature_b64), d.to_json().encode())
            agent_pub = self.b64_to_public_key(d.agent_public_key_b64)
            agent_pub.verify(base64.b64decode(passport.agent_signature_b64), d.to_json().encode())
        except Exception as e:
            return VerificationResult(False, f"Signature error: {e}")
        return VerificationResult(True, "Valid", delegation_id=d.delegation_id, provider_npi=d.provider_npi, agent_id=d.agent_id, scope=d.scope)
    def revoke_agent(self, agent_id): self.revocation_list[agent_id] = int(time.time())
