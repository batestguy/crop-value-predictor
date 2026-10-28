/**
 * Records the README walkthrough (video) and its stills.
 *
 * This is a documentation tool, never imported by the app. The Quick Research
 * response is stubbed with page.route() so the recording is deterministic, costs
 * no Tavily credits, and can be produced offline by any maintainer.
 *
 * Usage (with a production build being served, e.g. `npm run preview -- --port 4180`):
 *   node scripts/demo-capture.mjs --video
 *   node scripts/demo-capture.mjs --shots
 *   node scripts/demo-capture.mjs            # both
 *
 * Outputs: docs/media/demo-walkthrough.webm (raw, encoded to .mp4 outside Node)
 *          docs/screenshots/*.png
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright";

const BASE = process.env.DEMO_URL ?? "http://localhost:4180/";
const MODE = process.argv[2] ?? "--all";
const wantVideo = MODE === "--video" || MODE === "--all";
const wantShots = MODE === "--shots" || MODE === "--all";

const SHOTS = "docs/screenshots";
const MEDIA = "docs/media";
fs.mkdirSync(SHOTS, { recursive: true });
fs.mkdirSync(MEDIA, { recursive: true });

const RESEARCH_RESPONSE = {
  status: "web_fallback",
  crop_id: "custom:soybean-dry-grain",
  state: "Bauchi",
  price_type: "retail",
  estimate_ngn_per_kg: 1250,
  low_ngn_per_kg: 1100,
  high_ngn_per_kg: 1400,
  yield_t_per_ha: 2.4,
  costs_per_ha: {
    land_preparation: 180000,
    seed: 50000,
    fertilizer: 120000,
    pesticide: 35000,
    labour: 90000,
    transport: 40000,
    storage: 25000,
  },
  confidence: "low",
  source_count: 8,
  sources: [
    { title: "Bauchi soybean market price survey", url: "https://example.com/bauchi-soybean" },
    { title: "North-east legume outlook", url: "https://example.com/legume-outlook" },
    { title: "Soybean agronomy guide for the savannah", url: "https://example.com/soybean-agronomy" },
    { title: "Input cost bulletin", url: "https://example.com/input-costs" },
  ],
  warnings: ["No usable local observation was found."],
};

const COSTS = ["Land prep", "Seed", "Fertilizer", "Pesticide", "Labour", "Irrigation", "Transport", "Storage"];

const wait = (page, ms) => page.waitForTimeout(ms);

async function smoothScrollTo(page, selector, block = "center", settle = 850) {
  await page.evaluate(
    ([sel, blk]) => {
      const el = document.querySelector(sel);
      if (el) el.scrollIntoView({ behavior: "smooth", block: blk });
    },
    [selector, block],
  );
  await wait(page, settle);
}

async function type(page, label, value, delay = 45) {
  const field = page.getByLabel(label, { exact: true });
  await field.click();
  await field.fill("");
  await field.pressSequentially(value, { delay });
}

async function fillCosts(page, values) {
  for (let i = 0; i < COSTS.length; i++) {
    await type(page, COSTS[i], String(values[i] ?? 0), 12);
  }
}

async function completeCrop(page, crop, { yieldT, price, costs }) {
  await page.getByLabel("Crop being edited").selectOption({ label: crop });
  await wait(page, 350);
  await type(page, "Yield tonnes per hectare", String(yieldT), 55);
  await type(page, "Selling price NGN per kg", String(price), 55);
  await fillCosts(page, costs);
  await wait(page, 300);
}

async function assertRanked(page, where) {
  const blocked = await page.locator(".results-panel .notice").innerText().catch(() => "");
  const ranked = await page.locator(".recommendation").count();
  if (!ranked) {
    throw new Error(`Scenario not ranked after ${where}. Panel says: ${blocked.replace(/\s+/g, " ").slice(0, 300)}`);
  }
}

function addBadgeScript() {
  const badge = document.createElement("div");
  badge.textContent = "Demo · research response stubbed";
  badge.style.cssText =
    "position:fixed;left:16px;bottom:14px;z-index:9999;padding:5px 10px;border-radius:20px;" +
    "background:rgba(23,61,50,.82);color:#f6f2e8;font:11px/1 'DM Mono',monospace;letter-spacing:.06em;pointer-events:none";
  document.body.appendChild(badge);
}

async function main() {
  const rawDir = fs.mkdtempSync(path.join(os.tmpdir(), "seasonmargin-demo-"));
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    ...(wantVideo ? { recordVideo: { dir: rawDir, size: { width: 1280, height: 720 } } } : {}),
  });
  const page = await context.newPage();

  await page.route("**/api/price-research", async (route) => {
    await wait(page, 900); // let the "Looking up..." state read on camera
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(RESEARCH_RESPONSE) });
  });

  await page.goto(BASE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForFunction(() => navigator.serviceWorker?.controller !== null, null, { timeout: 15000 }).catch(() => {});
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = "smooth";
  });
  if (wantVideo) await page.evaluate(addBadgeScript);
  await wait(page, 2000);

  if (wantShots) await page.screenshot({ path: `${SHOTS}/seasonmargin-overview.png` });
  await wait(page, 1600);

  // 1. Field size and bag size.
  await type(page, "Area in hectares", "2");
  await wait(page, 900);

  // 2. Add a crop that is not on the list.
  await smoothScrollTo(page, ".custom-crop-box", "center");
  await type(page, "Other crop name", "Soybean", 70);
  await type(page, "Other crop form", "dry grain", 70);
  await page.getByRole("button", { name: "Add other crop" }).click();
  await wait(page, 900);

  // 3. Ask the research assistant for starting values.
  await type(page, "Farm state", "Bauchi", 70);
  await wait(page, 300);
  await page.getByRole("button", { name: "Find all starting values" }).click();
  await wait(page, 1900);
  await smoothScrollTo(page, ".research-result", "center", 1100);

  if (wantShots) await page.locator(".editor-card").screenshot({ path: `${SHOTS}/research-output.png` });
  await wait(page, 2600);

  // 4. Accept the estimate, then replace it with the farmer's own price.
  await page.getByRole("button", { name: "Use this estimate" }).click();
  await wait(page, 1300);
  await type(page, "Selling price NGN per kg", "1180", 90);
  await wait(page, 900);
  // The estimate covers the price, yield and most costs; the farmer fills the rest.
  await fillCosts(page, [180000, 50000, 120000, 35000, 90000, 0, 40000, 25000]);
  await wait(page, 900);

  // 5. Complete the other two crops by hand.
  await smoothScrollTo(page, ".editor-card", "start");
  await completeCrop(page, "White maize", {
    yieldT: 2,
    price: 800,
    costs: [60000, 25000, 90000, 15000, 70000, 0, 30000, 20000],
  });
  await completeCrop(page, "Rice", {
    yieldT: 3,
    price: 1000,
    costs: [70000, 30000, 95000, 18000, 80000, 0, 35000, 20000],
  });

  // 6. The comparison now ranks.
  await assertRanked(page, "completing three crops");
  await smoothScrollTo(page, ".results-panel", "start", 1000);
  if (wantShots) await page.screenshot({ path: `${SHOTS}/decision-view.png` });
  await wait(page, 2400);

  // 7. A price range shows the interval, not a forecast.
  await page.getByLabel("Crop being edited").selectOption({ label: "White maize" });
  await wait(page, 400);
  await type(page, "Low price", "700", 60);
  await type(page, "High price", "900", 60);
  await wait(page, 1100);
  await smoothScrollTo(page, ".results-panel", "start", 900);
  await wait(page, 1200);

  // 8. Local units: change the bag size.
  await smoothScrollTo(page, ".control-panel", "start");
  await type(page, "Bag size in kilograms", "100", 90);
  await wait(page, 1100);

  // 9. The printable report carries the same figures.
  await page.emulateMedia({ media: "print" });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await wait(page, 800);
  await page.locator(".print-report").scrollIntoViewIfNeeded();
  await wait(page, 2400);
  if (wantShots) await page.locator(".print-report").screenshot({ path: `${SHOTS}/print-report.png` });
  await wait(page, 2200);
  await page.emulateMedia({ media: "screen" });

  // 10. The calculator still works with the network off.
  await context.setOffline(true);
  await page.reload();
  await wait(page, 1600);
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = "smooth";
  });
  if (wantVideo) await page.evaluate(addBadgeScript);
  await wait(page, 2200);
  if (wantShots) await page.screenshot({ path: `${SHOTS}/offline-restart.png` });
  await context.setOffline(false);

  await context.close();

  if (wantVideo) {
    const files = fs.readdirSync(rawDir).filter((f) => f.endsWith(".webm"));
    if (!files.length) throw new Error("No video produced");
    const src = path.join(rawDir, files[0]);
    const dest = `${MEDIA}/demo-walkthrough.webm`;
    fs.copyFileSync(src, dest);
    fs.rmSync(rawDir, { recursive: true, force: true });
    const mb = (fs.statSync(dest).size / 1024 / 1024).toFixed(1);
    console.log(`video: ${dest} (${mb} MB raw)`);
  }

  if (wantShots) {
    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
    const mp = await mobile.newPage();
    await mp.goto(BASE);
    await mp.evaluate(() => localStorage.clear());
    await mp.reload();
    await wait(mp, 900);
    await mp.screenshot({ path: `${SHOTS}/mobile.png` });
    await mobile.close();
    console.log("screenshots written");
  }

  await browser.close();
}

await main();
