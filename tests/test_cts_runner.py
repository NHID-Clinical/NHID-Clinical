"""5 deterministic tests for the NHID CTS runner and hosted evaluation endpoint."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cts_runner import run_cts
from functions.handler import lambda_handler


# ── Unit tests: run_cts() ────────────────────────────────────────────────────

class TestCTSRunner:
    def test_run_cts_returns_required_structure(self):
        report = run_cts()
        assert isinstance(report, dict)
        for key in ("passed", "failed", "skipped", "total", "results"):
            assert key in report, f"Missing key: {key}"
        assert isinstance(report["results"], list)
        assert report["total"] == len(report["results"])

    def test_all_policy_engine_cases_pass(self):
        report = run_cts()
        failures = [r for r in report["results"] if r["status"] == "fail"]
        assert failures == [], (
            "CTS failures: " + ", ".join(
                f"{r['test_id']}: {r['detail']}" for r in failures
            )
        )

    def test_http_only_edge_cases_are_skipped(self):
        report = run_cts()
        skipped_ids = {r["test_id"] for r in report["results"] if r["status"] == "skip"}
        assert "EDGE-MISSING-CALLSID" in skipped_ids
        assert "EDGE-MISSING-ALL-FIELDS" in skipped_ids

    def test_subset_by_test_ids_filters_correctly(self):
        report = run_cts(test_ids=["IDG-01-PASS", "IDG-01-FAIL-LATE"])
        assert report["total"] == 2
        ids = {r["test_id"] for r in report["results"]}
        assert ids == {"IDG-01-PASS", "IDG-01-FAIL-LATE"}

    def test_known_violation_idg01_fail_late(self):
        report = run_cts(test_ids=["IDG-01-FAIL-LATE"])
        result = report["results"][0]
        assert result["status"] == "pass", f"Expected pass, got: {result['detail']}"
        assert result["actual_action"] == "DENY_DATA"
        assert result["violations_matched"] is True


# ── Integration test: POST /v1/cts/evaluate endpoint ────────────────────────

class TestCTSEvaluateEndpoint:
    def _make_event(self, body: dict | None = None) -> dict:
        return {
            "httpMethod": "POST",
            "path": "/v1/cts/evaluate",
            "body": json.dumps(body or {}),
        }

    def test_endpoint_returns_200_with_report(self):
        resp = lambda_handler(self._make_event(), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        for key in ("passed", "failed", "skipped", "total", "results"):
            assert key in body

    def test_endpoint_subset_by_test_ids(self):
        resp = lambda_handler(
            self._make_event({"test_ids": ["PDX-01-PASS-CLEARED"]}), None
        )
        body = json.loads(resp["body"])
        assert body["total"] == 1
        assert body["results"][0]["test_id"] == "PDX-01-PASS-CLEARED"

    def test_endpoint_invalid_test_ids_type_returns_400(self):
        resp = lambda_handler(
            self._make_event({"test_ids": "not-a-list"}), None
        )
        assert resp["statusCode"] == 400

    def test_endpoint_all_cases_no_failures(self):
        resp = lambda_handler(self._make_event(), None)
        body = json.loads(resp["body"])
        assert body["failed"] == 0, (
            "CTS endpoint failures: " + str([
                r for r in body["results"] if r["status"] == "fail"
            ])
        )
