/**
 * Records the README walkthrough (video) and its stills.
 *
 * This is a documentation tool, never imported by the app. The Quick Research
 * response is stubbed with page.route() so the recording is deterministic, costs
 * no Tavily credits, and can be produced offline by any maintainer. The stub is
 * disclosed on camera and in the README.
 *
 * Every stage is a caption plus at least one visible action, padded to a minimum
 * on-screen duration, so no frame is filler and no caption flashes past.
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

/** One-line caption burned into the recording, bottom centre. */
async function say(page, text) {
  if (!wantVideo) return;
  await page.evaluate((t) => {
    let el = document.getElementById("demo-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "demo-caption";
      el.style.cssText =
        "position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:99999;" +
        "max-width:900px;padding:11px 24px;border-radius:999px;white-space:nowrap;" +
        "background:rgba(23,61,50,.93);color:#f7f3e8;font:500 22px/1.25 system-ui,-apple-system,'Segoe UI',sans-serif;" +
        "letter-spacing:.005em;pointer-events:none;box-shadow:0 10px 30px rgba(0,0,0,.18)";
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, text);
}

/**
 * Runs one stage: caption first, then the action, then pad to minMs so the
 * caption is readable and the shot always contains movement.
 */
async function stage(page, caption, minMs, action) {
  const started = Date.now();
  await say(page, caption);
  await wait(page, 140);
  await action();
  const remaining = minMs - (Date.now() - started);
  if (remaining > 0) await wait(page, remaining);
}

async function scrollTo(page, selector, block = "center", settle = 620) {
  await page.evaluate(
    ([sel, blk]) => {
      const el = document.querySelector(sel);
      if (el) el.scrollIntoView({ behavior: "smooth", block: blk });
    },
    [selector, block],
  );
  await wait(page, settle);
}

/** Types like a person, for the moments that must be seen. */
async function type(page, label, value, delay = 55) {
  const field = page.getByLabel(label, { exact: true });
  await field.click();
  await field.fill("");
  await field.pressSequentially(value, { delay });
}

/** Fills without animation, for the repetitive fields. */
async function fillField(page, label, value) {
  await page.getByLabel(label, { exact: true }).fill(String(value));
}

async function fillCosts(page, values, fast = false) {
  for (let i = 0; i < COSTS.length; i++) {
    if (fast) await fillField(page, COSTS[i], String(values[i] ?? 0));
    else await type(page, COSTS[i], String(values[i] ?? 0), 14);
  }
}

async function assertRanked(page, where) {
  if (!(await page.locator(".recommendation").count())) {
    const why = await page.locator(".results-panel").innerText().catch(() => "");
    throw new Error(`Scenario not ranked after ${where}: ${why.replace(/\s+/g, " ").slice(0, 300)}`);
  }
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
    await wait(page, 700); // the lookup state should read on camera, not flash
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(RESEARCH_RESPONSE) });
  });

  await page.goto(BASE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForFunction(() => navigator.serviceWorker?.controller !== null, null, { timeout: 15000 }).catch(() => {});
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = "smooth";
  });
  if (wantVideo) {
    await page.evaluate(() => {
      const badge = document.createElement("div");
      badge.textContent = "demo · research response stubbed";
      badge.style.cssText =
        "position:fixed;right:14px;bottom:18px;z-index:99998;padding:6px 11px;border-radius:999px;" +
        "background:rgba(23,61,50,.14);color:#4d6658;font:500 12px/1 system-ui,sans-serif;pointer-events:none";
      document.body.appendChild(badge);
    });
  }

  await stage(page, "Start with how much land you farm — every figure scales from it.", 4200, async () => {
    if (wantShots) await page.screenshot({ path: `${SHOTS}/seasonmargin-overview.png` });
    await scrollTo(page, ".control-panel", "start", 1300);
  });

  await stage(page, "Pick two or more crops; the shortlist carries through every step.", 5600, async () => {
    await type(page, "Area in hectares", "2", 110);
    await scrollTo(page, ".crop-list", "center");
    await page.getByLabel(/^Cassava/).check();
  });

  await stage(page, "Not on the list? Add the crop and how it is sold.", 5200, async () => {
    await scrollTo(page, ".custom-crop-box", "center");
    await type(page, "Other crop name", "Soybean", 45);
    await type(page, "Other crop form", "dry grain", 35);
    await page.getByRole("button", { name: "Add other crop" }).click();
  });

  await stage(page, "Ask the research assistant for starting values.", 4400, async () => {
    await type(page, "Farm state", "Bauchi", 45);
    await page.getByRole("button", { name: "Find all starting values" }).click();
    await wait(page, 900);
  });

  await stage(page, "Check the price, range and sources before you use anything.", 5400, async () => {
    await scrollTo(page, ".research-result", "end", 900);
    if (wantShots) await page.locator(".editor-card").screenshot({ path: `${SHOTS}/research-output.png` });
  });

  await stage(page, "Use it as a starting point — then type your own price.", 5600, async () => {
    await page.getByRole("button", { name: "Use this estimate" }).click();
    await wait(page, 700);
    await type(page, "Selling price NGN per kg", "1180", 80);
    await fillField(page, "Irrigation", 0);
  });

  await stage(page, "The other crops go in by hand: yield, price, eight costs.", 7200, async () => {
    await scrollTo(page, ".editor-card", "start");
    await page.getByLabel("Crop being edited").selectOption({ label: "White maize" });
    await wait(page, 300);
    await type(page, "Yield tonnes per hectare", "2", 60);
    await type(page, "Selling price NGN per kg", "800", 60);
    await fillCosts(page, [60000, 25000, 90000, 15000, 70000, 0, 30000, 20000]);

    await page.getByLabel("Crop being edited").selectOption({ label: "Rice" });
    await wait(page, 300);
    await fillField(page, "Yield tonnes per hectare", 3);
    await fillField(page, "Selling price NGN per kg", 1000);
    await fillCosts(page, [70000, 30000, 95000, 18000, 80000, 0, 35000, 20000], true);

    await page.getByLabel("Crop being edited").selectOption({ label: "Cassava" });
    await wait(page, 300);
    await fillField(page, "Yield tonnes per hectare", 15);
    await fillField(page, "Selling price NGN per kg", 400);
    await fillCosts(page, [50000, 20000, 40000, 10000, 60000, 0, 25000, 10000], true);
  });

  await stage(page, "Nothing is ranked until every selected crop is complete.", 4600, async () => {
    await assertRanked(page, "completing the shortlist");
    await scrollTo(page, ".recommendation", "start", 750);
    if (wantShots) await page.screenshot({ path: `${SHOTS}/decision-view.png` });
  });

  await stage(page, "Add a price range to see the spread — not a forecast.", 5400, async () => {
    await page.getByLabel("Crop being edited").selectOption({ label: "White maize" });
    await wait(page, 350);
    await type(page, "Low price", "700", 60);
    await type(page, "High price", "900", 60);
    await scrollTo(page, ".recommendation", "start", 650);
  });

  await stage(page, "Change the bag size and every price shows in your bags.", 4300, async () => {
    await scrollTo(page, ".control-panel", "start", 650);
    await type(page, "Bag size in kilograms", "100", 80);
  });

  await stage(page, "Print the same figures, with the same basis and wording.", 5600, async () => {
    await page.emulateMedia({ media: "print" });
    await page.locator(".print-report").scrollIntoViewIfNeeded();
    await wait(page, 900);
    if (wantShots) await page.locator(".print-report").screenshot({ path: `${SHOTS}/print-report.png` });
    await page.mouse.wheel(0, 240);
    await wait(page, 700);
    await page.mouse.wheel(0, 240);
    await wait(page, 500);
    await page.emulateMedia({ media: "screen" });
  });

  await stage(page, "Reload with the network off. The scenario is still there.", 5200, async () => {
    await context.setOffline(true);
    await page.reload();
    await wait(page, 900);
    // The reload wipes the injected caption; put it back so the last shot is labelled.
    await say(page, "Reload with the network off. The scenario is still there.");
    await wait(page, 500);
    if (wantShots) await page.screenshot({ path: `${SHOTS}/offline-restart.png` });
    await context.setOffline(false);
  });

  await context.close();

  if (wantVideo) {
    const files = fs.readdirSync(rawDir).filter((f) => f.endsWith(".webm"));
    if (!files.length) throw new Error("No video produced");
    const dest = `${MEDIA}/demo-walkthrough.webm`;
    fs.copyFileSync(path.join(rawDir, files[0]), dest);
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
