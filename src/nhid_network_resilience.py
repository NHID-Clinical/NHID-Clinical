"""Bounded retry with jittered exponential backoff for transient outbound
HTTP failures (network jitter, 5xx/429 responses) — mirrors
nhid_event_store.py::_run_sqlite_with_retry's shape, but for the two
unprotected external POSTs in functions/handler.py (Cloudflare Turnstile
verification, ElevenLabs outbound-call) instead of SQLite lock contention.
"""
import random
import time
from functools import wraps

try:
    import httpx
    _TRANSIENT_EXCEPTIONS = (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadError,
        httpx.NetworkError,
        httpx.RemoteProtocolError,
    )
except ImportError:  # pragma: no cover - httpx is an optional dependency elsewhere too
    httpx = None
    _TRANSIENT_EXCEPTIONS = (ConnectionError, TimeoutError)


def _is_transient_http_status(exc: BaseException) -> bool:
    """5xx and 429 are worth retrying; other 4xx responses are not — the
    request was rejected, not lost, and retrying it won't change that."""
    if httpx is not None and isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status >= 500 or status == 429
    return False


def retry_with_backoff(max_attempts: int = 3, base_delay: float = 0.5, jitter: float = 0.25):
    """Decorator: retry the wrapped call on transient network errors (timeouts,
    connection drops) or transient HTTP status codes (5xx, 429), up to
    max_attempts total tries, with jittered exponential backoff between
    attempts. Non-transient errors (4xx other than 429, programming errors)
    propagate immediately without retrying."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except _TRANSIENT_EXCEPTIONS:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                except Exception as exc:  # noqa: BLE001
                    if not _is_transient_http_status(exc):
                        raise
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                time.sleep(base_delay * (2 ** (attempt - 1)) + random.uniform(0, jitter))
        return wrapper
    return decorator
