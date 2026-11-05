"""Ida, the reference caller-agent: its definition and its agent-side signer.

Ida places a call to a payer's provider line for a fictional dental practice and
asks for one claim's status (`agents/ida_system_prompt.md`). Before she says any
patient identifier, her `nhid_gate` tool asks the payer-side gate whether she may
(`functions.handler.gate_turn`). This module is what stands between that tool and
the gate, on the agent's side:

1. **Per-call delegation.** The practice (the issuer) signs a delegation for this
   one call: Ida's key, the call id, a narrow scope (the claim-status workflow,
   which covers member id, date of birth and claim number) and a short expiry. `PracticeIssuer.delegate`.
2. **Challenge.** The gate issues a fresh verifier nonce for the call
   (`functions.handler.gate_challenge`).
3. **Proof of possession.** Ida signs the nonce with the key her delegation
   names (`src.agent_identity.PresentationProof`).
4. **Presentation.** The passport and the proof go to the gate with the planned
   sentence, out of band over HTTPS, bound to the call. The payer side checks
   them against its own trust anchors in DLG-01, and the verified scope limits
   what PDX-01 lets her say.

Three parties, one deployment: in the demonstration the practice, Ida and the
payer gate run in one service with separate keys, so the flow can be shown end
to end. In a real deployment each is a different organisation; the code paths
do not share keys or state.

Demo credentials only. Keys come from the environment (`from_environment`) and are
minted by `scripts/ida_demo_credentials.py`. They are never committed and never
production keys.
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from src.agent_identity import AgentIdentityManager, AgentPassport

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"

#: What Ida's delegation authorizes: the claim-status workflow, in the engine's
#: scope names (`_SCOPE_PERMITTED_FIELDS`). It covers the member id, date of
#: birth and claim number she needs; a prior-auth number, for example, it does not.
IDA_SCOPE = ("claim_status",)
#: A per-call delegation lives for one call, not a day.
DELEGATION_TTL_SECONDS = 15 * 60
#: A fictional practice NPI with a valid check digit. Registered to no one.
DEMO_PRACTICE_NPI = "1234567893"
IDA_AGENT_ID = "ida-reference-agent"


# ── definition ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentDefinition:
    """Everything that defines the agent, read from `agents/<name>.*`."""
    name: str
    first_message: str
    system_prompt: str
    config: dict = field(default_factory=dict)


def load_definition(agent: str = "ida") -> AgentDefinition:
    from src.elevenlabs_client import (
        _extract_canonical_first_message, _extract_canonical_name, _extract_canonical_prompt,
    )
    prompt_path = AGENTS / f"{agent}_system_prompt.md"
    config_path = AGENTS / f"{agent}.config.json"
    return AgentDefinition(
        name=_extract_canonical_name(prompt_path) or agent,
        first_message=_extract_canonical_first_message(prompt_path) or "",
        system_prompt=_extract_canonical_prompt(prompt_path) or "",
        config=json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {},
    )


# ── keys ─────────────────────────────────────────────────────────────────────

def private_key_to_b64(key: Ed25519PrivateKey) -> str:
    raw = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    return base64.b64encode(raw).decode()


def private_key_from_b64(b64: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(b64))


def passport_to_dict(passport: AgentPassport) -> dict:
    return {
        "delegation": asdict(passport.delegation),
        "signature_b64": passport.signature_b64,
        "agent_signature_b64": passport.agent_signature_b64,
    }


# ── the practice and the agent ──────────────────────────────────────────────

@dataclass
class PracticeIssuer:
    """The provider organisation Ida calls for. Holds the root signing key."""
    key: Ed25519PrivateKey
    npi: str = DEMO_PRACTICE_NPI
    kid: str = "demo-1"
    manager: AgentIdentityManager = field(default_factory=AgentIdentityManager)

    @property
    def public_key_b64(self) -> str:
        return self.manager.public_key_to_b64(self.key.public_key())

    def trust_anchor_entry(self) -> str:
        """This practice as the payer would configure it: NHID_TRUST_ANCHORS."""
        return f"{self.npi}:{self.public_key_b64}:{self.kid}"

    def delegate(self, agent_id: str, agent_key: Ed25519PrivateKey, call_id: str,
                 scope=IDA_SCOPE, ttl_seconds: int = DELEGATION_TTL_SECONDS) -> AgentPassport:
        """A dual-signed passport for one call. The agent co-signs with its own key."""
        delegation = self.manager.create_delegation(
            self.key, agent_id, agent_key.public_key(), list(scope),
            ttl_seconds=ttl_seconds, call_sid=call_id, provider_npi=self.npi, kid=self.kid,
        )
        signature = self.manager.sign_delegation(self.key, delegation)
        return self.manager.create_agent_passport(delegation, signature, agent_key)


Gate = Callable[[dict], Tuple[int, dict]]


@dataclass
class ReferenceAgentSigner:
    """Ida's side of the gate: gets a per-call delegation, answers the gate's
    challenge with her key, and presents both with the planned sentence."""
    agent_key: Ed25519PrivateKey
    issuer: PracticeIssuer
    agent_id: str = IDA_AGENT_ID
    manager: AgentIdentityManager = field(default_factory=AgentIdentityManager)
    _passports: Dict[str, AgentPassport] = field(default_factory=dict)

    def passport_for(self, call_id: str) -> AgentPassport:
        if call_id not in self._passports:
            if len(self._passports) > 1000:
                self._passports.clear()
            self._passports[call_id] = self.issuer.delegate(self.agent_id, self.agent_key, call_id)
        return self._passports[call_id]

    def gate(self, params: dict, *, get_challenge: Gate, payer_gate: Gate) -> Tuple[int, dict]:
        call_id = str((params or {}).get("session_id") or "").strip()
        if not call_id:
            return 400, {"error": "session_id is required"}
        passport = self.passport_for(call_id)
        status, challenge = get_challenge({"session_id": call_id})
        if status != 200:
            return status, challenge
        proof = self.manager.create_presentation_proof(
            self.agent_key, passport.delegation, challenge["verifier_nonce"])
        return payer_gate({
            **params,
            "actor_id": params.get("actor_id") or self.agent_id,
            "passport": passport_to_dict(passport),
            "presentation_proof": asdict(proof),
        })


ENV_AGENT_KEY = "IDA_AGENT_KEY_B64"
ENV_PRACTICE_KEY = "IDA_PRACTICE_KEY_B64"
ENV_PRACTICE_NPI = "IDA_PRACTICE_NPI"
ENV_PRACTICE_KID = "IDA_PRACTICE_KID"


def from_environment() -> Optional[ReferenceAgentSigner]:
    """Ida's signer from demo credentials in the environment, or None if unset."""
    agent_b64 = (os.environ.get(ENV_AGENT_KEY) or "").strip()
    practice_b64 = (os.environ.get(ENV_PRACTICE_KEY) or "").strip()
    if not agent_b64 or not practice_b64:
        return None
    issuer = PracticeIssuer(
        key=private_key_from_b64(practice_b64),
        npi=(os.environ.get(ENV_PRACTICE_NPI) or DEMO_PRACTICE_NPI).strip(),
        kid=(os.environ.get(ENV_PRACTICE_KID) or "demo-1").strip(),
    )
    return ReferenceAgentSigner(agent_key=private_key_from_b64(agent_b64), issuer=issuer)
