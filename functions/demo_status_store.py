"""
Live status store for the website demo features (Twilio scripted inbound demo,
Beacon outbound demo) — backed by DynamoDB with a TTL so sessions self-clean.

This is infrastructure for the demo website feature, NOT the NHID-Clinical
governance framework itself. Boto3 is provided by the Lambda runtime; it is
not a project dependency for local/test use — pass `table=` explicitly in
tests to avoid needing it installed locally.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

DEMO_CALL_STATUS_TABLE_ENV = "DEMO_CALL_STATUS_TABLE"
TTL_SECONDS = 60 * 60  # 1 hour — sessions self-clean via DynamoDB TTL

#: Fixed key mirroring the most recent demo call's status. The website
#: visitor watching the demo doesn't necessarily know their own call's
#: Twilio CallSid, so polling this fixed key shows "whichever call is
#: live right now" without requiring any caller-to-browser correlation.
LATEST_SESSION_KEY = "_latest_demo_call"


def _table():
    import boto3  # local import: only required in the real Lambda runtime

    table_name = os.environ.get(DEMO_CALL_STATUS_TABLE_ENV, "")
    if not table_name:
        raise RuntimeError(f"{DEMO_CALL_STATUS_TABLE_ENV} environment variable is not set")
    return boto3.resource("dynamodb").Table(table_name)


def put_turn(
    session_id: str,
    turn_index: int,
    decision: dict[str, Any],
    *,
    session_state: Optional[dict[str, Any]] = None,
    extra: Optional[dict[str, Any]] = None,
    table=None,
) -> dict[str, Any]:
    """Append a turn's decision to a session's status record. Returns the stored item."""
    table = table if table is not None else _table()
    now = int(time.time())

    existing = table.get_item(Key={"session_id": session_id}).get("Item") or {}
    turns = list(existing.get("turns", []))
    turns.append({"turn_index": turn_index, "decision": decision})

    item: dict[str, Any] = {
        "session_id": session_id,
        "turns": turns,
        "session_state": session_state if session_state is not None else existing.get("session_state", {}),
        "ttl": now + TTL_SECONDS,
        "updated_at": now,
    }
    if extra:
        item.update(extra)

    table.put_item(Item=item)
    return item


def get_status(session_id: str, *, table=None) -> dict[str, Any]:
    """Return the session's accumulated status, or {} if the session is unknown/expired."""
    table = table if table is not None else _table()
    item = table.get_item(Key={"session_id": session_id}).get("Item")
    return item or {}


def set_latest(item: dict[str, Any], *, table=None) -> None:
    """Mirror a call's full status item under LATEST_SESSION_KEY (overwritten,
    not accumulated). Lets the website show live status for whichever demo
    call is in progress, without the visitor needing to know their CallSid."""
    table = table if table is not None else _table()
    mirrored = dict(item)
    mirrored["session_id"] = LATEST_SESSION_KEY
    table.put_item(Item=mirrored)
