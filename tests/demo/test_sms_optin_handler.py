"""
Tests for functions/handler.py::_handle_demo_sms_optin() — the web opt-in that
texts the starter-pack link. Website demo feature, NOT the NHID-Clinical
governance framework (lives under tests/demo/, excluded from the framework's
pytest tests/ baseline — see pytest.ini).

Monkeypatches handler._verify_turnstile, rate_limiter.check_and_increment,
and twilio_sms.send_sms — no real network calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import functions.handler as handler  # noqa: E402
from functions import rate_limiter, twilio_sms  # noqa: E402


def _event(phone: str = "+12025551234", token: str = "good-token", consent: bool = True) -> dict:
    body = {"phone": phone, "turnstile_token": token}
    if consent is not None:
        body["consent"] = consent
    return {
        "body": json.dumps(body),
        "requestContext": {"identity": {"sourceIp": "203.0.113.5"}},
    }


def _allow_everything(monkeypatch, sent: list | None = None) -> None:
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: True)
    monkeypatch.setattr(rate_limiter, "check_and_increment", lambda *a, **k: True)
    monkeypatch.setenv(twilio_sms.ACCOUNT_SID_ENV, "AC-test")
    monkeypatch.setenv(twilio_sms.AUTH_TOKEN_ENV, "token-test")
    monkeypatch.setenv(twilio_sms.SMS_FROM_ENV, "+15550000000")

    def _fake_send(to, body, **kwargs):
        if sent is not None:
            sent.append((to, body))
        return True

    monkeypatch.setattr(twilio_sms, "send_sms", _fake_send)


def test_missing_body_rejected():
    resp = handler._handle_demo_sms_optin({})
    assert resp["statusCode"] == 400


def test_missing_consent_rejected_before_any_other_work(monkeypatch):
    called = []
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: called.append("ts") or True)
    monkeypatch.setattr(rate_limiter, "check_and_increment", lambda *a, **k: called.append("rl") or True)
    resp = handler._handle_demo_sms_optin(_event(consent=False))
    assert resp["statusCode"] == 400
    assert called == []  # no CAPTCHA/rate-limit work without consent


def test_failed_turnstile_rejected(monkeypatch):
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: False)
    resp = handler._handle_demo_sms_optin(_event())
    assert resp["statusCode"] == 400


def test_invalid_phone_rejected(monkeypatch):
    _allow_everything(monkeypatch)
    resp = handler._handle_demo_sms_optin(_event(phone="123"))
    assert resp["statusCode"] == 400


def test_ip_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: True)
    _allow_everything(monkeypatch)
    monkeypatch.setattr(
        rate_limiter, "check_and_increment",
        lambda key, **k: not key.startswith("smsoptin-ip:"),
    )
    resp = handler._handle_demo_sms_optin(_event())
    assert resp["statusCode"] == 429


def test_not_configured_returns_503(monkeypatch):
    monkeypatch.setattr(handler, "_verify_turnstile", lambda token: True)
    monkeypatch.setattr(rate_limiter, "check_and_increment", lambda *a, **k: True)
    monkeypatch.delenv(twilio_sms.ACCOUNT_SID_ENV, raising=False)
    monkeypatch.delenv(twilio_sms.AUTH_TOKEN_ENV, raising=False)
    monkeypatch.delenv(twilio_sms.SMS_FROM_ENV, raising=False)
    resp = handler._handle_demo_sms_optin(_event())
    assert resp["statusCode"] == 503


def test_successful_opt_in_sends_starter_pack(monkeypatch):
    sent: list = []
    _allow_everything(monkeypatch, sent=sent)
    resp = handler._handle_demo_sms_optin(_event(phone="(202) 555-1234"))
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["status"] == "sent"
    assert len(sent) == 1
    to, body = sent[0]
    assert to == "+12025551234"
    assert "shadow-evaluation-guide.html" in body
    assert "STOP" in body  # carrier-required opt-out language


def test_send_failure_returns_502(monkeypatch):
    _allow_everything(monkeypatch)
    monkeypatch.setattr(twilio_sms, "send_sms", lambda *a, **k: False)
    resp = handler._handle_demo_sms_optin(_event())
    assert resp["statusCode"] == 502
