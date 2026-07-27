"""
Enforcement Profile invariants (spec-maturity release).

These tests do NOT introduce new behavior. They pin the enforcement behavior
that already exists in src/nhid_policy_engine_v1.py so that the newly written
Chapter 10 (Enforcement Profile / Ladder / Consequence Matrix / CAS Authority
Boundary) stays true to the reference implementation.

Coverage:
  1. PolicyAction vocabulary stability (guards against an accidental 6th action)
  2. Enforcement ladder precedence
  3. Multiple simultaneous control failures
  4. CAS cannot override a PolicyDecision
  5. PolicyDecision serialization contract
"""
from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass

import pytest

from src.nhid_policy_engine_v1 import (
    PolicyAction,
    PolicyDecision,
    evaluate_all,
)
from src.nhid_cas import compute_cas, compute_nocf, NOCFInputs

EXPECTED_VOCABULARY = {
    "DISCLOSE_IDENTITY",
    "ESCALATE_HUMAN",
    "DENY_DATA",
    "CONTINUE_AI",
    "LOG_ONLY",
}


# ── helpers ────────────────────────────────────────────────────────────────

def _audit_fields() -> dict:
    """Full ATR-01 required field set so ATR-01 returns CONTINUE_AI and does
    not add LOG_ONLY noise (used when we want to isolate a different control)."""
    return {
        "event_id": "evt-1",
        "timestamp": "2026-07-27T15:00:00Z",
        "session_id": "sess-1",
        "request_id": "req-1",
        "event_type": "turn",
        "actor_id": "agent-1",
        "state_before": "OPEN",
        "state_after": "OPEN",
        "replay_mode": False,
        "external_calls_cached": True,
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
    }


def _event(*, governance: dict, speech: str = "", counterparty: str = "human_operator",
           with_audit: bool = True) -> dict:
    ev: dict = {
        "counterparty_type": counterparty,
        "healthcare_governance": governance,
        "input_payload": {"speech_text": speech},
    }
    if with_audit:
        ev.update(_audit_fields())
    return ev


# ── 1. PolicyAction vocabulary stability ───────────────────────────────────

def test_policyaction_vocabulary_is_exactly_the_five_values():
    """A sixth action must never appear silently — that would be a 6th control
    in disguise. This is the tripwire for the five-control invariant."""
    assert {a.value for a in PolicyAction} == EXPECTED_VOCABULARY
    assert len(PolicyAction) == 5


def test_policyaction_values_are_stable_uppercase_strings():
    for action in PolicyAction:
        assert isinstance(action.value, str)
        assert action.value == action.name  # value mirrors name, no drift


# ── 2. Enforcement ladder precedence ───────────────────────────────────────

def test_ladder_deny_data_dominates_escalate_human():
    # PDX-01 fail (PHI in fields, no disclosure) + EIT-01 fail (escalation, no path)
    gov = {"disclosure_timestamp": None, "phi_accessed": ["member_id"],
           "escalation_path_available": False}
    ev = _event(governance=gov, speech="I need to speak to a human")
    session = {"escalation_path_available": False, "turn_count": 1}
    decision = evaluate_all(session, ev)
    assert decision.action == PolicyAction.DENY_DATA


def test_ladder_escalate_human_dominates_disclose_identity():
    # IDG-01 fail (no disclosure) + EIT-01 fail (escalation, no path), NO PHI
    gov = {"disclosure_timestamp": None, "phi_accessed": []}
    ev = _event(governance=gov, speech="please transfer me to a representative")
    session = {"escalation_path_available": False, "turn_count": 1}
    decision = evaluate_all(session, ev)
    assert decision.action == PolicyAction.ESCALATE_HUMAN


def test_ladder_disclose_identity_dominates_log_only():
    # IDG-01 fail (DISCLOSE_IDENTITY) + ATR-01 fail (LOG_ONLY, audit omitted)
    gov = {"disclosure_timestamp": None, "phi_accessed": []}
    ev = _event(governance=gov, speech="hello", with_audit=False)
    session = {"turn_count": 0}
    decision = evaluate_all(session, ev)
    assert decision.action == PolicyAction.DISCLOSE_IDENTITY


def test_ladder_log_only_dominates_continue_ai():
    # Clean disclosure (IDG/PDX/EIT continue) + ATR-01 fail (LOG_ONLY)
    gov = {"disclosure_timestamp": "2026-07-27T15:00:00Z",
           "identity_assertion_text": "I am an automated system.",
           "phi_accessed": []}
    ev = _event(governance=gov, speech="thanks", with_audit=False)
    session = {"turn_count": 1}
    decision = evaluate_all(session, ev)
    assert decision.action == PolicyAction.LOG_ONLY


# ── 3. Multiple simultaneous control failures ──────────────────────────────

def test_multiple_simultaneous_failures_merge_all_violations():
    gov = {"disclosure_timestamp": None, "phi_accessed": ["member_id"],
           "escalation_path_available": False}
    ev = _event(governance=gov, speech="I need to speak to a human")
    session = {"escalation_path_available": False, "turn_count": 1}
    decision = evaluate_all(session, ev)
    rule_ids = {v.rule_id for v in decision.violations}
    # IDG-01 (undisclosed), PDX-01 (PHI pre-disclosure), EIT-01 (no escalation path)
    assert {"IDG-01", "PDX-01", "EIT-01"}.issubset(rule_ids)
    # Composite action is still the single most-restrictive one, not a merge
    assert decision.action == PolicyAction.DENY_DATA


def test_composite_action_is_one_of_the_vocabulary():
    gov = {"disclosure_timestamp": None, "phi_accessed": ["npi"]}
    ev = _event(governance=gov, speech="member id please")
    decision = evaluate_all({"turn_count": 1}, ev)
    assert decision.action in set(PolicyAction)


# ── 4. CAS cannot override a PolicyDecision ────────────────────────────────

def test_evaluate_all_does_not_consume_cas():
    """Structural proof: the decision authority cannot read CAS, so CAS can
    never influence the emitted PolicyAction."""
    params = set(inspect.signature(evaluate_all).parameters)
    assert params == {"session", "event"}


def test_cas_result_is_score_only_and_carries_no_action():
    nocf = compute_nocf(NOCFInputs(
        entity_match_rate=0.9, intent_accuracy=0.9, domain_hit_rate=0.9,
        successful_actions=8, attempted_actions=10,
        call_drop_rate=0.0, audio_corruption_rate=0.0, tool_failure_rate=0.0,
        latency_ms=800.0,
        hallucination_risk=0.1, pii_leakage_risk=0.1, identity_ambiguity_risk=0.1,
    ))
    cas = compute_cas(iaf=True, nocf_result=nocf, trace={})
    assert "cas" in cas and "tier" in cas
    # CAS is a measurement: it must not carry any enforcement action.
    assert "action" not in cas
    assert not any(str(v) in EXPECTED_VOCABULARY for v in cas.values())


def test_low_cas_does_not_downgrade_a_deny_decision():
    """A DENY_DATA decision stays DENY_DATA regardless of any CAS value — the
    decision is computed by the controls, not by the score."""
    gov = {"disclosure_timestamp": None, "phi_accessed": ["member_id"]}
    ev = _event(governance=gov, speech="member id please")
    decision = evaluate_all({"turn_count": 1}, ev)
    assert decision.action == PolicyAction.DENY_DATA
    # A deliberately low CAS exists independently and does not touch the action.
    low_nocf = compute_nocf(NOCFInputs(
        entity_match_rate=0.1, intent_accuracy=0.1, domain_hit_rate=0.1,
        successful_actions=1, attempted_actions=10,
        call_drop_rate=0.5, audio_corruption_rate=0.3, tool_failure_rate=0.3,
        latency_ms=2400.0,
        hallucination_risk=0.9, pii_leakage_risk=0.9, identity_ambiguity_risk=0.9,
    ))
    low_cas = compute_cas(iaf=False, nocf_result=low_nocf, trace={})
    assert low_cas["cas"] < 0.5  # low, review/deny tier
    assert decision.action == PolicyAction.DENY_DATA  # unchanged


# ── 5. PolicyDecision serialization contract ───────────────────────────────

def test_policydecision_serialization_contract():
    gov = {"disclosure_timestamp": None, "phi_accessed": []}
    decision = evaluate_all({"turn_count": 0}, _event(governance=gov))
    assert is_dataclass(decision)
    field_names = {f.name for f in fields(PolicyDecision)}
    required = {"action", "reason_code", "policy_version", "violations",
                "next_state", "twiml_fallback", "gather_speech"}
    assert required.issubset(field_names)
    # The public wire form uses action.value + reason_code.
    assert isinstance(decision.action.value, str)
    assert isinstance(decision.reason_code, str) and decision.reason_code
    assert isinstance(decision.next_state, str)


def test_policydecision_violations_are_structured():
    gov = {"disclosure_timestamp": None, "phi_accessed": ["member_id"]}
    decision = evaluate_all({"turn_count": 1}, _event(governance=gov, speech="member id"))
    assert decision.violations, "expected at least one violation"
    for v in decision.violations:
        assert v.rule_id and isinstance(v.rule_id, str)
        assert v.description and isinstance(v.description, str)
        assert v.severity.value in {"critical", "major", "minor"}
