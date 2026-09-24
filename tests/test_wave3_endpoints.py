"""6 deterministic tests for the Wave 3 handler routes: badge, metrics, pilot enroll."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from functions.handler import lambda_handler



class TestMetricsSummaryEndpoint:
    def test_missing_vendor_id_returns_400(self):
        resp = lambda_handler({
            "httpMethod": "GET",
            "path": "/v1/vendor/metrics/summary",
            "queryStringParameters": {},
        }, None)
        assert resp["statusCode"] == 400

    def test_valid_vendor_id_returns_metrics_shape(self):
        resp = lambda_handler({
            "httpMethod": "GET",
            "path": "/v1/vendor/metrics/summary",
            "queryStringParameters": {"vendor_id": "vendor_test_empty"},
        }, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        for key in ("vendor_id", "period_days", "calls_total", "pass_rate", "cas_avg"):
            assert key in body


class TestPilotEnrollEndpoint:
    def test_missing_org_name_returns_400(self):
        resp = lambda_handler({
            "httpMethod": "POST",
            "path": "/v1/pilot/enroll",
            "body": json.dumps({"contact_email": "ops@example.com"}),
        }, None)
        assert resp["statusCode"] == 400

    def test_valid_enrollment_returns_pilot_id(self):
        resp = lambda_handler({
            "httpMethod": "POST",
            "path": "/v1/pilot/enroll",
            "body": json.dumps({
                "org_name": "Acme Health Plan",
                "contact_email": "ops@acmehealth.example",
                "vendor_platform": "vapi",
            }),
        }, None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["pilot_id"].startswith("pilot-")
        assert body["status"] == "enrolled"
        assert "next_steps_url" in body
