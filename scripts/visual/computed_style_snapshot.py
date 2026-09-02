#!/usr/bin/env python3
"""Snapshot the computed style of every element on every published page.

A class rename is only safe if nothing renders differently afterwards. Diffing
the CSS by eye cannot show that -- a missed selector, a renamed class left
behind in one page, or two components accidentally sharing a new name all look
fine in the source and wrong in the browser. This walks the real DOM and records
the properties the site's own rules actually set, keyed by a structural path
that does NOT include class names, so the snapshot is comparable across a rename.

Runs under prefers-reduced-motion, which the site already honours by pinning
.reveal to its final state -- otherwise the entry transition is sampled
mid-flight and every run differs from the last for reasons that have nothing to
do with the change under test.

Each page is then measured repeatedly until two consecutive reads agree, so a
reported difference means the change under test rather than when the clock
happened to stop. See PROPS for the one read that agreement could not stabilise
and why dropping it costs nothing.

  python scripts/visual/computed_style_snapshot.py <out.json>

Serve _site/ on :8899 first; see scripts/visual/README.md.
"""
import json
import os
import sys
import pathlib

from playwright.sync_api import sync_playwright

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
BASE = "http://localhost:8899"
DEFAULT_PAGES = [
    "index.html", "faq.html", "specification.html", "evidence-pack.html",
    "for-payers.html", "about.html", "framework/controls.html",
    "regulatory-alignment.html", "shadow-evaluation-guide.html",
]
VIEWPORTS = [("mobile", 390, 844), ("tablet", 834, 1112), ("desktop", 1440, 900)]
# Both themes. The dark palette is a separate set of token values, so a token
# change can leave the light theme untouched and still break dark rendering.
THEMES = ["light", "dark"]
SETTLE_ATTEMPTS = 8

# The properties a stylesheet in this repo actually sets. Recording every
# property would drown real differences in inherited noise.
PROPS = [
    "display", "position", "grid-template-columns", "flex-direction", "flex-wrap",
    "gap", "width", "height", "max-width", "min-height",
    "margin-top", "margin-bottom",
    # margin-left/right are deliberately absent. On the sticky header they come
    # back as 0px perhaps one run in three while the element's width still reads
    # 1320 inside a 1440 viewport -- a pair that cannot both be true. It wanders
    # to a different page each run on an unchanged tree, so it is the browser
    # answering from an unfinished layout, and treating it as signal means every
    # comparison reports a difference that is not there. Nothing is lost: a real
    # horizontal margin change moves the element, and __box records x and width.
    "padding-top", "padding-right", "padding-bottom", "padding-left",
    "color", "background-color", "border-top-width", "border-top-color",
    "border-radius", "box-shadow", "opacity", "visibility",
    "font-family", "font-size", "font-weight", "line-height", "letter-spacing",
    "text-transform", "text-align", "white-space", "overflow-x", "transform",
]

SNAPSHOT_JS = """(props) => {
  void document.body.offsetHeight;   // flush any pending layout before reading
  const out = {};
  const path = el => {
    const parts = [];
    for (let n = el; n && n.nodeType === 1 && n !== document.documentElement; n = n.parentElement) {
      const sibs = [...(n.parentElement ? n.parentElement.children : [])];
      parts.unshift(n.tagName.toLowerCase() + '[' + sibs.indexOf(n) + ']');
    }
    return parts.join('/');
  };
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    const rec = {};
    for (const p of props) rec[p] = s.getPropertyValue(p);
    const r = el.getBoundingClientRect();
    rec['__box'] = [Math.round(r.width), Math.round(r.height),
                    Math.round(r.x), Math.round(r.y)].join(',');
    out[path(el)] = rec;
  }
  return out;
}"""


def route(r):
    r.continue_() if "localhost:8899" in r.request.url else r.abort()


def main():
    out_path = pathlib.Path(sys.argv[1])
    pages = os.environ.get("NHID_PAGES", "").split(",") if os.environ.get("NHID_PAGES") else DEFAULT_PAGES
    snap = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME)
        for theme in THEMES:
          for name, w, h in VIEWPORTS:
            pg = b.new_page(viewport={"width": w, "height": h}, reduced_motion="reduce")
            pg.route("**/*", route)
            for rel in pages:
                pg.goto(f"{BASE}/{rel}", wait_until="load", timeout=20000)
                pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                pg.wait_for_timeout(400)
                settle = "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
                pg.evaluate(settle)
                styled = pg.evaluate("""() => [...document.styleSheets]
                    .some(s => (s.href||'').includes('nhid-clinical-ui') && s.cssRules.length > 0)""")
                if not styled:
                    raise SystemExit(f"FAIL: site stylesheet did not parse on {rel} @ {name}")
                previous = pg.evaluate(SNAPSHOT_JS, PROPS)
                for attempt in range(SETTLE_ATTEMPTS):
                    pg.wait_for_timeout(150)
                    pg.evaluate(settle)
                    current = pg.evaluate(SNAPSHOT_JS, PROPS)
                    if current == previous:
                        break
                    previous = current
                else:
                    raise SystemExit(
                        f"FAIL: {rel} @ {name} never settled in {SETTLE_ATTEMPTS} reads"
                    )
                snap[f"{theme}|{name}|{rel}"] = current
            pg.close()
        b.close()
    out_path.write_text(json.dumps(snap, indent=0, sort_keys=True))
    elems = sum(len(v) for v in snap.values())
    print(f"snapshot: {len(snap)} page/viewport pairs, {elems} elements, {len(PROPS)} properties each")


if __name__ == "__main__":
    main()
