"""Healthcare AI Safety Evaluation Framework for NHID-Clinical.

Phase 1 (Complete): Failure modes, metrics, scoring, logging, safety case
Phase 2 (Complete): Adversarial corpus, attack generators, red team runner, robustness metrics

Components:
- Failure mode taxonomy (6 categories)
- Safety metrics with detection rate & false positive tracking
- Adversarial corpus (52 cases) for robustness evaluation
- Attack generator framework for scenario mutations
- Red team execution runner with evidence capture
- Robustness metrics (ASR, control score, coverage)
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
    AdversarialTactic,
    get_adversarial_cases_by_tactic,
    get_adversarial_cases_by_rule,
)
from src.safety_evaluation.attack_generators import (
    AttackGenerator,
    MutationStrategy,
    ScenarioMutation,
)
from src.safety_evaluation.red_team_runner import (
    RedTeamRunner,
    AttackResult,
    AttackOutcome,
    FailureClassification,
)
from src.safety_evaluation.adversarial_metrics import (
    MetricsCalculator,
    AdversarialMetrics,
    SeverityLevel,
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
    # Phase 1: Failure Modes
    "FailureMode",
    "FailureCategory",
    "FalseNegativeFailure",
    "FalsePositiveFailure",
    "SilentFailure",
    "AuditFailure",
    "PolicyFailure",
    "AdversarialBypassFailure",
    # Phase 1: Metrics
    "SafetyMetrics",
    "Tier0Thresholds",
    "MetricThreshold",
    # Phase 1: Scoring
    "SafetyScore",
    "RiskTier",
    "SafetyScoreReport",
    # Phase 1: Logging
    "ShadowModeLogger",
    "SafetyEvent",
    # Phase 1: Safety Case
    "SafetyClaim",
    "Evidence",
    "Argument",
    "SafetyCase",
    # Phase 2: Adversarial Corpus
    "AdversarialCase",
    "AdversarialCaseBuilder",
    "AdversarialTactic",
    "get_adversarial_cases_by_tactic",
    "get_adversarial_cases_by_rule",
    # Phase 2: Attack Generators
    "AttackGenerator",
    "MutationStrategy",
    "ScenarioMutation",
    # Phase 2: Red Team Runner
    "RedTeamRunner",
    "AttackResult",
    "AttackOutcome",
    "FailureClassification",
    # Phase 2: Robustness Metrics
    "MetricsCalculator",
    "AdversarialMetrics",
    "SeverityLevel",
]
