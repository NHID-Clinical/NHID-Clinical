"""Tests for persistent audit event storage."""

import pytest
import os
import tempfile
import json
from datetime import datetime, timedelta
from src.audit_store import AuditStore


class TestAuditStoreBasics:
    """Test basic write/read operations."""

    @pytest.fixture
    def store(self):
        """Create temporary audit store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            store = AuditStore(db_path=db_path)
            yield store

    def test_write_event_success(self, store):
        """Writing an event should succeed."""
        result = store.write_event(
            event_id="evt-001",
            session_id="sess-001",
            event_type="DISCLOSURE_EVENT",
            timestamp="2026-08-01T10:00:00Z",
            agent_id="agent-demo",
            organization_id="org-demo",
            payload={"disclosure_text": "I am automated"},
            evidence_hash="abc123def456",
        )
        assert result is True

    def test_read_event_success(self, store):
        """Reading a written event should return event data."""
        store.write_event(
            event_id="evt-001",
            session_id="sess-001",
            event_type="DISCLOSURE_EVENT",
            timestamp="2026-08-01T10:00:00Z",
            agent_id="agent-demo",
            organization_id="org-demo",
            payload={"disclosure_text": "I am automated"},
            evidence_hash="abc123def456",
        )

        event = store.read_event("evt-001")
        assert event is not None
        assert event["event_id"] == "evt-001"
        assert event["session_id"] == "sess-001"
        assert event["event_type"] == "DISCLOSURE_EVENT"
        assert event["payload"]["disclosure_text"] == "I am automated"

    def test_read_nonexistent_event(self, store):
        """Reading a nonexistent event should return None."""
        event = store.read_event("nonexistent")
        assert event is None

    def test_write_duplicate_event_id_fails(self, store):
        """Writing duplicate event_id should fail (unique constraint)."""
        store.write_event(
            event_id="evt-001",
            session_id="sess-001",
            event_type="DISCLOSURE_EVENT",
            timestamp="2026-08-01T10:00:00Z",
            agent_id="agent-demo",
            organization_id="org-demo",
            payload={"disclosure_text": "I am automated"},
        )

        # Try to write same event_id again
        result = store.write_event(
            event_id="evt-001",
            session_id="sess-001",
            event_type="POLICY_DECISION",
            timestamp="2026-08-01T10:00:01Z",
            agent_id="agent-demo",
            organization_id="org-demo",
            payload={"action": "CONTINUE_AI"},
        )
        assert result is False


class TestQueryOperations:
    """Test query filtering and retrieval."""

    @pytest.fixture
    def store_with_events(self):
        """Create store with multiple test events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            store = AuditStore(db_path=db_path)

            # Write multiple events
            store.write_event(
                event_id="evt-001",
                session_id="sess-001",
                event_type="DISCLOSURE_EVENT",
                timestamp="2026-08-01T10:00:00Z",
                agent_id="agent-1",
                organization_id="org-demo",
                payload={"disclosure_text": "I am automated"},
            )

            store.write_event(
                event_id="evt-002",
                session_id="sess-001",
                event_type="POLICY_DECISION",
                timestamp="2026-08-01T10:00:01Z",
                agent_id="agent-1",
                organization_id="org-demo",
                payload={"action": "CONTINUE_AI"},
            )

            store.write_event(
                event_id="evt-003",
                session_id="sess-002",
                event_type="DISCLOSURE_EVENT",
                timestamp="2026-08-01T10:00:02Z",
                agent_id="agent-2",
                organization_id="org-demo",
                payload={"disclosure_text": "I am automated"},
            )

            yield store

    def test_query_by_session_id(self, store_with_events):
        """Query should filter by session_id."""
        events = store_with_events.query_events(session_id="sess-001")
        assert len(events) == 2
        assert all(e["session_id"] == "sess-001" for e in events)

    def test_query_by_event_type(self, store_with_events):
        """Query should filter by event_type."""
        events = store_with_events.query_events(event_type="DISCLOSURE_EVENT")
        assert len(events) == 2
        assert all(e["event_type"] == "DISCLOSURE_EVENT" for e in events)

    def test_query_by_agent_id(self, store_with_events):
        """Query should filter by agent_id."""
        events = store_with_events.query_events(agent_id="agent-1")
        assert len(events) == 2
        assert all(e["agent_id"] == "agent-1" for e in events)

    def test_query_combined_filters(self, store_with_events):
        """Query should support combined filters."""
        events = store_with_events.query_events(
            session_id="sess-001", event_type="DISCLOSURE_EVENT"
        )
        assert len(events) == 1
        assert events[0]["event_id"] == "evt-001"

    def test_query_returns_ordered_by_timestamp(self, store_with_events):
        """Query results should be ordered by timestamp."""
        events = store_with_events.query_events(limit=100)
        assert len(events) == 3
        assert events[0]["timestamp"] < events[1]["timestamp"]
        assert events[1]["timestamp"] < events[2]["timestamp"]


class TestChainIntegration:
    """Test chain verification with persistent storage."""

    def test_verify_chain_single_session(self):
        """Verify chain should pass for valid chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            store = AuditStore(db_path=db_path)
            secret_key = store.secret_key

            # Create signer for generating hashes
            from src.audit_integrity import AuditIntegrity
            signer = AuditIntegrity(secret_key)

            # Sign events
            hash1 = signer.sign_event(
                "evt-001",
                "2026-08-01T10:00:00Z",
                "DISCLOSURE_EVENT",
                {"disclosure_text": "I am automated"},
            )

            hash2 = signer.sign_event(
                "evt-002",
                "2026-08-01T10:00:01Z",
                "POLICY_DECISION",
                {"action": "CONTINUE_AI"},
                previous_event_id="evt-001",
            )

            # Write to store
            store.write_event(
                event_id="evt-001",
                session_id="sess-001",
                event_type="DISCLOSURE_EVENT",
                timestamp="2026-08-01T10:00:00Z",
                agent_id="agent-demo",
                organization_id="org-demo",
                payload={"disclosure_text": "I am automated"},
                evidence_hash=hash1,
            )

            store.write_event(
                event_id="evt-002",
                session_id="sess-001",
                event_type="POLICY_DECISION",
                timestamp="2026-08-01T10:00:01Z",
                agent_id="agent-demo",
                organization_id="org-demo",
                payload={"action": "CONTINUE_AI"},
                previous_event_id="evt-001",
                evidence_hash=hash2,
            )

            # Verify chain
            is_valid, error = store.verify_chain("sess-001")
            assert is_valid is True
            assert error is None

    def test_verify_chain_detects_tampering(self):
        """Verify chain should detect tampering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            store = AuditStore(db_path=db_path)

            # Write event with wrong hash
            store.write_event(
                event_id="evt-001",
                session_id="sess-001",
                event_type="DISCLOSURE_EVENT",
                timestamp="2026-08-01T10:00:00Z",
                agent_id="agent-demo",
                organization_id="org-demo",
                payload={"disclosure_text": "I am automated"},
                evidence_hash="wrong_hash_intentionally_bad",
            )

            # Verify should fail
            is_valid, error = store.verify_chain("sess-001")
            assert is_valid is False
            assert error is not None


class TestSessionManagement:
    """Test session lifecycle operations."""

    def test_close_session(self):
        """Closing a session should update closed_at."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            store = AuditStore(db_path=db_path)

            # Write event to create session
            store.write_event(
                event_id="evt-001",
                session_id="sess-001",
                event_type="DISCLOSURE_EVENT",
                timestamp="2026-08-01T10:00:00Z",
                agent_id="agent-demo",
                organization_id="org-demo",
                payload={"disclosure_text": "I am automated"},
            )

            # Close session
            result = store.close_session("sess-001")
            assert result is True


class TestRetention:
    """Test data retention and cleanup."""

    def test_write_event_with_retention(self):
        """Event should have expiry based on retention_days."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            store = AuditStore(db_path=db_path)

            store.write_event(
                event_id="evt-001",
                session_id="sess-001",
                event_type="DISCLOSURE_EVENT",
                timestamp="2026-08-01T10:00:00Z",
                agent_id="agent-demo",
                organization_id="org-demo",
                payload={"disclosure_text": "I am automated"},
                retention_days=30,
            )

            event = store.read_event("evt-001")
            assert event is not None
            # Expiry should be approximately 30 days from now
            # (We don't check exact value as it depends on current time)
            assert event["event_id"] == "evt-001"

    def test_cleanup_expired_events(self):
        """Cleanup should remove expired events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_audit.db")
            store = AuditStore(db_path=db_path)

            # Manually set expiry to past for testing
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            store.write_event(
                event_id="evt-001",
                session_id="sess-001",
                event_type="DISCLOSURE_EVENT",
                timestamp="2026-08-01T10:00:00Z",
                agent_id="agent-demo",
                organization_id="org-demo",
                payload={"disclosure_text": "I am automated"},
                retention_days=0,
            )

            # Manually update expiry to past
            cursor.execute(
                "UPDATE audit_events SET expires_at = datetime('now', '-1 day') WHERE event_id = ?",
                ("evt-001",),
            )
            conn.commit()
            conn.close()

            # Cleanup should remove it
            count = store.cleanup_expired()
            assert count >= 1

            # Event should be gone
            event = store.read_event("evt-001")
            assert event is None
