#!/usr/bin/env python3
"""
Vet a candidate DBC-01 phrase/keyword against the full Fabricate real-corpus
before merging it into `_DBC_IMPERSONATION_PHRASES`. Per archive §9.1
invariant #7: a candidate only clears the bar if it produces zero
false-positive hits across every dbc01_violation=0 agent turn.

Usage:
  python3 scripts/mine_heuristic_candidate.py "personally take care of"
  python3 scripts/mine_heuristic_candidate.py "human" --negate "not a human,automated,ai system"
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.nhid_policy_engine_v1 import _assertion_implies_human  # noqa: E402

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fabricate"


def load_corpus():
    with open(FIXTURES / "conversations.csv", newline="", encoding="utf-8") as f:
        convs = {r["id"]: r for r in csv.DictReader(f)}
    with open(FIXTURES / "turns.csv", newline="", encoding="utf-8") as f:
        turns = list(csv.DictReader(f))
    return convs, [t for t in turns if t.get("speaker") == "agent"]


def score_candidate(candidate: str, negators: list[str], convs: dict, agent_turns: list) -> dict:
    candidate = candidate.lower()
    true_positives, false_positives = [], []

    for turn in agent_turns:
        text = (turn.get("text") or "").lower()
        if candidate not in text:
            continue
        if _assertion_implies_human(text) is not None:
            continue  # already caught by an existing phrase; not a new signal
        if any(n.lower() in text for n in negators):
            continue

        conv = convs.get(turn["conversation_id"], {})
        bucket = true_positives if conv.get("dbc01_violation") == "1" else false_positives
        bucket.append((turn["conversation_id"], turn["text"]))

    return {"true_positives": true_positives, "false_positives": false_positives}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", help="Substring to test, e.g. 'i'll personally'")
    parser.add_argument(
        "--negate",
        default="",
        help="Comma-separated negation phrases that suppress a match (disclosure language)",
    )
    args = parser.parse_args()

    negators = [n.strip() for n in args.negate.split(",") if n.strip()]
    convs, agent_turns = load_corpus()
    result = score_candidate(args.candidate, negators, convs, agent_turns)

    tp, fp = result["true_positives"], result["false_positives"]
    print(f"candidate: {args.candidate!r}")
    print(f"new true positives (dbc01_violation=1 convs):  {len(tp)}")
    print(f"new false positives (dbc01_violation=0 convs): {len(fp)}")
    print()
    verdict = "CLEARS THE BAR (0 false positives)" if not fp else "REJECTED (non-zero false positives)"
    print(f"verdict: {verdict}")

    if fp:
        print("\nfirst 5 false positives:")
        for conv_id, text in fp[:5]:
            print(f"  [{conv_id}] {text[:140]}")


if __name__ == "__main__":
    main()
