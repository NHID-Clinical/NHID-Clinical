#!/usr/bin/env python3
"""Make the built Pages artifact render sooner, without changing the source.

Runs on `_site` only, from scripts/build_pages_site.sh. The repository keeps its
separate stylesheets (tests/test_site_navigation.py checks their order and that
drafting.css loads last); the published copy gets:

  1. One stylesheet per page instead of five or six. Each page's local
     stylesheets are concatenated in their original order, comments and blank
     space removed, into assets/css/bundle.<hash>.css. Same order, same rules:
     the cascade is unchanged. The hash is of the content, so a changed rule
     gets a new URL and no browser keeps a stale copy.
  2. Google Fonts loaded without blocking first paint. The stylesheet is
     preloaded and applied on load (display=swap is already in the URL), with a
     <noscript> copy so a browser without scripting still gets the fonts.

Lighthouse found both on every page (render-blocking resources, about 2 s of
the mobile budget). Usage: optimize_build.py <_site>
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

LOCAL_SHEET = re.compile(r'<link rel="stylesheet" href="(/[^"#?]+\.css)"\s*/?>')
GOOGLE_FONTS = re.compile(
    r'<link href="(https://fonts\.googleapis\.com/css2\?[^"]+)" rel="stylesheet"\s*/?>')
SKIP_DIRS = ("assets/", "content/", "conformance/")


def minify(css: str) -> str:
    """Conservative: drop comments and blank space between declarations only.
    No property rewriting, so the result is the same rules in the same order."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    lines = (line.strip() for line in css.splitlines())
    return "\n".join(line for line in lines if line) + "\n"


def bundle(site: Path, hrefs: list[str], cache: dict) -> str:
    key = tuple(hrefs)
    if key not in cache:
        parts = []
        for href in hrefs:
            src = site / href.lstrip("/")
            parts.append(f"/* {href} */\n" + minify(src.read_text(encoding="utf-8")))
        text = "".join(parts)
        digest = hashlib.sha256(text.encode()).hexdigest()[:10]
        out = site / "assets" / "css" / f"bundle.{digest}.css"
        out.write_text(text, encoding="utf-8")
        cache[key] = f"/assets/css/bundle.{digest}.css"
    return cache[key]


def optimize_page(site: Path, page: Path, cache: dict) -> bool:
    html = page.read_text(encoding="utf-8")
    head_end = html.find("</head>")
    if head_end < 0:
        return False
    head, rest = html[:head_end], html[head_end:]
    changed = False

    sheets = LOCAL_SHEET.findall(head)
    if len(sheets) >= 2 and all((site / h.lstrip("/")).is_file() for h in sheets):
        href = bundle(site, sheets, cache)
        first = True

        def swap(m: re.Match) -> str:
            nonlocal first
            if first:
                first = False
                return f'<link rel="stylesheet" href="{href}"/>'
            return ""

        head = LOCAL_SHEET.sub(swap, head)
        changed = True

    def fonts(m: re.Match) -> str:
        url = m.group(1)
        return (f'<link rel="preload" as="style" href="{url}" '
                f'onload="this.onload=null;this.rel=\'stylesheet\'"/>'
                f'<noscript><link rel="stylesheet" href="{url}"/></noscript>')

    head, n = GOOGLE_FONTS.subn(fonts, head)
    changed = changed or bool(n)

    if changed:
        head = re.sub(r"\n[ \t]*\n", "\n", head)
        page.write_text(head + rest, encoding="utf-8")
    return changed


def main(site_dir: str) -> int:
    site = Path(site_dir)
    cache: dict = {}
    count = 0
    for page in sorted(site.rglob("*.html")):
        rel = page.relative_to(site).as_posix()
        if rel.startswith(SKIP_DIRS):
            continue
        count += optimize_page(site, page, cache)
    print(f"  optimized {count} pages into {len(cache)} stylesheet bundle(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "_site"))
