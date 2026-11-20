// High Peaks: the scene's life (owner, 2026-11-18: "we don't want it static"), drawn on one canvas laid exactly over the
// background plate (#bgwall's background, bonus_wall.webp = art/highpeaks/raw/peak_plate.png - the mountain top,
// peak pass 2026-11-19):
//
//   * fat clouds drifting across the sky
//   * green smoke puffs rising from the summit hut's chimney
//   * the hut's windows glowing and flickering softly
//   * gusts of spindrift: now and then the wind lifts a sheet of loose snow across the summit
//   * snow falling over the whole scene (heavier in FRESH POWDER)
//
// No people (owner, 2026-11-19: "get rid of the people going down the slope as skiers"): the skiers and snowboarders
// on the run and the lift's riders are gone - the lift's chairs are painted, standing at the top station.
//
// Every place is in PLATE pixels (3840x2160), read off the plate (peak_plate gridded). The layer is sized to the plate
// as the browser draws #bgwall's background (cover / position), the same way scenefx.js does, so it never drifts from
// the picture. In a bonus the plate is swapped for its own scene (Scene.to): the smoke and the windows belong to the
// base plate and rest; the clouds, the spindrift and the snow carry on. One rAF loop at ~30 fps, paused while the tab
// is hidden; with reduced motion only a still frame is drawn.
//
//   SkyFX.start(host)     once, with #bgwall
//   SkyFX.layout()        after a re-fit (placeScenery)
//   SkyFX.scene(name)     "normal" | "zombie" (FRESH POWDER) | "midnight" (BLACK DIAMOND) | "nitro" (AVALANCHE)
(function () {
  "use strict";
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PW = 3840, PH = 2160;
  const B = "assets/scene/";
  const CHIMNEY = [652, 742], PUFF = 150, PUFF_EVERY = 900, PUFF_LIFE = 5200;
  const WINDOWS = [[755, 1170, 190, 130], [515, 1158, 90, 100]];
  const SKY = [40, 380];        // the band the clouds drift in
  const GROUND = [1480, 2120];  // the summit's snow floor, where the spindrift blows
  const GUST_GAP = [3500, 9000], GUST_MS = 2600;

  let host = null, root = null, cv = null, g = null, rect = null, scale = 1;
  let raf = 0, last = 0, now0 = 0, mode = "normal", live = true;
  const pics = {};
  const puffs = [], clouds = [], flakes = [], drift = [];
  let nextPuff = 0, nextGust = 2500;
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

  // ---------------------------------------------------------------- setup
  function seed() {
    for (let i = 0; i < 3; i++) clouds.push({ x: rand(-400, PW), y: rand(SKY[0], SKY[1]), v: rand(10, 22), k: rand(.7, 1.25) });
    for (let i = 0; i < 160; i++) flakes.push(newFlake(true));
  }
  function newFlake(anywhere) {
    const z = Math.random();   // depth: near flakes are bigger, faster, brighter
    return { x: rand(0, PW), y: anywhere ? rand(0, PH) : rand(-60, -10), r: 3 + z * 9, v: 40 + z * 110, sway: rand(0, 6.28),
             sw: rand(.4, 1.2), a: .45 + z * .5 };
  }

  // ---------------------------------------------------------------- drawing
  function sprite(im, x, y, h, { flip = false, alpha = 1, anchorY = .5, src = null } = {}) {
    if (!ok(im)) return;
    const [sx, sy, sw, sh] = src || [0, 0, im.naturalWidth, im.naturalHeight];
    const w = h * sw / sh;
    g.save();
    g.globalAlpha = alpha;
    g.translate(x, y);
    if (flip) g.scale(-1, 1);
    g.drawImage(im, sx, sy, sw, sh, -w / 2, -h * anchorY, w, h);
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

    // spindrift: a gust lifts a sheet of loose snow off the summit and blows it across, low and fast
    if (!RM && t > nextGust) {
      const y0 = rand(GROUND[0], GROUND[1] - 160), dir = Math.random() < .5 ? -1 : 1, n = 70;
      for (let i = 0; i < n; i++) drift.push({ t0: t + rand(0, 700), ms: GUST_MS * rand(.7, 1.15), y: y0 + rand(-90, 90),
        x0: dir > 0 ? rand(-500, 900) : rand(PW - 900, PW + 500), v: dir * rand(900, 1500), r: rand(2.5, 6.5),
        lift: rand(30, 150), ph: rand(0, 6.28) });
      nextGust = t + rand(...GUST_GAP);
    }
    g.fillStyle = "#fff";
    for (let i = drift.length - 1; i >= 0; i--) {
      const p = drift[i], u = (t - p.t0) / p.ms;
      if (u >= 1) { drift.splice(i, 1); continue; }
      if (u < 0) continue;
      const x = p.x0 + p.v * u * p.ms / 1000, y = p.y - Math.sin(u * Math.PI) * p.lift + Math.sin(u * 9 + p.ph) * 14;
      g.globalAlpha = .75 * Math.sin(Math.PI * u);
      g.beginPath(); g.arc(x, y, p.r, 0, 6.2832); g.fill();
    }
    g.globalAlpha = 1;

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
    ["cloud", "puff"].forEach(pic);
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
