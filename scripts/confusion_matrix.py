#!/usr/bin/env python3
"""
Per-control confusion matrix for the NHID-Clinical policy engine against a
Fabricate battle-test corpus.

Reports, per control:
  - detection: expected / detected / detection_rate + missed conversation IDs
  - false positives on TRUE-compliant conversations (scenario_type == "compliant"):
    a detected rule_id on a conversation whose ground truth is clean.

Detection and FP are measured on disjoint populations:
  - detection over conversations that declare that expected violation
  - FP over conversations whose scenario_type is exactly "compliant"

This keeps heuristic FN vs FP tradeoffs visible and honest — text-matching
detection has inherent error on both sides; nothing here is a conformance claim.

Usage (Windows / PowerShell friendly):
  python confusion_matrix.py <corpus.jsonl>
  python confusion_matrix.py <conversations.csv> <turns.csv>
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

# Resolve the repo root robustly: walk up from this file until we find the
# directory that contains both 'adapters' and 'src'. Works whether this script
# lives in <repo>/scripts/ or is run from elsewhere.
_here = Path(__file__).resolve()
REPO = next(
    (p for p in [_here.parent, *_here.parents]
     if (p / "adapters").is_dir() and (p / "src").is_dir()),
    _here.parent.parent,
)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from adapters.fabricate_adapter import convert_csv, convert_jsonl  # noqa: E402
from synthetic_eval_loop import evaluate_conversation  # noqa: E402

ALL_CONTROLS = ["IDG-01", "PDX-01", "DBC-01", "EIT-01"]


def load(argv: list[str]) -> list[dict]:
    if len(argv) == 2 and argv[1].lower().endswith(".jsonl"):
        return convert_jsonl(argv[1])
    if len(argv) == 3:
        return convert_csv(argv[1], argv[2])
    raise SystemExit(__doc__)


def compute(conversations: list[dict]) -> dict:
    """Pure confusion-matrix computation shared by the CLI and other callers.

    Detection is measured over conversations that declare each control in
    `expected_violations`; false positives over the DISJOINT population of
    conversations whose `scenario_type == "compliant"`. ATR-01 is excluded
    (untestable in transcript replay). Returns structured results; prints
    nothing.
    """
    detect = {c: {"expected": 0, "detected": 0, "missed": []} for c in ALL_CONTROLS}
    fp = {c: {"clean": 0, "fp": 0, "fp_ids": []} for c in ALL_CONTROLS}

    n_compliant = 0
    for conv in conversations:
        cid = conv.get("conversation_id", "?")
        expected = set(conv.get("expected_violations", []))
        detected = {
            rid
            for r in evaluate_conversation(conv)
            for rid in r["detected_rule_ids"]
        }

        for ctrl in expected:
            if ctrl in detect:
                detect[ctrl]["expected"] += 1
                if ctrl in detected:
                    detect[ctrl]["detected"] += 1
                else:
                    detect[ctrl]["missed"].append(cid)

        if conv.get("scenario_type") == "compliant":
            n_compliant += 1
            for ctrl in ALL_CONTROLS:
                fp[ctrl]["clean"] += 1
                if ctrl in detected and ctrl not in expected:
                    fp[ctrl]["fp"] += 1
                    fp[ctrl]["fp_ids"].append(cid)

    controls = []
    for ctrl in ALL_CONTROLS:
        d, f = detect[ctrl], fp[ctrl]
        controls.append({
            "control": ctrl,
            "expected": d["expected"],
            "detected": d["detected"],
            "detection_rate": (d["detected"] / d["expected"]) if d["expected"] else None,
            "missed": d["missed"],
            "clean": f["clean"],
            "fp": f["fp"],
            "fp_rate": (f["fp"] / f["clean"]) if f["clean"] else None,
            "fp_ids": f["fp_ids"],
        })
    return {"n_conversations": len(conversations),
            "n_compliant": n_compliant, "controls": controls}


def run(conversations: list[dict]) -> None:
    result = compute(conversations)
    by = {c["control"]: c for c in result["controls"]}
    detect = {c: {"expected": by[c]["expected"], "detected": by[c]["detected"],
                  "missed": by[c]["missed"]} for c in ALL_CONTROLS}
    fp = {c: {"clean": by[c]["clean"], "fp": by[c]["fp"],
              "fp_ids": by[c]["fp_ids"]} for c in ALL_CONTROLS}
    n_compliant = result["n_compliant"]

    print(f"\nCorpus: {len(conversations)} conversations "
          f"({n_compliant} scenario_type=compliant)\n")
    hdr = f"{'control':<8} {'detect':>10} {'rate':>7}   {'FP/clean':>10} {'FP rate':>8}"
    print(hdr)
    print("-" * len(hdr))
    for ctrl in ALL_CONTROLS:
        d, f = detect[ctrl], fp[ctrl]
        rate = d["detected"] / d["expected"] if d["expected"] else float("nan")
        fprate = f["fp"] / f["clean"] if f["clean"] else float("nan")
        det_s = f"{d['detected']}/{d['expected']}"
        fp_s = f"{f['fp']}/{f['clean']}"
        rate_s = "  n/a " if d["expected"] == 0 else f"{rate:6.1%}"
        fpr_s = "  n/a " if f["clean"] == 0 else f"{fprate:6.1%}"
        print(f"{ctrl:<8} {det_s:>10} {rate_s:>7}   {fp_s:>10} {fpr_s:>8}")

    for ctrl in ALL_CONTROLS:
        if detect[ctrl]["missed"]:
            miss = detect[ctrl]["missed"]
            print(f"\n{ctrl} missed ({len(miss)}): "
                  + ", ".join(miss[:8]) + (" ..." if len(miss) > 8 else ""))
    for ctrl in ALL_CONTROLS:
        if fp[ctrl]["fp_ids"]:
            ids = fp[ctrl]["fp_ids"]
            print(f"{ctrl} FP on compliant ({len(ids)}): "
                  + ", ".join(ids[:8]) + (" ..." if len(ids) > 8 else ""))


if __name__ == "__main__":
    run(load(sys.argv))
