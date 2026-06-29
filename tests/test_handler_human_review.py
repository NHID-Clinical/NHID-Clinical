"""Integration tests: a conformance check that trips DBC-01 must be queued
for human review (docs/dbc01-human-review-sop.md), and a clean one must not."""
import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import nhid_event_store as store
from functions.handler import lambda_handler


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_nhid.db"
    monkeypatch.setattr(store, "DB_PATH", db_file)
    yield


def _make_event(body: dict) -> dict:
    return {"httpMethod": "POST", "path": "/v1/demo/check", "body": json.dumps(body)}


def _base_body() -> dict:
    return {
        "session": {"turn_count": 1, "escalation_path_available": True},
        "event": {
            "event_id": "test-review-001",
            "timestamp": "2026-06-12T00:00:00Z",
            "session_id": "sess-review-001",
            "request_id": "req-review-001",
            "event_type": "POLICY",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "counterparty_type": "human_operator",
            "healthcare_governance": {
                "disclosure_timestamp": "2026-06-12T00:00:01Z",
                "identity_assertion_text": "",
                "deceptive_artifact_flags": [],
                "escalation_timestamp": None,
                "escalation_outcome": None,
                "phi_accessed": [],
            },
            "input_payload": {"speech_text": "", "raw_form_fields": None},
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version": "1.0",
            },
            "actor_id": "test-agent",
            "replay_mode": "test",
            "external_calls_cached": True,
        },
    }


class TestDBC01TriggersReview:
    def test_impersonation_phrase_queues_review(self):
        body = _base_body()
        body["event"]["healthcare_governance"]["identity_assertion_text"] = "I am a human representative"
        resp = lambda_handler(_make_event(body), None)
        result = json.loads(resp["body"])

        assert result["human_review"]["queued"] is True
        assert result["human_review"]["trigger_reason"] == "DBC01_IMPERSONATION_PHRASE_DETECTED"
        assert result["human_review"]["queue_id"] is not None

        pending = store.list_pending_dbc01_reviews()
        assert len(pending) == 1
        assert pending[0]["session_id"] == "sess-review-001"

    def test_clean_response_does_not_queue_review(self):
        resp = lambda_handler(_make_event(_base_body()), None)
        result = json.loads(resp["body"])

        assert result["human_review"]["queued"] is False
        assert result["human_review"]["trigger_reason"] is None
        assert store.list_pending_dbc01_reviews() == []

    def test_low_cas_without_dbc01_violation_queues_review(self):
        body = _base_body()
        del body["event"]["request_id"]  # trips ATR-01 CRITICAL -> CAS < 0.75
        resp = lambda_handler(_make_event(body), None)
        result = json.loads(resp["body"])

        assert result["human_review"]["queued"] is True
        assert result["human_review"]["trigger_reason"] == "CAS_REVIEW_REQUIRED"
        assert result["human_review"]["queue_id"] is not None

    def test_enqueue_failure_does_not_report_queued(self, monkeypatch):
        def _raise(**kwargs):
            raise sqlite3.OperationalError("read-only database")

        monkeypatch.setattr(store, "enqueue_dbc01_review", _raise)

        body = _base_body()
        body["event"]["healthcare_governance"]["identity_assertion_text"] = "I am a human representative"
        resp = lambda_handler(_make_event(body), None)
        result = json.loads(resp["body"])

        assert result["conformant"] is False
        assert result["human_review"]["queued"] is False
        assert result["human_review"]["queue_id"] is None
        assert result["human_review"]["trigger_reason"] == "DBC01_IMPERSONATION_PHRASE_DETECTED"
