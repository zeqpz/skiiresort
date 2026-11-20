/* High Peaks yeti, the owner's three fixes measured in the real runtime (2026-11-20):
   1. the ember ON the joint's lit tip: every frame of every clip (whole and half frames), and live through play and
      cross-fades - the ember sprite vs the tip point, and the runtime's tip vs Blender's (qa_points.json)
   2. no see-through gap in either arm: each arm drawn alone on a transparent page, every frame of every clip,
      screenshotted for qa_holes.py
   3. the joint's end ON his lips through the hit: end vs lips per frame, plus zoomed crops of the contact
   node tools/highpeaks/yeti/qa_fixes.js [http://localhost:8755]  -> art/highpeaks/yeti/qa/fix/, a report on stdout */
const path = require("path"), fs = require("fs");
const { chromium } = require("C:/Users/CooperHinkel/Documents/ClaudeRoblox/.tools/pw/node_modules/playwright");
const BASE = process.argv[2] || "http://localhost:8755";
const ROOT = path.join(__dirname, "..", "..", "..");
const OUT = path.join(ROOT, "art", "highpeaks", "yeti", "qa", "fix");
const QP = JSON.parse(fs.readFileSync(path.join(ROOT, "art", "highpeaks", "yeti", "rig_build", "qa_points.json"), "utf8"));
fs.rmSync(OUT, { recursive: true, force: true });
for (const d of ["arm_r", "arm_l", "all", "crops"]) fs.mkdirSync(path.join(OUT, d), { recursive: true });
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const VW = 1500, VH = 1600;
const clamp = r => { const x = Math.max(0, Math.min(VW - 10, r.x)), y = Math.max(0, Math.min(VH - 10, r.y));
                     return { x, y, width: Math.max(10, Math.min(VW - x, r.width)), height: Math.max(10, Math.min(VH - y, r.height)) }; };
const ARMS = { arm_r: ["arm_r_up", "arm_r_lo"], arm_l: ["arm_l"] };

(async () => {
  const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const p = await (await b.newContext({ viewport: { width: 1500, height: 1600 }, deviceScaleFactor: 1 })).newPage();
  const errs = [];
  p.on("pageerror", e => errs.push("pageerror " + e.message));
  p.on("console", m => { if (["error", "warning"].includes(m.type()) && !/swiftshader|GPU stall|WebGL|GroupMarker/i.test(m.text())) errs.push(m.type() + " " + m.text()); });
  await p.goto(`${BASE}/yeti_test.html?size=qa`);
  await p.waitForFunction(() => window.__yetiReady !== undefined, null, { timeout: 60000 });
  const report = [];
  const say = l => { report.push(l); console.log(l); };
  const clips = Object.keys(QP.points);

  // ---- 1. the ember on the tip, every frame (and half frame) of every clip
  let worstEmber = 0, worstBlender = 0, n1 = 0, worstAt = "";
  for (const c of clips) {
    const nf = QP.points[c].length;
    const res = await p.evaluate(([c, nf]) => {
      const out = [];
      for (let f = 0; f < nf; f += .5) {
        Yeti.pose(c, f);
        const e = Yeti.emberAt(), t = Yeti.point("tip");
        out.push([f, e.x, e.y, t.x, t.y]);
      }
      return out;
    }, [c, nf]);
    for (const [f, ex, ey, tx, ty] of res) {
      n1++;
      const d = Math.hypot(ex - tx, ey - ty);
      if (d > worstEmber) { worstEmber = d; worstAt = `${c} ${f}`; }
      if (Number.isInteger(f)) {
        const [bx, by] = QP.points[c][f];
        worstBlender = Math.max(worstBlender, Math.hypot(tx - bx, ty - by));
      }
    }
  }
  say(`1. ember vs joint tip: ${n1} posed frames (every whole and half frame of ${clips.length} clips): worst ${worstEmber.toFixed(4)} art px (${worstAt}); runtime tip vs Blender's tip: worst ${worstBlender.toFixed(4)} art px`);
  // live: through play, one-shots, the hold and the cross-fades, sampled every animation frame
  const live = await p.evaluate(async () => {
    Yeti.resume();
    let worst = 0, n = 0;
    const seq = [["win", 1200], ["anticipation", 1500], ["lose", 1500], ["big_win", 1800], ["idle", 900], ["bonus", 1500], ["idle", 5200]];
    for (const [r, ms] of seq) {
      Yeti.react(r);
      const t0 = performance.now();
      while (performance.now() - t0 < ms) {
        await new Promise(ok => requestAnimationFrame(ok));
        const e = Yeti.emberAt(), t = Yeti.point("tip");
        worst = Math.max(worst, Math.hypot(e.x - t.x, e.y - t.y)); n++;
      }
    }
    return { worst, n };
  });
  say(`   live play (win, anticipation, lose, big_win, bonus, idle incl. the cross-fades between them): ${live.n} frames, worst ember-to-tip ${live.worst.toFixed(4)} art px`);

  // ---- 3. the joint's end on his lips through the hit (and the crops)
  const [a, bb, cc, d] = QP.contact.idle[0];
  const lipsRes = await p.evaluate(([a, d]) => {
    const out = [];
    for (let f = a; f <= d; f++) { Yeti.pose("idle", f); const e = Yeti.point("end"), l = Yeti.point("lips"); out.push([f, Math.hypot(e.x - l.x, e.y - l.y)]); }
    return out;
  }, [a, d]);
  const hold = lipsRes.filter(([f]) => f >= bb && f <= cc).map(r => r[1]);
  say(`3. joint end vs lips (idle hit, hold ${bb}-${cc}): max ${Math.max(...hold).toFixed(3)} art px over ${hold.length} frames; ramp in ${a}-${bb}: ${lipsRes.filter(([f]) => f < bb).map(r => r[1].toFixed(1)).join(" ")}; ramp out: ${lipsRes.filter(([f]) => f > cc).map(r => r[1].toFixed(1)).join(" ")}`);
  const host = await p.evaluate(() => { const r = document.getElementById("host").getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; });
  const k = host[3] / 1.06 / 1463;                        // screen px per art px
  const toScreen = (x, y) => [host[0] + host[2] / 2 + (x - 512) * k, host[1] + host[3] - (1509 - y) * k];
  for (const f of [108, 112, 116, 124, 132, 142, 148]) {
    await p.evaluate(f => Yeti.pose("idle", f), f);
    const [sx, sy] = toScreen(QP.points.idle[f][4], QP.points.idle[f][5]);
    await p.screenshot({ path: path.join(OUT, "crops", `lips_idle_${f}.png`), clip: clamp({ x: sx - 120, y: sy - 110, width: 300, height: 220 }) });
  }
  for (const [c, f] of [["idle", 0], ["idle", 128], ["win", 24], ["big_win", 40], ["anticipation", 30]]) {
    await p.evaluate(([c, f]) => Yeti.pose(c, f), [c, f]);
    const [sx, sy] = toScreen(QP.points[c][f][0], QP.points[c][f][1]);
    await p.screenshot({ path: path.join(OUT, "crops", `ember_${c}_${f}.png`), clip: clamp({ x: sx - 90, y: sy - 90, width: 180, height: 180 }) });
  }

  // ---- 2. each arm alone, every frame, on a transparent page (qa_holes.py reads them)
  // the arms' region: the upper body and everything his arms can reach (thrown up included)
  const box = clamp({ x: host[0] - 300, y: host[1] - 330, width: host[2] + 600, height: 330 + host[3] * .62 });
  const allBox = clamp({ x: host[0] - 300, y: host[1] - 330, width: host[2] + 600, height: host[3] + 330 });
  let shots = 0;
  for (const [arm, names] of Object.entries(ARMS)) {
    await p.evaluate(n => Yeti.only(n), names);
    for (const c of clips) {
      for (let f = 0; f < QP.points[c].length; f++) {
        await p.evaluate(([c, f]) => Yeti.pose(c, f), [c, f]);
        await p.screenshot({ path: path.join(OUT, arm, `${c}_${String(f).padStart(3, "0")}.png`), clip: box, omitBackground: true });
        shots++;
      }
    }
  }
  await p.evaluate(() => Yeti.only(null));
  for (const c of clips) {
    for (let f = 0; f < QP.points[c].length; f += 3) {
      await p.evaluate(([c, f]) => Yeti.pose(c, f), [c, f]);
      await p.screenshot({ path: path.join(OUT, "all", `${c}_${String(f).padStart(3, "0")}.png`), clip: allBox, omitBackground: true });
      shots++;
    }
  }
  say(`2. ${shots} transparent screenshots (each arm alone every frame, the whole figure every 3rd) -> qa_holes.py`);
  say(`console: ${errs.length ? errs.join(" | ") : "clean"}`);
  console.log("---- summary");
  await b.close();
})();
