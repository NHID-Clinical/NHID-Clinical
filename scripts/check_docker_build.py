#!/usr/bin/env python3
"""Build the Docker image and prove the container actually serves /health.

Why this is a script and not a test
-----------------------------------
`scripts/validate_ci.py` pins `SKIP_EXPECTED = 0`, so a test that skips when no
Docker daemon is reachable fails CI. That constraint is why
`tests/test_docker_smoke.py` carried a `docker_image_built` fixture **no test
ever took as an argument** — wiring it would have either failed the suite or
skipped it, so it was left inert and the image went unverified. It was broken
three independent ways:

  * `CMD` served `functions.handler:app`, which does not exist;
  * not one of the eleven root-level application modules was copied in;
  * dependencies were installed to /root/.local and read as a non-root user.

The static half of that is now asserted in `tests/test_docker_smoke.py`, which
needs no daemon and therefore runs everywhere. This script is the other half:
the real build, plus a container that has to answer on /health.

Usage
-----
    python scripts/check_docker_build.py            # build, run, probe, clean up
    python scripts/check_docker_build.py --keep     # leave the container running

Exit codes: 0 pass · 1 a real failure · 2 Docker unavailable (not a pass).
A missing daemon is reported as "could not verify", never as success.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "nhid-clinical:build-check"
CONTAINER = "nhid-clinical-build-check"
PORT = 8123
HEALTH_URL = f"http://127.0.0.1:{PORT}/health"


def _run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout
    )


def _docker_ready() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "the docker binary is not on PATH"
    probe = _run(["docker", "info"], timeout=30)
    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout or "").strip().splitlines()
        return False, detail[-1] if detail else "docker info failed"
    return True, ""


def _cleanup() -> None:
    _run(["docker", "rm", "-f", CONTAINER], timeout=60)
    _run(["docker", "rmi", "-f", IMAGE], timeout=120)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true",
                        help="leave the container running for inspection")
    args = parser.parse_args(argv)

    ready, why = _docker_ready()
    if not ready:
        print(f"DOCKER UNAVAILABLE: {why}")
        print("  This is NOT a pass. The image was not verified. Re-run where a")
        print("  Docker daemon is reachable; tests/test_docker_smoke.py covers")
        print("  the static half and does run everywhere.")
        return 2

    print(f"Building {IMAGE} ...")
    build = _run(["docker", "build", "-t", IMAGE, "."])
    if build.returncode != 0:
        print("BUILD FAIL")
        print(build.stderr[-4000:])
        return 1
    print("  build ok")

    _run(["docker", "rm", "-f", CONTAINER], timeout=60)
    print(f"Starting {CONTAINER} on port {PORT} ...")
    up = _run([
        "docker", "run", "-d", "--name", CONTAINER,
        "-p", f"{PORT}:8000", IMAGE,
    ], timeout=120)
    if up.returncode != 0:
        print("RUN FAIL")
        print(up.stderr[-4000:])
        _cleanup()
        return 1

    # The container has to answer, not merely exist: a bad CMD exits instantly
    # and `docker run -d` still returns 0.
    deadline = time.monotonic() + 60
    body = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
                if response.status == 200:
                    body = response.read().decode("utf-8")
                    break
        except (urllib.error.URLError, OSError):
            pass
        state = _run(["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER],
                     timeout=30)
        if state.stdout.strip() == "false":
            logs = _run(["docker", "logs", CONTAINER], timeout=60)
            print("CONTAINER EXITED before serving /health")
            print((logs.stdout or "")[-2000:])
            print((logs.stderr or "")[-2000:])
            if not args.keep:
                _cleanup()
            return 1
        time.sleep(1)

    if body is None:
        logs = _run(["docker", "logs", CONTAINER], timeout=60)
        print(f"HEALTH FAIL: no 200 from {HEALTH_URL} within 60s")
        print((logs.stdout or "")[-2000:])
        print((logs.stderr or "")[-2000:])
        if not args.keep:
            _cleanup()
        return 1

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        print(f"HEALTH FAIL: /health returned non-JSON: {body[:200]!r}")
        if not args.keep:
            _cleanup()
        return 1

    print(f"  /health -> {parsed}")

    if args.keep:
        print(f"DOCKER BUILD PASS: {CONTAINER} left running on port {PORT}")
        return 0

    _cleanup()
    print("DOCKER BUILD PASS: image builds, container starts, /health answers 200")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
