"""Monitoring and observability for NHID-Clinical audit trail.

Provides structured logging, metrics collection, and health checks for
operational monitoring and CloudWatch integration.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class MetricName(str, Enum):
    """Audit trail metrics."""
    AUDIT_EVENTS_TOTAL = "audit_events_total"
    AUDIT_VERIFICATION_FAILURES = "audit_verification_failures"
    AUDIT_STORE_LATENCY_MS = "audit_store_latency_ms"
    POLICY_VIOLATIONS_TOTAL = "policy_violations_total"
    CONFIGURATION_ERRORS = "configuration_errors"


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthCheckResult:
    """Health check result with component status."""
    status: HealthStatus
    timestamp: str
    audit_store: str  # "connected" | "disconnected"
    audit_store_latency_ms: float
    secret_key_loaded: bool  # False if key not available
    deployment_mode: str
    message: Optional[str] = None


@dataclass
class AuditMetrics:
    """Collected audit metrics for export."""
    events_written: int = 0
    verification_failures: int = 0
    average_store_latency_ms: float = 0.0
    policy_violations_by_rule: Dict[str, int] = None
    config_errors: int = 0
    timestamp: str = None

    def __post_init__(self):
        """Initialize timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        if self.policy_violations_by_rule is None:
            self.policy_violations_by_rule = {}


class StructuredLogger:
    """Structured logging with JSON output for CloudWatch parsing."""

    def __init__(self, name: str, level: int = logging.INFO):
        """Initialize structured logger.

        Args:
            name: Logger name (module name typically)
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # JSON formatter for CloudWatch Logs Insights
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def info(self, message: str, **fields: Any) -> None:
        """Log info with structured fields.

        Args:
            message: Log message
            **fields: Additional fields for JSON output
        """
        log_obj = {
            "level": "INFO",
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **fields
        }
        self.logger.info(json.dumps(log_obj))

    def error(self, message: str, **fields: Any) -> None:
        """Log error with structured fields.

        Args:
            message: Log message
            **fields: Additional fields for JSON output
        """
        log_obj = {
            "level": "ERROR",
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **fields
        }
        self.logger.error(json.dumps(log_obj))

    def warning(self, message: str, **fields: Any) -> None:
        """Log warning with structured fields.

        Args:
            message: Log message
            **fields: Additional fields for JSON output
        """
        log_obj = {
            "level": "WARNING",
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **fields
        }
        self.logger.warning(json.dumps(log_obj))

    def debug(self, message: str, **fields: Any) -> None:
        """Log debug with structured fields.

        Args:
            message: Log message
            **fields: Additional fields for JSON output
        """
        log_obj = {
            "level": "DEBUG",
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **fields
        }
        self.logger.debug(json.dumps(log_obj))


class MetricsCollector:
    """Collects and aggregates audit metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.events_written = 0
        self.verification_failures = 0
        self.store_latencies = []  # List of latency measurements
        self.policy_violations_by_rule = {}
        self.config_errors = 0
        self.logger = StructuredLogger(__name__)

    def record_event_written(self) -> None:
        """Record a new event written."""
        self.events_written += 1

    def record_verification_failure(self, error: str) -> None:
        """Record a verification failure.

        Args:
            error: Error message
        """
        self.verification_failures += 1
        self.logger.error(
            "Audit chain verification failed",
            error=error,
            verification_failures=self.verification_failures
        )

    def record_store_latency(self, latency_ms: float) -> None:
        """Record audit store operation latency.

        Args:
            latency_ms: Operation latency in milliseconds
        """
        self.store_latencies.append(latency_ms)
        # Keep last 100 measurements for average
        if len(self.store_latencies) > 100:
            self.store_latencies.pop(0)

    def record_policy_violation(self, rule_id: str) -> None:
        """Record a policy violation detected.

        Args:
            rule_id: Policy rule ID (IDG-01, PDX-01, etc.)
        """
        if rule_id not in self.policy_violations_by_rule:
            self.policy_violations_by_rule[rule_id] = 0
        self.policy_violations_by_rule[rule_id] += 1

    def record_config_error(self, error: str) -> None:
        """Record a configuration error.

        Args:
            error: Error message
        """
        self.config_errors += 1
        self.logger.error(
            "Configuration error",
            error=error,
            config_errors=self.config_errors
        )

    def get_average_latency_ms(self) -> float:
        """Get average audit store latency.

        Returns:
            Average latency in milliseconds (0 if no measurements)
        """
        if not self.store_latencies:
            return 0.0
        return sum(self.store_latencies) / len(self.store_latencies)

    def get_metrics(self) -> AuditMetrics:
        """Get current metrics snapshot.

        Returns:
            AuditMetrics with current values
        """
        return AuditMetrics(
            events_written=self.events_written,
            verification_failures=self.verification_failures,
            average_store_latency_ms=self.get_average_latency_ms(),
            policy_violations_by_rule=self.policy_violations_by_rule.copy(),
            config_errors=self.config_errors,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self.events_written = 0
        self.verification_failures = 0
        self.store_latencies = []
        self.policy_violations_by_rule = {}
        self.config_errors = 0


# Global metrics collector instance
_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector.

    Returns:
        Global MetricsCollector instance
    """
    return _metrics


class HealthChecker:
    """Health check for audit trail components."""

    def __init__(self, audit_store):
        """Initialize health checker.

        Args:
            audit_store: AuditStore instance to check
        """
        self.audit_store = audit_store
        self.logger = StructuredLogger(__name__)

    def check(self, deployment_mode: str) -> HealthCheckResult:
        """Perform health check.

        Args:
            deployment_mode: Current deployment mode

        Returns:
            HealthCheckResult with status and metrics
        """
        try:
            # Check audit store connectivity
            start_time = time.time()
            try:
                # Try a simple read operation
                self.audit_store.read_event("_health_check_")
                store_latency_ms = (time.time() - start_time) * 1000
                store_status = "connected"
            except Exception as e:
                store_latency_ms = (time.time() - start_time) * 1000
                store_status = "disconnected"
                self.logger.warning(
                    "Audit store health check failed",
                    error=str(e),
                    latency_ms=store_latency_ms
                )

            # Check secret key
            secret_key_loaded = (
                self.audit_store.secret_key is not None
                and len(self.audit_store.secret_key) == 32
            )

            # Determine overall status
            if store_status == "connected" and secret_key_loaded:
                status = HealthStatus.HEALTHY
            elif store_status == "connected" or secret_key_loaded:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            result = HealthCheckResult(
                status=status,
                timestamp=datetime.utcnow().isoformat() + "Z",
                audit_store=store_status,
                audit_store_latency_ms=store_latency_ms,
                secret_key_loaded=secret_key_loaded,
                deployment_mode=deployment_mode,
                message=None if status == HealthStatus.HEALTHY else "See component status"
            )

            if status == HealthStatus.HEALTHY:
                self.logger.info(
                    "Health check passed",
                    audit_store=store_status,
                    latency_ms=store_latency_ms,
                    deployment_mode=deployment_mode
                )

            return result

        except Exception as e:
            self.logger.error(
                "Health check failed with exception",
                error=str(e)
            )
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.utcnow().isoformat() + "Z",
                audit_store="disconnected",
                audit_store_latency_ms=0.0,
                secret_key_loaded=False,
                deployment_mode=deployment_mode,
                message=str(e)
            )


def format_metrics_for_prometheus(metrics: AuditMetrics) -> str:
    """Format metrics in Prometheus text format.

    Args:
        metrics: AuditMetrics to format

    Returns:
        Prometheus-formatted metrics string
    """
    lines = [
        f'# HELP {MetricName.AUDIT_EVENTS_TOTAL.value} Total audit events written',
        f'# TYPE {MetricName.AUDIT_EVENTS_TOTAL.value} counter',
        f'{MetricName.AUDIT_EVENTS_TOTAL.value} {metrics.events_written}',
        '',
        f'# HELP {MetricName.AUDIT_VERIFICATION_FAILURES.value} Audit chain verification failures',
        f'# TYPE {MetricName.AUDIT_VERIFICATION_FAILURES.value} counter',
        f'{MetricName.AUDIT_VERIFICATION_FAILURES.value} {metrics.verification_failures}',
        '',
        f'# HELP {MetricName.AUDIT_STORE_LATENCY_MS.value} Average audit store latency in milliseconds',
        f'# TYPE {MetricName.AUDIT_STORE_LATENCY_MS.value} gauge',
        f'{MetricName.AUDIT_STORE_LATENCY_MS.value} {metrics.average_store_latency_ms}',
        '',
        f'# HELP {MetricName.POLICY_VIOLATIONS_TOTAL.value} Policy violations by rule',
        f'# TYPE {MetricName.POLICY_VIOLATIONS_TOTAL.value} counter',
    ]

    for rule_id, count in metrics.policy_violations_by_rule.items():
        lines.append(f'{MetricName.POLICY_VIOLATIONS_TOTAL.value}{{rule="{rule_id}"}} {count}')

    lines.extend([
        '',
        f'# HELP {MetricName.CONFIGURATION_ERRORS.value} Configuration errors',
        f'# TYPE {MetricName.CONFIGURATION_ERRORS.value} counter',
        f'{MetricName.CONFIGURATION_ERRORS.value} {metrics.config_errors}',
    ])

    return '\n'.join(lines) + '\n'


def format_health_check_for_json(result: HealthCheckResult) -> Dict[str, Any]:
    """Format health check result as JSON.

    Args:
        result: HealthCheckResult

    Returns:
        JSON-serializable dictionary
    """
    return {
        "status": result.status.value,
        "timestamp": result.timestamp,
        "audit_store": result.audit_store,
        "audit_store_latency_ms": round(result.audit_store_latency_ms, 2),
        "secret_key_loaded": result.secret_key_loaded,
        "deployment_mode": result.deployment_mode,
        "message": result.message
    }
