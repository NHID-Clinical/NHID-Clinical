"""
Representative-page screenshots at three viewports, for before/after comparison
across CSS consolidation stages.

Served over HTTP, not file://. The pages reference stylesheets by absolute path
(/assets/css/...), which under file:// resolve to the filesystem root and
silently fail to load — producing an unstyled page that looks like a layout bug.
External requests (webfonts, analytics) are aborted since this environment has
no egress, so faces fall back; layout, spacing, colour and overflow are exercised.
"""
import os, sys, pathlib
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://localhost:8899'
PAGES = ['index.html', 'framework/controls.html', 'specification.html',
         'evidence-pack.html', 'for-payers.html', 'about.html']
VIEWPORTS = [('mobile', 390, 844), ('tablet', 834, 1112), ('desktop', 1440, 900)]
# Optional sweep: `NHID_VIEWPORTS="719x900,721x900"` replaces the three defaults.
# Used to bracket each breakpoint (one pixel either side) after a breakpoint
# change, where a mis-rounded query shows up as overflow in a narrow band that
# the three representative widths step straight over.
if os.environ.get('NHID_VIEWPORTS'):
    VIEWPORTS = [(spec, int(spec.split('x')[0]), int(spec.split('x')[1]))
                 for spec in os.environ['NHID_VIEWPORTS'].split(',')]
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

def route(r):
    r.continue_() if 'localhost:8899' in r.request.url else r.abort()

rows, overflow = [], 0
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for name, w, h in VIEWPORTS:
        pg = b.new_page(viewport={'width': w, 'height': h})
        pg.route('**/*', route)
        for rel in PAGES:
            try:
                resp = pg.goto(f'{BASE}/{rel}', wait_until='domcontentloaded', timeout=15000)
                if not resp or resp.status >= 400:
                    rows.append(f"  {name:8} {rel:30} HTTP {resp.status if resp else '?'}"); continue
                pg.wait_for_timeout(250)
            except Exception as e:
                rows.append(f"  {name:8} {rel:30} ERROR {type(e).__name__}"); continue
            # confirm the site stylesheet actually loaded before trusting any measurement
            styled = pg.evaluate("""() => [...document.styleSheets]
                .some(s => (s.href||'').includes('nhid-clinical-ui') && s.cssRules.length > 0)""")
            ow = pg.evaluate("() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)")
            bad = ow > w + 1
            overflow += bad
            pg.screenshot(path=str(OUT / f"{rel.replace('/','_').replace('.html','')}__{name}.png"), full_page=True)
            rows.append(f"  {name:8} {rel:30} css={'yes' if styled else 'NO!':3} width={ow:5} {'OVERFLOW' if bad else 'ok'}")
        pg.close()
    b.close()
print("\n".join(rows))
print(f"\noverflowing page/viewport combinations: {overflow}")
