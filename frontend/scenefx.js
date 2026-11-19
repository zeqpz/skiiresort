// The Falcos scene's life, laid exactly over the night plate (#bgwall's background, bonus_wall.webp):
// the canopy's FALCOS neon now and then stuttering off (sign_off). The scene has no people any more
// (2026-11-12, tools/falcos/clear_scene.py): the woman, her car and the people in the shop window are gone
// from the plates, and with them their blinks and loops (blink_woman / blink_cashier, fx_arm / fx_people /
// fx_cashier). The loop and blink machinery stays, for any layer scene.json lists.
//
// Everything is described by assets/scene/scene.json in PLATE pixels (the plate is 3840x2160).
// The layer (#scenefx) is put inside #bgwall and sized to the plate exactly as the browser draws
// #bgwall's background - its computed background-size (cover / contain) and background-position
// read straight off the element, so it can never drift from the picture at any window size or
// orientation - and every overlay sits in it in percent of the plate. Being inside #bgwall it
// rides the wall's lean, hop and the camera with it.
//
// The loops ship as grid frame sheets ({w, h, cols, per_sheet, sheets[], frames, fps}); each is
// drawn on a canvas, one frame at a time at its own 30 fps, decoded once at the size the screen
// shows it (never above the sheet's own). A loop whose box is off the screen (a phone in portrait
// shows only part of the plate) is not fetched until it would show. Nothing runs while the tab is
// hidden; with reduced motion the loops hold their first frame and nothing flickers or blinks.
//
//   SceneFX.start(hostElement)   once, with #bgwall
//   SceneFX.surge()              a nervous stutter of the sign right now (a big win)
(function () {
  "use strict";
  const BASE = "assets/scene/";
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // the neon: mostly on, now and then a stutter (art/falcos/previews/showcase reference)
  const NEON_GAP = [1800, 6000];                                  // ms between stutters
  const NEON_SHORT = [90, 70], NEON_LONG = [70, 60, 50, 120, 40, 260], NEON_LONG_ODDS = .3;
  const BLINK_MS = 130, BLINKS = {};   // name -> [min, max] ms between blinks
  // Two failing letters (owner, 2026-11-12: "only have a couple letters flicker but make it seem like a realistic
  // flicker"; tools/falcos/sign_letters.py cuts their off-state pieces). The rest of the sign burns steady. Each letter
  // runs its own fault on its own clock: long stretches lit, then an episode - a buzz (a ragged burst of drop-outs,
  // some only half way, the way a tired electrode arcs), a drop-out (dark for a moment, then it sputters back) or a
  // brown-out (a dim waver). The S is the worse of the two.
  const FAULTS = { sign_off_l: { gap: [4500, 14000], weights: [.55, .2, .25] },
                   sign_off_s: { gap: [2200, 8000], weights: [.45, .35, .2] } };

  let host = null, root = null, cfg = null, rect = null;
  const els = {}, loops = [], timers = new Set();
  let raf = 0, live = false;

  const later = (ms, fn) => { const id = setTimeout(() => { timers.delete(id); fn(); }, ms); timers.add(id); return id; };
  const rand = (a, b) => a + Math.random() * (b - a);

  function pct(r) {
    const [W, H] = cfg.size;
    return { left: r[0] / W * 100 + "%", top: r[1] / H * 100 + "%", width: r[2] / W * 100 + "%", height: r[3] / H * 100 + "%" };
  }

  // where the plate is drawn inside host, in host px - from host's own computed background
  function plateBox() {
    const W = host.clientWidth, H = host.clientHeight, cs = getComputedStyle(host);
    const [pw0, ph0] = cfg.size;
    const size = (cs.backgroundSize || "cover").split(",").pop().trim();
    let s;
    if (size === "contain") s = Math.min(W / pw0, H / ph0);
    else if (size === "cover") s = Math.max(W / pw0, H / ph0);
    else {   // "<w> <h>" in px or % ("auto" for one of them): the plate keeps its shape
      const [w, h = "auto"] = size.split(/\s+/);
      const len = (v, box, nat) => v.endsWith("%") ? box * parseFloat(v) / 100 / nat : v.endsWith("px") ? parseFloat(v) / nat : null;
      s = len(w, W, pw0) ?? len(h, H, ph0) ?? Math.max(W / pw0, H / ph0);
    }
    const pw = pw0 * s, ph = ph0 * s;
    const pos = (cs.backgroundPosition || "50% 50%").split(",").pop().trim().split(/\s+/);
    const at = (v, free) => v.endsWith("%") ? free * parseFloat(v) / 100 : v.endsWith("px") ? parseFloat(v) : free / 2;
    return { x: at(pos[0] || "50%", W - pw), y: at(pos[1] || "50%", H - ph), w: pw, h: ph, s };
  }

  function layout() {
    if (!root || !cfg) return;
    rect = plateBox();
    Object.assign(root.style, { left: rect.x.toFixed(2) + "px", top: rect.y.toFixed(2) + "px",
                                width: rect.w.toFixed(2) + "px", height: rect.h.toFixed(2) + "px" });
    for (const L of loops) wantLoop(L);
  }

  /* ---------- the loops ---------- */
  function onScreen(el) {
    const r = el.getBoundingClientRect();
    return r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight && r.width > 0;
  }
  // fetch a loop's sheets once it would show, decoded at the size the screen draws it
  function wantLoop(L) {
    if (L.loading || !onScreen(L.cv)) return;
    const shown = L.cv.getBoundingClientRect().width * Math.min(window.devicePixelRatio || 1, 1.5);
    const k = Math.max(.35, Math.min(1, shown / L.d.w * 1.1));
    L.loading = Promise.all(L.d.sheets.map(async name => {
      const blob = await fetch(BASE + name).then(r => r.ok ? r.blob() : Promise.reject(new Error(name + " " + r.status)));
      const im = new Image();
      im.src = URL.createObjectURL(blob);
      await im.decode();
      // always held as an ImageBitmap (perf, 2026-11-10): drawn from the <img> itself, the browser was free to
      // drop its decoded pixels and decode the whole sheet again on the main thread - 200-340 ms stalls every
      // second or two on a phone, the game's worst lag (compress_assets.py also cut the sheets ~9x)
      if (typeof createImageBitmap === "function") {
        try {
          const bm = k < .97 ? await createImageBitmap(im, { resizeWidth: Math.round(im.naturalWidth * k), resizeHeight: Math.round(im.naturalHeight * k), resizeQuality: "high" })
                             : await createImageBitmap(im);
          URL.revokeObjectURL(im.src);
          return { src: bm, k: k < .97 ? k : 1 };
        } catch (e) { /* no bitmap: the sheet as it is */ }
      }
      return { src: im, k: 1 };
    })).then(sheets => {
      L.sheets = sheets;
      const k = sheets[0].k;
      L.cv.width = Math.round(L.d.w * k); L.cv.height = Math.round(L.d.h * k);
      L.f = -1; L.t0 = performance.now() - Math.random() * L.d.frames / L.d.fps * 1000;   // each starts somewhere in its loop
      draw(L, 0);
      kick();
    }).catch(e => { console.warn("scene loop:", e.message); });
  }
  function draw(L, f) {
    if (!L.sheets || f === L.f) return;
    const d = L.d, si = Math.floor(f / d.per_sheet), i = f % d.per_sheet, sh = L.sheets[si];
    if (!sh) return;
    const k = sh.k, w = Math.round(d.w * k), h = Math.round(d.h * k);
    const g = L.ctx;
    g.clearRect(0, 0, L.cv.width, L.cv.height);
    g.drawImage(sh.src, (i % d.cols) * d.w * k, Math.floor(i / d.cols) * d.h * k, w, h, 0, 0, L.cv.width, L.cv.height);
    L.f = f;
  }
  function step(now) {
    raf = 0;
    if (!live || RM) return;
    for (const L of loops) if (L.sheets) draw(L, Math.floor((now - L.t0) / 1000 * L.d.fps) % L.d.frames);
    raf = requestAnimationFrame(step);
  }
  function kick() { if (live && !RM && !raf && loops.some(L => L.sheets)) raf = requestAnimationFrame(step); }

  /* ---------- the sign and the blinks ---------- */
  function stutter(seq) {
    const off = els.sign_off;
    if (!off) return 0;
    let t = 0;
    seq.forEach((ms, i) => { later(t, () => { off.style.opacity = i % 2 ? "0" : (.75 + Math.random() * .25).toFixed(2); }); t += ms; });
    later(t, () => { off.style.opacity = "0"; });
    return t;
  }
  function neon() {   // the whole sign's stutter: the big win's only now (surge); idle, only the faulty letters go
    if (!live) return;
    const t = stutter(Math.random() < NEON_LONG_ODDS ? NEON_LONG : NEON_SHORT);
    later(t + rand(...NEON_GAP), neon);
  }
  // one letter's episode as [opacity of its off piece, ms] steps (0 = lit, 1 = dark); it always ends lit
  function episode(kind) {
    const s = [];
    if (kind === 0) {                       // buzz: 5-14 ragged flickers, 15-90 ms each, some only half dark
      const n = 5 + Math.floor(Math.random() * 10);
      for (let i = 0; i < n; i++) {
        s.push([Math.random() < .3 ? rand(.35, .7) : rand(.8, 1), rand(15, 90)]);
        s.push([0, rand(20, i === n - 1 ? 60 : 140)]);
      }
    } else if (kind === 1) {                // drop-out: dark 0.3-2.2 s, then sputters back on with 2-5 catches
      s.push([1, rand(40, 90)], [0, rand(30, 70)], [1, rand(300, 2200)]);
      const n = 2 + Math.floor(Math.random() * 4);
      for (let i = 0; i < n; i++) s.push([0, rand(25, 110)], [rand(.6, 1), rand(30, 160)]);
    } else {                                // brown-out: wavers dim two or three times
      const n = 2 + Math.floor(Math.random() * 2);
      for (let i = 0; i < n; i++) s.push([rand(.3, .6), rand(90, 380)], [rand(0, .12), rand(60, 200)]);
    }
    s.push([0, 0]);
    return s;
  }
  function fault(name) {
    const el = els[name], f = FAULTS[name];
    if (!live || !el) return;
    const r = Math.random();
    const kind = r < f.weights[0] ? 0 : r < f.weights[0] + f.weights[1] ? 1 : 2;
    let t = 0;
    for (const [op, ms] of episode(kind)) { later(t, () => { el.style.opacity = op.toFixed(2); }); t += ms; }
    // now and then the fault comes straight back (a letter on its way out rarely fails just once)
    later(t + (Math.random() < .25 ? rand(300, 1200) : rand(...f.gap)), () => fault(name));
  }
  function blink(name) {
    const el = els[name];
    if (!live || !el) return;
    el.style.opacity = "1";
    later(BLINK_MS, () => { el.style.opacity = "0"; });
    later(rand(...BLINKS[name]), () => blink(name));
  }

  function run() {
    if (live || RM || document.hidden) return;
    live = true;
    for (const name of Object.keys(FAULTS)) later(rand(800, FAULTS[name].gap[0]), () => fault(name));
    for (const name of Object.keys(BLINKS)) later(rand(400, BLINKS[name][0]), () => blink(name));
    for (const L of loops) if (L.sheets) L.t0 = performance.now() - (L.f > 0 ? L.f : 0) / L.d.fps * 1000;   // carry on where it was
    kick();
  }
  function halt() {
    live = false;
    for (const id of timers) clearTimeout(id);
    timers.clear();
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    for (const k of ["sign_off", ...Object.keys(BLINKS), ...Object.keys(FAULTS)]) if (els[k]) els[k].style.opacity = "0";
  }

  async function start(el) {
    if (host || !el) return;
    host = el;
    try {
      cfg = await fetch(BASE + "scene.json").then(r => r.ok ? r.json() : Promise.reject(new Error("scene.json " + r.status)));
    } catch (e) { console.warn("scene fx unavailable:", e.message); return; }
    root = document.createElement("div");
    root.id = "scenefx";
    root.setAttribute("aria-hidden", "true");
    root.style.cssText = "position:absolute;pointer-events:none;overflow:visible;z-index:0";
    // the loops under the stills: the sign's off state and the closed eyes paint over them
    for (const [name, d] of Object.entries(cfg.layers)) {
      if (!d.sheets) continue;
      const cv = document.createElement("canvas");
      cv.className = "sfxloop " + name;
      Object.assign(cv.style, { position: "absolute", display: "block" }, pct(d.rect));
      root.appendChild(cv);
      loops.push({ name, d, cv, ctx: cv.getContext("2d"), sheets: null, loading: null, f: -1, t0: 0 });
    }
    for (const [name, d] of Object.entries(cfg.layers)) {
      if (d.sheets) continue;
      const im = new Image();
      im.alt = ""; im.draggable = false; im.decoding = "async";
      im.className = "sfxstill " + name;
      im.src = BASE + name + ".webp";
      Object.assign(im.style, { position: "absolute", display: "block", opacity: "0" }, pct(d.rect));
      root.appendChild(im);
      els[name] = im;
    }
    host.prepend(root);
    layout();
    let pend = 0;   // re-laid on the next frame, never inside the observer's own pass
    if (window.ResizeObserver) new ResizeObserver(() => { if (!pend) pend = requestAnimationFrame(() => { pend = 0; layout(); }); }).observe(host);
    addEventListener("resize", layout);
    document.addEventListener("visibilitychange", () => (document.hidden ? halt() : run()));
    run();
  }

  window.SceneFX = {
    start,
    surge() { if (live) stutter(NEON_LONG); },
    layout,
    // the base game's letter faults, for a scene laid over this one (PREMIUM's plate: index.html's Scene)
    episode, FAULTS,
  };
})();
