from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class PolicyAction(Enum):
    DISCLOSE = "DISCLOSE"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"
    ROUTE_LLM = "ROUTE_LLM"
    ERROR = "ERROR"


@dataclass
class PolicyDecision:
    action: PolicyAction
    message: str
    gather: bool = True
    next_state: str = ""
    reason_code: str = ""
    confidence: float = 1.0
    metadata: Dict[str, str] = field(default_factory=dict)
    policy_version: str = "nhid_policy_v1"
    state_transition: str = ""


class NHIDPolicyEngine:
    POLICY_VERSION = "nhid_policy_v1"
    DISCLOSURE_MESSAGE = (
        "I am an automated assistant calling on behalf of a healthcare organization."
    )
    ESCALATION_MESSAGE = "Connecting you to a human representative."
    MISSING_INPUT_MESSAGE = "I did not receive a response. Please speak again."
    SAFETY_FALLBACK_MESSAGE = "system error"
    ESCALATION_KEYWORDS = {"human", "agent", "representative", "operator", "supervisor"}

    def evaluate(self, session: dict, user_text: str) -> PolicyDecision:
        normalized = " ".join((user_text or "").split()).lower()
        current_state = session.get("state", "INIT")
        metadata = {
            "normalized_text": normalized,
            "session_state": current_state,
            "disclosed": str(session.get("disclosed", False)),
        }

        if not normalized:
            return PolicyDecision(
                action=PolicyAction.BLOCK,
                message=self.MISSING_INPUT_MESSAGE,
                gather=False,
                next_state="BLOCKED",
                reason_code="MISSING_INPUT",
                confidence=1.0,
                metadata=metadata,
                policy_version=self.POLICY_VERSION,
                state_transition="BLOCKED",
            )

        if current_state == "BLOCKED":
            return PolicyDecision(
                action=PolicyAction.ERROR,
                message=self.SAFETY_FALLBACK_MESSAGE,
                gather=False,
                next_state="BLOCKED",
                reason_code="SESSION_BLOCKED",
                confidence=1.0,
                metadata=metadata,
                policy_version=self.POLICY_VERSION,
                state_transition="BLOCKED",
            )

        if not session.get("disclosed", False):
            return PolicyDecision(
                action=PolicyAction.DISCLOSE,
                message=self.DISCLOSURE_MESSAGE,
                gather=True,
                next_state="DISCLOSURE",
                reason_code="DISCLOSURE_GATE",
                confidence=1.0,
                metadata=metadata,
                policy_version=self.POLICY_VERSION,
                state_transition="DISCLOSURE",
            )

        if any(keyword in normalized for keyword in self.ESCALATION_KEYWORDS):
            return PolicyDecision(
                action=PolicyAction.ESCALATE,
                message=self.ESCALATION_MESSAGE,
                gather=False,
                next_state="ESCALATE",
                reason_code="HUMAN_ESCALATION",
                confidence=1.0,
                metadata=metadata,
                policy_version=self.POLICY_VERSION,
                state_transition="ESCALATE",
            )

        if current_state not in {"DISCLOSURE", "ROUTE", "EXECUTE"}:
            return PolicyDecision(
                action=PolicyAction.ERROR,
                message=self.SAFETY_FALLBACK_MESSAGE,
                gather=False,
                next_state="BLOCKED",
                reason_code="INVALID_SESSION_STATE",
                confidence=1.0,
                metadata=metadata,
                policy_version=self.POLICY_VERSION,
                state_transition="BLOCKED",
            )

        return PolicyDecision(
            action=PolicyAction.ROUTE_LLM,
            message="",
            gather=True,
            next_state="ROUTE",
            reason_code="ROUTING",
            confidence=1.0,
            metadata=metadata,
            policy_version=self.POLICY_VERSION,
            state_transition="ROUTE",
        )
