"""
EIT-01 Multi-Turn Escalation Tests
====================================
Verifies that EIT-01 (Escalation Honor) correctly detects:
1. Escalation requests across multiple turns
2. Escalation deflection from previous turns
3. Repeated escalation attempts
4. Escalation combined with other control violations
"""
from src.nhid_policy_engine_v1 import evaluate_all, PolicyAction, BoundaryViolation
from src.synthetic_eval_loop import build_session, build_event, extract_rule_ids


class TestEIT01AcrossTurns:
    """Test escalation detection across multiple turns."""

    def test_escalation_in_current_turn(self):
        """Escalation request in current turn triggers EIT-01 when path unavailable."""
        conversation_id = "test-eit01-curr"

        # Turn 0: disclosure
        turn0 = {
            "turn_count": 0,
            "speech_text": "I'm an automated system.",
            "disclosure_timestamp": "2026-08-01T10:00:00Z",
            "identity_assertion_text": "I'm an automated system.",
            "escalation_path_available": True,
        }
        session0 = build_session(turn0)
        event0 = build_event(conversation_id, 0, turn0)
        decision0 = evaluate_all(session0, event0)
        assert decision0.action == PolicyAction.CONTINUE_AI

        # Turn 1: escalation request, but path unavailable
        turn1 = {
            "turn_count": 1,
            "speech_text": "I need to speak to a human.",
            "escalation_path_available": False,
        }
        session1 = build_session(turn1)
        event1 = build_event(conversation_id, 1, turn1)
        decision1 = evaluate_all(session1, event1)
        assert decision1.action == PolicyAction.ESCALATE_HUMAN
        assert "EIT-01" in extract_rule_ids(decision1.violations)

    def test_escalation_deflection_from_previous_turn(self):
        """Escalation outcome=deflected in current turn triggers violation for previous request."""
        conversation_id = "test-eit01-deflect"

        # Turn 0: agent discloses
        turn0 = {
            "turn_count": 0,
            "speech_text": "This is an automated system.",
            "disclosure_timestamp": "2026-08-01T10:00:00Z",
            "identity_assertion_text": "This is an automated system.",
            "escalation_path_available": True,
        }
        session0 = build_session(turn0)
        event0 = build_event(conversation_id, 0, turn0)
        evaluate_all(session0, event0)  # Baseline disclosure

        # Turn 1: user requests escalation
        turn1 = {
            "turn_count": 1,
            "speech_text": "I want to speak with a representative.",
            "escalation_path_available": True,
        }
        session1 = build_session(turn1)
        event1 = build_event(conversation_id, 1, turn1)
        decision1 = evaluate_all(session1, event1)  # Request is recorded
        assert "EIT-01" not in extract_rule_ids(decision1.violations)  # Path is available

        # Turn 2: escalation marked as deflected (agent failed to honor request)
        turn2 = {
            "turn_count": 2,
            "speech_text": "System connecting you to help queue.",
            "escalation_outcome": "deflected",  # False honor
        }
        session2 = build_session(turn2)
        event2 = build_event(conversation_id, 2, turn2)
        decision2 = evaluate_all(session2, event2)
        assert "EIT-01" in extract_rule_ids(decision2.violations)
        assert decision2.action == PolicyAction.ESCALATE_HUMAN

    def test_repeated_escalation_requests(self):
        """Multiple escalation requests should each be evaluated."""
        conversation_id = "test-eit01-repeat"

        # Setup: disclosure + escalation path available
        turn0 = {
            "turn_count": 0,
            "speech_text": "Hello, this is automated.",
            "disclosure_timestamp": "2026-08-01T10:00:00Z",
            "escalation_path_available": True,
        }
        session0 = build_session(turn0)
        event0 = build_event(conversation_id, 0, turn0)
        evaluate_all(session0, event0)

        # Turn 1: first escalation request
        turn1 = {
            "turn_count": 1,
            "speech_text": "I need a human please.",
            "escalation_path_available": True,
        }
        session1 = build_session(turn1)
        event1 = build_event(conversation_id, 1, turn1)
        decision1 = evaluate_all(session1, event1)
        assert "EIT-01" not in extract_rule_ids(decision1.violations)

        # Turn 2: second escalation request, path now unavailable (escalation was denied)
        turn2 = {
            "turn_count": 2,
            "speech_text": "Can I please talk to someone?",
            "escalation_path_available": False,  # Path not available after failed escalation
        }
        session2 = build_session(turn2)
        event2 = build_event(conversation_id, 2, turn2)
        decision2 = evaluate_all(session2, event2)
        assert "EIT-01" in extract_rule_ids(decision2.violations)

    def test_escalation_with_undisclosed_plus_no_path(self):
        """Escalation violation combines with IDG-01 when undisclosed."""
        conversation_id = "test-eit01-combo"

        # Turn 0: no disclosure, escalation request, no path
        turn0 = {
            "turn_count": 0,
            "speech_text": "I want to speak to a human.",
            "disclosure_timestamp": None,  # Not disclosed
            "escalation_path_available": False,  # No path
        }
        session0 = build_session(turn0)
        event0 = build_event(conversation_id, 0, turn0)
        decision0 = evaluate_all(session0, event0)
        violated = extract_rule_ids(decision0.violations)

        # Both violations expected
        assert "IDG-01" in violated
        assert "EIT-01" in violated
        # ESCALATE_HUMAN should dominate (hierarchy)
        assert decision0.action == PolicyAction.ESCALATE_HUMAN

    def test_escalation_unrelated_turns_between_request_and_outcome(self):
        """Escalation outcome is evaluated regardless of unrelated speech between request and outcome."""
        conversation_id = "test-eit01-unrelated"

        # Turn 0: disclosure
        turn0 = {
            "turn_count": 0,
            "speech_text": "Automated system.",
            "disclosure_timestamp": "2026-08-01T10:00:00Z",
            "escalation_path_available": True,
        }
        session0 = build_session(turn0)
        event0 = build_event(conversation_id, 0, turn0)
        evaluate_all(session0, event0)

        # Turn 1: escalation request
        turn1 = {
            "turn_count": 1,
            "speech_text": "I need a human.",
            "escalation_path_available": True,
        }
        session1 = build_session(turn1)
        event1 = build_event(conversation_id, 1, turn1)
        evaluate_all(session1, event1)

        # Turn 2: agent responds with unrelated speech, no escalation_outcome yet
        turn2 = {
            "turn_count": 2,
            "speech_text": "I understand. Let me check something.",
            "escalation_path_available": True,
        }
        session2 = build_session(turn2)
        event2 = build_event(conversation_id, 2, turn2)
        decision2 = evaluate_all(session2, event2)
        assert "EIT-01" not in extract_rule_ids(decision2.violations)

        # Turn 3: escalation marked as deflected
        turn3 = {
            "turn_count": 3,
            "speech_text": "I'm queuing you for a callback.",
            "escalation_outcome": "deflected",  # Late-reported deflection
        }
        session3 = build_session(turn3)
        event3 = build_event(conversation_id, 3, turn3)
        decision3 = evaluate_all(session3, event3)
        # EIT-01 should trigger despite multiple turns between request and outcome
        assert "EIT-01" in extract_rule_ids(decision3.violations)


class TestEIT01EdgeCases:
    """Test edge cases and boundary conditions for EIT-01."""

    def test_escalation_honored_outcome_passes(self):
        """escalation_outcome='honored' should not trigger EIT-01."""
        conversation_id = "test-eit01-honored"

        turn0 = {
            "turn_count": 0,
            "speech_text": "Automated system.",
            "disclosure_timestamp": "2026-08-01T10:00:00Z",
            "escalation_path_available": True,
        }
        session0 = build_session(turn0)
        event0 = build_event(conversation_id, 0, turn0)
        evaluate_all(session0, event0)

        turn1 = {
            "turn_count": 1,
            "speech_text": "I need a human.",
            "escalation_outcome": "honored",  # Escalation was honored
        }
        session1 = build_session(turn1)
        event1 = build_event(conversation_id, 1, turn1)
        decision1 = evaluate_all(session1, event1)
        assert "EIT-01" not in extract_rule_ids(decision1.violations)

    def test_escalation_no_request_no_violation(self):
        """Absence of escalation request should not trigger EIT-01."""
        conversation_id = "test-eit01-noreq"

        turn0 = {
            "turn_count": 0,
            "speech_text": "Can I help you with your balance?",
            "disclosure_timestamp": "2026-08-01T10:00:00Z",
            "escalation_path_available": True,
        }
        session0 = build_session(turn0)
        event0 = build_event(conversation_id, 0, turn0)
        decision0 = evaluate_all(session0, event0)
        assert "EIT-01" not in extract_rule_ids(decision0.violations)

    def test_escalation_path_available_true_default(self):
        """When escalation_path_available not specified, should default to True."""
        conversation_id = "test-eit01-default"

        # Turn without explicit escalation_path_available
        turn = {
            "turn_count": 1,
            "speech_text": "I want to speak to someone.",
            "disclosure_timestamp": "2026-08-01T10:00:00Z",
            # escalation_path_available not set - should default to True
        }
        session = build_session(turn)
        event = build_event(conversation_id, 0, turn)
        decision = evaluate_all(session, event)
        # Should not violate EIT-01 since path defaults to available
        assert "EIT-01" not in extract_rule_ids(decision.violations)
