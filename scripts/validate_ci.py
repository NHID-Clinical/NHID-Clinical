#!/usr/bin/env python3
"""
NHID-Clinical CI invariant validator.

Hard rules (fail CI if violated):
  - Unit tests: exactly 72 passed, 0 unit tests skipped
  - No test failures
  - No collection errors

Soft rules (never block CI):
  - Integration suite: 18 tests, may pass or skip (expected)
"""
import re
import subprocess
import sys


UNIT_EXPECTED = 72
INTEGRATION_EXPECTED = 18


def run_pytest():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
    )
    return result.stdout + result.stderr, result.returncode


def parse_summary(output):
    # Matches lines like: "72 passed, 18 skipped in 0.31s"
    # or "1 failed, 71 passed, 18 skipped in 0.41s"
    # or "72 passed in 0.31s"
    pattern = re.compile(
        r"(?:(\d+) failed,?\s*)?"
        r"(?:(\d+) error,?\s*)?"
        r"(\d+) passed"
        r"(?:,\s*(\d+) skipped)?",
        re.IGNORECASE,
    )
    counts = {"passed": 0, "skipped": 0, "failed": 0, "error": 0}
    for line in output.splitlines():
        m = pattern.search(line)
        if m and "passed" in line:
            counts["failed"] = int(m.group(1) or 0)
            counts["error"] = int(m.group(2) or 0)
            counts["passed"] = int(m.group(3) or 0)
            counts["skipped"] = int(m.group(4) or 0)
    return counts


def validate(counts):
    violations = []

    # Hard: exactly 72 unit tests must pass
    if counts["passed"] != UNIT_EXPECTED:
        violations.append(
            f"FAIL: expected {UNIT_EXPECTED} passed, got {counts['passed']}"
        )

    # Hard: no failures
    if counts["failed"] > 0:
        violations.append(f"FAIL: {counts['failed']} test(s) failed")

    # Hard: no collection errors
    if counts["error"] > 0:
        violations.append(f"FAIL: {counts['error']} collection error(s)")

    # Hard: unit tests must not be skipped.
    # Total skipped must equal integration count only (0 or INTEGRATION_EXPECTED).
    if counts["skipped"] not in (0, INTEGRATION_EXPECTED):
        violations.append(
            f"FAIL: unexpected skip count {counts['skipped']} "
            f"(allowed: 0 when server running, {INTEGRATION_EXPECTED} when no server)"
        )

    return violations


def main():
    print("Running NHID-Clinical test invariant check...")
    output, _returncode = run_pytest()

    counts = parse_summary(output)
    if not any(counts.values()):
        print("ERROR: could not parse pytest summary output")
        print(output)
        sys.exit(1)

    violations = validate(counts)

    print()
    if not violations:
        print(f"Unit invariant preserved: {counts['passed']} passed, 0 skipped")
        print(
            f"Integration suite: {counts['skipped']} of {INTEGRATION_EXPECTED} tests "
            "skipped (expected when no server running)"
            if counts["skipped"]
            else f"Integration suite: {INTEGRATION_EXPECTED} tests, may pass or skip (expected)"
        )
        print()
        print("CI PASS")
        sys.exit(0)
    else:
        for v in violations:
            print(v)
        print()
        print("CI FAIL — unit invariant violated")
        sys.exit(1)


if __name__ == "__main__":
    main()
