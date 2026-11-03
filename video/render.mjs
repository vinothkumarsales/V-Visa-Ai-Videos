import puppeteer from "puppeteer-core";
import { mkdir, rm } from "node:fs/promises";
import path from "node:path";

const sample = process.argv.includes("--sample");
const FPS = 30;
const DURATION = 72.172;
const OUT = sample ? "/tmp/reel-preview" : "/tmp/reel-frames-out";

const times = sample
  ? [0.4, 1.6, 3.2, 5.6, 9.0, 12.4, 15.4, 18.6, 22.2, 26.2, 30.0, 34.5, 40.2, 44.0, 47.0, 52.0, 57.0, 61.4, 65.6, 68.6, 71.3]
  : null;

const browser = await puppeteer.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: "new",
  args: [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--hide-scrollbars",
    "--disable-gpu",
    "--force-color-profile=srgb",
    "--font-render-hinting=none"
  ]
});

const page = await browser.newPage();
await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
await page.goto("file:///workspace/video/index.html", { waitUntil: "networkidle0" });
await page.evaluate(() => document.fonts.ready);

await rm(OUT, { recursive: true, force: true });
await mkdir(OUT, { recursive: true });

async function shoot(t, file) {
  await page.evaluate((time) => window.renderFrame(time), t);
  await page.screenshot({
    path: file,
    type: "jpeg",
    quality: sample ? 80 : 84,
    captureBeyondViewport: false
  });
}

if (sample) {
  for (const t of times) {
    const name = `t${String(t).replace(".", "_")}.jpg`;
    await shoot(t, path.join(OUT, name));
    console.log("sample", name);
  }
} else {
  const n = Math.round(DURATION * FPS);
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    const t = i / FPS;
    await shoot(t, path.join(OUT, String(i).padStart(5, "0") + ".jpg"));
    if (i % 60 === 0) {
      const el = (Date.now() - t0) / 1000;
      const rate = i === 0 ? 0 : i / el;
      const eta = rate ? (n - i) / rate : 0;
      console.log(`frame ${i}/${n} ${el.toFixed(1)}s eta ${eta.toFixed(0)}s`);
    }
  }
  console.log("frames", n);
}

await browser.close();
