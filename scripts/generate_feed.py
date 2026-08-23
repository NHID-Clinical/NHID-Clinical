#!/usr/bin/env python3
"""
NHID-Clinical — Atom feed generator
===================================
Generates `feed.xml` from `news.html`, so the project has a following mechanism
that belongs to the project rather than to a platform account.

`news.html` is the single source of truth. This script parses the entries
already published there and emits an Atom 1.0 document; it never carries its
own copy of the news text, so the two cannot drift.

Design notes:

  * **Atom, not RSS 2.0.** Atom requires an explicit `<updated>` and a globally
    unique `<id>` per entry, both of which matter for a feed whose entries are
    dated by month rather than by timestamp.
  * **Stable entry IDs.** The id is a `tag:` URI derived from the entry title,
    so re-generating the feed does not churn ids and re-notify subscribers.
  * **Month-precision dates.** The news page dates entries by month. Rather than
    invent a day and time the source does not have, each entry is dated to the
    first of its month at 00:00:00Z, which is stable across regenerations.
  * **No claims of its own.** Entry content is the published summary text,
    escaped. The generator adds no wording that is not already on the page.

Usage:
    python scripts/generate_feed.py            # writes feed.xml
    python scripts/generate_feed.py --check    # verify without writing
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_HTML = ROOT / "news.html"
FEED_XML = ROOT / "feed.xml"

SITE = "https://nhid-clinical.org"
FEED_URL = f"{SITE}/feed.xml"
NEWS_URL = f"{SITE}/news.html"
TITLE = "NHID-Clinical"
SUBTITLE = (
    "Release notes and updates from NHID-Clinical — an open policy-and-evidence "
    "layer for healthcare administrative AI voice interactions."
)
AUTHOR = "NHID-Clinical"
# tagURI per RFC 4151. The date is the domain-ownership date component and is
# deliberately fixed: it identifies the naming authority, not the entry.
TAG_BASE = "tag:nhid-clinical.org,2026:news"

_MONTHS = {
    m: i
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"],
        start=1,
    )
}

_ARTICLE = re.compile(r'<article class="news-card">(.*?)</article>', re.S)
_BADGE = re.compile(r'<span class="news-badge[^"]*">(.*?)</span>', re.S)
_DATE = re.compile(r'<time class="news-date">(.*?)</time>', re.S)
_TITLE = re.compile(r"<h2>(.*?)</h2>", re.S)
_PARA = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_TAGS = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Entry:
    title: str
    category: str
    summary: str
    published: datetime

    @property
    def entry_id(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return f"{TAG_BASE}:{self.published:%Y-%m}:{slug}"


def _text(fragment: str) -> str:
    """Strip tags and unescape entities, collapsing whitespace."""
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub("", fragment))).strip()


def _parse_month(value: str) -> datetime:
    """'August 2026' -> 2026-08-01T00:00:00Z. Raises on an unparseable date."""
    parts = _text(value).split()
    if len(parts) != 2 or parts[0] not in _MONTHS:
        raise ValueError(f"unrecognised news date: {value!r}")
    return datetime(int(parts[1]), _MONTHS[parts[0]], 1, tzinfo=timezone.utc)


def parse_news(html_text: str) -> list[Entry]:
    """Extract entries from news.html in document order (newest first)."""
    entries: list[Entry] = []
    for block in _ARTICLE.findall(html_text):
        title_m = _TITLE.search(block)
        date_m = _DATE.search(block)
        if not title_m or not date_m:
            continue
        badge_m = _BADGE.search(block)
        paras = _PARA.findall(block)
        entries.append(
            Entry(
                title=_text(title_m.group(1)),
                category=_text(badge_m.group(1)) if badge_m else "Update",
                summary=_text(paras[0]) if paras else "",
                published=_parse_month(date_m.group(1)),
            )
        )
    return entries


def build_feed(entries: list[Entry], updated: datetime | None = None) -> str:
    """Render an Atom 1.0 document. Deterministic apart from `updated`."""
    # Feed-level `updated` is the newest entry's date, not the build time, so
    # regenerating an unchanged news page produces a byte-identical feed.
    if updated is None:
        updated = max((e.published for e in entries), default=datetime(
            2026, 1, 1, tzinfo=timezone.utc))

    def esc(s: str) -> str:
        return html.escape(s, quote=False)

    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{esc(TITLE)}</title>",
        f"  <subtitle>{esc(SUBTITLE)}</subtitle>",
        f'  <link href="{FEED_URL}" rel="self" type="application/atom+xml"/>',
        f'  <link href="{NEWS_URL}" rel="alternate" type="text/html"/>',
        f"  <id>{TAG_BASE}</id>",
        f"  <updated>{updated:%Y-%m-%dT%H:%M:%SZ}</updated>",
        f"  <author><name>{esc(AUTHOR)}</name><uri>{SITE}</uri></author>",
        "  <rights>CC BY 4.0</rights>",
        f'  <generator uri="{SITE}">scripts/generate_feed.py</generator>',
    ]
    for e in entries:
        parts += [
            "  <entry>",
            f"    <title>{esc(e.title)}</title>",
            f'    <link href="{NEWS_URL}" rel="alternate" type="text/html"/>',
            f"    <id>{esc(e.entry_id)}</id>",
            f"    <updated>{e.published:%Y-%m-%dT%H:%M:%SZ}</updated>",
            f"    <published>{e.published:%Y-%m-%dT%H:%M:%SZ}</published>",
            f'    <category term="{esc(e.category)}"/>',
            f"    <summary>{esc(e.summary)}</summary>",
            "  </entry>",
        ]
    parts.append("</feed>")
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the Atom feed from news.html.")
    ap.add_argument("--check", action="store_true",
                    help="fail if feed.xml is missing or out of date; write nothing")
    args = ap.parse_args(argv)

    if not NEWS_HTML.exists():
        print(f"ERROR: {NEWS_HTML} not found", file=sys.stderr)
        return 1

    entries = parse_news(NEWS_HTML.read_text(encoding="utf-8"))
    if not entries:
        print("ERROR: no news entries parsed — has news.html's markup changed?",
              file=sys.stderr)
        return 1

    feed = build_feed(entries)

    if args.check:
        if not FEED_XML.exists():
            print("FEED FAIL: feed.xml does not exist. Run scripts/generate_feed.py.",
                  file=sys.stderr)
            return 1
        if FEED_XML.read_text(encoding="utf-8") != feed:
            print("FEED FAIL: feed.xml is stale relative to news.html. "
                  "Run scripts/generate_feed.py and commit the result.",
                  file=sys.stderr)
            return 1
        print(f"FEED PASS: feed.xml matches news.html ({len(entries)} entries)")
        return 0

    FEED_XML.write_text(feed, encoding="utf-8")
    print(f"Wrote {FEED_XML.relative_to(ROOT)} — {len(entries)} entries, "
          f"newest {max(e.published for e in entries):%Y-%m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
