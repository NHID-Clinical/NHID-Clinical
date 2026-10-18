"""
IDG-01 — a disclosure counts only if it was heard
==================================================
Platforms commonly log the whole scripted line even when the counterparty
barged in and playback stopped part-way. A transcript reading "I'm an automated
assistant" therefore does not show the words were heard. These tests pin the
rule: an interrupted disclosure is credited only when the part actually played
(`heard_text` / `disclosure_heard_text`) states a non-human identity, and with
no heard text it is not credited at all. PDX-01 follows: protected data stays
gated until a disclosure has been heard.
"""
from adapters.call_progress_adapter import to_nhid_event
from adapters.twilio_adapter import twilio_transcript_to_nhid
from adapters.vapi_adapter import vapi_to_nhid_trace
from src.nhid_policy_engine_v1 import PolicyAction, evaluate_idg01, evaluate_pdx01

DISCLOSED_AT = "2026-10-18T10:00:00Z"
LINE = "Hi, this is Ava, I'm an automated assistant calling from the clinic."


def _session():
    return {"turn_count": 1, "escalation_path_available": True,
            "counterparty_type": "human_operator", "disclosure_established_prior": True}


def _event(speech="", **gov):
    governance = {
        "disclosure_timestamp": DISCLOSED_AT,
        "identity_assertion_text": LINE,
        "deceptive_artifact_flags": [],
        "escalation_timestamp": None,
        "escalation_outcome": None,
        "phi_accessed": [],
    }
    governance.update(gov)
    return {
        "event_id": "e-1", "timestamp": DISCLOSED_AT, "session_id": "s-1",
        "request_id": "r-1", "event_type": "POLICY", "actor_id": "agent-1",
        "counterparty_type": "human_operator", "state_before": "ACTIVE",
        "state_after": "ACTIVE", "healthcare_governance": governance,
        "input_payload": {"speech_text": speech, "raw_form_fields": None},
    }


# ── Engine ────────────────────────────────────────────────────────────────

def test_an_interrupted_disclosure_is_not_a_disclosure():
    decision = evaluate_idg01(_session(), _event(
        disclosure_interrupted=True, disclosure_heard_text="Hi, this is Ava, I'm an"))
    assert decision.reason_code == "IDG01_DISCLOSURE_INTERRUPTED"
    assert decision.action == PolicyAction.DISCLOSE_IDENTITY
    assert decision.violations[0].severity.value == "critical"


def test_interrupted_with_no_heard_text_is_not_a_disclosure():
    """Fail closed: nothing shows the words were played."""
    decision = evaluate_idg01(_session(), _event(disclosure_interrupted=True))
    assert decision.reason_code == "IDG01_DISCLOSURE_INTERRUPTED"


def test_interrupted_after_the_identity_was_heard_still_counts():
    decision = evaluate_idg01(_session(), _event(
        disclosure_interrupted=True,
        disclosure_heard_text="Hi, this is Ava, I'm an automated assistant"))
    assert decision.reason_code == "IDG01_DISCLOSURE_CONFIRMED"


def test_without_the_flag_behaviour_is_unchanged():
    assert evaluate_idg01(_session(), _event()).reason_code == "IDG01_DISCLOSURE_CONFIRMED"


def test_protected_data_stays_gated_behind_an_unheard_disclosure():
    decision = evaluate_pdx01(_session(), _event(
        speech="Can I get the member ID?", phi_accessed=["member_id"],
        disclosure_interrupted=True, disclosure_heard_text="Hi, this is"))
    assert decision.action == PolicyAction.DENY_DATA
    assert decision.reason_code == "PDX01_PHI_GATE_TRIGGERED"


# ── Adapters ──────────────────────────────────────────────────────────────

def test_twilio_does_not_credit_an_interrupted_disclosure():
    trace = twilio_transcript_to_nhid({"call_sid": "CA1", "transcript": [
        {"text": LINE, "timestamp": 0.5, "speaker": "agent",
         "interrupted": True, "heard_text": "Hi, this is Ava"},
        {"text": "Sorry, who?", "timestamp": 2.0, "speaker": "human"},
        {"text": "Can I get the member ID?", "timestamp": 4.0, "speaker": "agent"},
    ]})
    c = trace["compliance"]
    assert c["disclosure_made"] is False
    assert c["interrupted_disclosure_offsets_s"] == [0.5]
    assert c["IDG-01"].startswith("FAIL – disclosure interrupted")
    assert trace["events"][0]["event_type"] == "DISCLOSURE_INTERRUPTED"


def test_twilio_credits_a_repeated_disclosure_and_reports_it_late():
    trace = twilio_transcript_to_nhid({"call_sid": "CA2", "transcript": [
        {"text": LINE, "timestamp": 0.5, "speaker": "agent", "interrupted": True},
        {"text": "Hello?", "timestamp": 2.0, "speaker": "human"},
        {"text": "I'm an automated assistant from the clinic.", "timestamp": 3.0,
         "speaker": "agent"},
        {"text": "What is the member ID?", "timestamp": 6.0, "speaker": "agent"},
    ]})
    c = trace["compliance"]
    assert c["disclosure_timestamp_offset_s"] == 3.0
    assert c["IDG-01"] == "PASS"


def test_vapi_does_not_credit_an_interrupted_disclosure():
    trace = vapi_to_nhid_trace({"call": {"id": "v1"}, "messages": [
        {"role": "bot", "message": LINE, "secondsFromStart": 0.4,
         "interrupted": True, "heard_text": "Hi there"},
        {"role": "user", "message": "Hello?", "secondsFromStart": 1.5},
    ]})
    assert trace["compliance"]["disclosure_made"] is False
    assert trace["compliance"]["interrupted_disclosure_offsets_s"] == [0.4]


def test_call_progress_passes_the_interruption_to_the_engine():
    _, event = to_nhid_event({
        "session_id": "c1", "turn_index": 0, "speaker": "agent", "text": LINE,
        "interrupted": True, "heard_text": "Hi, this is Ava",
        "session_state": {"turn_count": 1, "disclosure_timestamp": None},
    })
    gov = event["healthcare_governance"]
    assert gov["disclosure_interrupted"] is True
    assert gov["disclosure_heard_text"] == "Hi, this is Ava"
    assert evaluate_idg01(_session(), event).reason_code == "IDG01_DISCLOSURE_INTERRUPTED"
