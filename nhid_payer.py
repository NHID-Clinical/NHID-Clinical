from datetime import datetime, timezone
from fastapi import APIRouter, Request
from pydantic import BaseModel

from nhid_api_auth import tenant_of
from nhid_attest import find_attestation

router = APIRouter()

# Screening reads the attestations table through nhid_attest, so the schema
# migration runs and the lookup is scoped to the caller's tenant: a payer can
# screen only references minted under its own key. Another tenant's reference
# gets the same "not found" reject as one that does not exist.

class PayerScreenRequest(BaseModel):
    caller_npi: str
    reference_id: str
    requested_scope: str

@router.post("/v1/payer/screen")
def screen_incoming_call(body: PayerScreenRequest, request: Request):
    row = find_attestation(body.reference_id, tenant_of(request))

    if row is None:
        return {
            "verified": False,
            "compliant": False,
            "recommended_action": "reject",
            "reason": "No attestation found for this reference ID"
        }

    now = datetime.now(timezone.utc).isoformat()
    expired = row["expires_at"] < now
    revoked = bool(row["revoked"])
    npi_match = row["delegating_entity"] == body.caller_npi
    scope_permitted = body.requested_scope in row["scope"].split(",")

    if revoked:
        return {
            "verified": False,
            "compliant": False,
            "recommended_action": "reject",
            "reason": "Attestation has been revoked"
        }

    if expired:
        return {
            "verified": False,
            "compliant": False,
            "recommended_action": "reject",
            "reason": "Attestation has expired"
        }

    if not npi_match:
        return {
            "verified": False,
            "compliant": False,
            "recommended_action": "reject",
            "reason": "Caller NPI does not match delegating entity"
        }

    if not scope_permitted:
        return {
            "verified": True,
            "compliant": False,
            "recommended_action": "escalate",
            "reason": f"Requested scope '{body.requested_scope}' not in permitted scope"
        }

    return {
        "verified": True,
        "compliant": True,
        "recommended_action": "accept",
        "reason": "Attestation valid, NPI matches, scope permitted"
    }