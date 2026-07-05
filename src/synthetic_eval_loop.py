"""
NHID-Clinical Synthetic Detection-Rate Evaluator
==================================================
Runs a batch of synthetic conversations (each a list of "turns") through
the policy engine's `evaluate_all` and reports a per-control detection
rate: of the violations a conversation's fixture says it should trigger,
how many did the engine actually surface.

Why this module exists
-----------------------
A naive version of this loop tends to report 0 detections for DBC-01 and
EIT-01 even though IDG-01 / PDX-01 / ATR-01 work fine. That is not a bug
in the policy engine (see src/nhid_policy_engine_v1.py) — those two rules
are conditioned on fields that a careless per-turn dict-builder silently
drops:

  - EIT-01 only produces a violation when BOTH (a) the turn's speech asks
    for a human AND (b) `session["escalation_path_available"]` is False
    for that turn. `evaluate_eit01` defaults escalation_path_available to
    True (see _safe_get(..., default=True) in the engine), so if a loop
    builds `session` once per conversation and never threads the turn's
    `escalation_path_available` override into it, every EIT-01 fixture
    silently evaluates as "no violation" — not an engine failure, a
    wiring gap in the harness.

  - DBC-01 only inspects `event["healthcare_governance"]["deceptive_artifact_flags"]`
    and `event["healthcare_governance"]["identity_assertion_text"]`. If a
    harness stores artifact flags as a top-level `turn["deceptive_artifact_flags"]`
    and never copies them into the nested `healthcare_governance` dict the
    engine actually reads, DBC-01 has nothing to inspect and returns 0
    violations every time, regardless of how many fixtures expect one.

This module fixes both: `build_session` and `build_event` thread every
turn-level override (escalation_path_available, deceptive_artifact_flags,
identity_assertion_text, ...) into the exact nested location the engine
reads, mirroring the pattern already established in src/cts_runner.py.
"""
from __future__ import annotations

from typing import Any

from src.nhid_policy_engine_v1 import evaluate_all, BoundaryViolation


# ──────────────────────────────────────────────────────────────────────────
# Rule-ID extraction
# ──────────────────────────────────────────────────────────────────────────

def extract_rule_ids(violations: list[Any]) -> list[str]:
    """
    Pull `rule_id` off each violation in a decision's `.violations` list.

    Accepts both the real `BoundaryViolation` dataclass instances that
    `evaluate_all` returns and dict-shaped violations (e.g. fixtures
    loaded straight from JSON/YAML), so the same extraction code works
    whether you're reading live engine output or a stored expected-result
    fixture.
    """
    ids: list[str] = []
    for v in violations:
        if isinstance(v, BoundaryViolation) or hasattr(v, "rule_id"):
            rule_id = v.rule_id
        elif isinstance(v, dict):
            rule_id = v.get("rule_id")
        else:
            rule_id = None
        if rule_id:
            ids.append(rule_id)
    return ids


# ──────────────────────────────────────────────────────────────────────────
# Turn -> (session, event) builders
# ──────────────────────────────────────────────────────────────────────────
# A "turn" is a plain dict describing one conversational exchange. Every
# field below is optional except `speech_text`; missing fields fall back
# to conformant defaults so a turn that isn't testing a given control
# doesn't accidentally trip it.

def build_session(turn: dict[str, Any]) -> dict[str, Any]:
    """Build the `session` dict evaluate_all() expects, from one turn."""
    return {
        "turn_count": turn.get("turn_count", 0),
        # Default True so turns that aren't testing EIT-01 don't spuriously
        # fail it — but a turn that sets this False MUST have it carried
        # through, which is exactly the wiring a naive loop tends to drop.
        "escalation_path_available": turn.get("escalation_path_available", True),
        "counterparty_type": turn.get("counterparty_type", "human_operator"),
    }


def build_event(conversation_id: str, turn_index: int, turn: dict[str, Any]) -> dict[str, Any]:
    """Build the `event` dict evaluate_all() expects, from one turn."""
    speech_text = turn.get("speech_text", "") or ""
    state = turn.get("state", "ACTIVE")

    return {
        "event_id": f"{conversation_id}-turn-{turn_index}",
        "timestamp": turn.get("timestamp", "2026-06-01T00:00:00Z"),
        "session_id": conversation_id,
        "request_id": f"req-{conversation_id}-{turn_index}",
        "event_type": "POLICY",
        "actor_id": turn.get("actor_id", f"agent-{conversation_id}"),
        "counterparty_type": turn.get("counterparty_type", "human_operator"),
        "state_before": state,
        "state_after": state,
        "healthcare_governance": {
            "disclosure_timestamp": turn.get("disclosure_timestamp"),
            "identity_assertion_text": turn.get("identity_assertion_text", ""),
            # The field DBC-01 actually reads. Must come from the turn,
            # not be left to default to [] regardless of fixture intent.
            "deceptive_artifact_flags": list(turn.get("deceptive_artifact_flags") or []),
            "escalation_timestamp": turn.get("escalation_timestamp"),
            "escalation_outcome": turn.get("escalation_outcome"),
            "phi_accessed": list(turn.get("phi_accessed") or []),
        },
        "input_payload": {
            "speech_text": speech_text,
            "raw_form_fields": None,
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "replay_mode": "test",
        "external_calls_cached": True,
    }


# ──────────────────────────────────────────────────────────────────────────
# Evaluation loop
# ──────────────────────────────────────────────────────────────────────────

def evaluate_conversation(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Run every turn of one conversation through evaluate_all().

    Returns one result dict per turn:
        {"turn_index": int, "action": str, "detected_rule_ids": [str, ...]}
    """
    conversation_id = conversation.get("conversation_id", "unknown")
    results = []
    for i, turn in enumerate(conversation.get("turns", [])):
        session = build_session(turn)
        event = build_event(conversation_id, i, turn)
        decision = evaluate_all(session, event)
        results.append({
            "turn_index": i,
            "action": decision.action.value,
            "detected_rule_ids": extract_rule_ids(decision.violations),
        })
    return results


def compute_detection_rates(conversations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Aggregate per-control detection rates across many conversations.

    Each conversation may declare `expected_violations` as a list of
    rule_id strings (e.g. ["DBC-01"]) meaning: across this conversation's
    turns, at least one turn must surface that rule_id. Returns:

        {
            "DBC-01": {
                "expected": 12,
                "detected": 11,
                "missed": [conversation_id, ...],
                "detection_rate": 0.9166...,
            },
            ...
        }
    """
    stats: dict[str, dict[str, Any]] = {}

    for conversation in conversations:
        conversation_id = conversation.get("conversation_id", "unknown")
        expected_rule_ids = conversation.get("expected_violations", [])
        if not expected_rule_ids:
            continue

        turn_results = evaluate_conversation(conversation)
        detected_rule_ids = {
            rid for r in turn_results for rid in r["detected_rule_ids"]
        }

        for rule_id in expected_rule_ids:
            bucket = stats.setdefault(rule_id, {"expected": 0, "detected": 0, "missed": []})
            bucket["expected"] += 1
            if rule_id in detected_rule_ids:
                bucket["detected"] += 1
            else:
                bucket["missed"].append(conversation_id)

    for bucket in stats.values():
        bucket["detection_rate"] = (
            bucket["detected"] / bucket["expected"] if bucket["expected"] else 0.0
        )

    return stats


def print_report(stats: dict[str, dict[str, Any]]) -> None:
    """Print a clean, human-readable detection-rate table."""
    if not stats:
        print("No conversations declared expected_violations — nothing to report.")
        return

    header = f"{'rule_id':<10} {'expected':>9} {'detected':>9} {'rate':>8}"
    print(header)
    print("-" * len(header))
    for rule_id in sorted(stats):
        s = stats[rule_id]
        print(f"{rule_id:<10} {s['expected']:>9} {s['detected']:>9} {s['detection_rate']:>7.1%}")
        if s["missed"]:
            print(f"  missed in: {', '.join(s['missed'])}")


if __name__ == "__main__":
    # Minimal smoke run using the conformance-suite-style fixtures defined
    # in tests/test_synthetic_eval_loop.py would require importing pytest
    # fixtures; for a quick manual check, see that test file instead.
    print("Import this module and call compute_detection_rates(conversations).")
