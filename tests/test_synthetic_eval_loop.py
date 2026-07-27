"""
Regression test for src/synthetic_eval_loop.py.

Proves the per-control detection loop correctly surfaces DBC-01 and EIT-01
(the two controls a naive turn-builder tends to silently drop — see the
module docstring in synthetic_eval_loop.py for why) alongside IDG-01,
PDX-01, and ATR-01. Fixtures mirror the six documented synthetic-data
scenarios.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.synthetic_eval_loop import (
    extract_rule_ids,
    compute_detection_rates,
    evaluate_conversation,
)
from src.nhid_policy_engine_v1 import BoundaryViolation, ViolationSeverity


_CONVERSATIONS = [
    {
        "conversation_id": "CONV-CONFORM-001",
        "expected_violations": [],
        "turns": [
            {
                "speech_text": "Hello, I am an automated system calling about a prior authorization. I am not a human representative.",
                "disclosure_timestamp": "2026-06-10T15:02:11Z",
                "identity_assertion_text": "Hello, I am an automated system calling about a prior authorization. I am not a human representative.",
                "turn_count": 0,
            },
        ],
    },
    {
        "conversation_id": "CONV-IDG01-PDX01-001",
        "expected_violations": ["IDG-01", "PDX-01"],
        "turns": [
            {
                "speech_text": "I need the member ID and date of birth on file to continue.",
                "disclosure_timestamp": None,
                "turn_count": 3,
                "phi_accessed": ["member_id", "date_of_birth"],
            },
        ],
    },
    {
        "conversation_id": "CONV-DBC01-001",
        "expected_violations": ["DBC-01"],
        "turns": [
            {
                "speech_text": "*inhales* one moment, pulling that up.",
                "disclosure_timestamp": "2026-06-12T11:39:50Z",
                "deceptive_artifact_flags": ["fake_breathing"],
                "turn_count": 2,
            },
        ],
    },
    {
        "conversation_id": "CONV-EIT01-001",
        "expected_violations": ["EIT-01"],
        "turns": [
            {
                "speech_text": "I want to speak to a human about this denial.",
                "disclosure_timestamp": "2026-06-13T16:54:10Z",
                "escalation_path_available": False,
                "turn_count": 3,
            },
        ],
    },
    {
        "conversation_id": "CONV-ATR01-001",
        "expected_violations": ["ATR-01"],
        "turns": [
            {
                "speech_text": "Checking eligibility for outpatient physical therapy.",
                "disclosure_timestamp": "2026-06-14T08:20:40Z",
                "turn_count": 1,
            },
        ],
    },
]

# Force an ATR-01 violation on the dedicated fixture by knocking out a
# required audit field, mirroring the documented Scenario 5.
_CONVERSATIONS[4]["turns"][0]["_force_missing_session_id"] = True


def _build_event_with_missing_session_id(conversation_id, turn_index, turn):
    from src.synthetic_eval_loop import build_event
    event = build_event(conversation_id, turn_index, turn)
    if turn.get("_force_missing_session_id"):
        event["session_id"] = None
    return event


class TestExtractRuleIds:
    def test_extracts_from_dataclass_instances(self):
        violations = [
            BoundaryViolation(rule_id="DBC-01", description="x", severity=ViolationSeverity.CRITICAL),
            BoundaryViolation(rule_id="EIT-01", description="y", severity=ViolationSeverity.CRITICAL),
        ]
        assert extract_rule_ids(violations) == ["DBC-01", "EIT-01"]

    def test_extracts_from_dict_fixtures(self):
        violations = [{"rule_id": "ATR-01", "severity": "critical", "description": "z"}]
        assert extract_rule_ids(violations) == ["ATR-01"]

    def test_empty_list_yields_empty(self):
        assert extract_rule_ids([]) == []


class TestDetectionRates:
    def test_idg01_pdx01_detected(self):
        stats = compute_detection_rates([_CONVERSATIONS[1]])
        assert stats["IDG-01"]["detection_rate"] == 1.0
        assert stats["PDX-01"]["detection_rate"] == 1.0

    def test_dbc01_detected_not_zero(self):
        # This is the exact regression case: a naive loop that fails to
        # copy deceptive_artifact_flags into healthcare_governance reports
        # 0 here. It must not.
        stats = compute_detection_rates([_CONVERSATIONS[2]])
        assert stats["DBC-01"]["detected"] == 1
        assert stats["DBC-01"]["detection_rate"] == 1.0

    def test_eit01_detected_not_zero(self):
        # Same regression shape: a session built without threading
        # escalation_path_available=False through reports 0 here.
        stats = compute_detection_rates([_CONVERSATIONS[3]])
        assert stats["EIT-01"]["detected"] == 1
        assert stats["EIT-01"]["detection_rate"] == 1.0

    def test_conformant_conversation_contributes_nothing(self):
        stats = compute_detection_rates([_CONVERSATIONS[0]])
        assert stats == {}

    def test_full_batch_all_controls_at_100_percent(self):
        conversations = _CONVERSATIONS[:4]  # skip the ATR-01 override fixture
        stats = compute_detection_rates(conversations)
        for rule_id in ("IDG-01", "PDX-01", "DBC-01", "EIT-01"):
            assert stats[rule_id]["detection_rate"] == 1.0, (
                f"{rule_id} detection rate should be 1.0, got {stats[rule_id]}"
            )

    def test_atr01_detected_via_missing_session_id(self):
        conversation = _CONVERSATIONS[4]
        turn = conversation["turns"][0]
        results = []
        session_builder_input = turn
        from src.synthetic_eval_loop import build_session
        session = build_session(session_builder_input)
        event = _build_event_with_missing_session_id(conversation["conversation_id"], 0, turn)
        from src.nhid_policy_engine_v1 import evaluate_all
        decision = evaluate_all(session, event)
        assert "ATR-01" in extract_rule_ids(decision.violations)


class TestEvaluateConversation:
    def test_returns_one_result_per_turn(self):
        results = evaluate_conversation(_CONVERSATIONS[1])
        assert len(results) == 1
        assert "DENY_DATA" == results[0]["action"]
        assert set(results[0]["detected_rule_ids"]) == {"IDG-01", "PDX-01"}
