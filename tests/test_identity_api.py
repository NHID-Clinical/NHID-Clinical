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


class TestVerifyPassportV1IsOnlyAConsistencyCheck:
    def test_v1_labels_its_own_answer(self):
        """The route is handed both the passport and the key to check it
        against, so `valid: true` cannot mean the issuer is trusted. The label
        exists so no integrator reads it that way."""
        body, _ = _make_passport_body()
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is True
        assert result["trust"] == "caller_supplied_key"

    def test_anyone_can_get_a_pass_from_v1(self):
        """Demonstrating why the label matters: a self-minted keypair signing a
        delegation that names any NPI verifies here, because the caller chose
        the issuer."""
        body, _ = _make_passport_body(npi="9999999999")
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is True
        assert result["provider_npi"] == "9999999999"

    def test_a_passport_naming_no_provider_is_not_valid(self):
        """`require_npi` on this route: a lone passport asserting no provider
        used to come back valid with provider_npi ''."""
        body, _ = _make_passport_body(npi="")
        resp = lambda_handler(_make_event("/v1/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False
        assert "ERR_INVALID_NPI" in result["reason"]


class TestVerifyPassportV2:
    """v2 resolves the provider key from server configuration, so its answer
    depends on who signed rather than on what the caller asserted."""

    @staticmethod
    def _anchored(monkeypatch, scope=None, npi="1234567890", call_sid="", kid=""):
        m = AgentIdentityManager()
        provider_priv, provider_pub = m.generate_agent_keys()
        agent_priv, agent_pub = m.generate_agent_keys()
        delegation = m.create_delegation(
            provider_priv, "agent-001", agent_pub, scope or ["eligibility"],
            ttl_seconds=86400, call_sid=call_sid, provider_npi=npi, kid=kid,
        )
        sig = m.sign_delegation(provider_priv, delegation)
        passport = m.create_agent_passport(delegation, sig, agent_priv)
        from dataclasses import asdict
        body = {
            "delegation": asdict(delegation),
            "signature_b64": passport.signature_b64,
            "agent_signature_b64": passport.agent_signature_b64,
        }
        anchor = f"{npi}:{m.public_key_to_b64(provider_pub)}"
        if kid:
            anchor += f":{kid}"
        monkeypatch.setenv("NHID_TRUST_ANCHORS", anchor)
        return body, delegation, agent_priv, m

    def test_an_anchored_passport_verifies(self, monkeypatch):
        body, _d, _ap, _m = self._anchored(monkeypatch)
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        assert resp["statusCode"] == 200
        result = json.loads(resp["body"])
        assert result["valid"] is True
        assert result["trust"] == "configured_trust_anchor"

    def test_an_unanchored_provider_does_not_verify(self, monkeypatch):
        """The difference from v1 in one test: the same passport that v1 passes
        fails here, because this deployment never said it trusted that NPI."""
        body, _d, _ap, _m = self._anchored(monkeypatch)
        monkeypatch.setenv("NHID_TRUST_ANCHORS", "1111111111:" + "A" * 43 + "=")
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False
        assert result["reason"] == "ERR_TRUST_ANCHOR_UNRESOLVED"

    def test_a_caller_supplied_key_is_refused_outright(self, monkeypatch):
        body, _d, _ap, _m = self._anchored(monkeypatch)
        body["provider_public_key_b64"] = "anything"
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        assert resp["statusCode"] == 400
        assert "not accepted on this route" in json.loads(resp["body"])["error"]

    def test_no_configured_anchors_is_503_not_a_pass(self, monkeypatch):
        """Unconfigured must be distinguishable from untrusted: the route
        cannot answer the question, which is not the same as answering no."""
        body, _d, _ap, _m = self._anchored(monkeypatch)
        monkeypatch.delenv("NHID_TRUST_ANCHORS", raising=False)
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        assert resp["statusCode"] == 503

    def test_malformed_anchor_configuration_is_500(self, monkeypatch):
        body, _d, _ap, _m = self._anchored(monkeypatch)
        monkeypatch.setenv("NHID_TRUST_ANCHORS", "not-a-valid-entry")
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        assert resp["statusCode"] == 500

    def test_durable_revocation_is_honoured(self, monkeypatch):
        body, delegation, _ap, _m = self._anchored(monkeypatch)
        lambda_handler(
            _make_event("/v1/identity/revoke-passport",
                        {"delegation_id": delegation.delegation_id}), None
        )
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False
        assert result["reason"] == "ERR_REVOKED"

    def test_a_kid_selects_among_a_providers_keys(self, monkeypatch):
        body, _d, _ap, _m = self._anchored(monkeypatch, kid="2026-q4")
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        assert json.loads(resp["body"])["valid"] is True

    def test_proof_of_possession_can_be_required(self, monkeypatch):
        from dataclasses import asdict
        body, delegation, agent_priv, m = self._anchored(monkeypatch)
        from src.agent_identity import new_verifier_nonce
        nonce = new_verifier_nonce()

        # Challenged with no proof: refused.
        challenged = dict(body, verifier_nonce=nonce)
        resp = lambda_handler(
            _make_event("/v2/identity/verify-passport", challenged), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False
        assert "ERR_PROOF_MISSING" in result["reason"]

        # Challenged with the agent's answer: accepted, and labelled.
        proof = m.create_presentation_proof(agent_priv, delegation, nonce)
        answered = dict(challenged, presentation_proof=asdict(proof))
        resp = lambda_handler(
            _make_event("/v2/identity/verify-passport", answered), None)
        result = json.loads(resp["body"])
        assert result["valid"] is True
        assert result["possession_proved"] is True

    def test_a_proof_from_the_wrong_key_is_refused(self, monkeypatch):
        from dataclasses import asdict
        body, delegation, _agent_priv, m = self._anchored(monkeypatch)
        from src.agent_identity import new_verifier_nonce
        nonce = new_verifier_nonce()
        thief_priv, _ = m.generate_agent_keys()
        forged = m.create_presentation_proof(thief_priv, delegation, nonce)
        resp = lambda_handler(_make_event(
            "/v2/identity/verify-passport",
            dict(body, verifier_nonce=nonce, presentation_proof=asdict(forged)),
        ), None)
        result = json.loads(resp["body"])
        assert result["valid"] is False
        assert "ERR_PROOF_MISMATCH" in result["reason"]

    def test_an_unchallenged_request_does_not_claim_possession(self, monkeypatch):
        body, _d, _ap, _m = self._anchored(monkeypatch)
        resp = lambda_handler(_make_event("/v2/identity/verify-passport", body), None)
        result = json.loads(resp["body"])
        assert result["valid"] is True
        assert result["possession_proved"] is False

    def test_a_malformed_proof_object_is_400(self, monkeypatch):
        body, _d, _ap, _m = self._anchored(monkeypatch)
        resp = lambda_handler(_make_event(
            "/v2/identity/verify-passport",
            dict(body, verifier_nonce="n", presentation_proof="not an object"),
        ), None)
        assert resp["statusCode"] == 400
