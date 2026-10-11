#!/usr/bin/env python3
"""
NHID-Clinical Tier 0 pilot measurement script
==============================================
Replays captured call turns through the real policy engine and reports the
Tier 0 pilot metrics. Reads capture-schema JSONL (one record per call turn —
see docs/pilot-kit/minimal-event-schema.json).

Usage:
  python docs/pilot-kit/measure_pilot.py calls.jsonl
  python docs/pilot-kit/measure_pilot.py calls.jsonl --results-dir out/
  python docs/pilot-kit/measure_pilot.py --demo

With --results-dir, one conformance-result JSON per call is written in the
format `tools/pilot_report_generator.py` consumes, so a markdown pilot report
is one more command:
  python tools/pilot_report_generator.py out/ pilot_report.md

Or produce the whole evidence pack — report, PDF and metrics — in one command:
  nhid pilot calls.jsonl --out pilot-evidence/

THIS FILE IS A SHIM, ON PURPOSE
-------------------------------
The measurement logic lives in `src/pilot_measure.py`. It moved there so the
kit could be one installed command instead of a path into a checkout: a file
under `docs/` is not an importable module. This shim stays because its command
line is written down in the kit README, the Playbook and on the website, and
breaking a documented command to tidy a layout is not a trade worth making.
Both entry points call the same functions, so they cannot report different
numbers.

SENDS NOTHING. Guarded by `scripts/check_offline_kit.py`.

NHID-Clinical is a voluntary open proposal. This script is licensed
Apache-2.0 (see LICENSE); the control text it measures against is CC BY 4.0
(see LICENSE-DOCS).
Metrics are measurements, not conformance certifications.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Run from the repo root; make the repo importable when invoked by path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pilot_measure import (  # noqa: E402
    demo_records, load_jsonl, measure_records, print_summary,
    write_per_call_results,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("jsonl", nargs="?", help="capture-schema JSONL file (one record per turn)")
    parser.add_argument("--demo", action="store_true", help="run against three built-in demo calls")
    parser.add_argument("--results-dir", help="write per-call conformance JSONs for tools/pilot_report_generator.py")
    parser.add_argument("--json", action="store_true", help="print the aggregate summary as JSON")
    args = parser.parse_args()

    if args.demo:
        records = demo_records()
    elif args.jsonl:
        records = load_jsonl(args.jsonl)
    else:
        parser.error("provide a JSONL file or --demo")

    calls, summary = measure_records(records)

    if args.results_dir:
        out = Path(args.results_dir)
        written = write_per_call_results(calls, out)
        print(f"Wrote {written} per-call results to {out}/ "
              f"(next: python tools/pilot_report_generator.py {out}/ pilot_report.md)")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
