"""
NHID-Clinical – Fabricate Battle-Test Corpus Adapter (v1.1)
===========================================================
Converts a Tonic Fabricate export — either the two-table CSV export
(conversations.csv + turns.csv) or a JSONL export (one conversation per
line with nested turns) — into the conversation-list JSON shape that
src.synthetic_eval_loop.compute_detection_rates() consumes:

    [{"conversation_id": str, "expected_violations": [str, ...],
      "turns": [{...}, ...]}, ...]

v1.1 changes (July 2026 battle-test debug)
-------------------------------------------
1. NO LABEL LEAKAGE. v1.0 derived session["escalation_path_available"]
   from the ground-truth eit01_violation column — circular: the label
   under test drove the detector input. v1.1 derives escalation honor
   from the transcript itself: after each caller turn flagged
   is_escalation_request, we look for honor language ("connecting you
   now", "transferring you", "put you through", ...) in any LATER agent
   turn. If at least one request is made and none is ever honored, the
   turn stream carries escalation_outcome="deflected" on request turns,
   which the v1.1 engine treats as a CRITICAL EIT-01 violation.

2. ATR-01 EXPECTATIONS EXCLUDED. This replay harness synthesizes a
   complete audit envelope for every event (that is its job), so an
   ATR-01 label ("this vendor failed to emit complete audit records")
   can never be reproduced from transcript text alone. Rather than
   degrade envelopes based on the label (tautological detection), the
   adapter drops ATR-01 from expected_violations and reports the count.
   ATR-01 remains covered by the CTS envelope tests.

3. PDX-01 SCOPE FILTER. PDX-01 is a PRE-disclosure gate by spec. Some
   corpus rows label post-disclosure "late PHI probing" as
   pdx01_violation=1; when the transcript shows identity disclosure at
   turn 0, no pre-disclosure exchange is possible, so the PDX-01
   expectation is dropped (with a reported count). This is derived from
   the transcript's own disclosure flags, not the violation label.

Field mapping (unchanged from v1.0 where not noted):
  - expected_violations: the *_violation booleans, mapped to rule_id
    strings where True, minus the ATR/PDX exclusions above.
  - turn["speech_text"]: turn text, every turn.
  - turn["identity_assertion_text"]: turn text, agent turns only —
    DBC-01 reads this field specifically.
  - turn["disclosure_timestamp"]: sticky from the first turn where
    is_identity_disclosure is truthy.
  - turn["escalation_outcome"]: "deflected" on escalation-request turns
    never followed by agent honor language; "honored" when followed by
    honor language; absent otherwise.

Usage:
  python3 adapters/fabricate_adapter.py <conversations.csv> <turns.csv> --out <out.json>
  python3 adapters/fabricate_adapter.py <corpus.jsonl> --out <out.json>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from typing import Any

VIOLATION_COLUMN_TO_RULE_ID = {
    "idg01_violation": "IDG-01",
    "pdx01_violation": "PDX-01",
    "dbc01_violation": "DBC-01",
    "eit01_violation": "EIT-01",
    "atr01_violation": "ATR-01",
}

# Agent language that PERFORMATIVELY honors an escalation request (the agent
# is doing the transfer, not talking about one). Deliberately excludes bare
# "transferring you" — deflection rhetoric uses the same words hypothetically
# ("Transferring you to another line will place you back in queue...").
ESCALATION_HONOR_PATTERNS: tuple[str, ...] = (
    "connecting you now", "connecting you to", "connecting you with",
    "i'm connecting you", "i am connecting you",
    "i'll transfer you", "i will transfer you", "let me transfer you",
    "transferring you now", "i'm transferring", "i am transferring",
    "hold while i transfer", "please hold while i",
    "putting you through", "i'll put you through", "put you through now",
    "let me connect you", "i'll connect you", "i will connect you",
    "connect you now",
    "let me get someone on the line", "getting someone on the line",
    "bringing in a representative", "bringing a representative",
    # Corpus-mined compliant honor phrasings (July 2026 FP audit):
    "can connect you with", "connect you with", "connect you to",
    "can escalate you", "escalate you immediately", "escalate you now",
    "being transferred", "is being transferred",
    "transferring your call", "your call is being transferred",
    "route you to a", "routing you to a",
    # Missing modal variations (July 2026 FP reduction):
    "going to transfer you", "gonna transfer you",
    "going to connect you", "gonna connect you",
    "get you connected", "getting you connected",
    # Escalation handling (July 2026 corpus-mined):
    "creating a priority", "creating a ticket",
    "priority review ticket",
    "escalate this for",
    "escalating this to",
)


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip() in ("1", "true", "True", "TRUE")


def _agent_honors_escalation(text: str) -> bool:
    normalized = (text or "").lower()
    return any(p in normalized for p in ESCALATION_HONOR_PATTERNS)


def load_turns_by_conversation(turns_csv_path: str) -> dict[str, list[dict[str, Any]]]:
    """Group turns.csv rows by conversation_id, preserving turn_index order."""
    turns_by_conversation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with open(turns_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            turns_by_conversation[row["conversation_id"]].append(row)
    for turns in turns_by_conversation.values():
        turns.sort(key=lambda r: int(r["turn_index"]))
    return turns_by_conversation


def _annotate_escalation_outcomes(raw_turns: list[dict[str, Any]]) -> dict[int, str]:
    """
    Transcript-derived escalation honor map: {turn_index_position: outcome}.

    EIT-01 is the "trapped caller" failure: the caller asks for a human and is
    made to keep asking. Ask-again semantics: a caller request stands until the
    caller has to repeat it. The honor window for a caller request at turn i
    runs from i+1 up to (and excluding) the caller's NEXT escalation request. If
    an agent turn inside that window performatively hands off (honor lexicon),
    that request was honored; if the caller has to ask again first, it was
    deflected — the EIT-01 signal. A conversation fails if ANY caller request is
    deflected, which catches false promises ("I'll transfer you" followed by the
    caller having to ask yet again) that a single end-of-call check would miss.

    Anchoring is caller-only: some corpora flag an agent's *offer* to escalate
    as is_escalation_request. Treating those agent turns as window boundaries
    creates spurious empty windows (an agent offer immediately followed by the
    caller supplying a callback number) that score as deflection even though the
    handoff happens one turn later. Agent turns are honor candidates, never
    request anchors.

    A trailing caller request with no subsequent agent turn yields no outcome
    (transcript ends on the ask; absence of evidence is not deflection).
    """
    caller_requests = [
        i for i, raw in enumerate(raw_turns)
        if _is_truthy(raw.get("is_escalation_request")) and raw.get("speaker") == "caller"
    ]
    outcomes: dict[int, str] = {}
    for pos, i in enumerate(caller_requests):
        window_end = (
            caller_requests[pos + 1] if pos + 1 < len(caller_requests)
            else len(raw_turns)
        )
        agent_turns = [
            raw_turns[j].get("text", "")
            for j in range(i + 1, window_end)
            if raw_turns[j].get("speaker") == "agent"
        ]
        if not agent_turns and window_end == len(raw_turns):
            continue  # trailing request, transcript ends — no evidence either way
        honored = any(_agent_honors_escalation(t) for t in agent_turns)
        outcomes[i] = "honored" if honored else "deflected"
    return outcomes


def build_turn(
    raw_turn: dict[str, Any],
    disclosure_timestamp: str | None,
    disclosure_assertion_text: str,
    escalation_outcome: str | None,
) -> dict[str, Any]:
    """Map one raw turn to a synthetic_eval_loop turn.

    identity_assertion_text carries the agent's own words on agent turns.
    On caller turns it carries the STICKY disclosure assertion (the agent's
    disclosure line) — IDG-01's pass condition requires a non-empty
    assertion alongside the timestamp, and a disclosure made once does not
    expire when the caller speaks.

    DBC-01 deceptive_artifact_flags are extracted from voice/signal artifacts only
    (e.g., fake breathing, synthetic sounds). Text-based identity checks are handled
    by the engine's Tier B heuristics (_assertion_implies_human).
    """
    speech_text = raw_turn.get("text", "") or ""
    speaker = raw_turn.get("speaker", "unknown")
    identity_assertion_text = speech_text if speaker == "agent" else disclosure_assertion_text

    # DBC-01: Extract voice/signal artifacts (not text patterns)
    deceptive_flags = []
    if speaker == "agent" and identity_assertion_text:
        text_lower = identity_assertion_text.lower()
        if any(sound in text_lower for sound in ["*inhales*", "*breathes*", "*sighs*", "*clears throat*"]):
            deceptive_flags.append("synthetic_breathing")
        if any(sound in text_lower for sound in ["*typing*", "*keystroke*", "*click*"]):
            deceptive_flags.append("synthetic_typing")

    turn: dict[str, Any] = {
        "speech_text": speech_text,
        "identity_assertion_text": identity_assertion_text,
        "deceptive_artifact_flags": deceptive_flags,
        "phi_accessed": [],
        "disclosure_timestamp": disclosure_timestamp,
    }
    if escalation_outcome is not None:
        turn["escalation_outcome"] = escalation_outcome
        turn["escalation_path_available"] = escalation_outcome != "deflected"
    return turn


def fabricate_conversation_to_eval_shape(
    conversation_row: dict[str, Any],
    raw_turns: list[dict[str, Any]],
    exclusion_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Map one conversation row + its turns to the eval-loop conversation shape."""
    if exclusion_counts is None:
        exclusion_counts = defaultdict(int)
    expected_violations = [
        rule_id
        for column, rule_id in VIOLATION_COLUMN_TO_RULE_ID.items()
        if _is_truthy(conversation_row.get(column, "0"))
    ]

    # ATR-01: untestable in transcript replay (see module docstring).
    if "ATR-01" in expected_violations:
        expected_violations.remove("ATR-01")
        exclusion_counts["ATR-01 (untestable in replay)"] += 1

    escalation_outcomes = _annotate_escalation_outcomes(raw_turns)

    turns: list[dict[str, Any]] = []
    disclosure_timestamp: str | None = None
    disclosure_turn_index: int | None = None
    disclosure_assertion_text = ""
    for i, raw_turn in enumerate(raw_turns):
        if disclosure_timestamp is None and _is_truthy(
            raw_turn.get("is_identity_disclosure", "0")
        ):
            disclosure_timestamp = raw_turn.get("created_at") or f"turn-{i}"
            disclosure_turn_index = i
            disclosure_assertion_text = raw_turn.get("text", "") or ""
        turn = build_turn(
            raw_turn, disclosure_timestamp, disclosure_assertion_text,
            escalation_outcomes.get(i),
        )
        turns.append(turn)

    # PDX-01: pre-disclosure gate — drop expectation when the transcript
    # discloses at turn 0 (post-disclosure probing is out of PDX-01 scope).
    if "PDX-01" in expected_violations and disclosure_turn_index == 0:
        expected_violations.remove("PDX-01")
        exclusion_counts["PDX-01 (disclosure at turn 0; probe is post-disclosure)"] += 1

    return {
        "conversation_id": conversation_row["id"],
        "conversation_ref": conversation_row.get("conversation_ref"),
        "scenario_type": conversation_row.get("scenario_type"),
        "target_control": conversation_row.get("target_control"),
        "expected_violations": expected_violations,
        "turns": turns,
    }


def convert_csv(conversations_csv_path: str, turns_csv_path: str) -> list[dict[str, Any]]:
    exclusion_counts: dict[str, int] = defaultdict(int)
    turns_by_conversation = load_turns_by_conversation(turns_csv_path)
    conversations: list[dict[str, Any]] = []
    with open(conversations_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw_turns = turns_by_conversation.get(row["id"], [])
            conversations.append(
                fabricate_conversation_to_eval_shape(row, raw_turns, exclusion_counts)
            )
    _print_exclusions(exclusion_counts)
    return conversations


# Backward-compatible alias. The public entry point was ``convert`` in v1.0;
# v1.1 split CSV vs JSONL ingestion into convert_csv / convert_jsonl. Existing
# imports and the CSV path continue to work unchanged via this alias.
convert = convert_csv


def convert_jsonl(jsonl_path: str) -> list[dict[str, Any]]:
    """Convert a Fabricate JSONL export (nested turns, expected_violations dict)."""
    exclusion_counts: dict[str, int] = defaultdict(int)
    conversations: list[dict[str, Any]] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            # Normalize to the row shape fabricate_conversation_to_eval_shape reads.
            row: dict[str, Any] = {
                "id": rec.get("conversation_id") or rec.get("id") or rec["conversation_ref"],
                "conversation_ref": rec.get("conversation_ref"),
                "scenario_type": rec.get("scenario_type"),
                "target_control": rec.get("target_control"),
            }
            expected = rec.get("expected_violations") or {}
            for column, rule_id in VIOLATION_COLUMN_TO_RULE_ID.items():
                row[column] = "1" if expected.get(rule_id) else "0"
            raw_turns = [
                {
                    "turn_index": t.get("turn_index", i),
                    "speaker": t.get("speaker"),
                    "text": t.get("text", ""),
                    "contains_phi": t.get("contains_phi"),
                    "is_identity_disclosure": t.get("is_identity_disclosure"),
                    "is_escalation_request": t.get("is_escalation_request"),
                    "created_at": t.get("created_at"),
                }
                for i, t in enumerate(rec.get("turns", []))
            ]
            raw_turns.sort(key=lambda r: int(r["turn_index"]))
            conversations.append(
                fabricate_conversation_to_eval_shape(row, raw_turns, exclusion_counts)
            )
    _print_exclusions(exclusion_counts)
    return conversations


def _print_exclusions(exclusion_counts: dict[str, int]) -> None:
    for reason, count in sorted(exclusion_counts.items()):
        print(f"note: dropped {count} expectation(s): {reason}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+",
                        help="<conversations.csv> <turns.csv>  OR  <corpus.jsonl>")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    if len(args.inputs) == 1 and args.inputs[0].lower().endswith(".jsonl"):
        conversations = convert_jsonl(args.inputs[0])
    elif len(args.inputs) == 2:
        conversations = convert_csv(args.inputs[0], args.inputs[1])
    else:
        parser.error("expected either one .jsonl file or conversations.csv + turns.csv")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(conversations, f, indent=2)
    print(f"Wrote {len(conversations)} conversations to {args.out}")


if __name__ == "__main__":
    main()
