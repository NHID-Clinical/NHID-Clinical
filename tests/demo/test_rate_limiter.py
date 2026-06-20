"""
Tests for functions/rate_limiter.py — abuse deterrence for public website
demo forms. Website demo feature infrastructure, NOT the NHID-Clinical
governance framework (lives under tests/demo/, excluded from the framework's
pytest tests/ baseline — see pytest.ini).

Uses a hand-rolled fake DynamoDB table (no moto dependency), mirroring the
pattern in tests/demo/test_demo_status_store.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from functions import rate_limiter  # noqa: E402


class _FakeTable:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def get_item(self, Key: dict) -> dict:
        item = self.items.get(Key["rl_key"])
        return {"Item": item} if item is not None else {}

    def put_item(self, Item: dict) -> None:
        self.items[Item["rl_key"]] = Item


def test_allows_up_to_limit():
    table = _FakeTable()
    for _ in range(3):
        assert rate_limiter.check_and_increment("ip-1", limit=3, window_seconds=3600, table=table) is True


def test_blocks_once_limit_exceeded():
    table = _FakeTable()
    for _ in range(3):
        rate_limiter.check_and_increment("ip-1", limit=3, window_seconds=3600, table=table)

    assert rate_limiter.check_and_increment("ip-1", limit=3, window_seconds=3600, table=table) is False


def test_different_keys_have_independent_limits():
    table = _FakeTable()
    for _ in range(3):
        rate_limiter.check_and_increment("ip-1", limit=3, window_seconds=3600, table=table)

    assert rate_limiter.check_and_increment("ip-2", limit=3, window_seconds=3600, table=table) is True


def test_blocked_attempt_does_not_increment_further():
    table = _FakeTable()
    for _ in range(3):
        rate_limiter.check_and_increment("ip-1", limit=3, window_seconds=3600, table=table)

    rate_limiter.check_and_increment("ip-1", limit=3, window_seconds=3600, table=table)
    rate_limiter.check_and_increment("ip-1", limit=3, window_seconds=3600, table=table)

    matching = [v for k, v in table.items.items() if k.startswith("ip-1:")]
    assert len(matching) == 1
    assert matching[0]["count"] == 3


def test_sets_ttl_past_window_end():
    table = _FakeTable()
    rate_limiter.check_and_increment("ip-1", limit=5, window_seconds=3600, table=table)
    item = next(iter(table.items.values()))
    assert item["ttl"] > 0
