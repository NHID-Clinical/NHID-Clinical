"""
NHID-Clinical v2 — Cryptographic Agent Identity & Delegation Layer

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
"""
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import re, hashlib, json, secrets, time, uuid, base64
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_EXPIRED         = "ERR_EXPIRED"
ERR_REVOKED         = "ERR_REVOKED"
ERR_INVALID_SIG     = "ERR_INVALID_SIG"
ERR_NONCE_MISMATCH  = "ERR_NONCE_MISMATCH"
ERR_SCOPE_VIOLATION = "ERR_SCOPE_VIOLATION"
ERR_INVALID_NPI     = "ERR_INVALID_NPI"
ERR_CHAIN_NARROWING = "ERR_CHAIN_NARROWING"
ERR_CHAIN_TOO_LONG  = "ERR_CHAIN_TOO_LONG"
ERR_PROOF_MISSING   = "ERR_PROOF_MISSING"
ERR_PROOF_MISMATCH  = "ERR_PROOF_MISMATCH"
ERR_PROOF_STALE     = "ERR_PROOF_STALE"

MAX_CHAIN_DEPTH = 3

#: Format version carried inside every signed `Delegation`. Bump it only for a
#: change a verifier must not silently misread; a verifier that does not know a
#: version refuses the delegation rather than failing its signature check and
#: reporting what looks like a forgery.
DELEGATION_FORMAT_VERSION = "2"
ERR_UNSUPPORTED_VERSION = "ERR_UNSUPPORTED_VERSION"

#: How long a presentation proof stays acceptable. A proof is answered and
#: checked within one call setup, so this is generous rather than tight; it
#: exists to bound replay of a proof captured from an earlier exchange, and the
#: nonce is what actually ties a proof to this verification.
MAX_PROOF_AGE_SECONDS = 300
_NPI_RE = re.compile(r'^\d{10}$')


#: Prefix CMS specifies for the NPI's Luhn computation, standing in for the
#: ISO 7812 issuer identifier the 10-digit NPI omits.
_NPI_LUHN_PREFIX = "80840"


def npi_check_digit_valid(npi: str) -> bool:
    """Whether `npi`'s tenth digit is the correct Luhn check digit.

    Computed over `"80840" + npi[:9]`, as CMS specifies.

    This is **not a security control** and must never be described as one: an
    attacker generates Luhn-valid NPIs as easily as any other. It catches
    transcription errors and NPIs invented without reference to the algorithm.
    The only real check is the registry — see `src/npi_registry_validator.py`,
    which is not wired into verification.
    """
    if not isinstance(npi, str) or not _NPI_RE.match(npi):
        return False
    total = 0
    for i, ch in enumerate(reversed(_NPI_LUHN_PREFIX + npi[:9])):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10 == int(npi[9])


def _validate_npi(npi: str, *, check_digit: bool = False) -> None:
    """Format-validate an NPI, optionally including its check digit.

    An empty NPI passes: a sub-delegation names no provider of its own and
    inherits the root's. `check_digit` is off by default because turning it on
    is a deployment decision — it is wired through
    `DelegationContext.require_npi_check_digit`, not applied globally.
    """
    if npi and not _NPI_RE.match(npi):
        raise ValueError(f"{ERR_INVALID_NPI}: '{npi}' must be exactly 10 digits")
    if npi and check_digit and not npi_check_digit_valid(npi):
        raise ValueError(f"{ERR_INVALID_NPI}: '{npi}' has an invalid check digit")


# ── Data model ────────────────────────────────────────────────────────────────
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
    #: Which of the provider's signing keys signed this delegation. Empty means
    #: "the provider's only key", which is the pre-rotation state.
    #:
    #: Without a key identifier there is no key rotation: a provider that
    #: rotates its root key makes every outstanding delegation fail as
    #: ERR_INVALID_SIG, and a verifier cannot tell that from a forgery. The
    #: field is inside the signed payload deliberately — an attacker who could
    #: edit it would choose which key verifies their delegation.
    kid: str = ""
    #: Format version of this delegation object, so a verifier can refuse a
    #: shape it does not understand instead of failing a signature check and
    #: reporting a forgery.
    nhid_auth_version: str = DELEGATION_FORMAT_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(',', ':'))

    @classmethod
    def from_json(cls, data: str):
        d = json.loads(data)
        d.setdefault("call_sid", "")
        d.setdefault("nonce", "")
        d.setdefault("kid", "")
        d.setdefault("nhid_auth_version", DELEGATION_FORMAT_VERSION)
        return cls(**d)


@dataclass
class AgentPassport:
    delegation: Delegation
    signature_b64: str
    agent_signature_b64: str


@dataclass
class PresentationProof:
    """Evidence that the party presenting a passport *now* holds the agent key.

    The passport's own `agent_signature_b64` covers the delegation JSON — the
    same bytes the provider signed. It is therefore a static artifact: it
    proves whoever assembled the passport held the agent private key at
    assembly time, and anyone who later captures those bytes holds a complete,
    verifiable passport. Nothing in it is bound to the moment of presentation.

    This closes that. The verifier issues a fresh nonce, the agent signs it
    alongside this delegation's id and a timestamp, and the verifier checks the
    result against the public key already named in the signed delegation. A
    captured passport replayed without the matching private key cannot produce
    one, and a proof captured from an earlier exchange names the wrong nonce.

    Same shape as the proof-of-possession layer HTTP APIs get from DPoP, minus
    the HTTP binding — there is no request to bind to on a telephone call, so
    the verifier's nonce is what supplies freshness.
    """

    delegation_id: str
    verifier_nonce: str
    issued_at: int
    signature_b64: str

    def signing_payload(self) -> bytes:
        """The bytes the agent signs. Excludes the signature itself."""
        return json.dumps(
            {
                "delegation_id": self.delegation_id,
                "verifier_nonce": self.verifier_nonce,
                "issued_at": self.issued_at,
            },
            sort_keys=True,
            separators=(',', ':'),
        ).encode()


def new_verifier_nonce() -> str:
    """A fresh, unpredictable challenge for one verification.

    Unlike `Delegation.nonce` — which is `sha256(call_sid:created_at)` over two
    fields of the delegation it travels in, and so carries no entropy the
    signed payload does not already have — this is random and chosen by the
    verifier, which is what makes a reply to it evidence of anything.
    """
    return secrets.token_urlsafe(24)


@dataclass
class VerificationResult:
    valid: bool
    reason: str
    delegation_id: Optional[str] = None
    provider_npi: Optional[str] = None
    agent_id: Optional[str] = None
    scope: Optional[List[str]] = None


# ── Identity manager ──────────────────────────────────────────────────────────
class AgentIdentityManager:
    def __init__(self):
        self.revocation_list: Dict[str, int] = {}
        self.revoked_delegations: Dict[str, int] = {}

    def generate_agent_keys(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
        priv = Ed25519PrivateKey.generate()
        return priv, priv.public_key()

    def public_key_to_b64(self, pub: Ed25519PublicKey) -> str:
        return base64.b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()

    def b64_to_public_key(self, b64: str) -> Ed25519PublicKey:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(b64))

    def create_delegation(self, provider_priv, agent_id, agent_pub, scope,
                          ttl_seconds=86400, call_sid="", provider_npi="",
                          kid=""):
        """Mint an unsigned delegation.

        `kid` names which of the signer's keys will sign it, so a verifier
        holding several keys for one provider can select the right one instead
        of guessing. Leave it empty while a provider has a single key.
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
            kid=kid,
        )

    def sign_delegation(self, provider_priv, delegation: Delegation) -> str:
        return base64.b64encode(provider_priv.sign(delegation.to_json().encode())).decode()

    def create_agent_passport(self, delegation: Delegation, provider_sig: str,
                              agent_priv) -> AgentPassport:
        agent_sig = base64.b64encode(agent_priv.sign(delegation.to_json().encode())).decode()
        return AgentPassport(delegation=delegation, signature_b64=provider_sig,
                             agent_signature_b64=agent_sig)

    def create_presentation_proof(self, agent_priv, delegation: Delegation,
                                  verifier_nonce: str) -> PresentationProof:
        """Answer a verifier's challenge with the agent key.

        Called by the agent at presentation time, not at issuance — the whole
        point is that it cannot be precomputed, because the nonce comes from
        the verifier.
        """
        if not verifier_nonce:
            raise ValueError("a presentation proof needs a verifier nonce")
        proof = PresentationProof(
            delegation_id=delegation.delegation_id,
            verifier_nonce=verifier_nonce,
            issued_at=int(time.time()),
            signature_b64="",
        )
        signature = agent_priv.sign(proof.signing_payload())
        proof.signature_b64 = base64.b64encode(signature).decode()
        return proof

    def _verify_presentation_proof(
        self, delegation: Delegation, verifier_nonce: str,
        proof: Optional[PresentationProof],
    ) -> Optional[VerificationResult]:
        """None when the proof is acceptable, else the failure to return."""
        if proof is None:
            return VerificationResult(
                False, f"{ERR_PROOF_MISSING}: verification was challenged with a "
                       f"nonce and no presentation proof was supplied",
                delegation_id=delegation.delegation_id,
            )
        if proof.verifier_nonce != verifier_nonce:
            return VerificationResult(
                False, f"{ERR_PROOF_MISMATCH}: proof answers a different challenge",
                delegation_id=delegation.delegation_id,
            )
        if proof.delegation_id != delegation.delegation_id:
            return VerificationResult(
                False, f"{ERR_PROOF_MISMATCH}: proof names a different delegation",
                delegation_id=delegation.delegation_id,
            )
        age = int(time.time()) - proof.issued_at
        if age > MAX_PROOF_AGE_SECONDS or age < -MAX_PROOF_AGE_SECONDS:
            return VerificationResult(
                False, f"{ERR_PROOF_STALE}: proof is {age}s old, limit is "
                       f"{MAX_PROOF_AGE_SECONDS}s",
                delegation_id=delegation.delegation_id,
            )
        try:
            agent_pub = self.b64_to_public_key(delegation.agent_public_key_b64)
            agent_pub.verify(
                base64.b64decode(proof.signature_b64), proof.signing_payload()
            )
        except Exception:
            return VerificationResult(
                False, f"{ERR_PROOF_MISMATCH}: proof signature does not verify "
                       f"against the delegated agent key",
                delegation_id=delegation.delegation_id,
            )
        return None

    def verify_passport(self, passport: AgentPassport, provider_pub,
                        call_sid: str = "",
                        required_scope: Optional[List[str]] = None,
                        require_npi: bool = False,
                        verifier_nonce: str = "",
                        proof: Optional[PresentationProof] = None) -> VerificationResult:
        """Verify one passport against the key that should have signed it.

        `require_npi` asks whether this delegation must name a provider. It
        defaults to False because only the **root** of a chain anchors to an
        NPI — a sub-delegation is signed by its parent agent and inherits the
        root's provider, which is why `validate_chain` reports
        `passports[0].delegation.provider_npi` and the hops carry none.

        Set it True wherever a passport stands alone and is therefore claiming
        provider authority on its own: `validate_chain` sets it for the root,
        and a verifier answering "is this passport valid?" should set it too.
        Without it a delegation naming no provider verifies as valid and
        reports `provider_npi: ""` — a passport that asserts no authority,
        presented as though it had some.

        `verifier_nonce` opts into proof of possession. Supply one and a
        matching `PresentationProof` becomes **required**; omit it and
        behaviour is exactly as before, so a caller that knows nothing about
        proofs is unaffected. See `PresentationProof` for why the passport's
        own agent signature is not sufficient on its own.
        """
        d = passport.delegation

        if d.agent_id in self.revocation_list:
            return VerificationResult(False, ERR_REVOKED)
        if d.delegation_id in self.revoked_delegations:
            return VerificationResult(False, ERR_REVOKED)
        if d.nhid_auth_version != DELEGATION_FORMAT_VERSION:
            return VerificationResult(
                False,
                f"{ERR_UNSUPPORTED_VERSION}: delegation format "
                f"'{d.nhid_auth_version}', this verifier understands "
                f"'{DELEGATION_FORMAT_VERSION}'",
                delegation_id=d.delegation_id,
            )
        if require_npi and not d.provider_npi:
            return VerificationResult(
                False, f"{ERR_INVALID_NPI}: delegation names no provider",
                delegation_id=d.delegation_id,
            )
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

        # Proof of possession last among the cryptographic checks: a proof is
        # only worth evaluating once the delegation it answers for is known to
        # be genuine, otherwise an attacker chooses both halves.
        if verifier_nonce:
            failure = self._verify_presentation_proof(d, verifier_nonce, proof)
            if failure is not None:
                return failure

        if required_scope:
            missing = [a for a in required_scope if a not in d.scope]
            if missing:
                return VerificationResult(False, f"{ERR_SCOPE_VIOLATION}: {missing}")

        return VerificationResult(True, "Valid", delegation_id=d.delegation_id,
                                  provider_npi=d.provider_npi, agent_id=d.agent_id,
                                  scope=d.scope)

    def revoke_agent(self, agent_id: str) -> None:
        self.revocation_list[agent_id] = int(time.time())

    def revoke_delegation(self, delegation_id: str) -> None:
        self.revoked_delegations[delegation_id] = int(time.time())

    def validate_chain(self, passports: List[AgentPassport],
                       provider_pub, call_sid: str = "",
                       verifier_nonce: str = "",
                       proof: Optional[PresentationProof] = None) -> VerificationResult:
        """Verify a delegation chain root-first, enforcing monotonic scope
        narrowing and — when `call_sid` is supplied — the same call binding
        `verify_passport` applies to a single passport.

        Binding is enforced **per hop**: a hop carrying a `call_sid` must match
        the live call, while a hop with an empty `call_sid` asserts no call of
        its own and rides its parent's binding. That shape is deliberate — a
        provider issues the root for a call and the vendor sub-delegates without
        restating it.

        `call_sid` was missing here entirely, which meant every hop was verified
        with the default empty value and the binding branch in `verify_passport`
        was never entered. A chain minted for one call verified on any other,
        while the single-passport path rejected exactly that.

        A `verifier_nonce` is checked against the **leaf** only. The leaf agent
        is the one presenting the chain and the only one whose key is in play;
        the intermediate hops are historical facts about who delegated what,
        and their holders are not party to this exchange.
        """
        if not passports:
            return VerificationResult(False, "Empty chain")
        if len(passports) > MAX_CHAIN_DEPTH:
            return VerificationResult(False, f"{ERR_CHAIN_TOO_LONG}: max {MAX_CHAIN_DEPTH}")

        # The root is the only hop that claims provider authority directly, so
        # it is the only one required to name an NPI.
        result = self.verify_passport(
            passports[0], provider_pub, call_sid=call_sid, require_npi=True
        )
        if not result.valid:
            return result

        current_scope = set(passports[0].delegation.scope)

        for i, passport in enumerate(passports[1:], start=1):
            prev_agent_pub = self.b64_to_public_key(
                passports[i - 1].delegation.agent_public_key_b64
            )
            result = self.verify_passport(passport, prev_agent_pub, call_sid=call_sid)
            if not result.valid:
                return result
            next_scope = set(passport.delegation.scope)
            if not next_scope.issubset(current_scope):
                escalated = sorted(next_scope - current_scope)
                return VerificationResult(
                    False, f"{ERR_CHAIN_NARROWING}: {escalated} not in parent scope"
                )
            current_scope = next_scope

        last = passports[-1].delegation

        # Possession is proved by whoever is presenting, which is the leaf.
        if verifier_nonce:
            failure = self._verify_presentation_proof(last, verifier_nonce, proof)
            if failure is not None:
                return failure
        return VerificationResult(True, "Valid chain", delegation_id=last.delegation_id,
                                  provider_npi=passports[0].delegation.provider_npi,
                                  agent_id=last.agent_id, scope=sorted(current_scope))
