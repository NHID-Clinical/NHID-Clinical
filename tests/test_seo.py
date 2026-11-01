"""
Search and link-preview guards for the published site.

The audit behind these (Nov 2026) found the site already rendered real HTML
with one H1 and a unique title per page. What it lacked, and what these keep
fixed:

* no robots.txt and no sitemap.xml were published;
* every page shared one link-preview image;
* no Organization or article structured data;
* three meta descriptions longer than search results show;
* redirect stubs declared relative, fragment-bearing canonicals;
* five or six render-blocking stylesheets plus blocking web fonts per page,
  which held mobile Lighthouse Performance under 90 on most pages.
"""
from __future__ import annotations

import importlib.util
import json
import re
import struct
from pathlib import Path

import pytest

from tests.test_site_navigation import PUBLISHED

ROOT = Path(__file__).resolve().parents[1]
TABLE = {k: v for k, v in json.loads((ROOT / "scripts/seo/pages.json").read_text()).items()
         if not k.startswith("_")}


def load(rel: str):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def head(page: str) -> str:
    return (ROOT / page).read_text(encoding="utf-8").split("</head>", 1)[0]


def jsonld(page: str) -> list:
    blocks = re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
                        (ROOT / page).read_text(encoding="utf-8"), re.S)
    return [json.loads(b) for b in blocks]


def types_in(obj) -> set:
    found = set()
    if isinstance(obj, dict):
        t = obj.get("@type")
        found.update([t] if isinstance(t, str) else (t or []))
        for v in obj.values():
            found |= types_in(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= types_in(v)
    return found


# ── Coverage ─────────────────────────────────────────────────────────────────

def test_every_published_page_has_a_row_in_the_seo_table():
    assert sorted(TABLE) == sorted(PUBLISHED)


def test_seo_head_is_current():
    assert load("scripts/seo/seo_head.py").main(check=True) == 0


# ── Titles and descriptions ──────────────────────────────────────────────────

def test_titles_and_descriptions_are_unique_and_fit_a_result():
    titles, descs = {}, {}
    for page in PUBLISHED:
        h = head(page)
        titles.setdefault(re.search(r"<title>([^<]+)</title>", h).group(1), []).append(page)
        d = re.search(r'<meta name="description" content="([^"]+)"', h).group(1)
        assert 50 <= len(d) <= 160, f"{page}: description is {len(d)} characters"
        descs.setdefault(d, []).append(page)
    assert all(len(v) == 1 for v in titles.values()), titles
    assert all(len(v) == 1 for v in descs.values()), descs


@pytest.mark.parametrize("page", PUBLISHED)
def test_exactly_one_h1(page):
    assert len(re.findall(r"<h1\b", (ROOT / page).read_text(encoding="utf-8"))) == 1


# ── Link previews ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("page", PUBLISHED)
def test_each_page_previews_with_its_own_card(page):
    h, slug = head(page), TABLE[page]["slug"]
    want = f"https://nhid-clinical.org/assets/og/{slug}.png"
    assert f'<meta property="og:image" content="{want}"' in h
    assert f'<meta name="twitter:image" content="{want}"' in h
    assert 'name="twitter:image:alt"' in h and 'property="og:image:alt"' in h
    png = (ROOT / "assets/og" / f"{slug}.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (1200, 630)


def test_cards_are_distinct():
    blobs = {(ROOT / "assets/og" / f"{r['slug']}.png").read_bytes() for r in TABLE.values()}
    assert len(blobs) == len(TABLE)


# ── Structured data ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("page", PUBLISHED)
def test_structured_data_parses_and_names_the_organization(page):
    found = set().union(*(types_in(b) for b in jsonld(page)))
    assert "Organization" in found
    assert "Product" not in found, "claim-boundaries: the project is not a product"
    if TABLE[page]["type"] == "article":
        assert "TechArticle" in found
    if page != "index.html":
        assert "BreadcrumbList" in found


def test_faq_keeps_its_faqpage():
    assert "FAQPage" in set().union(*(types_in(b) for b in jsonld("faq.html")))


# ── robots.txt and sitemap.xml ───────────────────────────────────────────────

def test_robots_allows_everything_and_names_the_sitemap():
    text = (ROOT / "robots.txt").read_text()
    assert not re.search(r"(?mi)^disallow:\s*/\S*", text)
    assert "Sitemap: https://nhid-clinical.org/sitemap.xml" in text


@pytest.fixture
def mini_site(tmp_path):
    site = tmp_path / "_site"
    (site / "specs").mkdir(parents=True)
    page = '<html><head><title>{t}</title>{extra}</head><body><h1>{t}</h1></body></html>'
    (site / "index.html").write_text(page.format(t="Home", extra=""))
    (site / "faq.html").write_text(page.format(t="FAQ", extra=""))
    (site / "old.html").write_text(page.format(
        t="Moved", extra='<meta http-equiv="refresh" content="0; url=/faq.html">'))
    (site / "draft.html").write_text(page.format(
        t="Draft", extra='<meta name="robots" content="noindex,follow">'))
    (site / "google0123abcd.html").write_text("google-site-verification: google0123abcd.html")
    (site / "specs" / "Spec.pdf").write_bytes(b"%PDF-1.4")
    (site / "specs" / "index.html").write_text(page.format(t="Downloads", extra=""))
    return site


def test_sitemap_lists_what_is_published_and_nothing_else(mini_site):
    load("scripts/seo/build_sitemap.py").main(str(mini_site))
    locs = re.findall(r"<loc>([^<]+)</loc>", (mini_site / "sitemap.xml").read_text())
    assert locs == ["https://nhid-clinical.org/faq.html", "https://nhid-clinical.org/",
                    "https://nhid-clinical.org/specs/",
                    "https://nhid-clinical.org/specs/Spec.pdf"]


def test_sitemap_urls_match_each_pages_canonical():
    mod = load("scripts/seo/build_sitemap.py")
    for page in PUBLISHED:
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', head(page)).group(1)
        assert canon == mod.ORIGIN + "/" + re.sub(r"(^|/)index\.html$", r"\1", page), page


def test_build_script_generates_the_sitemap_after_the_redirects():
    script = (ROOT / "scripts/build_pages_site.sh").read_text()
    assert script.index("make_redirects.py") < script.index("build_sitemap.py")
    assert script.index("optimize_build.py") < script.index("make_redirects.py")


# ── Redirect stubs ───────────────────────────────────────────────────────────

def test_redirect_canonicals_are_absolute_and_fragment_free(tmp_path):
    mod = load("scripts/ia/make_redirects.py")
    assert mod.main(str(tmp_path)) == 0
    stubs = list(tmp_path.rglob("*.html"))
    assert stubs
    for stub in stubs:
        text = stub.read_text()
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', text).group(1)
        assert canon.startswith("https://") and "#" not in canon, (stub, canon)
        assert 'content="noindex,follow"' in text


def test_no_redirect_points_at_another_redirect():
    rows = [line.split("\t") for line in
            (ROOT / "scripts/ia/redirects.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")]
    routes = {r for r, _ in rows}
    for route, dest in rows:
        assert dest.split("#")[0].lstrip("/") not in routes, f"chain: {route} -> {dest}"


# ── Render path ──────────────────────────────────────────────────────────────

def test_build_bundles_stylesheets_in_order_and_unblocks_fonts(tmp_path):
    site = tmp_path / "_site"
    (site / "assets/css").mkdir(parents=True)
    (site / "a.css").write_text("/* first */\n.a { color: red; }\n")
    (site / "assets/css/b.css").write_text(".b { color: blue; }\n\n.a { color: green; }\n")
    fonts = "https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap"
    (site / "page.html").write_text(
        f'<html><head>\n<link href="{fonts}" rel="stylesheet"/>\n'
        '<link rel="stylesheet" href="/a.css"/>\n<link rel="stylesheet" href="/assets/css/b.css"/>\n'
        "</head><body><h1>x</h1></body></html>")
    load("scripts/seo/optimize_build.py").main(str(site))
    out = (site / "page.html").read_text()

    sheets = re.findall(r'<link rel="stylesheet" href="(/assets/css/bundle\.[0-9a-f]{10}\.css)"', out)
    assert len(sheets) == 1 and "/a.css" not in out
    css = (site / sheets[0].lstrip("/")).read_text()
    # Same rules, same order: the later .a still wins the cascade.
    assert css.index(".a { color: red; }") < css.index(".b { color: blue; }") < css.index(".a { color: green; }")
    assert "first" not in css.replace("/* /a.css */", "")

    assert f'<link rel="preload" as="style" href="{fonts}"' in out
    assert f'<noscript><link rel="stylesheet" href="{fonts}"/></noscript>' in out
    assert f'<link href="{fonts}" rel="stylesheet"/>' not in out


def test_no_published_page_is_outside_the_build_steps():
    """specs/index.html was first skipped by both build steps because its
    folder also holds the PDFs. Every published page must be in scope."""
    for rel in ("scripts/seo/optimize_build.py", "scripts/seo/build_sitemap.py"):
        skip = load(rel).SKIP_DIRS
        assert not [p for p in PUBLISHED if p.startswith(skip)], rel
