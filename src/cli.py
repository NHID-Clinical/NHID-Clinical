"""
NHID-Clinical command-line interface
====================================
A thin dispatcher over functionality that already exists. It defines no policy,
computes no result, and holds no logic of its own — each subcommand calls the
same code the test suite exercises.

    nhid conformance            run the 18-case conformance suite
    nhid conformance --ci       ...and exit non-zero if any case fails
    nhid export-evidence --out DIR
                                assemble a reproducible evidence pack

The `--ci` flag exists so a vendor can gate their own pipeline on the controls
still behaving as specified after a change to their integration. A failing
build means a case that used to pass no longer does; it does not mean the
vendor is non-conformant with anything, and nothing here issues a pass/fail
judgement about a product.
"""
from __future__ import annotations

import argparse
import json
import sys


def _cmd_conformance(args: argparse.Namespace) -> int:
    from src.cts_runner import run_cts

    results = run_cts(yaml_path=args.suite, test_ids=args.test_id or None)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(
            f"Conformance: {results['passed']} passed, {results['failed']} failed, "
            f"{results['skipped']} skipped ({results['total']} cases)"
        )
        for case in results["results"]:
            if case["status"] == "fail":
                print(f"  FAIL {case['test_id']}: {case['detail']}")

    if args.ci and results["failed"]:
        print(
            f"\n{results['failed']} conformance case(s) failed. The controls no "
            f"longer behave as the suite specifies.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_export_evidence(args: argparse.Namespace) -> int:
    from scripts.export_evidence_pack import main as export_main

    argv = ["--out", args.out]
    if args.audit_db:
        argv += ["--audit-db", args.audit_db]
    if args.session_id:
        argv += ["--session-id", args.session_id]
    if args.audit_secret_key:
        argv += ["--audit-secret-key", args.audit_secret_key]
    if args.no_conformance:
        argv.append("--no-conformance")
    return export_main(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nhid",
        description=(
            "NHID-Clinical — policy and evidence tooling for healthcare "
            "administrative AI voice interactions."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    conf = sub.add_parser("conformance", help="run the conformance test suite")
    conf.add_argument("--ci", action="store_true", help="exit non-zero on any failure")
    conf.add_argument("--json", action="store_true", help="emit results as JSON")
    conf.add_argument("--suite", default=None, help="override the suite YAML path")
    conf.add_argument(
        "--test-id", action="append", default=None,
        help="run only this case (repeatable)",
    )
    conf.set_defaults(func=_cmd_conformance)

    exp = sub.add_parser("export-evidence", help="assemble an evidence pack")
    exp.add_argument("--out", required=True, help="output directory")
    exp.add_argument("--audit-db", default=None, help="path to the audit store")
    exp.add_argument("--session-id", default=None, help="session to export")
    exp.add_argument(
        "--audit-secret-key", default=None,
        help="hex HMAC key the audit events were signed with",
    )
    exp.add_argument("--no-conformance", action="store_true", help="skip the suite run")
    exp.set_defaults(func=_cmd_export_evidence)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
