"""
Every vendor route resolves to a real adapter, and survives a bad payload
=========================================================================
`functions/handler.py` dispatches five vendor routes, and three of them import
from `adapters/archive/` — unmaintained code that is nonetheless reachable over
HTTP. Nothing connected the two facts, so deleting an "archived" adapter would
have broken a published route with no test objecting, and the guard that was
supposed to keep the website's adapter claims honest
(`test_published_adapter_claims_match_the_repository`) had itself stopped
covering those three the moment the files moved.

The second half of this file is adversarial. An adapter's whole job is to take
a shape this project does not control — a vendor's call payload — and normalise
it. That makes a missing key or a wrong type the *expected* input, not the
exceptional one, so each route must answer with a status code rather than an
unhandled exception.
"""
import importlib
import json
import re
from pathlib import Path

import pytest

from functions.handler import lambda_handler

ROOT = Path(__file__).resolve().parents[1]

#: vendor slug -> (route path, module that must import cleanly)
#: Taken from the dispatch in functions/handler.py, and checked against it
#: below so this table cannot drift away from the code.
VENDOR_ROUTES = {
    "vapi": ("/v1/adapters/vapi/check", "adapters.vapi_adapter"),
    "twilio": ("/v1/adapters/twilio/check", "adapters.twilio_adapter"),
    "vonage": ("/v1/adapters/vonage/check", "adapters.archive.vonage_adapter"),
    "retell": ("/v1/adapters/retell/check", "adapters.archive.retell_adapter"),
    "connect": ("/v1/adapters/connect/check",
                "adapters.archive.amazon_connect_adapter"),
}


def _post(path, body):
    return lambda_handler(
        {"httpMethod": "POST", "path": path,
         "body": body if isinstance(body, str) else json.dumps(body)},
        None,
    )


# ── The table matches the dispatch ────────────────────────────────────────────

def test_the_table_covers_every_vendor_the_handler_dispatches():
    """If a sixth vendor is routed, this file must learn about it."""
    source = (ROOT / "functions" / "handler.py").read_text(encoding="utf-8")
    dispatched = set(re.findall(r'_handle_vendor\(event,\s*"(\w+)"\)', source))
    assert dispatched == set(VENDOR_ROUTES), (
        f"handler dispatches {sorted(dispatched)}, this file knows "
        f"{sorted(VENDOR_ROUTES)}"
    )


# ── Each route's adapter exists and is importable ─────────────────────────────

@pytest.mark.parametrize("vendor", sorted(VENDOR_ROUTES))
def test_the_routes_adapter_module_imports(vendor):
    """The defect this prevents: deleting an archived adapter during a tidy-up
    while its published route stays live."""
    _path, module_name = VENDOR_ROUTES[vendor]
    module = importlib.import_module(module_name)
    assert hasattr(module, "to_nhid_event"), (
        f"{module_name} has no to_nhid_event, which is what the handler calls"
    )


@pytest.mark.parametrize("vendor", sorted(VENDOR_ROUTES))
def test_the_adapter_file_is_present_on_disk(vendor):
    _path, module_name = VENDOR_ROUTES[vendor]
    assert (ROOT / (module_name.replace(".", "/") + ".py")).is_file()


def test_the_elevenlabs_webhook_adapter_imports():
    """Reached from its own handler rather than through _handle_vendor.
    Un-archived 2026-10-29 when the Ida demo was revived, so it is
    maintained against ElevenLabs' current post-call envelope."""
    module = importlib.import_module("adapters.elevenlabs_postcall_adapter")
    assert hasattr(module, "iter_turns")
    assert hasattr(module, "parse_postcall")
    assert not (ROOT / "adapters" / "archive" / "elevenlabs_postcall_adapter.py").exists(), \
        "the archived copy must not linger beside the maintained one"


# ── Adversarial vendor payloads ───────────────────────────────────────────────

MALFORMED_PAYLOADS = [
    pytest.param({}, id="empty-object"),
    pytest.param({"message": None}, id="null-message"),
    pytest.param({"message": {}}, id="empty-message"),
    pytest.param({"message": {"type": "status-update"}}, id="unknown-type"),
    pytest.param({"message": []}, id="message-is-a-list"),
    pytest.param({"message": "a string"}, id="message-is-a-string"),
    pytest.param({"call": {"id": None}}, id="null-call-id"),
    pytest.param({"transcript": 12345}, id="numeric-transcript"),
    pytest.param({"turns": "not a list"}, id="turns-wrong-type"),
    pytest.param({"turns": [None, None]}, id="null-turns"),
    pytest.param({"turns": [{"role": "agent"}]}, id="turn-missing-text"),
    pytest.param({"CallSid": None, "SpeechResult": None}, id="null-twilio-fields"),
    pytest.param({"ContactId": "", "Transcript": []}, id="empty-connect-fields"),
    pytest.param({"unexpected_root_key": {"nested": [1, 2, 3]}}, id="unknown-shape"),
]


@pytest.mark.parametrize("vendor", sorted(VENDOR_ROUTES))
@pytest.mark.parametrize("payload", MALFORMED_PAYLOADS)
def test_a_malformed_vendor_payload_gets_a_status_code_not_a_traceback(vendor, payload):
    """A vendor payload is untrusted input from a shape this project does not
    control, so every one of these is an expected input."""
    path, _module = VENDOR_ROUTES[vendor]
    response = _post(path, payload)
    assert isinstance(response, dict) and "statusCode" in response
    assert 200 <= response["statusCode"] < 600
    # Whatever the outcome, the body must be JSON the caller can read.
    json.loads(response["body"])


@pytest.mark.parametrize("vendor", sorted(VENDOR_ROUTES))
def test_a_deeply_nested_vendor_payload_is_refused(vendor):
    path, _module = VENDOR_ROUTES[vendor]
    response = _post(path, "[" * 60_000 + "]" * 60_000)
    assert response["statusCode"] == 400


@pytest.mark.parametrize("vendor", sorted(VENDOR_ROUTES))
def test_unicode_and_control_characters_do_not_crash_an_adapter(vendor):
    """Transcripts arrive from ASR and carry whatever the vendor sends."""
    path, _module = VENDOR_ROUTES[vendor]
    nasty = "member id \x00\x07‮😀 \u0000 'OR 1=1-- <script>"
    response = _post(path, {
        "message": {"type": "transcript", "transcript": nasty, "role": "user"},
        "SpeechResult": nasty,
        "Transcript": [{"ParticipantRole": "CUSTOMER", "Content": nasty}],
        "transcript": nasty,
        "call": {"id": nasty},
        "CallSid": nasty,
    })
    assert isinstance(response, dict) and "statusCode" in response
    json.loads(response["body"])
