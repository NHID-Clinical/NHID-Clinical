#!/usr/bin/env python3
"""
NHID-Clinical CI Validation

Validates test suite health by verifying:
- All tests execute successfully (no collection errors)
- No test failures
- Expected integration tests are skipped (18)

Does NOT enforce an exact historical test count, since the suite grows legitimately
with new controls and features. CI validates correctness of execution, not linecount.
"""
import re, subprocess, sys

# Expected skipped count: integration tests that require external resources
INTEGRATION_EXPECTED = 18

# The unit-test count currently published on public surfaces (README badge,
# website stats, PDFs). This is NOT a CI gate — the suite is allowed to grow
# without failing the build. It exists so scripts/check_number_drift.py has a
# canonical number to compare published claims against. Update it in the same
# commit as any change to the published count.
UNIT_PUBLISHED = 759

def run_pytest():
    result = subprocess.run([sys.executable,"-m","pytest","tests/","-q","--tb=short","--no-header"],capture_output=True,text=True)
    return result.stdout+result.stderr, result.returncode

def parse_summary(output):
    pattern = re.compile(r"(?:(\d+) failed,?\s*)?(?:(\d+) error,?\s*)?(\d+) passed(?:,\s*(\d+) skipped)?",re.IGNORECASE)
    counts = {"passed":0,"skipped":0,"failed":0,"error":0}
    for line in output.splitlines():
        m = pattern.search(line)
        if m and "passed" in line:
            counts["failed"]=int(m.group(1) or 0);counts["error"]=int(m.group(2) or 0)
            counts["passed"]=int(m.group(3) or 0);counts["skipped"]=int(m.group(4) or 0)
    return counts

def validate(counts):
    """Validate test execution health. Fail on errors/failures, warn on unexpected skips."""
    v=[]
    # Fail on actual failures
    if counts["failed"]>0: v.append(f"FAIL: {counts['failed']} test(s) failed")
    # Fail on collection errors
    if counts["error"]>0: v.append(f"FAIL: {counts['error']} collection error(s)")
    # Warn (but don't fail) on unexpected skip counts
    if counts["skipped"] != INTEGRATION_EXPECTED:
        print(f"WARNING: expected {INTEGRATION_EXPECTED} skipped tests, got {counts['skipped']}")
    # Warn (but don't fail) when the published count no longer matches reality.
    # check_number_drift.py only enforces that published surfaces agree with
    # UNIT_PUBLISHED — they can all be consistently wrong, which is how a
    # superseded count survived across the whole repository once already.
    # Deliberately a warning, not a gate: the suite is allowed to grow without
    # breaking the build, but the staleness must not be silent.
    if counts["passed"] != UNIT_PUBLISHED:
        print(
            f"WARNING: suite now reports {counts['passed']} passing but "
            f"UNIT_PUBLISHED is {UNIT_PUBLISHED}. Published surfaces are stale — "
            f"update UNIT_PUBLISHED and every surface in the same commit, then "
            f"re-run scripts/check_number_drift.py."
        )
    # Pass condition: tests executed, no failures, no errors
    return v

def main():
    print("Running NHID-Clinical test validation...")
    output,_=run_pytest()
    counts=parse_summary(output)
    if not any(counts.values()):
        print("ERROR: could not parse pytest summary")
        print(output)
        sys.exit(1)
    violations=validate(counts)
    if not violations:
        print(f"CI PASS: {counts['passed']} tests passed (+ {counts['skipped']} skipped)")
        sys.exit(0)
    else:
        for v in violations: print(v)
        print("CI FAIL")
        sys.exit(1)

if __name__=="__main__": main()
