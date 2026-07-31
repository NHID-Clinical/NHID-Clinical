"""Tests for shadow mode logging."""

import pytest
from src.safety_evaluation.safety_logger import (
    ShadowModeLogger,
    SafetyEvent,
    SafetyEventType,
)


class TestShadowLoggerBasics:
    """Test ShadowModeLogger basic operations."""

    def test_logger_initialization(self, shadow_logger, sample_session_id):
        """Test ShadowModeLogger initialization."""
        assert shadow_logger.component_name == "test_component"
        assert shadow_logger.session_id == sample_session_id
        assert shadow_logger.get_event_count() == 0
        assert shadow_logger.get_error_count() == 0

    def test_log_event_success(self, shadow_logger):
        """Test logging an event succeeds."""
        import uuid
        event = SafetyEvent(
            event_id=str(uuid.uuid4()),
            timestamp="2024-01-01T00:00:00Z",
            event_type=SafetyEventType.POLICY_DECISION_MADE,
            session_id=shadow_logger.session_id,
            turn_index=1,
            policy_action="CONTINUE_AI",
        )
        result = shadow_logger.log_event(event)
        assert result is True
        assert shadow_logger.get_event_count() == 1

    def test_log_event_returns_false_on_error(self, shadow_logger):
        """Test that logging errors don't raise exceptions."""
        # Create invalid event to trigger error
        event = None
        result = shadow_logger.log_event(event)
        assert result is False
        assert shadow_logger.get_error_count() > 0

    def test_get_events_returns_copy(self, shadow_logger):
        """Test that get_events returns a copy of events."""
        import uuid
        event1 = SafetyEvent(
            event_id=str(uuid.uuid4()),
            timestamp="2024-01-01T00:00:00Z",
            event_type=SafetyEventType.POLICY_DECISION_MADE,
            session_id=shadow_logger.session_id,
            turn_index=1,
            policy_action="CONTINUE_AI",
        )
        shadow_logger.log_event(event1)
        events = shadow_logger.get_events()
        assert len(events) == 1
        # Modifying returned list shouldn't affect buffer
        events.clear()
        assert shadow_logger.get_event_count() == 1


class TestShadowLoggerMethods:
    """Test shadow logger convenience methods."""

    def test_log_policy_decision(self, shadow_logger):
        """Test log_policy_decision method."""
        result = shadow_logger.log_policy_decision(
            turn_index=1,
            policy_action="ESCALATE_HUMAN",
            violations=["IDG-01"],
            confidence_score=0.95,
        )
        assert result is True
        assert shadow_logger.get_event_count() == 1
        events = shadow_logger.get_events()
        assert events[0].event_type == SafetyEventType.POLICY_DECISION_MADE
        assert events[0].policy_action == "ESCALATE_HUMAN"

    def test_log_violation_detected(self, shadow_logger):
        """Test log_violation_detected method."""
        result = shadow_logger.log_violation_detected(
            turn_index=2,
            rule_id="PDX-01",
            violation_description="PHI before disclosure",
            risk_level="critical",
            confidence_score=0.99,
        )
        assert result is True
        assert shadow_logger.get_event_count() == 1
        events = shadow_logger.get_events()
        assert events[0].event_type == SafetyEventType.VIOLATION_DETECTED
        assert events[0].violations_detected == ["PDX-01"]

    def test_log_false_positive_candidate(self, shadow_logger):
        """Test log_false_positive_candidate method."""
        result = shadow_logger.log_false_positive_candidate(
            turn_index=1,
            rule_id="IDG-01",
            flagged_action="DENY_DATA",
            description="D2 disclosure flagged as insufficient",
        )
        assert result is True
        events = shadow_logger.get_events()
        assert events[0].event_type == SafetyEventType.FALSE_POSITIVE_CANDIDATE

    def test_log_audit_event_missing(self, shadow_logger):
        """Test log_audit_event_missing method."""
        result = shadow_logger.log_audit_event_missing(
            turn_index=1,
            expected_event_type="DISCLOSURE_EVENT",
            policy_action="CONTINUE_AI",
        )
        assert result is True
        events = shadow_logger.get_events()
        assert events[0].event_type == SafetyEventType.AUDIT_EVENT_MISSING
        assert events[0].risk_level == "critical"

    def test_log_engine_error(self, shadow_logger):
        """Test log_engine_error method."""
        result = shadow_logger.log_engine_error(
            turn_index=1,
            error_type="RuntimeError",
            error_message="Policy evaluation timeout",
            error_tb="Traceback...",
        )
        assert result is True
        events = shadow_logger.get_events()
        assert events[0].event_type == SafetyEventType.ENGINE_ERROR
        assert events[0].error_type == "RuntimeError"

    def test_log_threshold_breach(self, shadow_logger):
        """Test log_threshold_breach method."""
        result = shadow_logger.log_threshold_breach(
            metric_name="detection_rate",
            expected_threshold=0.95,
            actual_value=0.87,
        )
        assert result is True
        events = shadow_logger.get_events()
        assert events[0].event_type == SafetyEventType.THRESHOLD_BREACH


class TestShadowLoggerNonBlocking:
    """Test that shadow logger never blocks policy decisions."""

    def test_logging_error_doesnt_raise(self, shadow_logger):
        """Test that logging errors don't propagate."""
        # Intentionally break the logger
        shadow_logger.events_buffer = None  # This will cause AttributeError
        # These should all succeed despite the broken state
        result1 = shadow_logger.log_policy_decision(1, "CONTINUE_AI", [])
        result2 = shadow_logger.log_violation_detected(1, "IDG-01", "test", "minor", 0.5)
        # Results are False but no exception raised
        assert result1 is False
        assert result2 is False
        assert shadow_logger.get_error_count() >= 2

    def test_multiple_consecutive_errors_tracked(self, shadow_logger):
        """Test that multiple logging errors are tracked."""
        shadow_logger.events_buffer = None
        for i in range(5):
            shadow_logger.log_policy_decision(i, "CONTINUE_AI", [])
        assert shadow_logger.get_error_count() >= 5


class TestSafetyEventTypes:
    """Test SafetyEvent creation with different event types."""

    def test_policy_decision_event(self, sample_session_id):
        """Test creating a policy decision event."""
        import uuid
        event = SafetyEvent(
            event_id=str(uuid.uuid4()),
            timestamp="2024-01-01T00:00:00Z",
            event_type=SafetyEventType.POLICY_DECISION_MADE,
            session_id=sample_session_id,
            turn_index=1,
            policy_action="DENY_DATA",
            violations_detected=["IDG-01", "PDX-01"],
        )
        assert event.event_type == SafetyEventType.POLICY_DECISION_MADE
        assert len(event.violations_detected) == 2

    def test_event_to_dict(self, sample_session_id):
        """Test event serialization to dict."""
        import uuid
        event = SafetyEvent(
            event_id=str(uuid.uuid4()),
            timestamp="2024-01-01T00:00:00Z",
            event_type=SafetyEventType.VIOLATION_DETECTED,
            session_id=sample_session_id,
            turn_index=2,
            policy_action="LOG_ONLY",
            risk_level="major",
        )
        event_dict = event.to_dict()
        assert event_dict["event_type"] == SafetyEventType.VIOLATION_DETECTED
        assert event_dict["turn_index"] == 2
        assert event_dict["risk_level"] == "major"

    def test_event_to_json(self, sample_session_id):
        """Test event serialization to JSON."""
        import uuid
        import json
        event = SafetyEvent(
            event_id=str(uuid.uuid4()),
            timestamp="2024-01-01T00:00:00Z",
            event_type=SafetyEventType.ENGINE_ERROR,
            session_id=sample_session_id,
            turn_index=1,
            policy_action="ERROR",
            error_message="Test error",
        )
        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert parsed["event_type"] == SafetyEventType.ENGINE_ERROR.value
        assert parsed["error_message"] == "Test error"
