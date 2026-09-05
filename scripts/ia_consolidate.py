#!/usr/bin/env python3
"""Retire a route to a redirect stub, matching the repository's existing pattern.

Phase B (IA consolidation). Every retired route keeps a stub so existing links,
bookmarks and search results resolve rather than 404. The stub markup is copied
from the pattern already in `pilot.html` and `conformance.html` so retired routes
behave identically whether they were retired before or during this phase.
"""
from __future__ import annotations
import pathlib
import sys

STUB = """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0; url={target}">
  <link rel="canonical" href="https://nhid-clinical.org{target}">
  <title>Redirecting…</title>
  <script defer data-domain="nhid-clinical.org" src="https://plausible.io/js/script.js"></script>
  <link rel="alternate" type="application/atom+xml" title="NHID-Clinical news" href="/feed.xml"/>
</head>
<body>
  <script>window.location.replace("{target}");</script>
  <p>This page has moved to <a href="{target}">{label}</a>.</p>
</body>
</html>
"""


def retire(route: str, target: str, label: str) -> None:
    p = pathlib.Path(route)
    if not p.exists():
        raise SystemExit(f"{route}: does not exist")
    p.write_text(STUB.format(target=target, label=label))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: ia_consolidate.py <route> <target> <label>")
    retire(*sys.argv[1:])
    print(f"retired {sys.argv[1]} -> {sys.argv[2]}")
