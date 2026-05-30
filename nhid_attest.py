import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
import jwt

router = APIRouter()

DB_PATH = os.getenv("NHID_AUTH_DB", "nhid_auth.db")

def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attestations (
            reference_id      TEXT PRIMARY KEY,
            delegating_entity TEXT NOT NULL,
            authorized_actor  TEXT NOT NULL,
            scope             TEXT NOT NULL,
            expires_at        TEXT NOT NULL,
            issued_at         TEXT NOT NULL,
            revoked           INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    return conn

class AttestRequest(BaseModel):
    delegating_entity: str
    authorized_actor: str
    scope: List[str]
    expires_at: str

@router.post("/v1/attest")
def create_attestation(body: AttestRequest):
    secret = os.getenv("NHID_JWT_SECRET", "nhid-dev-secret")
    reference_id = str(uuid.uuid4())
    issued_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "reference_id": reference_id,
        "delegating_entity": body.delegating_entity,
        "authorized_actor": body.authorized_actor,
        "scope": body.scope,
        "expires_at": body.expires_at,
        "iat": issued_at,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    db = _get_db()
    db.execute(
        "INSERT INTO attestations VALUES (?,?,?,?,?,?,0)",
        (reference_id, body.delegating_entity, body.authorized_actor,
         ",".join(body.scope), body.expires_at, issued_at),
    )
    db.commit()
    db.close()
    return {
        "reference_id": reference_id,
        "token": token,
        "revocation_endpoint": f"/v1/attest/revoke/{reference_id}"
    }

@router.get("/v1/attest/verify/{reference_id}")
def verify_attestation(reference_id: str):
    db = _get_db()
    row = db.execute(
        "SELECT * FROM attestations WHERE reference_id = ?",
        (reference_id,)
    ).fetchone()
    db.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Attestation not found")
    now = datetime.now(timezone.utc).isoformat()
    expired = row["expires_at"] < now
    return {
        "valid": not row["revoked"] and not expired,
        "delegating_entity": row["delegating_entity"],
        "authorized_actor": row["authorized_actor"],
        "scope": row["scope"].split(","),
        "expires_at": row["expires_at"],
        "revoked": bool(row["revoked"]),
        "expired": expired,
    }