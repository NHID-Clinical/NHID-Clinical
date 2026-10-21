"""Smoke tests for Docker container deployment."""

import ast
import importlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest

# Resolve repository root relative to this test file (tests/ -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[1]

# Optional helper: skip docker-heavy tests if docker isn't available in the runner
DOCKER_AVAILABLE = shutil.which("docker") is not None


def _dockerfile() -> str:
    return (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")


def _cmd_target(dockerfile: str) -> str:
    """The `module:attr` uvicorn is told to serve."""
    match = re.search(r'uvicorn"?,?\s*"([A-Za-z_][\w.]*:[A-Za-z_]\w*)"', dockerfile)
    assert match, "could not find the uvicorn target in the Dockerfile CMD"
    return match.group(1)


def _copied_paths(dockerfile: str) -> set[str]:
    """Everything the final stage copies in from the build context."""
    copied: set[str] = set()
    for line in dockerfile.splitlines():
        line = line.strip()
        if not line.startswith("COPY ") or "--from=" in line:
            continue
        parts = line[len("COPY "):].split()
        for token in parts[:-1]:          # the last token is the destination
            copied.add(token.rstrip("/"))
    return copied


class TestTheImageCouldActuallyStart:
    """The checks that would have caught a three-ways-broken image.

    What was here before asserted that the Dockerfile *contained the strings*
    "FROM python", "HEALTHCHECK" and "EXPOSE". Meanwhile:

      * `CMD` served `functions.handler:app`, which does not exist —
        functions/handler.py is a Lambda entry point with no ASGI object, so
        uvicorn exited with "Attribute 'app' not found in module";
      * not one of the eleven root-level modules the application is made of was
        copied into the image;
      * dependencies were installed to /root/.local and then read as a non-root
        user, and /root is mode 700.

    A `docker_image_built` fixture existed that would have caught all three —
    and **no test took it as an argument**, so it never ran. These tests are
    static on purpose: they need no daemon, so they run in CI. An actual
    `docker build` cannot live in this suite at all, because it would skip
    wherever no daemon is reachable and `scripts/validate_ci.py` pins
    `SKIP_EXPECTED = 0`; that is the tension that left the image unchecked.
    The real build is `scripts/check_docker_build.py`, run on a
    docker-enabled runner.
    """

    def test_the_cmd_target_module_exists_and_exposes_its_attribute(self):
        """The defect that made the image unstartable."""
        module_name, _, attr = _cmd_target(_dockerfile()).partition(":")
        module = importlib.import_module(module_name)
        assert hasattr(module, attr), (
            f"Dockerfile CMD serves {module_name}:{attr}, but {module_name} has "
            f"no attribute {attr!r}"
        )

    def test_the_cmd_target_is_an_asgi_application(self):
        module_name, _, attr = _cmd_target(_dockerfile()).partition(":")
        target = getattr(importlib.import_module(module_name), attr)
        # An ASGI app is callable; FastAPI instances also carry routes.
        assert callable(target), f"{module_name}:{attr} is not callable"
        assert hasattr(target, "routes"), f"{module_name}:{attr} exposes no routes"

    def test_the_cmd_target_serves_the_path_the_healthcheck_probes(self):
        """A HEALTHCHECK against a path the served app does not route would
        mark every container unhealthy."""
        dockerfile = _dockerfile()
        probe = re.search(r"curl -f http://localhost:\d+(/\S*)", dockerfile)
        assert probe, "could not find the HEALTHCHECK probe path"
        path = probe.group(1)

        module_name, _, attr = _cmd_target(dockerfile).partition(":")
        target = getattr(importlib.import_module(module_name), attr)
        paths = {getattr(route, "path", None) for route in target.routes}
        assert path in paths, (
            f"HEALTHCHECK probes {path}, which {module_name}:{attr} does not "
            f"serve; it serves {sorted(p for p in paths if p)}"
        )

    def test_every_root_module_the_app_needs_is_copied_into_the_image(self):
        """Walks the real import closure rather than trusting the COPY list."""
        dockerfile = _dockerfile()
        module_name = _cmd_target(dockerfile).partition(":")[0]

        root_modules = {p.stem: p for p in REPO_ROOT.glob("*.py")}
        needed, queue = set(), [module_name]
        while queue:
            name = queue.pop()
            if name in needed or name not in root_modules:
                continue
            needed.add(name)
            tree = ast.parse(root_modules[name].read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    queue.extend(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    queue.append(node.module.split(".")[0])

        copied = _copied_paths(dockerfile)
        missing = sorted(
            f"{name}.py" for name in needed
            if f"{name}.py" not in copied and name not in copied
        )
        assert not missing, (
            f"the image serves {module_name}:app but does not copy "
            f"{missing}; it would fail on import"
        )

    def test_packages_are_installed_somewhere_a_non_root_user_can_read(self):
        """/root is mode 700, so copying site-packages there and then dropping
        to USER nhid makes every dependency unreadable.

        Scans instructions only — the comment explaining this fix names the old
        path, and matching prose would make the test fail on its own rationale.
        """
        instructions = "\n".join(
            line for line in _dockerfile().splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
        if "USER " not in instructions:
            return  # runs as root; the permission trap does not apply
        assert "/root/.local" not in instructions, (
            "dependencies are installed into or copied from /root/.local while "
            "the image drops to a non-root user, which cannot traverse /root "
            "(mode 700)"
        )

    def test_the_runtime_directories_the_code_reads_are_copied(self):
        """tests/ and scripts/ are runtime dependencies here, not test baggage:
        src/cts_runner.py loads tests/nhid_conformance_test_suite_v1.yaml for
        POST /v1/cts/evaluate, and src/cli.py and src/pilot_pdf.py import from
        scripts/. Pinned so a tidy-up does not quietly remove a feature."""
        copied = _copied_paths(_dockerfile())
        for required in ("src", "functions", "adapters", "tests", "scripts"):
            assert required in copied, f"{required}/ is not copied into the image"


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
