"""
Tests for functions/handler.py::_handle_demo_call() — triggers a Beacon
outbound ElevenLabs call. The one demo route with real per-call
Twilio/ElevenLabs cost, so it's gated by Cloudflare Turnstile + per-IP/
per-number rate limits before any network call is made. Website demo
feature, NOT the NHID-Clinical governance framework (lives under
tests/demo/, excluded from the framework's pytest tests/ baseline — see
pytest.ini).

Monkeypatches handler._verify_turnstile, rate_limiter.check_and_increment,
and httpx.post — no real network calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import functions.handler as handler  # noqa: E402
from functions import rate_limiter  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


def _event(phone: str = "+12025551234", token: str = "good-token") -> dict:
    return {
        "body": json.dumps({"phone": phone, "turnstile_token": token}),
        "requestContext": {"identity": {"sourceIp": "203.0.113.5"}},
    }


def _allow_everything(monkeypatch) -> None:
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: True)
    monkeypatch.setattr(rate_limiter, "check_and_increment", lambda *a, **k: True)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_PHONE_NUMBER_ID", "phone-123")


def test_missing_body_rejected():
    resp = handler._handle_demo_call({})
    assert resp["statusCode"] == 400


def test_failed_turnstile_rejected_before_any_other_work(monkeypatch):
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: False)
    called = []
    monkeypatch.setattr(rate_limiter, "check_and_increment", lambda *a, **k: called.append(1) or True)
    resp = handler._handle_demo_call(_event())
    assert resp["statusCode"] == 400
    assert called == []


def test_missing_phone_rejected(monkeypatch):
    _allow_everything(monkeypatch)
    resp = handler._handle_demo_call(_event(phone=""))
    assert resp["statusCode"] == 400


def test_invalid_phone_format_rejected(monkeypatch):
    _allow_everything(monkeypatch)
    resp = handler._handle_demo_call(_event(phone="123"))
    assert resp["statusCode"] == 400


def test_ip_rate_limit_exceeded_returns_429(monkeypatch):
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: True)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_PHONE_NUMBER_ID", "phone-123")

    def _fake_limit(key, limit, window_seconds, table=None):
        return not key.startswith("ip:")

    monkeypatch.setattr(rate_limiter, "check_and_increment", _fake_limit)
    resp = handler._handle_demo_call(_event())
    assert resp["statusCode"] == 429


def test_phone_rate_limit_exceeded_returns_429(monkeypatch):
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: True)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_PHONE_NUMBER_ID", "phone-123")

    def _fake_limit(key, limit, window_seconds, table=None):
        return not key.startswith("phone:")

    monkeypatch.setattr(rate_limiter, "check_and_increment", _fake_limit)
    resp = handler._handle_demo_call(_event())
    assert resp["statusCode"] == 429


def test_missing_env_config_returns_503(monkeypatch):
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: True)
    monkeypatch.setattr(rate_limiter, "check_and_increment", lambda *a, **k: True)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_PHONE_NUMBER_ID", raising=False)
    resp = handler._handle_demo_call(_event())
    assert resp["statusCode"] == 503


def test_successful_call_returns_call_id(monkeypatch):
    _allow_everything(monkeypatch)
    monkeypatch.setattr(
        handler.httpx, "post", lambda *a, **k: _FakeResponse({"call_id": "call_abc123"})
    )
    resp = handler._handle_demo_call(_event())
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "dialing"
    assert body["call_id"] == "call_abc123"


def test_falls_back_to_conversation_id_when_call_id_absent(monkeypatch):
    _allow_everything(monkeypatch)
    monkeypatch.setattr(
        handler.httpx, "post", lambda *a, **k: _FakeResponse({"conversation_id": "conv_xyz"})
    )
    resp = handler._handle_demo_call(_event())
    body = json.loads(resp["body"])
    assert body["call_id"] == "conv_xyz"


def test_outbound_api_error_returns_502(monkeypatch):
    _allow_everything(monkeypatch)

    def _raise(*a, **k):
        raise ConnectionError("network down")

    monkeypatch.setattr(handler.httpx, "post", _raise)
    resp = handler._handle_demo_call(_event())
    assert resp["statusCode"] == 502


def test_posts_correct_agent_id_and_phone_to_elevenlabs(monkeypatch):
    _allow_everything(monkeypatch)
    captured = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse({"call_id": "call_1"})

    monkeypatch.setattr(handler.httpx, "post", _fake_post)
    handler._handle_demo_call(_event(phone="(202) 555-1234"))

    assert "phone-123" in captured["url"]
    assert captured["json"]["agent_id"] == handler._BEACON_AGENT_ID
    assert captured["json"]["to_number"] == "+12025551234"
    assert captured["headers"]["xi-api-key"] == "test-key"
