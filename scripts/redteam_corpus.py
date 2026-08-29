#!/usr/bin/env python3
"""
Adversarial red-team evaluation.

Runs tests/adversarial_corpus_v1.json — realistic attempts by a healthcare
voice agent to evade IDG-01 and PDX-01 — and reports bypasses (an expected
violation the engine missed) separately from false positives (a violation on a
scenario labelled compliant).

This corpus is NOT the Governance Evaluation Corpus and NOT the conformance
suite. Its numbers describe how hard the engine is to fool, not how it scores
on the published corpus, and the three must never be combined.

Usage:
    python scripts/redteam_corpus.py            # report
    python scripts/redteam_corpus.py --verbose  # show every scenario
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.nhid_policy_engine_v1 import evaluate_all
from src.synthetic_eval_loop import (
    build_event, build_session, carry_disclosure_forward, extract_rule_ids,
)

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "tests" / "adversarial_corpus_v1.json"


def detect(scenario):
    """Rule ids the engine surfaces anywhere in the scenario."""
    found = set()
    for i, turn in enumerate(carry_disclosure_forward(scenario["turns"])):
        decision = evaluate_all(build_session(turn),
                                build_event(scenario["scenario_id"], i, turn))
        found.update(extract_rule_ids(decision.violations))
    return found


def evaluate(scenarios):
    bypasses, false_positives, caught = [], [], []
    for s in scenarios:
        expected = set(s.get("expected_violations") or [])
        found = detect(s)
        missed = expected - found
        if not expected:
            if found:
                false_positives.append((s, sorted(found)))
        elif missed:
            bypasses.append((s, sorted(missed), sorted(found)))
        else:
            caught.append(s)
    return bypasses, false_positives, caught


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the adversarial red-team corpus.")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    scenarios = corpus["scenarios"]
    bypasses, false_positives, caught = evaluate(scenarios)

    attacks = [s for s in scenarios if s.get("expected_violations")]
    controls = [s for s in scenarios if not s.get("expected_violations")]

    print("=" * 68)
    print("ADVERSARIAL RED-TEAM CORPUS")
    print("=" * 68)
    print(f"Scenarios: {len(scenarios)}  ({len(attacks)} attacks, "
          f"{len(controls)} compliant controls)")
    print(f"Turns: {sum(len(s['turns']) for s in scenarios)}")
    print("-" * 68)
    held = len(attacks) - len(bypasses)
    print(f"Attacks withstood:      {held}/{len(attacks)}"
          f"  ({held / len(attacks):.1%})" if attacks else "no attacks")
    print(f"Successful bypasses:    {len(bypasses)}")
    print(f"False positives:        {len(false_positives)}/{len(controls)}"
          f"  ({len(false_positives) / len(controls):.1%})" if controls else "")

    if bypasses:
        print("-" * 68)
        print("BYPASSES")
        for s, missed, found in bypasses:
            print(f"  {s['scenario_id']}")
            print(f"      attack:  {s['attack']}")
            print(f"      missed:  {', '.join(missed)}")
            print(f"      engine reported: {', '.join(found) or 'nothing'}")

    if false_positives:
        print("-" * 68)
        print("FALSE POSITIVES")
        for s, found in false_positives:
            print(f"  {s['scenario_id']}: {', '.join(found)}")
            print(f"      {s['attack']}")

    if args.verbose:
        print("-" * 68)
        for s in caught:
            print(f"  held  {s['scenario_id']}: {s['attack']}")

    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
