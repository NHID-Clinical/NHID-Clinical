#!/usr/bin/env python3
"""Emit redirect stubs for every route the IA consolidation retired.

GitHub Pages serves static files and has no redirect table, so each retired
route becomes a small page that redirects. It carries three things rather than
one, because each covers a different reader:

  * <meta http-equiv="refresh"> moves a browser immediately;
  * <link rel="canonical"> tells a crawler which URL is authoritative, so the
    retired route does not compete with its destination in search;
  * a visible link, so the page still works with scripting disabled and anyone
    who lands on it can see where the content went rather than guessing.
"""
from __future__ import annotations

import sys
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moved &mdash; NHID-Clinical</title>
<link rel="canonical" href="{dest}">
<meta http-equiv="refresh" content="0; url={dest}">
<meta name="robots" content="noindex,follow">
<style>
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
         min-height: 100vh; display: grid; place-items: center; padding: 2rem;
         background: #fbfbfa; color: #14202a; }}
  main {{ max-width: 32rem; text-align: center; }}
  a {{ color: #0d7c86; font-weight: 600; }}
</style>
</head>
<body>
<main>
  <h1>This page has moved</h1>
  <p>Its content is now part of another page.</p>
  <p><a href="{dest}">Continue to {dest}</a></p>
</main>
</body>
</html>
"""


def main(out_dir: str) -> int:
    out = Path(out_dir)
    mapping = Path(__file__).with_name("redirects.txt")
    written = 0
    for line in mapping.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            route, dest = line.split("\t")
        except ValueError:
            print(f"malformed line (needs a tab): {line!r}", file=sys.stderr)
            return 1
        target = out / route
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(TEMPLATE.format(dest=dest))
        written += 1
    print(f"  redirects written: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "_site"))
