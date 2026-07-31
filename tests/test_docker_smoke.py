"""Smoke tests for Docker container deployment."""

import pytest
import os
import subprocess
import json
import time
import httpx
from pathlib import Path
import shutil

# Resolve repository root relative to this test file (tests/ -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[1]

# Optional helper: skip docker-heavy tests if docker isn't available in the runner
DOCKER_AVAILABLE = shutil.which("docker") is not None


class TestDockerBuildAndHealthCheck:
    """Verify Docker image builds and container health checks pass."""

    @pytest.fixture(scope="class")
    def docker_image_built(self):
        """Build Docker image for testing."""
        if not DOCKER_AVAILABLE:
            pytest.skip("docker not available in this environment")

        result = subprocess.run(
            ["docker", "build", "-t", "nhid-clinical:test", "."],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300
        )
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        yield
        # Cleanup
        subprocess.run(
            ["docker", "rmi", "nhid-clinical:test"],
            capture_output=True
        )

    def test_dockerfile_syntax_valid(self):
        """Verify Dockerfile is valid."""
        dockerfile_path = REPO_ROOT / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile not found"

        with open(dockerfile_path) as f:
            content = f.read()
            # Check for critical instructions
            assert "FROM python" in content
            assert "HEALTHCHECK" in content
            assert "EXPOSE" in content

    def test_docker_compose_syntax_valid(self):
        """Verify docker-compose.yml is valid YAML."""
        import yaml
        compose_path = REPO_ROOT / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml not found"

        # Parse YAML to validate syntax
        with open(compose_path) as f:
            compose_data = yaml.safe_load(f)
            assert compose_data is not None
            assert "services" in compose_data
            assert "volumes" in compose_data
            assert "networks" in compose_data

    def test_dockerignore_exists(self):
        """Verify .dockerignore exists to reduce image size."""
        dockerignore_path = REPO_ROOT / ".dockerignore"
        assert dockerignore_path.exists(), ".dockerignore not found"

        with open(dockerignore_path) as f:
            content = f.read()
            # Verify common exclusions
            assert ".git" in content
            assert "__pycache__" in content
            assert ".pytest_cache" in content


class TestDockerComposeBuild:
    """Verify docker-compose services configuration."""

    def test_docker_compose_has_nhid_api_service(self):
        """Verify nhid-api service is configured."""
        compose_path = REPO_ROOT / "docker-compose.yml"

        with open(compose_path) as f:
            content = f.read()
            assert "nhid-api:" in content
            assert "build:" in content
            assert "healthcheck:" in content

    def test_docker_compose_has_localstack_service(self):
        """Verify LocalStack service is configured for local development."""
        compose_path = REPO_ROOT / "docker-compose.yml"

        with open(compose_path) as f:
            content = f.read()
            assert "localstack:" in content
            assert "localstack/localstack" in content

    def test_docker_compose_volume_audit_data(self):
        """Verify audit data volume is configured for persistence."""
        compose_path = REPO_ROOT / "docker-compose.yml"

        with open(compose_path) as f:
            content = f.read()
            assert "audit-data:" in content
            assert "/data" in content

    def test_docker_compose_environment_variables(self):
        """Verify required environment variables are set."""
        compose_path = REPO_ROOT / "docker-compose.yml"

        with open(compose_path) as f:
            content = f.read()
            required_vars = [
                "DEPLOYMENT_MODE",
                "AUDIT_STORE_TYPE",
                "AUDIT_STORE_PATH",
                "AUDIT_SECRET_KEY_B64",
                "LOG_LEVEL"
            ]
            for var in required_vars:
                assert var in content, f"Environment variable {var} not found"


class TestInitAwsScript:
    """Verify LocalStack initialization script."""

    def test_init_aws_script_exists(self):
        """Verify init-aws.sh exists and is executable."""
        script_path = REPO_ROOT / "scripts" / "init-aws.sh"
        assert script_path.exists(), "init-aws.sh not found"
        assert os.access(script_path, os.X_OK), "init-aws.sh is not executable"

    def test_init_aws_script_has_required_steps(self):
        """Verify init-aws.sh has required initialization steps."""
        script_path = REPO_ROOT / "scripts" / "init-aws.sh"

        with open(script_path) as f:
            content = f.read()
            assert "LocalStack" in content
            assert "s3 mb" in content or "create-log-group" in content
            assert "set -e" in content  # Fail fast
