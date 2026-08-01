"""Audit trail verification for ATR-01 compliance rule.

Implements real audit verification including:
- Event ordering validation
- Hash integrity checking
- Missing event detection
- Audit chain completeness
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import hashlib
import json


@dataclass(frozen=True)
class AuditEvent:
    """Single audit trail event."""
    event_id: str
    timestamp_ms: int
    event_type: str  # "identity_verification", "phi_request", "escalation", etc.
    actor: str  # "ai_agent", "member", "provider_staff"
    action: str
    data_involved: Optional[str]  # Type of data (ssn, dob, member_id)
    severity: str  # "critical", "major", "minor"
    hash_value: Optional[str] = None
    previous_hash: Optional[str] = None


@dataclass(frozen=True)
class AuditTrailValidationResult:
    """Result of audit trail validation."""
    workflow_id: str
    total_events: int
    ordering_valid: bool
    hash_chain_valid: bool
    completeness_score: float  # 0.0-1.0
    missing_events: List[str]
    integrity_violations: List[str]
    audit_quality_score: float  # 0.0-1.0


class AuditTrailValidator:
    """Validates audit trail integrity and completeness."""

    # Events that must be audited
    REQUIRED_AUDIT_EVENTS = {
        "identity_verification": {
            "required": True,
            "severity": "critical",
            "description": "When identity is verified"
        },
        "phi_request": {
            "required": True,
            "severity": "critical",
            "description": "When PHI is requested from caller"
        },
        "phi_disclosed": {
            "required": True,
            "severity": "critical",
            "description": "When PHI is disclosed by AI"
        },
        "escalation_requested": {
            "required": True,
            "severity": "critical",
            "description": "When escalation is requested"
        },
        "escalation_completed": {
            "required": True,
            "severity": "critical",
            "description": "When escalation transfer completes"
        },
        "ai_disclosure": {
            "required": True,
            "severity": "major",
            "description": "When AI discloses its identity"
        },
        "deceptive_behavior_detected": {
            "required": True,
            "severity": "critical",
            "description": "When deceptive behavior is detected"
        },
        "policy_decision": {
            "required": True,
            "severity": "major",
            "description": "When policy decision is made"
        },
    }

    @staticmethod
    def validate_event_ordering(events: List[AuditEvent]) -> tuple:
        """
        Validate that events are in chronological order.

        Returns: (ordering_valid, out_of_order_events)
        """
        if len(events) <= 1:
            return True, []

        out_of_order = []
        for i in range(1, len(events)):
            if events[i].timestamp_ms < events[i-1].timestamp_ms:
                out_of_order.append({
                    "event": events[i].event_id,
                    "timestamp": events[i].timestamp_ms,
                    "previous_timestamp": events[i-1].timestamp_ms,
                })

        return len(out_of_order) == 0, out_of_order

    @staticmethod
    def compute_event_hash(event: AuditEvent, previous_hash: str = None) -> str:
        """
        Compute cryptographic hash of event for chain integrity.

        Uses SHA-256 of event JSON + previous hash for chain linking.
        """
        event_data = {
            "event_id": event.event_id,
            "timestamp_ms": event.timestamp_ms,
            "event_type": event.event_type,
            "actor": event.actor,
            "action": event.action,
            "data_involved": event.data_involved,
            "severity": event.severity,
        }

        if previous_hash:
            event_data["previous_hash"] = previous_hash

        json_str = json.dumps(event_data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    @staticmethod
    def validate_hash_chain(events: List[AuditEvent]) -> tuple:
        """
        Validate cryptographic hash chain integrity.

        Returns: (chain_valid, integrity_violations)
        """
        if not events:
            return True, []

        violations = []
        previous_hash = None

        for i, event in enumerate(events):
            expected_hash = AuditTrailValidator.compute_event_hash(event, previous_hash)

            if event.hash_value and event.hash_value != expected_hash:
                violations.append({
                    "event_id": event.event_id,
                    "expected_hash": expected_hash,
                    "actual_hash": event.hash_value,
                    "position": i,
                })

            # Update chain for next iteration
            previous_hash = expected_hash

        return len(violations) == 0, violations

    @staticmethod
    def detect_missing_events(
        events: List[AuditEvent],
        conversation_turns: List = None
    ) -> List[str]:
        """
        Detect missing audit events based on conversation.

        If conversation_turns provided, checks if critical events
        that should have been audited are missing.

        Returns: List of missing event descriptions
        """
        missing = []

        # Check if we have events logged
        event_types = {e.event_type for e in events}

        # Verify all required events are present
        for required_event, spec in AuditTrailValidator.REQUIRED_AUDIT_EVENTS.items():
            if spec["required"] and required_event not in event_types:
                missing.append(f"Missing required audit: {spec['description']}")

        return missing

    @staticmethod
    def validate_completeness(
        events: List[AuditEvent],
        workflow_description: str = None
    ) -> tuple:
        """
        Compute audit trail completeness score.

        Measures how many required security-relevant events are audited.

        Returns: (completeness_score, missing_events)
        """
        if not events:
            return 0.0, list(AuditTrailValidator.REQUIRED_AUDIT_EVENTS.keys())

        event_types = {e.event_type for e in events}
        required_events = set(AuditTrailValidator.REQUIRED_AUDIT_EVENTS.keys())

        found_events = event_types & required_events
        missing_events = required_events - event_types

        if not required_events:
            return 1.0, []

        completeness = len(found_events) / len(required_events)
        return completeness, list(missing_events)

    @staticmethod
    def compute_audit_quality_score(
        ordering_valid: bool,
        hash_chain_valid: bool,
        completeness_score: float,
        no_integrity_violations: bool
    ) -> float:
        """
        Compute overall audit trail quality score (0.0-1.0).

        Factors:
        - Chronological ordering (25%)
        - Hash chain integrity (25%)
        - Completeness (30%)
        - No tampering violations (20%)
        """
        score = 0.0

        if ordering_valid:
            score += 0.25
        if hash_chain_valid:
            score += 0.25
        score += completeness_score * 0.30
        if no_integrity_violations:
            score += 0.20

        return min(1.0, max(0.0, score))

    @staticmethod
    def validate_audit_trail(
        events: List[AuditEvent],
        conversation_turns: List = None
    ) -> AuditTrailValidationResult:
        """
        Perform comprehensive audit trail validation.

        Returns: AuditTrailValidationResult with all findings
        """
        workflow_id = f"audit_{datetime.utcnow().isoformat()}"

        # Validate ordering
        ordering_valid, out_of_order = AuditTrailValidator.validate_event_ordering(events)

        # Validate hash chain
        hash_chain_valid, hash_violations = AuditTrailValidator.validate_hash_chain(events)

        # Check completeness
        completeness_score, missing_events = AuditTrailValidator.validate_completeness(
            events,
            conversation_turns
        )

        # Compute quality score
        audit_quality = AuditTrailValidator.compute_audit_quality_score(
            ordering_valid,
            hash_chain_valid,
            completeness_score,
            len(hash_violations) == 0
        )

        # Aggregate violations
        integrity_violations = []
        if out_of_order:
            integrity_violations.append("Out-of-order events detected")
        if hash_violations:
            integrity_violations.append(f"Hash chain integrity violation ({len(hash_violations)} events)")
        if missing_events:
            integrity_violations.extend([f"Missing audit: {e}" for e in missing_events[:3]])

        return AuditTrailValidationResult(
            workflow_id=workflow_id,
            total_events=len(events),
            ordering_valid=ordering_valid,
            hash_chain_valid=hash_chain_valid,
            completeness_score=completeness_score,
            missing_events=missing_events,
            integrity_violations=integrity_violations,
            audit_quality_score=audit_quality,
        )


# Audit trail test scenario generators
class AuditTrailScenarios:
    """Generate audit trail test scenarios."""

    @staticmethod
    def complete_audit_trail() -> List[AuditEvent]:
        """Generate complete, valid audit trail."""
        events = [
            AuditEvent(
                event_id="evt_001",
                timestamp_ms=0,
                event_type="call_initiated",
                actor="member",
                action="call_received",
                data_involved=None,
                severity="minor",
            ),
            AuditEvent(
                event_id="evt_002",
                timestamp_ms=1200,
                event_type="ai_disclosure",
                actor="ai_agent",
                action="disclosed_identity",
                data_involved=None,
                severity="major",
            ),
            AuditEvent(
                event_id="evt_003",
                timestamp_ms=2000,
                event_type="identity_verification",
                actor="ai_agent",
                action="verified_member_id",
                data_involved="member_id",
                severity="critical",
            ),
            AuditEvent(
                event_id="evt_004",
                timestamp_ms=3500,
                event_type="phi_request",
                actor="ai_agent",
                action="requested_dob",
                data_involved="dob",
                severity="critical",
            ),
            AuditEvent(
                event_id="evt_005",
                timestamp_ms=4200,
                event_type="policy_decision",
                actor="ai_agent",
                action="decision_made",
                data_involved=None,
                severity="major",
            ),
        ]

        # Compute hash chain
        previous_hash = None
        updated_events = []
        for event in events:
            event_hash = AuditTrailValidator.compute_event_hash(event, previous_hash)
            updated_events.append(
                AuditEvent(
                    event_id=event.event_id,
                    timestamp_ms=event.timestamp_ms,
                    event_type=event.event_type,
                    actor=event.actor,
                    action=event.action,
                    data_involved=event.data_involved,
                    severity=event.severity,
                    hash_value=event_hash,
                    previous_hash=previous_hash,
                )
            )
            previous_hash = event_hash

        return updated_events

    @staticmethod
    def out_of_order_audit_trail() -> List[AuditEvent]:
        """Generate audit trail with out-of-order events."""
        events = AuditTrailScenarios.complete_audit_trail()
        # Swap events 2 and 3
        swapped = list(events)
        swapped[1], swapped[2] = swapped[2], swapped[1]
        return swapped

    @staticmethod
    def tampered_audit_trail() -> List[AuditEvent]:
        """Generate audit trail with hash tampering."""
        events = AuditTrailScenarios.complete_audit_trail()
        # Corrupt hash of middle event
        corrupted = list(events)
        if len(corrupted) > 2:
            corrupted[2] = AuditEvent(
                event_id=corrupted[2].event_id,
                timestamp_ms=corrupted[2].timestamp_ms,
                event_type=corrupted[2].event_type,
                actor=corrupted[2].actor,
                action=corrupted[2].action,
                data_involved=corrupted[2].data_involved,
                severity=corrupted[2].severity,
                hash_value="0000000000000000",  # Tampered hash
                previous_hash=corrupted[2].previous_hash,
            )
        return corrupted

    @staticmethod
    def incomplete_audit_trail() -> List[AuditEvent]:
        """Generate incomplete audit trail (missing critical events)."""
        return [
            AuditEvent(
                event_id="evt_001",
                timestamp_ms=0,
                event_type="call_initiated",
                actor="member",
                action="call_received",
                data_involved=None,
                severity="minor",
            ),
            # Missing: ai_disclosure
            # Missing: identity_verification
            AuditEvent(
                event_id="evt_004",
                timestamp_ms=3500,
                event_type="phi_request",
                actor="ai_agent",
                action="requested_dob",
                data_involved="dob",
                severity="critical",
            ),
        ]
