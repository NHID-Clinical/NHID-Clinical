"""CRUD tests for nhid_event_store's dbc01_review_queue table."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import nhid_event_store as store


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_nhid.db"
    monkeypatch.setattr(store, "DB_PATH", db_file)
    yield


class TestEnqueue:
    def test_enqueue_inserts_pending_row(self):
        row = store.enqueue_dbc01_review(
            session_id="sess-1",
            event_id="evt-1",
            request_id="req-1",
            trigger_reason="DBC01_IMPERSONATION_PHRASE_DETECTED",
            severity="major",
            identity_assertion_text="I am a human representative",
            cas_score=0.6,
            cas_tier="Review Required",
        )
        assert row["status"] == "pending"
        assert row["session_id"] == "sess-1"
        assert row["trigger_reason"] == "DBC01_IMPERSONATION_PHRASE_DETECTED"
        assert row["disposition"] is None

    def test_missing_trigger_reason_raises(self):
        with pytest.raises(ValueError, match="trigger_reason"):
            store.enqueue_dbc01_review("sess-1", "evt-1", "req-1", trigger_reason="")

    def test_duplicate_identity_is_idempotent(self):
        first = store.enqueue_dbc01_review(
            "sess-dup", "evt-dup", "req-dup", trigger_reason="CAS_REVIEW_REQUIRED"
        )
        second = store.enqueue_dbc01_review(
            "sess-dup", "evt-dup", "req-dup", trigger_reason="CAS_REVIEW_REQUIRED"
        )
        assert first["id"] == second["id"]
        assert len(store.list_pending_dbc01_reviews()) == 1


class TestListPending:
    def test_lists_only_pending(self):
        a = store.enqueue_dbc01_review("sess-a", "evt-a", "req-a", trigger_reason="CAS_REVIEW_REQUIRED")
        store.enqueue_dbc01_review("sess-b", "evt-b", "req-b", trigger_reason="CAS_REVIEW_REQUIRED")
        store.resolve_dbc01_review(a["id"], "false_positive", reviewer="alice")

        pending = store.list_pending_dbc01_reviews()
        assert len(pending) == 1
        assert pending[0]["session_id"] == "sess-b"

    def test_empty_queue_returns_empty_list(self):
        assert store.list_pending_dbc01_reviews() == []


class TestGetReview:
    def test_get_existing_review(self):
        row = store.enqueue_dbc01_review("sess-1", "evt-1", "req-1", trigger_reason="X")
        fetched = store.get_dbc01_review(row["id"])
        assert fetched["id"] == row["id"]

    def test_get_missing_review_returns_none(self):
        assert store.get_dbc01_review(9999) is None


class TestResolve:
    def test_resolve_sets_disposition_and_status(self):
        row = store.enqueue_dbc01_review("sess-1", "evt-1", "req-1", trigger_reason="X")
        resolved = store.resolve_dbc01_review(
            row["id"], "confirmed_impersonation", reviewer="bob", notes="escalated"
        )
        assert resolved["status"] == "resolved"
        assert resolved["disposition"] == "confirmed_impersonation"
        assert resolved["reviewer"] == "bob"
        assert resolved["notes"] == "escalated"
        assert resolved["resolved_at"]

    def test_resolve_removes_from_pending_list(self):
        row = store.enqueue_dbc01_review("sess-1", "evt-1", "req-1", trigger_reason="X")
        store.resolve_dbc01_review(row["id"], "false_positive")
        assert store.list_pending_dbc01_reviews() == []

    def test_resolve_unknown_id_raises(self):
        with pytest.raises(ValueError, match="No review queued"):
            store.resolve_dbc01_review(9999, "false_positive")

    def test_resolve_already_resolved_raises(self):
        row = store.enqueue_dbc01_review("sess-1", "evt-1", "req-1", trigger_reason="X")
        store.resolve_dbc01_review(row["id"], "false_positive")
        with pytest.raises(ValueError, match="already resolved"):
            store.resolve_dbc01_review(row["id"], "confirmed_impersonation")

    def test_invalid_disposition_raises(self):
        row = store.enqueue_dbc01_review("sess-1", "evt-1", "req-1", trigger_reason="X")
        with pytest.raises(ValueError, match="disposition must be one of"):
            store.resolve_dbc01_review(row["id"], "not_a_real_disposition")
