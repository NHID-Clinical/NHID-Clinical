#!/usr/bin/env python3
"""
Rewrite the navigation on every surviving page to the consolidated IA.

Navigation is hardcoded twice in every page -- a desktop `.nav-links` block and
a `.mobile-nav` drawer -- with no partial or template. Editing eleven files by
hand, twice each, is twenty-two chances to leave a stale link to a route that no
longer exists, so it is done here and verified by the link checker afterwards.

The old nav carried 22 entries across five groups, including six `platform/`
routes and a "Simulator" group whose heading had no links under it at all.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SURVIVING = [
    "index.html", "specification.html", "shadow-evaluation-guide.html",
    "developers.html", "evidence-pack.html", "regulatory-alignment.html",
    "framework/nhid-auth.html", "faq.html", "specs/index.html",
    "privacy.html", "sms-opt-in.html",
]

CHEV = ('<svg class="chev" viewBox="0 0 24 24" width="13" height="13" fill="none" '
        'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>')

DESKTOP = f'''<div class="nav-links">
      <div class="nav-dropdown">
        <button class="nav-dropdown-trigger" type="button" aria-haspopup="true" aria-expanded="false">Framework {CHEV}</button>
        <div class="nav-dropdown-menu">
          <a href="/specification.html">Specification (v1.3)</a>
          <a href="/regulatory-alignment.html">Regulatory alignment</a>
          <a href="/framework/nhid-auth.html">NHID-Auth (agent identity)</a>
        </div>
      </div>
      <div class="nav-dropdown">
        <button class="nav-dropdown-trigger" type="button" aria-haspopup="true" aria-expanded="false">Evidence {CHEV}</button>
        <div class="nav-dropdown-menu">
          <a href="/evidence-pack.html">Evidence pack</a>
          <a href="/shadow-evaluation-guide.html">Shadow evaluation guide</a>
        </div>
      </div>
      <a href="/developers.html">Developers</a>
      <a href="/specs/">Downloads</a>
      <a href="/faq.html">FAQ</a>
      <a href="https://github.com/NHID-Clinical" target="_blank" rel="noopener noreferrer">GitHub &#x2197;</a>
    </div>'''

MOBILE = '''<nav class="mobile-nav" id="mobile-nav" aria-label="Mobile navigation">
  <a href="/">Home</a>
  <strong class="mobile-nav-group">Framework</strong>
  <a href="/specification.html">Specification (v1.3)</a>
  <a href="/regulatory-alignment.html">Regulatory alignment</a>
  <a href="/framework/nhid-auth.html">NHID-Auth (agent identity)</a>
  <strong class="mobile-nav-group">Evidence</strong>
  <a href="/evidence-pack.html">Evidence pack</a>
  <a href="/shadow-evaluation-guide.html">Shadow evaluation guide</a>
  <strong class="mobile-nav-group">Build</strong>
  <a href="/developers.html">Developers</a>
  <a href="/specs/">Downloads</a>
  <strong class="mobile-nav-group">More</strong>
  <a href="/faq.html">FAQ</a>
  <a href="https://github.com/NHID-Clinical" target="_blank" rel="noopener noreferrer">GitHub &#x2197;</a>
  '''

DESKTOP_RE = re.compile(r'<div class="nav-links">.*?</div>\s*(?=<div class="nav-actions">)', re.S)
MOBILE_RE = re.compile(r'<nav class="mobile-nav".*?(?=<div class="mobile-nav-footer">)', re.S)
PILL_RE = re.compile(r'(<a class="primary-pill" href=")[^"]*(")')


def rewrite(path: Path) -> None:
    t = path.read_text()
    before = t

    if not DESKTOP_RE.search(t):
        sys.exit(f"{path}: no .nav-links block found")
    t = DESKTOP_RE.sub(DESKTOP + "\n    ", t, count=1)

    if not MOBILE_RE.search(t):
        sys.exit(f"{path}: no .mobile-nav block found")
    t = MOBILE_RE.sub(MOBILE, t, count=1)

    # The primary call to action pointed at for-payers.html, which is merged away.
    t = PILL_RE.sub(r"\1/shadow-evaluation-guide.html\2", t)

    if t != before:
        path.write_text(t)
    print(f"  nav rewritten: {path}")


if __name__ == "__main__":
    for f in SURVIVING:
        p = Path(f)
        if not p.exists():
            sys.exit(f"{f}: surviving page does not exist")
        rewrite(p)
    print(f"\n{len(SURVIVING)} pages updated")
