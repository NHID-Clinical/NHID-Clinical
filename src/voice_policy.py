"""
voice_policy.py — Deterministic voice policy enforcement engine (NHID-Clinical).

Reference implementation of the NHID voice conformance policy. The engine
evaluates an ordered list of rules against each transcript chunk and returns a
deterministic enforcement decision. It has NO external dependencies (no I/O, no
database, no network) — it is pure, importable, and fully testable in isolation.

Supported rule types
  builtin      : REQUIRE_UPFRONT_DISCLOSURE — first-turn AI identity disclosure
  phrase_match : HUMAN_ESCALATION_REQUESTED — escalate on trigger phrases

New rule types can be added to _RULE_EVALUATORS without touching the
run_voice_policy call site.

Backward-compatibility note
  The legacy `phrases` and `policy_version` keyword arguments are supported so
  that callers using the simple (non-ruleset) form continue to work unchanged.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional

POLICY_VERSION = "VOICE-POLICY-v1.0"

# ── Legacy defaults (used when no ruleset/phrases arg is supplied) ─────────────
_ESCALATION_PHRASES = [
    "speak to a human",
    "real person",
    "agent please",
    "transfer me",
    "human agent",
    "talk to someone",
]

# ── Immutable global safety phrases — enforced even when ruleset is provided ───
# These cannot be disabled by tenant configuration. "Speak to a human" must
# always be honored regardless of what any custom ruleset says.
_GLOBAL_SAFETY_PHRASES: tuple = (
    "speak to a human",
    "agent please",
    "real person",
)


# ── Disclosure state machine ──────────────────────────────────────────────────

class DisclosureState(str, Enum):
    AWAITING = "awaiting_disclosure_ack"
    CONFIRMED = "disclosure_confirmed"


def get_disclosure_state(session_state: Dict[str, Any]) -> DisclosureState:
    if session_state.get("disclosure_confirmed", False):
        return DisclosureState.CONFIRMED
    return DisclosureState.AWAITING


def phi_gate(session_state: Dict[str, Any], phi_fields: Optional[Dict[str, Any]]) -> None:
    """Raise PermissionError if PHI fields are present before disclosure is confirmed."""
    if phi_fields and get_disclosure_state(session_state) != DisclosureState.CONFIRMED:
        raise PermissionError("PHI processing blocked: disclosure not yet confirmed")


# ── Low-level rule evaluators ─────────────────────────────────────────────────

def check_disclosure(session_state: Dict[str, Any]) -> bool:
    """
    Return True (disclosure needed) when the opening disclosure has not yet
    been confirmed for this session.
    """
    return not session_state.get("disclosure_confirmed", False)


def check_escalation(
    transcript_text: str,
    phrases: Optional[List[str]] = None,
) -> bool:
    """
    Return True (escalation needed) when the transcript contains any trigger phrase.
    Comparison is case-insensitive.
    If `phrases` is None the module-level hardcoded list is used.
    """
    phrase_list = phrases if phrases is not None else _ESCALATION_PHRASES
    lower = transcript_text.lower()
    return any(phrase in lower for phrase in phrase_list)


# ── Per-rule-type evaluator functions ─────────────────────────────────────────
# Signature: (rule, transcript_text, session_state) -> decision dict or None
# Return None to pass through (rule did not trigger).

def _eval_builtin_disclosure(
    rule: Dict[str, Any],
    transcript_text: str,
    session_state: Dict[str, Any],
    policy_version: str,
) -> Optional[Dict[str, Any]]:
    if check_disclosure(session_state):
        return {
            "action": "disclose",
            "reason_code": rule.get("rule_key", "REQUIRE_UPFRONT_DISCLOSURE"),
            "policy_version": policy_version,
        }
    return None


def _eval_phrase_match(
    rule: Dict[str, Any],
    transcript_text: str,
    session_state: Dict[str, Any],
    policy_version: str,
) -> Optional[Dict[str, Any]]:
    # Use the stored phrases list authoritatively.
    # An empty list means "no triggers configured" — match nothing.
    # Only fall back to hardcoded defaults in the legacy (non-ruleset) path.
    phrases_val = rule.get("params", {}).get("phrases")
    phrases: List[str] = phrases_val if isinstance(phrases_val, list) else []
    if check_escalation(transcript_text, phrases):
        return {
            "action": "escalate",
            "reason_code": rule.get("rule_key", "HUMAN_ESCALATION_REQUESTED"),
            "policy_version": policy_version,
        }
    return None


# Map rule_key → evaluator; rule_type is used as fallback.
_RULE_EVALUATORS: Dict[str, Callable] = {
    "REQUIRE_UPFRONT_DISCLOSURE": _eval_builtin_disclosure,
    "HUMAN_ESCALATION_REQUESTED": _eval_phrase_match,
    # rule_type aliases
    "builtin": _eval_builtin_disclosure,
    "phrase_match": _eval_phrase_match,
}


def _evaluate_rule(
    rule: Dict[str, Any],
    transcript_text: str,
    session_state: Dict[str, Any],
    policy_version: str,
) -> Optional[Dict[str, Any]]:
    """Dispatch a single rule to its evaluator, return decision dict or None."""
    key = rule.get("rule_key", "")
    rtype = rule.get("rule_type", "")
    evaluator = _RULE_EVALUATORS.get(key) or _RULE_EVALUATORS.get(rtype)
    if evaluator is None:
        return None
    return evaluator(rule, transcript_text, session_state, policy_version)


# ── Public entry point ────────────────────────────────────────────────────────

def run_voice_policy(
    transcript_text: str,
    session_state: Dict[str, Any],
    phrases: Optional[List[str]] = None,
    policy_version: Optional[str] = None,
    ruleset: Optional[List[Dict[str, Any]]] = None,
    phi_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run the voice policy engine and return an enforcement decision.

    Parameters
    ----------
    transcript_text : caller transcript chunk
    session_state   : at minimum {"disclosure_confirmed": bool}
    phrases         : (legacy) override escalation phrases; used when `ruleset` is None
    policy_version  : (legacy) version string to embed; defaults to POLICY_VERSION
    ruleset         : (preferred) full ordered rule list; when provided the
                      rule-based evaluation path is used

    Returns
    -------
    dict with keys: action, reason_code, policy_version
      action      — "disclose" | "escalate" | "allow"
      reason_code — rule key on trigger, None on allow
    """
    version = policy_version if policy_version is not None else POLICY_VERSION

    phi_gate(session_state, phi_fields)

    if ruleset is not None:
        # ── Rule-based evaluation (preferred path) ────────────────────────────
        # Rules are evaluated in ascending priority order; first trigger wins.
        for rule in sorted(ruleset, key=lambda r: r.get("priority", 0)):
            if not rule.get("enabled", True):
                continue
            decision = _evaluate_rule(rule, transcript_text, session_state, version)
            if decision is not None:
                return decision
        # Global safety phrases are enforced after all configured rules.
        # They cannot be disabled by any ruleset configuration.
        if check_escalation(transcript_text, list(_GLOBAL_SAFETY_PHRASES)):
            return {"action": "escalate", "reason_code": "HUMAN_ESCALATION_REQUESTED", "policy_version": version}
        return {"action": "allow", "reason_code": None, "policy_version": version}

    # ── Legacy path (backward-compat) ────────────────────────────────────────
    if check_disclosure(session_state):
        return {
            "action": "disclose",
            "reason_code": "REQUIRE_UPFRONT_DISCLOSURE",
            "policy_version": version,
        }

    if check_escalation(transcript_text, phrases):
        return {
            "action": "escalate",
            "reason_code": "HUMAN_ESCALATION_REQUESTED",
            "policy_version": version,
        }

    return {"action": "allow", "reason_code": None, "policy_version": version}
