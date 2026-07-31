"""Tests for NHID-Clinical configuration management."""

import pytest
import os
import base64
from src.config import (
    load_config,
    get_config,
    reset_config,
    DeploymentMode,
    AuditStoreType,
    LogLevel,
    _decode_secret_key,
    _get_env,
)


class TestConfigEnvironmentVariables:
    """Test environment variable parsing."""

    def test_get_env_with_value(self):
        """Environment variable should be retrieved."""
        os.environ["TEST_VAR"] = "test_value"
        assert _get_env("TEST_VAR") == "test_value"
        del os.environ["TEST_VAR"]

    def test_get_env_with_default(self):
        """Default should be returned when variable not set."""
        assert _get_env("NONEXISTENT_VAR", "default") == "default"

    def test_get_env_required_raises(self):
        """Required variable should raise ValueError when not set."""
        with pytest.raises(ValueError, match="Required environment variable"):
            _get_env("NONEXISTENT_VAR", required=True)


class TestSecretKeyDecoding:
    """Test cryptographic secret key handling."""

    def test_decode_valid_secret_key(self):
        """Valid 32-byte secret key should decode."""
        key = os.urandom(32)
        b64_key = base64.b64encode(key).decode()
        decoded = _decode_secret_key(b64_key)
        assert decoded == key
        assert len(decoded) == 32

    def test_decode_invalid_length_raises(self):
        """Secret key with invalid length should raise ValueError."""
        key_16 = base64.b64encode(os.urandom(16)).decode()
        with pytest.raises(ValueError, match="must be 32 bytes"):
            _decode_secret_key(key_16)

        key_64 = base64.b64encode(os.urandom(64)).decode()
        with pytest.raises(ValueError, match="must be 32 bytes"):
            _decode_secret_key(key_64)

    def test_decode_invalid_base64_raises(self):
        """Invalid base64 should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid secret key"):
            _decode_secret_key("not-valid-base64!!!")


class TestDeploymentModes:
    """Test deployment mode configuration."""

    def test_development_mode(self, monkeypatch):
        """Development mode should allow debug and generated keys."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "development")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.deployment_mode == DeploymentMode.DEVELOPMENT
        assert config.debug is True
        # Secret key should be auto-generated
        assert len(config.audit_security.secret_key) == 32

    def test_staging_mode(self, monkeypatch):
        """Staging mode should require keys but allow full logging."""
        key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setenv("DEPLOYMENT_MODE", "staging")
        monkeypatch.setenv("AUDIT_SECRET_KEY_B64", key)

        config = load_config()
        assert config.deployment_mode == DeploymentMode.STAGING
        assert config.debug is False

    def test_production_mode(self, monkeypatch):
        """Production mode should require keys and deny debug."""
        key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setenv("DEPLOYMENT_MODE", "production")
        monkeypatch.setenv("AUDIT_SECRET_KEY_B64", key)
        monkeypatch.setenv("AUDIT_STORE_PATH", "/tmp/audit.db")

        config = load_config()
        assert config.deployment_mode == DeploymentMode.PRODUCTION
        assert config.debug is False

    def test_production_requires_secret_key(self, monkeypatch, tmp_path):
        """Production mode should require AUDIT_SECRET_KEY_B64."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "production")
        monkeypatch.setenv("AUDIT_STORE_PATH", str(tmp_path / "audit.db"))
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        with pytest.raises(ValueError, match="required in production"):
            load_config()

    def test_production_denies_debug_logging(self, monkeypatch, tmp_path):
        """Production mode should reject DEBUG logging."""
        key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setenv("DEPLOYMENT_MODE", "production")
        monkeypatch.setenv("AUDIT_SECRET_KEY_B64", key)
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("AUDIT_STORE_PATH", str(tmp_path / "audit.db"))

        with pytest.raises(ValueError, match="LOG_LEVEL=DEBUG is not allowed in production"):
            load_config()


class TestAuditStoreConfiguration:
    """Test audit storage backend configuration."""

    def test_sqlite_store_default(self, monkeypatch):
        """SQLite should be default storage backend."""
        monkeypatch.delenv("AUDIT_STORE_TYPE", raising=False)
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.audit_store.store_type == AuditStoreType.SQLITE
        assert config.audit_store.sqlite_path == "/data/audit_events.db"

    def test_sqlite_store_custom_path(self, monkeypatch):
        """SQLite path should be configurable."""
        monkeypatch.setenv("AUDIT_STORE_TYPE", "sqlite")
        monkeypatch.setenv("AUDIT_STORE_PATH", "/custom/path/audit.db")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.audit_store.sqlite_path == "/custom/path/audit.db"

    def test_dynamodb_store_requires_config(self, monkeypatch):
        """DynamoDB store requires table and region."""
        key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setenv("DEPLOYMENT_MODE", "production")
        monkeypatch.setenv("AUDIT_STORE_TYPE", "dynamodb")
        monkeypatch.setenv("AUDIT_SECRET_KEY_B64", key)
        monkeypatch.setenv("AUDIT_DYNAMODB_TABLE", "audit-events")
        monkeypatch.setenv("AUDIT_DYNAMODB_REGION", "us-east-1")

        config = load_config()
        assert config.audit_store.store_type == AuditStoreType.DYNAMODB
        assert config.audit_store.dynamodb_table == "audit-events"
        assert config.audit_store.dynamodb_region == "us-east-1"

    def test_retention_days_configurable(self, monkeypatch):
        """Retention days should be configurable."""
        monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.audit_store.retention_days == 30

    def test_retention_days_default(self, monkeypatch):
        """Retention days should default to 90."""
        monkeypatch.delenv("AUDIT_RETENTION_DAYS", raising=False)
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.audit_store.retention_days == 90


class TestLoggingConfiguration:
    """Test logging configuration."""

    @pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING", "ERROR"])
    def test_log_levels_valid(self, monkeypatch, log_level):
        """All valid log levels should be accepted."""
        monkeypatch.setenv("LOG_LEVEL", log_level)
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.logging.level == LogLevel(log_level)

    def test_log_level_case_insensitive(self, monkeypatch):
        """Log level should be case-insensitive."""
        monkeypatch.setenv("LOG_LEVEL", "debug")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.logging.level == LogLevel.DEBUG

    def test_invalid_log_level_raises(self, monkeypatch):
        """Invalid log level should raise ValueError."""
        monkeypatch.setenv("LOG_LEVEL", "INVALID")

        with pytest.raises(ValueError, match="Invalid LOG_LEVEL"):
            load_config()

    def test_log_level_default(self, monkeypatch):
        """Log level should default to INFO."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.logging.level == LogLevel.INFO


class TestAWSConfiguration:
    """Test AWS integration configuration."""

    def test_aws_region_default(self, monkeypatch):
        """AWS region should default to us-east-1."""
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.aws.region == "us-east-1"

    def test_aws_region_custom(self, monkeypatch):
        """AWS region should be configurable."""
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.aws.region == "eu-west-1"

    def test_localstack_endpoint_detection(self, monkeypatch):
        """LocalStack endpoint should be detected."""
        monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localstack:4566")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.aws.use_local_stack is True
        assert config.aws.endpoint_url == "http://localstack:4566"

    def test_production_aws_endpoint(self, monkeypatch, tmp_path):
        """Production should not use LocalStack endpoint."""
        key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setenv("DEPLOYMENT_MODE", "production")
        monkeypatch.setenv("AUDIT_SECRET_KEY_B64", key)
        monkeypatch.setenv("AUDIT_STORE_PATH", str(tmp_path / "audit.db"))
        monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)

        config = load_config()
        assert config.aws.use_local_stack is False


class TestAPIConfiguration:
    """Test API server configuration."""

    def test_api_defaults(self, monkeypatch):
        """API should default to 0.0.0.0:8000."""
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8000

    def test_api_custom_host_port(self, monkeypatch):
        """API host and port should be configurable."""
        monkeypatch.setenv("API_HOST", "127.0.0.1")
        monkeypatch.setenv("API_PORT", "9000")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.api_host == "127.0.0.1"
        assert config.api_port == 9000


class TestConfigurationCaching:
    """Test global configuration caching."""

    def test_get_config_loads_once(self, monkeypatch):
        """get_config() should cache configuration."""
        reset_config()
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        # First call loads
        config1 = get_config()
        # Second call returns cached instance
        config2 = get_config()
        assert config1 is config2

    def test_reset_config_clears_cache(self, monkeypatch):
        """reset_config() should clear cached configuration."""
        reset_config()
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config1 = get_config()
        reset_config()
        config2 = get_config()
        # New instances
        assert config1 is not config2
        # But equal configuration
        assert config1.deployment_mode == config2.deployment_mode


class TestConfigurationIntegration:
    """Integration tests for complete configuration scenarios."""

    def test_development_full_config(self, monkeypatch):
        """Development mode should work with minimal configuration."""
        monkeypatch.setenv("DEPLOYMENT_MODE", "development")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.delenv("AUDIT_SECRET_KEY_B64", raising=False)

        config = load_config()
        assert config.deployment_mode == DeploymentMode.DEVELOPMENT
        assert config.logging.level == LogLevel.DEBUG
        assert len(config.audit_security.secret_key) == 32

    def test_production_full_config(self, monkeypatch, tmp_path):
        """Production mode should require all security settings."""
        key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setenv("DEPLOYMENT_MODE", "production")
        monkeypatch.setenv("AUDIT_SECRET_KEY_B64", key)
        monkeypatch.setenv("AUDIT_STORE_TYPE", "dynamodb")
        monkeypatch.setenv("AUDIT_DYNAMODB_TABLE", "audit-events")
        monkeypatch.setenv("AUDIT_DYNAMODB_REGION", "us-east-1")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        config = load_config()
        assert config.deployment_mode == DeploymentMode.PRODUCTION
        assert config.audit_store.store_type == AuditStoreType.DYNAMODB
        assert config.debug is False

    def test_docker_compose_config(self, monkeypatch):
        """Should load typical docker-compose environment."""
        key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setenv("DEPLOYMENT_MODE", "development")
        monkeypatch.setenv("AUDIT_STORE_TYPE", "sqlite")
        monkeypatch.setenv("AUDIT_STORE_PATH", "/data/audit_events.db")
        monkeypatch.setenv("AUDIT_SECRET_KEY_B64", key)
        monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localstack:4566")

        config = load_config()
        assert config.audit_store.sqlite_path == "/data/audit_events.db"
        assert config.aws.use_local_stack is True
