#!/usr/bin/env node
// Recapture assets/images/trust-gateway.png, the README's still of Scenario B.
//
// A screenshot of specification.html's Trust Gateway panel with Scenario A
// hidden, so it shows nhid_ec_combo_008 exactly as the page renders it from
// scripts/build_gateway_fixture.py. Run it after that fixture changes; it is
// listed in docs/agents/surfaces.md.
//
//   node scripts/visual/capture_trust_gateway.cjs
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
// Absolute asset paths need a server: python -m http.server 8765 from the repo root.
const PAGE = process.env.PAGE_URL || "http://127.0.0.1:8765/specification.html";
const OUT = path.join(ROOT, "assets", "images", "trust-gateway.png");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 760, height: 1200 }, deviceScaleFactor: 2, colorScheme: "dark" });
  await page.goto(PAGE);
  await page.waitForSelector("#trust-gateway .ink-panel");
  await page.addStyleTag({ content: ".tg-controls{display:none !important}" });
  await page.evaluate(() => {
    for (const s of document.querySelectorAll(".tg-scenario")) s.hidden = s.dataset.scenario !== "nhid_ec_combo_008";
    document.querySelectorAll(".tg-controls").forEach((c) => (c.hidden = true));
    document.querySelectorAll(".tg-turn").forEach((t) => { t.hidden = false; });
  });
  await page.locator("#trust-gateway .ink-panel").screenshot({ path: OUT });
  await browser.close();
  console.log("Wrote " + path.relative(ROOT, OUT));
})();
