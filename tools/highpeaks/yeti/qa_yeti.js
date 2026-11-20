/* High Peaks yeti QA in a real browser (Playwright, headless Chromium): the test page loads with no console errors or
   failed requests, every clip is posed at several frames (Yeti.pose: deterministic) and screenshotted whole, plus 2x
   crops of the joints (shoulders, elbows, wrists, neck, knees) in the hardest frames; then the live clock is checked:
   react() starts each clip, a one-shot eases back to the idle, anticipation holds until idle().

   node tools/highpeaks/yeti/qa_yeti.js [http://localhost:8755]   -> art/highpeaks/yeti/qa/*.png, a report on stdout */
const path = require("path"), fs = require("fs");
const { chromium } = require("C:/Users/CooperHinkel/Documents/ClaudeRoblox/.tools/pw/node_modules/playwright");
const BASE = process.argv[2] || "http://localhost:8755";
const OUT = path.join(__dirname, "..", "..", "..", "art", "highpeaks", "yeti", "qa");
fs.mkdirSync(OUT, { recursive: true });
const FRAMES = { idle: [0, 60, 112, 128, 150, 200], anticipation: [0, 15, 30, 45], win: [0, 14, 24, 40, 60],
                 big_win: [10, 24, 34, 60, 90, 104, 120], bonus: [20, 30, 64, 100, 130, 150], lose: [10, 30, 50, 75, 90] };
// joint crops in host px (host 420 x 640, "big"): [name, x, y, w, h]
const JOINTS = [["shoulders_neck", 80, 150, 270, 170], ["arm_r_elbow", 220, 160, 220, 260], ["arm_l", 0, 160, 200, 260],
                ["knees_boots", 80, 400, 280, 240]];

(async () => {
  const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const report = [];
  for (const flip of [false, true]) {
    const p = await (await b.newContext({ viewport: { width: 900, height: 900 }, deviceScaleFactor: 1 })).newPage();
    const errs = [];
    p.on("pageerror", e => errs.push("pageerror " + e.message));
    p.on("console", m => { if (["error", "warning"].includes(m.type()) && !/swiftshader|GPU stall|WebGL|GroupMarker/i.test(m.text())) errs.push(m.type() + " " + m.text()); });
    p.on("requestfailed", r => errs.push("failed " + r.url()));
    p.on("response", r => { if (r.status() >= 400) errs.push(r.status() + " " + r.url()); });
    await p.goto(`${BASE}/yeti_test.html?size=big${flip ? "&flip=1" : ""}`);
    await p.waitForFunction(() => window.__yetiReady !== undefined, null, { timeout: 60000 });
    const ok = await p.evaluate(() => window.__yetiReady);
    report.push(`flip=${flip} mounted=${ok} density=${JSON.stringify(await p.evaluate(() => Yeti.state() && Yeti.state().density))}`);
    if (!ok) { report.push("errors: " + errs.join(" | ")); continue; }
    const hostBox = await p.evaluate(() => { const r = document.getElementById("host").getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; });
    const tag = flip ? "flip_" : "";
    if (!flip) {
      for (const [clip, fr] of Object.entries(FRAMES)) {
        for (const f of fr) {
          await p.evaluate(([c, f]) => Yeti.pose(c, f), [clip, f]);
          await p.waitForTimeout(60);
          const clipBox = { x: Math.max(0, hostBox[0] - 160), y: Math.max(0, hostBox[1] - 200), width: hostBox[2] + 320, height: hostBox[3] + 220 };
          await p.screenshot({ path: path.join(OUT, `${clip}_${String(f).padStart(3, "0")}.png`), clip: clipBox });
        }
      }
      // the joints, 2x, in the hardest frames
      for (const [clip, f] of [["idle", 128], ["big_win", 34], ["bonus", 100], ["anticipation", 30], ["win", 24], ["lose", 50]]) {
        await p.evaluate(([c, f]) => Yeti.pose(c, f), [clip, f]);
        await p.waitForTimeout(60);
        for (const [jn, x, y, w, h] of JOINTS) {
          await p.screenshot({ path: path.join(OUT, `joint_${clip}_${f}_${jn}.png`),
                               clip: { x: hostBox[0] + x, y: hostBox[1] + y, width: w, height: h }, scale: "device" });
        }
      }
    } else {
      await p.evaluate(() => Yeti.pose("idle", 0));
      await p.waitForTimeout(60);
      await p.screenshot({ path: path.join(OUT, `flip_idle_000.png`) });
    }
    // the live clock
    const live = [];
    for (const r of ["win", "big_win", "bonus", "lose"]) {
      await p.evaluate(r => Yeti.react(r), r);
      await p.waitForTimeout(400);
      const s1 = await p.evaluate(() => Yeti.state());
      await p.waitForTimeout(r === "bonus" ? 5600 : r === "big_win" ? 4400 : r === "lose" ? 3400 : 2400);
      const s2 = await p.evaluate(() => Yeti.state());
      live.push(`${r}: playing=${s1.clip} -> after=${s2.clip}`);
    }
    await p.evaluate(() => Yeti.react("anticipation"));
    await p.waitForTimeout(3500);
    const sa = await p.evaluate(() => Yeti.state());
    await p.screenshot({ path: path.join(OUT, `${tag}live_anticipation.png`) });
    await p.evaluate(() => Yeti.react("win"));          // a reaction cuts in on the held loop
    await p.waitForTimeout(300);
    const sw = await p.evaluate(() => Yeti.state());
    await p.evaluate(() => Yeti.react("anticipation"));
    await p.waitForTimeout(300);
    await p.evaluate(() => Yeti.idle());
    await p.waitForTimeout(500);
    const si = await p.evaluate(() => Yeti.state());
    live.push(`anticipation held 3.5 s: ${sa.clip} hold=${sa.hold}; win cuts in: ${sw.clip}; idle(): ${si.clip}`);
    // big_win must not be cut short by a win
    await p.evaluate(() => Yeti.react("big_win"));
    await p.waitForTimeout(300);
    const refused = await p.evaluate(() => Yeti.react("win"));
    live.push(`win during big_win accepted=${refused} (want false)`);
    report.push(`[${flip ? "flipped" : "normal"}] ` + live.join("; "));
    report.push(`[${flip ? "flipped" : "normal"}] console/network: ${errs.length ? errs.join(" | ") : "clean"}`);
  }
  // a page without WebGL/Pixi: mount must say false, no throw
  const p2 = await (await b.newContext()).newPage();
  const e2 = [];
  p2.on("pageerror", e => e2.push(e.message));
  await p2.route("**/pixi.min.js", r => r.fulfill({ status: 200, contentType: "text/javascript", body: "" }));
  await p2.goto(`${BASE}/yeti_test.html`);
  await p2.waitForFunction(() => window.__yetiReady !== undefined, null, { timeout: 30000 });
  report.push(`no Pixi: mounted=${await p2.evaluate(() => window.__yetiReady)} pageerrors=${e2.length}`);
  console.log(report.join("\n"));
  await b.close();
})();
