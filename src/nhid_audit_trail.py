"""
NHID-Clinical Audit Trail (ATR-01) Implementation
==================================================
Immutable audit event logging for healthcare AI agent governance.

Preserves the identity → authority → decision → action chain to enable
post-event review, incident investigation, and compliance reconstruction.

Design:
  - Write-once, tamper-evident event records
  - Agent identity, organization identity, authority scope capture
  - Disclosure event classification (D0-D4 levels)
  - PHI access attempt logging (allowed and denied)
  - Policy decision records with rationale
  - Escalation event logging
  - Immutable, synchronized timestamps
  - Session replay metadata for audit reconstruction
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime
import os

from src.audit_integrity import AuditIntegrity


class DisclosureLevel(str, Enum):
    """IDG-01 disclosure quality taxonomy."""
    D0 = "D0"  # No disclosure
    D1 = "D1"  # Generic system name ("claims system")
    D2 = "D2"  # Weak AI disclosure ("automated assistant") — WARNING
    D3 = "D3"  # AI identity disclosure (MINIMUM PASS) — "AI assistant"
    D4 = "D4"  # AI + organizational scope (PREFERRED) — "AI assistant operated by [Org]"


class AuditEventType(str, Enum):
    """Audit event classification."""
    SESSION_START = "SESSION_START"
    DISCLOSURE_EVENT = "DISCLOSURE_EVENT"
    PHI_ACCESS_ATTEMPT = "PHI_ACCESS_ATTEMPT"
    POLICY_DECISION = "POLICY_DECISION"
    ESCALATION_EVENT = "ESCALATION_EVENT"
    SESSION_END = "SESSION_END"


class PHIAccessOutcome(str, Enum):
    """PHI access request outcome."""
    ALLOWED = "ALLOWED"  # PHI transmitted
    DENIED = "DENIED"    # PHI blocked by governance
    REDACTED = "REDACTED"  # PHI transmitted with redactions


@dataclass(frozen=True)
class AgentIdentity:
    """Agent identity and version information."""
    agent_id: str
    agent_name: str | None = None
    model: str | None = None  # LLM model, voice model, etc.
    configuration_id: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class OrganizationIdentity:
    """Organization operating the agent."""
    organization_id: str
    organization_name: str | None = None
    authority_scope: str | None = None  # "eligibility", "authorization", "claims", etc.
    delegation_chain: list[str] = field(default_factory=list)  # For multi-agent scenarios


@dataclass(frozen=True)
class DisclosureEventRecord:
    """Disclosure event captured during session."""
    timestamp: str  # ISO 8601 format
    level: DisclosureLevel
    disclosure_text: str
    speaker: str  # "agent" or "system"
    turn_index: int


@dataclass(frozen=True)
class PHIAccessRecord:
    """PHI access attempt (allowed or denied)."""
    timestamp: str  # ISO 8601 format
    turn_index: int
    phi_fields_requested: list[str]  # member_id, date_of_birth, NPI, etc.
    phi_fields_accessed: list[str]  # Subset of requested (may be empty if denied)
    outcome: PHIAccessOutcome
    governance_decision_id: str | None = None
    denial_reason: str | None = None


@dataclass(frozen=True)
class PolicyDecisionRecord:
    """Policy evaluation decision and rationale."""
    timestamp: str  # ISO 8601 format
    turn_index: int
    decision_id: str
    policy_version: str
    action: str  # PolicyAction.value
    reason_code: str
    violations_detected: list[str]  # Rule IDs: IDG-01, PDX-01, etc.
    violations_detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EscalationEventRecord:
    """Escalation event (human oversight invocation)."""
    timestamp: str  # ISO 8601 format
    turn_index: int
    escalation_trigger: str  # Rule that triggered escalation
    trigger_reason: str
    escalation_outcome: str  # "honored", "denied", "redirected", "deflected"
    human_recipient: str | None = None  # Identity of human who received escalation
    escalation_method: str | None = None  # "call_transfer", "queue", "callback", etc.


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit trail event."""
    event_id: str  # Unique event identifier (uuid)
    session_id: str
    event_type: AuditEventType
    timestamp: str  # ISO 8601, immutable
    agent_identity: AgentIdentity
    organization_identity: OrganizationIdentity

    # Event-specific payload (one will be populated per event type)
    disclosure_event: DisclosureEventRecord | None = None
    phi_access_record: PHIAccessRecord | None = None
    policy_decision_record: PolicyDecisionRecord | None = None
    escalation_event: EscalationEventRecord | None = None

    # Metadata for session reconstruction
    state_before: str = ""  # Session state before this event
    state_after: str = ""   # Session state after this event

    # Integrity fields
    previous_event_id: str | None = None  # Link to prior event (chain)
    evidence_hash: str | None = None  # HMAC for integrity verification

    # Replay metadata
    request_id: str | None = None
    replay_mode: str = "live"  # "live" or "replay"


@dataclass
class AuditTrail:
    """In-memory audit trail for a session."""
    session_id: str
    agent_identity: AgentIdentity
    organization_identity: OrganizationIdentity
    events: list[AuditEvent] = field(default_factory=list)
    _signer: AuditIntegrity | None = field(default=None, init=False)

    def __post_init__(self):
        """Initialize signer with secret key from environment or generate new one."""
        secret_key_b64 = os.getenv("AUDIT_SECRET_KEY_B64")
        if secret_key_b64:
            import base64
            secret_key = base64.b64decode(secret_key_b64)
        else:
            secret_key = os.urandom(32)
        object.__setattr__(self, "_signer", AuditIntegrity(secret_key))

    def add_event(self, event: AuditEvent) -> AuditEvent:
        """Append immutable event to trail, signing for integrity.

        Args:
            event: AuditEvent to add

        Returns:
            AuditEvent with evidence_hash set (signed)
        """
        # Get previous event for chain linking
        previous_event_id = self.events[-1].event_id if self.events else None

        # Build payload for signing
        payload = {}
        if event.disclosure_event:
            payload["disclosure_event"] = {
                "timestamp": event.disclosure_event.timestamp,
                "level": event.disclosure_event.level.value,
                "text": event.disclosure_event.disclosure_text,
                "speaker": event.disclosure_event.speaker,
            }
        elif event.phi_access_record:
            payload["phi_access_record"] = {
                "phi_requested": event.phi_access_record.phi_fields_requested,
                "phi_accessed": event.phi_access_record.phi_fields_accessed,
                "outcome": event.phi_access_record.outcome.value,
            }
        elif event.policy_decision_record:
            payload["policy_decision"] = {
                "action": event.policy_decision_record.action,
                "violations": event.policy_decision_record.violations_detected,
            }
        elif event.escalation_event:
            payload["escalation"] = {
                "trigger": event.escalation_event.escalation_trigger,
                "outcome": event.escalation_event.escalation_outcome,
            }

        # Sign the event
        evidence_hash = self._signer.sign_event(
            event_id=event.event_id,
            timestamp=event.timestamp,
            event_type=event.event_type.value,
            payload=payload,
            previous_event_id=previous_event_id,
        )

        # Create signed copy of event
        signed_event = AuditEvent(
            event_id=event.event_id,
            session_id=event.session_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            agent_identity=event.agent_identity,
            organization_identity=event.organization_identity,
            disclosure_event=event.disclosure_event,
            phi_access_record=event.phi_access_record,
            policy_decision_record=event.policy_decision_record,
            escalation_event=event.escalation_event,
            state_before=event.state_before,
            state_after=event.state_after,
            previous_event_id=previous_event_id,
            evidence_hash=evidence_hash,
            request_id=event.request_id,
            replay_mode=event.replay_mode,
        )

        self.events.append(signed_event)
        return signed_event

    def verify_chain(self) -> tuple[bool, str | None]:
        """Verify integrity of entire audit trail.

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if entire chain is valid and tamper-free
            - (False, error_msg) if tampering or signature verification fails
        """
        if not self._signer:
            return False, "Signer not initialized"

        if not self.events:
            return True, None

        # Build event representations for verification
        events_for_verification = []
        for event in self.events:
            payload = {}
            if event.disclosure_event:
                payload["disclosure_event"] = {
                    "timestamp": event.disclosure_event.timestamp,
                    "level": event.disclosure_event.level.value,
                    "text": event.disclosure_event.disclosure_text,
                    "speaker": event.disclosure_event.speaker,
                }
            elif event.phi_access_record:
                payload["phi_access_record"] = {
                    "phi_requested": event.phi_access_record.phi_fields_requested,
                    "phi_accessed": event.phi_access_record.phi_fields_accessed,
                    "outcome": event.phi_access_record.outcome.value,
                }
            elif event.policy_decision_record:
                payload["policy_decision"] = {
                    "action": event.policy_decision_record.action,
                    "violations": event.policy_decision_record.violations_detected,
                }
            elif event.escalation_event:
                payload["escalation"] = {
                    "trigger": event.escalation_event.escalation_trigger,
                    "outcome": event.escalation_event.escalation_outcome,
                }

            events_for_verification.append(
                {
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "event_type": event.event_type.value,
                    "payload": payload,
                    "evidence_hash": event.evidence_hash or "",
                    "previous_event_id": event.previous_event_id,
                }
            )

        return self._signer.verify_chain(events_for_verification)

    def get_disclosure_events(self) -> list[DisclosureEventRecord]:
        """Retrieve all disclosure events in order."""
        return [
            e.disclosure_event for e in self.events
            if e.event_type == AuditEventType.DISCLOSURE_EVENT and e.disclosure_event
        ]

    def get_phi_access_records(self) -> list[PHIAccessRecord]:
        """Retrieve all PHI access attempts (allowed and denied)."""
        return [
            e.phi_access_record for e in self.events
            if e.event_type == AuditEventType.PHI_ACCESS_ATTEMPT and e.phi_access_record
        ]

    def get_policy_decisions(self) -> list[PolicyDecisionRecord]:
        """Retrieve all policy decisions in order."""
        return [
            e.policy_decision_record for e in self.events
            if e.event_type == AuditEventType.POLICY_DECISION and e.policy_decision_record
        ]

    def get_escalation_events(self) -> list[EscalationEventRecord]:
        """Retrieve all escalation events."""
        return [
            e.escalation_event for e in self.events
            if e.event_type == AuditEventType.ESCALATION_EVENT and e.escalation_event
        ]

    def get_latest_disclosure(self) -> DisclosureEventRecord | None:
        """Get the most recent disclosure event."""
        events = self.get_disclosure_events()
        return events[-1] if events else None

    def get_phi_access_chain(self) -> list[PHIAccessRecord]:
        """Reconstruct PHI access chain for session."""
        return self.get_phi_access_records()

    def get_decision_chain(self) -> list[PolicyDecisionRecord]:
        """Reconstruct policy decision chain for session."""
        return self.get_policy_decisions()

    def to_audit_report(self) -> dict[str, Any]:
        """Generate audit report for compliance review."""
        return {
            "session_id": self.session_id,
            "agent_identity": {
                "agent_id": self.agent_identity.agent_id,
                "agent_name": self.agent_identity.agent_name,
                "model": self.agent_identity.model,
                "version": self.agent_identity.version,
            },
            "organization_identity": {
                "organization_id": self.organization_identity.organization_id,
                "organization_name": self.organization_identity.organization_name,
                "authority_scope": self.organization_identity.authority_scope,
            },
            "event_count": len(self.events),
            "disclosure_events": [
                {
                    "timestamp": e.timestamp,
                    "level": e.disclosure_event.level.value,
                    "text": e.disclosure_event.disclosure_text,
                }
                for e in self.events
                if e.event_type == AuditEventType.DISCLOSURE_EVENT and e.disclosure_event
            ],
            "phi_access_attempts": [
                {
                    "timestamp": e.timestamp,
                    "requested": e.phi_access_record.phi_fields_requested,
                    "accessed": e.phi_access_record.phi_fields_accessed,
                    "outcome": e.phi_access_record.outcome.value,
                }
                for e in self.events
                if e.event_type == AuditEventType.PHI_ACCESS_ATTEMPT and e.phi_access_record
            ],
            "policy_decisions": [
                {
                    "timestamp": e.timestamp,
                    "action": e.policy_decision_record.action,
                    "violations": e.policy_decision_record.violations_detected,
                }
                for e in self.events
                if e.event_type == AuditEventType.POLICY_DECISION and e.policy_decision_record
            ],
            "escalation_events": [
                {
                    "timestamp": e.timestamp,
                    "trigger": e.escalation_event.escalation_trigger,
                    "outcome": e.escalation_event.escalation_outcome,
                    "human_recipient": e.escalation_event.human_recipient,
                }
                for e in self.events
                if e.event_type == AuditEventType.ESCALATION_EVENT and e.escalation_event
            ],
        }
