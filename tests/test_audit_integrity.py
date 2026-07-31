"""Tests for ATR-01 audit event cryptographic signing and verification."""

import pytest
import os
from src.audit_integrity import AuditIntegrity


class TestAuditIntegrityBasics:
    """Test basic signing and verification operations."""

    @pytest.fixture
    def integrity(self):
        """Create AuditIntegrity with test key."""
        secret_key = os.urandom(32)
        return AuditIntegrity(secret_key)

    def test_sign_event_returns_hex_digest(self, integrity):
        """Signed event should return a hex digest."""
        evidence_hash = integrity.sign_event(
            event_id="evt-001",
            timestamp="2026-08-01T10:00:00Z",
            event_type="POLICY_DECISION",
            payload={"action": "CONTINUE_AI"},
        )
        assert isinstance(evidence_hash, str)
        assert len(evidence_hash) == 64  # SHA256 hex is 64 chars
        assert all(c in "0123456789abcdef" for c in evidence_hash)

    def test_verify_event_with_correct_signature(self, integrity):
        """Verification should succeed with correct signature."""
        event_id = "evt-001"
        timestamp = "2026-08-01T10:00:00Z"
        event_type = "POLICY_DECISION"
        payload = {"action": "CONTINUE_AI"}

        evidence_hash = integrity.sign_event(event_id, timestamp, event_type, payload)
        is_valid = integrity.verify_event(
            event_id, timestamp, event_type, payload, evidence_hash
        )
        assert is_valid is True

    def test_verify_event_with_tampered_payload(self, integrity):
        """Verification should fail if payload is tampered."""
        event_id = "evt-001"
        timestamp = "2026-08-01T10:00:00Z"
        event_type = "POLICY_DECISION"
        original_payload = {"action": "CONTINUE_AI"}

        evidence_hash = integrity.sign_event(event_id, timestamp, event_type, original_payload)

        # Tamper with payload
        tampered_payload = {"action": "DENY_DATA"}
        is_valid = integrity.verify_event(
            event_id, timestamp, event_type, tampered_payload, evidence_hash
        )
        assert is_valid is False

    def test_verify_event_with_tampered_timestamp(self, integrity):
        """Verification should fail if timestamp is changed."""
        event_id = "evt-001"
        original_timestamp = "2026-08-01T10:00:00Z"
        event_type = "POLICY_DECISION"
        payload = {"action": "CONTINUE_AI"}

        evidence_hash = integrity.sign_event(event_id, original_timestamp, event_type, payload)

        # Tamper with timestamp
        is_valid = integrity.verify_event(
            event_id, "2026-08-01T10:00:01Z", event_type, payload, evidence_hash
        )
        assert is_valid is False

    def test_sign_event_with_chain_linking(self, integrity):
        """Sign event with previous_event_id for chain linking."""
        event_1 = integrity.sign_event(
            event_id="evt-001",
            timestamp="2026-08-01T10:00:00Z",
            event_type="DISCLOSURE",
            payload={"disclosure_text": "I am automated"},
        )

        event_2 = integrity.sign_event(
            event_id="evt-002",
            timestamp="2026-08-01T10:00:01Z",
            event_type="POLICY_DECISION",
            payload={"action": "CONTINUE_AI"},
            previous_event_id="evt-001",
        )

        assert event_1 != event_2
        # Verify second event includes chain reference
        is_valid = integrity.verify_event(
            event_id="evt-002",
            timestamp="2026-08-01T10:00:01Z",
            event_type="POLICY_DECISION",
            payload={"action": "CONTINUE_AI"},
            evidence_hash=event_2,
            previous_event_id="evt-001",
        )
        assert is_valid is True

    def test_key_size_validation(self):
        """AuditIntegrity should reject keys that are not 32 bytes."""
        with pytest.raises(ValueError, match="Secret key must be 32 bytes"):
            AuditIntegrity(os.urandom(16))

        with pytest.raises(ValueError, match="Secret key must be 32 bytes"):
            AuditIntegrity(os.urandom(64))


class TestChainVerification:
    """Test chain integrity verification."""

    @pytest.fixture
    def integrity(self):
        """Create AuditIntegrity with test key."""
        secret_key = os.urandom(32)
        return AuditIntegrity(secret_key)

    def test_verify_chain_empty_list(self, integrity):
        """Empty event list should verify as valid."""
        is_valid, error = integrity.verify_chain([])
        assert is_valid is True
        assert error is None

    def test_verify_chain_single_event(self, integrity):
        """Single event should verify if signature is correct."""
        event = {
            "event_id": "evt-001",
            "timestamp": "2026-08-01T10:00:00Z",
            "event_type": "DISCLOSURE",
            "payload": {"disclosure_text": "I am automated"},
            "evidence_hash": integrity.sign_event(
                "evt-001",
                "2026-08-01T10:00:00Z",
                "DISCLOSURE",
                {"disclosure_text": "I am automated"},
            ),
            "previous_event_id": None,
        }

        is_valid, error = integrity.verify_chain([event])
        assert is_valid is True
        assert error is None

    def test_verify_chain_multiple_events_valid(self, integrity):
        """Chain of properly linked events should verify."""
        evt1_hash = integrity.sign_event(
            "evt-001",
            "2026-08-01T10:00:00Z",
            "DISCLOSURE",
            {"disclosure_text": "I am automated"},
        )

        evt2_hash = integrity.sign_event(
            "evt-002",
            "2026-08-01T10:00:01Z",
            "POLICY_DECISION",
            {"action": "CONTINUE_AI"},
            previous_event_id="evt-001",
        )

        evt3_hash = integrity.sign_event(
            "evt-003",
            "2026-08-01T10:00:02Z",
            "PHI_ACCESS",
            {"phi_fields": ["member_id"]},
            previous_event_id="evt-002",
        )

        events = [
            {
                "event_id": "evt-001",
                "timestamp": "2026-08-01T10:00:00Z",
                "event_type": "DISCLOSURE",
                "payload": {"disclosure_text": "I am automated"},
                "evidence_hash": evt1_hash,
                "previous_event_id": None,
            },
            {
                "event_id": "evt-002",
                "timestamp": "2026-08-01T10:00:01Z",
                "event_type": "POLICY_DECISION",
                "payload": {"action": "CONTINUE_AI"},
                "evidence_hash": evt2_hash,
                "previous_event_id": "evt-001",
            },
            {
                "event_id": "evt-003",
                "timestamp": "2026-08-01T10:00:02Z",
                "event_type": "PHI_ACCESS",
                "payload": {"phi_fields": ["member_id"]},
                "evidence_hash": evt3_hash,
                "previous_event_id": "evt-002",
            },
        ]

        is_valid, error = integrity.verify_chain(events)
        assert is_valid is True
        assert error is None

    def test_verify_chain_tampering_detected(self, integrity):
        """Chain verification should detect payload tampering."""
        evt1_hash = integrity.sign_event(
            "evt-001",
            "2026-08-01T10:00:00Z",
            "DISCLOSURE",
            {"disclosure_text": "I am automated"},
        )

        events = [
            {
                "event_id": "evt-001",
                "timestamp": "2026-08-01T10:00:00Z",
                "event_type": "DISCLOSURE",
                "payload": {"disclosure_text": "I am human"},  # Tampered!
                "evidence_hash": evt1_hash,
                "previous_event_id": None,
            },
        ]

        is_valid, error = integrity.verify_chain(events)
        assert is_valid is False
        assert "signature verification failed" in error

    def test_verify_chain_broken_link_detected(self, integrity):
        """Chain verification should detect broken links (via signature failure).

        When previous_event_id is tampered, it's part of the canonical form being signed,
        so signature verification detects the tampering before explicit link checking.
        """
        evt1_hash = integrity.sign_event(
            "evt-001",
            "2026-08-01T10:00:00Z",
            "DISCLOSURE",
            {"disclosure_text": "I am automated"},
        )

        evt2_hash = integrity.sign_event(
            "evt-002",
            "2026-08-01T10:00:01Z",
            "POLICY_DECISION",
            {"action": "CONTINUE_AI"},
            previous_event_id="evt-001",
        )

        events = [
            {
                "event_id": "evt-001",
                "timestamp": "2026-08-01T10:00:00Z",
                "event_type": "DISCLOSURE",
                "payload": {"disclosure_text": "I am automated"},
                "evidence_hash": evt1_hash,
                "previous_event_id": None,
            },
            {
                "event_id": "evt-002",
                "timestamp": "2026-08-01T10:00:01Z",
                "event_type": "POLICY_DECISION",
                "payload": {"action": "CONTINUE_AI"},
                "evidence_hash": evt2_hash,
                "previous_event_id": "evt-999",  # Wrong! Should be evt-001
            },
        ]

        is_valid, error = integrity.verify_chain(events)
        assert is_valid is False
        # Broken links are detected as signature failures (since previous_event_id is signed)
        assert "signature verification failed" in error
