"""
Tests for functions/demo_status_store.py — website demo feature infrastructure,
NOT the NHID-Clinical governance framework. Lives under tests/demo/ so it is
excluded from the framework's pytest tests/ baseline (see pytest.ini).

Uses a hand-rolled fake DynamoDB table (no moto dependency) since boto3 is
intentionally not a project dependency for local/test use.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from functions import demo_status_store  # noqa: E402


class _FakeTable:
    """Minimal stand-in for a boto3 DynamoDB Table resource."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def get_item(self, Key: dict) -> dict:
        session_id = Key["session_id"]
        item = self.items.get(session_id)
        return {"Item": item} if item is not None else {}

    def put_item(self, Item: dict) -> None:
        self.items[Item["session_id"]] = Item


def test_put_turn_sets_ttl():
    table = _FakeTable()
    item = demo_status_store.put_turn("call-1", 0, {"action": "LOG_ONLY"}, table=table)
    assert "ttl" in item
    assert item["ttl"] > 0


def test_put_turn_accumulates_multiple_turns():
    table = _FakeTable()
    demo_status_store.put_turn("call-1", 0, {"action": "LOG_ONLY"}, table=table)
    demo_status_store.put_turn("call-1", 1, {"action": "DENY_DATA"}, table=table)

    status = demo_status_store.get_status("call-1", table=table)
    assert len(status["turns"]) == 2
    assert status["turns"][0]["turn_index"] == 0
    assert status["turns"][1]["turn_index"] == 1
    assert status["turns"][1]["decision"]["action"] == "DENY_DATA"


def test_put_turn_carries_session_state_forward():
    table = _FakeTable()
    demo_status_store.put_turn(
        "call-1", 0, {"action": "LOG_ONLY"}, session_state={"turn_count": 1}, table=table
    )
    status = demo_status_store.get_status("call-1", table=table)
    assert status["session_state"] == {"turn_count": 1}

    # Omitting session_state on the next call preserves the prior value.
    demo_status_store.put_turn("call-1", 1, {"action": "LOG_ONLY"}, table=table)
    status = demo_status_store.get_status("call-1", table=table)
    assert status["session_state"] == {"turn_count": 1}


def test_put_turn_merges_extra_fields():
    table = _FakeTable()
    demo_status_store.put_turn(
        "call-1", 0, {"action": "LOG_ONLY"}, extra={"script": "compliant"}, table=table
    )
    status = demo_status_store.get_status("call-1", table=table)
    assert status["script"] == "compliant"


def test_get_status_missing_session_returns_empty_dict():
    table = _FakeTable()
    assert demo_status_store.get_status("does-not-exist", table=table) == {}


def test_set_latest_mirrors_under_fixed_key():
    table = _FakeTable()
    item = demo_status_store.put_turn("call-1", 0, {"action": "LOG_ONLY"}, table=table)
    demo_status_store.set_latest(item, table=table)

    latest = demo_status_store.get_status(demo_status_store.LATEST_SESSION_KEY, table=table)
    assert latest["turns"] == item["turns"]
    assert latest["session_id"] == demo_status_store.LATEST_SESSION_KEY


def test_set_latest_overwrites_rather_than_accumulates():
    table = _FakeTable()
    item_a = demo_status_store.put_turn("call-a", 0, {"action": "LOG_ONLY"}, table=table)
    demo_status_store.set_latest(item_a, table=table)

    item_b = demo_status_store.put_turn("call-b", 0, {"action": "DENY_DATA"}, table=table)
    demo_status_store.set_latest(item_b, table=table)

    latest = demo_status_store.get_status(demo_status_store.LATEST_SESSION_KEY, table=table)
    assert len(latest["turns"]) == 1
    assert latest["turns"][0]["decision"]["action"] == "DENY_DATA"
