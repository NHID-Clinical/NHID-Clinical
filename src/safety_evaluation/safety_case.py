"""Evidence-based safety case for deployment assurance.

Structured representation of safety claims, supporting evidence, and logical
arguments showing "why deployment is safe" based on evaluation results.

Format: Claims, Evidence, and Argument (CEA) structure allowing auditors
and stakeholders to trace safety assurance back to test data and metrics.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime


class EvidenceType(str, Enum):
    """Types of evidence supporting safety claims."""
    DETECTION_RATE = "detection_rate"  # Metric: violations detected
    AUDIT_COMPLETENESS = "audit_completeness"  # Metric: decisions logged
    FALSE_POSITIVE_RATE = "false_positive_rate"  # Metric: user friction
    FAILURE_MODE_TESTING = "failure_mode_testing"  # Corpus: adversarial
    POLICY_ENGINE_TESTING = "policy_engine_testing"  # Unit: engine stability
    INTEGRATION_TESTING = "integration_testing"  # E2E: full call flow
    CONFIGURATION_REVIEW = "configuration_review"  # Manual: policy rules
    EXPERT_REVIEW = "expert_review"  # Manual: domain expert assessment


class ClaimSeverity(str, Enum):
    """Severity of claim if violated in production."""
    CRITICAL = "critical"  # Patient safety, privacy breach
    MAJOR = "major"        # Regulatory violation
    MINOR = "minor"        # Degraded UX, detectable issue


@dataclass(frozen=True)
class Evidence:
    """Single piece of evidence supporting a claim."""
    evidence_id: str  # UUID
    evidence_type: EvidenceType
    description: str
    source: str  # "evaluation_corpus_v1.json", "test_safety_metrics.py", etc.
    metric_or_result: str  # e.g., "detection_rate=0.95", "2/20 adversarial cases bypassed"
    confidence: float  # 0-1, how strong is this evidence?
    timestamp: str  # ISO 8601

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Argument:
    """Logical argument linking evidence to claim."""
    argument_id: str  # UUID
    premise_type: str  # "inductive", "deductive", "abductive"
    premises: List[str]  # References to evidence IDs
    conclusion: str  # Specific claim this argument supports
    strength: str  # "strong", "moderate", "weak"
    counterarguments: List[str] = field(default_factory=list)  # Known weaknesses
    mitigation: str = ""  # How we address weaknesses


@dataclass(frozen=True)
class SafetyClaim:
    """Single safety claim with supporting evidence and argument."""
    claim_id: str  # UUID
    rule_id: str  # IDG-01, PDX-01, etc.
    claim_text: str  # E.g., "Policy engine correctly detects IDG-01 violations"
    severity: ClaimSeverity
    is_verified: bool  # True if evidence supports claim
    evidence: List[Evidence] = field(default_factory=list)
    arguments: List[Argument] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class SafetyCase:
    """Complete safety case for deployment."""

    def __init__(
        self,
        case_id: str,
        product_name: str,
        version: str,
        evaluation_date: str,
    ):
        """Initialize safety case.

        Args:
            case_id: Unique identifier for this safety case
            product_name: "NHID-Clinical"
            version: "1.0.0"
            evaluation_date: ISO 8601 date
        """
        self.case_id = case_id
        self.product_name = product_name
        self.version = version
        self.evaluation_date = evaluation_date
        self.created_timestamp = datetime.utcnow().isoformat() + "Z"

        self.claims: List[SafetyClaim] = []
        self.overall_status = "unverified"  # unverified, partially_verified, verified
        self.deployment_recommendation = "unknown"

    def add_claim(self, claim: SafetyClaim) -> None:
        """Add a safety claim to the case."""
        self.claims.append(claim)

    def add_evidence_to_claim(
        self,
        claim_id: str,
        evidence: Evidence,
    ) -> bool:
        """Add evidence to an existing claim."""
        for claim in self.claims:
            if claim.claim_id == claim_id:
                claim.evidence.append(evidence)
                return True
        return False

    def verify_case(self) -> tuple[bool, List[str]]:
        """Verify all claims are supported by evidence.

        Returns:
            Tuple of (all_verified: bool, unverified_claims: List[str])
        """
        unverified = []
        all_verified = True

        for claim in self.claims:
            if not claim.evidence or not claim.arguments:
                unverified.append(f"{claim.rule_id}: {claim.claim_text}")
                all_verified = False
            else:
                claim.is_verified = True

        if all_verified:
            self.overall_status = "verified"
        else:
            self.overall_status = "partially_verified"

        return all_verified, unverified

    def get_deployment_recommendation(self) -> str:
        """Determine deployment readiness based on case verification.

        Returns:
            "READY_TO_DEPLOY" | "CONDITIONAL_DEPLOYMENT" | "DO_NOT_DEPLOY"
        """
        if self.overall_status == "verified":
            self.deployment_recommendation = "READY_TO_DEPLOY"
        elif self.overall_status == "partially_verified":
            self.deployment_recommendation = "CONDITIONAL_DEPLOYMENT"
        else:
            self.deployment_recommendation = "DO_NOT_DEPLOY"

        return self.deployment_recommendation

    def to_dict(self) -> dict:
        """Export safety case as dictionary."""
        return {
            "case_id": self.case_id,
            "product": self.product_name,
            "version": self.version,
            "evaluation_date": self.evaluation_date,
            "created_timestamp": self.created_timestamp,
            "overall_status": self.overall_status,
            "deployment_recommendation": self.deployment_recommendation,
            "claims": [claim.to_dict() for claim in self.claims],
        }

    def to_markdown(self) -> str:
        """Export safety case as markdown report."""
        md = f"""# Safety Case: {self.product_name} v{self.version}

**Evaluation Date:** {self.evaluation_date}
**Case ID:** {self.case_id}
**Overall Status:** {self.overall_status}
**Deployment Recommendation:** {self.deployment_recommendation}

---

## Claims and Evidence

"""
        for claim in self.claims:
            md += f"### Claim: {claim.claim_text}\n"
            md += f"**Rule:** {claim.rule_id}  \n"
            md += f"**Severity:** {claim.severity.value}  \n"
            md += f"**Verified:** {'✓' if claim.is_verified else '✗'}  \n\n"

            if claim.evidence:
                md += "**Supporting Evidence:**\n"
                for ev in claim.evidence:
                    md += f"- ({ev.evidence_type.value}) {ev.description}\n"
                    md += f"  - Source: {ev.source}\n"
                    md += f"  - Result: {ev.metric_or_result}\n"
                    md += f"  - Confidence: {ev.confidence:.0%}\n"
                md += "\n"

            if claim.arguments:
                md += "**Arguments:**\n"
                for arg in claim.arguments:
                    md += f"- {arg.premise_type.upper()}: {arg.conclusion}\n"
                    md += f"  - Strength: {arg.strength}\n"
                    if arg.counterarguments:
                        md += f"  - Counterarguments: {', '.join(arg.counterarguments)}\n"
                md += "\n"

            if claim.assumptions:
                md += "**Assumptions:**\n"
                for assumption in claim.assumptions:
                    md += f"- {assumption}\n"
                md += "\n"

            md += "---\n\n"

        return md


# Tier 0 Safety Case Template (5 core claims, one per rule)
def create_tier_0_safety_case() -> SafetyCase:
    """Create template safety case for Tier 0 pilot."""
    import uuid

    case = SafetyCase(
        case_id=str(uuid.uuid4()),
        product_name="NHID-Clinical",
        version="1.0.0-pilot",
        evaluation_date=datetime.utcnow().strftime("%Y-%m-%d"),
    )

    # Claim 1: IDG-01 Detection
    claim_idg01 = SafetyClaim(
        claim_id=str(uuid.uuid4()),
        rule_id="IDG-01",
        claim_text="Policy engine correctly detects missing AI identity disclosure (D3+)",
        severity=ClaimSeverity.CRITICAL,
        is_verified=False,
        assumptions=[
            "Disclosure level taxonomy (D0-D4) correctly implemented",
            "Policy engine regex patterns match specification",
            "Evaluation corpus covers all D0-D2 scenarios",
        ],
    )
    case.add_claim(claim_idg01)

    # Claim 2: PDX-01 Detection
    claim_pdx01 = SafetyClaim(
        claim_id=str(uuid.uuid4()),
        rule_id="PDX-01",
        claim_text="Policy engine correctly gates PHI access until after D3+ disclosure",
        severity=ClaimSeverity.CRITICAL,
        is_verified=False,
        assumptions=[
            "Timestamp ordering enforced in turn evaluation",
            "PHI field detection regex accurate",
            "Disclosure timing captured correctly",
        ],
    )
    case.add_claim(claim_pdx01)

    # Claim 3: DBC-01 Detection
    claim_dbc01 = SafetyClaim(
        claim_id=str(uuid.uuid4()),
        rule_id="DBC-01",
        claim_text="Policy engine detects deceptive identity claims (false human assertion)",
        severity=ClaimSeverity.CRITICAL,
        is_verified=False,
        assumptions=[
            "Deceptive artifact flags extracted from caller speech",
            "Pattern matching captures common mimicry tactics",
            "Adversarial corpus covers known evasion techniques",
        ],
    )
    case.add_claim(claim_dbc01)

    # Claim 4: EIT-01 Detection
    claim_eit01 = SafetyClaim(
        claim_id=str(uuid.uuid4()),
        rule_id="EIT-01",
        claim_text="Policy engine honors escalation requests and detects escalation denial",
        severity=ClaimSeverity.MAJOR,
        is_verified=False,
        assumptions=[
            "Escalation outcome field populated accurately",
            "Engine returns ESCALATE_HUMAN when escalation_requested=True",
            "Corpus includes escalation denial scenarios",
        ],
    )
    case.add_claim(claim_eit01)

    # Claim 5: ATR-01 Audit Trail
    claim_atr01 = SafetyClaim(
        claim_id=str(uuid.uuid4()),
        rule_id="ATR-01",
        claim_text="Audit trail captures all policy decisions with cryptographic integrity verification",
        severity=ClaimSeverity.CRITICAL,
        is_verified=False,
        assumptions=[
            "AuditTrail initialized and events populated for all turns",
            "Evidence hash computed and verified for all events",
            "Chain verification detects tampering or corruption",
        ],
    )
    case.add_claim(claim_atr01)

    return case
