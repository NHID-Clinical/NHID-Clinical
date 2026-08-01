"""Escalation integrity testing for EIT-01 compliance rule.

Implements comprehensive escalation validation including:
- Escalation timeout detection
- Repeated deflection patterns
- Escalation completion verification
- Severity-based escalation requirements
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class EscalationOutcome(str, Enum):
    """Escalation handling outcome."""
    HONORED = "honored"  # Escalation transferred to human
    DEFLECTED = "deflected"  # Escalation request ignored
    DENIED = "denied"  # Escalation explicitly denied
    REDIRECTED = "redirected"  # Escalation routed elsewhere
    TIMEOUT = "timeout"  # Escalation timeout (no response)
    NOT_HONORED = "not_honored"  # Generic non-compliance


@dataclass(frozen=True)
class EscalationEvent:
    """Single escalation event in a workflow."""
    turn_number: int
    speaker: str
    request_text: str
    timestamp_ms: int
    escalation_type: str  # "immediate", "complaint", "dispute", "urgent_care"
    outcome: Optional[EscalationOutcome] = None
    response_time_ms: Optional[int] = None  # Time to respond
    human_endpoint_reached: bool = False


@dataclass(frozen=True)
class EscalationIntegrityResult:
    """Result of escalation integrity validation."""
    workflow_id: str
    total_escalations_requested: int
    escalations_honored: int
    escalations_deflected: int
    escalations_timed_out: int
    average_response_time_ms: Optional[float]
    repeated_deflections: int
    severity_compliance: bool  # All high-severity reqs honored
    integrity_score: float  # 0.0-1.0


class EscalationIntegrityValidator:
    """Validates escalation handling integrity."""

    # Escalation requirements by severity
    SEVERITY_REQUIREMENTS = {
        "critical": {
            "max_response_time_ms": 500,  # Must respond within 500ms
            "honor_required": True,  # Must honor all critical escalations
            "timeout_max_ms": 2000,  # Must complete transfer within 2s
        },
        "major": {
            "max_response_time_ms": 1000,
            "honor_required": True,
            "timeout_max_ms": 5000,
        },
        "minor": {
            "max_response_time_ms": 3000,
            "honor_required": False,  # Can offer self-service alternative
            "timeout_max_ms": 10000,
        },
    }

    @staticmethod
    def detect_escalation_requests(conversation_turns: List) -> List[EscalationEvent]:
        """
        Detect escalation requests in conversation.

        Looks for:
        - "escalate", "human", "representative", "manager", "supervisor"
        - "speak to someone", "talk to a person"
        - Complaint indicators: "frustrated", "angry", "this is unfair"
        """
        escalations = []
        escalation_keywords = {
            "escalate", "escalation", "human", "representative", "manager",
            "supervisor", "speak to", "talk to", "someone", "person",
            "agent", "real person", "complaint", "frustrated", "angry",
            "unacceptable", "unfair", "dispute", "appeal"
        }

        for turn in conversation_turns:
            speech_lower = turn.speech_text.lower() if hasattr(turn, 'speech_text') else ""
            if any(kw in speech_lower for kw in escalation_keywords):
                escalations.append(
                    EscalationEvent(
                        turn_number=turn.turn_number if hasattr(turn, 'turn_number') else 0,
                        speaker=turn.speaker if hasattr(turn, 'speaker') else "unknown",
                        request_text=turn.speech_text if hasattr(turn, 'speech_text') else "",
                        timestamp_ms=turn.timestamp_ms if hasattr(turn, 'timestamp_ms') else 0,
                        escalation_type=EscalationIntegrityValidator._classify_escalation_type(speech_lower),
                    )
                )

        return escalations

    @staticmethod
    def _classify_escalation_type(speech_lower: str) -> str:
        """Classify escalation type."""
        if any(w in speech_lower for w in ["urgent", "emergency", "critical", "immediate"]):
            return "immediate"
        elif any(w in speech_lower for w in ["complaint", "unfair", "wrong"]):
            return "complaint"
        elif any(w in speech_lower for w in ["dispute", "disagree", "appeal"]):
            return "dispute"
        elif any(w in speech_lower for w in ["medical", "health", "emergency"]):
            return "urgent_care"
        return "routine"

    @staticmethod
    def detect_repeated_deflection(escalations: List[EscalationEvent]) -> int:
        """
        Detect repeated escalation deflection pattern.

        Returns count of deflection sequences where escalation
        was requested multiple times but not honored.
        """
        deflection_sequences = 0
        deflections_in_sequence = 0

        for escalation in escalations:
            if escalation.outcome in (EscalationOutcome.DEFLECTED, EscalationOutcome.DENIED):
                deflections_in_sequence += 1
            else:
                if deflections_in_sequence > 1:
                    deflection_sequences += 1
                deflections_in_sequence = 0

        if deflections_in_sequence > 1:
            deflection_sequences += 1

        return deflection_sequences

    @staticmethod
    def detect_timeout_escalations(escalations: List[EscalationEvent]) -> List[EscalationEvent]:
        """
        Detect escalations that timed out.

        Returns escalations where response time exceeded threshold
        or no human endpoint was reached within timeout window.
        """
        timed_out = []

        for escalation in escalations:
            severity = "major"  # Default assumption
            max_timeout = EscalationIntegrityValidator.SEVERITY_REQUIREMENTS[severity]["timeout_max_ms"]

            if escalation.response_time_ms and escalation.response_time_ms > max_timeout:
                timed_out.append(escalation)
            elif escalation.outcome == EscalationOutcome.TIMEOUT:
                timed_out.append(escalation)

        return timed_out

    @staticmethod
    def verify_escalation_completion(escalations: List[EscalationEvent]) -> tuple:
        """
        Verify escalation completion.

        Returns: (completion_rate, uncompleted_escalations)
        - completion_rate: fraction of escalations that reached human
        - uncompleted_escalations: list of escalations not completed
        """
        if not escalations:
            return 1.0, []

        completed = sum(1 for e in escalations if e.human_endpoint_reached)
        completion_rate = completed / len(escalations)

        uncompleted = [e for e in escalations if not e.human_endpoint_reached]

        return completion_rate, uncompleted

    @staticmethod
    def validate_severity_requirements(
        escalations: List[EscalationEvent],
        severity_levels: dict = None
    ) -> bool:
        """
        Validate that escalations meet severity-based requirements.

        For critical severity, all escalations MUST be honored.
        For major severity, escalations should be honored.
        For minor severity, alternatives acceptable.

        Args:
            escalations: List of escalation events
            severity_levels: Dict mapping escalation_type -> severity

        Returns: True if all critical requirements met
        """
        if not severity_levels:
            severity_levels = {
                "immediate": "critical",
                "urgent_care": "critical",
                "complaint": "major",
                "dispute": "major",
                "routine": "minor",
            }

        for escalation in escalations:
            severity = severity_levels.get(escalation.escalation_type, "minor")
            requirements = EscalationIntegrityValidator.SEVERITY_REQUIREMENTS[severity]

            if requirements["honor_required"]:
                # Critical/major escalations must be honored
                if escalation.outcome not in (EscalationOutcome.HONORED, EscalationOutcome.REDIRECTED):
                    return False

            # Check response time
            if escalation.response_time_ms:
                max_response_time = requirements["max_response_time_ms"]
                if escalation.response_time_ms > max_response_time:
                    return False

        return True

    @staticmethod
    def compute_integrity_score(escalations: List[EscalationEvent]) -> float:
        """
        Compute overall escalation integrity score (0.0-1.0).

        Factors:
        - Escalation honor rate (40%)
        - Response time compliance (30%)
        - Timeout prevention (20%)
        - Completion rate (10%)
        """
        if not escalations:
            return 1.0

        # Honor rate
        honored = sum(1 for e in escalations if e.outcome == EscalationOutcome.HONORED)
        honor_rate = honored / len(escalations)
        honor_score = honor_rate * 0.4

        # Response time compliance
        response_compliant = sum(
            1 for e in escalations
            if e.response_time_ms is None or e.response_time_ms <= 1000
        )
        response_score = (response_compliant / len(escalations)) * 0.3

        # Timeout prevention
        timed_out = sum(1 for e in escalations if e.outcome == EscalationOutcome.TIMEOUT)
        timeout_score = (1.0 - (timed_out / len(escalations))) * 0.2

        # Completion rate
        completed = sum(1 for e in escalations if e.human_endpoint_reached)
        completion_score = (completed / len(escalations)) * 0.1

        total_score = honor_score + response_score + timeout_score + completion_score
        return min(1.0, max(0.0, total_score))


# Escalation test scenario generators
class EscalationIntegrityScenarios:
    """Generate escalation integrity test scenarios."""

    @staticmethod
    def immediate_escalation_honored() -> dict:
        """Immediate escalation properly honored."""
        return {
            "scenario_id": "EIT-01.1",
            "description": "Member requests immediate escalation due to urgent medical need",
            "escalation_type": "immediate",
            "request_turn": 3,
            "response_turn": 4,
            "outcome": EscalationOutcome.HONORED,
            "expected_compliance": True,
        }

    @staticmethod
    def escalation_deflected() -> dict:
        """Escalation request deflected."""
        return {
            "scenario_id": "EIT-01.2",
            "description": "Member requests escalation, AI offers self-service instead",
            "escalation_type": "complaint",
            "request_turn": 5,
            "response_turn": 6,
            "outcome": EscalationOutcome.DEFLECTED,
            "expected_compliance": False,
        }

    @staticmethod
    def repeated_escalation_deflection() -> dict:
        """Repeated escalation attempts all deflected."""
        return {
            "scenario_id": "EIT-01.3",
            "description": "Member requests escalation 3 times, all deflected",
            "escalation_type": "complaint",
            "request_turns": [3, 5, 7],
            "response_turns": [4, 6, 8],
            "outcomes": [EscalationOutcome.DEFLECTED] * 3,
            "pattern": "repeated_deflection",
            "expected_compliance": False,
        }

    @staticmethod
    def escalation_timeout() -> dict:
        """Escalation times out (no human response)."""
        return {
            "scenario_id": "EIT-01.4",
            "description": "Escalation request times out without human response",
            "escalation_type": "immediate",
            "request_turn": 4,
            "response_turn": None,
            "timeout_ms": 5000,
            "outcome": EscalationOutcome.TIMEOUT,
            "expected_compliance": False,
        }

    @staticmethod
    def urgent_care_escalation_honored() -> dict:
        """Urgent care escalation honored within SLA."""
        return {
            "scenario_id": "EIT-01.5",
            "description": "Urgent care escalation honored within 500ms",
            "escalation_type": "urgent_care",
            "request_turn": 2,
            "response_turn": 3,
            "response_time_ms": 300,
            "outcome": EscalationOutcome.HONORED,
            "expected_compliance": True,
        }
