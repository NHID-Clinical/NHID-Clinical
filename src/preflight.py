"""Refuse to start a staging or production API that is missing a security setting.

Each protected surface already fails closed on its own: an unset API key gives
503 on every authenticated route, an unset ``TWILIO_AUTH_TOKEN`` gives 503 on
the voice webhooks, incomplete audit configuration gives 503 on ``/v1/audit``.
That is safe, but a misconfigured deployment still starts, answers ``/health``
with "ok", and reveals each gap only when a request happens to hit it.

``main.py`` runs ``problems()`` at startup in ``staging`` and ``production``
and refuses to start, listing every problem at once. Development is never
blocked. Operators can run the same check before deploying::

    DEPLOYMENT_MODE=production python -m src.preflight

which prints problems and warnings and exits 1 if there are any problems.
"""
from __future__ import annotations

import os
import sys
from typing import List

from src.webhook_security import STRICT_MODES, deployment_mode


def _flag(env: str) -> bool:
    return (os.getenv(env) or "").strip().lower() in {"1", "true", "yes", "on"}


def problems() -> List[str]:
    """Settings a strict deployment must not start without. Empty in development."""
    if deployment_mode() not in STRICT_MODES:
        return []
    found: List[str] = []

    from nhid_api_auth import API_KEY_ENV, API_KEYS_ENV, configured_api_key, configured_tenant_keys
    try:
        tenants = configured_tenant_keys()
    except ValueError as exc:  # json.JSONDecodeError is a ValueError
        found.append(f"{API_KEYS_ENV} is malformed: {exc}")
    else:
        if not tenants and not configured_api_key():
            found.append(f"no API key configured: set {API_KEYS_ENV} (or the legacy {API_KEY_ENV})")

    if not (os.getenv("TWILIO_AUTH_TOKEN") or "").strip():
        found.append("TWILIO_AUTH_TOKEN is unset: voice webhooks cannot be verified")

    from fastapi import HTTPException
    import nhid_audit_export
    try:
        nhid_audit_export.get_store()
    except HTTPException as exc:
        found.append(str(exc.detail))
    except Exception as exc:  # unwritable path, unopenable database, ...
        found.append(f"audit storage could not be opened: {exc}")

    if _flag("NHID_ATTEST_ENABLED"):
        from nhid_attest import MIN_SECRET_LENGTH
        if len((os.getenv("NHID_JWT_SECRET") or "").strip()) < MIN_SECRET_LENGTH:
            found.append(
                f"NHID_ATTEST_ENABLED is set but NHID_JWT_SECRET is unset or shorter "
                f"than {MIN_SECRET_LENGTH} characters")
    return found


def warnings() -> List[str]:
    """Settings worth a look that do not block startup."""
    if deployment_mode() not in STRICT_MODES:
        return []
    found: List[str] = []
    if deployment_mode() == "production" and _flag("NHID_ENABLE_DEBUG_REPLAY"):
        found.append("NHID_ENABLE_DEBUG_REPLAY is on in production: session transcripts "
                     "are readable by any API key holder at /voice/debug/replay")
    if not (os.getenv("NHID_PUBLIC_BASE_URL") or "").strip():
        found.append("NHID_PUBLIC_BASE_URL is unset: Twilio signatures will fail behind "
                     "a proxy that rewrites the host or scheme")
    return found


def enforce() -> List[str]:
    """Raise if there are problems; otherwise return the warnings."""
    found = problems()
    if found:
        raise RuntimeError(
            f"refusing to start in DEPLOYMENT_MODE={deployment_mode()}: "
            + "; ".join(found))
    return warnings()


def main() -> int:
    mode = deployment_mode()
    found, cautions = problems(), warnings()
    print(f"DEPLOYMENT_MODE={mode}")
    if mode not in STRICT_MODES:
        print("development mode: nothing is required (staging and production are checked)")
    for p in found:
        print(f"PROBLEM  {p}")
    for w in cautions:
        print(f"WARNING  {w}")
    if not found and mode in STRICT_MODES:
        print("preflight passed")
    return 1 if found else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(main())
