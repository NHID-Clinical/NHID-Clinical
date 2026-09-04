#!/usr/bin/env python3
"""
Merge one page's content into another as a section.

Every page here follows the same shape:

    <main id="main">
      <section class="inner-hero ...">  <h1> + lede </section>
      <section class="page-section"> ... </section>   * n
    </main>

Merging means taking the source's content sections, demoting their headings one
level so they nest under a new <h2>, and appending them inside the destination's
<main>. The source's <h1> becomes that <h2> and its lede becomes the section's
opening paragraph, so no writing is lost in the move.

Headings are demoted deepest-first (h4->h5, then h3->h4, then h2->h3). Doing it
the other way round demotes the same element twice: h2 becomes h3, and then the
h3 rule moves it again to h4.

This does not decide *what* to merge. It performs a merge that has already been
decided, and it refuses rather than guesses when a page does not match the shape.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERO = re.compile(r'<section class="inner-hero.*?</section>\s*', re.S)
H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)
LEDE = re.compile(r'<p class="lede[^"]*"[^>]*>(.*?)</p>', re.S | re.I)


def read_main(path: Path) -> str:
    t = path.read_text()
    m = re.search(r"<main\b[^>]*>(.*?)</main>", t, re.S | re.I)
    if not m:
        sys.exit(f"{path}: no <main> element; refusing to guess its content")
    return m.group(1)


def source_parts(path: Path) -> tuple[str, str, str]:
    """Return (title, lede_html, body_html) for a source page.

    Two shapes exist. The standard page wraps its title in an inner-hero
    section. The `alignment/` stubs do not -- they are a bare <h1>, a sentence,
    and a table. Rather than force the second into the first, each is read on
    its own terms; the tool refuses only when a page matches neither.
    """
    main = read_main(path)
    hero = HERO.search(main)
    if not hero:
        h1 = H1.search(main)
        if not h1:
            sys.exit(f"{path}: neither an inner-hero nor an <h1>; refusing to guess")
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        body = H1.sub("", main, count=1)
        # The stubs end with a bare link back to the specification. Once the
        # content lives on a page that already links there, it is noise.
        body = re.sub(r'<p>\s*<a href="\.\./specification\.html">[^<]*</a>\s*</p>\s*', "", body)
        # Promote the leading sentence to the section lede.
        lead = re.search(r"\s*<p>(.*?)</p>", body, re.S)
        lede_html = ""
        if lead and "<table" not in lead.group(1):
            lede_html = lead.group(1).strip()
            body = body[:lead.start()] + body[lead.end():]
        return title, lede_html, body
    h1 = H1.search(hero.group(0))
    lede = LEDE.search(hero.group(0))
    body = HERO.sub("", main, count=1)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h1.group(1))).strip() if h1 else path.stem
    lede_html = lede.group(1).strip() if lede else ""
    return title, lede_html, body


def demote(html: str) -> str:
    for a, b in (("h4", "h5"), ("h3", "h4"), ("h2", "h3")):
        html = re.sub(rf"<{a}\b", f"<{b}", html)
        html = re.sub(rf"</{a}>", f"</{b}>", html)
    return html


def merge(src: Path, dest: Path, *, heading: str | None = None, anchor: str | None = None) -> None:
    title, lede, body = source_parts(src)
    heading = heading or title
    anchor = anchor or re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")

    lede_p = (
        f'\n      <p class="lede-text" style="color:var(--body);line-height:1.85">{lede}</p>'
        if lede else ""
    )
    block = (
        f'\n<!-- ── {heading} (merged from {src.name}) ───────────────────── -->\n'
        f'  <section class="page-section" id="{anchor}">\n'
        f'    <div class="container" style="max-width:860px">\n'
        f'      <h2>{heading}</h2>{lede_p}\n'
        f'    </div>\n'
        f'  </section>\n'
        f'{demote(body)}'
    )

    t = dest.read_text()
    close = t.rfind("</main>")
    if close == -1:
        sys.exit(f"{dest}: no </main>; refusing to append blindly")
    dest.write_text(t[:close] + block + "\n" + t[close:])
    print(f"merged {src}  ->  {dest}  as '{heading}' (#{anchor})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: merge_page.py SRC DEST [HEADING] [ANCHOR]")
    merge(
        Path(sys.argv[1]), Path(sys.argv[2]),
        heading=sys.argv[3] if len(sys.argv) > 3 else None,
        anchor=sys.argv[4] if len(sys.argv) > 4 else None,
    )
