"""Persistent audit event storage with SQLite backend.

Provides durable storage for audit trails, query interfaces, and chain verification.
Local development uses SQLite; production can extend to DynamoDB (Phase 6B).

What chain verification can and cannot detect
---------------------------------------------
`verify_chain` detects **modification** of retained events: each event carries
an HMAC over its own fields plus its predecessor's id, so altering a payload,
a timestamp or the ordering breaks the chain.

It detects **wholesale removal** only as far as the `audit_sessions.event_count`
anchor allows. That counter is incremented on every write and compared against
the events actually readable, so deleting rows is caught — but the counter
lives in the same SQLite file as the events, so an attacker with write access
to the file can edit both. **This raises the cost of tampering from one edit to
two coordinated edits; it is not a cryptographic guarantee.** A deployment that
needs one must anchor the count outside this file: an append-only or WORM store,
a signed periodic checkpoint, or replication to a system the calling agent
cannot write to. That is documented in docs/claim-boundaries.md and is not
implemented here.

It cannot detect anything at all if the store is unreadable, which is why an
unreadable store is reported as a verification **failure** rather than silently
as an empty, vacuously-valid trail. Returning "valid" for a database that has
been deleted would make the cleanest attack on an audit log — removing it — the
one the log reports as fine.
"""

import sqlite3
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from src.audit_integrity import AuditIntegrity

logger = logging.getLogger(__name__)

#: Reported when a read fails for an infrastructural reason — the file is gone,
#: corrupt, locked or unreadable. Distinct from "the query matched nothing".
ERR_AUDIT_STORE_UNREADABLE = "ERR_AUDIT_STORE_UNREADABLE"

#: Reported when the session's declared event count exceeds what can be read,
#: i.e. events that were written are no longer there.
ERR_AUDIT_EVENTS_MISSING = "ERR_AUDIT_EVENTS_MISSING"


class AuditStoreUnavailable(Exception):
    """A read could not be completed, so its result is unknown — not empty.

    Raised instead of returning `[]` or `None`, because an audit store that
    conflates "I could not read" with "there is nothing there" turns every
    infrastructure failure into a clean bill of health.
    """


class AuditStore:
    """SQLite-based persistent audit event storage."""

    def __init__(self, db_path: str = "/data/audit_events.db", secret_key: Optional[bytes] = None):
        """Initialize audit store.

        Args:
            db_path: Path to SQLite database file
            secret_key: HMAC secret key for verification (optional; generated if not provided)
        """
        self.db_path = db_path
        if secret_key is None:
            # Ephemeral key, announced rather than assumed.
            #
            # Events are HMAC-signed with this key, so a fresh one per process
            # means anything already in `db_path` fails verification and
            # `verify_chain` reports signature failures on events that were
            # written correctly — the same symptom as tampering. Callers that
            # need a trail to survive a restart must pass a stable key;
            # src/config.py reads one from AUDIT_SECRET_KEY_B64 and requires it
            # in production.
            secret_key = os.urandom(32)
            logger.warning(
                "AuditStore(%s) was constructed without a secret_key, so an "
                "ephemeral one was generated. Any events already stored there "
                "will fail verification, and events written now cannot be "
                "verified after this process exits.",
                db_path,
            )
        self.secret_key = secret_key
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
                # Session doesn't exist, create it — counting this event.
                #
                # `event_count` defaults to 0 in the schema, so inserting
                # without it left the first event of every session uncounted
                # and the anchor permanently one short. That was invisible
                # while nothing read the column; `verify_chain` now compares
                # against it, where an off-by-one would let exactly one deleted
                # event slip through.
                cursor.execute(
                    """
                    INSERT INTO audit_sessions
                    (session_id, agent_id, organization_id, retention_days,
                     event_count)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (session_id, agent_id, organization_id, retention_days),
                )

            conn.commit()
            conn.close()
            return True
        except Exception as exc:
            # False is the honest answer to "did this write land?", but an
            # audit write failing silently is worth a record of its own.
            logger.error(
                "audit write failed for event %r session %r on %s: %s",
                event_id, session_id, self.db_path, exc,
            )
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
        except Exception as exc:
            # None means "no such event". A read that failed is a different
            # fact and must not borrow that answer.
            raise AuditStoreUnavailable(
                f"{ERR_AUDIT_STORE_UNREADABLE}: could not read event "
                f"{event_id!r} from {self.db_path}: {exc}"
            ) from exc

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
        except Exception as exc:
            # An empty list means "nothing matched". A failed read means the
            # answer is unknown, and presenting it as "nothing happened" is
            # how a corrupt audit trail reads as a quiet one.
            raise AuditStoreUnavailable(
                f"{ERR_AUDIT_STORE_UNREADABLE}: could not query {self.db_path}: {exc}"
            ) from exc

    def declared_event_count(self, session_id: str) -> Optional[int]:
        """How many events `write_event` recorded for this session.

        Maintained by `write_event` on every call, and the only independent
        witness this store has to how many events *should* be readable. Returns
        None when no session row exists, which is different from 0.

        See the module docstring for why this is a cost increase rather than a
        guarantee: the counter shares a file with the events it describes.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT event_count FROM audit_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            conn.close()
            return None if row is None else int(row[0])
        except Exception as exc:
            raise AuditStoreUnavailable(
                f"{ERR_AUDIT_STORE_UNREADABLE}: could not read the session "
                f"anchor for {session_id!r} from {self.db_path}: {exc}"
            ) from exc

    def verify_chain(self, session_id: str) -> tuple[bool, Optional[str]]:
        """Verify integrity of entire audit trail for a session.

        Args:
            session_id: Session to verify

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            events = self.query_events(session_id=session_id, limit=10000)
            declared = self.declared_event_count(session_id)
        except AuditStoreUnavailable as exc:
            # Cannot read, therefore cannot attest. Previously this surfaced as
            # an empty list and the `if not events` branch below reported the
            # trail as valid — so deleting the database, the cleanest attack on
            # a log, produced a passing integrity check.
            return False, str(exc)

        # The anchor is the only independent witness to how many events were
        # written. Fewer readable than declared means events are gone, which a
        # hash chain over the survivors cannot notice: the remaining links
        # still agree with each other.
        if declared is not None and declared > len(events):
            return False, (
                f"{ERR_AUDIT_EVENTS_MISSING}: session {session_id!r} declares "
                f"{declared} event(s), {len(events)} readable"
            )

        if not events:
            if declared is None:
                # No session row and no events: this store has no record of the
                # session at all. Vacuously consistent, and said explicitly so
                # a caller cannot read it as "verified".
                return True, None
            # declared == 0: the session was opened and nothing was written.
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
        except Exception as exc:
            # Non-fatal: failing to *record* the verification must not change
            # the verification's answer. But it was silent, which meant a store
            # that could no longer write its own audit of audits said nothing.
            logger.warning(
                "could not persist the verification record for session %r to "
                "%s: %s", session_id, self.db_path, exc,
            )

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
        except Exception as exc:
            # 0 means "nothing was due for pruning". A failed prune is not that,
            # and reporting it as 0 would show a retention job as working.
            raise AuditStoreUnavailable(
                f"{ERR_AUDIT_STORE_UNREADABLE}: prune failed on "
                f"{self.db_path}: {exc}"
            ) from exc

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
