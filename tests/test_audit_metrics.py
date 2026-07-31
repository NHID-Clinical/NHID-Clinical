"""Tests for monitoring and observability."""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, MagicMock
from src.audit_metrics import (
    MetricsCollector,
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    StructuredLogger,
    format_metrics_for_prometheus,
    format_health_check_for_json,
    get_metrics_collector,
)
from src.audit_store import AuditStore


class TestMetricsCollector:
    """Test metrics collection."""

    def test_record_event_written(self):
        """Recording events should increment counter."""
        collector = MetricsCollector()
        assert collector.events_written == 0

        collector.record_event_written()
        assert collector.events_written == 1

        collector.record_event_written()
        assert collector.events_written == 2

    def test_record_verification_failure(self):
        """Recording verification failures should increment counter."""
        collector = MetricsCollector()
        assert collector.verification_failures == 0

        collector.record_verification_failure("Test error")
        assert collector.verification_failures == 1

    def test_record_store_latency(self):
        """Recording latencies should track measurements."""
        collector = MetricsCollector()
        assert len(collector.store_latencies) == 0

        collector.record_store_latency(10.5)
        collector.record_store_latency(20.3)
        assert len(collector.store_latencies) == 2

    def test_average_latency(self):
        """Average latency should compute correctly."""
        collector = MetricsCollector()
        collector.record_store_latency(10.0)
        collector.record_store_latency(20.0)
        collector.record_store_latency(30.0)

        assert collector.get_average_latency_ms() == 20.0

    def test_average_latency_empty(self):
        """Average latency should be 0 with no measurements."""
        collector = MetricsCollector()
        assert collector.get_average_latency_ms() == 0.0

    def test_latency_window_keeps_last_100(self):
        """Latency measurements should keep only last 100."""
        collector = MetricsCollector()

        # Record 150 measurements
        for i in range(150):
            collector.record_store_latency(float(i))

        # Should have only last 100
        assert len(collector.store_latencies) == 100
        # Should be measurements 50-149
        assert collector.store_latencies[0] == 50.0
        assert collector.store_latencies[-1] == 149.0

    def test_record_policy_violation(self):
        """Recording violations should track by rule."""
        collector = MetricsCollector()

        collector.record_policy_violation("IDG-01")
        collector.record_policy_violation("IDG-01")
        collector.record_policy_violation("PDX-01")

        assert collector.policy_violations_by_rule["IDG-01"] == 2
        assert collector.policy_violations_by_rule["PDX-01"] == 1

    def test_get_metrics(self):
        """Getting metrics should return snapshot."""
        collector = MetricsCollector()
        collector.record_event_written()
        collector.record_event_written()
        collector.record_verification_failure("error")
        collector.record_store_latency(15.0)
        collector.record_policy_violation("IDG-01")

        metrics = collector.get_metrics()
        assert metrics.events_written == 2
        assert metrics.verification_failures == 1
        assert metrics.average_store_latency_ms == 15.0
        assert metrics.policy_violations_by_rule["IDG-01"] == 1
        assert metrics.timestamp is not None

    def test_reset_metrics(self):
        """Resetting should clear all metrics."""
        collector = MetricsCollector()
        collector.record_event_written()
        collector.record_verification_failure("error")
        collector.record_store_latency(10.0)
        collector.record_policy_violation("IDG-01")

        collector.reset()

        assert collector.events_written == 0
        assert collector.verification_failures == 0
        assert len(collector.store_latencies) == 0
        assert len(collector.policy_violations_by_rule) == 0


class TestHealthChecker:
    """Test health check functionality."""

    @pytest.fixture
    def mock_audit_store(self):
        """Create mock audit store."""
        store = Mock(spec=AuditStore)
        store.secret_key = os.urandom(32)
        return store

    def test_health_check_healthy(self, mock_audit_store):
        """Healthy status when store connected and key loaded."""
        mock_audit_store.read_event.return_value = None

        checker = HealthChecker(mock_audit_store)
        result = checker.check("development")

        assert result.status == HealthStatus.HEALTHY
        assert result.audit_store == "connected"
        assert result.secret_key_loaded is True
        assert result.deployment_mode == "development"

    def test_health_check_store_disconnected(self, mock_audit_store):
        """Degraded status when store disconnected."""
        mock_audit_store.read_event.side_effect = Exception("Connection failed")

        checker = HealthChecker(mock_audit_store)
        result = checker.check("production")

        assert result.status == HealthStatus.DEGRADED
        assert result.audit_store == "disconnected"
        assert result.secret_key_loaded is True
        assert result.deployment_mode == "production"

    def test_health_check_no_secret_key(self, mock_audit_store):
        """Degraded status when secret key missing."""
        mock_audit_store.secret_key = None
        mock_audit_store.read_event.return_value = None

        checker = HealthChecker(mock_audit_store)
        result = checker.check("development")

        assert result.status == HealthStatus.DEGRADED
        assert result.secret_key_loaded is False

    def test_health_check_unhealthy(self, mock_audit_store):
        """Unhealthy status when both store and key fail."""
        mock_audit_store.secret_key = None
        mock_audit_store.read_event.side_effect = Exception("Connection failed")

        checker = HealthChecker(mock_audit_store)
        result = checker.check("staging")

        assert result.status == HealthStatus.UNHEALTHY
        assert result.audit_store == "disconnected"
        assert result.secret_key_loaded is False

    def test_health_check_latency_recorded(self, mock_audit_store):
        """Health check should record latency."""
        mock_audit_store.read_event.return_value = None

        checker = HealthChecker(mock_audit_store)
        result = checker.check("production")

        assert result.audit_store_latency_ms > 0.0

    def test_health_check_exception_handling(self, mock_audit_store):
        """Uncaught exceptions should return unhealthy."""
        mock_audit_store.secret_key = Mock()  # Invalid secret key
        checker = HealthChecker(mock_audit_store)

        result = checker.check("development")
        assert result.status == HealthStatus.UNHEALTHY


class TestMetricsFormatting:
    """Test metrics output formatting."""

    def test_prometheus_format_basic(self):
        """Prometheus format should include all metrics."""
        collector = MetricsCollector()
        collector.record_event_written()
        collector.record_event_written()
        collector.record_verification_failure("error")
        collector.record_store_latency(15.0)
        collector.record_policy_violation("IDG-01")
        collector.record_policy_violation("IDG-01")
        collector.record_policy_violation("PDX-01")

        metrics = collector.get_metrics()
        prometheus_output = format_metrics_for_prometheus(metrics)

        # Should contain metric names
        assert "audit_events_total" in prometheus_output
        assert "audit_verification_failures" in prometheus_output
        assert "audit_store_latency_ms" in prometheus_output
        assert "policy_violations_total" in prometheus_output
        assert "configuration_errors" in prometheus_output

        # Should contain values
        assert "2" in prometheus_output  # events_written
        assert "1" in prometheus_output  # verification_failures
        assert "15" in prometheus_output  # latency (approximately)

    def test_prometheus_format_with_labels(self):
        """Prometheus format should include rule labels for violations."""
        collector = MetricsCollector()
        collector.record_policy_violation("IDG-01")
        collector.record_policy_violation("PDX-01")

        metrics = collector.get_metrics()
        prometheus_output = format_metrics_for_prometheus(metrics)

        # Should include rule labels
        assert 'policy_violations_total{rule="IDG-01"}' in prometheus_output
        assert 'policy_violations_total{rule="PDX-01"}' in prometheus_output

    def test_health_check_json_format(self):
        """Health check JSON format should be valid."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            timestamp="2026-07-31T12:34:56Z",
            audit_store="connected",
            audit_store_latency_ms=5.2,
            secret_key_loaded=True,
            deployment_mode="production",
            message=None
        )

        json_output = format_health_check_for_json(result)

        assert json_output["status"] == "healthy"
        assert json_output["audit_store"] == "connected"
        assert json_output["audit_store_latency_ms"] == 5.2
        assert json_output["secret_key_loaded"] is True
        assert json_output["deployment_mode"] == "production"
        assert json_output["message"] is None

    def test_health_check_json_with_message(self):
        """Health check JSON should include error message if present."""
        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            timestamp="2026-07-31T12:34:56Z",
            audit_store="disconnected",
            audit_store_latency_ms=0.0,
            secret_key_loaded=False,
            deployment_mode="production",
            message="Database connection failed"
        )

        json_output = format_health_check_for_json(result)
        assert json_output["status"] == "unhealthy"
        assert json_output["message"] == "Database connection failed"


class TestStructuredLogging:
    """Test structured logging."""

    def test_structured_logger_creation(self):
        """Structured logger should be created successfully."""
        logger = StructuredLogger("test_logger")
        assert logger is not None
        assert logger.logger is not None

    def test_logger_has_handlers(self):
        """Structured logger should have handlers."""
        logger = StructuredLogger("test_logger")
        assert len(logger.logger.handlers) > 0


class TestGlobalMetricsCollector:
    """Test global metrics collector."""

    def test_get_metrics_collector_singleton(self):
        """get_metrics_collector should return same instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        assert collector1 is collector2

    def test_global_collector_works(self):
        """Global collector should track metrics."""
        collector = get_metrics_collector()
        collector.reset()  # Clear for test

        collector.record_event_written()
        metrics = collector.get_metrics()

        assert metrics.events_written > 0
