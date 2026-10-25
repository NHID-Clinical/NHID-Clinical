"""The header, drawer and footer are one generated block on every published page.

Before `scripts/ia/build_site_chrome.py` existed (25 Oct 2026) the footer had
drifted into six variants across twelve pages and nothing noticed. These tests
keep the generator honest the way `test_journey_wayfinder.py` keeps the
wayfinder honest: the check passes on the repository as committed, and it
fails on a page that has been edited by hand.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ia" / "build_site_chrome.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_site_chrome", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_published_page_carries_the_generated_chrome():
    result = subprocess.run([sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_check_bites_on_a_hand_edited_footer(tmp_path):
    """A guard that has never failed has not been tested."""
    mod = _load()
    page = ROOT / "about.html"
    html = page.read_text(encoding="utf-8")
    drifted = html.replace("Maintainer on LinkedIn", "Maintainer on LinkedIn (edited by hand)")
    assert drifted != html
    assert mod.stamp(drifted, "about.html") == mod.stamp(html, "about.html") == html


def test_the_chrome_keeps_what_site_js_binds():
    mod = _load()
    for needle in ('class="icon-button menu-button"', 'aria-controls="mobile-nav"', 'aria-expanded="false"',
                   'id="mobile-nav"', 'id="nav-backdrop"', 'class="nav-dropdown-trigger"', 'class="nav-dropdown-menu"',
                   'id="theme-toggle"', 'class="theme-toggle mobile-theme-toggle"', 'class="mobile-theme-label"',
                   'id="search-toggle"', 'id="search-overlay"', 'id="search-input"', 'id="search-results"', 'id="search-close"'):
        assert needle in mod.HEADER + mod.DRAWER, f"site.js binds {needle}; the generated chrome dropped it"
    js = (ROOT / "site.js").read_text(encoding="utf-8")
    for hook in (".menu-button", "#mobile-nav", "#nav-backdrop", ".nav-dropdown-trigger", ".theme-toggle", ".mobile-theme-label"):
        assert hook.lstrip(".#") in js, f"site.js no longer references {hook}; update the generator's docstring"


def test_the_published_set_matches_the_navigation_tests():
    from tests.test_site_navigation import PUBLISHED
    assert set(_load().PUBLISHED) == set(PUBLISHED)


@pytest.mark.parametrize("rel", [p for p in _load().PUBLISHED if 'class="doc-rail"' in (ROOT / p).read_text(encoding="utf-8")])
def test_a_contents_fold_is_open_in_the_markup(rel):
    """The rail is a <details>; site.js closes it on a phone. The markup must
    carry `open` so a reader without JavaScript sees the list everywhere."""
    html = (ROOT / rel).read_text(encoding="utf-8")
    fold = re.search(r'<details class="doc-rail-fold"([^>]*)>', html)
    assert fold, f"{rel}: the rail is not a details fold"
    assert "open" in fold.group(1), f"{rel}: the contents fold is closed in the markup"
    assert '<summary class="doc-rail-label">Contents</summary>' in html
