"""ACC-01 record-level access, opt-in inside PDX-01.

docs/proposals/patient-access-authorization.md. A caller-agent with a valid
delegation and an in-scope field request can still ask about a record nothing
ties to its provider. ACC-01 asks the payer's own records whether this record
is linked to the delegating provider, under the payer's relationship policy.

Two seams:
  * `record_access.evaluate_access`: the payer-side check. Every one of the 20
    fixtures in fixtures/patient-access/ is reproduced exactly.
  * `evaluate_all` with `DelegationContext(require_record_access=True)`: the
    engine reads the result after PDX-01's field scope passes. Off by default,
    so nothing that runs today changes.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.agent_identity import AgentIdentityManager
from src.nhid_policy_engine_v1 import (
    DelegationContext, DelegationResult, PolicyAction, evaluate_all,
)
from src.record_access import (
    DEFAULT_POLICY, AccessRequest, MappingPayerRecords, evaluate_access,
)
from src.trust_anchor import StaticTrustAnchorResolver

FIXTURES = json.loads((Path(__file__).resolve().parents[1]
                       / "fixtures" / "patient-access" / "scenarios.json").read_text())["scenarios"]
FIXTURE_NPI = "1234567893"


def _verified(npi=FIXTURE_NPI, scope=("eligibility", "claim_status", "prior_auth")):
    return DelegationResult(evaluated=True, verified=True, reason="DLG01_DELEGATION_VERIFIED",
                            scope=frozenset(scope), provider_npi=npi)


def _expected_trace(s):
    return s["turns"][0]["healthcare_governance"]["access_authorization"]


# ── The payer-side check reproduces every fixture ──────────────────────────

@pytest.mark.parametrize("s", FIXTURES, ids=[s["scenario_id"] for s in FIXTURES])
def test_every_fixture_is_reproduced(s):
    prerequisites = s["expected"]["VER-01"] == "pass" and s["expected"]["PDX-01"] == "pass"
    result = evaluate_access(
        AccessRequest(operation=s["operation"], resource_binding=s["resource_binding"]),
        MappingPayerRecords(s["payer_record"]),
        delegation=_verified(scope=s["delegated_scope"]),
        prerequisites_met=prerequisites,
    )
    assert result.to_trace_field() == _expected_trace(s)


def test_the_npi_comes_only_from_the_verified_delegation():
    """The same record, a delegation for another provider: not linked."""
    s = next(x for x in FIXTURES if x["scenario_id"] == "FIX-ACC-001")
    result = evaluate_access(AccessRequest("claim_status", s["resource_binding"]),
                             MappingPayerRecords(s["payer_record"]),
                             delegation=_verified(npi="1987654320"), prerequisites_met=True)
    assert result.result == "exception" and result.reason_code == "RECORD_NOT_LINKED"


def test_an_unverified_delegation_is_never_assessed():
    s = FIXTURES[0]
    unverified = DelegationResult(evaluated=True, verified=False, reason="DLG01_VERIFICATION_FAILED",
                                  provider_npi=FIXTURE_NPI)
    result = evaluate_access(AccessRequest("claim_status", s["resource_binding"]),
                             MappingPayerRecords(s["payer_record"]),
                             delegation=unverified, prerequisites_met=True)
    assert result.result == "not_assessable"


def test_an_operation_outside_the_delegated_purpose_is_refused():
    s = next(x for x in FIXTURES if x["scenario_id"] == "FIX-ACC-001")
    result = evaluate_access(AccessRequest("claim_status", s["resource_binding"]),
                             MappingPayerRecords(s["payer_record"]),
                             delegation=_verified(scope=("eligibility",)), prerequisites_met=True)
    assert result.result == "exception" and result.reason_code == "PURPOSE_NOT_DELEGATED"
    assert result.checks["purpose"] == "exception"


def test_the_policy_is_data_a_payer_can_narrow():
    """A payer that does not accept rendering-provider evidence: 002 no longer passes."""
    s = next(x for x in FIXTURES if x["scenario_id"] == "FIX-ACC-002")
    strict = dict(DEFAULT_POLICY, claim_status=("CLAIM_BILLING_PROVIDER",))
    result = evaluate_access(AccessRequest("claim_status", s["resource_binding"]),
                             MappingPayerRecords(s["payer_record"]),
                             delegation=_verified(), prerequisites_met=True, policy=strict)
    assert result.result == "exception" and result.reason_code == "RECORD_NOT_LINKED"


def test_unknown_evidence_never_passes():
    for s in FIXTURES:
        trace = _expected_trace(s)
        if trace["relationship_basis"] == "UNKNOWN":
            assert trace["result"] == "unknown" and s["expected_outcome"] == "ESCALATE_HUMAN"


# ── Inside PDX-01, opt-in ──────────────────────────────────────────────────

PROVIDER_NPI = "1234567890"
CALL_SID = "CA-acc-0001"


@pytest.fixture
def world():
    manager = AgentIdentityManager()
    provider_priv, provider_pub = manager.generate_agent_keys()
    agent_priv, agent_pub = manager.generate_agent_keys()
    delegation = manager.create_delegation(provider_priv, "voice-agent-001", agent_pub,
                                           scope=["claim_status"], ttl_seconds=3600,
                                           call_sid=CALL_SID, provider_npi=PROVIDER_NPI)
    passport = manager.create_agent_passport(
        delegation, manager.sign_delegation(provider_priv, delegation), agent_priv)
    resolver = StaticTrustAnchorResolver({PROVIDER_NPI: manager.public_key_to_b64(provider_pub)})
    return {"manager": manager, "passport": passport, "resolver": resolver}


def _session(world, access=None):
    s = {"turn_count": 1, "escalation_path_available": True,
         "agent_passport": world["passport"], "identity_manager": world["manager"]}
    if access is not None:
        s["access_authorization"] = access
    return s


def _event(phi=("member_id", "claim_number")):
    return {
        "event_id": "e-1", "session_id": CALL_SID, "request_id": "req-1",
        "timestamp": "2026-11-08T10:00:00.000Z", "event_type": "POLICY", "actor_id": "agent-001",
        "state_before": "ACTIVE", "state_after": "ACTIVE", "counterparty_type": "human_operator",
        "replay_mode": "live", "external_calls_cached": False,
        "execution_context": {"pipeline_version": "1.0.0", "policy_engine_version": "1.0.0",
                              "nhid_schema_version": "1.0.0"},
        "input_payload": {"speech_text": ""},
        "healthcare_governance": {
            "disclosure_timestamp": "2026-11-08T09:59:55.000Z",
            "identity_assertion_text": "I am an automated system",
            "deceptive_artifact_flags": [], "escalation_timestamp": None,
            "escalation_outcome": None, "phi_accessed": list(phi),
        },
    }


def _access(result, reason=None):
    return {"result": result, "reason_code": reason, "operation": "claim_status",
            "relationship_basis": "CLAIM_BILLING_PROVIDER" if result == "pass" else None,
            "resource_binding": {"type": "MEMBER_CLAIM", "ref": "hmac-sha256:x"},
            "binding_checks": {"patient_binding": "pass", "identifier_match": "pass",
                               "record_relationship": result, "purpose": "pass"}}


def _ctx(world, on=True):
    return DelegationContext(resolver=world["resolver"], require_record_access=on)


def test_a_linked_record_is_released(world):
    d = evaluate_all(_session(world, _access("pass")), _event(), _ctx(world))
    assert d.action == PolicyAction.CONTINUE_AI, d.reason_code


def test_an_unlinked_record_is_denied(world):
    d = evaluate_all(_session(world, _access("exception", "RECORD_NOT_LINKED")), _event(), _ctx(world))
    assert d.action == PolicyAction.DENY_DATA
    assert d.reason_code == "PDX01_RECORD_NOT_AUTHORIZED"


def test_unresolved_evidence_escalates(world):
    d = evaluate_all(_session(world, _access("unknown", "RELATIONSHIP_EVIDENCE_UNKNOWN")),
                     _event(), _ctx(world))
    assert d.action == PolicyAction.ESCALATE_HUMAN
    assert d.reason_code == "PDX01_RECORD_ACCESS_UNRESOLVED"


def test_no_result_at_all_escalates_rather_than_passes(world):
    d = evaluate_all(_session(world), _event(), _ctx(world))
    assert d.action == PolicyAction.ESCALATE_HUMAN
    assert d.reason_code == "PDX01_RECORD_ACCESS_UNRESOLVED"


def test_a_result_for_another_operation_is_not_accepted(world):
    access = dict(_access("pass"), operation="eligibility")
    d = evaluate_all(_session(world, access), _event(), _ctx(world))
    assert d.action == PolicyAction.ESCALATE_HUMAN


def test_off_by_default_the_engine_ignores_it(world):
    d = evaluate_all(_session(world, _access("exception", "RECORD_NOT_LINKED")), _event(),
                     _ctx(world, on=False))
    assert d.action == PolicyAction.CONTINUE_AI


def test_field_scope_decides_first(world):
    """A field outside the delegation is denied by scope; ACC-01 is not consulted."""
    d = evaluate_all(_session(world, _access("pass")), _event(phi=("prior_auth_number",)), _ctx(world))
    assert d.reason_code == "PDX01_SCOPE_NOT_AUTHORIZED"


def test_no_protected_field_requested_means_nothing_to_authorize(world):
    d = evaluate_all(_session(world), _event(phi=()), _ctx(world))
    assert d.action == PolicyAction.CONTINUE_AI


def test_an_unresolved_identifier_never_passes_a_linked_record():
    s = next(x for x in FIXTURES if x["scenario_id"] == "FIX-ACC-012")
    record = dict(s["payer_record"], member_dob_matches=None)
    result = evaluate_access(AccessRequest("eligibility", s["resource_binding"]),
                             MappingPayerRecords(record),
                             delegation=_verified(), prerequisites_met=True)
    assert result.result == "unknown" and result.checks["identifier_match"] == "unknown"


def test_every_result_validates_against_the_trace_schema():
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[1] / "schema" / "nhid_trace_schema_v1.json").read_text())
    sub = schema["properties"]["healthcare_governance"]["properties"]["access_authorization"]
    for s in FIXTURES:
        result = evaluate_access(AccessRequest(s["operation"], s["resource_binding"]),
                                 MappingPayerRecords(s["payer_record"]),
                                 delegation=_verified(scope=s["delegated_scope"]), prerequisites_met=True)
        jsonschema.validate(result.to_trace_field(), sub)
