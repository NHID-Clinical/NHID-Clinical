"""Regression tests for the v1.3.2 scope corrections.

Four changes are locked in here, each of which was made because the previous
behaviour claimed something the framework could not support:

1. The composite score, its trust tiers and its badges are gone. Nothing may
   reintroduce a blended score or a tier vocabulary.
2. DBC-01 ignores caller-supplied artifact flags. The flag was self-reported by
   the agent under evaluation, so it established nothing.
3. The event schema carries transcription attestation, language and
   interpreter-present, so a finding can state the precision it rests on.
4. EIT-01 can distinguish escalation requested / completed / not completed /
   outcome unknown, with unknown as a first-class answer rather than a guess.
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.nhid_policy_engine_v1 import (  # noqa: E402
    ESCALATION_COMPLETED,
    ESCALATION_NOT_COMPLETED,
    ESCALATION_NOT_REQUESTED,
    ESCALATION_OUTCOME_UNKNOWN,
    ESCALATION_STATES,
    PolicyAction,
    escalation_state,
    evaluate_dbc01,
)

ROOT = Path(__file__).resolve().parent.parent


def _event(**gov):
    return {
        "event_id": "ev-1",
        "timestamp": "2026-06-01T00:00:00Z",
        "session_id": "s-1",
        "event_type": "POLICY",
        "state_before": "DISCLOSED",
        "healthcare_governance": gov,
        "input_payload": {"speech_text": gov.pop("_speech", "")},
    }


# ── 1. The score, the tiers and the badges stay gone ────────────────────────

def test_no_composite_score_module_exists():
    assert not (ROOT / "src" / "nhid_cas.py").exists()
    assert not (ROOT / "src" / "nhid_badge_generator.py").exists()


def test_no_trust_tier_vocabulary_in_source():
    """'Verified Trust' / 'Conditional Trust' read as a certification this
    project does not issue. They must not come back anywhere in src/."""
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for phrase in ("Verified Trust", "Conditional Trust", "badge_eligible"):
            if phrase in text:
                offenders.append(f"{path.name}: {phrase}")
    assert not offenders, f"withdrawn trust-tier vocabulary reappeared: {offenders}"


def test_handler_reports_evidence_completeness_with_its_denominator():
    """What replaced the score is a fraction that states what it is over."""
    from functions.handler import _evidence_completeness

    result = _evidence_completeness({"event_id": "a", "timestamp": "b"})
    assert result["present"] == 2
    assert result["expected"] == 4
    assert result["fraction"] == 0.5
    assert "tier" not in result and "score" not in result


# ── 2. DBC-01 ignores self-reported artifact flags ──────────────────────────

def test_self_reported_artifact_flag_produces_no_finding():
    decision = evaluate_dbc01({}, _event(deceptive_artifact_flags=["fake_breathing"]))
    assert decision.action == PolicyAction.CONTINUE_AI
    assert decision.violations == []


def test_persona_claim_is_still_caught_from_what_was_said():
    decision = evaluate_dbc01(
        {}, _event(identity_assertion_text="I'm one of the nurses on our team.")
    )
    assert decision.action == PolicyAction.LOG_ONLY
    assert any(v.rule_id == "DBC-01" for v in decision.violations)


def test_artifact_flag_cannot_escalate_a_persona_finding_to_critical():
    """Even alongside a real persona match, the flag must add nothing."""
    decision = evaluate_dbc01(
        {},
        _event(
            identity_assertion_text="I'm one of the nurses on our team.",
            deceptive_artifact_flags=["fake_breathing", "fake_typing"],
        ),
    )
    assert all(v.severity.value != "critical" for v in decision.violations)
    assert decision.reason_code == "DBC01_IMPERSONATION_PHRASE_DETECTED"


# ── 3. The schema carries what a finding rests on ───────────────────────────

@pytest.fixture(scope="module")
def schema():
    return json.loads((ROOT / "schema" / "nhid_trace_schema_v1.json").read_text())


def test_schema_carries_transcription_attestation(schema):
    gov = schema["properties"]["healthcare_governance"]["properties"]
    att = gov["transcription_attestation"]
    assert set(att["properties"]["status"]["enum"]) == {"measured", "attested", "unattested"}
    assert att["required"] == ["status"]


def test_schema_carries_language_and_interpreter(schema):
    gov = schema["properties"]["healthcare_governance"]["properties"]
    assert "language" in gov
    assert "interpreter_present" in gov


def test_artifact_field_is_documented_as_ignored(schema):
    gov = schema["properties"]["healthcare_governance"]["properties"]
    desc = gov["deceptive_artifact_flags"]["description"]
    assert "IGNORED" in desc and "self-reported" in desc


# ── 4. EIT-01 distinguishes four outcomes, and admits when it cannot ────────

def test_no_request_is_not_requested():
    assert escalation_state({}, _event()) == ESCALATION_NOT_REQUESTED


def test_request_with_completion_is_completed():
    state = escalation_state(
        {}, _event(escalation_timestamp="2026-06-01T00:01:00Z", escalation_outcome="transferred")
    )
    assert state == ESCALATION_COMPLETED


def test_request_that_was_deflected_is_not_completed():
    state = escalation_state(
        {}, _event(escalation_timestamp="2026-06-01T00:01:00Z", escalation_outcome="deflected")
    )
    assert state == ESCALATION_NOT_COMPLETED


def test_request_with_no_reported_outcome_is_unknown_not_completed():
    """The governance failure this exists to expose: a request that was made and
    whose completion nobody recorded. Guessing either way invents a fact."""
    state = escalation_state({}, _event(escalation_timestamp="2026-06-01T00:01:00Z"))
    assert state == ESCALATION_OUTCOME_UNKNOWN


def test_unrecognised_outcome_is_unknown_not_completed():
    state = escalation_state(
        {}, _event(escalation_timestamp="2026-06-01T00:01:00Z", escalation_outcome="¯\\_(ツ)_/¯")
    )
    assert state == ESCALATION_OUTCOME_UNKNOWN


def test_escalation_state_never_raises():
    for bad in (None, {}, {"healthcare_governance": "not-a-dict"}):
        assert escalation_state({}, bad or {}) in ESCALATION_STATES
