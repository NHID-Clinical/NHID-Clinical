#!/usr/bin/env python3
"""
Operator CLI for docs/dbc01-human-review-sop.md's review queue
(nhid_event_store.dbc01_review_queue). Lists sessions a conformance check
routed for human review, and records the reviewer's disposition.

Usage:
  python3 scripts/resolve_dbc01_review.py --list
  python3 scripts/resolve_dbc01_review.py --resolve 3 --disposition false_positive --reviewer alice
  python3 scripts/resolve_dbc01_review.py --resolve 3 --disposition confirmed_impersonation \
      --reviewer alice --notes "escalated per org incident process"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import nhid_event_store as store  # noqa: E402


def _print_review(row: dict) -> None:
    print(
        f"[{row['id']}] session={row.get('session_id')!r} "
        f"trigger={row['trigger_reason']} severity={row.get('severity')} "
        f"cas_score={row.get('cas_score')} status={row['status']}"
    )
    if row.get("identity_assertion_text"):
        print(f"      identity_assertion_text: {row['identity_assertion_text'][:140]!r}")
    if row["status"] == "resolved":
        print(
            f"      disposition={row.get('disposition')} reviewer={row.get('reviewer')!r} "
            f"resolved_at={row.get('resolved_at')}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List pending reviews")
    parser.add_argument("--resolve", type=int, metavar="QUEUE_ID", help="Resolve a queued review")
    parser.add_argument(
        "--disposition",
        choices=sorted(store.REVIEW_DISPOSITIONS),
        help="Required with --resolve",
    )
    parser.add_argument("--reviewer", default="", help="Reviewer name/id")
    parser.add_argument("--notes", default="", help="Free-text reviewer notes")
    args = parser.parse_args()

    if not args.list and args.resolve is None:
        parser.error("specify --list or --resolve QUEUE_ID")

    if args.list:
        pending = store.list_pending_dbc01_reviews()
        if not pending:
            print("No pending reviews.")
        for row in pending:
            _print_review(row)

    if args.resolve is not None:
        if not args.disposition:
            parser.error("--resolve requires --disposition")
        try:
            row = store.resolve_dbc01_review(
                args.resolve, args.disposition, reviewer=args.reviewer, notes=args.notes
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)
        print("resolved:")
        _print_review(row)


if __name__ == "__main__":
    main()
