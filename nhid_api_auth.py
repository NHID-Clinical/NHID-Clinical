"""API-key authentication for the NHID-Clinical reference API.

Kept out of ``main.py`` so it can be imported, and tested, without pulling in
the voice pipeline — ``main`` imports ``app``, which imports ``llm``, which
needs the ``openai`` package at import time.

The dependency fails **closed**. The version this replaces read::

    expected = os.getenv("NHID_API_KEY")
    if expected and api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

When ``NHID_API_KEY`` was unset that accepted every request on every protected
route, including a request carrying no credential at all — and did so silently,
so a deployment that forgot the variable looked identical to one that had not.
Three routers depended on it and none of them were protected.

Unset now refuses with ``503`` rather than refusing to start, so ``/health`` and
the mounted ``/voice`` demo keep serving on an existing deployment while the
protected surface stays closed.

Per-customer keys
-----------------
One shared key cannot tell two customers apart, so anything stored under it
(audit exports, attestations) is readable by every key holder. ``NHID_API_KEYS``
holds one key **per tenant**, stored only as a SHA-256 hash::

    NHID_API_KEYS='{"payer-a": "sha256:<64 hex>", "payer-b": "sha256:<64 hex>"}'

The authenticated tenant is set on ``request.state.tenant_id`` for routes to
scope their data by. ``NHID_API_KEY`` still works and authenticates as the
tenant ``default``, so an existing single-key deployment is unchanged.

A malformed ``NHID_API_KEYS`` fails closed (``503``): a typo in the key table
must not silently fall back to "no tenants" or to the legacy key alone.
"""

import hashlib
import hmac
import json
import logging
import os
import re
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_ENV = "NHID_API_KEY"
API_KEYS_ENV = "NHID_API_KEYS"
DEFAULT_TENANT = "default"

_TENANT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(api_key: str) -> str:
    """The stored form of a tenant key. Use this to provision ``NHID_API_KEYS``."""
    return "sha256:" + hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def configured_api_key() -> str:
    """The legacy single key, or an empty string when none is configured.

    Read per request rather than cached at import, so that a process which has
    its environment corrected does not have to be restarted to notice.
    """
    return (os.getenv(API_KEY_ENV) or "").strip()


def configured_tenant_keys() -> Dict[str, str]:
    """Tenant id -> stored key hash, from ``NHID_API_KEYS``.

    Raises ``ValueError`` on anything malformed; callers fail closed on it.
    """
    raw = (os.getenv(API_KEYS_ENV) or "").strip()
    if not raw:
        return {}
    table = json.loads(raw)
    if not isinstance(table, dict) or not table:
        raise ValueError(f"{API_KEYS_ENV} must be a non-empty JSON object")
    for tenant, digest in table.items():
        if not isinstance(tenant, str) or not _TENANT_ID.match(tenant):
            raise ValueError(f"{API_KEYS_ENV}: invalid tenant id {tenant!r}")
        if not isinstance(digest, str) or not _HASH.match(digest):
            raise ValueError(
                f"{API_KEYS_ENV}: tenant {tenant!r} must map to 'sha256:<64 hex>', "
                "never a plaintext key")
    if DEFAULT_TENANT in table and configured_api_key():
        raise ValueError(
            f"{API_KEYS_ENV} defines tenant {DEFAULT_TENANT!r}, which {API_KEY_ENV} "
            "already authenticates as; use one or the other")
    return table


def api_key_configured() -> bool:
    try:
        return bool(configured_api_key() or configured_tenant_keys())
    except (ValueError, json.JSONDecodeError):
        return False


def authenticate(api_key: Optional[str]) -> str:
    """Return the tenant a presented key belongs to, or raise.

    503 — no key is configured (or the key table is malformed), so the server
          cannot authenticate anyone.
    401 — keys are configured and the caller sent no ``X-API-Key`` header.
    403 — the key presented matches no tenant.
    """
    try:
        tenants = configured_tenant_keys()
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("%s is malformed; refusing all authenticated requests: %s",
                     API_KEYS_ENV, exc)
        raise HTTPException(
            status_code=503,
            detail=f"Server is not configured for authenticated access: {API_KEYS_ENV} is malformed",
        )
    legacy = configured_api_key()
    if not legacy and not tenants:
        raise HTTPException(
            status_code=503,
            detail=(
                "Server is not configured for authenticated access: "
                f"{API_KEY_ENV} is unset"
            ),
        )
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    # Compare against every entry, in constant time, without stopping at the
    # first match, so timing does not reveal which tenant a key is close to.
    presented = hash_api_key(api_key)
    matched: Optional[str] = None
    for tenant, digest in tenants.items():
        if hmac.compare_digest(presented, digest):
            matched = tenant
    if legacy and hmac.compare_digest(api_key, legacy):
        matched = DEFAULT_TENANT
    if matched is None:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return matched


def get_api_key(request: Request, api_key: str = Security(api_key_header)) -> str:
    """FastAPI dependency: allow the request only on a verified API key.

    Sets ``request.state.tenant_id`` to the authenticated tenant. Returns the
    presented key, as before, for callers that used the return value.
    """
    request.state.tenant_id = authenticate(api_key)
    return api_key


def tenant_of(request: Request) -> str:
    """The tenant the request authenticated as. Routes behind ``get_api_key`` only."""
    tenant = getattr(request.state, "tenant_id", None)
    if not tenant:
        # A route reading tenant data without authentication is a wiring bug;
        # refusing is safer than defaulting to some tenant's data.
        raise HTTPException(status_code=500, detail="Request has no authenticated tenant")
    return tenant


if not api_key_configured():
    logger.error(
        "Neither %s nor %s is configured (or %s is malformed): every "
        "authenticated route will refuse with 503 until it is.",
        API_KEY_ENV, API_KEYS_ENV, API_KEYS_ENV,
    )
