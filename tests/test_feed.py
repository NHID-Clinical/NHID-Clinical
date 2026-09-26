"""
Atom feed — regression tests
============================
The feed is the project's platform-independent following mechanism, so the
properties that matter are: it is valid Atom, it derives from
docs/release-history.md rather than carrying its own copy of the release notes,
entry ids are stable across regenerations, and it cannot silently go stale.

The source was news.html until the Phase B IA consolidation (2026-09-05) retired
that route. These tests moved with the generator: every property below is the
one it guarded before, restated against the new source. The point of the suite
is that the feed cannot drift from whatever holds the release record — not that
the record lives at any particular path.
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.generate_feed import (
    FEED_XML,
    RELEASE_HISTORY,
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
    return parse_news(RELEASE_HISTORY.read_text(encoding="utf-8"))


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


# ── It derives from the release history ────────────────────────────────────

def test_entry_count_matches_the_release_history(entries, feed_root):
    assert len(feed_root.findall("a:entry", ATOM)) == len(entries)
    assert len(entries) >= 1


def test_entry_titles_come_from_the_release_history(entries, feed_root):
    feed_titles = {e.find("a:title", ATOM).text for e in feed_root.findall("a:entry", ATOM)}
    assert feed_titles == {e.title for e in entries}


def test_feed_adds_no_prose_of_its_own(entries, feed_root):
    """Every summary must be text that already appears in the release history."""
    source = RELEASE_HISTORY.read_text(encoding="utf-8")
    import html as _html

    # The generator strips markdown emphasis and link syntax from summaries, so
    # compare against a source with the same stripping applied. Anything that
    # survives both is prose the generator carried over rather than invented.
    import re as _re
    flat = _re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", source)
    flat = " ".join(_html.unescape(_re.sub(r"[*_`]+", "", flat)).split())

    for e in feed_root.findall("a:entry", ATOM):
        summary = e.find("a:summary", ATOM)
        if summary is None or not summary.text:
            continue
        # first eight words is enough to prove provenance without whitespace games
        probe = " ".join(summary.text.split()[:8])
        assert probe in flat, \
            f"summary text not found in docs/release-history.md: {probe!r}"


def test_parser_fails_loudly_on_unrecognised_date():
    with pytest.raises(ValueError, match="unrecognised news date"):
        parse_news("## Title\n\n*Smarch 2026 · Release*\n\nBody.\n")


def test_parser_skips_blocks_without_a_title_or_date():
    """Front matter and undated headings are not entries."""
    assert parse_news("# Release history\n\nSome prose with no entry.\n") == []
    assert parse_news("## Orphan\n\nNo date line, so not an entry.\n") == []


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

def test_committed_feed_matches_current_release_history(entries):
    """Catches an edited release history with a forgotten regenerate."""
    assert FEED_XML.read_text(encoding="utf-8") == build_feed(entries), (
        "feed.xml is stale — run `python scripts/generate_feed.py` and commit it"
    )


def test_check_mode_returns_zero_when_current():
    assert main(["--check"]) == 0


# ── Site integration ───────────────────────────────────────────────────────

def test_the_retired_news_route_still_redirects():
    """news.html is a stub now; it must still resolve rather than 404."""
    stub = (REPO_ROOT / "news.html").read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in stub, "news.html should be a redirect stub"
    assert 'rel="canonical"' in stub


def test_key_pages_carry_the_discovery_link():
    for page in ("index.html", "faq.html", "developers.html"):
        s = (REPO_ROOT / page).read_text(encoding="utf-8")
        assert 'type="application/atom+xml"' in s, f"{page} lacks feed discovery"


def test_build_script_ships_the_feed():
    build = (REPO_ROOT / "scripts" / "build_pages_site.sh").read_text(encoding="utf-8")
    assert "feed.xml" in build, "build_pages_site.sh does not copy feed.xml"
