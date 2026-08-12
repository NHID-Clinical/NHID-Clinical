#!/usr/bin/env python3
"""
NHID-Clinical Corpus Evaluation Harness

Loads Tonic synthetic evaluation corpus, reconstructs conversations,
feeds through policy engine, and calculates control-specific metrics.

PHASES:
  3: Corpus mapping (classify scenarios)
  4: Build evaluation harness
  6: Calculate control metrics
"""

import csv
import sys
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.nhid_policy_engine_v1 import evaluate_all, PolicyAction, PolicyDecision


class CorpusEvaluator:
    """Comprehensive corpus evaluation against policy engine."""

    def __init__(self, corpus_path):
        self.corpus_path = corpus_path
        self.sessions = defaultdict(lambda: {"turns": [], "metadata": {}})
        self.results = []
        self.metrics = defaultdict(lambda: {
            "total": 0, "correct": 0, "pass": 0, "violation": 0,
            "tp": 0, "tn": 0, "fp": 0, "fn": 0
        })

    def load_corpus(self):
        """Load flat corpus CSV and group by session."""
        with open(self.corpus_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                session_id = row['session_id']
                turn_num = int(row['turn_number'])

                # Store turn
                self.sessions[session_id]["turns"].append({
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

                # Store metadata (same for all turns in session)
                if not self.sessions[session_id]["metadata"]:
                    self.sessions[session_id]["metadata"] = {
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

        # Sort turns by turn_number within each session
        for session in self.sessions.values():
            session["turns"].sort(key=lambda t: t["turn_number"])

        return len(self.sessions)

    def reconstruct_event(self, turn):
        """Convert turn to policy engine event dict."""
        return {
            "speaker": turn["speaker"],
            "utterance": turn["utterance"],
            "event_type": turn["event_type"],
            "contains_phi": turn["contains_phi"],
            "contains_pii": turn["contains_pii"],
            "disclosure_status": turn["disclosure_status"],
            "escalation_requested": turn["escalation_requested"],
            "escalation_outcome": turn["escalation_outcome"],
            "deception_pattern": turn["deception_pattern"],
        }

    def reconstruct_session(self, turn_data, processed_turns):
        """Build session state for policy engine."""
        session = {
            "session_id": "eval_session",
            "turns_so_far": [
                self.reconstruct_event(t)
                for t in processed_turns
            ],
            "current_turn_index": len(processed_turns),
            "disclosure_timestamp": None,
            "escalation_request_turn": None,
            "phi_exchanged_before_disclosure": False,
        }

        # Track disclosure
        for i, t in enumerate(processed_turns):
            if t["event_type"] == "IDENTITY_DISCLOSURE" and t["disclosure_status"] == "DISCLOSED":
                session["disclosure_timestamp"] = i

        # Track escalation request
        for i, t in enumerate(processed_turns):
            if t["escalation_requested"]:
                session["escalation_request_turn"] = i
                break

        # Track PHI before disclosure
        if session["disclosure_timestamp"] is None:
            for t in processed_turns:
                if t["contains_phi"]:
                    session["phi_exchanged_before_disclosure"] = True
                    break

        return session

    def evaluate_session(self, session_id):
        """Evaluate a single session against policy engine."""
        session_data = self.sessions[session_id]
        metadata = session_data["metadata"]
        turns = session_data["turns"]

        # Track violations seen during evaluation
        violations_detected = {
            "idg_01": False,
            "pdx_01": False,
            "dbc_01": False,
            "eit_01": False,
        }

        # Feed each turn through engine
        processed_turns = []
        final_decision = None

        for turn in turns:
            processed_turns.append(turn)
            reconstructed_session = self.reconstruct_session(turn, processed_turns[:len(processed_turns)])
            event = self.reconstruct_event(turn)

            try:
                decision = evaluate_all(reconstructed_session, event)

                # Track violations by rule_id
                if decision.violations:
                    for v in decision.violations:
                        rule_id = v.rule_id if hasattr(v, 'rule_id') else str(v)
                        if 'IDG-01' in rule_id:
                            violations_detected["idg_01"] = True
                        if 'PDX-01' in rule_id:
                            violations_detected["pdx_01"] = True
                        if 'DBC-01' in rule_id:
                            violations_detected["dbc_01"] = True
                        if 'EIT-01' in rule_id:
                            violations_detected["eit_01"] = True

                final_decision = decision

            except Exception as e:
                import traceback
                print(f"ERROR in {session_id} turn {len(processed_turns)}: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return None

        return {
            "session_id": session_id,
            "scenario_id": metadata["scenario_id"],
            "primary_control": metadata["primary_control_focus"],
            "cross_controls": metadata["cross_controls"],
            "expected_idg_01": metadata["expected_idg_01"],
            "expected_pdx_01": metadata["expected_pdx_01"],
            "expected_dbc_01": metadata["expected_dbc_01"],
            "expected_eit_01": metadata["expected_eit_01"],
            "expected_decision": metadata["expected_final_decision"],
            "predicted_idg_01": "1" if violations_detected["idg_01"] else "0",
            "predicted_pdx_01": "1" if violations_detected["pdx_01"] else "0",
            "predicted_dbc_01": "1" if violations_detected["dbc_01"] else "0",
            "predicted_eit_01": "1" if violations_detected["eit_01"] else "0",
            "predicted_action": str(final_decision.action) if final_decision else "UNKNOWN",
            "expected_reason": metadata["expected_reason"],
        }

    def evaluate_all_sessions(self):
        """Evaluate corpus and calculate metrics."""
        total = len(self.sessions)
        for i, session_id in enumerate(sorted(self.sessions.keys()), 1):
            print(f"[{i}/{total}] Evaluating {session_id}...", file=sys.stderr)
            result = self.evaluate_session(session_id)
            if result:
                self.results.append(result)

        return len(self.results)

    def calculate_metrics(self):
        """Calculate per-control metrics."""
        controls = ["idg_01", "pdx_01", "dbc_01", "eit_01"]
        metrics = {}

        for control in controls:
            expected_key = f"expected_{control}"
            predicted_key = f"predicted_{control}"

            tp = fn = fp = tn = 0
            for result in self.results:
                exp = result[expected_key]
                pred = result[predicted_key]

                # Skip N/A or unknown results
                if exp in ("N/A", ""):
                    continue

                # Convert string violations to binary (VIOLATION -> 1, PASS -> 0)
                exp_binary = "1" if exp == "VIOLATION" else "0"
                pred_binary = pred  # Already 0 or 1

                if exp_binary == "1" and pred_binary == "1":
                    tp += 1
                elif exp_binary == "1" and pred_binary == "0":
                    fn += 1
                elif exp_binary == "0" and pred_binary == "1":
                    fp += 1
                elif exp_binary == "0" and pred_binary == "0":
                    tn += 1

            total = tp + tn + fp + fn
            detection_rate = (tp / (tp + fn)) if (tp + fn) > 0 else 0
            false_positive_rate = (fp / (fp + tn)) if (fp + tn) > 0 else 0
            accuracy = (tp + tn) / total if total > 0 else 0

            metrics[control.upper()] = {
                "total_sessions": total,
                "violations_expected": tp + fn,
                "violations_detected": tp + fp,
                "true_positives": tp,
                "false_negatives": fn,
                "false_positives": fp,
                "true_negatives": tn,
                "detection_rate": f"{detection_rate*100:.1f}%",
                "false_positive_rate": f"{false_positive_rate*100:.1f}%",
                "accuracy": f"{accuracy*100:.1f}%",
            }

        return metrics

    def save_results(self, output_path):
        """Save evaluation results to JSON."""
        metrics = self.calculate_metrics()
        output = {
            "timestamp": datetime.now().isoformat(),
            "corpus_size": len(self.sessions),
            "evaluated_sessions": len(self.results),
            "per_control_metrics": metrics,
            "detailed_results": self.results[:10],  # Sample first 10 for review
        }

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        return output


if __name__ == "__main__":
    corpus_path = "/root/.claude/uploads/44c6fd1e-68a3-5f7e-bc5c-9a33e24f19ef/db86f0f9-nhid_corpus_flat.csv"

    print("=== NHID-Clinical Corpus Evaluation ===")
    print(f"Loading corpus from {corpus_path}...")

    evaluator = CorpusEvaluator(corpus_path)
    loaded = evaluator.load_corpus()
    print(f"Loaded {loaded} sessions")

    print("Evaluating against policy engine...")
    evaluated = evaluator.evaluate_all_sessions()
    print(f"Successfully evaluated {evaluated}/{loaded} sessions")

    print("Calculating metrics...")
    metrics = evaluator.calculate_metrics()

    print("\n=== EVALUATION RESULTS ===")
    for control, stats in sorted(metrics.items()):
        print(f"\n{control}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    # Save results
    output_path = "/home/user/NHID-Clinical/corpus_evaluation_results.json"
    evaluator.save_results(output_path)
    print(f"\nDetailed results saved to {output_path}")
