#!/usr/bin/env python3
"""Diff two computed-style snapshots. Exit 1 if anything renders differently.

  python scripts/visual/diff_style_snapshots.py before.json after.json
"""
import json
import sys


def main():
    a = json.loads(open(sys.argv[1]).read())
    b = json.loads(open(sys.argv[2]).read())

    diffs = []
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    for key in sorted(set(a) & set(b)):
        ea, eb = a[key], b[key]
        for path in sorted(set(ea) - set(eb)):
            diffs.append(f"{key} :: {path} :: element disappeared")
        for path in sorted(set(eb) - set(ea)):
            diffs.append(f"{key} :: {path} :: element appeared")
        for path in sorted(set(ea) & set(eb)):
            for prop, va in ea[path].items():
                vb = eb[path].get(prop)
                if va != vb:
                    diffs.append(f"{key} :: {path} :: {prop}: {va!r} -> {vb!r}")

    for k in only_a:
        diffs.append(f"page/viewport missing from the second snapshot: {k}")
    for k in only_b:
        diffs.append(f"page/viewport only in the second snapshot: {k}")

    elems = sum(len(v) for v in a.values())
    for d in diffs[:40]:
        print("  " + d)
    if len(diffs) > 40:
        print(f"  ... and {len(diffs) - 40} more")
    verdict = "FAIL" if diffs else "PASS"
    print(f"STYLE {verdict}: {elems} elements across {len(a)} page/viewport pairs, "
          f"{len(diffs)} computed-style differences")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
