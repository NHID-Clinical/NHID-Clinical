"""Persistent audit event storage with SQLite backend.

Provides durable storage for audit trails, query interfaces, and chain verification.
Local development uses SQLite; production can extend to DynamoDB (Phase 6B).
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from src.audit_integrity import AuditIntegrity


class AuditStore:
    """SQLite-based persistent audit event storage."""

    def __init__(self, db_path: str = "/data/audit_events.db", secret_key: Optional[bytes] = None):
        """Initialize audit store.

        Args:
            db_path: Path to SQLite database file
            secret_key: HMAC secret key for verification (optional; generated if not provided)
        """
        self.db_path = db_path
        self.secret_key = secret_key or os.urandom(32)
        self._integrity = AuditIntegrity(self.secret_key)
        self._init_db()

    def _init_db(self):
        """Create database schema if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Audit events table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                payload JSON NOT NULL,
                previous_event_id TEXT,
                evidence_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
            """
        )

        # Audit sessions table (metadata about sessions)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                agent_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                event_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                retention_days INTEGER DEFAULT 90
            )
            """
        )

        # Verification records (for tracking chain verification results)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_valid INTEGER NOT NULL,
                error_message TEXT,
                event_count INTEGER,
                FOREIGN KEY (session_id) REFERENCES audit_sessions(session_id)
            )
            """
        )

        # Create indices for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON audit_events(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON audit_events(expires_at)")

        conn.commit()
        conn.close()

    def write_event(
        self,
        event_id: str,
        session_id: str,
        event_type: str,
        timestamp: str,
        agent_id: str,
        organization_id: str,
        payload: dict,
        previous_event_id: Optional[str] = None,
        evidence_hash: Optional[str] = None,
        retention_days: int = 90,
    ) -> bool:
        """Write an audit event to persistent storage.

        Args:
            event_id: Unique event identifier
            session_id: Session identifier
            event_type: Event type (POLICY_DECISION, DISCLOSURE_EVENT, etc.)
            timestamp: ISO 8601 timestamp
            agent_id: Agent identifier
            organization_id: Organization identifier
            payload: Event payload (dict)
            previous_event_id: ID of previous event for chain linking
            evidence_hash: Cryptographic signature (optional)
            retention_days: TTL for this event (default 90 days)

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            expires_at = (datetime.utcnow() + timedelta(days=retention_days)).isoformat()

            cursor.execute(
                """
                INSERT INTO audit_events
                (event_id, session_id, event_type, timestamp, agent_id, organization_id,
                 payload, previous_event_id, evidence_hash, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    event_type,
                    timestamp,
                    agent_id,
                    organization_id,
                    json.dumps(payload),
                    previous_event_id,
                    evidence_hash or "",
                    expires_at,
                ),
            )

            # Update session event count
            cursor.execute(
                "UPDATE audit_sessions SET event_count = event_count + 1 WHERE session_id = ?",
                (session_id,),
            )

            if cursor.rowcount == 0:
                # Session doesn't exist, create it
                cursor.execute(
                    """
                    INSERT INTO audit_sessions
                    (session_id, agent_id, organization_id, retention_days)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, agent_id, organization_id, retention_days),
                )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            return False

    def read_event(self, event_id: str) -> Optional[dict]:
        """Read a single event from storage.

        Args:
            event_id: Event identifier to retrieve

        Returns:
            Event dict or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM audit_events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return {
                "event_id": row["event_id"],
                "session_id": row["session_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "agent_id": row["agent_id"],
                "organization_id": row["organization_id"],
                "payload": json.loads(row["payload"]),
                "previous_event_id": row["previous_event_id"],
                "evidence_hash": row["evidence_hash"],
            }
        except Exception:
            return None

    def query_events(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query events with optional filtering.

        Args:
            session_id: Filter by session
            event_type: Filter by event type
            agent_id: Filter by agent
            limit: Maximum results

        Returns:
            List of events matching criteria
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []

            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)

            query += " ORDER BY timestamp ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "event_id": row["event_id"],
                    "session_id": row["session_id"],
                    "event_type": row["event_type"],
                    "timestamp": row["timestamp"],
                    "agent_id": row["agent_id"],
                    "organization_id": row["organization_id"],
                    "payload": json.loads(row["payload"]),
                    "previous_event_id": row["previous_event_id"],
                    "evidence_hash": row["evidence_hash"],
                }
                for row in rows
            ]
        except Exception:
            return []

    def verify_chain(self, session_id: str) -> tuple[bool, Optional[str]]:
        """Verify integrity of entire audit trail for a session.

        Args:
            session_id: Session to verify

        Returns:
            Tuple of (is_valid, error_message)
        """
        events = self.query_events(session_id=session_id, limit=10000)

        if not events:
            return True, None

        # Build verification format
        events_for_verification = [
            {
                "event_id": e["event_id"],
                "timestamp": e["timestamp"],
                "event_type": e["event_type"],
                "payload": e["payload"],
                "evidence_hash": e["evidence_hash"],
                "previous_event_id": e["previous_event_id"],
            }
            for e in events
        ]

        # Verify with integrity module
        is_valid, error = self._integrity.verify_chain(events_for_verification)

        # Record verification result
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO verification_records
                (session_id, is_valid, error_message, event_count)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, 1 if is_valid else 0, error, len(events)),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        return is_valid, error

    def cleanup_expired(self) -> int:
        """Remove expired audit events.

        Returns:
            Number of events deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM audit_events WHERE expires_at < datetime('now')")
            count = cursor.rowcount

            conn.commit()
            conn.close()
            return count
        except Exception:
            return 0

    def close_session(self, session_id: str) -> bool:
        """Mark a session as closed.

        Args:
            session_id: Session to close

        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE audit_sessions SET closed_at = datetime('now') WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
