import json
import os
import sqlite3
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "nhid_events.db"


def _utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _migrate_identity_columns(conn: sqlite3.Connection) -> None:
    """Add call_sid / session_id_source to an events table created before them.

    CREATE TABLE IF NOT EXISTS silently does nothing when the table already
    exists, so a database written by an earlier version keeps the old shape and
    every insert naming the new columns fails. Existing rows get NULL, which is
    honest: those events predate the distinction and nothing here knows whether
    their session_id was a real CallSid.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(events);")}
    for column in ("call_sid", "session_id_source"):
        if column not in existing:
            conn.execute(f"ALTER TABLE events ADD COLUMN {column} TEXT;")


def _get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "session_id TEXT NOT NULL,"
        "request_id TEXT,"
        "timestamp TEXT NOT NULL,"
        "event_type TEXT NOT NULL,"
        "state_before TEXT,"
        "state_after TEXT,"
        "input_text TEXT,"
        "policy_action TEXT,"
        "reason_code TEXT,"
        "response_text TEXT,"
        "llm_input TEXT,"
        "llm_output TEXT,"
        "policy_version TEXT,"
        # The Twilio CallSid as received. NULL means the upstream request did
        # not carry one -- which is a fact worth recording, not a value to
        # invent. session_id then holds a synthetic identifier instead.
        "call_sid TEXT,"
        # 'twilio_callsid' when session_id IS the upstream CallSid;
        # 'synthetic' when it was minted here. Without this an auditor cannot
        # tell a real call identifier from one this service made up.
        "session_id_source TEXT"
        ");"
    )
    _migrate_identity_columns(conn)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS processed_requests ("
        "request_id TEXT PRIMARY KEY,"
        "session_id TEXT NOT NULL,"
        "timestamp TEXT NOT NULL"
        ");"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_event_unique ON events(session_id, request_id, event_type);"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS conformance_results ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "vendor_id TEXT NOT NULL,"
        "session_id TEXT NOT NULL,"
        "timestamp TEXT NOT NULL,"
        "cas_score REAL NOT NULL,"
        "conformant INTEGER NOT NULL,"
        "control_results TEXT"
        ");"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cr_vendor_ts ON conformance_results(vendor_id, timestamp);"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS revoked_delegations ("
        "delegation_id TEXT PRIMARY KEY,"
        "reason TEXT,"
        "revoked_at TEXT NOT NULL"
        ");"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS dbc01_review_queue ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "session_id TEXT,"
        "event_id TEXT,"
        "request_id TEXT,"
        "timestamp TEXT NOT NULL,"
        "trigger_reason TEXT NOT NULL,"
        "severity TEXT,"
        "identity_assertion_text TEXT,"
        "cas_score REAL,"
        "cas_tier TEXT,"
        "status TEXT NOT NULL DEFAULT 'pending',"
        "disposition TEXT,"
        "reviewer TEXT,"
        "resolved_at TEXT,"
        "notes TEXT,"
        "UNIQUE(session_id, event_id, request_id)"
        ");"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_review_queue_status ON dbc01_review_queue(status);"
    )
    conn.commit()
    return conn


def _run_sqlite_with_retry(operation):
    attempts = 0
    while True:
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if "database is locked" in str(exc).lower() or "database is busy" in str(exc).lower():
                attempts += 1
                if attempts > 5:
                    raise
                time.sleep(0.1 * attempts)
                continue
            raise


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def append_event(event: Dict[str, Any]) -> Dict[str, Any]:
    def operation():
        conn = _get_db_connection()
        try:
            with conn:
                ev = _validate_event_shape(event, event.get("session_id"), event.get("request_id"))
                conn.execute(
                    "INSERT OR IGNORE INTO events (session_id, request_id, timestamp, event_type, state_before, state_after, input_text, policy_action, reason_code, response_text, llm_input, llm_output, policy_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        ev.get("session_id"),
                        ev.get("request_id"),
                        ev.get("timestamp"),
                        ev.get("event_type"),
                        ev.get("state_before"),
                        ev.get("state_after"),
                        ev.get("input_text"),
                        ev.get("policy_action"),
                        ev.get("reason_code"),
                        ev.get("response_text"),
                        ev.get("llm_input"),
                        ev.get("llm_output"),
                        ev.get("policy_version"),
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM events WHERE session_id = ? AND request_id = ? AND event_type = ? ORDER BY id DESC LIMIT 1",
                    (ev.get("session_id"), ev.get("request_id"), ev.get("event_type")),
                ).fetchone()
                return _row_to_dict(row) if row else {}
        finally:
            conn.close()
    return _run_sqlite_with_retry(operation)


def _validate_event_shape(event: Dict[str, Any], session_id: str, request_id: str) -> Dict[str, Any]:
    # Required keys must be present in the normalized event shape.
    required = [
        "event_type",
        "state_before",
        "state_after",
        "input_text",
        "policy_action",
        "reason_code",
        "response_text",
    ]

    if not session_id:
        raise ValueError("session_id is required for event validation")
    if not request_id:
        raise ValueError("request_id is required for event validation")

    full = dict(event)
    full.setdefault("timestamp", _utc_timestamp())
    full["session_id"] = session_id
    full["request_id"] = request_id

    missing = [k for k in required if k not in full]
    if missing:
        raise ValueError(f"event missing required fields: {missing}")

    if full["event_type"] == "RESPONSE" and full.get("response_text") is None:
        raise ValueError("RESPONSE event must include response_text")

    # All validated; return normalized event
    return full


def append_events_batch(session_id: str, events: List[Dict[str, Any]], request_id: str, mark_processed: bool = False, call_sid: Optional[str] = None, session_id_source: str = "twilio_callsid") -> None:
    """Append a batch of events for a single request_id. This is atomic.

    Args:
        session_id: call/session identifier
        events: list of event dicts (will be normalized)
        request_id: idempotency key
        mark_processed: if True, mark request as processed in same transaction
        call_sid: the upstream Twilio CallSid, or None when the request did not
            carry one. Never synthesised -- absence is recorded as absence.
        session_id_source: 'twilio_callsid' or 'synthetic'.
    """

    if mark_processed and not any(event.get("event_type") == "RESPONSE" for event in events):
        raise ValueError("mark_processed=True requires a RESPONSE event in the batch")
    if mark_processed and not request_id:
        raise ValueError("request_id is required when mark_processed=True")

    def operation():
        conn = _get_db_connection()
        try:
            with conn:
                for event in events:
                    ev = _validate_event_shape(event, session_id, request_id)
                    conn.execute(
                        "INSERT OR IGNORE INTO events (session_id, request_id, timestamp, event_type, state_before, state_after, input_text, policy_action, reason_code, response_text, llm_input, llm_output, policy_version, call_sid, session_id_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            ev.get("session_id"),
                            ev.get("request_id"),
                            ev.get("timestamp"),
                            ev.get("event_type"),
                            ev.get("state_before"),
                            ev.get("state_after"),
                            ev.get("input_text"),
                            ev.get("policy_action"),
                            ev.get("reason_code"),
                            ev.get("response_text"),
                            ev.get("llm_input"),
                            ev.get("llm_output"),
                            ev.get("policy_version"),
                            call_sid,
                            session_id_source,
                        ),
                    )
                if mark_processed:
                    conn.execute(
                        "INSERT OR IGNORE INTO processed_requests (request_id, session_id, timestamp) VALUES (?, ?, ?)",
                        (request_id, session_id, _utc_timestamp()),
                    )
        finally:
            conn.close()

    _run_sqlite_with_retry(operation)


def mark_request_processed(request_id: str, session_id: str) -> None:
    if not request_id:
        return

    def operation():
        conn = _get_db_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT OR IGNORE INTO processed_requests (request_id, session_id, timestamp) VALUES (?, ?, ?)",
                    (request_id, session_id, _utc_timestamp()),
                )
        finally:
            conn.close()

    _run_sqlite_with_retry(operation)


def get_events(session_id: str) -> List[Dict[str, Any]]:
    def operation():
        conn = _get_db_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [_row_to_dict(row) for row in rows]
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def is_duplicate_request(request_id: str) -> bool:
    if not request_id:
        return False

    def operation():
        conn = _get_db_connection()
        try:
            row = conn.execute(
                "SELECT 1 FROM processed_requests WHERE request_id = ? LIMIT 1",
                (request_id,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def get_response_for_request(request_id: str) -> Optional[str]:
    if not request_id:
        return None

    def operation():
        conn = _get_db_connection()
        try:
            row = conn.execute(
                "SELECT response_text FROM events WHERE request_id = ? AND event_type = 'RESPONSE' ORDER BY id DESC LIMIT 1",
                (request_id,),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def get_events_for_request(request_id: str) -> List[Dict[str, Any]]:
    if not request_id:
        return []

    def operation():
        conn = _get_db_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM events WHERE request_id = ? ORDER BY id ASC",
                (request_id,),
            ).fetchall()
            return [_row_to_dict(row) for row in rows]
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def reconstruct_session_from_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    session = {
        "session_id": events[0]["session_id"] if events else "unknown",
        "state": "INIT",
        "disclosed": False,
        "turn_count": 0,
        "last_user_text": "",
        "policy_version": "nhid_policy_v1",
    }
    for event in events:
        if event["event_type"] == "USER_INPUT":
            session["last_user_text"] = event.get("input_text") or ""
            session["turn_count"] += 1
        elif event["event_type"] == "POLICY_DECISION":
            if event.get("reason_code") == "DISCLOSURE_GATE":
                session["disclosed"] = True
            session["state"] = event.get("state_after") or session["state"]
        elif event["event_type"] == "STATE_TRANSITION":
            session["state"] = event.get("state_after") or session["state"]

        if event.get("policy_action") == "CALL_STARTED":
            session["state"] = event.get("state_after") or session["state"]
        if event.get("policy_version"):
            session["policy_version"] = event.get("policy_version")
    return session


def reconstruct_session(session_id: str) -> Dict[str, Any]:
    events = get_events(session_id)
    session = {
        "session_id": session_id,
        "state": "INIT",
        "disclosed": False,
        "turn_count": 0,
        "last_user_text": "",
        "policy_version": "nhid_policy_v1",
    }
    for event in events:
        if event["event_type"] == "USER_INPUT":
            session["last_user_text"] = event.get("input_text") or ""
            session["turn_count"] += 1
        elif event["event_type"] == "POLICY_DECISION":
            if event.get("reason_code") == "DISCLOSURE_GATE":
                session["disclosed"] = True
            session["state"] = event.get("state_after") or session["state"]
        elif event["event_type"] == "STATE_TRANSITION":
            session["state"] = event.get("state_after") or session["state"]

        if event.get("policy_action") == "CALL_STARTED":
            session["state"] = event.get("state_after") or session["state"]
        if event.get("policy_version"):
            session["policy_version"] = event.get("policy_version")
    return session


def get_session_trace(session_id: str) -> Dict[str, Any]:
    events = get_events(session_id)
    return {
        "session_id": session_id,
        "reconstructed_state": reconstruct_session(session_id),
        "events": events,
    }


def replay(session_id: str) -> List[Dict[str, Any]]:
    return get_events(session_id)


# ── Vendor conformance metrics ────────────────────────────────────────────────

def record_conformance_result(
    vendor_id: str,
    session_id: str,
    cas_score: float,
    conformant: bool,
    control_results: Dict[str, Any] | None = None,
) -> None:
    """Persist a single conformance check result for vendor trend analytics."""
    if not vendor_id:
        raise ValueError("vendor_id is required")
    if not session_id:
        raise ValueError("session_id is required")

    def operation():
        conn = _get_db_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO conformance_results "
                    "(vendor_id, session_id, timestamp, cas_score, conformant, control_results) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        vendor_id,
                        session_id,
                        _utc_timestamp(),
                        float(cas_score),
                        1 if conformant else 0,
                        json.dumps(control_results) if control_results else None,
                    ),
                )
        finally:
            conn.close()

    _run_sqlite_with_retry(operation)


# ── NHID-Auth v2 delegation revocation (durable, survives stateless Lambda) ───

def record_revocation(delegation_id: str, reason: str = "") -> None:
    """Durably revoke a delegation_id. AgentIdentityManager's own revocation
    dicts are in-memory and reset every Lambda invocation, so this table is
    the revocation store of record for verify_passport callers."""
    if not delegation_id:
        raise ValueError("delegation_id is required")

    def operation():
        conn = _get_db_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO revoked_delegations (delegation_id, reason, revoked_at) "
                    "VALUES (?, ?, ?)",
                    (delegation_id, reason, _utc_timestamp()),
                )
        finally:
            conn.close()

    _run_sqlite_with_retry(operation)


def is_delegation_revoked(delegation_id: str) -> bool:
    if not delegation_id:
        return False

    def operation():
        conn = _get_db_connection()
        try:
            row = conn.execute(
                "SELECT 1 FROM revoked_delegations WHERE delegation_id = ? LIMIT 1",
                (delegation_id,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


# ── DBC-01 human-review queue (docs/dbc01-human-review-sop.md) ───────────────

REVIEW_DISPOSITIONS = ("confirmed_impersonation", "false_positive")


def enqueue_dbc01_review(
    session_id: str | None,
    event_id: str | None,
    request_id: str | None,
    trigger_reason: str,
    severity: str | None = None,
    identity_assertion_text: str | None = None,
    cas_score: float | None = None,
    cas_tier: str | None = None,
) -> Dict[str, Any]:
    """Queue a session for human review. Returns the inserted row."""
    if not trigger_reason:
        raise ValueError("trigger_reason is required")

    def operation():
        conn = _get_db_connection()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO dbc01_review_queue "
                    "(session_id, event_id, request_id, timestamp, trigger_reason, severity, "
                    "identity_assertion_text, cas_score, cas_tier, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending') "
                    "ON CONFLICT(session_id, event_id, request_id) DO NOTHING",
                    (
                        session_id,
                        event_id,
                        request_id,
                        _utc_timestamp(),
                        trigger_reason,
                        severity,
                        identity_assertion_text,
                        cas_score,
                        cas_tier,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM dbc01_review_queue WHERE session_id IS ? AND event_id IS ? "
                    "AND request_id IS ?",
                    (session_id, event_id, request_id),
                ).fetchone()
                return _row_to_dict(row)
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def list_pending_dbc01_reviews() -> List[Dict[str, Any]]:
    def operation():
        conn = _get_db_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM dbc01_review_queue WHERE status = 'pending' ORDER BY id ASC"
            ).fetchall()
            return [_row_to_dict(row) for row in rows]
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def get_dbc01_review(queue_id: int) -> Optional[Dict[str, Any]]:
    def operation():
        conn = _get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM dbc01_review_queue WHERE id = ?", (queue_id,)
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def resolve_dbc01_review(
    queue_id: int, disposition: str, reviewer: str = "", notes: str = ""
) -> Dict[str, Any]:
    """Resolve a pending review with a disposition. One-way transition —
    raises if the queue_id doesn't exist or is already resolved."""
    if disposition not in REVIEW_DISPOSITIONS:
        raise ValueError(f"disposition must be one of {REVIEW_DISPOSITIONS}, got {disposition!r}")

    def operation():
        conn = _get_db_connection()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE dbc01_review_queue SET status = 'resolved', disposition = ?, "
                    "reviewer = ?, resolved_at = ?, notes = ? WHERE id = ? AND status = 'pending'",
                    (disposition, reviewer, _utc_timestamp(), notes, queue_id),
                )
                if cur.rowcount == 0:
                    row = conn.execute(
                        "SELECT * FROM dbc01_review_queue WHERE id = ?", (queue_id,)
                    ).fetchone()
                    if row is None:
                        raise ValueError(f"No review queued with id={queue_id}")
                    raise ValueError(f"Review id={queue_id} is already resolved")

                resolved = conn.execute(
                    "SELECT * FROM dbc01_review_queue WHERE id = ?", (queue_id,)
                ).fetchone()
                return _row_to_dict(resolved)
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)


def get_vendor_metrics(vendor_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Return aggregated conformance metrics for a vendor over the last N days.

    Returns:
        {
            "vendor_id": str,
            "period_days": int,
            "calls_total": int,
            "pass_rate": float,        # 0.0–1.0
            "cas_avg": float,          # average CAS score
            "cas_min": float,
            "cas_max": float,
        }
    """
    if not vendor_id:
        raise ValueError("vendor_id is required")

    def operation():
        conn = _get_db_connection()
        try:
            cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            # SQLite date arithmetic: filter rows within the last N days
            row = conn.execute(
                "SELECT "
                "  COUNT(*) AS total,"
                "  SUM(conformant) AS passed,"
                "  AVG(cas_score) AS cas_avg,"
                "  MIN(cas_score) AS cas_min,"
                "  MAX(cas_score) AS cas_max "
                "FROM conformance_results "
                "WHERE vendor_id = ? "
                "  AND timestamp >= datetime('now', ? || ' days')",
                (vendor_id, f"-{days}"),
            ).fetchone()
            total = row["total"] or 0
            passed = row["passed"] or 0
            return {
                "vendor_id": vendor_id,
                "period_days": days,
                "calls_total": total,
                "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
                "cas_avg": round(row["cas_avg"] or 0.0, 4),
                "cas_min": round(row["cas_min"] or 0.0, 4),
                "cas_max": round(row["cas_max"] or 0.0, 4),
            }
        finally:
            conn.close()

    return _run_sqlite_with_retry(operation)
