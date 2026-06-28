"""
NHID-Clinical – Fabricate Battle-Test Corpus Adapter
=====================================================
Converts a Tonic Fabricate two-table CSV export (conversations.csv + turns.csv)
into the conversation-list JSON shape that
src.synthetic_eval_loop.compute_detection_rates() consumes:

    [{"conversation_id": str, "expected_violations": [str, ...],
      "turns": [{...}, ...]}, ...]

Field mapping (see adapters/twilio_adapter.py for the single-event analog):
  - expected_violations: the five *_violation booleans on the conversation
    row, mapped to rule_id strings where True.
  - session["escalation_path_available"] (applied via every turn): derived
    as `not eit01_violation` — in violation conversations the agent
    stonewalls a transfer request; in clean ones it's honored.
  - turn["speech_text"]: turns.csv text, every turn.
  - turn["identity_assertion_text"]: turns.csv text, but only for
    speaker == "agent" — DBC-01's impersonation-phrase heuristic reads this
    field specifically, not speech_text.
  - turn["disclosure_timestamp"]: sticky — set on the first turn where
    is_identity_disclosure == 1, carried forward to every later turn so a
    disclosure made once doesn't "expire".
  - turn["deceptive_artifact_flags"] / turn["phi_accessed"]: always [];
    Fabricate's schema has no structured equivalent and the engine's
    speech-text pattern matching already covers this corpus's phrasing.

Usage:
  python3 adapters/fabricate_adapter.py <conversations.csv> <turns.csv> --out <conversations.json>
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from typing import Any

VIOLATION_COLUMN_TO_RULE_ID = {
    "idg01_violation": "IDG-01",
    "pdx01_violation": "PDX-01",
    "dbc01_violation": "DBC-01",
    "eit01_violation": "EIT-01",
    "atr01_violation": "ATR-01",
}


def _is_truthy(value: str) -> bool:
    return value.strip() in ("1", "true", "True", "TRUE")


def load_turns_by_conversation(turns_csv_path: str) -> dict[str, list[dict[str, Any]]]:
    """Group turns.csv rows by conversation_id, preserving turn_index order."""
    turns_by_conversation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with open(turns_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            turns_by_conversation[row["conversation_id"]].append(row)
    for turns in turns_by_conversation.values():
        turns.sort(key=lambda r: int(r["turn_index"]))
    return turns_by_conversation


def build_turn(raw_turn: dict[str, Any], disclosure_timestamp: str | None) -> dict[str, Any]:
    """Map one turns.csv row (plus the persisted first disclosure timestamp) to a synthetic_eval_loop turn."""
    speech_text = raw_turn.get("text", "") or ""
    speaker = raw_turn.get("speaker", "unknown")

    return {
        "speech_text": speech_text,
        "identity_assertion_text": speech_text if speaker == "agent" else "",
        "deceptive_artifact_flags": [],
        "phi_accessed": [],
        "disclosure_timestamp": disclosure_timestamp,
    }


def fabricate_conversation_to_eval_shape(
    conversation_row: dict[str, Any], raw_turns: list[dict[str, Any]]
) -> dict[str, Any]:
    """Map one conversations.csv row + its turns.csv rows to the eval-loop conversation shape."""
    expected_violations = [
        rule_id
        for column, rule_id in VIOLATION_COLUMN_TO_RULE_ID.items()
        if _is_truthy(conversation_row.get(column, "0"))
    ]
    escalation_path_available = not _is_truthy(conversation_row.get("eit01_violation", "0"))

    turns: list[dict[str, Any]] = []
    disclosure_timestamp: str | None = None
    for raw_turn in raw_turns:
        if disclosure_timestamp is None and _is_truthy(
            raw_turn.get("is_identity_disclosure", "0")
        ):
            disclosure_timestamp = raw_turn.get("created_at")
        turn = build_turn(raw_turn, disclosure_timestamp)
        turn["escalation_path_available"] = escalation_path_available
        turns.append(turn)

    return {
        "conversation_id": conversation_row["id"],
        "conversation_ref": conversation_row.get("conversation_ref"),
        "scenario_type": conversation_row.get("scenario_type"),
        "target_control": conversation_row.get("target_control"),
        "expected_violations": expected_violations,
        "turns": turns,
    }


def convert(conversations_csv_path: str, turns_csv_path: str) -> list[dict[str, Any]]:
    turns_by_conversation = load_turns_by_conversation(turns_csv_path)
    conversations: list[dict[str, Any]] = []
    with open(conversations_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw_turns = turns_by_conversation.get(row["id"], [])
            conversations.append(fabricate_conversation_to_eval_shape(row, raw_turns))
    return conversations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("conversations_csv")
    parser.add_argument("turns_csv")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    conversations = convert(args.conversations_csv, args.turns_csv)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(conversations, f, indent=2)
    print(f"Wrote {len(conversations)} conversations to {args.out}")


if __name__ == "__main__":
    main()
