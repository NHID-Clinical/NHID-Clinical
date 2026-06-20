"""
Best-effort rate limiter for public website demo forms (e.g. the Beacon
outbound-call demo) — backed by DynamoDB with a TTL so windows self-clean.

This is abuse deterrence for a free demo form, not a security boundary:
check_and_increment() is a plain get-then-put (not a conditional atomic
increment), so concurrent requests in the same window could both squeak
through right at the limit. That tradeoff is acceptable here — the goal is
blocking casual bot hammering and call-harassment-via-form, not withstanding
a determined attacker.

Website demo feature infrastructure, NOT the NHID-Clinical governance
framework itself.
"""

from __future__ import annotations

import os
import time

RATE_LIMIT_TABLE_ENV = "RATE_LIMIT_TABLE"


def _table():
    import boto3  # local import: only required in the real Lambda runtime

    table_name = os.environ.get(RATE_LIMIT_TABLE_ENV, "")
    if not table_name:
        raise RuntimeError(f"{RATE_LIMIT_TABLE_ENV} environment variable is not set")
    return boto3.resource("dynamodb").Table(table_name)


def check_and_increment(key: str, limit: int, window_seconds: int, *, table=None) -> bool:
    """Record one hit for `key` in the current fixed window.

    Returns True if the hit is within `limit` (and has been recorded), False
    if `key` has already hit `limit` in this window (caller should reject —
    nothing is recorded in that case).
    """
    table = table if table is not None else _table()
    now = int(time.time())
    window_start = now - (now % window_seconds)
    rl_key = f"{key}:{window_start}"

    existing = table.get_item(Key={"rl_key": rl_key}).get("Item") or {}
    count = int(existing.get("count", 0))

    if count >= limit:
        return False

    table.put_item(Item={
        "rl_key": rl_key,
        "count": count + 1,
        "ttl": window_start + window_seconds + 60,
    })
    return True
