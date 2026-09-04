#!/usr/bin/env python3
"""
NHID-Clinical — Atom feed generator
===================================
Generates `feed.xml` from `docs/release-history.md`, so the project has a
following mechanism that belongs to the project rather than to a platform
account.

`docs/release-history.md` is the single source of truth. This script parses the
entries already published there and emits an Atom 1.0 document; it never carries
its own copy of the release text, so the two cannot drift.

The source was `news.html` until the Phase B IA consolidation (2026-09-05)
retired that route: a changelog is something people check, not a destination
they arrive at, so it failed the destination test in `ia-disposition.md` §4.3.
Retiring the route without moving the generator would have silently killed the
feed, so the generator moved with the content. Entry links now point at the
release history on GitHub, which is where the record actually lives.

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
RELEASE_HISTORY = ROOT / "docs" / "release-history.md"
FEED_XML = ROOT / "feed.xml"

SITE = "https://nhid-clinical.org"
FEED_URL = f"{SITE}/feed.xml"
NEWS_URL = "https://github.com/NHID-Clinical/NHID-Clinical/blob/main/docs/release-history.md"
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

# An entry in the release history is an H2 followed by an italic
# "*Month Year · Category*" line and then its prose. Anything before the first
# H2 is front matter (the move note and the annotation table) and is skipped.
_ENTRY = re.compile(
    r"^## +(?P<title>.+?)\s*$\n+\*(?P<month>[A-Z][a-z]+ \d{4})\s*·\s*(?P<category>[^*]+?)\*\s*$"
    r"(?P<rest>.*?)(?=^## |\Z)",
    re.M | re.S,
)
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_EMPH = re.compile(r"[*_`]+")
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


def _first_paragraph(rest: str) -> str:
    """The entry's first prose paragraph, as plain text.

    Skips blank lines, block quotes and tables so the summary is the entry's
    own sentence rather than a piece of an annotation.
    """
    for para in re.split(r"\n\s*\n", rest.strip()):
        line = para.strip()
        if not line or line.startswith((">", "|", "#", "-", "*   ")):
            continue
        text = _MD_LINK.sub(r"\1", line)
        text = _MD_EMPH.sub("", _TAGS.sub("", text))
        return re.sub(r"\s+", " ", text).strip()
    return ""


def parse_news(source_text: str) -> list[Entry]:
    """Extract entries from the release history in document order (newest first)."""
    entries: list[Entry] = []
    for m in _ENTRY.finditer(source_text):
        entries.append(
            Entry(
                title=_MD_EMPH.sub("", m.group("title")).strip(),
                category=m.group("category").strip() or "Update",
                summary=_first_paragraph(m.group("rest")),
                published=_parse_month(m.group("month")),
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
    ap = argparse.ArgumentParser(
        description="Generate the Atom feed from docs/release-history.md.")
    ap.add_argument("--check", action="store_true",
                    help="fail if feed.xml is missing or out of date; write nothing")
    args = ap.parse_args(argv)

    if not RELEASE_HISTORY.exists():
        print(f"ERROR: {RELEASE_HISTORY} not found", file=sys.stderr)
        return 1

    entries = parse_news(RELEASE_HISTORY.read_text(encoding="utf-8"))
    if not entries:
        print("ERROR: no entries parsed — has docs/release-history.md's "
              "heading format changed?", file=sys.stderr)
        return 1

    feed = build_feed(entries)

    if args.check:
        if not FEED_XML.exists():
            print("FEED FAIL: feed.xml does not exist. Run scripts/generate_feed.py.",
                  file=sys.stderr)
            return 1
        if FEED_XML.read_text(encoding="utf-8") != feed:
            print("FEED FAIL: feed.xml is stale relative to "
                  "docs/release-history.md. "
                  "Run scripts/generate_feed.py and commit the result.",
                  file=sys.stderr)
            return 1
        print(f"FEED PASS: feed.xml matches docs/release-history.md "
              f"({len(entries)} entries)")
        return 0

    FEED_XML.write_text(feed, encoding="utf-8")
    print(f"Wrote {FEED_XML.relative_to(ROOT)} — {len(entries)} entries, "
          f"newest {max(e.published for e in entries):%Y-%m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
