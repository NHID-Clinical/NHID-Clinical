"""
NHID-Clinical – Twilio Adapter
================================
Converts Twilio call transcript data to an NHID-Clinical v1.3 event trace.

This is a simulation demonstrating schema mapping. It shows how a real vendor's
call log format can be normalized into the NHID-Clinical canonical event schema
for conformance testing.

In a production integration, twilio_log would come from:
  - Twilio Voice Intelligence transcripts (REST API)
  - Twilio webhook payloads (StatusCallback)
  - Exported call logs via Twilio bulk export

Usage:
  python adapters/twilio_adapter.py

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

import json
from typing import Any

# Keywords that indicate an identity disclosure event
DISCLOSURE_KEYWORDS = {"automated", "agent", "system", "virtual", "bot", "ai"}

# Keywords that indicate an operational data request
DATA_REQUEST_KEYWORDS = {"npi", "member id", "member number", "claim number",
                         "date of birth", "dob", "tax id", "ein", "group number"}


def twilio_transcript_to_nhid(twilio_log: dict[str, Any]) -> dict[str, Any]:
    """
    Map a Twilio call transcript to an NHID-Clinical v1.3 event trace.

    Args:
        twilio_log: Dict with keys:
            - call_sid (str): Twilio call identifier
            - start_time (str): ISO 8601 call start timestamp
            - transcript (list): [{text, timestamp, speaker}, ...]

    Returns:
        NHID-Clinical trace dict with events and compliance summary.
    """
    transcript = twilio_log.get("transcript", [])
    call_sid = twilio_log.get("call_sid", "unknown")
    start_time = twilio_log.get("start_time", "")

    events: list[dict[str, Any]] = []
    disclosure_timestamp: float | None = None
    first_data_request_timestamp: float | None = None

    for entry in transcript:
        text = entry.get("text", "").lower()
        ts = float(entry.get("timestamp", 0.0))
        speaker = entry.get("speaker", "unknown")

        words = set(text.replace(",", " ").replace(".", " ").split())

        if DISCLOSURE_KEYWORDS & words and speaker in ("agent", "ai", "unknown"):
            if disclosure_timestamp is None:
                disclosure_timestamp = ts
            events.append({
                "event_type": "DISCLOSURE",
                "timestamp_offset_s": ts,
                "speaker": speaker,
                "text_snippet": entry.get("text", "")[:120],
                "nhid_rule": "IDG-01",
            })

        elif DATA_REQUEST_KEYWORDS & words:
            if first_data_request_timestamp is None:
                first_data_request_timestamp = ts
            events.append({
                "event_type": "DATA_REQUEST",
                "timestamp_offset_s": ts,
                "speaker": speaker,
                "text_snippet": entry.get("text", "")[:120],
                "nhid_rule": "PDX-01",
            })

        elif any(kw in text for kw in ("transfer", "human", "representative", "agent please")):
            events.append({
                "event_type": "ESCALATION_REQUEST",
                "timestamp_offset_s": ts,
                "speaker": speaker,
                "text_snippet": entry.get("text", "")[:120],
                "nhid_rule": "EIT-01",
            })

    # IDG-01 evaluation: disclosure must precede any data request
    if disclosure_timestamp is None:
        idg01 = "FAIL – no disclosure detected"
    elif first_data_request_timestamp is not None and disclosure_timestamp > first_data_request_timestamp:
        idg01 = "FAIL – disclosure occurred after data request (impersonation latency)"
    else:
        idg01 = "PASS"

    return {
        "trace_id": f"twilio_{call_sid}",
        "source_format": "twilio_transcript",
        "correlation_id": call_sid,
        "call_start_time": start_time,
        "policy_version": "1.3",
        "nhid_schema_version": "1.0",
        "events": events,
        "compliance": {
            "IDG-01": idg01,
            "disclosure_timestamp_offset_s": disclosure_timestamp,
            "first_data_request_offset_s": first_data_request_timestamp,
            "disclosure_made": disclosure_timestamp is not None,
        },
    }


# ---------------------------------------------------------------------------
# Example / smoke test
# ---------------------------------------------------------------------------

SAMPLE_TWILIO_COMPLIANT = {
    "call_sid": "CA123456789",
    "start_time": "2026-05-27T14:00:00Z",
    "transcript": [
        {"text": "Hello, this is an automated system calling on behalf of Dr. Smith's office.",
         "timestamp": 0.5, "speaker": "agent"},
        {"text": "Can I get the NPI number please?",
         "timestamp": 3.2, "speaker": "agent"},
        {"text": "Sure, it's 1234567890.",
         "timestamp": 5.8, "speaker": "human"},
    ],
}

SAMPLE_TWILIO_NONCOMPLIANT = {
    "call_sid": "CA999888777",
    "start_time": "2026-05-27T14:05:00Z",
    "transcript": [
        {"text": "Hi, can I get the member ID and NPI?",
         "timestamp": 0.3, "speaker": "agent"},
        {"text": "Sure — NPI is 1234567890.",
         "timestamp": 2.1, "speaker": "human"},
        {"text": "Thank you. By the way, I'm an automated system.",
         "timestamp": 4.0, "speaker": "agent"},
    ],
}


if __name__ == "__main__":
    print("=== Compliant call ===")
    result = twilio_transcript_to_nhid(SAMPLE_TWILIO_COMPLIANT)
    print(json.dumps(result, indent=2))

    print("\n=== Non-compliant call (late disclosure) ===")
    result2 = twilio_transcript_to_nhid(SAMPLE_TWILIO_NONCOMPLIANT)
    print(json.dumps(result2, indent=2))
