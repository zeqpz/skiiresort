// High Peaks: the scene's life (owner, 2026-11-18: "we don't want it static"), drawn on one canvas laid exactly over the
// lodge plate (#bgwall's background, bonus_wall.webp = art/highpeaks/raw/plate_base2.png):
//
//   * chairs riding the chairlift's cable up the slope (empty ones and ones carrying two goofy skiers)
//   * skiers and snowboarders coming down the groomed run now and then, growing as they come closer
//   * green smoke puffs rising from the lodge chimney
//   * fat clouds drifting across the sky
//   * snow falling over the whole scene (heavier in FRESH POWDER)
//   * the lodge windows glowing and flickering softly
//
// Every place is in PLATE pixels (3840x2160), read off the plate (tools/highpeaks: plate_base2 gridded). The layer is
// sized to the plate as the browser draws #bgwall's background (cover / position), the same way scenefx.js does, so it
// never drifts from the picture. In a bonus the plate is swapped for its own scene (Scene.to): the lift, the skiers,
// the smoke and the windows belong to the base plate and rest; the clouds and the snow carry on. One rAF loop at ~30
// fps, paused while the tab is hidden; with reduced motion only a still frame is drawn.
//
//   SkyFX.start(host)     once, with #bgwall
//   SkyFX.layout()        after a re-fit (placeScenery)
//   SkyFX.scene(name)     "normal" | "zombie" (FRESH POWDER) | "midnight" (BLACK DIAMOND) | "nitro" (AVALANCHE)
(function () {
  "use strict";
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PW = 3840, PH = 2160;
  const B = "assets/scene/";
  // the lift's cable, bottom right (off the plate) up to the top tower; chairs ride it upward
  const LIFT = [[3900, 760], [3620, 668], [3460, 553], [3296, 412], [3440, 334], [3532, 284]];
  const LIFT_SCALE = y => .36 + (Math.min(760, Math.max(284, y)) - 284) / (760 - 284) * .7;   // far chairs are smaller
  const CHAIR_H = 190, CHAIRS = 7, LIFT_SPEED = 46;                                               // plate px / s
  // the ski run, its top (far, small) to past the plate's right edge (near, big): [x, y, scale]
  const RUN = [[3185, 360, .2], [3125, 520, .3], [3092, 720, .42], [3128, 920, .56], [3255, 1115, .72],
               [3420, 1300, .88], [3615, 1478, 1.04], [3920, 1680, 1.2]];
  const RIDER_H = 230, RIDE_MS = [8500, 11500], RIDE_GAP = [2500, 7000];
  const CHIMNEY = [1092, 430], PUFF = 150, PUFF_EVERY = 900, PUFF_LIFE = 5200;
  const WINDOWS = [[1320, 1008, 300, 200], [1884, 1008, 420, 200], [2436, 1008, 300, 200], [1332, 1464, 330, 200], [2436, 1464, 330, 200]];
  const SKY = [40, 300];   // the band the clouds drift in

  let host = null, root = null, cv = null, g = null, rect = null, scale = 1;
  let raf = 0, last = 0, now0 = 0, mode = "normal", live = true;
  const pics = {};
  const chairs = [], riders = [], puffs = [], clouds = [], flakes = [];
  let nextRide = 0, nextPuff = 0;
  const rand = (a, b) => a + Math.random() * (b - a);

  function pic(name) {
    if (!pics[name]) { const im = new Image(); im.decoding = "async"; im.src = B + name + ".webp"; pics[name] = im; }
    return pics[name];
  }
  const ok = im => im && im.complete && im.naturalWidth > 0;

  // the plate's box inside host, from host's own computed background (as scenefx.js)
  function plateBox() {
    const W = host.clientWidth, H = host.clientHeight, cs = getComputedStyle(host);
    const size = (cs.backgroundSize || "cover").split(",").pop().trim();
    let s = size === "contain" ? Math.min(W / PW, H / PH) : Math.max(W / PW, H / PH);
    if (size !== "contain" && size !== "cover") {
      const [w, h = "auto"] = size.split(/\s+/);
      const len = (v, box, nat) => v.endsWith("%") ? box * parseFloat(v) / 100 / nat : v.endsWith("px") ? parseFloat(v) / nat : null;
      s = len(w, W, PW) ?? len(h, H, PH) ?? s;
    }
    const pw = PW * s, ph = PH * s;
    const pos = (cs.backgroundPosition || "50% 50%").split(",").pop().trim().split(/\s+/);
    const at = (v, free) => v.endsWith("%") ? free * parseFloat(v) / 100 : v.endsWith("px") ? parseFloat(v) : free / 2;
    return { x: at(pos[0] || "50%", W - pw), y: at(pos[1] || "50%", H - ph), w: pw, h: ph };
  }

  function layout() {
    if (!root) return;
    rect = plateBox();
    Object.assign(root.style, { left: rect.x.toFixed(1) + "px", top: rect.y.toFixed(1) + "px", width: rect.w.toFixed(1) + "px", height: rect.h.toFixed(1) + "px" });
    // the canvas at the size it is shown (capped: it is scenery), drawing in plate px through one transform
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const w = Math.max(1, Math.round(rect.w * dpr)), h = Math.max(1, Math.round(rect.h * dpr));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    scale = w / PW;
    if (RM) draw(performance.now(), 0);
  }

  // ---------------------------------------------------------------- paths
  function pathOf(pts) {
    const seg = [];
    let L = 0;
    for (let i = 1; i < pts.length; i++) {
      const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      seg.push([L, d]); L += d;
    }
    return { pts, seg, L };
  }
  function along(p, s) {   // the point (and any third value) s plate px along the path
    s = Math.max(0, Math.min(p.L, s));
    let i = p.seg.findIndex(([a, d]) => s <= a + d);
    if (i < 0) i = p.seg.length - 1;
    const [a, d] = p.seg[i], t = d ? (s - a) / d : 0, A = p.pts[i], Bp = p.pts[i + 1];
    return A.map((v, k) => v + (Bp[k] - v) * t);
  }
  // a smooth curve through the run's points (Catmull-Rom), for the riders
  function runAt(t) {
    const n = RUN.length - 1, f = Math.max(0, Math.min(.9999, t)) * n, i = Math.floor(f), u = f - i;
    const P = k => RUN[Math.max(0, Math.min(n, k))];
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    return [0, 1, 2].map(k => .5 * (2 * p1[k] + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u * u
                                     + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u * u * u));
  }
  const liftPath = pathOf(LIFT);

  // ---------------------------------------------------------------- setup
  function seed() {
    for (let i = 0; i < CHAIRS; i++) chairs.push({ s: liftPath.L * i / CHAIRS, full: i % 2 === 1 });
    for (let i = 0; i < 3; i++) clouds.push({ x: rand(-400, PW), y: rand(SKY[0], SKY[1]), v: rand(10, 22), k: rand(.7, 1.25) });
    for (let i = 0; i < 160; i++) flakes.push(newFlake(true));
  }
  function newFlake(anywhere) {
    const z = Math.random();   // depth: near flakes are bigger, faster, brighter
    return { x: rand(0, PW), y: anywhere ? rand(0, PH) : rand(-60, -10), r: 3 + z * 9, v: 40 + z * 110, sway: rand(0, 6.28),
             sw: rand(.4, 1.2), a: .45 + z * .5 };
  }

  // ---------------------------------------------------------------- drawing
  function sprite(im, x, y, h, { flip = false, alpha = 1, anchorY = .5 } = {}) {
    if (!ok(im)) return;
    const w = h * im.naturalWidth / im.naturalHeight;
    g.save();
    g.globalAlpha = alpha;
    g.translate(x, y);
    if (flip) g.scale(-1, 1);
    g.drawImage(im, -w / 2, -h * anchorY, w, h);
    g.restore();
  }

  function draw(t, dt) {
    g.setTransform(scale, 0, 0, scale, 0, 0);
    g.clearRect(0, 0, PW, PH);
    const base = mode === "normal";

    // clouds (behind everything else of ours)
    const cloud = pic("cloud");
    for (const c of clouds) {
      c.x += c.v * dt;
      if (c.x > PW + 500) { c.x = -500; c.y = rand(SKY[0], SKY[1]); c.k = rand(.7, 1.25); }
      sprite(cloud, c.x, c.y, 200 * c.k, { alpha: mode === "midnight" ? .35 : .92 });
    }

    if (base) {
      // windows: a warm glow that breathes and now and then flickers
      g.save();
      g.globalCompositeOperation = "lighter";
      WINDOWS.forEach(([x, y, w, h], i) => {
        const a = .1 + .06 * Math.sin(t / 900 + i * 1.7) + (Math.random() < .015 ? .08 : 0);
        const gr = g.createRadialGradient(x, y, 10, x, y, Math.max(w, h) * .75);
        gr.addColorStop(0, `rgba(255, 210, 110, ${a.toFixed(3)})`);
        gr.addColorStop(1, "rgba(255, 180, 60, 0)");
        g.fillStyle = gr;
        g.fillRect(x - w, y - h * 1.2, w * 2, h * 2.4);
      });
      g.restore();

      // the chairlift: chairs hang under the cable, grip at the top
      for (const c of chairs) {
        c.s = (c.s + LIFT_SPEED * dt) % liftPath.L;
        const [x, y] = along(liftPath, c.s);
        const fadeTop = Math.min(1, (liftPath.L - c.s) / 60);
        sprite(pic(c.full ? "chair2" : "chair"), x, y, CHAIR_H * LIFT_SCALE(y), { anchorY: .04, alpha: fadeTop });
      }

      // riders on the run
      if (t > nextRide) {
        riders.push({ t0: t, ms: rand(...RIDE_MS), who: Math.random() < .5 ? "skier" : "boarder", wob: rand(0, 6.28) });
        nextRide = t + rand(...RIDE_GAP);
      }
      for (let i = riders.length - 1; i >= 0; i--) {
        const r = riders[i], u = (t - r.t0) / r.ms;
        if (u >= 1) { riders.splice(i, 1); continue; }
        const [x, y, k] = runAt(u), [x2] = runAt(Math.min(1, u + .01));
        const carve = Math.sin(u * 18 + r.wob) * 30 * k;   // a little side to side as they carve
        sprite(pic(r.who), x + carve, y, RIDER_H * k, { flip: x2 > x, anchorY: .85, alpha: Math.min(1, u * 8) });
      }

      // chimney smoke
      if (t > nextPuff) { puffs.push({ t0: t, dx: rand(-20, 20), spin: rand(-.3, .3) }); nextPuff = t + PUFF_EVERY * rand(.7, 1.3); }
      for (let i = puffs.length - 1; i >= 0; i--) {
        const p = puffs[i], u = (t - p.t0) / PUFF_LIFE;
        if (u >= 1) { puffs.splice(i, 1); continue; }
        const x = CHIMNEY[0] + p.dx + u * 260 + Math.sin(u * 5) * 30, y = CHIMNEY[1] - u * 520;
        const a = u < .12 ? u / .12 : 1 - (u - .12) / .88;
        sprite(pic("puff"), x, y, PUFF * (.35 + u * 1.1), { alpha: .85 * a, anchorY: .6 });
      }
    }

    // snow, over everything of ours
    const heavy = mode === "zombie" ? 1 : mode === "nitro" ? .8 : .55;
    g.fillStyle = "#fff";
    for (let i = 0; i < flakes.length; i++) {
      const f = flakes[i];
      if (i / flakes.length > heavy) continue;
      f.y += f.v * dt; f.sway += f.sw * dt;
      const x = f.x + Math.sin(f.sway) * 26;
      if (f.y > PH + 20) Object.assign(f, newFlake(false));
      g.globalAlpha = f.a;
      g.beginPath(); g.arc(x, f.y, f.r, 0, 6.2832); g.fill();
    }
    g.globalAlpha = 1;
  }

  function step(t) {
    raf = 0;
    if (!live) return;
    const dt = Math.min(.1, (t - (last || t)) / 1000);
    if (t - last >= 30 || !last) { draw(t, dt); last = t; }   // ~30 fps is plenty for scenery
    raf = requestAnimationFrame(step);
  }
  function kick() { if (!raf && live && !RM) raf = requestAnimationFrame(step); }

  function start(h) {
    if (root || !h) return;
    host = h;
    root = document.createElement("div");
    root.id = "skyfx";
    root.setAttribute("aria-hidden", "true");
    Object.assign(root.style, { position: "absolute", pointerEvents: "none", zIndex: "5" });
    cv = document.createElement("canvas");
    Object.assign(cv.style, { width: "100%", height: "100%", display: "block" });
    root.appendChild(cv);
    host.appendChild(root);
    g = cv.getContext("2d");
    ["cloud", "chair", "chair2", "skier", "boarder", "puff"].forEach(pic);
    seed();
    layout();
    if (typeof ResizeObserver === "function") new ResizeObserver(layout).observe(host);
    document.addEventListener("visibilitychange", () => { live = !document.hidden; last = 0; kick(); });
    if (RM) { Object.values(pics).forEach(im => im.addEventListener("load", () => draw(performance.now(), 0), { once: true })); }
    kick();
  }

  function scene(name) {
    mode = name === "zombie" || name === "midnight" || name === "nitro" ? name : "normal";
    if (root) root.parentElement === host && host.appendChild(root);   // stay over a bonus plate laid in after us
    if (RM) draw(performance.now(), 0);
  }

  window.SkyFX = { start, layout, scene };
})();
