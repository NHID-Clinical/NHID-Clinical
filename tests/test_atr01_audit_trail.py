"""ATR-01 Audit Trail Requirements tests."""
import pytest
from src.nhid_policy_engine_v1 import (
    PolicyAction,
    PolicyDecision,
    ViolationSeverity,
    evaluate_atr01,
    evaluate_all,
)
from src.nhid_audit_trail import (
    AuditEventType,
    AuditTrail,
    AgentIdentity,
    OrganizationIdentity,
)


class TestATR01AuditTrailGeneration:
    """Test that evaluate_atr01 generates valid audit trails."""

    def test_atr01_creates_audit_trail_with_valid_event(self):
        """ATR-01 should create an AuditTrail when all required fields present."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {},
        }

        decision = evaluate_atr01(session, event)

        assert decision.action == PolicyAction.CONTINUE_AI
        assert decision.reason_code == "ATR01_AUDIT_COMPLETE"
        assert decision.audit_trail is not None
        assert isinstance(decision.audit_trail, AuditTrail)
        assert decision.audit_trail.session_id == "sess-001"

    def test_atr01_audit_trail_contains_policy_decision_event(self):
        """Audit trail should contain at least one policy decision event."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {},
        }

        decision = evaluate_atr01(session, event)

        trail = decision.audit_trail
        assert trail is not None
        assert len(trail.events) > 0
        assert any(
            e.event_type == AuditEventType.POLICY_DECISION for e in trail.events
        )

    def test_atr01_audit_event_has_agent_identity(self):
        """Audit events should capture agent identity."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-nlp-01",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {},
        }

        decision = evaluate_atr01(session, event)

        trail = decision.audit_trail
        assert trail is not None
        assert trail.agent_identity is not None
        assert trail.agent_identity.agent_id == "agent"

    def test_atr01_audit_event_has_organization_identity(self):
        """Audit events should capture organization identity."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {},
        }

        decision = evaluate_atr01(session, event)

        trail = decision.audit_trail
        assert trail is not None
        assert trail.organization_identity is not None
        assert trail.organization_identity.organization_id == "default-org"

    def test_atr01_missing_required_field_returns_violation(self):
        """ATR-01 should return violations for missing required fields."""
        session = {"turn_count": 0}
        event = {
            # Missing session_id
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
        }

        decision = evaluate_atr01(session, event)

        assert decision.action == PolicyAction.LOG_ONLY
        assert decision.reason_code == "ATR01_AUDIT_FIELDS_MISSING"
        assert len(decision.violations) > 0
        assert any(v.rule_id == "ATR-01" for v in decision.violations)

    def test_atr01_missing_execution_context_field_returns_violation(self):
        """ATR-01 should return violations for missing execution context fields."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                # Missing policy_engine_version
                "nhid_schema_version": "1.0",
            },
        }

        decision = evaluate_atr01(session, event)

        assert decision.action == PolicyAction.LOG_ONLY
        assert decision.reason_code == "ATR01_AUDIT_FIELDS_MISSING"
        assert len(decision.violations) > 0

    def test_atr01_empty_execution_context_returns_violation(self):
        """ATR-01 should return violations for empty execution context."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {},
        }

        decision = evaluate_atr01(session, event)

        assert decision.action == PolicyAction.LOG_ONLY
        assert decision.reason_code == "ATR01_AUDIT_FIELDS_MISSING"
        assert len(decision.violations) > 0


class TestATR01WithEvaluateAll:
    """Test that audit trails are properly merged in evaluate_all."""

    def test_evaluate_all_attaches_audit_trail_from_atr01(self):
        """evaluate_all should attach the audit trail to final decision."""
        session = {"turn_count": 0, "escalation_path_available": True}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "counterparty_type": "human_operator",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {
                "disclosure_timestamp": "2026-01-15T10:29:00Z",
                "identity_assertion_text": "I am an AI assistant",
                "deceptive_artifact_flags": [],
                "phi_accessed": [],
            },
            "input_payload": {"speech_text": "Hello, how are you?"},
        }

        decision = evaluate_all(session, event)

        assert decision.audit_trail is not None
        assert isinstance(decision.audit_trail, AuditTrail)
        assert decision.audit_trail.session_id == "sess-001"

    def test_evaluate_all_audit_trail_contains_events(self):
        """Audit trail in evaluate_all result should contain policy events."""
        session = {"turn_count": 0, "escalation_path_available": True}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "counterparty_type": "human_operator",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {
                "disclosure_timestamp": "2026-01-15T10:29:00Z",
                "identity_assertion_text": "I am an AI assistant",
                "deceptive_artifact_flags": [],
                "phi_accessed": [],
            },
            "input_payload": {"speech_text": "Hello, how are you?"},
        }

        decision = evaluate_all(session, event)

        trail = decision.audit_trail
        assert trail is not None
        assert len(trail.events) > 0

    def test_evaluate_all_audit_trail_has_identity_info(self):
        """Audit trail should preserve agent and organization identity."""
        session = {"turn_count": 1, "escalation_path_available": True}
        event = {
            "event_id": "evt-002",
            "timestamp": "2026-01-15T10:31:00Z",
            "session_id": "sess-001",
            "request_id": "req-002",
            "event_type": "POLICY",
            "actor_id": "agent-voice-002",
            "counterparty_type": "human_operator",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "organization_name": "ExampleHealth",
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {
                "disclosure_timestamp": "2026-01-15T10:29:00Z",
                "identity_assertion_text": "I am an AI assistant operated by ExampleHealth",
                "deceptive_artifact_flags": [],
                "phi_accessed": [],
            },
            "input_payload": {"speech_text": "Is there anything else I can help you with?"},
        }

        decision = evaluate_all(session, event)

        trail = decision.audit_trail
        assert trail is not None
        assert trail.agent_identity is not None
        assert trail.organization_identity is not None
        assert trail.organization_identity.organization_name == "ExampleHealth"


class TestATR01ComplianceReport:
    """Test audit trail report generation for compliance."""

    def test_audit_trail_report_includes_session_info(self):
        """Audit trail report should include session and agent information."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {},
        }

        decision = evaluate_atr01(session, event)
        trail = decision.audit_trail

        assert trail is not None
        report = trail.to_audit_report()

        assert "session_id" in report
        assert "agent_identity" in report
        assert "organization_identity" in report
        assert "event_count" in report
        assert report["session_id"] == "sess-001"

    def test_audit_trail_report_includes_policy_decisions(self):
        """Audit trail report should include policy decision records."""
        session = {"turn_count": 0}
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-01-15T10:30:00Z",
            "session_id": "sess-001",
            "request_id": "req-001",
            "event_type": "POLICY",
            "actor_id": "agent-demo",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "replay_mode": "live",
            "external_calls_cached": True,
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "healthcare_governance": {},
        }

        decision = evaluate_atr01(session, event)
        trail = decision.audit_trail

        assert trail is not None
        report = trail.to_audit_report()

        assert "policy_decisions" in report
        assert len(report["policy_decisions"]) > 0
