"""
Adversarial input against the HTTP surface
==========================================
Every case here previously produced an **unhandled exception** — a 502 and a
crash log rather than a 4xx — on routes reachable without an API key.

Two causes, both in the body-parsing each route inlined:

1. `json.JSONDecodeError` was the only parse failure caught. CPython's decoder
   recurses once per nesting level, so a body of 60,000 open brackets raises
   `RecursionError`, which is not a `ValueError` and not covered. Depth is the
   attack; size is incidental.
2. Nothing checked that a body which parsed was a JSON *object*. Every route
   then called `.get(...)` on it, so a top-level array, string, number or
   `null` raised `AttributeError` or `TypeError` after parsing cleanly.

Both are fixed centrally in `functions.handler._parse_json_body`, so these
tests sweep the routes rather than testing the helper in isolation — the helper
being right is worth nothing if a route still parses its own body.
"""
import json

import pytest

from functions.handler import MAX_BODY_BYTES, lambda_handler

#: Routes that accept a JSON object body and are reachable in the test harness.
#: Deliberately includes the no-API-key routes, which are the exposed surface.
OBJECT_BODY_ROUTES = [
    "/v1/conformance/check",
    "/v1/demo/check",
    "/v1/identity/verify-passport",
    "/v2/identity/verify-passport",
    "/v1/identity/revoke-passport",
    "/v1/adapters/vapi/check",
    "/v1/adapters/twilio/check",
    "/v1/adapters/retell/check",
    "/v1/adapters/connect/check",
    "/v1/webhooks/call-progress",
    "/v1/pilot/enroll",
    "/v1/cts/evaluate",
    "/v1/webhooks/elevenlabs/postcall",
]


def _post(path, body):
    return lambda_handler(
        {
            "httpMethod": "POST",
            "path": path,
            "body": body if isinstance(body, str) else json.dumps(body),
        },
        None,
    )


def _deeply_nested_array(depth=60_000):
    return "[" * depth + "]" * depth


def _deeply_nested_object(depth=5_000):
    return '{"a":' * depth + "null" + "}" * depth


# ── Parse-depth ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", OBJECT_BODY_ROUTES)
def test_a_deeply_nested_array_is_refused_not_crashed(path):
    """`RecursionError` is not a `JSONDecodeError`, so it was unhandled."""
    response = _post(path, _deeply_nested_array())
    assert response["statusCode"] == 400
    assert "Invalid JSON" in json.loads(response["body"])["error"]


@pytest.mark.parametrize("path", OBJECT_BODY_ROUTES)
def test_a_deeply_nested_object_is_refused_not_crashed(path):
    response = _post(path, _deeply_nested_object())
    assert response["statusCode"] == 400


# ── Body must be an object ────────────────────────────────────────────────────

@pytest.mark.parametrize("path", OBJECT_BODY_ROUTES)
@pytest.mark.parametrize("body", ["[1,2,3]", '"a string"', "12345", "null", "true"])
def test_a_body_that_is_not_an_object_is_refused(path, body):
    """These parse cleanly, so the route reached `.get(...)` on a list, a str,
    an int or None and raised rather than answering."""
    response = _post(path, body)
    assert response["statusCode"] == 400
    assert "JSON object" in json.loads(response["body"])["error"]


# ── Size ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", OBJECT_BODY_ROUTES)
def test_an_oversized_body_is_refused_before_parsing(path):
    """413 rather than spending CPU parsing it."""
    oversized = '{"x":"' + "a" * (MAX_BODY_BYTES + 1) + '"}'
    response = _post(path, oversized)
    assert response["statusCode"] == 413


def test_a_body_at_the_limit_is_still_parsed():
    """The cap must not reject what it is sized to allow."""
    filler = "a" * (MAX_BODY_BYTES - 64)
    body = json.dumps({"x": filler})
    assert len(body) <= MAX_BODY_BYTES
    response = _post("/v1/conformance/check", body)
    # Parsed, then refused on its own terms — a missing field, not a size error.
    assert response["statusCode"] == 400
    assert "event" in json.loads(response["body"])["error"]


# ── Malformed but shallow ─────────────────────────────────────────────────────

@pytest.mark.parametrize("path", OBJECT_BODY_ROUTES)
@pytest.mark.parametrize("body", ["{", "{'single':'quotes'}", "{,}", "\x00\x01"])
def test_ordinary_malformed_json_still_returns_400(path, body):
    """The behaviour that already worked, pinned so the rewrite kept it."""
    response = _post(path, body)
    assert response["statusCode"] == 400


# ── Empty body ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [p for p in OBJECT_BODY_ROUTES if p != "/v1/cts/evaluate"])
def test_an_empty_body_is_refused(path):
    response = lambda_handler({"httpMethod": "POST", "path": path, "body": ""}, None)
    assert response["statusCode"] == 400
    assert "required" in json.loads(response["body"])["error"].lower()


def test_the_cts_route_treats_an_empty_body_as_no_options():
    """One route legitimately accepts no body: it means "run every test".
    Pinned because the shared parser defaults to refusing an empty body."""
    response = lambda_handler(
        {"httpMethod": "POST", "path": "/v1/cts/evaluate", "body": ""}, None
    )
    assert response["statusCode"] != 400


# ── The routes still work ─────────────────────────────────────────────────────

def test_a_well_formed_request_is_unaffected():
    """Hardening that broke the happy path would not be hardening."""
    response = _post("/v1/identity/verify-passport", {"delegation": {}})
    body = json.loads(response["body"])
    assert response["statusCode"] == 400
    # Reached the route's own field validation, not the parser.
    assert "Missing required fields" in body["error"]
