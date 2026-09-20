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
"""

import hmac
import logging
import os

from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_ENV = "NHID_API_KEY"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def configured_api_key() -> str:
    """The expected API key, or an empty string when none is configured.

    Read per request rather than cached at import, so that a process which has
    its environment corrected does not have to be restarted to notice.
    """
    return (os.getenv(API_KEY_ENV) or "").strip()


def api_key_configured() -> bool:
    return bool(configured_api_key())


def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """FastAPI dependency: allow the request only on a verified API key.

    503 — the server has no key configured, so it cannot authenticate anyone.
    401 — a key is configured and the caller sent no ``X-API-Key`` header.
    403 — a key is configured and the one presented does not match.
    """
    expected = configured_api_key()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail=(
                "Server is not configured for authenticated access: "
                f"{API_KEY_ENV} is unset"
            ),
        )
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    # Constant-time, matching the comparison used on the SaaS side.
    if not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


if not api_key_configured():
    logger.error(
        "%s is unset: every authenticated route will refuse with 503 until it "
        "is configured.",
        API_KEY_ENV,
    )
