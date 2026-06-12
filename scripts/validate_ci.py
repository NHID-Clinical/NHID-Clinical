#!/usr/bin/env python3
import re, subprocess, sys
UNIT_EXPECTED = 219
INTEGRATION_EXPECTED = 18
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
    v=[]
    if counts["passed"]!=UNIT_EXPECTED: v.append(f"FAIL: expected {UNIT_EXPECTED} passed, got {counts['passed']}")
    if counts["failed"]>0: v.append(f"FAIL: {counts['failed']} test(s) failed")
    if counts["error"]>0: v.append(f"FAIL: {counts['error']} collection error(s)")
    if counts["skipped"] not in (0,INTEGRATION_EXPECTED): v.append(f"FAIL: unexpected skip count {counts['skipped']}")
    return v
def main():
    print("Running NHID-Clinical test invariant check...")
    output,_=run_pytest()
    counts=parse_summary(output)
    if not any(counts.values()): print("ERROR: could not parse pytest summary"); print(output); sys.exit(1)
    violations=validate(counts)
    if not violations: print(f"CI PASS: {counts['passed']} passed"); sys.exit(0)
    else:
        for v in violations: print(v)
        print("CI FAIL"); sys.exit(1)
if __name__=="__main__": main()
