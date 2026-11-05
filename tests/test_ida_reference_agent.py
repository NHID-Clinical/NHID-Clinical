"""Ida, the reference caller-agent, and her proof of authority at the payer gate.

The gate (`functions.handler.gate_turn`) accepts an optional NHID-Auth passport
and a proof of possession. When one is presented, DLG-01 runs against the
payer's own trust anchors, bound to the call, with a fresh gate-issued
challenge, and the delegation's scope constrains PDX-01.

These tests check the wiring: a valid, call-bound, in-scope passport with a
proof gets through, and each way of getting it wrong is denied. They assert
the gate's reshaping and never restate control semantics.
"""
import os
import sys
from dataclasses import asdict, replace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import nhid_event_store  # noqa: E402
from functions import handler  # noqa: E402
from src.gate_challenges import CHALLENGES, ChallengeStore  # noqa: E402
from src.reference_agent import (  # noqa: E402
    ENV_AGENT_KEY, ENV_PRACTICE_KEY, PracticeIssuer, ReferenceAgentSigner,
    load_definition, passport_to_dict, private_key_to_b64,
)

CLAIM_TURN = {
    "turn": "The member ID is RVD-204-7731 and the claim number is 9921-0417. What's the status?",
    "disclosed": "true",
    "turn_index": "2",
    "heard": "Go ahead.",
}
PRIOR_AUTH_TURN = "The member ID is RVD-204-7731. What's the status of prior auth number PA-55120934?"


@pytest.fixture
def practice(monkeypatch):
    issuer = PracticeIssuer(key=Ed25519PrivateKey.generate())
    monkeypatch.setenv("NHID_TRUST_ANCHORS", issuer.trust_anchor_entry())
    monkeypatch.setattr(nhid_event_store, "is_delegation_revoked", lambda _id: False)
    return issuer


@pytest.fixture
def ida(practice):
    return ReferenceAgentSigner(agent_key=Ed25519PrivateKey.generate(), issuer=practice)


def _present(signer, call_id, *, passport=None, proof_nonce=None, extra=None):
    """Present a passport for `call_id`, answering whatever challenge is live."""
    passport = passport or signer.passport_for(call_id)
    params = {**CLAIM_TURN, "session_id": call_id, "passport": passport_to_dict(passport)}
    nonce = proof_nonce if proof_nonce is not None else CHALLENGES.current(call_id)
    if nonce:
        proof = signer.manager.create_presentation_proof(signer.agent_key, passport.delegation, nonce)
        params["presentation_proof"] = asdict(proof)
    params.update(extra or {})
    return handler.gate_turn(params)


def _denied_by_dlg01(status, body):
    assert status == 200, body
    assert body["delegation_checked"] is True
    assert body["allowed"] is False
    assert body["action"] == "DENY_DATA"
    assert body["reason_code"].startswith("DLG01_"), body["reason_code"]


# ── pass ─────────────────────────────────────────────────────────────────────

def test_valid_call_bound_passport_with_proof_is_allowed(ida):
    status, body = ida.gate({**CLAIM_TURN, "session_id": "CA-pass"},
                            get_challenge=handler.gate_challenge, payer_gate=handler.gate_turn)
    assert status == 200, body
    assert body["delegation_checked"] is True
    assert body["allowed"] is True
    assert body["actor_id"] == "ida-reference-agent"


def test_no_passport_leaves_the_gate_unchanged(practice):
    status, body = handler.gate_turn({**CLAIM_TURN, "session_id": "CA-plain"})
    assert status == 200, body
    assert body["delegation_checked"] is False


# ── fail ─────────────────────────────────────────────────────────────────────

def test_passport_for_another_call_is_denied(ida):
    handler.gate_challenge({"session_id": "CA-other"})
    _denied_by_dlg01(*_present(ida, "CA-other", passport=ida.passport_for("CA-original")))


def test_expired_passport_is_denied(ida, practice):
    expired = practice.delegate(ida.agent_id, ida.agent_key, "CA-expired", ttl_seconds=-60)
    handler.gate_challenge({"session_id": "CA-expired"})
    _denied_by_dlg01(*_present(ida, "CA-expired", passport=expired))


def test_revoked_passport_is_denied(ida, monkeypatch):
    monkeypatch.setattr(nhid_event_store, "is_delegation_revoked", lambda _id: True)
    handler.gate_challenge({"session_id": "CA-revoked"})
    status, body = _present(ida, "CA-revoked")
    _denied_by_dlg01(status, body)
    assert body["reason_code"] == "DLG01_REVOKED"


def test_request_outside_the_delegated_scope_is_denied(ida):
    """Ida's delegation covers claim status, not a prior authorization."""
    handler.gate_challenge({"session_id": "CA-scope"})
    status, body = _present(ida, "CA-scope", extra={"turn": PRIOR_AUTH_TURN})
    assert status == 200, body
    assert body["delegation_checked"] is True
    assert body["allowed"] is False
    assert body["action"] == "DENY_DATA"
    assert body["reason_code"] == "PDX01_SCOPE_NOT_AUTHORIZED"
    # The same sentence without a passport is allowed: scope is what denied it.
    _, plain = handler.gate_turn({**CLAIM_TURN, "session_id": "CA-scope-plain",
                                  "turn": PRIOR_AUTH_TURN})
    assert plain["allowed"] is True


def test_passport_without_a_challenge_is_denied(ida):
    status, body = _present(ida, "CA-no-challenge-issued")
    _denied_by_dlg01(status, body)


def test_passport_without_a_proof_is_denied(ida):
    handler.gate_challenge({"session_id": "CA-no-proof"})
    passport = ida.passport_for("CA-no-proof")
    status, body = handler.gate_turn({**CLAIM_TURN, "session_id": "CA-no-proof",
                                      "passport": passport_to_dict(passport)})
    _denied_by_dlg01(status, body)


def test_proof_over_a_stale_challenge_is_denied(ida):
    handler.gate_challenge({"session_id": "CA-stale"})
    old = CHALLENGES.current("CA-stale")
    handler.gate_challenge({"session_id": "CA-stale"})  # replaces the old one
    _denied_by_dlg01(*_present(ida, "CA-stale", proof_nonce=old))


def test_proof_signed_by_another_key_is_denied(ida, practice):
    thief = ReferenceAgentSigner(agent_key=Ed25519PrivateKey.generate(), issuer=practice)
    handler.gate_challenge({"session_id": "CA-forged"})
    _denied_by_dlg01(*_present(thief, "CA-forged", passport=ida.passport_for("CA-forged")))


def test_passport_from_an_untrusted_practice_is_denied(ida):
    stranger = PracticeIssuer(key=Ed25519PrivateKey.generate())
    other = ReferenceAgentSigner(agent_key=ida.agent_key, issuer=stranger)
    handler.gate_challenge({"session_id": "CA-stranger"})
    _denied_by_dlg01(*_present(other, "CA-stranger"))


def test_tampered_scope_is_denied(ida):
    passport = ida.passport_for("CA-tamper")
    widened = replace(passport, delegation=replace(passport.delegation,
                                                   scope=["claim_status", "prior_auth"]))
    handler.gate_challenge({"session_id": "CA-tamper"})
    _denied_by_dlg01(*_present(ida, "CA-tamper", passport=widened))


def test_no_trust_anchors_is_503_never_a_silent_pass(ida, monkeypatch):
    monkeypatch.delenv("NHID_TRUST_ANCHORS", raising=False)
    passport = ida.passport_for("CA-unconfigured")
    status, body = handler.gate_turn({**CLAIM_TURN, "session_id": "CA-unconfigured",
                                      "passport": passport_to_dict(passport)})
    assert status == 503
    assert "NHID_TRUST_ANCHORS" in body["error"]


def test_malformed_passport_is_400(practice):
    status, body = handler.gate_turn({**CLAIM_TURN, "session_id": "CA-bad",
                                      "passport": "{not json"})
    assert status == 400


# ── challenge route ─────────────────────────────────────────────────────────

def test_challenge_requires_a_session_id():
    assert handler.gate_challenge({})[0] == 400
    assert handler.gate_challenge({"session_id": "x" * 201})[0] == 400


def test_challenge_is_fresh_each_time():
    _, first = handler.gate_challenge({"session_id": "CA-fresh"})
    _, second = handler.gate_challenge({"session_id": "CA-fresh"})
    assert first["verifier_nonce"] != second["verifier_nonce"]
    assert CHALLENGES.current("CA-fresh") == second["verifier_nonce"]


def test_challenge_expires():
    now = [1000.0]
    store = ChallengeStore(ttl_seconds=10, clock=lambda: now[0])
    nonce, expires = store.issue("CA-ttl")
    assert store.current("CA-ttl") == nonce and expires == 1010
    now[0] = 1011.0
    assert store.current("CA-ttl") is None


def test_challenge_route_through_lambda():
    resp = handler.lambda_handler({"httpMethod": "POST", "path": "/v1/gate/challenge",
                                   "queryStringParameters": {"session_id": "CA-lambda"}}, None)
    assert resp["statusCode"] == 200
    assert "verifier_nonce" in resp["body"]


# ── Ida's route ─────────────────────────────────────────────────────────────

def test_ida_gate_is_503_without_credentials(monkeypatch):
    monkeypatch.setattr(handler, "_IDA_SIGNER", None)
    monkeypatch.delenv(ENV_AGENT_KEY, raising=False)
    monkeypatch.delenv(ENV_PRACTICE_KEY, raising=False)
    status, body = handler.ida_gate({**CLAIM_TURN, "session_id": "CA-ida"})
    assert status == 503


def test_ida_gate_end_to_end_from_environment(practice, monkeypatch):
    monkeypatch.setattr(handler, "_IDA_SIGNER", None)
    monkeypatch.setenv(ENV_AGENT_KEY, private_key_to_b64(Ed25519PrivateKey.generate()))
    monkeypatch.setenv(ENV_PRACTICE_KEY, private_key_to_b64(practice.key))
    status, body = handler.ida_gate({**CLAIM_TURN, "session_id": "CA-ida-env"})
    assert status == 200, body
    assert body["delegation_checked"] is True and body["allowed"] is True


def test_ida_gate_requires_a_session_id(practice, monkeypatch):
    monkeypatch.setattr(handler, "_IDA_SIGNER", None)
    monkeypatch.setenv(ENV_AGENT_KEY, private_key_to_b64(Ed25519PrivateKey.generate()))
    monkeypatch.setenv(ENV_PRACTICE_KEY, private_key_to_b64(practice.key))
    assert handler.ida_gate({**CLAIM_TURN})[0] == 400


# ── the agent definition ────────────────────────────────────────────────────

def test_ida_definition_loads_and_discloses_first():
    from src.nhid_policy_engine_v1 import _asserts_nonhuman_identity
    ida = load_definition("ida")
    assert ida.name.startswith("Ida")
    assert ida.system_prompt
    assert _asserts_nonhuman_identity(ida.first_message), ida.first_message


def test_ida_first_message_places_the_call():
    first = load_definition("ida").first_message.lower()
    assert "calling" in first
    for receiver_voice in ("thank you for calling", "how can i help", "what's your member id"):
        assert receiver_voice not in first
