import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const base = process.env.SCREENSHOT_BASE_URL ?? "http://localhost:3000";
await mkdir("screenshots", { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
for (const [name, path] of [["journey", "/"], ["itinerary", "/itinerary"], ["hotels", "/hotels"], ["budget", "/costs"]]) {
  await page.goto(`${base}${path}`, { waitUntil: "networkidle" });
  await page.screenshot({ path: `screenshots/${name}-desktop.png`, fullPage: true });
}
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
await mobile.goto(base, { waitUntil: "networkidle" });
await mobile.screenshot({ path: "screenshots/journey-mobile.png", fullPage: true });
await browser.close();
console.log("Screenshots written to screenshots/");
