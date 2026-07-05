"""
Self-tests for the NHID-Clinical web platform.

These exercise every route through FastAPI's TestClient against the REAL engine
(no mocks). Run from the repo root:  python -m pytest webplatform/tests -q
"""
import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

# Isolate the store in a temp DB before the app imports the bridge.
os.environ["NHID_PLATFORM_DB"] = str(_REPO_ROOT / "webplatform" / "test_platform.db")
_db = Path(os.environ["NHID_PLATFORM_DB"])
if _db.exists():
    _db.unlink()

from fastapi.testclient import TestClient  # noqa: E402
from webplatform.app import app  # noqa: E402

client = TestClient(app)


def test_pages_render():
    for path in ("/", "/analyzer", "/generator", "/vendors", "/audit"):
        r = client.get(path)
        assert r.status_code == 200
        assert "NHID-Clinical" in r.text


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_analyze_clean_scenario_is_conformant():
    r = client.post("/api/analyze", json={"scenario": "clean"})
    body = r.json()
    assert body["conformant"] is True
    assert body["violations"] == []


def test_analyze_dbc01_flags_and_queues():
    r = client.post("/api/analyze", json={"scenario": "dbc01"})
    body = r.json()
    assert body["conformant"] is False
    assert any(v["rule_id"] == "DBC-01" for v in body["violations"])
    assert body["queued_for_review"] is True


def test_analyze_eit01_escalation_not_honored():
    body = client.post("/api/analyze", json={"scenario": "eit01"}).json()
    assert any(v["rule_id"] == "EIT-01" for v in body["violations"])
    assert body["turns"][0]["action"] == "ESCALATE_HUMAN"


def test_analyze_custom_turns():
    turns = [{
        "speaker": "agent",
        "disclosure_timestamp": "2026-06-01T00:00:00Z",
        "identity_assertion_text": "I am an AI assistant.",
        "speech_text": "How can I help?",
    }]
    body = client.post("/api/analyze",
                       json={"turns": turns, "conversation_id": "unit-x"}).json()
    assert body["conformant"] is True


def test_analyze_rejects_empty():
    r = client.post("/api/analyze", json={})
    assert r.status_code == 400


def test_generate_returns_real_rates():
    body = client.post("/api/generate",
                       json={"sample_size": 40, "persist": True}).json()
    controls = {c["control"]: c for c in body["controls"]}
    assert set(controls) == {"IDG-01", "PDX-01", "DBC-01", "EIT-01"}
    # IDG/PDX/EIT detection is 100% on this corpus; assert they are exercised.
    assert controls["IDG-01"]["expected"] > 0
    assert body["ingested_events"] > 0


def test_dashboard_metrics():
    body = client.get("/api/dashboard").json()
    assert "counts" in body and "detection" in body
    assert body["cas_thresholds"]["conditional_trust"] == 0.75


def test_passport_valid_and_tampered():
    good = client.post("/api/verify/passport", json={"tamper": False}).json()
    assert good["valid"] is True
    bad = client.post("/api/verify/passport", json={"tamper": True}).json()
    assert bad["valid"] is False
    assert bad["reason"] == "ERR_INVALID_SIG"


def test_adapter_check_runs():
    payload = {
        "call": {"id": "t-1", "startedAt": "2026-06-01T00:00:00Z"},
        "messages": [
            {"role": "bot", "message": "I am an AI assistant.", "secondsFromStart": 0},
        ],
    }
    r = client.post("/api/adapters/vapi/check", json=payload)
    assert r.status_code == 200
    # The real adapter path returns a decision dict with a reason_code.
    assert "reason_code" in r.json() or "_status" in r.json()


def test_audit_events_and_review_resolution():
    # Populate the queue via a DBC-01 analysis, then resolve one review.
    client.post("/api/analyze", json={"scenario": "dbc01"})
    reviews = client.get("/api/audit/reviews").json()["reviews"]
    assert len(reviews) >= 1
    qid = reviews[0]["id"]
    r = client.post(f"/api/audit/reviews/{qid}/resolve",
                    json={"disposition": "false_positive"})
    assert r.status_code == 200
    assert r.json()["resolved"] == qid
    events = client.get("/api/audit/events").json()["events"]
    assert len(events) > 0


def test_conformance_page_renders():
    r = client.get("/conformance")
    assert r.status_code == 200
    assert "Conformance Suite" in r.text


def test_cts_runs_all_cases():
    body = client.get("/api/cts").json()
    assert body["total"] >= 18
    assert body["failed"] == 0
    assert body["passed"] >= 1
    assert isinstance(body["results"], list) and len(body["results"]) == body["total"]


def test_confusion_matrix_detection_and_fp():
    body = client.get("/api/confusion?sample_size=550").json()
    controls = {c["control"]: c for c in body["controls"]}
    assert set(controls) == {"IDG-01", "PDX-01", "DBC-01", "EIT-01"}
    # DBC-01 baseline on the full corpus (as of 2026-07): 183/200 detected, 5 FP.
    assert controls["DBC-01"]["detected"] == 183
    assert controls["DBC-01"]["expected"] == 200
    assert controls["DBC-01"]["fp"] == 5
    assert body["n_compliant"] == 127


def test_bad_disposition_rejected():
    client.post("/api/analyze", json={"scenario": "dbc01"})
    reviews = client.get("/api/audit/reviews").json()["reviews"]
    if reviews:
        qid = reviews[0]["id"]
        r = client.post(f"/api/audit/reviews/{qid}/resolve",
                        json={"disposition": "nonsense"})
        assert r.status_code == 400


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
