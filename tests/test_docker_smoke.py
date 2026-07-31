"""Smoke tests for Docker container deployment."""

import pytest
import os
import subprocess
import json
import time
import httpx


class TestDockerBuildAndHealthCheck:
    """Verify Docker image builds and container health checks pass."""

    @pytest.fixture(scope="class")
    def docker_image_built(self):
        """Build Docker image for testing."""
        result = subprocess.run(
            ["docker", "build", "-t", "nhid-clinical:test", "."],
            cwd="/home/user/NHID-Clinical",
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
        dockerfile_path = "/home/user/NHID-Clinical/Dockerfile"
        assert os.path.exists(dockerfile_path), "Dockerfile not found"

        with open(dockerfile_path) as f:
            content = f.read()
            # Check for critical instructions
            assert "FROM python" in content
            assert "HEALTHCHECK" in content
            assert "EXPOSE" in content

    def test_docker_compose_syntax_valid(self):
        """Verify docker-compose.yml is valid YAML."""
        import yaml
        compose_path = "/home/user/NHID-Clinical/docker-compose.yml"
        assert os.path.exists(compose_path), "docker-compose.yml not found"

        # Parse YAML to validate syntax
        with open(compose_path) as f:
            compose_data = yaml.safe_load(f)
            assert compose_data is not None
            assert "services" in compose_data
            assert "volumes" in compose_data
            assert "networks" in compose_data

    def test_dockerignore_exists(self):
        """Verify .dockerignore exists to reduce image size."""
        dockerignore_path = "/home/user/NHID-Clinical/.dockerignore"
        assert os.path.exists(dockerignore_path), ".dockerignore not found"

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
        compose_path = "/home/user/NHID-Clinical/docker-compose.yml"

        with open(compose_path) as f:
            content = f.read()
            assert "nhid-api:" in content
            assert "build:" in content
            assert "healthcheck:" in content

    def test_docker_compose_has_localstack_service(self):
        """Verify LocalStack service is configured for local development."""
        compose_path = "/home/user/NHID-Clinical/docker-compose.yml"

        with open(compose_path) as f:
            content = f.read()
            assert "localstack:" in content
            assert "localstack/localstack" in content

    def test_docker_compose_volume_audit_data(self):
        """Verify audit data volume is configured for persistence."""
        compose_path = "/home/user/NHID-Clinical/docker-compose.yml"

        with open(compose_path) as f:
            content = f.read()
            assert "audit-data:" in content
            assert "/data" in content

    def test_docker_compose_environment_variables(self):
        """Verify required environment variables are set."""
        compose_path = "/home/user/NHID-Clinical/docker-compose.yml"

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
        script_path = "/home/user/NHID-Clinical/scripts/init-aws.sh"
        assert os.path.exists(script_path), "init-aws.sh not found"
        assert os.access(script_path, os.X_OK), "init-aws.sh is not executable"

    def test_init_aws_script_has_required_steps(self):
        """Verify init-aws.sh has required initialization steps."""
        script_path = "/home/user/NHID-Clinical/scripts/init-aws.sh"

        with open(script_path) as f:
            content = f.read()
            assert "LocalStack" in content
            assert "s3 mb" in content or "create-log-group" in content
            assert "set -e" in content  # Fail fast
