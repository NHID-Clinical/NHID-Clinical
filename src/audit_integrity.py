"""Cryptographic integrity for ATR-01 audit trails.

HMAC-SHA256 signing for audit events, chain linking via event_id/previous_event_id,
and verification for tamper-detection.
"""

import hmac
import hashlib
import json
from typing import Optional


class AuditIntegrity:
    """Sign and verify audit events using HMAC-SHA256."""

    def __init__(self, secret_key: bytes):
        """Initialize with HMAC secret key.

        Args:
            secret_key: 32-byte key for HMAC-SHA256 signing

        Raises:
            ValueError: If key is not exactly 32 bytes
        """
        if len(secret_key) != 32:
            raise ValueError(f"Secret key must be 32 bytes, got {len(secret_key)}")
        self.secret_key = secret_key

    def sign_event(
        self,
        event_id: str,
        timestamp: str,
        event_type: str,
        payload: dict,
        previous_event_id: Optional[str] = None,
    ) -> str:
        """Sign an audit event and return evidence_hash.

        Args:
            event_id: Unique event identifier
            timestamp: ISO 8601 timestamp
            event_type: Event type (POLICY, DISCLOSURE, etc.)
            payload: Event payload dict
            previous_event_id: ID of previous event for chain linking

        Returns:
            Base64-encoded HMAC-SHA256 hex digest
        """
        # Build canonical representation for signing
        canonical = json.dumps(
            {
                "event_id": event_id,
                "timestamp": timestamp,
                "event_type": event_type,
                "payload": payload,
                "previous_event_id": previous_event_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        # Sign with HMAC-SHA256
        sig = hmac.new(self.secret_key, canonical.encode("utf-8"), hashlib.sha256)
        return sig.hexdigest()

    def verify_event(
        self,
        event_id: str,
        timestamp: str,
        event_type: str,
        payload: dict,
        evidence_hash: str,
        previous_event_id: Optional[str] = None,
    ) -> bool:
        """Verify an audit event's signature.

        Args:
            event_id: Event identifier
            timestamp: ISO 8601 timestamp
            event_type: Event type
            payload: Event payload dict
            evidence_hash: Expected HMAC hex digest
            previous_event_id: ID of previous event for chain verification

        Returns:
            True if signature is valid, False otherwise
        """
        computed_hash = self.sign_event(
            event_id, timestamp, event_type, payload, previous_event_id
        )
        return hmac.compare_digest(computed_hash, evidence_hash)

    def verify_chain(
        self,
        events: list,
    ) -> tuple[bool, Optional[str]]:
        """Verify a chain of audit events.

        Args:
            events: List of event dicts, each with:
                {event_id, timestamp, event_type, payload, evidence_hash, previous_event_id}

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if entire chain is valid
            - (False, error_msg) if tampering detected
        """
        if not events:
            return True, None

        # Verify each event in isolation
        for i, event in enumerate(events):
            if not self.verify_event(
                event_id=event["event_id"],
                timestamp=event["timestamp"],
                event_type=event["event_type"],
                payload=event.get("payload", {}),
                evidence_hash=event["evidence_hash"],
                previous_event_id=event.get("previous_event_id"),
            ):
                return False, f"Event {i} ({event['event_id']}) signature verification failed"

        # Verify chain linking
        for i in range(1, len(events)):
            if events[i].get("previous_event_id") != events[i - 1]["event_id"]:
                return (
                    False,
                    f"Event {i} previous_event_id mismatch: expected {events[i-1]['event_id']}, "
                    f"got {events[i].get('previous_event_id')}",
                )

        return True, None
