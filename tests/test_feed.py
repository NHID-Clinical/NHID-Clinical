"""
Atom feed — regression tests
============================
The feed is the project's platform-independent following mechanism, so the
properties that matter are: it is valid Atom, it derives from news.html rather
than carrying its own copy of the news, entry ids are stable across
regenerations, and it cannot silently go stale.
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.generate_feed import (
    FEED_XML,
    NEWS_HTML,
    TAG_BASE,
    Entry,
    build_feed,
    main,
    parse_news,
)

ATOM = {"a": "http://www.w3.org/2005/Atom"}
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def entries():
    return parse_news(NEWS_HTML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def feed_root():
    return ET.fromstring(FEED_XML.read_text(encoding="utf-8"))


# ── The feed exists and is valid Atom ──────────────────────────────────────

def test_feed_is_committed():
    assert FEED_XML.exists(), "feed.xml must be committed, not generated at deploy time"


def test_feed_parses_as_atom(feed_root):
    assert feed_root.tag == "{http://www.w3.org/2005/Atom}feed"


def test_feed_has_required_atom_elements(feed_root):
    for element in ("title", "id", "updated", "author"):
        assert feed_root.find(f"a:{element}", ATOM) is not None, f"missing <{element}>"


def test_feed_declares_self_and_alternate_links(feed_root):
    rels = {l.get("rel") for l in feed_root.findall("a:link", ATOM)}
    assert {"self", "alternate"} <= rels


def test_every_entry_has_the_required_elements(feed_root):
    entries = feed_root.findall("a:entry", ATOM)
    assert entries, "feed has no entries"
    for e in entries:
        for element in ("title", "id", "updated"):
            assert e.find(f"a:{element}", ATOM) is not None


# ── It derives from news.html ──────────────────────────────────────────────

def test_entry_count_matches_the_news_page(entries, feed_root):
    assert len(feed_root.findall("a:entry", ATOM)) == len(entries)
    assert len(entries) >= 1


def test_entry_titles_come_from_the_news_page(entries, feed_root):
    feed_titles = {e.find("a:title", ATOM).text for e in feed_root.findall("a:entry", ATOM)}
    assert feed_titles == {e.title for e in entries}


def test_feed_adds_no_prose_of_its_own(entries, feed_root):
    """Every summary must be text that already appears on the news page."""
    news = NEWS_HTML.read_text(encoding="utf-8")
    import html as _html

    for e in feed_root.findall("a:entry", ATOM):
        summary = e.find("a:summary", ATOM)
        if summary is None or not summary.text:
            continue
        # first eight words is enough to prove provenance without whitespace games
        probe = " ".join(summary.text.split()[:8])
        assert probe in " ".join(_html.unescape(news).split()), \
            f"summary text not found in news.html: {probe!r}"


def test_parser_fails_loudly_on_unrecognised_date():
    with pytest.raises(ValueError, match="unrecognised news date"):
        parse_news(
            '<article class="news-card">'
            '<time class="news-date">Smarch 2026</time><h2>T</h2></article>'
        )


def test_parser_skips_blocks_without_a_title_or_date():
    assert parse_news('<article class="news-card"><p>orphan</p></article>') == []


# ── Stability and determinism ──────────────────────────────────────────────

def test_regeneration_is_byte_identical(entries):
    assert build_feed(entries) == build_feed(entries)


def test_feed_updated_is_the_newest_entry_not_the_build_time(entries, feed_root):
    """Otherwise every rebuild would look like new content to a reader."""
    newest = max(e.published for e in entries)
    assert feed_root.find("a:updated", ATOM).text == f"{newest:%Y-%m-%dT%H:%M:%SZ}"


def test_entry_ids_are_stable_and_unique(feed_root):
    ids = [e.find("a:id", ATOM).text for e in feed_root.findall("a:entry", ATOM)]
    assert len(ids) == len(set(ids)), "duplicate entry ids would collapse in readers"
    assert all(i.startswith(TAG_BASE) for i in ids)


def test_entry_id_depends_only_on_month_and_title():
    e = Entry("A Title", "Release", "s", datetime(2026, 8, 1, tzinfo=timezone.utc))
    same = Entry("A Title", "Commentary", "different summary",
                 datetime(2026, 8, 1, tzinfo=timezone.utc))
    assert e.entry_id == same.entry_id
    assert e.entry_id == f"{TAG_BASE}:2026-08:a-title"


def test_markup_is_escaped():
    e = Entry("Ampersand & <script>", "Release", "5 < 6 & 7 > 2",
              datetime(2026, 8, 1, tzinfo=timezone.utc))
    xml = build_feed([e])
    ET.fromstring(xml)          # would raise if escaping were wrong
    assert "<script>" not in xml


# ── It cannot go stale ─────────────────────────────────────────────────────

def test_committed_feed_matches_current_news(entries):
    """The guard that catches an edited news.html with a forgotten regenerate."""
    assert FEED_XML.read_text(encoding="utf-8") == build_feed(entries), (
        "feed.xml is stale — run `python scripts/generate_feed.py` and commit it"
    )


def test_check_mode_returns_zero_when_current():
    assert main(["--check"]) == 0


# ── Site integration ───────────────────────────────────────────────────────

def test_news_page_advertises_the_feed():
    news = NEWS_HTML.read_text(encoding="utf-8")
    assert 'type="application/atom+xml"' in news, "no <link rel=alternate> for discovery"
    assert 'href="/feed.xml"' in news


def test_key_pages_carry_the_discovery_link():
    for page in ("index.html", "faq.html", "developers.html"):
        s = (REPO_ROOT / page).read_text(encoding="utf-8")
        assert 'type="application/atom+xml"' in s, f"{page} lacks feed discovery"


def test_build_script_ships_the_feed():
    build = (REPO_ROOT / "scripts" / "build_pages_site.sh").read_text(encoding="utf-8")
    assert "feed.xml" in build, "build_pages_site.sh does not copy feed.xml"
