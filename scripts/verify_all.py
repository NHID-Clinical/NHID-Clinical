#!/usr/bin/env python3
"""
NHID-Clinical — complete pre-push verification
==============================================
One entry point that runs the whole verification surface, so the class of
failure that only shows up in CI can be seen before a push.

Why this exists
---------------
PR #391 went red twice on things a green `pytest` could not have predicted,
because both live in state the test suite never reads:

  1. `specs/NHID-Clinical-Playbook.pdf` was on disk and untracked. `.gitignore`
     ignores `*.pdf` repository-wide and the published PDFs are kept by
     `git add -f`, so `git add -A` skipped it silently and `git status` had
     nothing to show. Every local run passed — the file was right there. Only a
     clean checkout failed.
  2. `assets/data/walkthrough-trace.json` and `evidence-visuals.json` were stale
     after the DBC-01 artifact path was removed. Regenerating one surfaced the
     other.

Both are downstream artifacts: real published state that no test asserts on.
This script checks them alongside the suite.

Design rule: **call the existing checks, do not reimplement them.** Every step
below shells out to the same command `.github/workflows/ci.yml` runs. If CI
changes, this file changes with it or it is wrong — there is no second copy of
the logic to drift.

Usage:
  python scripts/verify_all.py            # everything
  python scripts/verify_all.py --fast     # skip step 1 (the ~3-minute suite)
  python scripts/verify_all.py --list     # print the steps and exit

Exit code is 0 only when every step passes.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# app:app, started the way ci.yml starts it. See `_serving()`.
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
SERVER_READY_TIMEOUT_S = 30

# Directories whose contents are published — shipped to readers rather than
# only read by the suite. A file here that exists on disk but not in the index
# is invisible locally and missing in a clean checkout.
PUBLISHED_DIRS = ("specs",)

# Generated fixtures. Each is produced by a `--check`-able generator above; a
# dirty one means a generator ran and its output was never committed.
GENERATED_FIXTURES = (
    "assets/data/gateway-trace.json",
    "assets/data/walkthrough-trace.json",
    "assets/data/evidence-visuals.json",
)


# --------------------------------------------------------------------------
# result plumbing
# --------------------------------------------------------------------------


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""
    remedy: str = ""
    lines: list[str] = field(default_factory=list)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def _run(name: str, argv: list[str], remedy: str, env: dict | None = None) -> Result:
    """Run one external check and capture enough output to act on a failure."""
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )
    output = (proc.stdout + proc.stderr).strip().splitlines()
    return Result(
        name=name,
        ok=proc.returncode == 0,
        detail=f"exit {proc.returncode}",
        remedy=remedy,
        # A failing check's own message is the useful part; the last lines carry
        # it for every script here and for pytest.
        lines=output[-25:] if proc.returncode else output[-1:],
    )


# --------------------------------------------------------------------------
# step 1 — the suite, against a live API
# --------------------------------------------------------------------------


class _serving:
    """Run `app:app` for the duration of the block.

    `validate_ci.py` runs the suite itself, and a large part of that suite needs
    an API on 127.0.0.1:8000. Without one it measures a different shape than CI
    does and reports a count that will never match UNIT_PUBLISHED — which is why
    ci.yml wraps the same call in a uvicorn start/poll/trap. Reproducing that
    here is the single biggest reason a local run and CI used to disagree.

    If something is already listening, use it and leave it alone.
    """

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.log = ROOT / ".verify-server.log"
        self.borrowed = False
        self.up = False
        self.why_not = ""

    def _up(self) -> bool:
        try:
            with urllib.request.urlopen(
                f"http://{SERVER_HOST}:{SERVER_PORT}/openapi.json", timeout=2
            ) as r:
                return r.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def _reason(self) -> str:
        """The last useful line of the server log, for a startup failure."""
        try:
            lines = [l.strip() for l in self.log.read_text().splitlines() if l.strip()]
        except OSError:
            return "no output"
        for line in reversed(lines):
            if "Error" in line or "error" in line or "Exception" in line:
                return line
        return lines[-1] if lines else "no output"

    def __enter__(self) -> "_serving":
        if self._up():
            self.borrowed = True
            self.up = True
            print(f"    · reusing the API already on :{SERVER_PORT}")
            return self

        with socket.socket() as s:
            if s.connect_ex((SERVER_HOST, SERVER_PORT)) == 0:
                self.why_not = (
                    f":{SERVER_PORT} is occupied by something that is not this API"
                )
                print(f"    ! {self.why_not}")
                return self

        self.proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app:app",
                "--host", SERVER_HOST, "--port", str(SERVER_PORT),
            ],
            cwd=ROOT,
            stdout=self.log.open("w"),
            stderr=subprocess.STDOUT,
        )

        for _ in range(SERVER_READY_TIMEOUT_S):
            if self.proc.poll() is not None:
                self.why_not = f"the API exited during startup: {self._reason()}"
                print(f"    ! {self.why_not}")
                return self
            if self._up():
                self.up = True
                print(f"    · API up on :{SERVER_PORT}")
                return self
            time.sleep(1)

        self.why_not = f"the API did not become ready within {SERVER_READY_TIMEOUT_S}s"
        print(f"    ! {self.why_not}")
        return self

    def __exit__(self, *exc) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.log.unlink(missing_ok=True)


def step_suite() -> Result:
    """The suite, measured the way CI measures it.

    The published count (UNIT_PUBLISHED) is the count *against a live API*: 18
    integration tests skip without one, so a suite run with no server can never
    reach it. `NHID_REQUIRE_SERVER=1` turns that into an error instead of a
    silent 18 skips — which is the whole reason ci.yml sets it.

    When the API cannot be started at all, say that, rather than reporting a
    count mismatch that is really a missing dependency. An earlier draft of this
    step blamed UNIT_PUBLISHED for a missing `openai` package, which would have
    sent someone to bump a published number that was correct.
    """
    with _serving() as server:
        if not server.up:
            probe = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--no-header"],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            tail = (probe.stdout + probe.stderr).strip().splitlines()
            return Result(
                name="Unit suite + published-count invariant",
                ok=False,
                detail="the API could not be started, so the suite was not measured "
                       "the way CI measures it",
                remedy=(
                    "pip install -r requirements.txt   "
                    "# app:app imports llm.py, which imports openai\n"
                    "    Then re-run. Until the API starts, the published count "
                    "cannot be checked locally:\n"
                    "    18 integration tests skip without it and the total can "
                    "never reach UNIT_PUBLISHED."
                ),
                lines=[server.why_not, "", "suite without an API (reduced shape):"]
                      + tail[-3:],
            )

        return _run(
            "Unit suite + published-count invariant",
            [sys.executable, "scripts/validate_ci.py"],
            remedy=(
                "The suite disagrees with UNIT_PUBLISHED in scripts/validate_ci.py. "
                "If the change to the test count is intended, run "
                "`python scripts/bump_published_test_count.py` to move the "
                "constant and every published surface together."
            ),
            # Without this a dead API degrades to a warning and the count is
            # measured against the wrong shape while still exiting 0.
            env={"NHID_REQUIRE_SERVER": "1"},
        )


# --------------------------------------------------------------------------
# step 9 — published artifacts are actually in the index
# --------------------------------------------------------------------------


def _tracked(path: str) -> bool:
    return _git("ls-files", "--error-unmatch", "--", path).returncode == 0


def _ignored(path: str) -> bool:
    return _git("check-ignore", "-q", "--", path).returncode == 0


def step_published_artifacts() -> Result:
    """Catch a published file that exists locally and is missing from the index.

    `git status` cannot find this one. `specs/*.pdf` matches the repository-wide
    `*.pdf` rule in .gitignore, so an untracked PDF there is not merely quiet —
    it is deliberately suppressed. The published ones are in the repository only
    because someone ran `git add -f`, and nothing re-applies that when a
    generator rewrites the file. So ask the index directly instead of asking
    status.
    """
    problems: list[str] = []
    checked = 0

    for directory in PUBLISHED_DIRS:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            checked += 1
            if _tracked(rel):
                continue
            problems.append(
                f"{rel} — on disk, NOT tracked"
                + (
                    "  (ignored by .gitignore; this is the force-add convention "
                    "failing silently)"
                    if _ignored(rel)
                    else ""
                )
            )

    # Modified-but-uncommitted published files and generated fixtures. A dirty
    # fixture means a generator ran and its output never got committed, which is
    # how walkthrough-trace.json and evidence-visuals.json went stale.
    watched = [
        p for p in (*GENERATED_FIXTURES,) if _tracked(p)
    ] + [
        p for p in _git("ls-files", "--", *PUBLISHED_DIRS).stdout.split()
    ]
    if watched:
        dirty = _git("diff", "--name-only", "--", *watched).stdout.split()
        for path in sorted(set(dirty)):
            problems.append(
                f"{path} — tracked, but the working copy differs from the "
                "last commit; commit it before pushing"
            )

    if problems:
        return Result(
            name="Published artifacts are tracked and committed",
            ok=False,
            detail=f"{len(problems)} problem(s) across {checked} published file(s)",
            remedy=(
                "For an untracked published file:  git add -f <path>\n"
                "    (plain `git add` and `git add -A` will not work — .gitignore "
                "ignores *.pdf repository-wide.)\n"
                "    For a modified one: commit it, or `git checkout --` it if the "
                "change was not intended.\n"
    "    This step is a pre-PUSH check, so it expects a clean tree. "
    "Mid-change, use --fast."
            ),
            lines=problems,
        )

    return Result(
        name="Published artifacts are tracked and committed",
        ok=True,
        detail=f"{checked} published file(s), all tracked and clean",
    )


# --------------------------------------------------------------------------
# the step table
# --------------------------------------------------------------------------

FIXTURE_REMEDY = "Re-run the generator without --check, then commit its output."

STEPS: list[tuple[str, str, callable]] = [
    (
        "suite",
        "Unit suite + published-count invariant",
        step_suite,
    ),
    (
        "drift",
        "Published-number drift",
        lambda: _run(
            "Published-number drift",
            [sys.executable, "scripts/check_number_drift.py"],
            remedy=(
                "A published figure no longer matches its source of truth. The "
                "failure names the file and both numbers."
            ),
        ),
    ),
    (
        "controls",
        "Control-set completeness",
        lambda: _run(
            "Control-set completeness",
            [sys.executable, "scripts/check_control_set.py"],
            remedy="An authoritative surface disagrees about the v1.3 control set.",
        ),
    ),
    (
        "gateway",
        "Trust Gateway fixture matches the engine",
        lambda: _run(
            "Trust Gateway fixture matches the engine",
            [sys.executable, "scripts/build_gateway_fixture.py", "--check"],
            remedy="python scripts/build_gateway_fixture.py   # then commit",
        ),
    ),
    (
        "walkthrough",
        "Front-Desk Walkthrough fixture matches the engine",
        lambda: _run(
            "Front-Desk Walkthrough fixture matches the engine",
            [sys.executable, "scripts/build_walkthrough_fixture.py", "--check"],
            remedy="python scripts/build_walkthrough_fixture.py   # then commit",
        ),
    ),
    (
        "visuals",
        "Evidence figures match the engine",
        lambda: _run(
            "Evidence figures match the engine",
            [sys.executable, "scripts/build_evidence_visuals.py", "--check"],
            remedy="python scripts/build_evidence_visuals.py   # then commit",
        ),
    ),
    (
        "wayfinder",
        "Journey wayfinder is current",
        lambda: _run(
            "Journey wayfinder is current",
            [sys.executable, "scripts/add_journey_wayfinder.py", "--check"],
            remedy="python scripts/add_journey_wayfinder.py   # then commit",
        ),
    ),
    (
        "integrity",
        "Integrity: playbook + audit chain",
        lambda: _run(
            "Integrity: playbook + audit chain",
            [
                sys.executable, "-m", "pytest",
                "tests/test_playbook_integrity.py",
                "tests/test_audit_integrity.py",
                "-q",
            ],
            remedy=(
                "A published artifact no longer matches its source, or the audit "
                "chain no longer detects tampering."
            ),
        ),
    ),
    (
        "tracked",
        "Published artifacts are tracked and committed",
        step_published_artifacts,
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete NHID-Clinical verification surface."
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="skip the full unit suite (step 1); everything else still runs",
    )
    parser.add_argument(
        "--list", action="store_true", help="print the steps and exit"
    )
    args = parser.parse_args()

    steps = [s for s in STEPS if not (args.fast and s[0] == "suite")]

    if args.list:
        for i, (key, title, _) in enumerate(STEPS, 1):
            print(f"{i}. {title}   [{key}]")
        return 0

    if shutil.which("git") is None:
        print("git is not on PATH; the published-artifact check cannot run.")
        return 1

    width = shutil.get_terminal_size((80, 24)).columns
    print("=" * min(width, 78))
    print("NHID-Clinical — complete verification")
    if args.fast:
        print("(--fast: the unit suite is skipped; CI still runs it)")
    print("=" * min(width, 78))

    results: list[Result] = []
    started = time.monotonic()

    for i, (_key, title, fn) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {title}")
        result = fn()
        results.append(result)
        print(f"    {'PASS' if result.ok else 'FAIL'}"
              + (f"  ({result.detail})" if result.detail else ""))
        if not result.ok:
            for line in result.lines:
                print(f"      | {line}")

    failed = [r for r in results if not r.ok]
    elapsed = time.monotonic() - started

    print("\n" + "=" * min(width, 78))
    for r in results:
        print(f"  {'PASS' if r.ok else 'FAIL'}  {r.name}")
    print("=" * min(width, 78))

    if not failed:
        print(f"\nVERIFY PASS — {len(results)} checks in {elapsed:.0f}s. Safe to push.")
        return 0

    print(f"\nVERIFY FAIL — {len(failed)} of {len(results)} checks failed "
          f"in {elapsed:.0f}s.\n")
    for r in failed:
        print(f"  {r.name}")
        if r.remedy:
            for line in r.remedy.splitlines():
                print(f"    {line}")
        print()
    print("Do not push until these pass. CI runs the same checks and will fail "
          "on the same things.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
