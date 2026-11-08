"""ACC-01 record-level access: the payer-side check, opt-in inside PDX-01.

docs/proposals/patient-access-authorization.md. PDX-01's field scope answers
"may this delegation receive *this kind* of field?". It cannot answer "is
*this patient's record* anything to do with the delegating provider?". A
caller-agent with a valid delegation for claim status can still ask about a
claim nothing ties to its provider. ACC-01 asks the payer's own records.

Three rules this module keeps:

* **The provider comes only from the verified delegation.** The NPI is read
  from `DelegationResult.provider_npi` after DLG-01 has verified it. Nothing
  the caller says on the call is consulted. NPIs are public; quoting one
  establishes nothing.
* **The relationship policy is data.** Which relationships a payer accepts for
  which operation is a dict the payer can narrow (`DEFAULT_POLICY`).
* **Unknown never passes.** Evidence the payer cannot resolve gives `unknown`,
  which the engine escalates to a human. Only a positive link gives `pass`.

This module does no network I/O. The payer's systems answer through the
`PayerRecords` protocol; the result is written into the session as
`session["access_authorization"]` (the trace field), where `evaluate_pdx01`
reads it when `DelegationContext.require_record_access` is set. ACC-01 is not
a control of its own: it is a check inside PDX-01.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol

PASS, EXCEPTION, UNKNOWN, NOT_ASSESSABLE = "pass", "exception", "unknown", "not_assessable"

OPERATIONS = ("eligibility", "claim_status", "prior_auth")

# Which relationship, in order of preference, a payer accepts for each operation.
DEFAULT_POLICY: Mapping[str, tuple[str, ...]] = {
    "eligibility": ("PAYER_ATTRIBUTION", "UPCOMING_APPOINTMENT"),
    "claim_status": ("CLAIM_BILLING_PROVIDER", "CLAIM_RENDERING_PROVIDER",
                     "ORGANIZATIONAL_MEMBERSHIP"),
    "prior_auth": ("PRIOR_AUTH_REQUESTING_PROVIDER", "PRIOR_AUTH_SERVICING_PROVIDER",
                   "ORGANIZATIONAL_MEMBERSHIP"),
}

# The typed resource each operation is bound to (proposal §8.1).
RESOURCE_TYPES = {
    "eligibility": "MEMBER_ELIGIBILITY_REQUEST",
    "claim_status": "MEMBER_CLAIM",
    "prior_auth": "MEMBER_AUTH_CASE",
}


@dataclass(frozen=True)
class AccessRequest:
    """What the caller asked for: an operation on one bound resource.

    `resource_binding` is `{"type": ..., "ref": "hmac-sha256:..."}`; the ref is
    a keyed hash, never a raw member or claim number.
    """
    operation: str
    resource_binding: Mapping[str, Any]


class PayerRecords(Protocol):
    """The payer's own systems, as ACC-01 needs them.

    Each relationship method returns True (linked), False (not linked) or
    None (the payer cannot tell).
    """
    def system_available(self) -> bool: ...
    def resource_matches_binding(self) -> bool: ...
    def identifiers_match(self) -> Optional[bool]: ...
    def relationship(self, basis: str, npi: str) -> Optional[bool]: ...
    def appointment_asserted(self) -> bool: ...


class MappingPayerRecords:
    """`PayerRecords` over a plain dict: the shape the fixtures use.

    A key that is absent means the record holds no such evidence (False). A
    key present with the value None means the payer cannot resolve it
    (unknown).
    """
    _NPI_FIELDS = {
        "CLAIM_BILLING_PROVIDER": "claim_billing_npi",
        "CLAIM_RENDERING_PROVIDER": "claim_rendering_npi",
        "PRIOR_AUTH_REQUESTING_PROVIDER": "case_requesting_npi",
        "PRIOR_AUTH_SERVICING_PROVIDER": "case_servicing_npi",
    }
    _FLAG_FIELDS = {
        "ORGANIZATIONAL_MEMBERSHIP": "delegating_npi_in_billing_group",
        "PAYER_ATTRIBUTION": "member_attributed_to_delegating_npi",
        "UPCOMING_APPOINTMENT": "appointment_verified_by_payer",
    }

    def __init__(self, record: Mapping[str, Any]):
        self._r = dict(record)

    def system_available(self) -> bool:
        return self._r.get("claim_system_available", True) is not False

    def resource_matches_binding(self) -> bool:
        return self._r.get("token_resource_matches", True) is not False

    def identifiers_match(self) -> Optional[bool]:
        return self._r.get("member_dob_matches", True)

    def appointment_asserted(self) -> bool:
        return self._r.get("appointment_asserted_by_agent") is True

    def relationship(self, basis: str, npi: str) -> Optional[bool]:
        if basis in self._NPI_FIELDS:
            key = self._NPI_FIELDS[basis]
            if key not in self._r:
                return False
            value = self._r[key]
            return None if value is None else value == npi
        key = self._FLAG_FIELDS.get(basis)
        if key is None or key not in self._r:
            return False
        value = self._r[key]
        return None if value is None else bool(value)


@dataclass(frozen=True)
class AccessResult:
    operation: str
    resource_binding: Mapping[str, Any]
    result: str
    reason_code: Optional[str]
    relationship_basis: Optional[str]
    checks: Mapping[str, str] = field(default_factory=dict)

    def to_trace_field(self) -> dict:
        """The `access_authorization` trace field, exactly as the schema has it."""
        return {
            "result": self.result,
            "reason_code": self.reason_code,
            "operation": self.operation,
            "relationship_basis": self.relationship_basis,
            "resource_binding": dict(self.resource_binding),
            "binding_checks": {k: self.checks[k] for k in
                               ("patient_binding", "identifier_match",
                                "record_relationship", "purpose")},
        }


def _checks(patient, identifier, relationship, purpose):
    return {"patient_binding": patient, "identifier_match": identifier,
            "record_relationship": relationship, "purpose": purpose}


def evaluate_access(request: AccessRequest, records: PayerRecords, *, delegation,
                    prerequisites_met: bool,
                    policy: Mapping[str, tuple[str, ...]] = DEFAULT_POLICY) -> AccessResult:
    """Is this record linked to the provider the verified delegation names?

    `delegation` is the `DelegationResult` DLG-01 produced. `prerequisites_met`
    is True only when call verification (VER-01, where enabled) and PDX-01's
    field scope have both passed; otherwise nothing is assessed.
    """
    def result(res, reason, basis, checks):
        return AccessResult(request.operation, request.resource_binding, res, reason, basis, checks)

    npi = getattr(delegation, "provider_npi", None)
    if not prerequisites_met or not getattr(delegation, "verified", False) or not npi:
        na = NOT_ASSESSABLE
        return result(NOT_ASSESSABLE, "PREREQUISITE_NOT_MET", None, _checks(na, na, na, na))

    scope = getattr(delegation, "scope", None) or frozenset()
    if request.operation not in scope or request.operation not in policy:
        na = NOT_ASSESSABLE
        return result(EXCEPTION, "PURPOSE_NOT_DELEGATED", None, _checks(na, na, na, EXCEPTION))

    if not records.resource_matches_binding():
        na = NOT_ASSESSABLE
        return result(EXCEPTION, "RESOURCE_BINDING_MISMATCH", None, _checks(EXCEPTION, na, na, PASS))

    if not records.system_available():
        return result(UNKNOWN, "PAYER_RECORD_UNAVAILABLE", "UNKNOWN",
                      _checks(PASS, UNKNOWN, UNKNOWN, PASS))

    # The relationship, under the payer's policy for this operation.
    basis, any_unknown = None, False
    for candidate in policy[request.operation]:
        linked = records.relationship(candidate, npi)
        if linked is True:
            basis = candidate
            break
        if linked is None:
            any_unknown = True
    if basis is not None:
        rel_result, rel_reason, rel_basis = PASS, None, basis
    elif any_unknown:
        rel_result, rel_reason, rel_basis = UNKNOWN, "RELATIONSHIP_EVIDENCE_UNKNOWN", "UNKNOWN"
    elif request.operation == "eligibility":
        reason = "APPOINTMENT_NOT_VERIFIED" if records.appointment_asserted() else "NO_RECOGNIZED_RELATIONSHIP"
        rel_result, rel_reason, rel_basis = UNKNOWN, reason, "UNKNOWN"
    else:
        rel_result, rel_reason, rel_basis = EXCEPTION, "RECORD_NOT_LINKED", None

    ids = records.identifiers_match()
    id_check = PASS if ids is True else (EXCEPTION if ids is False else UNKNOWN)
    checks = _checks(PASS, id_check, rel_result, PASS)

    # An exception outranks unknown: a wrong identifier is a refusal even when
    # the relationship is also unresolved.
    if id_check == EXCEPTION:
        return result(EXCEPTION, "IDENTIFIER_MISMATCH", rel_basis, checks)
    if rel_result == EXCEPTION:
        return result(EXCEPTION, rel_reason, rel_basis, checks)
    if id_check == UNKNOWN and rel_result == PASS:
        return result(UNKNOWN, "IDENTIFIER_UNRESOLVED", rel_basis, checks)
    return result(rel_result, rel_reason, rel_basis, checks)
