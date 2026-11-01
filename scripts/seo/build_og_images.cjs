#!/usr/bin/env node
/*
 * Render one 1200x630 link-preview card per published page into assets/og/.
 *
 * Dev-only, like tools/how-it-works: the PNGs are committed and CI has no Node
 * step. Text comes from scripts/seo/pages.json, which seo_head.py also reads for
 * the alt text, so the image and its description cannot disagree.
 *
 *   node scripts/seo/build_og_images.cjs   (needs Playwright's Chromium and Pillow)
 *
 * Each card is then reduced to a 256-colour dithered palette (about 70 KB
 * instead of 165 KB). Twelve full-colour cards added 2 MB to a Pages artifact
 * that CI caps at 40 MB.
 *
 * Fonts are the repository's own Inter and IBM Plex Mono files, loaded from
 * disk, so a render does not depend on Google Fonts being reachable.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const pages = JSON.parse(fs.readFileSync(path.join(__dirname, 'pages.json'), 'utf8'));
// Embedded as data URLs: a page set with setContent() cannot fetch file:// fonts,
// and a silent fallback would ship a card in the wrong typeface.
const font = (f) => 'data:font/ttf;base64,' + fs.readFileSync(path.join(ROOT, 'assets/fonts', f)).toString('base64');
const logo = fs.readFileSync(path.join(ROOT, 'assets/brand/logo-mark-rich.svg'), 'utf8');
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const card = (row) => `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Inter;font-weight:400;src:url(${font('Inter-Regular.ttf')})}
@font-face{font-family:Inter;font-weight:600;src:url(${font('Inter-SemiBold.ttf')})}
@font-face{font-family:Inter;font-weight:700;src:url(${font('Inter-Bold.ttf')})}
@font-face{font-family:Plex;font-weight:400;src:url(${font('IBMPlexMono-Regular.ttf')})}
*{margin:0;box-sizing:border-box}
body{width:1200px;height:630px;overflow:hidden;font-family:Inter,sans-serif;color:#f4f7fa;
  background:radial-gradient(900px 520px at 88% 8%,rgba(20,119,143,.42),transparent 70%),#0b1a2b;
  position:relative}
/* drafting grid: four columns, as on the site */
body:before{content:"";position:absolute;inset:0;
  background:linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px) 84px 0/258px 100%}
.wrap{position:absolute;inset:72px 84px 64px 84px;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:20px}
.brand svg{width:64px;height:64px}
.brand b{font-weight:600;font-size:34px;letter-spacing:-.01em}
.kicker{margin-top:58px;align-self:flex-start;font-family:Plex,monospace;font-size:22px;letter-spacing:.06em;
  text-transform:uppercase;color:#7fd3dc;border:1.5px solid rgba(127,211,220,.55);border-radius:999px;padding:8px 20px}
h1{margin-top:26px;font-weight:700;font-size:60px;line-height:1.08;letter-spacing:-.025em;max-width:1000px}
h1.long{font-size:52px}
.foot{margin-top:auto;display:flex;gap:14px;flex-wrap:nowrap;font-family:Plex,monospace;font-size:21px;color:#9fb4c4;white-space:nowrap}
.foot span+span:before{content:"·";margin-right:14px;color:#4f6b80}
</style></head><body><div class="wrap">
<div class="brand">${logo}<b>NHID-Clinical</b></div>
<div class="kicker">${esc(row.kicker)}</div>
<h1 class="${row.headline.length > 70 ? 'long' : ''}">${esc(row.headline)}</h1>
<div class="foot"><span>Open proposal</span><span>v1.3</span><span>Not a standard or certification</span><span>nhid-clinical.org</span></div>
</div></body></html>`;

const QUANTIZE = [
  'import sys',
  'from PIL import Image',
  'p = sys.argv[1]',
  'Image.open(p).convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT,',
  '    dither=Image.Dither.FLOYDSTEINBERG).save(p, optimize=True)',
].join('\n');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  for (const [route, row] of Object.entries(pages)) {
    if (route.startsWith('_')) continue;
    await page.setContent(card(row), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    const missing = await page.evaluate(() =>
      ['700 60px Inter', '400 22px Plex'].filter((f) => !document.fonts.check(f)));
    if (missing.length) throw new Error(`fonts not loaded for ${route}: ${missing}`);
    const overflow = await page.evaluate(() => {
      const w = document.querySelector('.wrap').getBoundingClientRect();
      return [...document.querySelectorAll('.wrap > *')].some((el) => {
        const r = el.getBoundingClientRect();
        return r.right > w.right + 1 || r.bottom > w.bottom + 1;
      });
    });
    if (overflow) throw new Error(`card text overflows for ${route}`);
    const out = path.join(ROOT, 'assets/og', `${row.slug}.png`);
    await page.screenshot({ path: out });
    execFileSync('python3', ['-c', QUANTIZE, out]);
    console.log('wrote', path.relative(ROOT, out), fs.statSync(out).size, 'bytes');
  }
  await browser.close();
})();
