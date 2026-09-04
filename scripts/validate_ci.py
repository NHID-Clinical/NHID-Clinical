#!/usr/bin/env python3
"""
NHID-Clinical CI Validation

Validates test suite health by verifying:
- All tests execute successfully (no collection errors)
- No test failures
- Nothing is silently skipped

Does NOT enforce an exact historical test count, since the suite grows legitimately
with new controls and features. CI validates correctness of execution, not linecount.

Suite shape, as of 2026-09-03
-----------------------------
Until this date the suite reported 987 passed and 18 skipped. Those 18 skipped
because nothing was listening on the API port, and CI never started a server --
so they had never once executed. Running them revealed 11 passes and 7 genuine
divergences between the harness and app.py. Both underlying contracts were then
resolved (docs/skipped-test-audit.md section 8), so the divergences are gone
rather than marked:

  * a missing or empty CallSid no longer becomes a shared literal; and
  * /debug/replay is settled as an inspection contract, on the repository's own
    evidence, rather than a replay engine being built to satisfy a test.

The suite now reports 1110 passed, 0 skipped, 0 xfailed, 0 xpassed against a
live API. Run it without one and 18 tests skip, which is why a nonzero skip
count is worth warning about: it means the integration tests did not run.
"""
import re, subprocess, sys

# Expected skipped count. Zero is the point: a skip here means the API was not
# running and 18 tests silently did not execute.
SKIP_EXPECTED = 0

# Zero, and it should stay zero. The seven divergences that briefly lived here
# were resolved by fixing the contracts they marked, not by keeping markers on
# them. A nonzero value means someone has started deferring a failure again.
XFAIL_EXPECTED = 0

# The unit-test count currently published on public surfaces (README badge,
# website stats, PDFs). This is NOT a CI gate — the suite is allowed to grow
# without failing the build. It exists so scripts/check_number_drift.py has a
# canonical number to compare published claims against. Update it in the same
# commit as any change to the published count.
UNIT_PUBLISHED = 1110

def run_pytest():
    result = subprocess.run([sys.executable,"-m","pytest","tests/","-q","--tb=short","--no-header"],capture_output=True,text=True)
    return result.stdout+result.stderr, result.returncode

def parse_summary(output):
    """Read pytest's terminal summary line, whatever order the outcomes appear in."""
    counts = {"passed":0,"skipped":0,"failed":0,"error":0,"xfailed":0,"xpassed":0}
    aliases = {"error":"error","errors":"error"}
    for line in output.splitlines():
        if "passed" not in line and "failed" not in line and "error" not in line:
            continue
        found = re.findall(r"(\d+)\s+(passed|failed|skipped|xfailed|xpassed|errors?)", line)
        if not found:
            continue
        for n, word in found:
            counts[aliases.get(word, word)] = int(n)
    return counts

def validate(counts):
    """Validate test execution health. Fail on errors/failures, warn on shape drift."""
    v=[]
    # Fail on actual failures
    if counts["failed"]>0: v.append(f"FAIL: {counts['failed']} test(s) failed")
    # Fail on collection errors
    if counts["error"]>0: v.append(f"FAIL: {counts['error']} collection error(s)")
    # Warn on unexpected skips. A skip here almost always means "no API running",
    # which silently removes the 18 integration tests from the run.
    if counts["skipped"] != SKIP_EXPECTED:
        print(
            f"WARNING: expected {SKIP_EXPECTED} skipped tests, got {counts['skipped']}. "
            f"If this is 18, the API was not running and the integration tests did "
            f"not execute — start it with: python -m uvicorn app:app --port 8000"
        )
    # Warn when the recorded divergences change shape.
    if counts["xfailed"] != XFAIL_EXPECTED:
        print(
            f"WARNING: expected {XFAIL_EXPECTED} xfailed tests, got {counts['xfailed']}. "
            f"See docs/skipped-test-audit.md §8 — a deferred failure has reappeared."
        )
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
        print(
            f"CI PASS: {counts['passed']} tests passed "
            f"({counts['xfailed']} xfailed, {counts['skipped']} skipped)"
        )
        sys.exit(0)
    else:
        for v in violations: print(v)
        print("CI FAIL")
        sys.exit(1)

if __name__=="__main__": main()
