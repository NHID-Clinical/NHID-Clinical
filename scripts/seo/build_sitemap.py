#!/usr/bin/env python3
"""Write sitemap.xml for the built Pages artifact.

Generated at build time from what is actually published, so it cannot drift
from the site: every HTML page in `_site` that is indexable, plus the published
PDFs. Left out, by rule rather than by list:

  * redirect stubs (they carry a meta refresh and noindex);
  * anything with a robots noindex;
  * search-console verification files.

No <lastmod>: the Pages workflow checks out one commit, so a date taken from git
there would be the same for every page, and a wrong lastmod is worse than none.

Usage: build_sitemap.py <_site>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ORIGIN = "https://nhid-clinical.org"
SKIP_DIRS = ("assets/", "content/", "conformance/")


def indexable(html: str) -> bool:
    head = html.split("</head>", 1)[0].lower()
    if 'http-equiv="refresh"' in head:
        return False
    robots = re.search(r'<meta name="robots" content="([^"]*)"', head)
    return not (robots and "noindex" in robots.group(1))


def urls(site: Path) -> list[str]:
    out = []
    for page in sorted(site.rglob("*.html")):
        rel = page.relative_to(site).as_posix()
        if rel.startswith(SKIP_DIRS):
            continue
        if re.fullmatch(r"google[0-9a-f]+\.html", rel):
            continue
        if not indexable(page.read_text(encoding="utf-8", errors="replace")):
            continue
        # A directory index is published, and canonicalized, as the directory.
        out.append(ORIGIN + "/" + re.sub(r"(^|/)index\.html$", r"\1", rel))
    for pdf in sorted((site / "specs").glob("*.pdf")):
        out.append(f"{ORIGIN}/specs/{pdf.name}")
    return out


def render(locs: list[str]) -> str:
    body = "".join(f"  <url><loc>{escape(u)}</loc></url>\n" for u in locs)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}</urlset>\n")


def main(site_dir: str) -> int:
    site = Path(site_dir)
    locs = urls(site)
    (site / "sitemap.xml").write_text(render(locs), encoding="utf-8")
    print(f"  sitemap.xml: {len(locs)} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "_site"))
