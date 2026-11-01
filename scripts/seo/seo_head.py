#!/usr/bin/env python3
"""Keep each published page's link-preview image and structured data current.

Reads scripts/seo/pages.json and, for every page listed there:

  * points og:image and twitter:image at that page's own card
    (assets/og/<slug>.png, rendered by build_og_images.cjs) and sets the alt
    text from the same row, so the image and its description agree;
  * writes one generated JSON-LD block between `seo:structured-data` markers:
      - an Organization node on every page (the project, with its founder);
      - a TechArticle on reference pages (type "article");
      - a BreadcrumbList on every page except the home page.
    Existing hand-written JSON-LD (WebSite, Person, SoftwareSourceCode,
    FAQPage, ProfilePage) is left exactly as it is.

No Product markup: docs/claim-boundaries.md does not allow presenting the
project as a product. No dates: a datePublished from a shallow CI checkout
would be wrong, and a wrong date is worse than none.

    python scripts/seo/seo_head.py          # write
    python scripts/seo/seo_head.py --check  # exit 1 if any page is stale
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "https://nhid-clinical.org"
TABLE = json.loads((Path(__file__).with_name("pages.json")).read_text(encoding="utf-8"))
START, END = "<!-- seo:structured-data -->", "<!-- /seo:structured-data -->"

PERSON = {
    "@type": "Person",
    "@id": f"{ORIGIN}/about.html#brianna-baynard",
    "name": "Brianna Baynard",
    "url": f"{ORIGIN}/about.html",
}
ORGANIZATION = {
    "@type": "Organization",
    "@id": f"{ORIGIN}/#organization",
    "name": "NHID-Clinical",
    "url": f"{ORIGIN}/",
    "logo": {
        "@type": "ImageObject",
        "url": f"{ORIGIN}/assets/brand/renders/nhid-nmark.png",
        "width": 655,
        "height": 765,
    },
    "description": (
        "An independent research project and open reference implementation for "
        "disclosure and authorization of AI voice agents on healthcare payer calls. "
        "Not a standard, a certification or a product."),
    "founder": {"@id": PERSON["@id"]},
    "sameAs": ["https://github.com/NHID-Clinical"],
}


def url_of(route: str) -> str:
    return f"{ORIGIN}/" + ("" if route == "index.html" else route)


def image_of(row: dict) -> str:
    return f"{ORIGIN}/assets/og/{row['slug']}.png"


def alt_of(row: dict) -> str:
    return f"NHID-Clinical {row['kicker']}: {row['headline']}"


def meta_content(text: str, attr: str, name: str) -> str:
    m = re.search(rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', text)
    if not m:
        raise SystemExit(f"missing <meta {attr}={name!r}>")
    return html.unescape(m.group(1))


def h1_text(text: str) -> str:
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).strip()


def graph(route: str, row: dict, text: str) -> dict:
    nodes = [dict(ORGANIZATION), PERSON]
    if row["type"] == "article":
        nodes.append({
            "@type": "TechArticle",
            "@id": url_of(route) + "#article",
            "headline": h1_text(text)[:110],
            "description": meta_content(text, "name", "description"),
            "url": url_of(route),
            "mainEntityOfPage": url_of(route),
            "image": image_of(row),
            "inLanguage": "en",
            "author": {"@id": PERSON["@id"]},
            "publisher": {"@id": ORGANIZATION["@id"]},
            "isPartOf": {"@id": f"{ORIGIN}/#website"},
        })
    if route != "index.html":
        nodes.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{ORIGIN}/"},
                {"@type": "ListItem", "position": 2, "name": row["kicker"], "item": url_of(route)},
            ],
        })
    return {"@context": "https://schema.org", "@graph": nodes}


def render(route: str, row: dict, text: str) -> str:
    out = text
    image, alt = image_of(row), html.escape(alt_of(row), quote=True)
    out = re.sub(r'(<meta property="og:image" content=")[^"]*(")', rf"\g<1>{image}\2", out)
    out = re.sub(r'(<meta name="twitter:image" content=")[^"]*(")', rf"\g<1>{image}\2", out)
    out = re.sub(r'(<meta property="og:image:alt" content=")[^"]*(")', lambda m: m.group(1) + alt + m.group(2), out)
    if 'name="twitter:image:alt"' in out:
        out = re.sub(r'(<meta name="twitter:image:alt" content=")[^"]*(")', lambda m: m.group(1) + alt + m.group(2), out)
    else:
        out = re.sub(r'(\s*)(<meta name="twitter:image" content="[^"]*"\s*/?>)',
                     lambda m: f'{m.group(1)}{m.group(2)}{m.group(1)}<meta name="twitter:image:alt" content="{alt}"/>',
                     out, count=1)

    block = json.dumps(graph(route, row, out), indent=2, ensure_ascii=False)
    script = f'{START}\n  <script type="application/ld+json">\n{block}\n  </script>\n  {END}'
    if START in out:
        out = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: script, out, flags=re.S)
    else:
        out = out.replace("</head>", f"  {script}\n</head>", 1)
    return out


def main(check: bool) -> int:
    stale = []
    for route, row in TABLE.items():
        if route.startswith("_"):
            continue
        path = ROOT / route
        card = ROOT / "assets" / "og" / f"{row['slug']}.png"
        if not card.is_file():
            stale.append(f"{route}: missing card {card.relative_to(ROOT)} "
                         f"(run node scripts/seo/build_og_images.cjs)")
            continue
        text = path.read_text(encoding="utf-8")
        new = render(route, row, text)
        if new != text:
            if check:
                stale.append(route)
            else:
                path.write_text(new, encoding="utf-8")
                print(f"  updated {route}")
    if stale:
        print("SEO HEAD STALE: " + ", ".join(stale) + " (run python scripts/seo/seo_head.py)")
        return 1
    if check:
        print(f"SEO HEAD PASS: {len([r for r in TABLE if not r.startswith('_')])} pages current")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
