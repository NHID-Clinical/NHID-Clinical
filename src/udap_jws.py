"""
NHID-Clinical — carrying the `nhid-agent` extension in a signed JWS

Why this exists
---------------
`src/udap_agent_extension.py` builds and verifies the `nhid-agent`
authorization extension object, but it builds it as a Python dict. A dict is
not transportable. UDAP's `extensions` claim lives inside an authentication
JWT, so until the object can be *signed into a token* the extension is a
design with no delivery mechanism — the gap this module closes.

What it does
------------
Encodes `hl7-b2b` and `nhid-agent` together into the `extensions` claim of a
signed JWS, and decodes one back. Nothing more: the authorization decision
still comes from `verify_extension`, which checks every field of `nhid-agent`
against the signed `AgentPassport`.

The ordering matters and is the same discipline as the extension module. A
valid JWS signature says the token was assembled by the holder of the signing
key. It says **nothing** about whether the delegation inside is genuine, and a
caller that treats a decoded token as authorization has learned nothing it did
not already assume. `decode_extensions` therefore returns data, never a
verdict, and the docstrings below say so in every place a reader might hope
otherwise.

What this is NOT
----------------
1. **Not a UDAP or HL7 conformance claim, and not evidence of one.** The UDAP
   Security IG specifies how an authentication JWT is signed and how the
   signer's certificate is conveyed — typically a certificate chain in an
   `x5c` header for a trust community that issues X.509 certificates. **This
   module has not been checked against that specification.** I have not read
   the IG, so this code must not be read as implementing its requirements:
   `alg` is a parameter here precisely because the correct value is a question
   for the IG and the trust community, not something to hard-code from
   memory. Before any conformance claim, confirm against the published IG
   which algorithms are permitted, whether `x5c` is required, and what else
   the authentication JWT must carry (`iss`, `sub`, `aud`, `exp`, `jti` and
   their required values). Treat the absence of those checks here as a known
   gap, not as a statement that they do not apply.

2. **Not a trust establishment mechanism.** `decode_extensions` takes the
   public key as an argument, which means the caller already decided whose key
   it is. That is the same boundary `src/trust_anchor.py` draws, and the same
   limitation: there is no discovery here.

3. **Not a replacement for the passport.** The extension object is a carrier.
   Signing the carrier does not make its contents true — the passport
   signature does, and `verify_extension` is what checks the two agree.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from src.udap_agent_extension import EXTENSION_KEY

#: Signature algorithms this module will encode or accept. Deliberately a
#: short allowlist rather than "whatever PyJWT supports": `none` must never be
#: reachable, and a verifier that accepts any algorithm the token names lets
#: the token choose its own verification.
SUPPORTED_ALGORITHMS = ("EdDSA", "RS256")

HL7_B2B_KEY = "hl7-b2b"

ERR_JWS_MALFORMED = "ERR_JWS_MALFORMED"
ERR_JWS_UNSUPPORTED_ALG = "ERR_JWS_UNSUPPORTED_ALG"


class JwsError(ValueError):
    """Raised when a token cannot be built or cannot be read as one."""


def _check_alg(alg: str) -> None:
    if alg not in SUPPORTED_ALGORITHMS:
        raise JwsError(
            f"{ERR_JWS_UNSUPPORTED_ALG}: {alg!r}; this module encodes and "
            f"accepts only {list(SUPPORTED_ALGORITHMS)}"
        )


def encode_extensions(
    hl7_b2b: Dict[str, Any],
    nhid_agent: Dict[str, Any],
    signing_key: Any,
    *,
    alg: str = "EdDSA",
    kid: str = "",
    claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Sign `hl7-b2b` and `nhid-agent` into one token's `extensions` claim.

    Args:
        hl7_b2b: the `hl7-b2b` object. Passed through unexamined — it is the
            caller's to populate, and `check_purpose_of_use` is what judges
            its `purpose_of_use` against a verified delegation.
        nhid_agent: the object from `udap_agent_extension.build_extension`.
            Build it from the passport; do not hand-assemble one, because
            `verify_extension`'s comparison is total and a field this module
            did not produce is a mismatch.
        signing_key: an Ed25519 or RSA private key, matching `alg`.
        alg: `EdDSA` or `RS256`. See the module docstring — which algorithm a
            trust community requires is a question for the UDAP IG, which this
            module has not been checked against.
        kid: key identifier for the header, so a verifier holding several of
            this signer's keys can select one. Omitted from the header when
            empty rather than sent as `""`, which would name a key called
            "empty string".
        claims: any additional top-level claims. The UDAP authentication JWT
            requires several (`iss`, `sub`, `aud`, `exp`, `jti` among them);
            this module does not add, default or validate them, so a caller
            targeting real UDAP must supply them here and confirm the set
            against the IG.

    Returns:
        The compact-serialized JWS.
    """
    _check_alg(alg)
    if not isinstance(hl7_b2b, dict) or not isinstance(nhid_agent, dict):
        raise JwsError(f"{ERR_JWS_MALFORMED}: both extension objects must be "
                       f"JSON objects")

    import jwt

    payload: Dict[str, Any] = dict(claims or {})
    if "extensions" in payload:
        raise JwsError(
            f"{ERR_JWS_MALFORMED}: `extensions` is built from the two objects "
            f"passed in and must not also be supplied in `claims`"
        )
    payload["extensions"] = {HL7_B2B_KEY: hl7_b2b, EXTENSION_KEY: nhid_agent}

    headers = {"kid": kid} if kid else None
    return jwt.encode(payload, signing_key, algorithm=alg, headers=headers)


def decode_extensions(
    token: str,
    public_key: Any,
    *,
    alg: str = "EdDSA",
    audience: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Verify the token's signature and return what it carries.

    Returns `(hl7_b2b, nhid_agent, claims)`, where `claims` is the rest of the
    payload with `extensions` removed.

    **A successful return is not an authorization decision and not evidence
    the delegation is genuine.** It means the token was signed by the key
    supplied — a key the caller chose, so trust in the signer was established
    before this call or not at all. The `nhid-agent` object inside is still
    unverified data at this point. Pass it to
    `udap_agent_extension.verify_extension` with the passport and the provider
    key; that is what verifies the passport first and then requires every
    field to agree with it.

    `algorithms` is pinned to the single `alg` the caller expects rather than
    read from the token's own header, so a token cannot nominate a weaker
    algorithm — or `none` — and have it honoured.
    """
    _check_alg(alg)

    import jwt

    options = {"verify_aud": audience is not None}
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[alg],
            audience=audience,
            options=options,
        )
    except Exception as exc:  # noqa: BLE001 — PyJWT raises a family of these
        raise JwsError(f"{ERR_JWS_MALFORMED}: {exc}") from exc

    if not isinstance(payload, dict):
        raise JwsError(f"{ERR_JWS_MALFORMED}: payload is not a JSON object")

    extensions = payload.get("extensions")
    if not isinstance(extensions, dict):
        raise JwsError(f"{ERR_JWS_MALFORMED}: no `extensions` object in the payload")

    hl7_b2b = extensions.get(HL7_B2B_KEY)
    nhid_agent = extensions.get(EXTENSION_KEY)
    if not isinstance(hl7_b2b, dict):
        raise JwsError(f"{ERR_JWS_MALFORMED}: `extensions` carries no "
                       f"{HL7_B2B_KEY!r} object")
    if not isinstance(nhid_agent, dict):
        raise JwsError(f"{ERR_JWS_MALFORMED}: `extensions` carries no "
                       f"{EXTENSION_KEY!r} object")

    claims = {k: v for k, v in payload.items() if k != "extensions"}
    return hl7_b2b, nhid_agent, claims


def token_kid(token: str) -> str:
    """The `kid` the token's header names, or "" if it names none.

    Read from an **unverified** header, which is the only way to learn which
    key to verify with. Use it to select a candidate key from keys you already
    trust; never to decide whether to trust one.
    """
    import jwt

    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:  # noqa: BLE001
        raise JwsError(f"{ERR_JWS_MALFORMED}: {exc}") from exc
    kid = header.get("kid", "")
    return kid if isinstance(kid, str) else ""
