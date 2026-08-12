"""
ATR-01 External Audit Persistence Layer
========================================
Bridges the pure policy engine (which produces audit_trail objects in
PolicyDecision) to persistent storage (AuditStore). This layer runs
OUTSIDE the policy engine, maintaining the pure design while enabling
ATR-01 compliance through external persistence.

Design:
  - Policy engine returns PolicyDecision with optional audit_trail
  - This layer receives the decision and audit_trail
  - Events are persisted to configured storage (SQLite, DynamoDB, etc.)
  - Audit chain integrity is maintained through hash-chaining
  - Persisted events can be retrieved for compliance reporting

The policy engine does NOT call this layer. The deployment/measurement
framework (e.g., pilot runner, handler, deployment layer) calls this
after receiving a PolicyDecision.
"""
from __future__ import annotations

from typing import Optional
import json
from datetime import datetime

from src.audit_store import AuditStore
from src.nhid_policy_engine_v1 import PolicyDecision
from src.nhid_audit_trail import AuditTrail, AuditEvent


class AuditPersistenceManager:
    """
    External persistence manager for audit trails.

    Handles:
    - Event serialization from AuditTrail/AuditEvent objects
    - Persistence to configured storage backend
    - Verification of persisted events
    - Session lifecycle management
    """

    def __init__(self, audit_store: AuditStore):
        """Initialize with an AuditStore backend."""
        self.store = audit_store

    def persist_decision(
        self,
        decision: PolicyDecision,
        session_id: str,
        agent_id: str,
        organization_id: str,
    ) -> bool:
        """
        Persist audit trail from a policy decision.

        Args:
            decision: PolicyDecision from evaluate_all()
            session_id: Session identifier
            agent_id: Agent identifier
            organization_id: Organization identifier

        Returns:
            True if all events persisted successfully, False on any failure
        """
        if not decision.audit_trail:
            # No audit trail to persist (normal for shadow-mode Tier 0)
            return True

        audit_trail: AuditTrail = decision.audit_trail
        success = True

        # Persist each event in the trail
        for event in audit_trail.events:
            if not self._persist_event(event, organization_id):
                success = False

        return success

    def _persist_event(self, event: AuditEvent, organization_id: str) -> bool:
        """
        Persist a single AuditEvent to storage.

        Args:
            event: AuditEvent to persist
            organization_id: Organization context

        Returns:
            True if persisted successfully
        """
        try:
            # Serialize event payload based on type
            payload = self._build_payload(event)

            # Write event to store
            return self.store.write_event(
                event_id=event.event_id,
                session_id=event.session_id,
                event_type=event.event_type.value,
                timestamp=event.timestamp,
                agent_id=event.agent_identity.agent_id,
                organization_id=organization_id,
                payload=payload,
                previous_event_id=event.previous_event_id,
                evidence_hash=event.evidence_hash,
                retention_days=90,  # Default retention
            )
        except Exception:
            return False

    def _build_payload(self, event: AuditEvent) -> dict:
        """Build serializable payload from AuditEvent."""
        payload = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp,
            "session_id": event.session_id,
            "agent_identity": {
                "agent_id": event.agent_identity.agent_id,
                "agent_name": event.agent_identity.agent_name,
                "model": event.agent_identity.model,
                "version": event.agent_identity.version,
            },
            "organization_identity": {
                "organization_id": event.organization_identity.organization_id,
                "organization_name": event.organization_identity.organization_name,
                "authority_scope": event.organization_identity.authority_scope,
            },
        }

        # Add event-specific payload
        if event.disclosure_event:
            payload["disclosure_event"] = {
                "timestamp": event.disclosure_event.timestamp,
                "level": event.disclosure_event.level.value,
                "text": event.disclosure_event.disclosure_text,
                "speaker": event.disclosure_event.speaker,
                "turn_index": event.disclosure_event.turn_index,
            }

        if event.phi_access_record:
            payload["phi_access_record"] = {
                "timestamp": event.phi_access_record.timestamp,
                "turn_index": event.phi_access_record.turn_index,
                "phi_fields_requested": event.phi_access_record.phi_fields_requested,
                "phi_fields_accessed": event.phi_access_record.phi_fields_accessed,
                "outcome": event.phi_access_record.outcome.value,
                "governance_decision_id": event.phi_access_record.governance_decision_id,
                "denial_reason": event.phi_access_record.denial_reason,
            }

        if event.policy_decision_record:
            payload["policy_decision_record"] = {
                "timestamp": event.policy_decision_record.timestamp,
                "turn_index": event.policy_decision_record.turn_index,
                "decision_id": event.policy_decision_record.decision_id,
                "policy_version": event.policy_decision_record.policy_version,
                "action": event.policy_decision_record.action,
                "reason_code": event.policy_decision_record.reason_code,
                "violations_detected": event.policy_decision_record.violations_detected,
                "violations_detail": event.policy_decision_record.violations_detail,
            }

        if event.escalation_event:
            payload["escalation_event"] = {
                "timestamp": event.escalation_event.timestamp,
                "turn_index": event.escalation_event.turn_index,
                "escalation_trigger": event.escalation_event.escalation_trigger,
                "trigger_reason": event.escalation_event.trigger_reason,
                "escalation_outcome": event.escalation_event.escalation_outcome,
                "human_recipient": event.escalation_event.human_recipient,
                "escalation_method": event.escalation_event.escalation_method,
            }

        # Add metadata
        payload["state_before"] = event.state_before
        payload["state_after"] = event.state_after
        payload["request_id"] = event.request_id
        payload["replay_mode"] = event.replay_mode

        return payload

    def verify_session(self, session_id: str) -> tuple[bool, Optional[str]]:
        """
        Verify audit trail integrity for a session.

        Args:
            session_id: Session to verify

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.store.verify_chain(session_id)

    def retrieve_session_events(
        self, session_id: str, limit: int = 1000
    ) -> list[dict]:
        """
        Retrieve all audit events for a session.

        Args:
            session_id: Session to retrieve
            limit: Maximum events to return

        Returns:
            List of persisted audit events
        """
        return self.store.query_events(session_id=session_id, limit=limit)

    def close_session(self, session_id: str) -> bool:
        """Mark a session as closed in the audit store."""
        return self.store.close_session(session_id)


def create_persistence_manager(db_path: str = "/data/audit_events.db") -> AuditPersistenceManager:
    """Factory function to create a persistence manager with SQLite backend."""
    store = AuditStore(db_path=db_path)
    return AuditPersistenceManager(store)
