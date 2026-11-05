"""
Dockerfile.pilot: the Tier 0 kit as one container, run with networking off.

The image cannot be built in every CI runner, so this pins its contract
statically: what it copies exists and is let through by its own dockerignore
(the repository-wide .dockerignore drops *.md, which would break the build,
since pyproject.toml declares README.md), it runs as a non-root user, its entry
point is the `nhid` command, and the documented run disables the network.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile.pilot").read_text()
IGNORE = (ROOT / "Dockerfile.pilot.dockerignore").read_text().splitlines()


def _copied() -> list[str]:
    sources = []
    for line in DOCKERFILE.splitlines():
        if line.startswith("COPY "):
            sources += line.split()[1:-1]
    return sources


def test_every_copied_path_exists_and_is_in_the_build_context():
    allowed = {line[1:].rstrip("/") for line in IGNORE if line.startswith("!")}
    assert "*" in IGNORE, "the pilot context should start from nothing and allow-list"
    for source in _copied():
        assert (ROOT / source).exists(), source
        assert source.rstrip("/") in allowed, f"{source} is excluded from the build context"


def test_the_readme_pyproject_declares_reaches_the_build():
    assert re.search(r'^readme = "README.md"', (ROOT / "pyproject.toml").read_text(), re.M)
    assert "README.md" in _copied()


def test_it_runs_as_a_non_root_user_with_nhid_as_the_entry_point():
    assert re.search(r"^USER kit$", DOCKERFILE, re.M)
    assert 'ENTRYPOINT ["nhid"]' in DOCKERFILE


def test_the_documented_run_switches_the_network_off():
    for text in (DOCKERFILE,
                 (ROOT / "docs" / "pilot-kit" / "README.md").read_text(),
                 (ROOT / "docs" / "pilot-offer.md").read_text()):
        assert "--network none" in text
