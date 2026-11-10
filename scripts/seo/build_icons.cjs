#!/usr/bin/env node
/* Renders the site's raster icons from assets/brand/favicon.svg, so the tab
 * icon, the home-screen icon and the installed-app icon can never drift from
 * the mark.
 *
 *   node scripts/seo/build_icons.cjs
 *
 * Writes favicon.ico, assets/brand/apple-touch-icon.png, assets/brand/icon-192.png,
 * assets/brand/icon-512.png, assets/brand/icon-maskable-512.png and
 * manifest.webmanifest. Needs Playwright with a Chromium (CHROMIUM_PATH to
 * point at a specific binary).
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const BRAND = path.join(ROOT, 'assets', 'brand');
const TILE = '#0f2440';
const svg = fs.readFileSync(path.join(BRAND, 'favicon.svg'), 'utf8');

/* A .ico is a 22-byte directory in front of a PNG; every current browser reads it. */
function ico(png, size) {
  const h = Buffer.alloc(22);
  h.writeUInt16LE(1, 2); h.writeUInt16LE(1, 4);
  h.writeUInt8(size, 6); h.writeUInt8(size, 7);
  h.writeUInt16LE(1, 10); h.writeUInt16LE(32, 12);
  h.writeUInt32LE(png.length, 14); h.writeUInt32LE(22, 18);
  return Buffer.concat([h, png]);
}

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  /* `bleed` fills the corners with the tile colour (iOS and maskable icons are
     cropped by the platform); `scale` shrinks the mark into the maskable safe zone. */
  async function render(size, { bleed = false, scale = 1 } = {}) {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await page.setContent(
      `<style>html,body{margin:0;height:100%;background:${bleed ? TILE : 'transparent'};display:grid;place-items:center}` +
      `svg{width:${size * scale}px;height:${size * scale}px;display:block}</style>${svg}`
    );
    const buf = await page.screenshot({ omitBackground: !bleed });
    await page.close();
    return buf;
  }

  fs.writeFileSync(path.join(ROOT, 'favicon.ico'), ico(await render(32), 32));
  fs.writeFileSync(path.join(BRAND, 'apple-touch-icon.png'), await render(180, { bleed: true }));
  fs.writeFileSync(path.join(BRAND, 'icon-192.png'), await render(192));
  fs.writeFileSync(path.join(BRAND, 'icon-512.png'), await render(512));
  fs.writeFileSync(path.join(BRAND, 'icon-maskable-512.png'), await render(512, { bleed: true, scale: 0.78 }));
  await browser.close();

  fs.writeFileSync(
    path.join(ROOT, 'manifest.webmanifest'),
    JSON.stringify({
      name: 'NHID-Clinical',
      short_name: 'NHID-Clinical',
      description: 'An open, testable control and evidence layer for provider-to-payer AI calls.',
      start_url: '/',
      display: 'browser',
      background_color: '#0b1725',
      theme_color: '#0b1725',
      icons: [
        { src: '/assets/brand/icon-192.png', sizes: '192x192', type: 'image/png' },
        { src: '/assets/brand/icon-512.png', sizes: '512x512', type: 'image/png' },
        { src: '/assets/brand/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    }, null, 2) + '\n'
  );
  console.log('icons and manifest written');
})();
