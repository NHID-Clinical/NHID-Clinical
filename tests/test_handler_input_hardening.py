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
import hashlib
import hmac
import json
import time

import pytest

from functions.handler import MAX_BODY_BYTES, lambda_handler

#: The ElevenLabs post-call route authenticates before it parses (it answers
#: 401 to an unsigned body, malformed or not), so these tests sign their
#: requests to it: the parser behind the signature is what they exercise.
SIGNED_ROUTE = "/v1/webhooks/elevenlabs/postcall"
_TEST_SECRET = "hardening-test-secret"


@pytest.fixture(autouse=True)
def _webhook_secret(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", _TEST_SECRET)


def _headers(path, body):
    if path != SIGNED_ROUTE:
        return {}
    ts = str(int(time.time()))
    digest = hmac.new(_TEST_SECRET.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return {"ElevenLabs-Signature": f"t={ts},v0={digest}"}

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
    body = body if isinstance(body, str) else json.dumps(body)
    return lambda_handler(
        {"httpMethod": "POST", "path": path, "body": body, "headers": _headers(path, body)},
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
    response = _post(path, "")
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


# ── The depth limit is the handler's, not the interpreter's ──────────────────
#
# The two tests above passed on CPython 3.11 because `json.loads` raised
# `RecursionError` at those depths and the handler caught it. On Python 3.14
# the same bodies parsed, and five routes answered 200 to a request the guard
# exists to refuse. A fail-closed check that depends on an interpreter detail
# is not a check. These pin the handler's own limit.

def test_the_depth_limit_fires_before_the_parser_is_consulted(monkeypatch):
    """Even a parser that would accept the body must not be reached."""
    import functions.handler as handler

    real_loads = json.loads  # the handler and this test share the json module

    def parser_that_accepts_anything(*args, **kwargs):
        raise AssertionError("json.loads was reached for an over-deep body")

    monkeypatch.setattr(handler.json, "loads", parser_that_accepts_anything)
    response = _post("/v1/demo/check", _deeply_nested_object(depth=handler.MAX_JSON_DEPTH + 1))
    monkeypatch.undo()
    # Had the handler reached the parser, the fake would have raised and this
    # would be the 500 the internal-error path returns, not a 400.
    assert response["statusCode"] == 400
    assert "nesting depth" in real_loads(response["body"])["error"]


def test_a_body_at_the_depth_limit_is_still_parsed():
    """The limit is a ceiling on attackers, not on the events the API serves."""
    from functions.handler import MAX_JSON_DEPTH, _json_nesting_depth
    at_limit = '{"a":' * (MAX_JSON_DEPTH - 1) + '{"ok":true}' + "}" * (MAX_JSON_DEPTH - 1)
    assert _json_nesting_depth(at_limit) == MAX_JSON_DEPTH
    response = _post("/v1/demo/check", at_limit)
    # Parsed and judged on its content: a missing 'event' is a 400 from the
    # route's own validation, not the depth guard.
    assert response["statusCode"] == 400
    assert "nesting depth" not in json.loads(response["body"])["error"]


def test_brackets_inside_strings_do_not_count_toward_depth():
    from functions.handler import _json_nesting_depth
    assert _json_nesting_depth(json.dumps({"note": "[" * 500 + '\\"{' * 50})) == 1


def test_the_signed_route_refuses_an_unsigned_body_before_parsing_it():
    """Authentication first: an unsigned malformed body is a 401, not a 400,
    so nothing about the parser is reachable without the shared secret."""
    response = lambda_handler(
        {"httpMethod": "POST", "path": SIGNED_ROUTE, "body": "[" * 60_000 + "]" * 60_000}, None
    )
    assert response["statusCode"] == 401
