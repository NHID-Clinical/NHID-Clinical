"""Deprecated symmetric-signing attestation scaffold.

``POST /v1/attest`` signs with **HS256**. The signing key is symmetric, so any
party able to verify one of these tokens can also mint one — there is no
separation between verifier and issuer, no key identifier, and no asymmetric
option. It is not a basis for trust across an organisational boundary, and the
Ed25519 delegation format in ``src/agent_identity.py`` supersedes it.

It also previously fell back to a signing secret published in this repository
(``"nhid-dev-secret"``), so a deployment that never set ``NHID_JWT_SECRET``
issued tokens anyone reading the source could forge. Combined with the router
being mounted without an authentication dependency, an unauthenticated caller
could obtain a delegation token signed with a known key.

Minting is therefore **off by default** and refuses with ``410``. An operator
who still needs it must opt in deliberately:

    NHID_ATTEST_ENABLED=1
    NHID_JWT_SECRET=<at least 32 characters, not from this repository>

There is no default secret; without one the endpoint refuses with ``503``
rather than signing. ``GET /v1/attest/verify/{reference_id}`` reads local state
and keeps working either way, so references issued earlier remain inspectable.

Retiring this module altogether is a separate decision.

Tenant scoping: every attestation records the tenant whose API key minted it,
and ``verify`` (and ``/v1/payer/screen``) see only the caller's own. Another
tenant's reference id reads as not found. Rows written before this column
existed belong to ``default``, the tenant the legacy ``NHID_API_KEY``
authenticates as, so a single-key deployment is unchanged.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Header, HTTPException, Depends, Request
from pydantic import BaseModel
import jwt

from nhid_api_auth import DEFAULT_TENANT, tenant_of

router = APIRouter()

DB_PATH = os.getenv("NHID_AUTH_DB", "nhid_auth.db")

#: Shortest secret accepted for HS256. Anything less is not worth signing with.
MIN_SECRET_LENGTH = 32


def attest_enabled() -> bool:
    """Whether an operator has explicitly opted in to minting. Default: no."""
    return (os.getenv("NHID_ATTEST_ENABLED") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _signing_secret() -> str:
    """The configured HS256 secret, or refuse. There is deliberately no default."""
    secret = (os.getenv("NHID_JWT_SECRET") or "").strip()
    if len(secret) < MIN_SECRET_LENGTH:
        raise HTTPException(
            status_code=503,
            detail=(
                "NHID_JWT_SECRET is unset or too short: attestation signing "
                f"requires at least {MIN_SECRET_LENGTH} characters. No default "
                "secret is used."
            ),
        )
    return secret

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
            revoked           INTEGER NOT NULL DEFAULT 0,
            tenant_id         TEXT NOT NULL DEFAULT 'default'
        )
    """)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(attestations)")}
    if "tenant_id" not in columns:
        # A table from before tenant scoping: its rows go to the legacy tenant.
        conn.execute(
            "ALTER TABLE attestations ADD COLUMN tenant_id TEXT NOT NULL "
            f"DEFAULT '{DEFAULT_TENANT}'"
        )
    conn.commit()
    return conn

def find_attestation(reference_id: str, tenant_id: str):
    """The tenant's attestation with this reference id, or None.

    None also when the id exists under another tenant: the two must be
    indistinguishable, or the endpoint tells a caller which ids are real.
    """
    db = _get_db()
    try:
        return db.execute(
            "SELECT * FROM attestations WHERE reference_id = ? AND tenant_id = ?",
            (reference_id, tenant_id),
        ).fetchone()
    finally:
        db.close()

class AttestRequest(BaseModel):
    delegating_entity: str
    authorized_actor: str
    scope: List[str]
    expires_at: str

@router.post("/v1/attest")
def create_attestation(body: AttestRequest, request: Request):
    if not attest_enabled():
        raise HTTPException(
            status_code=410,
            detail=(
                "/v1/attest is a deprecated HS256 attestation scaffold and is "
                "disabled. Its signing key is symmetric, so any verifier can "
                "also mint. Set NHID_ATTEST_ENABLED=1 and NHID_JWT_SECRET to "
                "re-enable it deliberately."
            ),
        )
    # Refuses before anything is generated or written, so a misconfigured
    # server never records an attestation it could not sign.
    secret = _signing_secret()
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
        "INSERT INTO attestations (reference_id, delegating_entity, "
        "authorized_actor, scope, expires_at, issued_at, revoked, tenant_id) "
        "VALUES (?,?,?,?,?,?,0,?)",
        (reference_id, body.delegating_entity, body.authorized_actor,
         ",".join(body.scope), body.expires_at, issued_at, tenant_of(request)),
    )
    db.commit()
    db.close()
    return {
        "reference_id": reference_id,
        "token": token,
        "revocation_endpoint": f"/v1/attest/revoke/{reference_id}"
    }

@router.get("/v1/attest/verify/{reference_id}")
def verify_attestation(reference_id: str, request: Request):
    row = find_attestation(reference_id, tenant_of(request))
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