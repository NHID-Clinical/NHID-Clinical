"""
ElevenLabs post-call webhook handler for the Ida outbound demo.

ElevenLabs delivers the full transcript once a call ends (not turn-by-turn
like Twilio), so this handler evaluates every turn in one pass: thread
session_state/disclosure_timestamp across turns exactly like
functions.twilio_demo_handler does, run each turn through the same real
pipeline (adapters.call_progress_adapter.to_nhid_event() +
src.nhid_policy_engine_v1.evaluate_all()), and write the accumulated result
into functions.demo_status_store keyed by ElevenLabs' conversation_id --
the same store, the same shape, the Twilio scripted demo line uses, so the
website's NHIDDemoStatus.render() component works for both.

Order of work, and why:

1. **Authenticate first.** The ElevenLabs-Signature header is verified over
   the raw body before anything is parsed or stored. Unsigned, the route let
   anyone POST a fabricated call and have it shown on the public site as the
   latest result. A bad or missing signature, a stale timestamp, or an unset
   secret is a 401 and nothing is written (fail closed).
2. **Ignore what is not a transcript.** post_call_audio and
   call_initiation_failure carry no transcript; they get 200 {"ignored": type}
   so ElevenLabs does not retry them or disable the webhook.
3. **Evaluate with real call time.** Each turn is stamped call start +
   time_in_call_secs, so Impersonation Latency is measured in the call's own
   seconds. Call start is data.metadata.start_time_unix_secs; when that is
   absent, event_timestamp - call_duration_secs (an estimate: ElevenLabs sends
   the webhook after post-call analysis, so it places the start no earlier
   than the true one). Latency in seconds is time_in_call_secs of the
   disclosure turn and does not depend on that estimate. Missing timing is
   reported as not recorded, never as zero.
4. **Orient the turns for a calling agent.** Ida is the CALLER (the
   canonical scenario: an agent phones a payer). The call-progress adapter was
   written receiver-side and looks for protected data only in the human's
   words, so Ida speaking a member ID was invisible to PDX-01. Agent turns
   get the same orientation /v1/gate/turn applies (functions.handler.gate_turn).
5. **Store the vendor's own grades beside, never into, the evaluation.**
   ElevenLabs' evaluation_criteria_results and data_collection_results are
   stored after the engine has run, labelled as vendor self-evaluation. The
   engine never reads them, for the same reason PR #391 stopped DBC-01 reading
   a self-reported artifact flag: the party being evaluated does not supply
   the evidence.

This is infrastructure for the demo website feature, NOT the NHID-Clinical
governance framework itself.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from adapters.call_progress_adapter import _detect_disclosure, to_nhid_event
from adapters.elevenlabs_postcall_adapter import TRANSCRIPTION_TYPE, iter_turns, parse_postcall
from functions import demo_status_store
from functions.twilio_demo_handler import _DEMO_GATE_RULE_IDS, _decision_summary
from src.nhid_policy_engine_v1 import _phi_fields_requested, evaluate_all
from src.pilot_measure import DISCLOSURE_BANDS, classify_disclosure_band

_SCRIPT_LABEL = "Ida outbound call"

#: Environment variable holding the post-call webhook's HMAC secret.
WEBHOOK_SECRET_ENV = "ELEVENLABS_WEBHOOK_SECRET"

#: How old a signed timestamp may be. Taken from the official elevenlabs
#: Python SDK (webhooks_custom.WebhooksClient.construct_event, v2.75.0):
#: "tolerance = int(time.time() * 1000) - 30 * 60 * 1000".
SIGNATURE_TOLERANCE_SECS = 30 * 60

#: The label every stored vendor grade carries, in the store and on the site.
VENDOR_LABEL = "vendor self-evaluation (ElevenLabs), not NHID evidence"

#: The event type as the first key of the envelope, read without parsing the
#: body. A post_call_audio event carries the whole call as base64 MP3 and can
#: exceed the parser's size cap; refusing it 413 would count as a failed
#: delivery, and ElevenLabs disables a webhook that keeps failing.
_LEADING_TYPE = re.compile(r'^\s*\{\s*"type"\s*:\s*"([A-Za-z_]{1,64})"')

_MAX_VENDOR_ENTRIES = 20
_MAX_VENDOR_TEXT = 500


# ── 1. Authentication ────────────────────────────────────────────────────────

def _header(event: dict[str, Any], name: str) -> str:
    """Case-insensitive header lookup: API Gateway may lowercase names."""
    wanted = name.lower()
    for key, value in (event.get("headers") or {}).items():
        if str(key).lower() == wanted:
            return str(value or "")
    return ""


def _raw_body(event: dict[str, Any]) -> str:
    """The body exactly as signed. API Gateway base64-encodes some bodies."""
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            return base64.b64decode(body).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return ""
    return body if isinstance(body, str) else ""


def verify_signature(raw_body: str, sig_header: str, secret: str,
                     *, now: Optional[float] = None) -> Optional[str]:
    """Return None when the signature is valid, else the reason it is not.

    Mirrors the official SDK's construct_event: the header is
    ``t=<unix seconds>,v0=<hex>``; the signed message is
    ``f"{t}.{raw_body}"``; the digest is ``"v0=" + HMAC-SHA256(secret,
    message).hexdigest()``; a timestamp older than 30 minutes is rejected.
    One deliberate difference: the comparison is constant-time
    (``hmac.compare_digest``), where the SDK uses ``!=``.
    """
    if not secret:
        return "webhook secret not configured"
    if not sig_header:
        return "missing ElevenLabs-Signature header"
    timestamp = signature = None
    for part in sig_header.split(","):
        part = part.strip()
        if part.startswith("t="):
            timestamp = part[2:]
        elif part.startswith("v0="):
            signature = part
    if not timestamp or not signature:
        return "no signature with expected scheme v0"
    try:
        ts = int(timestamp)
    except ValueError:
        return "signature timestamp is not an integer"
    current = time.time() if now is None else now
    if ts < current - SIGNATURE_TOLERANCE_SECS:
        return "signature timestamp outside the tolerance window"
    expected = "v0=" + hmac.new(
        secret.encode("utf-8"), f"{timestamp}.{raw_body}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature.encode("utf-8"), expected.encode("utf-8")):
        return "signature does not match"
    return None


# ── 3. Timing ────────────────────────────────────────────────────────────────

def call_start_unix_secs(record: dict[str, Any]) -> Optional[float]:
    """Call start: metadata.start_time_unix_secs, else event_timestamp minus
    call_duration_secs, else None (unknown)."""
    if record.get("start_time_unix_secs") is not None:
        return record["start_time_unix_secs"]
    if record.get("event_timestamp") is not None and record.get("call_duration_secs") is not None:
        return record["event_timestamp"] - record["call_duration_secs"]
    return None


def _turn_iso(start: Optional[float], offset: Optional[float]) -> Optional[str]:
    if start is None or offset is None:
        return None
    return datetime.fromtimestamp(start + offset, tz=timezone.utc).isoformat()


def disclosure_timing(turns: list[dict[str, Any]]) -> dict[str, Any]:
    """Impersonation Latency for one call, in the units pilot_measure uses.

    The disclosure is the first agent turn that states a non-human identity
    and was not interrupted (an interrupted disclosure was not heard and does
    not count). Seconds are that turn's time_in_call_secs: the offset from the
    moment the call connected, which is IL by definition
    (IL = t(disclosure) - t(connect)). The band is pilot_measure's own,
    reporting-only classification; nothing here gates a decision.
    """
    position = None
    for i, t in enumerate(turns):
        if t["speaker"] == "agent" and _detect_disclosure(t["text"]) and not t.get("interrupted"):
            position = i
            break
    cutoff = len(turns) if position is None else position
    pre_disclosure_phi = sum(len(_phi_fields_requested(t["text"], [])) for t in turns[:cutoff])
    il_seconds = turns[position].get("time_in_call_secs") if position is not None else None
    band = classify_disclosure_band(position is not None, position, il_seconds, pre_disclosure_phi)
    return {
        "disclosed": position is not None,
        "impersonation_latency_turns": position,
        "impersonation_latency_seconds": il_seconds,
        "timing_recorded": il_seconds is not None,
        "pre_disclosure_phi_fields": pre_disclosure_phi,
        "disclosure_band": band,
        "disclosure_band_meaning": DISCLOSURE_BANDS[band],
    }


# ── 5. Vendor grades, stored beside the evaluation ───────────────────────────

def _clip(value: Any) -> Any:
    if isinstance(value, str):
        return value[:_MAX_VENDOR_TEXT]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)[:_MAX_VENDOR_TEXT]


def vendor_self_evaluation(analysis: dict[str, Any]) -> Optional[dict[str, Any]]:
    """ElevenLabs' own grades of the call, normalised and labelled.

    Read only after the engine has decided every turn, and never passed to it.
    Returns None when the payload carried no grades.
    """
    criteria = analysis.get("evaluation_criteria_results")
    collected = analysis.get("data_collection_results")
    out_criteria: dict[str, Any] = {}
    if isinstance(criteria, dict):
        for key, entry in list(criteria.items())[:_MAX_VENDOR_ENTRIES]:
            entry = entry if isinstance(entry, dict) else {}
            out_criteria[str(key)[:100]] = {
                "result": _clip(entry.get("result")),
                "rationale": _clip(entry.get("rationale")),
            }
    out_collected: dict[str, Any] = {}
    if isinstance(collected, dict):
        for key, entry in list(collected.items())[:_MAX_VENDOR_ENTRIES]:
            entry = entry if isinstance(entry, dict) else {}
            out_collected[str(key)[:100]] = {
                "value": _clip(entry.get("value")),
                "rationale": _clip(entry.get("rationale")),
            }
    if not out_criteria and not out_collected:
        return None
    return {
        "label": VENDOR_LABEL,
        "evaluation_criteria": out_criteria,
        "data_collection": out_collected,
    }


# ── The handler ──────────────────────────────────────────────────────────────

def _critical_violation_count(turns: list[dict[str, Any]]) -> int:
    return sum(
        1
        for t in turns
        for v in t.get("decision", {}).get("violations", [])
        if v.get("severity") == "critical" and v.get("rule_id") in _DEMO_GATE_RULE_IDS
    )


def _orient_for_calling_agent(turn: dict[str, Any], session: dict[str, Any],
                              policy_event: dict[str, Any], *, disclosed_before: bool) -> None:
    """Give each engine slot the party it describes, for an agent that CALLS.

    Mirrors functions.handler.gate_turn: the agent's own words are both its
    identity assertion (DBC-01) and, when they carry an identifier, the data
    exchange PDX-01 gates. The human's words stay in speech_text, where EIT-01
    looks for a request for a person. Computes no decision of its own.
    """
    governance = policy_event["healthcare_governance"]
    if turn["speaker"] == "agent":
        governance["identity_assertion_text"] = turn["text"]
        governance["phi_accessed"] = sorted(_phi_fields_requested(turn["text"], []))
    # The handler is the harness that knows the conversation's history, so it
    # tells PDX-01 whether disclosure was established on an earlier turn.
    session["disclosure_established_prior"] = disclosed_before


def _handle_elevenlabs_postcall_webhook(event: dict[str, Any], *, status_table=None) -> dict[str, Any]:
    # 1. Authenticate before reading anything.
    raw = _raw_body(event)
    reason = verify_signature(
        raw,
        _header(event, "ElevenLabs-Signature"),
        os.environ.get(WEBHOOK_SECRET_ENV, ""),
    )
    if reason is not None:
        return _error(401, f"Unauthorized: {reason}")

    # Shares the conformance handler's body parser so this webhook gets the
    # same size cap and the same breadth of parse-failure handling. It parses
    # the body that was verified (already base64-decoded), so what is
    # evaluated is exactly what was signed.
    from functions.handler import MAX_BODY_BYTES, _parse_json_body

    if len(raw.encode("utf-8")) > MAX_BODY_BYTES:
        leading = _LEADING_TYPE.match(raw[:200])
        if leading and leading.group(1) != TRANSCRIPTION_TYPE:
            return _ok({"ignored": leading.group(1)})

    payload, parse_error = _parse_json_body({"body": raw})
    if parse_error:
        return parse_error

    # 2. Only transcripts are evaluated.
    try:
        record = parse_postcall(payload)
    except ValueError as exc:
        return _error(400, str(exc))
    if record["type"] != TRANSCRIPTION_TYPE:
        return _ok({"ignored": record["type"] or "unknown"})

    try:
        turns = list(iter_turns(payload))
    except ValueError as exc:
        return _error(400, str(exc))

    conversation_id = record["conversation_id"]
    start = call_start_unix_secs(record)
    session_state: dict[str, Any] = {
        "turn_count": 0,
        "disclosure_timestamp": None,
        "escalation_available": True,
    }

    stored: dict[str, Any] = {}
    for turn in turns:
        disclosed_before = session_state["disclosure_timestamp"] is not None
        adapter_body = {
            "session_id": turn["session_id"],
            "turn_index": turn["turn_index"],
            "speaker": turn["speaker"],
            "text": turn["text"],
            "interrupted": turn["interrupted"],
            "session_state": session_state,
        }
        turn_iso = _turn_iso(start, turn["time_in_call_secs"])
        if turn_iso:
            adapter_body["timestamp"] = turn_iso
        session, policy_event = to_nhid_event(adapter_body)
        _orient_for_calling_agent(turn, session, policy_event, disclosed_before=disclosed_before)
        decision = evaluate_all(session, policy_event)

        session_state = dict(session_state)
        session_state["turn_count"] = turn["turn_index"] + 1
        session_state["disclosure_timestamp"] = policy_event["healthcare_governance"]["disclosure_timestamp"]

        summary = _decision_summary(decision)
        summary["time_in_call_secs"] = turn["time_in_call_secs"]
        stored = demo_status_store.put_turn(
            conversation_id,
            turn["turn_index"],
            summary,
            session_state=session_state,
            extra={"script_label": _SCRIPT_LABEL, "completed": False},
            table=status_table,
        )

    # 5. Every engine decision is made; only now are the vendor's grades read.
    accumulated_turns = stored.get("turns", []) if stored else []
    extra: dict[str, Any] = {
        "script_label": _SCRIPT_LABEL,
        "completed": True,
        "disclosure_timing": disclosure_timing(turns),
    }
    vendor = vendor_self_evaluation(record["analysis"])
    if vendor is not None:
        extra["vendor_self_evaluation"] = vendor
    stored = demo_status_store.put_turn(
        conversation_id,
        len(turns),
        {"type": "summary", "critical_violation_count": _critical_violation_count(accumulated_turns)},
        session_state=session_state,
        extra=extra,
        table=status_table,
    )
    demo_status_store.set_latest(stored, table=status_table)

    return _ok({"conversation_id": conversation_id, "turns_evaluated": len(turns)})


_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,x-api-key",
    "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
}


def _ok(body: dict) -> dict:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps({"error": message}),
    }
