"""Healthcare AI Safety Evaluation Framework for NHID-Clinical.

Tier 0 Pilot Implementation:
- Failure mode taxonomy (6 categories)
- Safety metrics with detection rate & false positive tracking
- Adversarial corpus for stress testing
- Shadow mode logging (non-blocking, observation-only)
- Evidence-based safety case for deployment assurance
"""

from src.safety_evaluation.failure_modes import (
    FailureMode,
    FailureCategory,
    FalseNegativeFailure,
    FalsePositiveFailure,
    SilentFailure,
    AuditFailure,
    PolicyFailure,
    AdversarialBypassFailure,
)
from src.safety_evaluation.safety_metrics import (
    SafetyMetrics,
    Tier0Thresholds,
    MetricThreshold,
)
from src.safety_evaluation.adversarial_corpus import (
    AdversarialCase,
    AdversarialCaseBuilder,
)
from src.safety_evaluation.safety_scorer import (
    SafetyScore,
    RiskTier,
    SafetyScoreReport,
)
from src.safety_evaluation.safety_logger import (
    ShadowModeLogger,
    SafetyEvent,
)
from src.safety_evaluation.safety_case import (
    SafetyClaim,
    Evidence,
    Argument,
    SafetyCase,
)

__all__ = [
    "FailureMode",
    "FailureCategory",
    "FalseNegativeFailure",
    "FalsePositiveFailure",
    "SilentFailure",
    "AuditFailure",
    "PolicyFailure",
    "AdversarialBypassFailure",
    "SafetyMetrics",
    "Tier0Thresholds",
    "MetricThreshold",
    "AdversarialCase",
    "AdversarialCaseBuilder",
    "SafetyScore",
    "RiskTier",
    "SafetyScoreReport",
    "ShadowModeLogger",
    "SafetyEvent",
    "SafetyClaim",
    "Evidence",
    "Argument",
    "SafetyCase",
]
