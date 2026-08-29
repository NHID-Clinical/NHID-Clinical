#!/usr/bin/env python3
"""
Evaluate detection rates on the Governance Evaluation Corpus.

Reports two things, kept strictly separate because conflating them is how the
project ended up publishing an unsupported figure:

  * **Detection** — of the violations a scenario declares in
    `expected_violations`, how many did the engine surface. Measured over the
    20 scenarios that declare one.
  * **False positives** — of the compliant scenarios (those declaring no
    expected violations), how many emitted a violation anyway. Measured over
    the disjoint population of 5 compliant scenarios.

Before this script computed the second number, "0% false-positive rate" was
published against this corpus with nothing behind it. It is reported here so
the claim has a source, whatever the source says.

Usage:
    python scripts/eval_corpus.py [corpus.json]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.nhid_policy_engine_v1 import evaluate_all
from src.synthetic_eval_loop import (
    build_event,
    build_session,
    carry_disclosure_forward,
    extract_rule_ids,
)

SCENARIO_TYPES = ["compliant_scenarios", "single_rule_violations", "multi_rule_combinations"]


def load_corpus(path):
    """Load evaluation corpus (structured with metadata + scenario types)."""
    with open(path) as f:
        return json.load(f)


def evaluate_scenario(scenario_id, turns):
    """Evaluate all turns in a scenario and collect detected violations."""
    detected = set()

    # Disclosure is a conversation-level fact, not a per-turn one. Without this
    # every turn after the disclosing one looks undisclosed and the compliant
    # scenarios all report IDG-01/PDX-01. See carry_disclosure_forward().
    for i, turn in enumerate(carry_disclosure_forward(turns)):
        try:
            session = build_session(turn)
            event = build_event(scenario_id, i, turn)
            decision = evaluate_all(session, event)
            detected.update(extract_rule_ids(decision.violations))
        except Exception as e:
            print(f"Error evaluating turn {i}: {e}")

    return detected


def collect_scenarios(corpus):
    """Flatten the corpus's three scenario groups into one list."""
    scenarios = []
    for scenario_type in SCENARIO_TYPES:
        scenarios.extend(corpus.get(scenario_type, []))
    return scenarios


def evaluate_corpus(scenarios):
    """
    Run every scenario and return (detection_stats, false_positives).

    `false_positives` maps each compliant scenario's id to the sorted rule ids
    it emitted — an empty list means that scenario is clean.
    """
    stats = {}
    false_positives = {}

    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "unknown")
        expected_violations = set(scenario.get("expected_violations") or [])
        turns = scenario.get("turns", [])

        detected_violations = evaluate_scenario(scenario_id, turns)

        if not expected_violations:
            # A compliant scenario. Anything it emits is a false positive, and
            # it contributes nothing to the detection denominators.
            false_positives[scenario_id] = sorted(detected_violations)
            continue

        for rule_id in expected_violations:
            bucket = stats.setdefault(rule_id, {"expected": 0, "detected": 0, "missed": []})
            bucket["expected"] += 1
            if rule_id in detected_violations:
                bucket["detected"] += 1
            else:
                bucket["missed"].append(scenario_id)

    for bucket in stats.values():
        bucket["detection_rate"] = (
            bucket["detected"] / bucket["expected"] if bucket["expected"] else 0.0
        )

    return stats, false_positives


def print_detection(stats):
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
    print("="*60)


def print_false_positives(false_positives):
    clean_total = len(false_positives)
    dirty = {sid: rules for sid, rules in false_positives.items() if rules}

    print("\n" + "="*60)
    print("FALSE POSITIVES (compliant scenarios only)")
    print("="*60)
    if not clean_total:
        print("No compliant scenarios in this corpus — false-positive rate not measurable.")
        print("="*60 + "\n")
        return

    print(f"Compliant scenarios: {clean_total}")
    print(f"Emitting >= 1 violation: {len(dirty)}  ({len(dirty)/clean_total:.1%})")

    per_rule = {}
    for rules in false_positives.values():
        for rule_id in rules:
            per_rule[rule_id] = per_rule.get(rule_id, 0) + 1

    if per_rule:
        print("-"*60)
        print(f"{'Rule':<12} {'Scenarios':>10} {'FP rate':>10}")
        for rule_id in sorted(per_rule):
            n = per_rule[rule_id]
            print(f"{rule_id:<12} {n:>10} {n/clean_total:>9.1%}")
        print("-"*60)
        for sid, rules in sorted(dirty.items()):
            print(f"  {sid}: {', '.join(rules)}")
    print("="*60 + "\n")


def main():
    corpus_path = sys.argv[1] if len(sys.argv) > 1 else "tests/evaluation_corpus_v1.json"

    if not Path(corpus_path).exists():
        print(f"Corpus not found: {corpus_path}")
        sys.exit(1)

    corpus = load_corpus(corpus_path)
    scenarios = collect_scenarios(corpus)
    stats, false_positives = evaluate_corpus(scenarios)

    print(f"\nCorpus: {corpus_path}")
    print(f"Scenarios: {len(scenarios)}   Turns: {sum(len(s.get('turns', [])) for s in scenarios)}")
    print_detection(stats)
    print_false_positives(false_positives)


if __name__ == "__main__":
    main()
