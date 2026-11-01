"""Protection for the voice pipeline's public surface.

The voice app (``app.py``) is mounted beside the API-key routers, not behind
them, because Twilio cannot send an API key. That left two gaps:

1. ``/voice/incoming`` and ``/voice/process`` accepted any POST. Anyone who knew
   the URL could inject call events. Twilio signs every webhook with the
   account's auth token (``X-Twilio-Signature``); this module checks it.
2. ``/debug/replay/{session_id}`` returned a session's full forensic trace,
   transcripts included, to anyone who knew or guessed a session id.

Policy, by ``DEPLOYMENT_MODE``:

* **development** (default): webhooks are verified when ``TWILIO_AUTH_TOKEN`` is
  set and accepted with a warning when it is not; debug replay is available.
* **staging / production**: webhooks without a valid signature are refused, and
  a missing ``TWILIO_AUTH_TOKEN`` refuses every webhook (503) rather than
  accepting unsigned ones. Debug replay is **off** (404) unless
  ``NHID_ENABLE_DEBUG_REPLAY=1``, and even then needs an API key.

The signature algorithm follows Twilio's own ``RequestValidator`` (twilio-python
9.x): the full request URL, then each POST parameter's name and value in sorted
order, HMAC-SHA1 with the auth token, base64. The URL is tried with and without
its default port, as Twilio's validator does. Behind a proxy that rewrites the
host or scheme, set ``NHID_PUBLIC_BASE_URL`` to the URL Twilio was given.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from typing import Iterable, Mapping, Sequence, Tuple, Union
from urllib.parse import urlparse

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

STRICT_MODES = {"staging", "production"}
_warned_unsigned = False


def deployment_mode() -> str:
    return (os.getenv("DEPLOYMENT_MODE") or "development").strip().lower()


Params = Union[Mapping[str, str], Sequence[Tuple[str, str]]]


def _pairs(params: Params) -> Iterable[Tuple[str, str]]:
    items = params.items() if isinstance(params, Mapping) else params
    return [(str(k), str(v)) for k, v in items]


def twilio_signature(url: str, params: Params, auth_token: str) -> str:
    """Twilio's request signature for ``url`` and form ``params``."""
    pairs = _pairs(params)
    names = sorted({k for k, _ in pairs})
    data = url
    for name in names:
        for value in sorted({v for k, v in pairs if k == name}):
            data += name + value
    mac = hmac.new(auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode("ascii")


def _url_variants(url: str) -> Tuple[str, str]:
    """The URL without and with its default port, as Twilio's validator tries both."""
    parsed = urlparse(url)
    if parsed.port:
        return parsed._replace(netloc=parsed.netloc.split(":")[0]).geturl(), url
    port = 443 if parsed.scheme == "https" else 80
    return url, parsed._replace(netloc=f"{parsed.netloc}:{port}").geturl()


def signature_is_valid(url: str, params: Params, signature: str, auth_token: str) -> bool:
    if not signature:
        return False
    return any(hmac.compare_digest(twilio_signature(u, params, auth_token), signature)
               for u in _url_variants(url))


def _public_url(request: Request) -> str:
    base = (os.getenv("NHID_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base:
        return str(request.url)
    # request.url already carries any mount prefix (root_path), so the path is
    # the one the outside world called.
    query = f"?{request.url.query}" if request.url.query else ""
    return f"{base}{request.url.path}{query}"


async def require_twilio_signature(request: Request) -> None:
    """FastAPI dependency for Twilio webhook routes."""
    global _warned_unsigned
    token = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
    mode = deployment_mode()
    if not token:
        if mode in STRICT_MODES:
            raise HTTPException(
                status_code=503,
                detail="Webhook verification is not configured: TWILIO_AUTH_TOKEN is unset",
            )
        if not _warned_unsigned:
            logger.warning("TWILIO_AUTH_TOKEN is unset: accepting UNSIGNED voice webhooks "
                           "(DEPLOYMENT_MODE=%s). Never run this way with real calls.", mode)
            _warned_unsigned = True
        return
    form = await request.form()
    params = list(form.multi_items())
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature_is_valid(_public_url(request), params, signature, token):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


async def require_debug_access(request: Request) -> None:
    """FastAPI dependency for the debug replay route."""
    if deployment_mode() not in STRICT_MODES:
        return
    if (os.getenv("NHID_ENABLE_DEBUG_REPLAY") or "").strip() != "1":
        # 404, not 403: in strict modes the route does not exist.
        raise HTTPException(status_code=404, detail="Not Found")
    from nhid_api_auth import authenticate

    request.state.tenant_id = authenticate(request.headers.get("X-API-Key"))
