"""NHID-Clinical configuration management.

Centralizes environment-based configuration for deployment modes (development, staging, production).
Validates configuration at startup with fail-fast semantics.
"""

import os
import base64
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


class DeploymentMode(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AuditStoreType(str, Enum):
    """Audit event storage backend."""
    SQLITE = "sqlite"
    DYNAMODB = "dynamodb"


class LogLevel(str, Enum):
    """Logging verbosity."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class AuditStoreConfig:
    """Audit storage configuration."""
    store_type: AuditStoreType
    sqlite_path: Optional[str] = None  # /data/audit_events.db for sqlite
    dynamodb_table: Optional[str] = None  # audit-events for dynamodb
    dynamodb_region: Optional[str] = None  # us-east-1 for dynamodb
    retention_days: int = 90  # Default TTL for audit events


@dataclass(frozen=True)
class AuditSecurityConfig:
    """Cryptographic security configuration."""
    secret_key: bytes  # 32-byte HMAC secret for event signing
    verify_signatures: bool = True  # Always verify in production


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""
    level: LogLevel
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass(frozen=True)
class AWSConfig:
    """AWS integration configuration (for DynamoDB, CloudWatch, Secrets Manager)."""
    region: str = "us-east-1"
    endpoint_url: Optional[str] = None  # http://localstack:4566 for development
    use_local_stack: bool = False  # True if endpoint_url is set


@dataclass(frozen=True)
class NHIDConfig:
    """Complete NHID-Clinical configuration."""
    deployment_mode: DeploymentMode
    audit_store: AuditStoreConfig
    audit_security: AuditSecurityConfig
    logging: LoggingConfig
    aws: AWSConfig
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False  # Only True in development


def _get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Get environment variable with validation.

    Args:
        key: Environment variable name
        default: Default value if not set
        required: Raise ValueError if not set and no default

    Returns:
        Environment variable value or default

    Raises:
        ValueError: If required but not found
    """
    value = os.getenv(key, default)
    if value is None and required:
        raise ValueError(f"Required environment variable '{key}' not set")
    return value or ""


def _decode_secret_key(b64_encoded: str) -> bytes:
    """Decode base64-encoded secret key.

    Args:
        b64_encoded: Base64-encoded 32-byte key

    Returns:
        Decoded bytes

    Raises:
        ValueError: If not 32 bytes or invalid base64
    """
    try:
        decoded = base64.b64decode(b64_encoded)
        if len(decoded) != 32:
            raise ValueError(f"Secret key must be 32 bytes, got {len(decoded)}")
        return decoded
    except Exception as e:
        raise ValueError(f"Invalid secret key: {e}")


def load_config() -> NHIDConfig:
    """Load and validate configuration from environment variables.

    Returns:
        NHIDConfig instance with all settings

    Raises:
        ValueError: If configuration is invalid or incomplete
    """
    # Deployment mode
    mode_str = _get_env("DEPLOYMENT_MODE", "development").lower()
    try:
        deployment_mode = DeploymentMode(mode_str)
    except ValueError:
        raise ValueError(f"Invalid DEPLOYMENT_MODE: {mode_str}")

    # Audit storage
    store_type_str = _get_env("AUDIT_STORE_TYPE", "sqlite").lower()
    try:
        store_type = AuditStoreType(store_type_str)
    except ValueError:
        raise ValueError(f"Invalid AUDIT_STORE_TYPE: {store_type_str}")

    if store_type == AuditStoreType.SQLITE:
        sqlite_path = _get_env("AUDIT_STORE_PATH", "/data/audit_events.db")
        # Validate path is writable in production
        if deployment_mode == DeploymentMode.PRODUCTION:
            parent_dir = Path(sqlite_path).parent
            if not parent_dir.exists():
                raise ValueError(f"AUDIT_STORE_PATH parent directory does not exist: {parent_dir}")
            if not os.access(parent_dir, os.W_OK):
                raise ValueError(f"AUDIT_STORE_PATH parent directory is not writable: {parent_dir}")
        audit_store = AuditStoreConfig(
            store_type=store_type,
            sqlite_path=sqlite_path,
            retention_days=int(_get_env("AUDIT_RETENTION_DAYS", "90"))
        )
    elif store_type == AuditStoreType.DYNAMODB:
        audit_store = AuditStoreConfig(
            store_type=store_type,
            dynamodb_table=_get_env("AUDIT_DYNAMODB_TABLE", "audit-events"),
            dynamodb_region=_get_env("AUDIT_DYNAMODB_REGION", "us-east-1"),
            retention_days=int(_get_env("AUDIT_RETENTION_DAYS", "90"))
        )
    else:
        raise ValueError(f"Unsupported AUDIT_STORE_TYPE: {store_type}")

    # Audit security (secret key)
    secret_key_b64 = _get_env("AUDIT_SECRET_KEY_B64")
    if not secret_key_b64:
        if deployment_mode == DeploymentMode.PRODUCTION:
            raise ValueError("AUDIT_SECRET_KEY_B64 is required in production")
        # Generate temporary key for development
        import os as os_module
        secret_key = os_module.urandom(32)
    else:
        secret_key = _decode_secret_key(secret_key_b64)

    audit_security = AuditSecurityConfig(
        secret_key=secret_key,
        verify_signatures=True  # Always enabled
    )

    # Logging
    log_level_str = _get_env("LOG_LEVEL", "INFO").upper()
    try:
        log_level = LogLevel(log_level_str)
    except ValueError:
        raise ValueError(f"Invalid LOG_LEVEL: {log_level_str}")

    logging_config = LoggingConfig(level=log_level)

    # AWS configuration
    aws_region = _get_env("AWS_REGION", "us-east-1")
    aws_endpoint = _get_env("AWS_ENDPOINT_URL", None)
    aws_config = AWSConfig(
        region=aws_region,
        endpoint_url=aws_endpoint if aws_endpoint else None,
        use_local_stack=bool(aws_endpoint)
    )

    # Build complete configuration
    config = NHIDConfig(
        deployment_mode=deployment_mode,
        audit_store=audit_store,
        audit_security=audit_security,
        logging=logging_config,
        aws=aws_config,
        api_host=_get_env("API_HOST", "0.0.0.0"),
        api_port=int(_get_env("API_PORT", "8000")),
        debug=(deployment_mode == DeploymentMode.DEVELOPMENT)
    )

    # Validate configuration
    _validate_config(config)

    return config


def _validate_config(config: NHIDConfig) -> None:
    """Validate configuration for internal consistency.

    Raises:
        ValueError: If configuration is invalid
    """
    # Production-specific validation
    if config.deployment_mode == DeploymentMode.PRODUCTION:
        if config.debug:
            raise ValueError("debug=True is not allowed in production")
        if config.logging.level == LogLevel.DEBUG:
            raise ValueError("LOG_LEVEL=DEBUG is not allowed in production")
        if config.audit_store.store_type == AuditStoreType.SQLITE:
            # SQLite is acceptable but warn about production use
            pass

    # SQLite path validation
    if config.audit_store.store_type == AuditStoreType.SQLITE:
        if not config.audit_store.sqlite_path:
            raise ValueError("sqlite_path is required when AUDIT_STORE_TYPE=sqlite")

    # DynamoDB validation
    if config.audit_store.store_type == AuditStoreType.DYNAMODB:
        if not config.audit_store.dynamodb_table:
            raise ValueError("dynamodb_table is required when AUDIT_STORE_TYPE=dynamodb")
        if not config.audit_store.dynamodb_region:
            raise ValueError("dynamodb_region is required when AUDIT_STORE_TYPE=dynamodb")

    # Secret key validation
    if len(config.audit_security.secret_key) != 32:
        raise ValueError(f"Secret key must be 32 bytes, got {len(config.audit_security.secret_key)}")


# Global configuration instance (lazy-loaded)
_config: Optional[NHIDConfig] = None


def get_config() -> NHIDConfig:
    """Get or load global configuration.

    Returns:
        Cached NHIDConfig instance

    Raises:
        ValueError: If configuration is invalid
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset global configuration cache (for testing)."""
    global _config
    _config = None
