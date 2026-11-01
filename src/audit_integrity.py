"""Cryptographic integrity for ATR-01 audit trails.

HMAC-SHA256 signing for audit events, chain linking via event_id/previous_event_id,
and verification for tamper-detection.

Key rotation: events are always signed with the current key. Retired keys,
passed as ``retired_keys``, only verify events signed before a rotation; they
never sign. ``key_id(key)`` names a key without revealing it, and a caller
that recorded it lets verification try that one key instead of all of them.
"""

import hmac
import hashlib
import json
from typing import Dict, Iterable, Optional


def key_id(key: bytes) -> str:
    """A short, non-secret name for a key: the first 16 hex chars of its SHA-256."""
    return hashlib.sha256(key).hexdigest()[:16]


class AuditIntegrity:
    """Sign and verify audit events using HMAC-SHA256."""

    def __init__(self, secret_key: bytes, retired_keys: Iterable[bytes] = ()):
        """Initialize with HMAC secret key.

        Args:
            secret_key: 32-byte key for HMAC-SHA256 signing
            retired_keys: 32-byte keys that verify older events and never sign

        Raises:
            ValueError: If any key is not exactly 32 bytes, or the current key
                is also listed as retired
        """
        retired = list(retired_keys)
        for key in [secret_key, *retired]:
            if len(key) != 32:
                raise ValueError(f"Secret key must be 32 bytes, got {len(key)}")
        if secret_key in retired:
            raise ValueError("the current key cannot also be a retired key")
        self.secret_key = secret_key
        self.key_id = key_id(secret_key)
        # Current first, then retired in the order given.
        self._keys: Dict[str, bytes] = {self.key_id: secret_key}
        for key in retired:
            self._keys.setdefault(key_id(key), key)

    def _sign_with(self, key: bytes, event_id, timestamp, event_type, payload,
                   previous_event_id) -> str:
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
        return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

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
        return self._sign_with(self.secret_key, event_id, timestamp, event_type,
                               payload, previous_event_id)

    def verify_event(
        self,
        event_id: str,
        timestamp: str,
        event_type: str,
        payload: dict,
        evidence_hash: str,
        previous_event_id: Optional[str] = None,
        signed_by: Optional[str] = None,
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
        if signed_by is not None and signed_by in self._keys:
            candidates = [self._keys[signed_by]]
        else:
            # Unknown or unrecorded key id: try every configured key. A key id
            # naming no configured key falls through to the same search, so a
            # wrong label cannot make a valid event fail, nor a forged one pass.
            candidates = list(self._keys.values())
        return any(
            hmac.compare_digest(
                self._sign_with(key, event_id, timestamp, event_type, payload,
                                previous_event_id),
                evidence_hash or "",
            )
            for key in candidates
        )

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
                signed_by=event.get("key_id"),
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
