"""Tests for persistent audit event storage."""

import pytest
import os
import tempfile
import json
from datetime import datetime, timedelta
from src.audit_store import (
    ERR_AUDIT_EVENTS_MISSING,
    ERR_AUDIT_STORE_UNREADABLE,
    AuditStore,
    AuditStoreUnavailable,
)


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


class TestUnreadableStoreIsNotAnEmptyOne:
    """A read that fails must not borrow the answer "there is nothing there".

    Every test here corresponds to a state `verify_chain` previously reported as
    `(True, None)` — a passing integrity check. Deleting an audit database is
    the cleanest attack on an audit log, and it was the one the log called fine.
    """

    @staticmethod
    def _seeded(tmpdir, count=3, session_id="sess-chain"):
        """A store holding a correctly-signed chain of `count` events."""
        db_path = os.path.join(tmpdir, "test_audit.db")
        store = AuditStore(db_path=db_path, secret_key=b"k" * 32)
        previous = None
        for n in range(1, count + 1):
            timestamp = f"2026-08-01T10:00:0{n}Z"
            payload = {"step": n}
            store.write_event(
                event_id=f"evt-{n}",
                session_id=session_id,
                event_type="POLICY_DECISION",
                timestamp=timestamp,
                agent_id="agent-demo",
                organization_id="org-demo",
                payload=payload,
                previous_event_id=previous,
                evidence_hash=store._integrity.sign_event(
                    event_id=f"evt-{n}",
                    timestamp=timestamp,
                    event_type="POLICY_DECISION",
                    payload=payload,
                    previous_event_id=previous,
                ),
            )
            previous = f"evt-{n}"
        return store, db_path

    def test_the_seeded_chain_verifies(self):
        """The control. Without this the rest could pass by always failing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store, _ = self._seeded(tmpdir)
            assert store.verify_chain("sess-chain") == (True, None)

    def test_a_deleted_database_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir)
            os.remove(db_path)
            is_valid, error = store.verify_chain("sess-chain")
            assert is_valid is False
            assert ERR_AUDIT_STORE_UNREADABLE in error

    def test_a_corrupt_database_fails_verification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir)
            with open(db_path, "wb") as handle:
                handle.write(b"not a sqlite file")
            is_valid, error = store.verify_chain("sess-chain")
            assert is_valid is False
            assert ERR_AUDIT_STORE_UNREADABLE in error

    def test_query_events_raises_rather_than_returning_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir)
            os.remove(db_path)
            with pytest.raises(AuditStoreUnavailable):
                store.query_events(session_id="sess-chain")

    def test_read_event_raises_on_failure_but_returns_none_when_absent(self):
        """None must keep meaning "no such event" and nothing else."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir)
            assert store.read_event("evt-does-not-exist") is None
            os.remove(db_path)
            with pytest.raises(AuditStoreUnavailable):
                store.read_event("evt-1")

    def test_cleanup_raises_rather_than_reporting_zero_pruned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir)
            os.remove(db_path)
            with pytest.raises(AuditStoreUnavailable):
                store.cleanup_expired()

    def test_an_unknown_session_is_still_vacuously_valid(self):
        """The one case where "nothing there" is the true answer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store, _ = self._seeded(tmpdir)
            assert store.verify_chain("a-session-never-recorded") == (True, None)


class TestDeletedEventsAreDetected:
    """The session anchor catches removals the hash chain cannot.

    A hash chain binds each event to its predecessor, so it notices an event
    removed from the *middle*. It cannot notice one removed from the *end*: the
    survivors still link correctly and nothing points at what is gone. Dropping
    the inconvenient ending is the most natural way to redact a log, and it was
    undetectable.
    """

    def _seeded(self, tmpdir, count=3):
        return TestUnreadableStoreIsNotAnEmptyOne._seeded(tmpdir, count=count)

    def test_the_anchor_counts_every_event_including_the_first(self):
        """`event_count` defaulted to 0 on session creation, so the first event
        of every session went uncounted and the anchor sat permanently one
        short — enough for one deleted event to pass unnoticed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store, _ = self._seeded(tmpdir, count=3)
            assert store.declared_event_count("sess-chain") == 3
            assert len(store.query_events(session_id="sess-chain")) == 3

    def test_a_single_event_written_is_counted_as_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store, _ = self._seeded(tmpdir, count=1)
            assert store.declared_event_count("sess-chain") == 1

    def test_declared_count_is_none_for_an_unknown_session(self):
        """None and 0 are different facts: no session, versus a session with
        nothing written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store, _ = self._seeded(tmpdir)
            assert store.declared_event_count("never-opened") is None

    def test_tail_truncation_is_detected(self):
        """The case the hash chain is blind to, asserted both ways."""
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir, count=3)
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM audit_events WHERE event_id = 'evt-3'")
            conn.commit()
            conn.close()

            # The chain over the survivors is still perfectly consistent.
            survivors = store.query_events(session_id="sess-chain")
            chain_view = [
                {
                    "event_id": e["event_id"],
                    "timestamp": e["timestamp"],
                    "event_type": e["event_type"],
                    "payload": e["payload"],
                    "evidence_hash": e["evidence_hash"],
                    "previous_event_id": e["previous_event_id"],
                }
                for e in survivors
            ]
            assert store._integrity.verify_chain(chain_view) == (True, None)

            # The anchor is what notices.
            is_valid, error = store.verify_chain("sess-chain")
            assert is_valid is False
            assert ERR_AUDIT_EVENTS_MISSING in error
            assert "declares 3" in error and "2 readable" in error

    def test_wholesale_deletion_is_detected(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir, count=3)
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM audit_events")
            conn.commit()
            conn.close()
            is_valid, error = store.verify_chain("sess-chain")
            assert is_valid is False
            assert ERR_AUDIT_EVENTS_MISSING in error

    def test_mid_chain_deletion_is_still_detected(self):
        """Already caught by the link check; pinned so it stays caught."""
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir, count=3)
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM audit_events WHERE event_id = 'evt-2'")
            conn.commit()
            conn.close()
            is_valid, _error = store.verify_chain("sess-chain")
            assert is_valid is False

    def test_tampering_in_place_is_still_detected(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir, count=3)
            conn = sqlite3.connect(db_path)
            conn.execute(
                "UPDATE audit_events SET payload = ? WHERE event_id = 'evt-2'",
                (json.dumps({"step": 99}),),
            )
            conn.commit()
            conn.close()
            is_valid, error = store.verify_chain("sess-chain")
            assert is_valid is False
            assert "signature verification failed" in error

    def test_the_anchor_shares_a_file_with_what_it_describes(self):
        """The documented limit, asserted so it cannot be forgotten.

        An attacker with write access to the database can edit the counter as
        well as the events. This raises tampering from one edit to two
        coordinated edits; it is not a cryptographic guarantee, and a
        deployment needing one must anchor the count outside this file.
        """
        import sqlite3

        with tempfile.TemporaryDirectory() as tmpdir:
            store, db_path = self._seeded(tmpdir, count=3)
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM audit_events WHERE event_id = 'evt-3'")
            conn.execute(
                "UPDATE audit_sessions SET event_count = 2 WHERE session_id = 'sess-chain'"
            )
            conn.commit()
            conn.close()
            # Two coordinated edits defeat it, and that is the stated boundary.
            assert store.verify_chain("sess-chain") == (True, None)


class TestEphemeralSigningKeyIsAnnounced:
    """A silently-regenerated signing key makes a correct audit trail read as
    tampered.

    Events are HMAC-signed, so a fresh key per process means everything already
    on disk fails verification. `verify_chain` then reports signature failures
    on events that were written correctly — the same symptom as an attack. Both
    `AuditStore` and `src/config.py` generated one silently, so an operator
    investigating "the audit trail says it was tampered with" would have been
    chasing a key rotation.
    """

    def test_constructing_without_a_key_warns(self, caplog):
        import logging

        with tempfile.TemporaryDirectory() as tmpdir:
            with caplog.at_level(logging.WARNING, logger="src.audit_store"):
                AuditStore(db_path=os.path.join(tmpdir, "a.db"))
        assert any("ephemeral" in r.message.lower() for r in caplog.records), (
            "generating an ephemeral audit signing key must not be silent"
        )

    def test_passing_a_key_does_not_warn(self, caplog):
        import logging

        with tempfile.TemporaryDirectory() as tmpdir:
            with caplog.at_level(logging.WARNING, logger="src.audit_store"):
                AuditStore(db_path=os.path.join(tmpdir, "a.db"),
                           secret_key=b"k" * 32)
        assert not [r for r in caplog.records if "ephemeral" in r.message.lower()]

    def test_a_new_key_makes_an_existing_trail_read_as_tampered(self):
        """The consequence, demonstrated — this is what the warning is for."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "a.db")
            first = AuditStore(db_path=db_path, secret_key=b"a" * 32)
            payload = {"step": 1}
            first.write_event(
                event_id="evt-1", session_id="sess-1",
                event_type="POLICY_DECISION", timestamp="2026-08-01T10:00:00Z",
                agent_id="agent", organization_id="org", payload=payload,
                evidence_hash=first._integrity.sign_event(
                    event_id="evt-1", timestamp="2026-08-01T10:00:00Z",
                    event_type="POLICY_DECISION", payload=payload,
                    previous_event_id=None,
                ),
            )
            assert first.verify_chain("sess-1") == (True, None)

            # Same database, different key — as after a restart with no
            # AUDIT_SECRET_KEY_B64 set.
            second = AuditStore(db_path=db_path, secret_key=b"b" * 32)
            is_valid, error = second.verify_chain("sess-1")
            assert is_valid is False
            assert "signature verification failed" in error
