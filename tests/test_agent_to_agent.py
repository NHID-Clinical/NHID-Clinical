"""Robot to robot: Ida places the call and the payer's own AI answers it.

docs/agent-to-agent-calls.md. The canonical direction is unchanged: the
caller-agent places the call and asks for a patient's claim status. What
changes is the receiving party: an AI agent answers for the payer, not a
person. The controls still judge the CALLER. The payer's AI is the enforcement
point: it runs every caller turn through the payer's own gate
(`functions.handler.gate_turn`) and says nothing protected unless the gate
allowed the turn AND verified the caller's delegation.

Two seams:
  * `gate_turn(counterparty="ai_agent")`: the engine is told the caller is
    talking to an AI, so the bot-to-bot rule applies;
  * `src.agent_to_agent.run_call`: a whole call between a scripted caller and
    the reference payer agent, offline and deterministic.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import nhid_event_store  # noqa: E402
from functions import handler  # noqa: E402
from src import agent_to_agent as a2a  # noqa: E402
from src.reference_agent import PracticeIssuer, ReferenceAgentSigner  # noqa: E402


@pytest.fixture
def practice(monkeypatch):
    issuer = PracticeIssuer(key=Ed25519PrivateKey.generate())
    monkeypatch.setenv("NHID_TRUST_ANCHORS", issuer.trust_anchor_entry())
    monkeypatch.setattr(nhid_event_store, "is_delegation_revoked", lambda _id: False)
    return issuer


@pytest.fixture
def ida(practice):
    return ReferenceAgentSigner(agent_key=Ed25519PrivateKey.generate(), issuer=practice)


# ── the gate knows who answered ─────────────────────────────────────────────

ASK = "The member ID is RVD-204-7731 and the claim number is 9921-0417. What's the status?"


def test_the_gate_applies_the_bot_to_bot_rule_when_an_ai_answered():
    status, body = handler.gate_turn({"session_id": "CA-b2b-1", "turn": ASK,
                                      "counterparty": "ai_agent"})
    assert status == 200, body
    assert body["counterparty"] == "ai_agent"
    assert body["allowed"] is False
    assert any("Bot-to-bot" in v["description"] for v in body["violations"])


def test_the_gate_defaults_to_a_human_counterparty():
    status, body = handler.gate_turn({"session_id": "CA-b2b-2", "turn": ASK})
    assert status == 200 and body["counterparty"] == "human_operator"
    assert not any("Bot-to-bot" in v["description"] for v in body["violations"])


def test_an_unknown_counterparty_is_refused():
    status, body = handler.gate_turn({"session_id": "CA-b2b-3", "turn": ASK,
                                      "counterparty": "martian"})
    assert status == 400 and "counterparty" in body["error"]


# ── the payer's AI ──────────────────────────────────────────────────────────

def test_the_payer_agent_says_it_is_automated_before_anything_else():
    greeting = a2a.PayerAgent().greeting()
    assert "automated" in greeting.lower()
    assert "not a person" in greeting.lower()


# ── whole calls ─────────────────────────────────────────────────────────────

def test_verified_ida_gets_the_claim_status(ida):
    call = a2a.run_call(a2a.SCENARIOS["verified_ida"], signer=ida)
    assert call.outcome == "released", call.render()
    assert call.turns[0].speaker == "payer_agent"          # the payer's AI answers
    assert call.turns[1].speaker == "caller"               # Ida speaks next, and discloses
    released = [t for t in call.turns if t.speaker == "payer_agent" and t.released]
    assert len(released) == 1 and "9921-0417" in released[0].text
    assert all(t.gate["counterparty"] == "ai_agent" for t in call.turns if t.gate)


def test_an_undisclosed_bot_is_refused(ida):
    call = a2a.run_call(a2a.SCENARIOS["undisclosed_bot"], signer=None)
    assert call.outcome == "refused", call.render()
    assert not any(t.released for t in call.turns)


def test_a_disclosed_bot_without_a_delegation_is_refused():
    """Disclosure is not authorization: the gate allows the turn, the payer's
    AI still refuses, because no delegation was verified."""
    call = a2a.run_call(a2a.SCENARIOS["disclosed_no_delegation"], signer=None)
    assert call.outcome == "refused", call.render()
    ask = next(t for t in call.turns if t.speaker == "caller" and t.gate and t.gate["phi_requested"])
    assert ask.gate["delegation_checked"] is False


def test_a_delegation_from_an_untrusted_practice_is_refused(practice):
    stranger = ReferenceAgentSigner(agent_key=Ed25519PrivateKey.generate(),
                                    issuer=PracticeIssuer(key=Ed25519PrivateKey.generate()))
    call = a2a.run_call(a2a.SCENARIOS["verified_ida"], signer=stranger)
    assert call.outcome == "refused", call.render()


def test_a_request_outside_the_delegated_scope_is_refused(ida):
    call = a2a.run_call(a2a.SCENARIOS["out_of_scope"], signer=ida)
    assert call.outcome == "refused", call.render()
    assert any(t.gate and t.gate["reason_code"] == "PDX01_SCOPE_NOT_AUTHORIZED" for t in call.turns)


def test_a_caller_claiming_to_be_human_is_refused(ida):
    call = a2a.run_call(a2a.SCENARIOS["claims_to_be_human"], signer=ida)
    assert call.outcome == "refused", call.render()
    claim = call.turns[1].gate
    assert any(v["rule_id"] == "DBC-01" for v in claim["violations"])


def test_a_caller_who_asks_for_a_person_is_transferred(ida):
    call = a2a.run_call(a2a.SCENARIOS["asks_for_a_person"], signer=ida)
    assert call.outcome == "escalated", call.render()


def test_nothing_is_released_after_a_refusal(ida):
    """A refusal ends the protected part of the call: a later turn that would
    pass on its own does not reopen it."""
    call = a2a.run_call(a2a.SCENARIOS["retry_after_refusal"], signer=ida)
    assert call.outcome == "refused", call.render()
    assert not any(t.released for t in call.turns)


def test_every_scenario_is_deterministic(ida):
    for name, scenario in a2a.SCENARIOS.items():
        signer = ida if scenario.presents_delegation else None
        first = a2a.run_call(scenario, signer=signer)
        second = a2a.run_call(scenario, signer=signer)
        assert [(t.speaker, t.text) for t in first.turns] == \
               [(t.speaker, t.text) for t in second.turns], name


def test_the_cli_runs_a_call(practice, monkeypatch, capsys):
    from src import cli
    from src.reference_agent import ENV_AGENT_KEY, ENV_PRACTICE_KEY, private_key_to_b64
    monkeypatch.setenv(ENV_AGENT_KEY, private_key_to_b64(Ed25519PrivateKey.generate()))
    monkeypatch.setenv(ENV_PRACTICE_KEY, private_key_to_b64(practice.key))
    assert cli.main(["agent-to-agent", "--scenario", "verified_ida"]) == 0
    out = capsys.readouterr().out
    assert "Outcome: released" in out


def test_the_cli_mints_throwaway_demo_keys_when_none_are_set(monkeypatch, capsys):
    from src import cli
    monkeypatch.delenv("NHID_TRUST_ANCHORS", raising=False)
    monkeypatch.setattr(nhid_event_store, "is_delegation_revoked", lambda _id: False)
    assert cli.main(["agent-to-agent", "--scenario", "verified_ida"]) == 0
    assert "Outcome: released" in capsys.readouterr().out
