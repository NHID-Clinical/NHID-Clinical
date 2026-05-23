"""Pure NHID state machine logic.

This module contains deterministic state transition validation and
state application helpers only. It does not store session state,
perform audit logging, or write to any persistence layer.
"""

VALID_STATES = {"INIT", "DISCLOSURE", "ROUTE", "EXECUTE", "ESCALATE", "BLOCKED"}
VALID_TRANSITIONS = {
    "INIT": {"DISCLOSURE", "BLOCKED"},
    "DISCLOSURE": {"ROUTE", "ESCALATE", "BLOCKED", "DISCLOSURE"},
    "ROUTE": {"EXECUTE", "ESCALATE", "BLOCKED", "ROUTE"},
    "EXECUTE": {"ROUTE", "ESCALATE", "BLOCKED", "EXECUTE"},
    "ESCALATE": {"BLOCKED", "ESCALATE"},
    "BLOCKED": {"BLOCKED"},
}


def validate_transition(current_state: str, next_state: str) -> bool:
    """Return whether a transition from current_state to next_state is valid."""
    current_state = (current_state or "INIT").strip()
    next_state = (next_state or current_state).strip()

    if next_state not in VALID_STATES:
        return False

    return current_state == next_state or next_state in VALID_TRANSITIONS.get(current_state, set())


def apply_state(current_state: str, next_state: str) -> str:
    """Apply a state transition and return the resulting state."""
    if validate_transition(current_state, next_state):
        return next_state
    return current_state
