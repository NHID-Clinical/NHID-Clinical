#!/usr/bin/env python3
"""
Tonic Corpus → NHID-Clinical Policy Engine Schema Adapter

Transforms Tonic's turn-level conversation events into the healthcare governance
context and state-machine inputs that the NHID-Clinical policy engine expects.

The adapter preserves all source data fidelity while making deterministic inferences
for fields that cannot be directly mapped.
"""

import csv
from collections import defaultdict
from datetime import datetime
from typing import Optional, Dict, Any, List
import json

from src.nhid_policy_engine_v1 import POLICY_ENGINE_VERSION


class TonicschemAdapter:
    """Transforms Tonic corpus turns into engine-compatible events."""

    def __init__(self):
        self.inferences_log = []
        self.errors = []

    def load_corpus(self, csv_path: str) -> Dict[str, Dict]:
        """Load Tonic flat corpus and group by session."""
        sessions = defaultdict(lambda: {"turns": [], "metadata": {}})

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                session_id = row['session_id']
                turn_num = int(row['turn_number'])

                # Store turn
                sessions[session_id]["turns"].append({
                    "turn_number": turn_num,
                    "timestamp": row['timestamp'],
                    "speaker": row['speaker'],
                    "utterance": row['utterance'],
                    "event_type": row['event_type'],
                    "contains_phi": row['contains_phi'] == '1',
                    "contains_pii": row['contains_pii'] == '1',
                    "disclosure_status": row['disclosure_status'],
                    "escalation_requested": row['escalation_requested'] == '1',
                    "escalation_outcome": row['escalation_outcome'],
                    "deception_pattern": row['deception_pattern'],
                })

                # Store metadata
                if not sessions[session_id]["metadata"]:
                    sessions[session_id]["metadata"] = {
                        "scenario_id": row['scenario_id'],
                        "primary_control_focus": row['primary_control_focus'],
                        "scenario_subtype": row['scenario_subtype'],
                        "cross_controls": row['cross_controls'],
                        "control_count": int(row['control_count']),
                        "num_turns": int(row['num_turns']),
                        "expected_idg_01": row['expected_idg_01'],
                        "expected_pdx_01": row['expected_pdx_01'],
                        "expected_dbc_01": row['expected_dbc_01'],
                        "expected_eit_01": row['expected_eit_01'],
                        "expected_atr_01": row['expected_atr_01'],
                        "expected_final_decision": row['expected_final_decision'],
                        "expected_reason": row['expected_reason'],
                    }

        # Sort turns within each session
        for session in sessions.values():
            session["turns"].sort(key=lambda t: t["turn_number"])

        return sessions

    def infer_disclosure_timestamp(self, turns: List[Dict], processed_turn_idx: int) -> Optional[int]:
        """
        Infer the turn index when valid identity disclosure occurred.

        Inference rule:
        - Search backwards from current turn
        - Find first IDENTITY_DISCLOSURE event with disclosure_status == DISCLOSED
        - Return that turn's index
        - If no valid disclosure found, return None
        """
        for i in range(processed_turn_idx, -1, -1):
            if (turns[i]["event_type"] == "IDENTITY_DISCLOSURE" and
                turns[i]["disclosure_status"] == "DISCLOSED"):
                return i
        return None

    def infer_phi_fields_from_utterance(self, utterance: str) -> List[str]:
        """
        Infer which PHI fields are mentioned in utterance text.

        Inference rule: Search utterance for patterns matching known PHI field names.
        """
        phi_fields = []
        utterance_lower = utterance.lower()

        patterns = {
            "member_id": ["member id", "member number", "mbr-"],
            "date_of_birth": ["date of birth", "dob", "born"],
            "claim_number": ["claim number", "claim #", "clm-"],
            "npi": ["npi", "provider number"],
            "diagnosis_code": ["diagnosis", "icd", "dx code"],
            "procedure_code": ["procedure code", "cpt", "proc"],
        }

        for field, keywords in patterns.items():
            if any(kw in utterance_lower for kw in keywords):
                phi_fields.append(field)

        return phi_fields

    def infer_deceptive_artifacts(self, deception_pattern: str) -> List[str]:
        """
        Map Tonic deception_pattern enum to engine's deceptive_artifact_flags.

        Inference rule: Each deception pattern maps to a specific artifact classification.
        """
        mapping = {
            "NONE": [],
            "EXPLICIT_CONCEAL_REQUEST": ["explicit_conceal_ai"],
            "EXPLICIT_IMPERSONATION": ["explicit_impersonate_human"],
            "EXPLICIT_MISREPRESENTATION": ["explicit_misrepresent"],
            "IMPLICIT_EVASIVE": ["implicit_evasive_identity"],
            "AMBIGUOUS_IDENTITY_LANGUAGE": ["ambiguous_identity_language"],
            "HUMAN_PASSING_ATTEMPT": ["human_passing_attempt"],
        }
        return mapping.get(deception_pattern, [])

    def build_governance_context(
        self,
        session_id: str,
        turns: List[Dict],
        turn_idx: int,
    ) -> Dict[str, Any]:
        """
        Build healthcare_governance context for engine evaluation.

        This is the PRIMARY INFERENCE POINT where Tonic's simplified data
        becomes the engine's rich contextual input.
        """
        current_turn = turns[turn_idx]
        processed_turns = turns[:turn_idx+1]

        # Infer disclosure timestamp
        disclosure_timestamp = self.infer_disclosure_timestamp(turns, turn_idx)
        if disclosure_timestamp is not None:
            self.inferences_log.append({
                "session": session_id,
                "turn": turn_idx,
                "inference": "disclosure_timestamp",
                "value": disclosure_timestamp,
                "rule": "searched backwards for IDENTITY_DISCLOSURE + DISCLOSED",
            })

        # Infer PHI fields if PHI is indicated
        phi_fields = []
        if current_turn["contains_phi"]:
            phi_fields = self.infer_phi_fields_from_utterance(current_turn["utterance"])
            if phi_fields:
                self.inferences_log.append({
                    "session": session_id,
                    "turn": turn_idx,
                    "inference": "phi_accessed",
                    "value": phi_fields,
                    "rule": "matched utterance patterns against known PHI field names",
                })
            else:
                self.inferences_log.append({
                    "session": session_id,
                    "turn": turn_idx,
                    "inference": "phi_accessed",
                    "value": ["unknown_phi"],
                    "rule": "contains_phi=true but no specific fields matched (conservative: mark unknown)",
                })
                phi_fields = ["unknown_phi"]

        # Infer deceptive artifacts
        deceptive_artifacts = self.infer_deceptive_artifacts(current_turn["deception_pattern"])
        if deceptive_artifacts:
            self.inferences_log.append({
                "session": session_id,
                "turn": turn_idx,
                "inference": "deceptive_artifact_flags",
                "value": deceptive_artifacts,
                "rule": f"mapped deception_pattern={current_turn['deception_pattern']}",
            })

        return {
            "session_id": session_id,
            "disclosure_timestamp": disclosure_timestamp,
            "phi_accessed": phi_fields,
            "deceptive_artifact_flags": deceptive_artifacts,
            # IDG-01 pass condition is "disclosure_timestamp is set AND
            # identity_assertion_text is non-empty", so the assertion text has to
            # persist for as long as the timestamp does. Emitting it only on the
            # disclosure turn made IDG-01 re-fire on every later turn.
            "identity_assertion_text": (
                turns[disclosure_timestamp]["utterance"]
                if disclosure_timestamp is not None
                else ""
            ),
        }

    def infer_escalation_path_available(self, turns: List[Dict]) -> bool:
        """
        Determine whether the session's escalation requests were honored.

        The corpus encodes an EIT-01 violation as an *absence*: a turn with
        escalation_requested=1 and no later turn carrying
        escalation_outcome="TRANSFERRED_TO_HUMAN". There is no "DEFLECTED"
        value anywhere in the data, so the signal has to be derived.

        Returns True when there is nothing to honor, or when a request was
        followed by a transfer. Returns False when a request was never honored.
        """
        for i, turn in enumerate(turns):
            if not turn.get("escalation_requested"):
                continue
            honored = any(
                t.get("escalation_outcome") == "TRANSFERRED_TO_HUMAN"
                for t in turns[i:]
            )
            if not honored:
                return False
        return True

    def build_session(self, turns: List[Dict], turn_idx: int) -> Dict[str, Any]:
        """
        Build the session dict that accompanies an event into evaluate_all().

        Previously the evaluator passed {}, so the engine never received
        escalation_path_available and EIT-01 could not fire.
        """
        return {
            "turn_count": turn_idx,
            "escalation_path_available": self.infer_escalation_path_available(turns),
            "counterparty_type": "human_operator",
        }

    def build_audit_context(self, session_id: str, turn_idx: int) -> Dict[str, Any]:
        """
        Build audit context for ATR-01 evaluation.

        Preserves turn-level audit tracking information.
        """
        return {
            "event_id": f"evt-{session_id}-{turn_idx}",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "request_id": f"req-{session_id}-{turn_idx}",
            "actor_id": "voice_agent",  # Constant in voice workflow
            # ATR-01 requires event_type; its absence was the last per-turn
            # audit violation left after execution_context was supplied.
            "event_type": "POLICY",
            "state_before": "CONVERSATION",
            "state_after": "CONVERSATION",
            # ATR-01 requires one of "live" | "replay" | "test"; False is not a
            # valid value and was counted as a missing-field violation.
            "replay_mode": "replay",
            "external_calls_cached": False,
            # ATR-01 requires execution_context and its three version fields.
            # Omitting the block raised 4 violations on every single turn.
            "execution_context": {
                "pipeline_version": "1.0.0",
                "policy_engine_version": POLICY_ENGINE_VERSION,
                "nhid_schema_version": "1.0",
            },
        }

    def adapt_turn(
        self,
        session_id: str,
        turns: List[Dict],
        turn_idx: int,
    ) -> Dict[str, Any]:
        """
        Convert a single Tonic turn into engine input format.

        Returns a dict suitable for passing to policy engine's evaluate_all().
        """
        current_turn = turns[turn_idx]

        # Build governance context (PRIMARY INFERENCE)
        governance = self.build_governance_context(session_id, turns, turn_idx)

        # Build audit context
        audit = self.build_audit_context(session_id, turn_idx)

        # Direct mappings
        return {
            # Session context
            "session_id": session_id,
            "turns_so_far": [
                {
                    "speaker": t["speaker"],
                    "utterance": t["utterance"],
                    "event_type": t["event_type"],
                    "contains_phi": t["contains_phi"],
                    "contains_pii": t["contains_pii"],
                }
                for t in turns[:turn_idx]  # Prior turns only
            ],
            "current_turn_index": turn_idx,

            # Governance context (INFERRED)
            "healthcare_governance": governance,

            # Input payload
            "input_payload": {
                "speech_text": current_turn["utterance"],
            },

            # Audit context
            **audit,

            # State machine
            "state_before": "CONVERSATION",

            # Metadata (for tracking, not used by engine)
            "_source": {
                "tonic_scenario_id": None,  # Filled in by caller if needed
                "tonic_turn_number": current_turn["turn_number"],
                "tonic_event_type": current_turn["event_type"],
                "tonic_speaker": current_turn["speaker"],
                "tonic_timestamp": current_turn["timestamp"],
                "escalation_requested": current_turn["escalation_requested"],
                "escalation_outcome": current_turn["escalation_outcome"],
            }
        }

    def adapt_session(
        self,
        session_id: str,
        session_data: Dict,
    ) -> List[Dict]:
        """
        Convert all turns in a session to engine input format.

        Returns list of adapted events, one per turn, ready for engine evaluation.
        """
        turns = session_data["turns"]
        metadata = session_data["metadata"]

        adapted = []
        for turn_idx in range(len(turns)):
            try:
                adapted_event = self.adapt_turn(session_id, turns, turn_idx)
                # Attach scenario metadata for reference
                adapted_event["_scenario_id"] = metadata["scenario_id"]
                adapted_event["_expected_controls"] = {
                    "idg_01": metadata["expected_idg_01"],
                    "pdx_01": metadata["expected_pdx_01"],
                    "dbc_01": metadata["expected_dbc_01"],
                    "eit_01": metadata["expected_eit_01"],
                }
                adapted.append(adapted_event)
            except Exception as e:
                self.errors.append({
                    "session": session_id,
                    "turn": turn_idx,
                    "error": str(e),
                })

        return adapted

    def save_inference_report(self, output_path: str):
        """Save detailed inference report for auditing."""
        report = {
            "total_inferences": len(self.inferences_log),
            "total_errors": len(self.errors),
            "inferences_by_type": defaultdict(list),
            "errors": self.errors,
        }

        for inf in self.inferences_log:
            inf_type = inf["inference"]
            report["inferences_by_type"][inf_type].append(inf)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 tonic_schema_adapter.py <corpus.csv> [output_dir]")
        sys.exit(1)

    corpus_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    adapter = TonicschemAdapter()
    sessions = adapter.load_corpus(corpus_path)

    print(f"Loaded {len(sessions)} sessions")
    print(f"Adapting to engine format...")

    adapted_sessions = {}
    for session_id, session_data in sessions.items():
        adapted_sessions[session_id] = adapter.adapt_session(session_id, session_data)

    print(f"Adapted {len(adapted_sessions)} sessions")
    print(f"Total inferences: {len(adapter.inferences_log)}")
    print(f"Total errors: {len(adapter.errors)}")

    # Save inference report
    adapter.save_inference_report(f"{output_dir}/adapter_inferences.json")
    print(f"Saved inference report to {output_dir}/adapter_inferences.json")

    # Save adapted data
    adapted_path = f"{output_dir}/tonic_adapted.json"
    with open(adapted_path, 'w') as f:
        # Save session metadata and adapted turns (sample for brevity)
        summary = {
            "total_sessions": len(adapted_sessions),
            "total_adapted_turns": sum(len(v) for v in adapted_sessions.values()),
            "sample_sessions": {
                sess_id: {
                    "turn_count": len(turns),
                    "first_turn": turns[0] if turns else None,
                }
                for sess_id, turns in list(adapted_sessions.items())[:5]
            }
        }
        json.dump(summary, f, indent=2, default=str)

    print(f"Saved adapted data summary to {adapted_path}")
