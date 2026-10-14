"""
NHID-Clinical — the `nhid-agent` authorization extension object

The problem this exists for
---------------------------
HL7's UDAP Security IG (v2.0.0, STU 2) defines the `hl7-b2b` authorization
extension object, which a B2B client app using the `client_credentials` flow
puts in the `extensions` claim of its authentication JWT. It is how a token
request says who is asking for data and why. Read three of its rows together:

    subject_name   conditional   "...the human or NON-HUMAN requestor;
                                  required if known"
    subject_id     conditional   "required if known for HUMAN requestors...
                                  Omit for non-human requestors..."
    subject_role   conditional   "required if known for HUMAN requestors
                                  when subject_name is present"

So UDAP already contemplates a non-human requestor — an AI agent can be
*named* — but gives it no identifier, no role, and no evidence of whose
authority it is acting under. An AI voice agent calling a payer's Prior
Authorization API appears in the token request as a free-text name and
nothing else.

That gap closes on a deadline. CMS-0057-F requires impacted payers to stand
up a Prior Authorization API by 1 January 2027. Agent traffic will arrive at
those endpoints whether or not the token request can describe the agent.

What this module does
---------------------
UDAP's own text provides the extension point, in the same section:

    "Other implementation guides MAY define additional Authorization
     Extension Objects to use together with this object for B2B client
     credentials workflows."

`nhid-agent` is one proposal for that slot: a sibling object that travels
*alongside* `hl7-b2b`, carrying the agent's identity and the delegation it
acts under, with the provider NPI in the naming system UDAP itself prefers
(`urn:oid:2.16.840.1.113883.4.6#<npi>`).

What this module is NOT
-----------------------
1. It is **not** a UDAP or HL7 conformance claim. No part of this has been
   balloted, reviewed or accepted by HL7, UDAP.org, any trust community or
   any payer. It is a proposal that uses a documented extension point.

2. It is **not** an API-layer authorization control, and must never be
   described as one (see docs/claim-boundaries.md). The object is a
   *carrier*: it transports a claim about a delegation into a token request
   so the receiving side has something to check. The authorization decision
   still comes from verifying the signed `AgentPassport`.

3. It is **not** trusted on its own. This is the same caveat as the private
   JWT claim namespace in §2.4 of
   docs/nhid-auth-pki-and-oauth2-integration.md, and it is the reason
   `verify_extension` below verifies the passport *first* and then requires
   every field of the extension object to agree with it. A field that
   disagrees with the signed delegation is a failure, never a fallback — an
   extension object that can contradict its passport and still pass would
   be strictly worse than no extension object at all.

Purpose of use
--------------
`hl7-b2b` already requires `purpose_of_use`, so `nhid-agent` deliberately
does **not** carry a copy of it. That is not an omission — it is what keeps
the invariant below true:

    Every field of `nhid-agent` is derived from the signed delegation.
    There are no caller-supplied fields, so there is nothing in the object
    that `verify_extension` cannot check against a signature.

A duplicated `purpose_of_use` would have been the one exception, and an
unverifiable field inside a credential-adjacent object is exactly the defect
this module exists to avoid.

What is useful instead is the cross-check, which nothing in UDAP can do
today: is the purpose the token request asserts in `hl7-b2b` consistent with
the scope the provider actually delegated? A request asserting
`COVAUTH` (prior authorization) under a delegation scoped to `eligibility`
alone is a real inconsistency, and `check_purpose_of_use` reports it.

The mapping that makes that check possible runs both ways through
`SCOPE_PURPOSE_OF_USE`, and covers only the scopes with a defensible
counterpart, against codes verified in HL7 Terminology v7.4.0 (ValueSet
PurposeOfUse v3.1.0, CodeSystem v3-ActReason v4.0.0). A purpose with no
mapping is reported as **not assessable** rather than passed or failed, and
no code is ever invented to fill a field.

Worth noting what that value set does and does not contain. It has gained
AI-specific *purposes* — `PMTDS` "decision support assisted payment
decision" and `TREATDS` "decision support assisted treatment decision", both
defined as applying algorithms "(e.g. AI, CDS)" to reach a decision. Those
describe the holder's own AI decisioning, not an AI requestor acting under a
provider's delegation, so nothing here maps to them. The vocabulary has
started to name AI in the purpose slot while the requestor slot still has
nowhere to put one.
"""
from __future__ import annotations

import base64
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from src.agent_identity import (
    AgentIdentityManager,
    AgentPassport,
    VerificationResult,
    _validate_npi,
)

# ── Constants ─────────────────────────────────────────────────────────────────

#: Key this object is published under inside the authentication JWT's
#: `extensions` claim, beside `hl7-b2b`.
EXTENSION_KEY = "nhid-agent"

#: Mirrors `hl7-b2b`'s own `version` convention: a fixed string, not an int.
EXTENSION_VERSION = "1"

#: NPI naming system. UDAP's §5.2.1.3 worked example is
#: `urn:oid:2.16.840.1.113883.4.6#1234567890`.
NPI_NAMING_SYSTEM = "urn:oid:2.16.840.1.113883.4.6"

#: HL7 v3 ActReason, the code system behind the PurposeOfUse value set.
#: UDAP's own example for the treatment purpose is
#: `urn:oid:2.16.840.1.113883.5.8#TREAT`.
PURPOSE_OF_USE_SYSTEM = "urn:oid:2.16.840.1.113883.5.8"

ERR_EXTENSION_MISMATCH = "ERR_EXTENSION_MISMATCH"
ERR_EXTENSION_MALFORMED = "ERR_EXTENSION_MALFORMED"
ERR_PURPOSE_UNSUPPORTED = "ERR_PURPOSE_UNSUPPORTED"

#: Delegation scope -> HL7 PurposeOfUse code, for the scopes where a
#: defensible counterpart exists. Each entry carries why.
#:
#:   ELIGVER  "eligibility verification ... May entail provider contacting
#:            coverage source ... for confirmation of enrollment, eligibility
#:            for specific services, and any applicable copays."
#:            That sentence is the voice call this framework governs.
#:   COVAUTH  "coverage authorization ... for conducting prior authorization
#:            or predetermination of coverage for services."
#:   HPAYMT   "healthcare payment ... for conducting financial or contractual
#:            activities related to payment for provision of health care."
#:            Used for claim-status and billing scopes. This is a deliberate
#:            approximation: HPAYMT is the parent concept and the value set
#:            has no leaf for a claim-status inquiry. Stated here so nobody
#:            later mistakes it for an exact match.
SCOPE_PURPOSE_OF_USE: Dict[str, str] = {
    "eligibility": "ELIGVER",
    "eligibility_check": "ELIGVER",
    "prior_auth": "COVAUTH",
    "claim_status": "HPAYMT",
    "claim_status_inquiry": "HPAYMT",
    "claims_inquiry": "HPAYMT",
    "billing": "HPAYMT",
}


# ── Formatting helpers ────────────────────────────────────────────────────────

def npi_to_uri(npi: str) -> str:
    """Render an NPI in UDAP's preferred identifier format.

    Validated through `agent_identity._validate_npi` rather than a second
    regex here, so there is one definition of a well-formed NPI in the
    codebase and this cannot drift from the one the delegation was signed
    under.
    """
    if not npi:
        raise ValueError("cannot build an NPI URI from an empty NPI")
    _validate_npi(npi)
    return f"{NPI_NAMING_SYSTEM}#{npi}"


def purpose_of_use_to_uri(code: str) -> str:
    """Render an HL7 PurposeOfUse code in UDAP's preferred format."""
    return f"{PURPOSE_OF_USE_SYSTEM}#{code}"


def key_fingerprint(agent_public_key_b64: str) -> str:
    """SHA-256 over the raw Ed25519 public key bytes.

    The fingerprint is a short, loggable handle for "which key" that a payer
    can compare across calls without storing the key itself. It is derived
    from the delegation's own `agent_public_key_b64`, so it cannot name a
    different key than the one the provider signed for.
    """
    raw = base64.b64decode(agent_public_key_b64)
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def purposes_for_scope(scope: Iterable[str]) -> List[str]:
    """Purpose-of-use URIs for the scopes that have a defensible mapping.

    Intended for building the *`hl7-b2b`* object's required `purpose_of_use`
    array from a delegation, not for `nhid-agent`, which carries no copy of
    it. Returns only what `SCOPE_PURPOSE_OF_USE` covers, de-duplicated and
    sorted; a scope with no honest counterpart contributes nothing and is
    not approximated.

    An empty return means "this delegation's scope does not tell you the
    purpose of use" — the caller must then supply one. It does not mean the
    scope is unauthorized.
    """
    codes = {SCOPE_PURPOSE_OF_USE[s] for s in scope if s in SCOPE_PURPOSE_OF_USE}
    return [purpose_of_use_to_uri(c) for c in sorted(codes)]


def scopes_for_purpose(code: str) -> List[str]:
    """The scopes whose delegation would justify asserting this purpose.

    The inverse of `SCOPE_PURPOSE_OF_USE`. Several scopes can share one
    purpose — `HPAYMT` covers claim-status and billing scopes alike — so
    asserting a purpose is consistent with holding *any* of the scopes that
    map to it, not all of them.
    """
    bare = code.rsplit("#", 1)[-1]
    return sorted(s for s, c in SCOPE_PURPOSE_OF_USE.items() if c == bare)


def check_purpose_of_use(
    hl7_b2b: Dict[str, Any],
    verified_scope: Sequence[str],
) -> VerificationResult:
    """Is the purpose asserted in `hl7-b2b` consistent with the delegation?

    This is the check nothing in UDAP can perform today, because today there
    is no delegation in the token request to check against. A request
    asserting `COVAUTH` — prior authorization — while carrying a delegation
    scoped to `eligibility` alone is claiming a purpose the provider did not
    delegate authority for.

    Pass `verified_scope` from a `VerificationResult` that already came back
    valid, never from the unverified extension object. The signature is what
    makes the scope worth comparing against; a scope read out of an
    unverified payload would make this check theatre.

    Three outcomes, kept distinct on purpose:

    * **invalid** — an asserted purpose maps to scopes and the delegation
      carries none of them. A real contradiction.
    * **valid, nothing unassessed** — every asserted purpose is backed by a
      delegated scope.
    * **valid, some unassessed** — a purpose outside the mapping (`TREAT`,
      say). `reason` names them. Not an endorsement: it says this module
      has no basis to judge, which is different from judging it fine.
    """
    asserted = hl7_b2b.get("purpose_of_use") or []
    if not isinstance(asserted, list):
        return VerificationResult(
            False, f"{ERR_EXTENSION_MALFORMED}: hl7-b2b purpose_of_use must "
                   f"be an array"
        )

    held = set(verified_scope)
    unassessable: List[str] = []
    for code in asserted:
        justifying = scopes_for_purpose(str(code))
        if not justifying:
            unassessable.append(str(code))
            continue
        if not held.intersection(justifying):
            return VerificationResult(
                False,
                f"{ERR_PURPOSE_UNSUPPORTED}: {code} would require one of "
                f"{justifying}, delegated scope is {sorted(held)}",
                scope=sorted(held),
            )

    if unassessable:
        return VerificationResult(
            True,
            f"Consistent; not assessable against delegated scope: "
            f"{sorted(unassessable)}",
            scope=sorted(held),
        )
    return VerificationResult(True, "Consistent", scope=sorted(held))


# ── Build ─────────────────────────────────────────────────────────────────────

def build_extension(
    passport: Union[AgentPassport, Sequence[AgentPassport]],
) -> Dict[str, Any]:
    """Build the `nhid-agent` object from a passport, or from a chain.

    Takes nothing but the passport. Every value is read off the delegation,
    which is what lets `verify_extension` check all of them against a
    signature — see the note on purpose of use in the module docstring for
    why there is no second argument.

    For a chain, the agent fields describe the **last** hop (the agent that
    will actually make the request) while `provider_npi` comes from the
    **root** delegation (the provider whose authority the chain descends
    from). That split matches what `AgentIdentityManager.validate_chain`
    reports, so the object and the verifier agree on what a chain means.
    """
    chain = _as_chain(passport)
    leaf = chain[-1].delegation
    root = chain[0].delegation

    obj: Dict[str, Any] = {
        "version": EXTENSION_VERSION,
        "agent_id": leaf.agent_id,
        "agent_key_fingerprint": key_fingerprint(leaf.agent_public_key_b64),
        "delegation_id": leaf.delegation_id,
        "scope": list(leaf.scope),
        "expires_at": leaf.expires_at,
    }

    # Omitted rather than emitted empty: a delegation with no NPI asserts no
    # NPI, and `urn:oid:...#` with nothing after the hash would read as one.
    if root.provider_npi:
        obj["provider_npi"] = npi_to_uri(root.provider_npi)

    if leaf.call_sid:
        obj["call_sid"] = leaf.call_sid

    if len(chain) > 1:
        obj["delegation_chain_depth"] = len(chain)

    return obj


# ── Verify ────────────────────────────────────────────────────────────────────

def verify_extension(
    extension: Dict[str, Any],
    passport: Union[AgentPassport, Sequence[AgentPassport]],
    provider_pub,
    manager: Optional[AgentIdentityManager] = None,
    call_sid: str = "",
) -> VerificationResult:
    """Verify the passport, then require the extension object to agree with it.

    Order matters and is the whole point. The passport is verified first,
    through `AgentIdentityManager` — expiry, revocation, both signatures,
    call-SID nonce binding, and for a chain the depth limit and monotonic
    narrowing. Only then is the extension object compared against what was
    just verified.

    So a failing passport fails here with the passport's own reason code,
    unchanged, and a passing passport still fails if the extension object
    says anything different from it. There is no path by which a value in
    this object is believed on its own.

    Because `build_extension` takes no caller input, the comparison here
    is total: every key on either side must be present on the other and
    equal. A field this module does not produce is a mismatch rather than
    something that rides along unchecked, and a field it does produce cannot
    be dropped to avoid scrutiny.

    Purpose of use is not compared, because `nhid-agent` does not carry it.
    Use `check_purpose_of_use` against the `hl7-b2b` object and this
    result's `scope` for that.
    """
    mgr = manager or AgentIdentityManager()
    chain = _as_chain(passport)

    if len(chain) > 1:
        result = mgr.validate_chain(chain, provider_pub)
    else:
        result = mgr.verify_passport(chain[0], provider_pub, call_sid=call_sid)
    if not result.valid:
        return result

    if not isinstance(extension, dict):
        return VerificationResult(
            False, f"{ERR_EXTENSION_MALFORMED}: expected a JSON object"
        )

    shape = _check_shape(extension)
    if shape is not None:
        return VerificationResult(False, shape)

    expected = build_extension(chain)

    for key in sorted(set(expected) | set(extension)):
        if key not in extension:
            return VerificationResult(
                False, f"{ERR_EXTENSION_MISMATCH}: {key} is missing"
            )
        if key not in expected:
            return VerificationResult(
                False, f"{ERR_EXTENSION_MISMATCH}: {key} is not a field of "
                       f"{EXTENSION_KEY}"
            )
        if extension[key] != expected[key]:
            return VerificationResult(
                False,
                f"{ERR_EXTENSION_MISMATCH}: {key} does not match the "
                f"verified delegation",
            )

    return result


def _check_shape(extension: Dict[str, Any]) -> Optional[str]:
    """The one shape error worth naming separately from a value mismatch."""
    if extension.get("version") != EXTENSION_VERSION:
        return (
            f"{ERR_EXTENSION_MALFORMED}: version must be "
            f"{EXTENSION_VERSION!r}"
        )
    return None


def _as_chain(
    passport: Union[AgentPassport, Sequence[AgentPassport]]
) -> List[AgentPassport]:
    if isinstance(passport, AgentPassport):
        return [passport]
    chain = list(passport)
    if not chain:
        raise ValueError("an empty chain describes no agent")
    return chain
