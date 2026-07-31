"""
NHID-Clinical Conformance Test Suite (CTS) runner.

Loads the YAML conformance test cases and evaluates each one against the
policy engine. Returns structured pass/fail results suitable for the API
and for CI verification.

HTTP-level edge cases (EDGE-MISSING-CALLSID, EDGE-MISSING-ALL-FIELDS) that
require a running HTTP server are automatically skipped; the remaining 16 of
18 test cases are evaluated deterministically at the policy engine layer.
"""
from __future__ import annotations

import os
from typing import Any

import yaml

from src.nhid_policy_engine_v1 import evaluate_all

_YAML_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests",
    "nhid_conformance_test_suite_v1.yaml",
)

# Cases that test HTTP 400 infrastructure — no policy_action expected.
_HTTP_ONLY_CASES = {"EDGE-MISSING-CALLSID", "EDGE-MISSING-ALL-FIELDS"}

# Substrings that indicate an AI disclosure in speech text.
_DISCLOSURE_INDICATORS = (
    "automated system",
    "not a human",
    "automated ai",
    "ai agent",
    "virtual assistant",
    "i am a bot",
    "i'm a bot",
    "automated caller",
    "not human",
)


def _build_session(preconditions: dict) -> dict:
    return {
        "turn_count": preconditions.get("turn_count", 0),
        "escalation_path_available": preconditions.get("escalation_path_available", True),
        "counterparty_type": preconditions.get("counterparty_type", "human_operator"),
    }


def _speech_contains_disclosure(text: str) -> bool:
    """True if speech text contains AI self-identification language."""
    normalized = text.lower()
    return any(phrase in normalized for phrase in _DISCLOSURE_INDICATORS)


def _build_event(test_id: str, preconditions: dict, input_script: str,
                 overrides: dict | None) -> dict:
    speech = (input_script or "").strip().replace("\x00", "")

    # If speech contains a first-turn disclosure and preconditions have no
    # disclosure_timestamp, simulate the pipeline updating disclosure state.
    # This mirrors what the full pipeline does when it detects the disclosure
    # from the agent's speech before evaluating conformance.
    precon_disclosure_ts = preconditions.get("disclosure_timestamp")
    if precon_disclosure_ts is None and _speech_contains_disclosure(speech):
        precon_disclosure_ts = "2026-06-01T00:00:00Z"
        speech_for_assertion = speech
    else:
        speech_for_assertion = preconditions.get("identity_assertion_text", "")

    event: dict[str, Any] = {
        "event_id": f"cts-{test_id}",
        "timestamp": "2026-06-01T00:00:00Z",
        "session_id": f"session-{test_id}",
        "request_id": f"req-{test_id}",
        "event_type": "POLICY",
        "state_before": preconditions.get("state", "ACTIVE"),
        "state_after": preconditions.get("state", "ACTIVE"),
        "counterparty_type": preconditions.get("counterparty_type", "human_operator"),
        "healthcare_governance": {
            "disclosure_timestamp": precon_disclosure_ts,
            "identity_assertion_text": speech_for_assertion,
            "deceptive_artifact_flags": list(
                preconditions.get("deceptive_artifact_flags") or []
            ),
            "escalation_timestamp": None,
            "escalation_outcome": None,
            "phi_accessed": list(preconditions.get("phi_already_exchanged") or []),
        },
        "input_payload": {
            "speech_text": speech,
            "raw_form_fields": None,
        },
        "execution_context": {
            "pipeline_version": "1.0.0",
            "policy_engine_version": "1.0.0",
            "nhid_schema_version": "1.0",
        },
        "actor_id": f"cts-agent-{test_id}",
        "replay_mode": "test",
        "external_calls_cached": True,
    }

    if overrides:
        for k, v in overrides.items():
            if k == "execution_context" and isinstance(v, dict):
                event["execution_context"].update(v)
            else:
                event[k] = v

    return event


def _check_violations(expected: list[dict], actual_violations: list) -> tuple[bool, str]:
    """Return (matched, detail_message).

    Each expected violation must have at least one matching actual violation
    with the same rule_id and severity. If description_contains is set, at
    least one actual violation with that rule_id/severity must contain the
    substring (handles multiple violations with the same rule_id/severity).
    """
    actual = [
        {"rule_id": v.rule_id, "severity": v.severity.value, "description": v.description}
        for v in actual_violations
    ]
    for exp in expected:
        rule_id = exp.get("rule_id")
        severity = exp.get("severity")
        desc_contains = exp.get("description_contains")

        candidates = [a for a in actual if a["rule_id"] == rule_id and a["severity"] == severity]
        if not candidates:
            return False, f"Missing violation {rule_id}/{severity}"
        if desc_contains:
            if not any(desc_contains in c["description"] for c in candidates):
                return False, (
                    f"Violation {rule_id}/{severity} — no match for '{desc_contains}' "
                    f"in: {[c['description'][:60] for c in candidates]}"
                )
    return True, ""


def run_cts(yaml_path: str | None = None,
            test_ids: list[str] | None = None) -> dict:
    """
    Run NHID conformance test cases from the YAML test suite.

    Args:
        yaml_path: Override path to the YAML file. Defaults to the canonical path.
        test_ids:  Optional subset of test_id strings to run. Runs all if None.

    Returns:
        {
            "passed": int,
            "failed": int,
            "skipped": int,
            "total": int,
            "results": [
                {
                    "test_id": str,
                    "nhid_test_ref": str,
                    "status": "pass" | "fail" | "skip",
                    "expected_action": str | None,
                    "actual_action": str | None,
                    "violations_matched": bool,
                    "detail": str,
                }
            ]
        }
    """
    path = yaml_path or _YAML_PATH
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load_all(fh)
        cases = []
        for doc in raw:
            if doc is None:
                continue
            if isinstance(doc, list):
                cases.extend(doc)
            else:
                cases.append(doc)

    if test_ids is not None:
        cases = [c for c in cases if c.get("test_id") in test_ids]

    results = []
    passed = failed = skipped = 0

    for case in cases:
        tid = case.get("test_id", "unknown")
        ref = case.get("nhid_test_ref", "")
        expected_action = case.get("expected_policy_action")

        if tid in _HTTP_ONLY_CASES or expected_action is None:
            skipped += 1
            results.append({
                "test_id": tid,
                "nhid_test_ref": ref,
                "status": "skip",
                "expected_action": None,
                "actual_action": None,
                "violations_matched": None,
                "detail": "HTTP-infrastructure test; skipped at policy-engine layer",
            })
            continue

        preconditions = case.get("preconditions", {})
        input_script = case.get("input_script", "")
        overrides = case.get("input_event_overrides")
        expected_violations = case.get("expected_violations") or []

        session = _build_session(preconditions)
        policy_event = _build_event(tid, preconditions, input_script, overrides)

        decision = evaluate_all(session, policy_event)
        actual_action = decision.action.value

        action_ok = actual_action == expected_action
        violations_ok, viol_detail = _check_violations(
            expected_violations, decision.violations
        )

        if action_ok and violations_ok:
            passed += 1
            status = "pass"
            detail = ""
        else:
            failed += 1
            status = "fail"
            parts = []
            if not action_ok:
                parts.append(
                    f"action: expected {expected_action!r}, got {actual_action!r}"
                )
            if not violations_ok:
                parts.append(viol_detail)
            detail = "; ".join(parts)

        results.append({
            "test_id": tid,
            "nhid_test_ref": ref,
            "status": status,
            "expected_action": expected_action,
            "actual_action": actual_action,
            "violations_matched": violations_ok,
            "detail": detail,
        })

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": len(results),
        "results": results,
    }
