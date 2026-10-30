#!/usr/bin/env python3
"""
Site chrome — one header, one drawer, one footer, stamped into every page
=========================================================================
The published pages are static HTML with no templating, so the header, the
mobile drawer and the footer were copy-pasted into each of them. By 25 Oct 2026
the header had stayed identical but the footer existed in six variants: the
About link missing on ten pages, the copyright line duplicated inside the link
column on three, the demonstration line named two different ways, and a closing
sentence present on some pages and not others. Nothing checked, so nothing
noticed.

This script is the single source for all three regions. It writes them into
every published page between stable anchors and, with `--check`, fails CI when
a page has drifted from it. The pattern is `scripts/add_journey_wayfinder.py`.

What `site.js` binds, and therefore what must never change here without
changing it there too: `.menu-button[aria-controls="mobile-nav"]` and its
`aria-expanded`; `#mobile-nav`; `#nav-backdrop`; `.nav-dropdown-trigger` /
`.nav-dropdown-menu`; `.theme-toggle` and `.mobile-theme-toggle` /
`.mobile-theme-label`; `#search-toggle`, `#search-overlay`, `#search-input`,
`#search-results`, `#search-close`. The active link is set at runtime by
`site.js`, so the stamped markup carries no per-page state and is byte-identical
on every page.

Usage:
    python scripts/ia/build_site_chrome.py            # write or refresh
    python scripts/ia/build_site_chrome.py --check    # verify, write nothing
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The pages the build publishes. Keep in step with tests/test_site_navigation.PUBLISHED.
PUBLISHED = (
    "index.html", "about.html", "specification.html", "shadow-evaluation-guide.html",
    "developers.html", "evidence-pack.html", "regulatory-alignment.html",
    "framework/nhid-auth.html", "faq.html", "specs/index.html", "privacy.html", "sms-opt-in.html",
)

CHEV = ('<svg class="chev" viewBox="0 0 24 24" width="13" height="13" fill="none" '
        'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>')

GITHUB_ORG = "https://github.com/NHID-Clinical"
GITHUB_REPO = "https://github.com/NHID-Clinical/NHID-Clinical"
DEMO_LINE = ('<span class="footer-demo-line"><strong>Reference demonstration line</strong> &mdash; '
             '<a href="tel:+17176706772">+1 (717) 670-6772</a> '
             '<span class="footer-demo-note">(website demo, not personal contact)</span></span>')

# Primary navigation: five destinations and an About menu. Labels are the
# redesign brief's; "Pilot" is the shadow evaluation guide, which describes an
# observe-only pilot framework.
PRIMARY = (
    ("/specification.html", "Spec"),
    ("/evidence-pack.html", "Evidence"),
    ("/shadow-evaluation-guide.html", "Pilot"),
    ("/developers.html", "Developers"),
    ("/faq.html", "FAQ"),
)
ABOUT_MENU = (
    ("/about.html", "About the project"),
    ("/regulatory-alignment.html", "Regulatory alignment"),
    ("/framework/nhid-auth.html", "NHID-Auth (agent identity)"),
    ("/specs/", "Downloads"),
)
GITHUB_LINK = (f'<a href="{GITHUB_ORG}" target="_blank" rel="noopener noreferrer">'
               'GitHub &#x2197;</a>')


def _links(items, indent: str) -> str:
    return "\n".join(f'{indent}<a href="{href}">{label}</a>' for href, label in items)


HEADER = f'''<header class="site-header">
  <nav class="container nav" aria-label="Primary navigation">
    <a class="brand" href="/" aria-label="NHID-Clinical home">
      <span class="brand-mark" aria-hidden="true"><img src="/assets/brand/logo-mark-rich.svg" alt="" /></span>
      <span>
        <strong>NHID-Clinical</strong>
      </span>
    </a>
    <div class="nav-links">
{_links(PRIMARY, "      ")}
      <div class="nav-dropdown">
        <button class="nav-dropdown-trigger" type="button" aria-haspopup="true" aria-expanded="false">About {CHEV}</button>
        <div class="nav-dropdown-menu">
{_links(ABOUT_MENU, "          ")}
          {GITHUB_LINK}
        </div>
      </div>
    </div>
    <div class="nav-actions">
      <button class="icon-button search-toggle" type="button" aria-label="Search" id="search-toggle">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      </button>
      <button class="icon-button theme-toggle" type="button" aria-label="Toggle theme" id="theme-toggle">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
      </button>
      <a class="primary-pill" href="/shadow-evaluation-guide.html">Start a shadow evaluation</a>
      <button class="icon-button menu-button" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="mobile-nav">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
      </button>
    </div>
  </nav>
  <div class="search-overlay" id="search-overlay" hidden>
    <div class="container search-overlay-inner">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="flex-shrink:0;color:var(--body)" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="search" id="search-input" class="search-input" placeholder="Search NHID-Clinical…" autocomplete="off" aria-label="Search site"/>
      <button class="icon-button search-close" id="search-close" type="button" aria-label="Close search">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
    </div>
    <div class="container">
      <div class="search-results" id="search-results" role="listbox" aria-label="Search results"></div>
    </div>
  </div>
</header>'''

DRAWER = f'''<nav class="mobile-nav" id="mobile-nav" aria-label="Mobile navigation">
  <a href="/">Home</a>
{_links(PRIMARY, "  ")}
  <strong class="mobile-nav-group">About</strong>
{_links(ABOUT_MENU, "  ")}
  {GITHUB_LINK}
  <div class="mobile-nav-footer">
    <button class="theme-toggle mobile-theme-toggle" type="button" aria-label="Toggle dark mode">
      <svg class="sun-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
      <svg class="moon-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      <span class="mobile-theme-label">Switch to dark mode</span>
    </button>
  </div>
</nav>
<div class="nav-backdrop" id="nav-backdrop"></div>'''

FOOTER = f'''<footer id="contact" class="site-footer">
  <div class="container footer-inner">
    <div>
      <a href="/about.html">About</a>
      <a href="/privacy.html">Privacy</a>
      <a href="mailto:contact@nhid-clinical.org">Contact</a>
      <a href="{GITHUB_REPO}" target="_blank" rel="noopener noreferrer">GitHub</a>
      <a href="https://www.linkedin.com/in/brianna-baynard" target="_blank" rel="noopener noreferrer">Maintainer on LinkedIn</a>
    </div>
    <p class="footer-copy">© 2026 Brianna Baynard | NIST-2025-0035-0026 | CC BY 4.0 | contact@nhid-clinical.org | nhid-clinical.org</p>
    <p class="footer-copy">{DEMO_LINE}</p>
    <p class="footer-copy">This is an open, actively maintained framework &mdash; feedback and contributions welcome on <a href="{GITHUB_REPO}">GitHub</a>.</p>
  </div>
  <div class="container footer-wordmark" aria-hidden="true">NHID-Clinical</div>
</footer>'''

# Each region is replaced between anchors that every published page carries once.
REGIONS = (
    ("header", re.compile(r'<header class="site-header">.*?</header>', re.S), HEADER),
    ("drawer", re.compile(r'<nav class="mobile-nav".*?<div class="nav-backdrop" id="nav-backdrop"></div>', re.S), DRAWER),
    ("footer", re.compile(r'<footer\b[^>]*class="site-footer"[^>]*>.*?</footer>', re.S), FOOTER),
)


def stamp(html: str, path: str) -> str:
    for name, pattern, fresh in REGIONS:
        found = pattern.findall(html)
        if len(found) != 1:
            sys.exit(f"CHROME FAIL: {path} has {len(found)} {name} regions, expected 1")
        html = pattern.sub(lambda _m: fresh, html, count=1)
    return html


def apply(check: bool) -> int:
    changed, missing = [], []
    for rel in PUBLISHED:
        page = ROOT / rel
        if not page.exists():
            missing.append(rel)
            continue
        html = page.read_text(encoding="utf-8")
        fresh = stamp(html, rel)
        if fresh == html:
            continue
        changed.append(rel)
        if not check:
            page.write_text(fresh, encoding="utf-8")
    if missing:
        print(f"CHROME FAIL: published pages not found: {missing}", file=sys.stderr)
        return 1
    if check:
        if changed:
            print(f"CHROME FAIL: header/drawer/footer drifted on {changed}. "
                  "Run scripts/ia/build_site_chrome.py.", file=sys.stderr)
            return 1
        print(f"CHROME PASS: all {len(PUBLISHED)} published pages carry the shared header, drawer and footer")
        return 0
    print(f"Chrome written to {len(changed)} of {len(PUBLISHED)} pages"
          + (f": {changed}" if changed else " (all current)"))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 2)[1])
    ap.add_argument("--check", action="store_true", help="verify; write nothing; exit 1 on drift")
    sys.exit(apply(ap.parse_args().check))
