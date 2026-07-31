#!/usr/bin/env python3
"""Evaluate detection rates on the evaluation corpus."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.nhid_policy_engine_v1 import evaluate_all
from src.synthetic_eval_loop import build_event, build_session, extract_rule_ids


def load_corpus(path):
    """Load evaluation corpus (structured with metadata + scenario types)."""
    with open(path) as f:
        return json.load(f)


def evaluate_scenario(scenario_id, turns):
    """Evaluate all turns in a scenario and collect detected violations."""
    detected = set()

    for i, turn in enumerate(turns):
        try:
            session = build_session(turn)
            event = build_event(scenario_id, i, turn)
            decision = evaluate_all(session, event)
            detected.update(extract_rule_ids(decision.violations))
        except Exception as e:
            print(f"Error evaluating turn {i}: {e}")

    return detected


def main():
    corpus_path = sys.argv[1] if len(sys.argv) > 1 else "tests/evaluation_corpus_v1.json"

    if not Path(corpus_path).exists():
        print(f"Corpus not found: {corpus_path}")
        sys.exit(1)

    corpus = load_corpus(corpus_path)

    # Collect all scenarios
    scenarios = []
    scenario_types = ["compliant_scenarios", "single_rule_violations", "multi_rule_combinations"]

    for scenario_type in scenario_types:
        scenarios.extend(corpus.get(scenario_type, []))

    # Evaluate each scenario
    stats = {}
    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "unknown")
        expected_violations = set(scenario.get("expected_violations", []))
        turns = scenario.get("turns", [])

        detected_violations = evaluate_scenario(scenario_id, turns)

        # Track stats per rule
        for rule_id in expected_violations:
            bucket = stats.setdefault(rule_id, {"expected": 0, "detected": 0, "missed": []})
            bucket["expected"] += 1
            if rule_id in detected_violations:
                bucket["detected"] += 1
            else:
                bucket["missed"].append(scenario_id)

    # Calculate detection rates
    for bucket in stats.values():
        bucket["detection_rate"] = (
            bucket["detected"] / bucket["expected"] if bucket["expected"] else 0.0
        )

    # Print report
    print("\n" + "="*60)
    print("EVALUATION CORPUS DETECTION RATES")
    print("="*60)
    print(f"{'Rule':<12} {'Expected':>10} {'Detected':>10} {'Rate':>10}")
    print("-"*60)

    total_expected = 0
    total_detected = 0

    for rule_id in sorted(stats.keys()):
        bucket = stats[rule_id]
        rate = bucket["detection_rate"]
        print(f"{rule_id:<12} {bucket['expected']:>10} {bucket['detected']:>10} {rate:>9.1%}")
        total_expected += bucket["expected"]
        total_detected += bucket["detected"]

    print("-"*60)
    if total_expected:
        overall_rate = total_detected / total_expected
        print(f"{'OVERALL':<12} {total_expected:>10} {total_detected:>10} {overall_rate:>9.1%}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
