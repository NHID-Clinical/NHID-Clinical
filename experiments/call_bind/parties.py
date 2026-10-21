"""
The three parties, kept separate because the separation is the experiment.

`Issuer` holds the provider root key. `Agent` holds its own key and the
passport it was issued. `Receiver` holds trust anchors, a revocation store and
the policy engine — and, critically, **its own view of which call is in
progress**.

That last part is the whole point. In the current pipeline the call identifier
reaches the engine as `event["session_id"]`, supplied by whoever is integrating
— so an agent presenting both the credential and the call identifier it should
be checked against is not being checked against anything. Here the receiver
takes the call id from its own side, standing in for a payer's telephony
platform, which knows it because it is a party to the call.

Everything is synthetic: ephemeral keys, `CA-*` call ids, NPIs that are not
registered to anyone. No PHI, no network, no external service.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agent_identity import (  # noqa: E402
    AgentIdentityManager,
    AgentPassport,
    PresentationProof,
    new_verifier_nonce,
)
from src.nhid_policy_engine_v1 import (  # noqa: E402
    DelegationContext,
    PolicyAction,
    evaluate_all,
)
from src.trust_anchor import StaticTrustAnchorResolver  # noqa: E402


@dataclass
class Issuer:
    """A provider organization. Holds the root signing key."""

    npi: str
    kid: str = "2026-q4"
    manager: AgentIdentityManager = field(default_factory=AgentIdentityManager)

    def __post_init__(self) -> None:
        self._priv, self.pub = self.manager.generate_agent_keys()

    @property
    def public_key_b64(self) -> str:
        return self.manager.public_key_to_b64(self.pub)

    def delegate(self, agent: "Agent", scope: list[str], call_sid: str,
                 ttl_seconds: int = 3600, npi: Optional[str] = None) -> AgentPassport:
        """Issue and dual-sign a delegation to `agent` for one call."""
        delegation = self.manager.create_delegation(
            self._priv,
            agent.agent_id,
            agent.pub,
            scope,
            ttl_seconds=ttl_seconds,
            call_sid=call_sid,
            provider_npi=self.npi if npi is None else npi,
            kid=self.kid,
        )
        signature = self.manager.sign_delegation(self._priv, delegation)
        return self.manager.create_agent_passport(delegation, signature, agent.priv)


@dataclass
class Agent:
    """A voice agent. Holds the private key named in its delegation."""

    agent_id: str
    manager: AgentIdentityManager = field(default_factory=AgentIdentityManager)

    def __post_init__(self) -> None:
        self.priv, self.pub = self.manager.generate_agent_keys()

    def sub_delegate(self, child: "Agent", scope: list[str], parent: AgentPassport,
                     call_sid: str = "", ttl_seconds: int = 3600) -> AgentPassport:
        """Hand a narrower grant down one hop, signed with this agent's key.

        No server is contacted: attenuation happens at the holder, which is the
        property that makes an offline-verifiable chain possible at all.
        """
        delegation = self.manager.create_delegation(
            self.priv, child.agent_id, child.pub, scope,
            ttl_seconds=ttl_seconds, call_sid=call_sid,
            provider_npi="",  # only the root anchors to a provider
            kid="",
        )
        signature = self.manager.sign_delegation(self.priv, delegation)
        return self.manager.create_agent_passport(delegation, signature, child.priv)

    def answer_challenge(self, delegation, nonce: str) -> PresentationProof:
        """Prove possession of the delegated key, now, for this challenge."""
        return self.manager.create_presentation_proof(self.priv, delegation, nonce)


@dataclass
class Outcome:
    """What the receiver decided, and how long deciding took."""

    permitted: bool
    action: str
    reason_code: str
    detail: str
    latency_ms: float

    @property
    def diagnosis(self) -> str:
        """The reason code, plus the underlying error token when there is one.

        Reason codes group deliberately — two different forged-signature
        attacks both diagnose ERR_INVALID_SIG, which is correct. This is what
        the matrix asserts against.
        """
        token = ""
        for part in self.detail.replace(":", " ").split():
            # The error token is quoted inside a sentence, so it arrives with
            # whatever punctuation ended the clause attached to it.
            part = part.strip(".,;'\")")
            if part.startswith("ERR_"):
                token = part
                break
        return f"{self.reason_code}/{token}" if token else self.reason_code


class Receiver:
    """The payer side: verifies, and decides.

    Holds the trust anchors it decided to trust, the durable revocation set,
    and its own `live_call_sid` — the call identifier it reads from its own
    telephony platform rather than from the credential in front of it.
    """

    def __init__(self, anchors: dict[str, tuple[str, str]],
                 require_possession_proof: bool = True) -> None:
        """
        Args:
            anchors: npi -> (base64 public key, kid). Populated out of band, as
                `src/trust_anchor.py` documents — there is no discovery here
                and this experiment does not pretend otherwise.
            require_possession_proof: issue a challenge and require an answer.
        """
        self._resolver = StaticTrustAnchorResolver()
        for npi, (key_b64, kid) in anchors.items():
            self._resolver.add(npi, key_b64, kid)
        self._revoked: set[str] = set()
        self.require_possession_proof = require_possession_proof
        self.manager = AgentIdentityManager()

    def revoke(self, delegation_id: str) -> None:
        """Stand in for `nhid_event_store.record_revocation`.

        A set, not the SQLite store, so the experiment needs no filesystem —
        what is being tested is that the revocation *reaches the control*,
        which is the defect that existed, not that SQLite works.
        """
        self._revoked.add(delegation_id)

    def issue_challenge(self) -> str:
        return new_verifier_nonce() if self.require_possession_proof else ""

    def handle_call(
        self,
        live_call_sid: str,
        credential: Any,
        speech: str,
        proof: Optional[PresentationProof] = None,
        verifier_nonce: str = "",
    ) -> Outcome:
        """Evaluate one turn of a call the receiver is already party to.

        `live_call_sid` comes from the receiver, never from `credential`.
        """
        import time

        context = DelegationContext(
            resolver=self._resolver,
            require_delegation=True,
            enforce_scope=True,
            require_call_binding=True,
            require_possession_proof=self.require_possession_proof,
            revocation_checker=lambda did: did in self._revoked,
        )
        session: dict[str, Any] = {
            "turn_count": 1,
            "escalation_path_available": True,
            "counterparty_type": "human_operator",
            "disclosure_established_prior": True,
            "identity_manager": self.manager,
        }
        if credential is not None:
            session["agent_passport"] = credential
        if verifier_nonce:
            session["verifier_nonce"] = verifier_nonce
            session["presentation_proof"] = proof

        event = _event(live_call_sid, speech)

        started = time.perf_counter()
        decision = evaluate_all(session, event, context)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        detail = " ".join(v.description for v in decision.violations)
        return Outcome(
            permitted=decision.action
            not in (PolicyAction.DENY_DATA, PolicyAction.ESCALATE_HUMAN),
            action=decision.action.name,
            reason_code=decision.reason_code,
            detail=detail,
            latency_ms=elapsed_ms,
        )


def _event(call_sid: str, speech: str) -> dict:
    """A fully-populated NHID event for one agent turn.

    Disclosure is already established and every ATR-01 field is present, so
    the outcome under test is the delegation decision and not an audit or
    disclosure failure arriving first up the enforcement ladder.
    """
    return {
        "event_id": f"e-{call_sid}",
        "session_id": call_sid,
        "request_id": f"r-{call_sid}",
        "timestamp": "2026-10-21T10:00:00.000Z",
        "event_type": "POLICY",
        "actor_id": "agent-under-test",
        "state_before": "ACTIVE",
        "state_after": "ACTIVE",
        "counterparty_type": "human_operator",
        "replay_mode": "live",
        "external_calls_cached": False,
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0.0",
        },
        "input_payload": {"speech_text": speech, "raw_form_fields": None},
        "healthcare_governance": {
            "disclosure_timestamp": "2026-10-21T09:59:55.000Z",
            "identity_assertion_text": "I am an automated verification assistant",
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": [],
        },
    }
