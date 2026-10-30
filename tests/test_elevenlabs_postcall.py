"""
The Beacon demonstration's ElevenLabs integration, end to end, in the suite
CI runs (tests/demo/ is excluded from it; see pytest.ini).

One block per audit finding (2026-10-29), each written against the real
ElevenLabs shapes:

  1. the post-call envelope {type, event_timestamp, data} is read;
  2. call timing (time_in_call_secs) reaches the evaluation;
  3. the webhook is HMAC-authenticated and fails closed;
  4. the agent ID comes from the environment, never the source;
  5. ElevenLabs' own grades are stored beside the engine's, never read by it;
  6. the published copy describes both demonstration lines accurately.

Plus two found while verifying: Beacon is the caller, so its own words are
checked for patient identifiers; and the status store survives DynamoDB's
number types.

The signature scheme is the official elevenlabs Python SDK's
(webhooks_custom.WebhooksClient.construct_event, v2.75.0), re-implemented
here independently so the test does not just call the code it checks.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.elevenlabs_postcall_adapter import iter_turns, parse_postcall
from functions import demo_status_store
from functions import elevenlabs_postcall_handler as eph
from functions.elevenlabs_postcall_handler import _handle_elevenlabs_postcall_webhook

ROOT = Path(__file__).resolve().parent.parent
SECRET = "whsec_test_only_not_a_real_secret"
START = 1_761_700_000  # call start, unix seconds


class FakeTable:
    """Behaves like a boto3 Table where it matters: put_item rejects floats
    and get_item returns every number as Decimal."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {}
        self.writes = 0

    @staticmethod
    def _check(value):
        if isinstance(value, float):
            raise TypeError("Float types are not supported. Use Decimal types instead.")
        if isinstance(value, dict):
            for v in value.values():
                FakeTable._check(v)
        if isinstance(value, list):
            for v in value:
                FakeTable._check(v)

    @staticmethod
    def _as_dynamo(value):
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, dict):
            return {k: FakeTable._as_dynamo(v) for k, v in value.items()}
        if isinstance(value, list):
            return [FakeTable._as_dynamo(v) for v in value]
        return value

    def put_item(self, Item: dict) -> None:
        self._check(Item)
        self.writes += 1
        self.items[Item["session_id"]] = self._as_dynamo(Item)

    def get_item(self, Key: dict) -> dict:
        item = self.items.get(Key["session_id"])
        return {"Item": item} if item is not None else {}


def sign(raw: str, secret: str = SECRET, ts: int | None = None) -> str:
    ts = int(time.time()) if ts is None else ts
    digest = hmac.new(secret.encode(), f"{ts}.{raw}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v0={digest}"


def envelope(transcript, *, conversation_id="conv_test", analysis=None, metadata=None,
             event_type="post_call_transcription", event_timestamp=None):
    data = {"agent_id": "agent_test", "conversation_id": conversation_id, "transcript": transcript}
    data["metadata"] = metadata if metadata is not None else {"start_time_unix_secs": START,
                                                               "call_duration_secs": 60}
    if analysis is not None:
        data["analysis"] = analysis
    return {"type": event_type,
            "event_timestamp": START + 90 if event_timestamp is None else event_timestamp,
            "data": data}


def post(payload, table, *, header_name="ElevenLabs-Signature", signature=None, raw=None):
    raw = json.dumps(payload) if raw is None else raw
    headers = {} if signature is False else {header_name: signature or sign(raw)}
    return _handle_elevenlabs_postcall_webhook({"body": raw, "headers": headers}, status_table=table)


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", SECRET)


DISCLOSE = "Hi, this is Beacon, an automated AI assistant calling for a demonstration dental practice about a claim status."


# ── 1. The real envelope ─────────────────────────────────────────────────────

def test_the_real_envelope_is_evaluated_not_rejected():
    """Before the fix every real call answered 400 "conversation_id is
    required", because the adapter read it from the top level."""
    table = FakeTable()
    resp = post(envelope([{"role": "agent", "message": DISCLOSE, "time_in_call_secs": 1}]), table)
    assert resp["statusCode"] == 200, resp["body"]
    assert json.loads(resp["body"]) == {"conversation_id": "conv_test", "turns_evaluated": 1}
    assert "conv_test" in table.items


@pytest.mark.parametrize("event_type", ["post_call_audio", "call_initiation_failure", "something_new"])
def test_other_event_types_are_acknowledged_and_ignored(event_type):
    table = FakeTable()
    payload = {"type": event_type, "event_timestamp": START, "data": {"conversation_id": "c", "full_audio": "AAAA"}}
    resp = post(payload, table)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"ignored": event_type}
    assert table.writes == 0


def test_an_oversized_audio_event_is_acknowledged_not_refused():
    """post_call_audio carries the call as base64 MP3. Over the 2 MB parse cap
    it must still get 200, or ElevenLabs counts a failed delivery."""
    from functions.handler import MAX_BODY_BYTES
    table = FakeTable()
    raw = json.dumps({"type": "post_call_audio", "event_timestamp": START,
                      "data": {"conversation_id": "c", "full_audio": "A" * (MAX_BODY_BYTES + 10)}})
    resp = post(None, table, raw=raw)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"ignored": "post_call_audio"}
    assert table.writes == 0


def test_an_oversized_transcript_is_still_refused():
    from functions.handler import MAX_BODY_BYTES
    raw = json.dumps(envelope([{"role": "agent", "message": "a" * (MAX_BODY_BYTES + 10)}]))
    assert post(None, FakeTable(), raw=raw)["statusCode"] == 413


def test_the_flat_shape_still_parses():
    record = parse_postcall({"conversation_id": "c1", "transcript": []})
    assert record["type"] == "post_call_transcription"
    assert record["conversation_id"] == "c1"


# ── 2. Call timing ───────────────────────────────────────────────────────────

def _timing(transcript, **kw):
    table = FakeTable()
    assert post(envelope(transcript, **kw), table)["statusCode"] == 200
    return table, demo_status_store.get_status("conv_test", table=table)


def test_turn_timestamps_are_call_start_plus_time_in_call():
    _table, status = _timing([
        {"role": "user", "message": "Provider services, this is Dana.", "time_in_call_secs": 1},
        {"role": "agent", "message": DISCLOSE, "time_in_call_secs": 4},
    ])
    disclosed_at = status["session_state"]["disclosure_timestamp"]
    assert disclosed_at.startswith("2025-10-29T01:06:44"), disclosed_at  # START + 4 s
    assert status["turns"][1]["decision"]["time_in_call_secs"] == 4


def test_call_start_falls_back_to_event_timestamp_minus_duration():
    record = parse_postcall(envelope([], metadata={"call_duration_secs": 60}, event_timestamp=START + 60))
    assert eph.call_start_unix_secs(record) == START
    assert eph.call_start_unix_secs(parse_postcall(envelope([], metadata={}))) is None


def test_disclosure_on_the_first_turn_at_4_seconds_passes():
    _t, status = _timing([{"role": "agent", "message": DISCLOSE, "time_in_call_secs": 4}])
    timing = status["disclosure_timing"]
    assert timing["impersonation_latency_seconds"] == 4
    assert timing["impersonation_latency_turns"] == 0
    assert timing["disclosure_band"] == "pass"


def test_disclosure_after_a_turn_at_4_seconds_is_delayed():
    _t, status = _timing([
        {"role": "user", "message": "Hello?", "time_in_call_secs": 1},
        {"role": "agent", "message": DISCLOSE, "time_in_call_secs": 4},
    ])
    assert status["disclosure_timing"]["disclosure_band"] == "delayed"


@pytest.mark.parametrize("seconds", [12, 20])
def test_disclosure_after_10_seconds_is_flagged_late(seconds):
    """The repo's one seconds threshold is pilot_measure.DISCLOSURE_DELAY_SECONDS
    (10 s, reporting only). There is no 15-second band anywhere in the
    specification, so 12 s and 20 s land in the same band."""
    _t, status = _timing([
        {"role": "user", "message": "Hello?", "time_in_call_secs": 1},
        {"role": "agent", "message": DISCLOSE, "time_in_call_secs": seconds},
    ])
    timing = status["disclosure_timing"]
    assert timing["impersonation_latency_seconds"] == seconds
    assert timing["disclosure_band"] == "late"


def test_no_disclosure_fails():
    _t, status = _timing([
        {"role": "agent", "message": "Hi, calling from a dental practice about a claim.", "time_in_call_secs": 1},
        {"role": "user", "message": "Sure, what's the member ID?", "time_in_call_secs": 5},
    ])
    timing = status["disclosure_timing"]
    assert timing["disclosed"] is False
    assert timing["disclosure_band"] == "critical"


def test_missing_timing_is_not_recorded_never_zero():
    _t, status = _timing([{"role": "agent", "message": DISCLOSE}])
    timing = status["disclosure_timing"]
    assert timing["impersonation_latency_seconds"] is None
    assert timing["timing_recorded"] is False
    assert status["turns"][0]["decision"]["time_in_call_secs"] is None


def test_an_interrupted_disclosure_does_not_count():
    _t, status = _timing([
        {"role": "agent", "message": DISCLOSE, "time_in_call_secs": 1, "interrupted": True},
        {"role": "agent", "message": "I'm Beacon, an automated AI assistant.", "time_in_call_secs": 9},
    ])
    timing = status["disclosure_timing"]
    assert timing["impersonation_latency_turns"] == 1
    assert timing["impersonation_latency_seconds"] == 9


# ── 3. Authentication ────────────────────────────────────────────────────────

GOOD = envelope([{"role": "agent", "message": DISCLOSE, "time_in_call_secs": 1}])


def test_a_valid_signature_is_accepted():
    assert post(GOOD, FakeTable())["statusCode"] == 200


@pytest.mark.parametrize("header_name", ["elevenlabs-signature", "ELEVENLABS-SIGNATURE", "ElevenLabs-Signature"])
def test_the_header_name_is_case_insensitive(header_name):
    assert post(GOOD, FakeTable(), header_name=header_name)["statusCode"] == 200


def test_a_base64_encoded_body_is_verified_over_the_decoded_bytes():
    raw = json.dumps(GOOD)
    event = {"body": base64.b64encode(raw.encode()).decode(), "isBase64Encoded": True,
             "headers": {"elevenlabs-signature": sign(raw)}}
    assert _handle_elevenlabs_postcall_webhook(event, status_table=FakeTable())["statusCode"] == 200


def _rejected(resp, table):
    assert resp["statusCode"] == 401, resp["body"]
    assert table.writes == 0, "a rejected request must write nothing"


def test_a_bad_signature_is_rejected_and_writes_nothing():
    table = FakeTable()
    _rejected(post(GOOD, table, signature=sign(json.dumps(GOOD), secret="the-wrong-secret")), table)


def test_a_tampered_body_is_rejected():
    table = FakeTable()
    raw = json.dumps(GOOD)
    signature = sign(raw)
    tampered = raw.replace("demonstration", "elsewhere")
    _rejected(post(None, table, raw=tampered, signature=signature), table)


def test_a_stale_timestamp_is_rejected():
    table = FakeTable()
    raw = json.dumps(GOOD)
    _rejected(post(None, table, raw=raw, signature=sign(raw, ts=int(time.time()) - 31 * 60)), table)


def test_a_missing_header_is_rejected():
    table = FakeTable()
    _rejected(post(GOOD, table, signature=False), table)


def test_an_unset_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_WEBHOOK_SECRET", raising=False)
    table = FakeTable()
    _rejected(post(GOOD, table), table)


def test_the_tolerance_matches_the_sdk():
    raw = "{}"
    now = 2_000_000_000
    assert eph.verify_signature(raw, sign(raw, ts=now - 29 * 60), SECRET, now=now) is None
    assert eph.verify_signature(raw, sign(raw, ts=now - 31 * 60), SECRET, now=now) is not None
    assert eph.SIGNATURE_TOLERANCE_SECS == 30 * 60


def test_the_comparison_is_constant_time():
    source = (ROOT / "functions" / "elevenlabs_postcall_handler.py").read_text(encoding="utf-8")
    assert "hmac.compare_digest" in source


# ── 4. The agent ID comes from the environment ───────────────────────────────

def test_no_agent_id_is_hard_coded_in_the_handler():
    source = (ROOT / "functions" / "handler.py").read_text(encoding="utf-8")
    assert not re.search(r"agent_[0-9a-z]{20,}", source)


def test_outbound_calls_need_the_agent_id(monkeypatch):
    from functions import handler
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_PHONE_NUMBER_ID", "p")
    monkeypatch.delenv("ELEVENLABS_AGENT_ID", raising=False)
    assert handler._outbound_call_config() is None
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_x")
    if handler._HTTPX_OK:
        assert handler._outbound_call_config() == ("k", "p", "agent_x")


@pytest.mark.parametrize("parameter,variable", [
    ("ElevenLabsAgentId", "ELEVENLABS_AGENT_ID"),
    ("ElevenLabsWebhookSecret", "ELEVENLABS_WEBHOOK_SECRET"),
])
def test_the_new_parameters_are_wired_like_the_other_secrets(parameter, variable):
    template = (ROOT / "template.yaml").read_text(encoding="utf-8")
    block = re.search(rf"^  {parameter}:\n((?:    .*\n)+)", template, re.M)
    assert block, parameter
    assert "NoEcho: true" in block.group(1)
    assert 'Default: ""' in block.group(1)
    assert f"{variable}: !Ref {parameter}" in template
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert f"PARAM_OVERRIDES += {parameter}=$({variable})" in makefile
    deploy = (ROOT / "scripts" / "deploy.ps1").read_text(encoding="utf-8")
    assert f'"{parameter}=${parameter}"' in deploy
    assert f"$env:{variable}" in deploy


def test_make_deploy_does_not_echo_the_overrides():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "\t@sam deploy" in makefile


def test_the_committed_agent_config_holds_a_placeholder():
    config = json.loads((ROOT / "agents" / "beacon.config.json").read_text(encoding="utf-8"))
    assert config["agent_id"] == "agent_REPLACE_ME"


def test_the_environment_agent_id_wins_over_the_config(monkeypatch):
    import scripts.sync_agent_config as sac
    monkeypatch.delenv("ELEVENLABS_AGENT_ID", raising=False)
    assert sac.resolve_agent_id({"agent_id": "agent_REPLACE_ME"}) == ""
    assert sac.resolve_agent_id({"agent_id": "agent_from_file"}) == "agent_from_file"
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_from_env")
    assert sac.resolve_agent_id({"agent_id": "agent_from_file"}) == "agent_from_env"


def test_the_prompt_file_parses_for_the_sync_tool():
    from src.elevenlabs_client import (_extract_canonical_first_message, _extract_canonical_name,
                                       _extract_canonical_prompt)
    path = ROOT / "agents" / "beacon_system_prompt.md"
    assert _extract_canonical_name(path) == "Beacon"
    assert "automated AI assistant" in _extract_canonical_first_message(path)
    prompt = _extract_canonical_prompt(path)
    assert "nhid_gate" in prompt and "RULE 4" in prompt
    assert not re.search(r"agent_[0-9a-z]{20,}", path.read_text(encoding="utf-8"))


# ── 5. Vendor grades beside, never into, the evaluation ──────────────────────

ANALYSIS = {
    "evaluation_criteria_results": {
        "IDG-01": {"criteria_id": "IDG-01", "result": "success", "rationale": "Stated it is an AI first."},
        "PDX-01": {"criteria_id": "PDX-01", "result": "success", "rationale": "No identifiers early."},
    },
    "data_collection_results": {
        "disclosure_heard": {"data_collection_id": "disclosure_heard", "value": True, "rationale": "Rep said ok."},
    },
    "call_successful": "success",
    "transcript_summary": "Claim status checked.",
}

LEAKY = [
    {"role": "agent", "message": "Hi, calling about Jordan Avery, member ID RVD-204-7731.", "time_in_call_secs": 1},
    {"role": "user", "message": "Okay.", "time_in_call_secs": 4},
]


def test_vendor_grades_are_stored_with_their_label():
    table = FakeTable()
    post(envelope(LEAKY, analysis=ANALYSIS), table)
    vendor = demo_status_store.get_status("conv_test", table=table)["vendor_self_evaluation"]
    assert vendor["label"] == "vendor self-evaluation (ElevenLabs), not NHID evidence"
    assert vendor["evaluation_criteria"]["IDG-01"]["result"] == "success"
    assert vendor["data_collection"]["disclosure_heard"]["value"] is True


def test_the_engine_decides_the_same_with_or_without_vendor_grades():
    with_grades, without = FakeTable(), FakeTable()
    post(envelope(LEAKY, analysis=ANALYSIS), with_grades)
    post(envelope(LEAKY), without)
    a = demo_status_store.get_status("conv_test", table=with_grades)
    b = demo_status_store.get_status("conv_test", table=without)
    assert a["turns"] == b["turns"]
    # The vendor said PDX-01 passed; the engine, reading the words, says it did not.
    rules = {v["rule_id"] for t in a["turns"] for v in t["decision"].get("violations", [])}
    assert "PDX-01" in rules
    assert "vendor_self_evaluation" not in b


def test_vendor_text_is_clipped():
    long = {"evaluation_criteria_results": {"x": {"result": "success", "rationale": "y" * 5000}}}
    vendor = eph.vendor_self_evaluation(long)
    assert len(vendor["evaluation_criteria"]["x"]["rationale"]) == 500


# ── The calling agent's own words, and the store's number types ──────────────

def _rules(transcript):
    table = FakeTable()
    post(envelope(transcript), table)
    turns = demo_status_store.get_status("conv_test", table=table)["turns"]
    return [{v["rule_id"] for v in t["decision"].get("violations", []) if v["severity"] == "critical"}
            for t in turns if t["decision"].get("type") != "summary"]


def test_beacon_speaking_a_member_id_before_disclosure_is_a_pdx01_finding():
    """Beacon is the caller. The receiver-side adapter looked for identifiers
    only in the human's words, so this used to pass clean."""
    assert "PDX-01" in _rules(LEAKY)[0]


def test_the_same_member_id_after_disclosure_is_not():
    rules = _rules([
        {"role": "agent", "message": DISCLOSE, "time_in_call_secs": 1},
        {"role": "user", "message": "Okay, go ahead.", "time_in_call_secs": 5},
        {"role": "agent", "message": "The member ID is RVD-204-7731.", "time_in_call_secs": 9},
    ])
    assert "PDX-01" not in rules[2]


def test_the_status_store_round_trips_dynamodb_numbers():
    table = FakeTable()
    demo_status_store.put_turn("s1", 0, {"time_in_call_secs": 4.5}, extra={"x": 1.25}, table=table)
    status = demo_status_store.get_status("s1", table=table)
    assert status["turns"][0]["decision"]["time_in_call_secs"] == 4.5
    assert status["turns"][0]["turn_index"] == 0 and isinstance(status["turns"][0]["turn_index"], int)
    json.dumps(status)  # the status route serialises exactly this


# ── 6. The published copy ────────────────────────────────────────────────────

GUIDE = (ROOT / "shadow-evaluation-guide.html").read_text(encoding="utf-8")
DEMO = GUIDE[GUIDE.index('id="demo"'):GUIDE.index('class="page-close')]


def test_the_scripted_line_is_not_called_an_ai_agent():
    assert "Grok Voice" not in GUIDE
    card1 = DEMO[DEMO.index("1. Call the scripted demo line"):DEMO.index("2. Or let Beacon call you")]
    assert "Twilio" in card1 and "not an AI" in card1
    assert "Beacon" not in card1


def test_beacon_is_described_as_gated_mid_call_and_graded_after():
    card2 = DEMO[DEMO.index("2. Or let Beacon call you"):DEMO.index("3. See how the call was evaluated")]
    assert "ElevenLabs" in card2 and "/v1/gate/turn" in card2 and "graded" in card2


def test_no_production_traffic_is_implied():
    assert "production traffic" not in GUIDE
    for word in ("compliant", "certified", "conformant"):
        assert not re.search(rf"\b{word}\b", DEMO, re.I), word


def test_the_demo_section_is_wired():
    assert "challenges.cloudflare.com/turnstile/v0/api.js" in GUIDE
    assert '"/v1/demo/call"' in GUIDE
    assert "NHIDDemoStatus.poll" in GUIDE and "session_id=latest" in GUIDE


def test_the_vendor_column_survives_the_widget_purge():
    """site.js deletes any element whose class or id contains "elevenlabs" or
    "convai". A vendor column named after the vendor would vanish."""
    site = (ROOT / "site.js").read_text(encoding="utf-8")
    block = site[site.index("window.NHIDDemoStatus"):site.index("Compass / ElevenLabs widget")]
    classes = re.findall(r'class="([^"]+)"', block)
    assert classes
    assert not [c for c in classes if re.search(r"elevenlabs|convai", c, re.I)]
    assert "authoritative" in block and "not NHID evidence" in (ROOT / "functions" /
                                                                 "elevenlabs_postcall_handler.py").read_text()
