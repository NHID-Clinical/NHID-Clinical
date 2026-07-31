"""
Tests for src/fhir_audit_emitter.py

Verifies that build_audit_bundle produces structurally valid
FHIR R4 AuditEvent Bundles — every required R4 element present,
correct milestone selection, and correct outcome coding.

All tests are pure unit tests: no I/O, no network, no server.
"""

import pytest

from src.fhir_audit_emitter import build_audit_bundle, emit_cts_bundle, _bundle_id, _ae_id


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_session():
    return {
        "session_id": "CA1234567890abcdef1234567890abcd",
        "turn_count": 1,
        "escalation_path_available": True,
    }


@pytest.fixture
def conformant_event():
    """IDG-01 + PDX-01 pass: disclosure before PHI exchange."""
    return {
        "event_id": "550e8400-e29b-41d4-a716-446655440001",
        "timestamp": "2026-06-12T14:30:00.000Z",
        "session_id": "CA1234567890abcdef1234567890abcd",
        "request_id": "req-cts-idg01-pass",
        "event_type": "POLICY",
        "actor_id": "agent_4001krn32nmwe5t8mqzgee0w84rj",
        "counterparty_type": "human_operator",
        "state_before": "DISCLOSED",
        "state_after": "DATA_EXCHANGE_AUTHORIZED",
        "partial_failure": False,
        "boundary_violations": [],
        "healthcare_governance": {
            "disclosure_timestamp": "2026-06-12T14:30:05.000Z",
            "identity_assertion_text": (
                "Hi, this is Beacon, an AI assistant calling from a provider's office. "
                "I am not a human."
            ),
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": ["claim_number", "npi"],
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "replay_mode": "live",
        "external_calls_cached": False,
    }


@pytest.fixture
def noncompliant_event():
    """IDG-01 + PDX-01 fail: PHI before disclosure."""
    return {
        "event_id": "550e8400-e29b-41d4-a716-446655440002",
        "timestamp": "2026-06-12T15:00:00.000Z",
        "session_id": "CA9999999999abcdef9999999999abcd",
        "request_id": "req-cts-idg01-fail",
        "event_type": "POLICY",
        "actor_id": "agent_test_noncompliant",
        "counterparty_type": "human_operator",
        "state_before": "AWAITING_DISCLOSURE",
        "state_after": "GATE_BLOCKED",
        "partial_failure": True,
        "boundary_violations": [
            {"rule_id": "IDG-01", "description": "No disclosure", "severity": "critical"},
            {"rule_id": "PDX-01", "description": "PHI before disclosure", "severity": "critical"},
        ],
        "healthcare_governance": {
            "disclosure_timestamp": None,
            "identity_assertion_text": None,
            "deceptive_artifact_flags": [],
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": ["member_id", "date_of_birth"],
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "replay_mode": "live",
        "external_calls_cached": False,
    }


@pytest.fixture
def escalation_event():
    """EIT-01 triggered: caller requested human, escalation connected."""
    return {
        "event_id": "550e8400-e29b-41d4-a716-446655440003",
        "timestamp": "2026-06-12T16:00:00.000Z",
        "session_id": "CAescalation000abcdef0000abcdef00",
        "request_id": "req-cts-eit01",
        "event_type": "POLICY",
        "actor_id": "agent_4001krn32nmwe5t8mqzgee0w84rj",
        "counterparty_type": "human_operator",
        "state_before": "DISCLOSED",
        "state_after": "ESCALATING",
        "partial_failure": False,
        "boundary_violations": [],
        "healthcare_governance": {
            "disclosure_timestamp": "2026-06-12T16:00:01.000Z",
            "identity_assertion_text": "Hi, this is Beacon, an AI assistant.",
            "deceptive_artifact_flags": [],
            "escalation_timestamp": "2026-06-12T16:01:00.000Z",
            "escalation_outcome": "connected",
            "phi_accessed": [],
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "replay_mode": "live",
        "external_calls_cached": False,
    }


def _entries(bundle):
    return [e["resource"] for e in bundle["entry"]]


def _milestones(bundle):
    return {
        e["subtype"][0]["code"]
        for e in _entries(bundle)
        if e.get("subtype")
    }


# ── Test 1-3: Bundle structure ─────────────────────────────────────────────

def test_bundle_resourcetype(minimal_session, conformant_event):
    b = build_audit_bundle(minimal_session, conformant_event)
    assert b["resourceType"] == "Bundle"


def test_bundle_type_collection(minimal_session, conformant_event):
    b = build_audit_bundle(minimal_session, conformant_event)
    assert b["type"] == "collection"


def test_bundle_has_entries(minimal_session, conformant_event):
    b = build_audit_bundle(minimal_session, conformant_event)
    assert len(b["entry"]) > 0


# ── Test 4-6: All entries are valid AuditEvent shells ─────────────────────

def test_all_entries_are_audit_events(minimal_session, conformant_event):
    for entry in _entries(build_audit_bundle(minimal_session, conformant_event)):
        assert entry["resourceType"] == "AuditEvent"


def test_required_type_present(minimal_session, conformant_event):
    """R4 requires AuditEvent.type (Coding)."""
    for ae in _entries(build_audit_bundle(minimal_session, conformant_event)):
        t = ae.get("type", {})
        assert t.get("system") and t.get("code"), f"Missing type in {ae.get('id')}"


def test_required_recorded_present(minimal_session, conformant_event):
    """R4 requires AuditEvent.recorded (instant)."""
    for ae in _entries(build_audit_bundle(minimal_session, conformant_event)):
        assert ae.get("recorded"), f"Missing recorded in {ae.get('id')}"


# ── Test 7-8: Agent requirements ──────────────────────────────────────────

def test_required_agent_requestor(minimal_session, conformant_event):
    """R4 requires AuditEvent.agent[*].requestor (boolean)."""
    for ae in _entries(build_audit_bundle(minimal_session, conformant_event)):
        assert ae.get("agent"), f"No agent in {ae.get('id')}"
        for a in ae["agent"]:
            assert "requestor" in a, f"agent.requestor missing in {ae.get('id')}"
            assert isinstance(a["requestor"], bool)


def test_first_agent_is_requestor(minimal_session, conformant_event):
    """The AI voice agent is always the first agent and always requestor=true."""
    for ae in _entries(build_audit_bundle(minimal_session, conformant_event)):
        assert ae["agent"][0]["requestor"] is True


# ── Test 9: Source requirement ─────────────────────────────────────────────

def test_required_source_observer(minimal_session, conformant_event):
    """R4 requires AuditEvent.source.observer."""
    for ae in _entries(build_audit_bundle(minimal_session, conformant_event)):
        src = ae.get("source", {})
        assert src.get("observer"), f"Missing source.observer in {ae.get('id')}"


# ── Test 10-13: Milestone selection ───────────────────────────────────────

def test_session_start_always_emitted(minimal_session, conformant_event):
    assert "nhid-session-start" in _milestones(
        build_audit_bundle(minimal_session, conformant_event)
    )


def test_call_end_always_emitted(minimal_session, conformant_event):
    assert "nhid-call-end" in _milestones(
        build_audit_bundle(minimal_session, conformant_event)
    )


def test_idg01_milestone_when_disclosure_present(minimal_session, conformant_event):
    assert "nhid-identity-disclosure" in _milestones(
        build_audit_bundle(minimal_session, conformant_event)
    )


def test_phi_gate_milestone_when_phi_accessed(minimal_session, conformant_event):
    assert "nhid-phi-gate" in _milestones(
        build_audit_bundle(minimal_session, conformant_event)
    )


def test_phi_exchange_milestone_when_gate_cleared(minimal_session, conformant_event):
    # disclosure set + phi_accessed non-empty → phi_exchange emitted
    assert "nhid-phi-exchange" in _milestones(
        build_audit_bundle(minimal_session, conformant_event)
    )


def test_escalation_milestone_when_triggered(minimal_session, escalation_event):
    assert "nhid-escalation" in _milestones(
        build_audit_bundle(minimal_session, escalation_event)
    )


def test_no_phi_exchange_without_disclosure(minimal_session, noncompliant_event):
    # PHI accessed but no disclosure → gate blocked, no phi_exchange milestone
    assert "nhid-phi-exchange" not in _milestones(
        build_audit_bundle(minimal_session, noncompliant_event)
    )


# ── Test 17-19: Outcome codes ─────────────────────────────────────────────

def test_idg01_outcome_zero_on_conformant(minimal_session, conformant_event):
    b = build_audit_bundle(minimal_session, conformant_event)
    idg = next(
        ae for ae in _entries(b)
        if ae.get("subtype", [{}])[0].get("code") == "nhid-identity-disclosure"
    )
    assert idg["outcome"] == "0"


def test_idg01_outcome_eight_on_violation(minimal_session, noncompliant_event):
    b = build_audit_bundle(minimal_session, noncompliant_event)
    idg = next(
        ae for ae in _entries(b)
        if ae.get("subtype", [{}])[0].get("code") == "nhid-identity-disclosure"
    )
    assert idg["outcome"] == "8"


def test_phi_gate_outcome_eight_on_violation(minimal_session, noncompliant_event):
    b = build_audit_bundle(minimal_session, noncompliant_event)
    gate = next(
        ae for ae in _entries(b)
        if ae.get("subtype", [{}])[0].get("code") == "nhid-phi-gate"
    )
    assert gate["outcome"] == "8"


# ── Test 20-21: Entity and session ID ─────────────────────────────────────

def test_entity_carries_session_id(minimal_session, conformant_event):
    expected = "CA1234567890abcdef1234567890abcd"
    for ae in _entries(build_audit_bundle(minimal_session, conformant_event)):
        entity_values = [
            e.get("what", {}).get("identifier", {}).get("value")
            for e in ae.get("entity", [])
        ]
        assert expected in entity_values, f"session_id not in entity for {ae.get('id')}"


def test_bundle_id_is_deterministic(minimal_session, conformant_event):
    b1 = build_audit_bundle(minimal_session, conformant_event)
    b2 = build_audit_bundle(minimal_session, conformant_event)
    assert b1["id"] == b2["id"]


# ── Test 22: Provider agent slice ──────────────────────────────────────────

def test_provider_agent_present_when_npi_given(minimal_session, conformant_event):
    b = build_audit_bundle(
        minimal_session, conformant_event,
        provider_npi="1234567890", provider_name="Sunny Dental"
    )
    for ae in _entries(b):
        npi_values = [
            a.get("who", {}).get("identifier", {}).get("value")
            for a in ae.get("agent", [])
        ]
        assert "1234567890" in npi_values, f"Provider NPI not in agents for {ae.get('id')}"


# ── Test 23: Auth verification milestone ──────────────────────────────────

def test_auth_verification_milestone_when_provider_npi(minimal_session, conformant_event):
    b = build_audit_bundle(
        minimal_session, conformant_event, provider_npi="1234567890"
    )
    assert "nhid-auth-verification" in _milestones(b)


def test_no_auth_milestone_without_provider_npi(minimal_session, conformant_event):
    b = build_audit_bundle(minimal_session, conformant_event)
    assert "nhid-auth-verification" not in _milestones(b)


# ── Test 25: fullUrl required by R4 collection bundles ─────────────────────

def test_entry_has_full_url(minimal_session, conformant_event):
    """R4 requires fullUrl on every entry in a collection Bundle."""
    b = build_audit_bundle(minimal_session, conformant_event)
    for i, entry in enumerate(b["entry"]):
        assert "fullUrl" in entry, f"entry[{i}] missing fullUrl"
        assert entry["fullUrl"].startswith("urn:uuid:"), (
            f"entry[{i}] fullUrl should be urn:uuid:, got {entry['fullUrl']!r}"
        )
