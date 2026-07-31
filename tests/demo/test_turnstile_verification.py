"""
Tests for functions/handler.py::_verify_turnstile() — Cloudflare Turnstile
CAPTCHA verification for public website demo forms. Website demo feature,
NOT the NHID-Clinical governance framework (lives under tests/demo/,
excluded from the framework's pytest tests/ baseline — see pytest.ini).

Monkeypatches httpx.post — no real network calls, matching the convention
in tests/demo/test_elevenlabs_client.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import functions.handler as handler  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_missing_token_rejected_without_network_call(monkeypatch):
    monkeypatch.setenv(handler.TURNSTILE_SECRET_ENV, "test-secret")
    called = []
    monkeypatch.setattr(handler.httpx, "post", lambda *a, **k: called.append(1))

    assert handler._verify_turnstile("") is False
    assert called == []


def test_missing_secret_env_rejected(monkeypatch):
    monkeypatch.delenv(handler.TURNSTILE_SECRET_ENV, raising=False)
    assert handler._verify_turnstile("some-token") is False


def test_successful_verification(monkeypatch):
    monkeypatch.setenv(handler.TURNSTILE_SECRET_ENV, "test-secret")
    monkeypatch.setattr(
        handler.httpx, "post", lambda *a, **k: _FakeResponse({"success": True})
    )
    assert handler._verify_turnstile("good-token") is True


def test_cloudflare_rejection(monkeypatch):
    monkeypatch.setenv(handler.TURNSTILE_SECRET_ENV, "test-secret")
    monkeypatch.setattr(
        handler.httpx, "post", lambda *a, **k: _FakeResponse({"success": False, "error-codes": ["invalid-input-response"]})
    )
    assert handler._verify_turnstile("bad-token") is False


def test_network_error_rejected(monkeypatch):
    monkeypatch.setenv(handler.TURNSTILE_SECRET_ENV, "test-secret")

    def _raise(*a, **k):
        raise ConnectionError("network down")

    monkeypatch.setattr(handler.httpx, "post", _raise)
    assert handler._verify_turnstile("any-token") is False


def test_http_error_status_rejected(monkeypatch):
    monkeypatch.setenv(handler.TURNSTILE_SECRET_ENV, "test-secret")
    monkeypatch.setattr(
        handler.httpx, "post", lambda *a, **k: _FakeResponse({}, status_code=500)
    )
    assert handler._verify_turnstile("any-token") is False


def test_posts_secret_and_token_to_cloudflare(monkeypatch):
    monkeypatch.setenv(handler.TURNSTILE_SECRET_ENV, "my-secret")
    captured = {}

    def _fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _FakeResponse({"success": True})

    monkeypatch.setattr(handler.httpx, "post", _fake_post)
    handler._verify_turnstile("the-token")

    assert captured["url"] == handler.TURNSTILE_VERIFY_URL
    assert captured["data"]["secret"] == "my-secret"
    assert captured["data"]["response"] == "the-token"
