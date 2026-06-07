import os
import sqlite3
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "nhid_events.db"


def _utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


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
        "policy_version TEXT"
        ");"
    )
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


def append_events_batch(session_id: str, events: List[Dict[str, Any]], request_id: str, mark_processed: bool = False) -> None:
    """Append a batch of events for a single request_id. This is atomic.

    Args:
        session_id: call/session identifier
        events: list of event dicts (will be normalized)
        request_id: idempotency key
        mark_processed: if True, mark request as processed in same transaction
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
