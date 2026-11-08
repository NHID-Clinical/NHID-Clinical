"""POST /v1/pilot/enroll must not claim something it did not do.

It used to answer `"status": "enrolled"` while storing nothing and notifying
no one, so a form wired to it would have told a payer it was enrolled when the
request had gone nowhere. The site's pilot call to action is a prefilled email
(nhid-clinical.org, "Request a shadow pilot"), and this route now says the
request was not recorded and points to that address.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from functions.handler import lambda_handler  # noqa: E402


def _enroll(body):
    resp = lambda_handler({"httpMethod": "POST", "path": "/v1/pilot/enroll",
                           "body": json.dumps(body)}, None)
    return resp["statusCode"], json.loads(resp["body"])


def test_it_never_claims_an_enrolment_it_did_not_record():
    status, body = _enroll({"org_name": "Lakeside Health Plan", "contact_email": "ops@lakeside.example"})
    assert status == 200
    assert body["status"] == "not_recorded"
    assert "enrolled" not in json.dumps(body).lower()


def test_it_points_to_the_real_way_to_ask():
    _, body = _enroll({"org_name": "Lakeside Health Plan", "contact_email": "ops@lakeside.example"})
    assert body["contact"] == "contact@nhid-clinical.org"
    assert any("contact@nhid-clinical.org" in step for step in body["next_steps"])


def test_bad_input_is_still_refused():
    assert _enroll({"contact_email": "x@y.example"})[0] == 400
    assert _enroll({"org_name": "X", "contact_email": "nope"})[0] == 400
