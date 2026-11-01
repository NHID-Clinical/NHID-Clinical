"""
NHID-Clinical — call-scoped verification prototype (candidate VER-01)

**CANDIDATE prototype.** This module implements the proposal in
`docs/proposals/verification-and-nonverbal-disclosure.md` so its requirements
can be tested. It is not evaluated by the v1.3 policy engine, it is not wired
into the API, any telephony adapter or the site, and it is not a conformance
claim. VER-01 is not part of the canonical control set.

The scenario is the canonical one: a caller-agent telephones a payer and asks
for a patient's protected information. This module is the **payer's** side of
an out-of-band check, in two steps:

1. **Issuance**, before the call. The agent sends a call-intent request over an
   authenticated API, signed with its AgentPassport key under an RFC 9421 HTTP
   Message Signatures profile. The payer verifies the provider-signed
   delegation against keys and an enrollment registry it holds itself, never
   against the agent's own claims, and mints a short-lived, call-scoped token.
   The agent gets back an opaque `token_ref` and, for legacy IVRs, a DTMF
   handle: a lookup key for the server-side record, not a credential.

2. **Redemption**, during the call. The payer looks the token up, checks every
   binding (window, revocation, originating number, provider, purpose, proof of
   possession of the agent key), and only then consumes it atomically. A second
   redemption, sequential or concurrent, fails as a replay.

What a pass means, and does not: VER-01 says this call is the one a provider
authorized. It is **not** disclosure (IDG-01) and it is **not** authority to
receive any particular record. A token exchange alone never satisfies IDG-01.

Requirements this module answers (proposal §10), each with a test in
`tests/test_call_verification.py`:

  1. payer verifies a provider-signed delegation and its registry status;
  2. proof of possession of the agent key at redemption;
  3. the call intent carries nonce, created/expires and payer audience, signed
     under a stated RFC 9421 profile;
  4. random nonces;
  5. atomic single redemption in a shared store, binding checks first;
  6. DTMF handles stored server-side and checked for collisions;
  7. `intent_hmac` is a keyed HMAC, never a plain hash of member or claim ids;
  8. the key fingerprint is derived from the key (`key_fingerprint`);
  9. agent metadata is the existing `nhid-agent` object, with agent_id and
     call_sid;
 10. no IETF/IANA registration claim and no version bump: this is v1.3-era
     candidate code.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple
from urllib.parse import urlsplit

from src.agent_identity import (
    AgentIdentityManager,
    AgentPassport,
    MAX_PROOF_AGE_SECONDS,
    PresentationProof,
)
from src.trust_anchor import TrustAnchorResolver
from src.udap_agent_extension import EXTENSION_KEY, key_fingerprint, verify_extension

# ── Result vocabulary (the same four values every control uses) ──────────────
PASS = "pass"
EXCEPTION = "exception"
UNKNOWN = "unknown"
NOT_ASSESSABLE = "not_assessable"

#: The binding checks, in the order they are reported. The names are the keys of
#: `healthcare_governance.call_verification.binding_checks` in the trace schema.
BINDING_CHECKS = (
    "originating_number",
    "provider_npi",
    "purpose",
    "time_window",
    "proof_of_possession",
    "revocation",
    "replay",
)

#: Reason code for the first failing binding, in priority order. A token that
#: fails several bindings reports the earliest here; every failure is still
#: visible in `binding_checks`.
_REASON_PRIORITY = (
    # (binding, code when it is an exception, code when it is unknown)
    ("revocation", "DELEGATION_REVOKED", "REVOCATION_STATUS_UNKNOWN"),
    ("time_window", "TOKEN_EXPIRED", "TOKEN_WINDOW_UNKNOWN"),
    ("purpose", "SCOPE_MISMATCH", "PURPOSE_UNKNOWN"),
    ("provider_npi", "PROVIDER_MISMATCH", "PROVIDER_UNKNOWN"),
    ("originating_number", "NUMBER_MISMATCH", "NUMBER_UNAVAILABLE"),
    ("proof_of_possession", "PROOF_OF_POSSESSION_FAILED", "PROOF_OF_POSSESSION_UNKNOWN"),
    ("replay", "TOKEN_ALREADY_REDEEMED", "REPLAY_STATUS_UNKNOWN"),
)

#: Candidate high-risk-write rule (proposal §8): even in scope and verified,
#: these need out-of-band confirmation with the provider.
HIGH_RISK_WRITE_SCOPES = frozenset({
    "eft_update",
    "bank_account_update",
    "remittance_update",
    "demographic_update",
})


def requires_out_of_band(purpose: str) -> bool:
    """True when a purpose is a high-risk write (candidate rule, proposal §8)."""
    return purpose in HIGH_RISK_WRITE_SCOPES


# ── RFC 9421 profile ─────────────────────────────────────────────────────────
#
# The profile, stated so the label means something:
#   * covered components, in this order: "@method" "@target-uri" "content-digest"
#   * Content-Digest per RFC 9530, algorithm sha-256, over the exact body bytes
#   * signature parameters: created, expires, nonce, keyid, alg, tag
#       keyid = key_fingerprint() of the delegated agent key
#       alg   = "ed25519"
#       tag   = "nhid-call-intent"
#   * signature label "nhid", carried in Signature-Input and Signature
#
# The signature base and the structured-field serialization follow RFC 9421
# §2.3 and §2.5. `tests/test_call_verification.py` checks them against the
# RFC's Appendix B.2.6 Ed25519 example, not only against this module.

PROFILE_COMPONENTS = ("@method", "@target-uri", "content-digest")
PROFILE_TAG = "nhid-call-intent"
PROFILE_ALG = "ed25519"
SIGNATURE_LABEL = "nhid"
CALL_INTENT_PATH = "/nhid/call-intent"

_SF_KEY = re.compile(r"^[a-z*][a-z0-9_\-.*]*$")


def _sf_string(value: str) -> str:
    if any(ord(c) < 0x20 or ord(c) > 0x7E for c in value):
        raise ValueError("structured-field strings must be printable ASCII")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def serialize_signature_params(
    components: Sequence[str], params: Sequence[Tuple[str, Any]]
) -> str:
    """Serialize `@signature-params` as an RFC 8941 inner list with parameters.

    `params` keeps its order, because the serialization is what gets signed and
    the order is part of it.
    """
    inner = "(" + " ".join(_sf_string(c) for c in components) + ")"
    out = [inner]
    for key, value in params:
        if not _SF_KEY.match(key):
            raise ValueError(f"invalid parameter key {key!r}")
        if isinstance(value, bool):
            raise ValueError("boolean parameters are not used by this profile")
        if isinstance(value, int):
            out.append(f";{key}={value}")
        else:
            out.append(f";{key}={_sf_string(str(value))}")
    return "".join(out)


def signature_base(component_values: Sequence[Tuple[str, str]], params_value: str) -> bytes:
    """RFC 9421 §2.5 signature base: one line per covered component, then
    `"@signature-params"`. Lines end in LF; the last line has none."""
    lines = []
    for name, value in component_values:
        if "\n" in value or "\r" in value:
            raise ValueError("component values cannot contain line breaks")
        lines.append(f'"{name}": {value}')
    lines.append(f'"@signature-params": {params_value}')
    return "\n".join(lines).encode("ascii")


def content_digest(body: bytes) -> str:
    """RFC 9530 Content-Digest with sha-256."""
    return "sha-256=:" + base64.b64encode(hashlib.sha256(body).digest()).decode() + ":"


def _parse_signature_input(header: str, label: str) -> Tuple[List[str], List[Tuple[str, Any]], str]:
    """Parse one `label=(...);k=v` member of Signature-Input.

    Deliberately narrow: it accepts exactly what this profile emits (an inner
    list of strings, integer and string parameters) and rejects anything else
    rather than guessing. Returns (components, params, raw serialized value).
    """
    prefix = f"{label}="
    members = [m.strip() for m in _split_top_level(header)]
    raw = next((m[len(prefix):] for m in members if m.startswith(prefix)), None)
    if raw is None:
        raise ValueError(f"no {label!r} member in Signature-Input")
    if not raw.startswith("("):
        raise ValueError("signature input must be an inner list")
    close = raw.index(")")
    inner, rest = raw[1:close], raw[close + 1:]
    components = re.findall(r'"((?:[^"\\]|\\.)*)"', inner)
    if " ".join(f'"{c}"' for c in components) != inner.strip():
        raise ValueError("covered components must be quoted strings")
    params: List[Tuple[str, Any]] = []
    for part in [p for p in rest.split(";") if p]:
        key, _, value = part.partition("=")
        if not _SF_KEY.match(key):
            raise ValueError(f"invalid parameter key {key!r}")
        if re.fullmatch(r"-?\d{1,15}", value):
            params.append((key, int(value)))
        elif re.fullmatch(r'"(?:[^"\\]|\\.)*"', value):
            params.append((key, re.sub(r"\\(.)", r"\1", value[1:-1])))
        else:
            raise ValueError(f"unsupported parameter value for {key!r}")
    return components, params, raw


def _split_top_level(header: str) -> List[str]:
    """Split a dictionary header on commas outside quotes and parentheses."""
    out, depth, quoted, start, i = [], 0, False, 0, 0
    while i < len(header):
        ch = header[i]
        if quoted:
            if ch == "\\":
                i += 1
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append(header[start:i])
            start = i + 1
        i += 1
    out.append(header[start:])
    return out


@dataclass
class SignedRequest:
    """An HTTP request as far as this profile needs it."""

    method: str
    target_uri: str
    headers: Dict[str, str]
    body: bytes

    def json(self) -> Dict[str, Any]:
        return json.loads(self.body)


def new_intent_nonce() -> str:
    """Random, from the OS CSPRNG. Never derived from time, counters or ids."""
    return secrets.token_urlsafe(24)


def sign_call_intent(
    agent_priv,
    body: Dict[str, Any],
    target_uri: str,
    keyid: str,
    created: int,
    expires: int,
    nonce: Optional[str] = None,
) -> SignedRequest:
    """Build and sign a call-intent request under the profile above.

    Called by the agent. `keyid` must be `key_fingerprint()` of the agent key
    named in the delegation; the payer refuses anything else.
    """
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    digest = content_digest(payload)
    params = [
        ("created", int(created)),
        ("expires", int(expires)),
        ("nonce", nonce or new_intent_nonce()),
        ("keyid", keyid),
        ("alg", PROFILE_ALG),
        ("tag", PROFILE_TAG),
    ]
    params_value = serialize_signature_params(PROFILE_COMPONENTS, params)
    base = signature_base(
        [("@method", "POST"), ("@target-uri", target_uri), ("content-digest", digest)],
        params_value,
    )
    signature = base64.b64encode(agent_priv.sign(base)).decode()
    return SignedRequest(
        method="POST",
        target_uri=target_uri,
        headers={
            "Content-Type": "application/json",
            "Content-Digest": digest,
            "Signature-Input": f"{SIGNATURE_LABEL}={params_value}",
            "Signature": f"{SIGNATURE_LABEL}=:{signature}:",
        },
        body=payload,
    )


@dataclass
class IntentSignature:
    valid: bool
    reason: str
    params: Dict[str, Any] = field(default_factory=dict)


def verify_call_intent_signature(request: SignedRequest, agent_pub) -> IntentSignature:
    """Check a call-intent request against the profile and the agent key.

    The base is rebuilt from the request as received, and Content-Digest is
    recomputed from the body, so a body edited after signing fails here.
    """
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        components, params, raw = _parse_signature_input(
            headers.get("signature-input", ""), SIGNATURE_LABEL
        )
    except ValueError as exc:
        return IntentSignature(False, f"SIGNATURE_MALFORMED: {exc}")
    if tuple(components) != PROFILE_COMPONENTS:
        return IntentSignature(False, f"PROFILE_MISMATCH: covered components {components}")
    p = dict(params)
    for required in ("created", "expires", "nonce", "keyid", "alg", "tag"):
        if required not in p:
            return IntentSignature(False, f"PROFILE_MISMATCH: missing {required}")
    if p["alg"] != PROFILE_ALG or p["tag"] != PROFILE_TAG:
        return IntentSignature(False, "PROFILE_MISMATCH: alg or tag")
    if request.method.upper() != "POST":
        return IntentSignature(False, "PROFILE_MISMATCH: method")
    digest = content_digest(request.body)
    if not hmac.compare_digest(headers.get("content-digest", ""), digest):
        return IntentSignature(False, "DIGEST_MISMATCH")
    sig_header = headers.get("signature", "")
    match = re.search(rf"(?:^|,)\s*{SIGNATURE_LABEL}=:([A-Za-z0-9+/=]+):", sig_header)
    if not match:
        return IntentSignature(False, "SIGNATURE_MALFORMED: no signature value")
    base = signature_base(
        [("@method", "POST"), ("@target-uri", request.target_uri), ("content-digest", digest)],
        raw,
    )
    try:
        agent_pub.verify(base64.b64decode(match.group(1)), base)
    except Exception:
        return IntentSignature(False, "SIGNATURE_INVALID")
    return IntentSignature(True, "Valid", p)


# ── Provider proofing: payer-portal enrollment ───────────────────────────────

ENROLLMENT_ACTIVE = "active"
ENROLLMENT_SUSPENDED = "suspended"
ENROLLMENT_REVOKED = "revoked"


@dataclass(frozen=True)
class Enrollment:
    """One provider's authorization of one agent key, recorded by this payer.

    Proves the provider-agent relationship **for this payer only** (proposal
    §7). Another payer learns nothing from it.
    """

    provider_npi: str
    agent_key_fingerprint: str
    scopes: frozenset
    status: str = ENROLLMENT_ACTIVE


class EnrollmentRegistry(Protocol):
    def lookup(self, provider_npi: str, agent_key_fingerprint: str) -> Optional[Enrollment]: ...


class PortalEnrollmentRegistry:
    """In-memory payer-portal enrollment. The payer populates it from its own
    provider portal; nothing the agent says can add to it."""

    def __init__(self) -> None:
        self._rows: Dict[Tuple[str, str], Enrollment] = {}

    def enroll(self, provider_npi: str, agent_key_fingerprint: str,
               scopes: Sequence[str], status: str = ENROLLMENT_ACTIVE) -> None:
        self._rows[(provider_npi, agent_key_fingerprint)] = Enrollment(
            provider_npi, agent_key_fingerprint, frozenset(scopes), status
        )

    def set_status(self, provider_npi: str, agent_key_fingerprint: str, status: str) -> None:
        row = self._rows[(provider_npi, agent_key_fingerprint)]
        self._rows[(provider_npi, agent_key_fingerprint)] = Enrollment(
            row.provider_npi, row.agent_key_fingerprint, row.scopes, status
        )

    def lookup(self, provider_npi: str, agent_key_fingerprint: str) -> Optional[Enrollment]:
        return self._rows.get((provider_npi, agent_key_fingerprint))


# ── Token store: shared, atomic single redemption ────────────────────────────

class DuplicateHandle(Exception):
    """A DTMF handle or token ref collided with a live record."""


@dataclass
class TokenRecord:
    """The server-side token. Holds no member or claim identifier in clear:
    only the keyed `intent_hmac`."""

    token_ref: str
    dtmf_handle: str
    delegation_id: str
    agent_id: str
    agent_key_b64: str
    agent_key_fingerprint: str
    provider_npi: str
    provider_kid: str
    originating_number: str
    purpose: str
    payer_audience: str
    issued_at: int
    expires_at: int
    intent_hmac: str
    consumed_at: Optional[int] = None
    consumed_call_sid: Optional[str] = None


class TokenStore(Protocol):
    def insert(self, record: TokenRecord) -> None: ...
    def get(self, token_ref_or_handle: str) -> Optional[TokenRecord]: ...
    def consume(self, token_ref: str, at: int, call_sid: str) -> bool: ...
    def remember_nonce(self, nonce: str, expires_at: int) -> bool: ...
    def find_by_call(self, call_sid: str) -> Optional[TokenRecord]: ...


class InMemoryTokenStore:
    """Single-process store. `consume` is a compare-and-set under a lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_ref: Dict[str, TokenRecord] = {}
        self._by_handle: Dict[str, str] = {}
        self._nonces: Dict[str, int] = {}

    def insert(self, record: TokenRecord) -> None:
        with self._lock:
            if record.token_ref in self._by_ref or record.dtmf_handle in self._by_handle:
                raise DuplicateHandle(record.dtmf_handle)
            self._by_ref[record.token_ref] = record
            self._by_handle[record.dtmf_handle] = record.token_ref

    def get(self, token_ref_or_handle: str) -> Optional[TokenRecord]:
        with self._lock:
            ref = self._by_handle.get(token_ref_or_handle, token_ref_or_handle)
            rec = self._by_ref.get(ref)
            return None if rec is None else TokenRecord(**asdict(rec))

    def consume(self, token_ref: str, at: int, call_sid: str) -> bool:
        with self._lock:
            rec = self._by_ref.get(token_ref)
            if rec is None or rec.consumed_at is not None:
                return False
            rec.consumed_at, rec.consumed_call_sid = at, call_sid
            return True

    def remember_nonce(self, nonce: str, expires_at: int) -> bool:
        with self._lock:
            if nonce in self._nonces:
                return False
            self._nonces[nonce] = expires_at
            return True

    def find_by_call(self, call_sid: str) -> Optional[TokenRecord]:
        with self._lock:
            for rec in self._by_ref.values():
                if call_sid and rec.consumed_call_sid == call_sid:
                    return TokenRecord(**asdict(rec))
            return None


class SqliteTokenStore:
    """A store several connections or processes can share.

    Single redemption is one conditional UPDATE, `... WHERE consumed_at IS
    NULL`, and its row count says who won. That is atomic in the database, so
    it holds across threads, connections and processes, not only inside one
    Python object. Handle uniqueness is a UNIQUE index, so a collision is
    refused by the database rather than by a read-then-write race.
    """

    _COLUMNS = [f.name for f in TokenRecord.__dataclass_fields__.values()]

    def __init__(self, path: str) -> None:
        self.path = path
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS tokens ("
                "token_ref TEXT PRIMARY KEY, dtmf_handle TEXT NOT NULL UNIQUE, "
                "delegation_id TEXT, agent_id TEXT, agent_key_b64 TEXT, "
                "agent_key_fingerprint TEXT, provider_npi TEXT, provider_kid TEXT, "
                "originating_number TEXT, purpose TEXT, payer_audience TEXT, "
                "issued_at INTEGER, expires_at INTEGER, intent_hmac TEXT, "
                "consumed_at INTEGER, consumed_call_sid TEXT)"
            )
            c.execute("CREATE TABLE IF NOT EXISTS nonces (nonce TEXT PRIMARY KEY, expires_at INTEGER)")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def insert(self, record: TokenRecord) -> None:
        cols = ",".join(self._COLUMNS)
        marks = ",".join("?" for _ in self._COLUMNS)
        try:
            with self._conn() as c:
                c.execute(f"INSERT INTO tokens ({cols}) VALUES ({marks})",
                          [getattr(record, k) for k in self._COLUMNS])
        except sqlite3.IntegrityError as exc:
            raise DuplicateHandle(record.dtmf_handle) from exc

    def _row(self, row) -> Optional[TokenRecord]:
        return None if row is None else TokenRecord(**dict(zip(self._COLUMNS, row)))

    def get(self, token_ref_or_handle: str) -> Optional[TokenRecord]:
        cols = ",".join(self._COLUMNS)
        with self._conn() as c:
            row = c.execute(
                f"SELECT {cols} FROM tokens WHERE token_ref=? OR dtmf_handle=?",
                (token_ref_or_handle, token_ref_or_handle),
            ).fetchone()
        return self._row(row)

    def consume(self, token_ref: str, at: int, call_sid: str) -> bool:
        with self._conn() as c:
            cur = c.execute(
                "UPDATE tokens SET consumed_at=?, consumed_call_sid=? "
                "WHERE token_ref=? AND consumed_at IS NULL",
                (at, call_sid, token_ref),
            )
            return cur.rowcount == 1

    def remember_nonce(self, nonce: str, expires_at: int) -> bool:
        try:
            with self._conn() as c:
                c.execute("INSERT INTO nonces (nonce, expires_at) VALUES (?, ?)", (nonce, expires_at))
            return True
        except sqlite3.IntegrityError:
            return False

    def find_by_call(self, call_sid: str) -> Optional[TokenRecord]:
        if not call_sid:
            return None
        cols = ",".join(self._COLUMNS)
        with self._conn() as c:
            row = c.execute(f"SELECT {cols} FROM tokens WHERE consumed_call_sid=?",
                            (call_sid,)).fetchone()
        return self._row(row)


# ── Results ──────────────────────────────────────────────────────────────────

@dataclass
class IssueResult:
    ok: bool
    reason: str
    token_ref: Optional[str] = None
    dtmf_handle: Optional[str] = None
    expires_at: Optional[int] = None


@dataclass
class CallContext:
    """What the payer observes about the live call at redemption."""

    call_sid: str
    originating_number: Optional[str]   # None when withheld or unavailable
    purpose: str
    asserted_provider_npi: Optional[str] = None


@dataclass
class CallVerificationResult:
    result: str
    reason_code: Optional[str]
    delegation_id: Optional[str]
    token_ref: Optional[str]
    redeemed_at: Optional[int]
    binding_checks: Dict[str, str]

    def restriction(self) -> Optional[str]:
        """The ladder outcome VER-01 asks for, or None when it asks for none.

        Not a pass/fail of the call: the composite is still the most
        restrictive decision across every control.
        """
        return None if self.result == PASS else "DENY_DATA"

    def to_trace_field(self) -> Dict[str, Any]:
        """`healthcare_governance.call_verification`, as the trace schema defines it."""
        redeemed = None
        if self.redeemed_at is not None:
            redeemed = datetime.fromtimestamp(self.redeemed_at, timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
        return {
            "result": self.result,
            "reason_code": self.reason_code,
            "delegation_id": self.delegation_id,
            "token_ref": self.token_ref,
            "redeemed_at": redeemed,
            "binding_checks": dict(self.binding_checks),
        }


# ── The payer-side service ───────────────────────────────────────────────────

class CallVerificationService:
    """Issues and redeems call-scoped tokens for one payer."""

    def __init__(
        self,
        payer_audience: str,
        manager: AgentIdentityManager,
        trust_anchors: TrustAnchorResolver,
        registry: EnrollmentRegistry,
        store: TokenStore,
        intent_hmac_key: bytes,
        *,
        clock: Callable[[], float] = time.time,
        max_intent_window: int = 300,
        clock_skew: int = 30,
        token_ttl: int = 600,
        dtmf_digits: int = 8,
        max_handle_attempts: int = 5,
        handle_source: Optional[Callable[[int], str]] = None,
        base_uri: str = "https://payer.example",
    ) -> None:
        if len(intent_hmac_key) < 32:
            raise ValueError("intent_hmac_key must be at least 32 bytes")
        self.payer_audience = payer_audience
        self.manager = manager
        self.trust_anchors = trust_anchors
        self.registry = registry
        self.store = store
        self._hmac_key = intent_hmac_key
        self._clock = clock
        self.max_intent_window = max_intent_window
        self.clock_skew = clock_skew
        self.token_ttl = token_ttl
        self.dtmf_digits = dtmf_digits
        self.max_handle_attempts = max_handle_attempts
        self._handle_source = handle_source or (
            lambda n: "".join(secrets.choice("0123456789") for _ in range(n)))
        self.target_uri = base_uri.rstrip("/") + CALL_INTENT_PATH

    def now(self) -> int:
        return int(self._clock())

    # -- keyed intent hash (requirement 7) --
    def intent_hmac(self, member_ref: str, claim_ref: str = "") -> str:
        """HMAC-SHA256 under the payer's key. Without the key, enumerating
        member or claim ids does not reverse it."""
        msg = json.dumps({"aud": self.payer_audience, "claim": claim_ref, "member": member_ref},
                         sort_keys=True, separators=(",", ":")).encode()
        return "hmac-sha256:" + hmac.new(self._hmac_key, msg, hashlib.sha256).hexdigest()

    def matches_intent(self, record: TokenRecord, member_ref: str, claim_ref: str = "") -> bool:
        return hmac.compare_digest(record.intent_hmac, self.intent_hmac(member_ref, claim_ref))

    # -- issuance --
    def issue(self, request: SignedRequest, passports: Sequence[AgentPassport]) -> IssueResult:
        """Verify a signed call intent and mint a token, or refuse.

        Order: the delegation and the payer's own registry first, so nothing
        below runs on an unverified key; then the request signature with that
        key; then audience, window and nonce; then purpose against the
        verified scope.
        """
        if not passports:
            return IssueResult(False, "DELEGATION_MISSING")
        chain = list(passports)
        root, leaf = chain[0].delegation, chain[-1].delegation

        # 1. Provider-signed delegation, key resolved by the payer (req. 1).
        provider_pub = self.trust_anchors.resolve(root.provider_npi, root.kid)
        if provider_pub is None:
            return IssueResult(False, "PROVIDER_NOT_TRUSTED")
        verified = self.manager.validate_chain(chain, provider_pub)
        if not verified.valid:
            return IssueResult(False, f"DELEGATION_INVALID: {verified.reason}")
        fingerprint = key_fingerprint(leaf.agent_public_key_b64)
        enrollment = self.registry.lookup(root.provider_npi, fingerprint)
        if enrollment is None:
            return IssueResult(False, "NOT_ENROLLED")
        if enrollment.status != ENROLLMENT_ACTIVE:
            return IssueResult(False, f"ENROLLMENT_{enrollment.status.upper()}")

        # 2. Signature with the key the delegation names (req. 3, 8).
        agent_pub = self.manager.b64_to_public_key(leaf.agent_public_key_b64)
        if request.target_uri != self.target_uri:
            return IssueResult(False, "WRONG_TARGET")
        sig = verify_call_intent_signature(request, agent_pub)
        if not sig.valid:
            return IssueResult(False, sig.reason)
        if sig.params["keyid"] != fingerprint:
            return IssueResult(False, "KEYID_MISMATCH")

        try:
            body = request.json()
        except ValueError:
            return IssueResult(False, "BODY_MALFORMED")

        # The agent's self-description must agree with the signed delegation
        # (req. 9); it is never read on its own.
        ext = verify_extension(body.get(EXTENSION_KEY), chain, provider_pub, self.manager)
        if not ext.valid:
            return IssueResult(False, f"EXTENSION_INVALID: {ext.reason}")
        if body.get("delegation_id") != leaf.delegation_id:
            return IssueResult(False, "DELEGATION_ID_MISMATCH")

        # 3. Audience, window, nonce (req. 3, 4).
        if body.get("payer_audience") != self.payer_audience:
            return IssueResult(False, "AUDIENCE_MISMATCH")
        now = self.now()
        created, expires = sig.params["created"], sig.params["expires"]
        if created > now + self.clock_skew:
            return IssueResult(False, "INTENT_NOT_YET_VALID")
        if expires <= now:
            return IssueResult(False, "INTENT_EXPIRED")
        if expires - created > self.max_intent_window:
            return IssueResult(False, "INTENT_WINDOW_TOO_LONG")
        if not self.store.remember_nonce(sig.params["nonce"], expires):
            return IssueResult(False, "INTENT_NONCE_REPLAYED")

        # 4. Purpose inside what was verified and enrolled.
        purpose = body.get("purpose", "")
        if purpose not in (verified.scope or []) or purpose not in enrollment.scopes:
            return IssueResult(False, "SCOPE_MISMATCH")
        number = body.get("originating_number") or ""
        if not re.fullmatch(r"\+[1-9]\d{6,14}", number):
            return IssueResult(False, "ORIGINATING_NUMBER_INVALID")

        # Mint. The window never outlives the delegation.
        expires_at = min(now + self.token_ttl, leaf.expires_at)
        for _ in range(self.max_handle_attempts):
            record = TokenRecord(
                token_ref="tok_" + secrets.token_urlsafe(18),
                dtmf_handle=self._handle_source(self.dtmf_digits),
                delegation_id=leaf.delegation_id,
                agent_id=leaf.agent_id,
                agent_key_b64=leaf.agent_public_key_b64,
                agent_key_fingerprint=fingerprint,
                provider_npi=root.provider_npi,
                provider_kid=root.kid,
                originating_number=number,
                purpose=purpose,
                payer_audience=self.payer_audience,
                issued_at=now,
                expires_at=expires_at,
                intent_hmac=self.intent_hmac(body.get("member_ref", ""), body.get("claim_ref", "")),
            )
            try:
                self.store.insert(record)
            except DuplicateHandle:
                continue
            return IssueResult(True, "Issued", record.token_ref, record.dtmf_handle, expires_at)
        return IssueResult(False, "HANDLE_SPACE_EXHAUSTED")

    # -- redemption --
    def new_challenge(self) -> str:
        """Verifier nonce for the redemption proof of possession."""
        return secrets.token_urlsafe(24)

    def redeem(
        self,
        token_ref_or_handle: str,
        call: CallContext,
        verifier_nonce: str,
        proof: Optional[PresentationProof],
    ) -> CallVerificationResult:
        """Check every binding, then consume once (req. 2, 5).

        A failed binding never consumes the token, so a mistyped number or an
        out-of-scope question does not burn a legitimate caller's token.
        """
        now = self.now()
        record = self.store.get(token_ref_or_handle)
        if record is None:
            return CallVerificationResult(
                EXCEPTION, "TOKEN_NOT_FOUND", None, None, now,
                {k: NOT_ASSESSABLE for k in BINDING_CHECKS})

        checks: Dict[str, str] = {}

        # Number: withheld is unknown, never pass.
        if not call.originating_number:
            checks["originating_number"] = UNKNOWN
        else:
            checks["originating_number"] = (
                PASS if call.originating_number == record.originating_number else EXCEPTION)

        # Provider: still a trust anchor here, and any NPI the caller states agrees.
        npi_ok = self.trust_anchors.resolve(record.provider_npi, record.provider_kid) is not None
        if call.asserted_provider_npi and call.asserted_provider_npi != record.provider_npi:
            npi_ok = False
        checks["provider_npi"] = PASS if npi_ok else EXCEPTION

        checks["purpose"] = PASS if call.purpose == record.purpose else EXCEPTION
        checks["time_window"] = PASS if record.issued_at <= now < record.expires_at else EXCEPTION

        # Proof of possession against the key the token is bound to.
        checks["proof_of_possession"] = self._check_possession(record, verifier_nonce, proof)

        # Revocation: the delegation, the agent, and the payer's enrollment row.
        enrollment = self.registry.lookup(record.provider_npi, record.agent_key_fingerprint)
        revoked = (
            record.delegation_id in self.manager.revoked_delegations
            or record.agent_id in self.manager.revocation_list
            or enrollment is None
            or enrollment.status != ENROLLMENT_ACTIVE
        )
        checks["revocation"] = EXCEPTION if revoked else PASS

        checks["replay"] = PASS if record.consumed_at is None else EXCEPTION

        ordered = {k: checks[k] for k in BINDING_CHECKS}
        if all(v == PASS for v in ordered.values()):
            # Only now, with every binding checked, is the token consumed.
            if not self.store.consume(record.token_ref, now, call.call_sid):
                ordered["replay"] = EXCEPTION
        return self._result(record, ordered, now)

    def result_for_call(self, call_sid: str) -> Optional[CallVerificationResult]:
        """A transfer inside the payer keeps the call's result; it does not redeem again."""
        record = self.store.find_by_call(call_sid)
        if record is None:
            return None
        return CallVerificationResult(
            PASS, None, record.delegation_id, record.token_ref, record.consumed_at,
            {k: PASS for k in BINDING_CHECKS})

    def _check_possession(self, record: TokenRecord, verifier_nonce: str,
                          proof: Optional[PresentationProof]) -> str:
        if proof is None or not verifier_nonce:
            return EXCEPTION
        if proof.verifier_nonce != verifier_nonce or proof.delegation_id != record.delegation_id:
            return EXCEPTION
        if abs(self.now() - proof.issued_at) > MAX_PROOF_AGE_SECONDS:
            return EXCEPTION
        try:
            self.manager.b64_to_public_key(record.agent_key_b64).verify(
                base64.b64decode(proof.signature_b64), proof.signing_payload())
        except Exception:
            return EXCEPTION
        return PASS

    @staticmethod
    def _result(record: TokenRecord, checks: Dict[str, str], now: int) -> CallVerificationResult:
        if any(v == EXCEPTION for v in checks.values()):
            result = EXCEPTION
        elif any(v == UNKNOWN for v in checks.values()):
            result = UNKNOWN
        else:
            result = PASS
        reason = None
        if result != PASS:
            for name, on_exception, on_unknown in _REASON_PRIORITY:
                if checks[name] == EXCEPTION:
                    reason = on_exception
                    break
            if reason is None:
                for name, _on_exception, on_unknown in _REASON_PRIORITY:
                    if checks[name] == UNKNOWN:
                        reason = on_unknown
                        break
        return CallVerificationResult(result, reason, record.delegation_id, record.token_ref,
                                      now, checks)
