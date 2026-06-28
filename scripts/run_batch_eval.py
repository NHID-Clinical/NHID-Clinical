#!/usr/bin/env python3
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.synthetic_eval_loop import compute_detection_rates, print_report  # noqa: E402
def load_conversations(path):
    with open(path) as f:
        return json.load(f)
def main():
    if len(sys.argv) != 2:
        print("usage: python3 scripts/run_batch_eval.py <conversations.json>"); sys.exit(1)
    conversations = load_conversations(sys.argv[1])
    stats = compute_detection_rates(conversations)
    print_report(stats)
if __name__=="__main__": main()
