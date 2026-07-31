"""5 deterministic tests verifying the CAS block is present in every conformance response."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from functions.handler import lambda_handler

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_event(body: dict) -> dict:
    return {"httpMethod": "POST", "path": "/v1/demo/check", "body": json.dumps(body)}


def _compliant_body() -> dict:
    return {
        "session": {"turn_count": 1, "escalation_path_available": True},
        "event": {
            "event_id": "test-cas-001",
            "timestamp": "2026-06-12T00:00:00Z",
            "session_id": "sess-cas-001",
            "request_id": "req-cas-001",
            "event_type": "POLICY",
            "state_before": "ACTIVE",
            "state_after": "ACTIVE",
            "counterparty_type": "human_operator",
            "healthcare_governance": {
                "disclosure_timestamp": "2026-06-12T00:00:01Z",
                "identity_assertion_text": "Hi, I am an automated AI system.",
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
        },
    }


def _noncompliant_body() -> dict:
    body = _compliant_body()
    # Remove disclosure — triggers IDG-01 + PDX-01
    body["event"]["healthcare_governance"]["disclosure_timestamp"] = None
    body["event"]["healthcare_governance"]["phi_accessed"] = ["member_id"]
    body["event"]["input_payload"]["speech_text"] = "what is the member id"
    return body


# ── tests ─────────────────────────────────────────────────────────────────────

class TestCASInAPIResponse:
    def test_cas_block_present_in_compliant_response(self):
        resp = lambda_handler(_make_event(_compliant_body()), None)
        body = json.loads(resp["body"])
        assert "cas" in body, "cas block missing from conformance response"

    def test_cas_score_is_float_between_zero_and_one(self):
        resp = lambda_handler(_make_event(_compliant_body()), None)
        cas = json.loads(resp["body"])["cas"]
        assert isinstance(cas["score"], (int, float))
        assert 0.0 <= cas["score"] <= 1.0

    def test_cas_tier_is_non_empty_string(self):
        resp = lambda_handler(_make_event(_compliant_body()), None)
        tier = json.loads(resp["body"])["cas"]["tier"]
        assert isinstance(tier, str) and len(tier) > 0

    def test_cas_badge_eligible_is_none_or_valid_string(self):
        resp = lambda_handler(_make_event(_compliant_body()), None)
        badge = json.loads(resp["body"])["cas"]["badge_eligible"]
        assert badge is None or badge in ("L1", "L2")

    def test_cas_score_lower_for_critical_violations(self):
        compliant_resp = lambda_handler(_make_event(_compliant_body()), None)
        noncompliant_resp = lambda_handler(_make_event(_noncompliant_body()), None)
        compliant_score = json.loads(compliant_resp["body"])["cas"]["score"]
        noncompliant_score = json.loads(noncompliant_resp["body"])["cas"]["score"]
        assert noncompliant_score < compliant_score, (
            f"noncompliant CAS ({noncompliant_score}) should be < compliant CAS ({compliant_score})"
        )
