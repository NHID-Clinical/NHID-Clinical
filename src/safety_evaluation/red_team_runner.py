"""Red team execution framework for adversarial robustness testing.

Runs adversarial corpus against policy engine, captures outcomes,
classifies failures, and generates evidence artifacts.

Shadow mode only - observation without affecting production decisions.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class AttackOutcome(str, Enum):
    """Result of adversarial attack."""
    DETECTED = "detected"  # Attack blocked by policy
    BYPASSED = "bypassed"  # Attack succeeded (false negative)
    ERROR = "error"  # Unexpected system error
    PARTIAL = "partial"  # Partially detected/mitigated


class FailureClassification(str, Enum):
    """Type of failure when attack succeeds."""
    FALSE_NEGATIVE = "false_negative"  # Violation not detected
    INCOMPLETE_DETECTION = "incomplete_detection"  # Some violations missed
    INSUFFICIENT_MITIGATION = "insufficient_mitigation"  # Weak response
    LOGIC_ERROR = "logic_error"  # Wrong decision logic
    ENCODING_ERROR = "encoding_error"  # Text handling issue
    TIMING_ERROR = "timing_error"  # Timestamp logic issue


@dataclass(frozen=True)
class AttackResult:
    """Result of executing single adversarial case."""
    case_id: str
    tactic: str
    target_rules: List[str]
    attack_timestamp: str  # ISO 8601
    payload_sent: Dict[str, Any]
    outcome: AttackOutcome
    expected_violations: List[str]
    detected_violations: List[str]
    policy_action: str  # ESCALATE_HUMAN, DENY_DATA, etc.
    expected_action: str
    classification: Optional[FailureClassification] = None
    severity: str = "major"
    evidence: Dict[str, Any] = field(default_factory=dict)


class RedTeamRunner:
    """Execute adversarial corpus against policy engine."""

    def __init__(self):
        """Initialize red team runner."""
        self.results: List[AttackResult] = []
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None

    def execute_case(
        self,
        case_id: str,
        tactic: str,
        target_rules: List[str],
        payload: Dict[str, Any],
        expected_violations: List[str],
        expected_action: str,
        severity: str,
        policy_engine_callable
    ) -> AttackResult:
        """Execute single adversarial test case.

        Args:
            case_id: Unique case identifier
            tactic: Attack tactic name
            target_rules: Rules being targeted
            payload: Adversarial input payload
            expected_violations: Which violations should be detected
            expected_action: Expected policy action
            severity: Attack severity
            policy_engine_callable: Function to call policy engine (for mocking)

        Returns:
            AttackResult with outcome and classification
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Execute against policy engine (stubbed for testing)
        detected_violations, policy_action = self._execute_against_engine(
            payload,
            policy_engine_callable
        )

        # Determine outcome
        outcome, classification = self._classify_outcome(
            expected_violations,
            detected_violations,
            expected_action,
            policy_action
        )

        # Build evidence
        evidence = self._build_evidence(
            case_id,
            tactic,
            payload,
            expected_violations,
            detected_violations,
            expected_action,
            policy_action
        )

        result = AttackResult(
            case_id=case_id,
            tactic=tactic,
            target_rules=target_rules,
            attack_timestamp=timestamp,
            payload_sent=payload,
            outcome=outcome,
            expected_violations=expected_violations,
            detected_violations=detected_violations,
            policy_action=policy_action,
            expected_action=expected_action,
            classification=classification,
            severity=severity,
            evidence=evidence
        )

        self.results.append(result)
        return result

    def _execute_against_engine(
        self,
        payload: Dict[str, Any],
        policy_engine_callable
    ) -> Tuple[List[str], str]:
        """Execute payload against policy engine.

        Returns:
            (detected_violations, policy_action)
        """
        try:
            if callable(policy_engine_callable):
                violations, action = policy_engine_callable(payload)
                return violations, action
            else:
                # Stub: return defaults for testing
                return [], "LOG_ONLY"
        except Exception as e:
            # Shadow mode: catch and return error state
            return [], "ERROR"

    def _classify_outcome(
        self,
        expected: List[str],
        detected: List[str],
        expected_action: str,
        actual_action: str
    ) -> Tuple[AttackOutcome, Optional[FailureClassification]]:
        """Classify attack outcome as detected, bypassed, or partial.

        Returns:
            (AttackOutcome, FailureClassification or None)
        """
        expected_set = set(expected)
        detected_set = set(detected)

        # Perfect detection
        if expected_set == detected_set and expected_action == actual_action:
            return AttackOutcome.DETECTED, None

        # Complete bypass
        if len(detected_set) == 0 and len(expected_set) > 0:
            return AttackOutcome.BYPASSED, FailureClassification.FALSE_NEGATIVE

        # Partial detection
        if 0 < len(detected_set) < len(expected_set):
            return AttackOutcome.PARTIAL, FailureClassification.INCOMPLETE_DETECTION

        # Detected violations but wrong action
        if expected_set == detected_set and expected_action != actual_action:
            return AttackOutcome.PARTIAL, FailureClassification.INSUFFICIENT_MITIGATION

        # Detected extra violations
        if detected_set > expected_set:
            return AttackOutcome.PARTIAL, FailureClassification.FALSE_NEGATIVE

        return AttackOutcome.ERROR, None

    def _build_evidence(
        self,
        case_id: str,
        tactic: str,
        payload: Dict[str, Any],
        expected_violations: List[str],
        detected_violations: List[str],
        expected_action: str,
        actual_action: str
    ) -> Dict[str, Any]:
        """Build evidence artifact for failed attacks."""
        missing = set(expected_violations) - set(detected_violations)
        extra = set(detected_violations) - set(expected_violations)

        return {
            "case_id": case_id,
            "tactic": tactic,
            "payload_summary": str(payload)[:200],  # Truncate for safety
            "expected_violations": expected_violations,
            "detected_violations": detected_violations,
            "missing_violations": list(missing),
            "extra_violations": list(extra),
            "expected_action": expected_action,
            "actual_action": actual_action,
            "action_mismatch": expected_action != actual_action,
            "bypass_evidence": {
                "complete_bypass": len(detected_violations) == 0,
                "partial_bypass": 0 < len(detected_violations) < len(expected_violations),
                "false_negatives": len(missing),
            }
        }

    def execute_campaign(
        self,
        cases: List[Dict[str, Any]],
        policy_engine_callable,
        campaign_name: str = "red_team_baseline"
    ) -> Dict[str, Any]:
        """Execute full adversarial campaign against all cases.

        Args:
            cases: List of adversarial test cases
            policy_engine_callable: Function to invoke policy engine
            campaign_name: Name for this campaign run

        Returns:
            Campaign summary with metrics
        """
        self.start_time = datetime.utcnow().isoformat() + "Z"
        self.results = []

        for case in cases:
            self.execute_case(
                case_id=case["case_id"],
                tactic=case["tactic"],
                target_rules=case["target_rules"],
                payload=case["payload"],
                expected_violations=case.get("expected_violations", []),
                expected_action=case.get("expected_action", "LOG_ONLY"),
                severity=case.get("severity", "major"),
                policy_engine_callable=policy_engine_callable
            )

        self.end_time = datetime.utcnow().isoformat() + "Z"

        return self.campaign_summary()

    def campaign_summary(self) -> Dict[str, Any]:
        """Generate campaign execution summary with metrics."""
        if not self.results:
            return {"error": "No results to summarize"}

        total_cases = len(self.results)
        detected = sum(1 for r in self.results if r.outcome == AttackOutcome.DETECTED)
        bypassed = sum(1 for r in self.results if r.outcome == AttackOutcome.BYPASSED)
        partial = sum(1 for r in self.results if r.outcome == AttackOutcome.PARTIAL)
        errors = sum(1 for r in self.results if r.outcome == AttackOutcome.ERROR)

        # Calculate ASR (Attack Success Rate)
        attack_success = bypassed + partial  # Partial still counts as bypass
        asr = attack_success / total_cases if total_cases > 0 else 0.0

        # Rule coverage
        rule_coverage = {}
        for result in self.results:
            for rule in result.target_rules:
                if rule not in rule_coverage:
                    rule_coverage[rule] = {"total": 0, "detected": 0}
                rule_coverage[rule]["total"] += 1
                if result.outcome == AttackOutcome.DETECTED:
                    rule_coverage[rule]["detected"] += 1

        # Tactic effectiveness
        tactic_effectiveness = {}
        for result in self.results:
            if result.tactic not in tactic_effectiveness:
                tactic_effectiveness[result.tactic] = {"total": 0, "bypassed": 0}
            tactic_effectiveness[result.tactic]["total"] += 1
            if result.outcome in (AttackOutcome.BYPASSED, AttackOutcome.PARTIAL):
                tactic_effectiveness[result.tactic]["bypassed"] += 1

        # Failure classification
        failures_by_type = {}
        for result in self.results:
            if result.classification:
                class_name = result.classification.value
                failures_by_type[class_name] = failures_by_type.get(class_name, 0) + 1

        return {
            "campaign_name": "red_team_baseline",
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_cases": total_cases,
            "outcomes": {
                "detected": detected,
                "bypassed": bypassed,
                "partial": partial,
                "errors": errors
            },
            "metrics": {
                "attack_success_rate": round(asr, 3),
                "control_robustness_score": round(1 - asr, 3),
                "detection_rate": round(detected / total_cases, 3) if total_cases > 0 else 0,
                "bypass_rate": round(attack_success / total_cases, 3) if total_cases > 0 else 0
            },
            "rule_coverage": {
                rule: {
                    "cases_tested": data["total"],
                    "cases_detected": data["detected"],
                    "detection_rate": round(data["detected"] / data["total"], 3) if data["total"] > 0 else 0
                }
                for rule, data in rule_coverage.items()
            },
            "tactic_effectiveness": {
                tactic: {
                    "cases_tested": data["total"],
                    "cases_bypassed": data["bypassed"],
                    "bypass_rate": round(data["bypassed"] / data["total"], 3) if data["total"] > 0 else 0
                }
                for tactic, data in tactic_effectiveness.items()
            },
            "failures_by_type": failures_by_type,
            "high_severity_bypasses": [
                r.case_id for r in self.results
                if r.outcome in (AttackOutcome.BYPASSED, AttackOutcome.PARTIAL)
                and r.severity == "critical"
            ]
        }

    def export_results_json(self) -> str:
        """Export campaign results as JSON."""
        return json.dumps({
            "campaign_summary": self.campaign_summary(),
            "detailed_results": [
                {
                    "case_id": r.case_id,
                    "outcome": r.outcome.value,
                    "classification": r.classification.value if r.classification else None,
                    "expected_violations": r.expected_violations,
                    "detected_violations": r.detected_violations,
                    "severity": r.severity,
                    "evidence": r.evidence
                }
                for r in self.results
            ]
        }, indent=2)

    def export_results_markdown(self) -> str:
        """Export campaign results as markdown report."""
        summary = self.campaign_summary()

        md = "# Red Team Campaign Results\n\n"
        md += f"**Campaign:** {summary['campaign_name']}\n"
        md += f"**Duration:** {summary['start_time']} to {summary['end_time']}\n"
        md += f"**Total Cases:** {summary['total_cases']}\n\n"

        md += "## Outcomes\n"
        outcomes = summary["outcomes"]
        md += f"- **Detected:** {outcomes['detected']} ({round(outcomes['detected']/summary['total_cases']*100, 1)}%)\n"
        md += f"- **Bypassed:** {outcomes['bypassed']} ({round(outcomes['bypassed']/summary['total_cases']*100, 1)}%)\n"
        md += f"- **Partial:** {outcomes['partial']} ({round(outcomes['partial']/summary['total_cases']*100, 1)}%)\n"
        md += f"- **Errors:** {outcomes['errors']} ({round(outcomes['errors']/summary['total_cases']*100, 1)}%)\n\n"

        md += "## Key Metrics\n"
        metrics = summary["metrics"]
        md += f"- **Attack Success Rate (ASR):** {metrics['attack_success_rate']*100:.1f}%\n"
        md += f"- **Control Robustness Score:** {metrics['control_robustness_score']*100:.1f}%\n"
        md += f"- **Detection Rate:** {metrics['detection_rate']*100:.1f}%\n"
        md += f"- **Bypass Rate:** {metrics['bypass_rate']*100:.1f}%\n\n"

        md += "## Rule Coverage\n"
        for rule, data in summary["rule_coverage"].items():
            rate = data["detection_rate"] * 100
            md += f"- **{rule}:** {data['cases_detected']}/{data['cases_tested']} ({rate:.1f}%)\n"

        md += "\n## Tactic Effectiveness\n"
        for tactic, data in summary["tactic_effectiveness"].items():
            rate = data["bypass_rate"] * 100
            md += f"- **{tactic}:** {data['cases_bypassed']} bypasses out of {data['cases_tested']} ({rate:.1f}%)\n"

        if summary.get("high_severity_bypasses"):
            md += "\n## Critical Findings\n"
            md += f"**High-severity attacks bypassed:** {len(summary['high_severity_bypasses'])}\n"
            for case_id in summary['high_severity_bypasses']:
                md += f"- {case_id}\n"

        return md
