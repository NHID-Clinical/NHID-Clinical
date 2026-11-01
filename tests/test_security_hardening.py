"""
Security hardening found by the readiness audit (Nov 2026).

1. ``/debug/replay/{session_id}`` returned a session's full forensic trace,
   transcripts included, with no authentication: the voice app is mounted
   beside the API-key routers, not behind them.
2. ``/voice/incoming`` and ``/voice/process`` accepted any POST: nothing checked
   Twilio's ``X-Twilio-Signature``.
3. One shared ``NHID_API_KEY`` could not tell customers apart, so every key
   holder could export every session's audit events.

The signature tests pin Twilio's documented example; the implementation was
also cross-checked against twilio-python 9.3.0's ``RequestValidator`` on 300
random cases during development (the package is not a dependency).
"""
from __future__ import annotations

import os
import sys
import types

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:  # same shim as tests/test_framework_auth.py: main -> app -> llm -> openai
    import openai  # noqa: F401
except ImportError:  # pragma: no cover
    _openai = types.ModuleType("openai")

    class _OpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _OpenAI
    sys.modules["openai"] = _openai

import main  # noqa: E402
import nhid_audit_export  # noqa: E402
from nhid_api_auth import DEFAULT_TENANT, authenticate, hash_api_key  # noqa: E402
from src.webhook_security import signature_is_valid, twilio_signature  # noqa: E402

KEY_A, KEY_B = "key-for-payer-a", "key-for-payer-b"
TOKEN = "twilio-auth-token-under-test"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("NHID_API_KEY", "NHID_API_KEYS", "TWILIO_AUTH_TOKEN", "DEPLOYMENT_MODE",
                "NHID_ENABLE_DEBUG_REPLAY", "NHID_PUBLIC_BASE_URL",
                "AUDIT_SECRET_KEY_B64", "AUDIT_ANCHOR_PATH", "AUDIT_ANCHOR_KEY_B64"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("AUDIT_STORE_PATH", str(tmp_path / "audit.db"))
    nhid_audit_export.reset_stores()
    yield
    nhid_audit_export.reset_stores()


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def two_tenants(monkeypatch):
    monkeypatch.setenv("NHID_API_KEYS",
                       f'{{"payer-a": "{hash_api_key(KEY_A)}", "payer-b": "{hash_api_key(KEY_B)}"}}')


# ── Twilio signatures ────────────────────────────────────────────────────────

def test_signature_matches_twilios_documented_example():
    url = "https://mycompany.com/myapp.php?foo=1&bar=2"
    params = {"CallSid": "CA1234567890ABCDE", "Caller": "+12349013030", "Digits": "1234",
              "From": "+12349013030", "To": "+18005551212"}
    assert twilio_signature(url, params, "12345") == "0/KCTR6DLpKmkAf8muzZqo1nDgQ="
    assert signature_is_valid(url, params, "0/KCTR6DLpKmkAf8muzZqo1nDgQ=", "12345")


def test_signature_accepts_the_url_with_or_without_its_default_port():
    params = {"CallSid": "CA1"}
    sig = twilio_signature("https://ex.com:443/voice/incoming", params, TOKEN)
    assert signature_is_valid("https://ex.com/voice/incoming", params, sig, TOKEN)


@pytest.mark.parametrize("change", ["param", "url", "token", "empty"])
def test_any_change_breaks_the_signature(change):
    url, params = "https://ex.com/voice/incoming", {"CallSid": "CA1", "From": "+15555550142"}
    sig = twilio_signature(url, params, TOKEN)
    if change == "param":
        assert not signature_is_valid(url, {**params, "From": "+15555550199"}, sig, TOKEN)
    elif change == "url":
        assert not signature_is_valid("https://ex.com/voice/process", params, sig, TOKEN)
    elif change == "token":
        assert not signature_is_valid(url, params, sig, "another-token")
    else:
        assert not signature_is_valid(url, params, "", TOKEN)


def test_unsigned_webhook_is_refused_when_a_token_is_set(client, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    r = client.post("/voice/voice/incoming", data={"CallSid": "CA-forged"})
    assert r.status_code == 403


def test_forged_signature_is_refused(client, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    data = {"CallSid": "CA-forged"}
    forged = twilio_signature("http://testserver/voice/voice/incoming", data, "wrong-token")
    r = client.post("/voice/voice/incoming", data=data, headers={"X-Twilio-Signature": forged})
    assert r.status_code == 403


def test_correctly_signed_webhook_passes_the_check(client, monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("NHID_PUBLIC_BASE_URL", "https://voice.example.org")
    data = {"CallSid": "CA-signed", "From": "+15555550142"}
    sig = twilio_signature("https://voice.example.org/voice/voice/incoming", data, TOKEN)
    r = client.post("/voice/voice/incoming", data=data, headers={"X-Twilio-Signature": sig})
    assert r.status_code != 403


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_strict_modes_refuse_webhooks_without_a_configured_token(client, monkeypatch, mode):
    monkeypatch.setenv("DEPLOYMENT_MODE", mode)
    r = client.post("/voice/voice/process", data={"CallSid": "CA1"})
    assert r.status_code == 503
    assert "TWILIO_AUTH_TOKEN" in r.json()["detail"]


# ── Debug replay ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", ["staging", "production"])
def test_debug_replay_does_not_exist_in_strict_modes(client, monkeypatch, mode):
    monkeypatch.setenv("DEPLOYMENT_MODE", mode)
    monkeypatch.setenv("NHID_API_KEY", KEY_A)
    r = client.get("/voice/debug/replay/any-session", headers={"X-API-Key": KEY_A})
    assert r.status_code == 404


def test_enabled_debug_replay_still_needs_a_key(client, monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_MODE", "production")
    monkeypatch.setenv("NHID_ENABLE_DEBUG_REPLAY", "1")
    monkeypatch.setenv("NHID_API_KEY", KEY_A)
    assert client.get("/voice/debug/replay/s1").status_code == 401
    assert client.get("/voice/debug/replay/s1", headers={"X-API-Key": "wrong"}).status_code == 403
    assert client.get("/voice/debug/replay/s1", headers={"X-API-Key": KEY_A}).status_code not in (401, 403, 404)


# ── Per-tenant API keys ──────────────────────────────────────────────────────

def test_each_key_authenticates_as_its_own_tenant(monkeypatch):
    two_tenants(monkeypatch)
    assert authenticate(KEY_A) == "payer-a"
    assert authenticate(KEY_B) == "payer-b"


def test_legacy_single_key_is_the_default_tenant(monkeypatch):
    monkeypatch.setenv("NHID_API_KEY", KEY_A)
    assert authenticate(KEY_A) == DEFAULT_TENANT


@pytest.mark.parametrize("table", [
    '{"payer-a": "plaintext-key"}',
    '{"Payer A": "sha256:' + "0" * 64 + '"}',
    "[]",
    "not json",
])
def test_a_malformed_key_table_fails_closed(client, monkeypatch, table):
    monkeypatch.setenv("NHID_API_KEYS", table)
    monkeypatch.setenv("NHID_API_KEY", KEY_A)   # even the legacy key stops working
    r = client.get("/v1/compliance/states", headers={"X-API-Key": KEY_A})
    assert r.status_code == 503


def test_tenant_keys_protect_routes(client, monkeypatch):
    two_tenants(monkeypatch)
    assert client.get("/v1/compliance/states").status_code == 401
    assert client.get("/v1/compliance/states", headers={"X-API-Key": "nope"}).status_code == 403
    assert client.get("/v1/compliance/states", headers={"X-API-Key": KEY_A}).status_code == 200


def test_one_tenant_cannot_export_anothers_audit_session(client, monkeypatch):
    two_tenants(monkeypatch)
    event = {"session_id": "sess-1", "agent_id": "agent-a", "event_type": "disclosure"}
    assert client.post("/v1/audit/log", json=event, headers={"X-API-Key": KEY_A}).status_code == 200
    mine = client.get("/v1/audit/export/sess-1", headers={"X-API-Key": KEY_A})
    theirs = client.get("/v1/audit/export/sess-1", headers={"X-API-Key": KEY_B})
    assert mine.status_code == 200
    assert theirs.status_code == 404


def test_stored_keys_are_hashes_never_plaintext():
    assert hash_api_key("secret").startswith("sha256:")
    assert "secret" not in hash_api_key("secret")
