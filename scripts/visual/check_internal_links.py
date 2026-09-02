#!/usr/bin/env python3
"""Resolve every internal href/src in the built site and report the ones that miss.

Runs against _site/ (the artefact GitHub Pages actually serves) rather than the
working tree, so a file that exists in the repo but is not copied by
scripts/build_pages_site.sh still shows up as broken -- which is what a visitor
would experience. External URLs, mailto:, tel:, data: and bare fragments are out
of scope; nothing here touches the network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "_site"

REF = re.compile(r"""\b(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
# Markup only. Inside <script> a fragment like "' + escapeHtml(e.website) + '"
# matches REF but is a runtime expression, not a reference the server ever sees.
SCRIPT = re.compile(r"<script\b.*?</script\s*>", re.I | re.S)
SKIP_SCHEME = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "//")


def resolve(page: Path, ref: str) -> Path | None:
    """Map one reference to the file the server would return, or None if N/A."""
    path = unquote(urlsplit(ref).path)
    if not path:
        return None                      # pure "#fragment" or "?query"
    base = SITE if path.startswith("/") else page.parent
    target = (base / path.lstrip("/")).resolve()
    if SITE not in target.parents and target != SITE:
        return None                      # escaped the site root; not ours to check
    return target


def exists(target: Path) -> bool:
    if target.is_file():
        return True
    if target.is_dir():                  # directory URLs serve index.html
        return (target / "index.html").is_file()
    return False


def main() -> int:
    if not SITE.is_dir():
        print("FAIL: _site/ not built. Run scripts/build_pages_site.sh first.")
        return 2

    checked = 0
    broken: list[tuple[Path, str]] = []
    for page in sorted(SITE.rglob("*.html")):
        markup = SCRIPT.sub("", page.read_text(errors="replace"))
        for quoted, single in REF.findall(markup):
            ref = quoted or single
            if not ref or ref.startswith(SKIP_SCHEME) or ref.startswith("#"):
                continue
            target = resolve(page, ref)
            if target is None:
                continue
            checked += 1
            if not exists(target):
                broken.append((page.relative_to(SITE), ref))

    for page, ref in broken:
        print(f"BROKEN  {page} -> {ref}")
    verdict = "FAIL" if broken else "PASS"
    print(f"LINKS {verdict}: {checked} internal references, {len(broken)} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
