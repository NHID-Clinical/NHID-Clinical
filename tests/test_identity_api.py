"""Tests for the /v1/identity/verify-passport and /v1/identity/revoke-passport
routes wiring src/agent_identity.py's NHID-Auth v2 library into the conformance
API, plus durable (SQLite-backed) revocation that survives across stateless
Lambda invocations."""
import base64
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import nhid_event_store as store
from functions.handler import lambda_handler
from src.agent_identity import AgentIdentityManager


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_nhid.db"
    monkeypatch.setattr(store, "DB_PATH", db_file)
    yield


def _make_passport_body(scope=None, ttl=86400, npi="1234567890", call_sid=""):
    m = AgentIdentityManager()
    provider_priv, provider_pub = m.generate_agent_keys()
    agent_priv, agent_pub = m.generate_agent_keys()
    delegation = m.create_delegation(
        provider_priv, "agent-001", agent_pub, scope or ["eligibility"],
        ttl_seconds=ttl, call_sid=call_sid, provider_npi=npi,
    )
    sig = m.sign_delegation(provider_priv, delegation)
    passport = m.create_agent_passport(delegation, sig, agent_priv)
    from dataclasses import asdict
    return {
        "delegation": asdict(delegation),
        "signature_b64": passport.signature_b64,
        "agent_signature_b64": passport.agent_signature_b64,
        "provider_public_key_b64": m.public_key_to_b64(provider_pub),
    }, delegation.delegation_id


def _make_event(path, body):
    return {"httpMethod": "POST", "path": path, "body": json.dumps(body)}


class TestVerifyPassport:
    def test_valid_passport_verifies(self):
        body, _ = _make_passport_body()
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", body), None)
        assert resp["statusCode"] == 200
        result = json.loads(resp["body"])
        assert result["valid"] is True
        assert result["agent_id"] == "agent-001"
        assert result["provider_npi"] == "1234567890"

    def test_missing_fields_returns_400(self):
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", {}), None)
        assert resp["statusCode"] == 400

    def test_tampered_signature_invalid(self):
        body, _ = _make_passport_body()
        body["signature_b64"] = base64.b64encode(b"not-a-real-signature-00000000").decode()
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False

    def test_scope_violation(self):
        body, _ = _make_passport_body(scope=["eligibility"])
        body["required_scope"] = ["claim_status"]
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False
        assert "SCOPE_VIOLATION" in result["reason"]

    def test_revoked_delegation_fails_durably(self):
        body, delegation_id = _make_passport_body()
        revoke_resp = lambda_handler(
            _make_event("/v1/identity/revoke-passport", {"delegation_id": delegation_id}), None
        )
        assert revoke_resp["statusCode"] == 200

        # A fresh AgentIdentityManager() per invocation has empty in-memory
        # revocation state — the durable store is what must catch this.
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False
        assert result["reason"] == "ERR_REVOKED"


class TestRevokePassport:
    def test_revoke_requires_delegation_id(self):
        resp = lambda_handler(_make_event("/v1/identity/revoke-passport", {}), None)
        assert resp["statusCode"] == 400

    def test_revoke_persists(self):
        lambda_handler(_make_event("/v1/identity/revoke-passport", {"delegation_id": "dlg-1"}), None)
        assert store.is_delegation_revoked("dlg-1") is True
        assert store.is_delegation_revoked("dlg-2") is False
