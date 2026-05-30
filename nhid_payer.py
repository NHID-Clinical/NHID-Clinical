import os
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

DB_PATH = os.getenv("NHID_AUTH_DB", "nhid_auth.db")

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class PayerScreenRequest(BaseModel):
    caller_npi: str
    reference_id: str
    requested_scope: str

@router.post("/v1/payer/screen")
def screen_incoming_call(body: PayerScreenRequest):
    db = _get_db()
    row = db.execute(
        "SELECT * FROM attestations WHERE reference_id = ?",
        (body.reference_id,)
    ).fetchone()
    db.close()

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