"""Shadow mode logging for safety evaluation.

Non-blocking, observation-only logging that never affects production policy decisions.
Appends to separate safety_events table; maintains complete audit trail without
modifying policy engine behavior.

Shadow mode guarantees:
- Never raises exception that blocks policy decision
- Catches and logs its own errors without escalating
- Append-only to separate table (never overwrites production audit trail)
- Latency overhead negligible (<5ms per event)
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import logging
import traceback


class SafetyEventType(str, Enum):
    """Types of safety events logged in shadow mode."""
    POLICY_DECISION_MADE = "policy_decision_made"
    VIOLATION_DETECTED = "violation_detected"
    FALSE_POSITIVE_CANDIDATE = "false_positive_candidate"
    AUDIT_EVENT_MISSING = "audit_event_missing"
    ESCALATION_HONORED = "escalation_honored"
    ESCALATION_DENIED = "escalation_denied"
    ENGINE_ERROR = "engine_error"
    THRESHOLD_BREACH = "threshold_breach"
    ANOMALY_DETECTED = "anomaly_detected"


@dataclass(frozen=True)
class SafetyEvent:
    """Single safety observation logged in shadow mode."""
    event_id: str  # UUID
    timestamp: str  # ISO 8601
    event_type: SafetyEventType
    session_id: str
    turn_index: int

    # Policy decision context
    policy_action: str  # CONTINUE_AI, ESCALATE_HUMAN, DENY_DATA, etc.
    violations_detected: List[str] = field(default_factory=list)

    # Safety-specific fields
    confidence_score: Optional[float] = None  # Detection confidence (0-1)
    risk_level: Optional[str] = None  # critical, major, minor
    anomaly_description: Optional[str] = None

    # Error tracking (if applicable)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    # Contextual metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Export event as dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Export event as JSON string."""
        return json.dumps(self.to_dict(), default=str)


class ShadowModeLogger:
    """Non-blocking safety event logger for shadow mode operation.

    All operations are wrapped in try-except to prevent logging failures
    from ever affecting policy engine behavior.

    Usage:
        logger = ShadowModeLogger("my_component")
        logger.log_event(event)  # Never raises, silently fails if needed
    """

    def __init__(
        self,
        component_name: str,
        session_id: str,
        events_buffer: Optional[List[SafetyEvent]] = None,
    ):
        """Initialize shadow mode logger.

        Args:
            component_name: Name of calling component
            session_id: Current session ID
            events_buffer: Optional in-memory buffer (e.g., for testing)
        """
        self.component_name = component_name
        self.session_id = session_id
        self.events_buffer = events_buffer or []
        self.logger = logging.getLogger(f"safety.shadow.{component_name}")
        self.error_count = 0

    def log_event(self, event: SafetyEvent) -> bool:
        """Log a safety event in shadow mode (never blocks).

        Args:
            event: SafetyEvent to log

        Returns:
            True if logged successfully, False if error (logged silently)
        """
        try:
            self.events_buffer.append(event)
            self.logger.info(
                f"Safety event: {event.event_type.value}",
                extra={
                    "event_id": event.event_id,
                    "violations": event.violations_detected,
                    "policy_action": event.policy_action,
                }
            )
            return True
        except Exception as e:
            self.error_count += 1
            self.logger.exception(
                f"Shadow logger error (count={self.error_count}): {str(e)}"
            )
            return False

    def log_policy_decision(
        self,
        turn_index: int,
        policy_action: str,
        violations: List[str],
        confidence_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log a policy decision in shadow mode."""
        import uuid
        try:
            event = SafetyEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                event_type=SafetyEventType.POLICY_DECISION_MADE,
                session_id=self.session_id,
                turn_index=turn_index,
                policy_action=policy_action,
                violations_detected=violations,
                confidence_score=confidence_score,
                metadata=metadata or {},
            )
            return self.log_event(event)
        except Exception as e:
            self.error_count += 1
            self.logger.exception(f"Error logging policy decision: {str(e)}")
            return False

    def log_violation_detected(
        self,
        turn_index: int,
        rule_id: str,
        violation_description: str,
        risk_level: str,
        confidence_score: float,
    ) -> bool:
        """Log a violation detection in shadow mode."""
        import uuid
        try:
            event = SafetyEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                event_type=SafetyEventType.VIOLATION_DETECTED,
                session_id=self.session_id,
                turn_index=turn_index,
                policy_action="DETECTION",
                violations_detected=[rule_id],
                risk_level=risk_level,
                confidence_score=confidence_score,
                metadata={
                    "violation_description": violation_description,
                },
            )
            return self.log_event(event)
        except Exception as e:
            self.error_count += 1
            self.logger.exception(f"Error logging violation: {str(e)}")
            return False

    def log_false_positive_candidate(
        self,
        turn_index: int,
        rule_id: str,
        flagged_action: str,
        description: str,
    ) -> bool:
        """Log a potential false positive in shadow mode."""
        import uuid
        try:
            event = SafetyEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                event_type=SafetyEventType.FALSE_POSITIVE_CANDIDATE,
                session_id=self.session_id,
                turn_index=turn_index,
                policy_action=flagged_action,
                violations_detected=[rule_id],
                risk_level="minor",
                anomaly_description=description,
                metadata={
                    "requires_review": True,
                },
            )
            return self.log_event(event)
        except Exception as e:
            self.error_count += 1
            self.logger.exception(f"Error logging false positive: {str(e)}")
            return False

    def log_audit_event_missing(
        self,
        turn_index: int,
        expected_event_type: str,
        policy_action: str,
    ) -> bool:
        """Log audit completeness gap (event exists but no audit trail)."""
        import uuid
        try:
            event = SafetyEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                event_type=SafetyEventType.AUDIT_EVENT_MISSING,
                session_id=self.session_id,
                turn_index=turn_index,
                policy_action=policy_action,
                risk_level="critical",
                anomaly_description=f"Expected {expected_event_type} event missing from audit trail",
                metadata={
                    "audit_failure": True,
                    "expected_event_type": expected_event_type,
                },
            )
            return self.log_event(event)
        except Exception as e:
            self.error_count += 1
            self.logger.exception(f"Error logging audit gap: {str(e)}")
            return False

    def log_engine_error(
        self,
        turn_index: int,
        error_type: str,
        error_message: str,
        error_tb: Optional[str] = None,
    ) -> bool:
        """Log policy engine error (crash, hang, timeout)."""
        import uuid
        try:
            event = SafetyEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                event_type=SafetyEventType.ENGINE_ERROR,
                session_id=self.session_id,
                turn_index=turn_index,
                policy_action="ERROR",
                risk_level="major",
                error_type=error_type,
                error_message=error_message,
                error_traceback=error_tb,
                metadata={
                    "engine_failure": True,
                },
            )
            return self.log_event(event)
        except Exception as e:
            self.error_count += 1
            self.logger.exception(f"Error logging engine error: {str(e)}")
            return False

    def log_threshold_breach(
        self,
        metric_name: str,
        expected_threshold: float,
        actual_value: float,
    ) -> bool:
        """Log a safety metric threshold breach."""
        import uuid
        try:
            event = SafetyEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                event_type=SafetyEventType.THRESHOLD_BREACH,
                session_id=self.session_id,
                turn_index=0,
                policy_action="ALERT",
                risk_level="major",
                metadata={
                    "metric_name": metric_name,
                    "expected_threshold": expected_threshold,
                    "actual_value": actual_value,
                    "threshold_breached": actual_value > expected_threshold or actual_value < expected_threshold,
                },
            )
            return self.log_event(event)
        except Exception as e:
            self.error_count += 1
            self.logger.exception(f"Error logging threshold breach: {str(e)}")
            return False

    def get_events(self) -> List[SafetyEvent]:
        """Get all logged events (for testing/export)."""
        return self.events_buffer.copy()

    def get_event_count(self) -> int:
        """Get total events logged."""
        return len(self.events_buffer)

    def get_error_count(self) -> int:
        """Get total logging errors."""
        return self.error_count
