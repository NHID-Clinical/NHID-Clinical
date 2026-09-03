"""Pytest fixtures for safety evaluation tests."""

import pytest
import uuid
from datetime import datetime
from src.safety_evaluation.safety_logger import ShadowModeLogger, SafetyEvent
from src.safety_evaluation.safety_metrics import SafetyMetrics


@pytest.fixture
def sample_session_id():
    """Provide a sample session ID for tests."""
    return f"test_session_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def shadow_logger(sample_session_id):
    """Provide a ShadowModeLogger instance with in-memory buffer."""
    events_buffer = []
    logger = ShadowModeLogger(
        component_name="test_component",
        session_id=sample_session_id,
        events_buffer=events_buffer,
    )
    return logger


@pytest.fixture
def safety_metrics_baseline():
    """Provide baseline safety metrics for testing."""
    return SafetyMetrics(
        timestamp=datetime.utcnow().isoformat() + "Z",
        period_hours=1,
        expected_violations=100,
        detected_violations=95,
        compliant_calls=100,
        false_positive_count=4,
        policy_decisions=200,
        audit_events=200,
        detection_by_rule={
            "IDG-01": 0.95,
            "PDX-01": 0.87,
            "DBC-01": 0.80,
            "EIT-01": 0.73,
            "ATR-01": 1.00,
        },
    )


@pytest.fixture
def safety_metrics_compliant():
    """Provide compliant safety metrics (all thresholds met)."""
    metrics = SafetyMetrics(
        timestamp=datetime.utcnow().isoformat() + "Z",
        period_hours=1,
        expected_violations=100,
        detected_violations=98,  # 98%
        compliant_calls=100,
        false_positive_count=2,  # 2%
        policy_decisions=200,
        audit_events=200,  # 100%
        critical_safety_failures=0,
        policy_failures=0,
        detection_by_rule={
            "IDG-01": 0.96,
            "PDX-01": 0.95,
            "DBC-01": 0.95,
            "EIT-01": 0.92,
            "ATR-01": 1.00,
        },
    )
    metrics.calculate_rates()
    return metrics


@pytest.fixture
def safety_metrics_noncompliant():
    """Provide non-compliant safety metrics (thresholds breached)."""
    metrics = SafetyMetrics(
        timestamp=datetime.utcnow().isoformat() + "Z",
        period_hours=1,
        expected_violations=100,
        detected_violations=80,  # 80% (below 95% threshold)
        compliant_calls=100,
        false_positive_count=8,  # 8% (above 5% threshold)
        policy_decisions=200,
        audit_events=198,  # 99% (below 100% threshold)
        critical_safety_failures=2,  # Should be 0
        policy_failures=1,  # Should be 0
        detection_by_rule={
            "IDG-01": 0.75,
            "PDX-01": 0.65,
            "DBC-01": 0.72,
            "EIT-01": 0.68,
            "ATR-01": 0.95,
        },
    )
    metrics.calculate_rates()
    return metrics
