// High Peaks: the scene in depth (owner, 2026-11-23: "redo the background - a foreground, midground and background,
// dynamic and animated", and "blend the yeti with the background").
//
// The mountain top is no longer one flat plate. Laid exactly over the plate (#bgwall's own background, which stays
// underneath as the picture before these load and the whole picture with reduced motion), back to front:
//
//   back     the sky, the sea of far peaks, the cloud sea, the valley village
//   clouds   fat clouds crossing the sky, smaller ones passing between the far peaks   each on its own slow clock
//   pines    the pines behind the hut, swaying
//   mid      the summit we stand on: snow floor, lift hut, trail sign, cairn (the board and the yeti stand on it)
//   props    lift chairs riding the cable out and back, the flag waving on its pole, glints of light on the snow
//   (skyfx.js, above all of these: gusts of spindrift, falling snow, the hut's windows)
//   front    held to the screen's corners, not the plate: close drifts, rocks and boughs
//
// Everything is described by assets/scene/layers/layers.json (tools/highpeaks/layers_install.py), in PLATE pixels
// (3840 x 2160). The layer root is sized to the plate as the browser draws #bgwall's background, as skyfx.js does.
// NOTHING SLIDES (owner, 2026-11-23: "dont make the background and foreground move"): the layers lie still on each
// other - no drift, no lean with the mouse - and the front pieces sit in #camfar with the plate, so the camera moves
// the whole scene as one picture, as it always did. What lives is IN the picture: clouds, chairs, the flag, glints,
// snow.
// In a bonus the plate is swapped for its own scene (Scene.to): these layers rest under it; the front pieces stay and
// take that scene's light. Reduced motion: the layers are laid but nothing moves.
//
//   Layers.start(bgwall, camfar)  -> Promise<config | null>
//   Layers.layout()                 after a re-fit (placeScenery)
//   Layers.scene(name)              "normal" | "zombie" | "midnight" | "nitro"
//   Layers.mood(name)               that scene's light on the yeti: { ground, body } (hex), for Yeti.mood
(function () {
  "use strict";
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const SMALL = matchMedia("(max-width: 900px) and (max-height: 1000px), (max-height: 500px)").matches;
  const B = "assets/scene/layers/";
  const rand = (a, b) => a + Math.random() * (b - a);
  const el = (tag, cls, css) => { const e = document.createElement(tag); if (cls) e.className = cls; if (css) Object.assign(e.style, css); return e; };

  let host = null, near = null, root = null, cfg = null, rect = null, mode = "normal", ready = null;
  let PW = 3840, PH = 2160;
  const parts = { back: null, clouds: null, front: [] };
  const loops = [];            // per-frame work: the flag, the lift chairs
  let raf = 0, last = 0, live = true;

  const css = `
    #layers { position: absolute; z-index: 0; pointer-events: none; overflow: visible; contain: layout style; }
    #layers.off { visibility: hidden; }
    #layers .ly, #layers img.fill { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
    #layers img.fill { display: block; }
    #layers .lean { position: absolute; inset: 0; will-change: transform; }
    #layers .drift { position: absolute; inset: 0; }
    #layers .track { position: absolute; left: 0; width: 100%; height: 0; animation: lyCross var(--t, 90s) linear infinite; animation-delay: var(--d, 0s); }
    @keyframes lyCross { from { translate: -22% 0; } to { translate: 106% 0; } }
    #layers .track > img { position: absolute; left: 0; top: 0; display: block; }
    #layers .pine { position: absolute; display: block; transform-origin: 50% 100%; animation: lySway var(--t, 5s) ease-in-out infinite alternate; animation-delay: var(--d, 0s); }
    @keyframes lySway { from { rotate: calc(var(--a, 1deg) * -1); } to { rotate: var(--a, 1deg); } }
    #layers .glint { position: absolute; width: var(--s, 1%); aspect-ratio: 1; background: #fff; opacity: 0;
      clip-path: polygon(50% 0, 58% 42%, 100% 50%, 58% 58%, 50% 100%, 42% 58%, 0 50%, 42% 42%);
      animation: lyGlint var(--t, 6s) ease-in-out infinite; animation-delay: var(--d, 0s); }
    @keyframes lyGlint { 0%, 78%, 100% { opacity: 0; scale: .2; rotate: 0deg; } 86% { opacity: .95; scale: 1; rotate: 25deg; } 94% { opacity: 0; scale: .3; rotate: 45deg; } }
    #layers canvas.flag, #layers img.chair { position: absolute; display: block; }
    #layers.off .track, #layers.off .pine, #layers.off .glint { animation-play-state: paused; }
    .lyfront { position: absolute; z-index: 3; display: block; pointer-events: none; user-select: none; transition: filter .9s ease;
      filter: brightness(.86) saturate(.96); }
    [data-lyscene="zombie"] > .lyfront { filter: brightness(.92) saturate(.9) sepia(.12) hue-rotate(-20deg); }
    [data-lyscene="midnight"] > .lyfront { filter: brightness(.5) saturate(.85) hue-rotate(12deg); }
    [data-lyscene="nitro"] > .lyfront { filter: brightness(.76) saturate(1.1) sepia(.28); }
    @media (prefers-reduced-motion: reduce) { #layers .track, #layers .pine, #layers .glint { animation: none !important; } #layers .glint { display: none; } }
  `;

  // the plate's box inside host, from host's own computed background (as skyfx.js and scenefx.js)
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
    return { x: at(pos[0] || "50%", W - pw), y: at(pos[1] || "50%", H - ph), w: pw, h: ph, s };
  }
  const pct = (v, of) => (v / of * 100).toFixed(3) + "%";
  const src = name => B + (SMALL && /^(back|mid)\.webp$/.test(name) ? name.replace(".webp", "_m.webp") : name);
  const img = (name, cls) => { const im = new Image(); im.alt = ""; im.draggable = false; im.decoding = "async"; if (cls) im.className = cls; im.src = src(name); return im; };

  // ---------------------------------------------------------------- build
  function build() {
    const st = document.createElement("style");
    st.textContent = css;
    document.head.appendChild(st);
    root = el("div"); root.id = "layers"; root.setAttribute("aria-hidden", "true");

    // back: the far distance
    const back = el("div", "ly"), bl = el("div", "lean"), bd = el("div", "drift");
    const bi = img(cfg.back.src, "fill");
    bd.appendChild(bi); bl.appendChild(bd); back.appendChild(bl); root.appendChild(back);
    parts.back = { lean: bl, drift: bd };

    // clouds: over the back, under the summit
    const cl = el("div", "ly"), cll = el("div", "lean");
    cl.appendChild(cll); root.appendChild(cl);
    parts.clouds = { lean: cll };
    const cloud = (band, hgt, secs, op) => {
      const t = el("div", "track", { top: pct(rand(band[0], band[1]), PH), opacity: String(op) });
      t.style.setProperty("--t", secs.toFixed(0) + "s");
      t.style.setProperty("--d", (-rand(0, secs)).toFixed(0) + "s");
      const im = new Image(); im.alt = ""; im.draggable = false; im.src = "assets/scene/cloud.webp";
      Object.assign(im.style, { width: pct(hgt * 1.9, PW), translate: "0 -50%" });
      if (Math.random() < .5) im.style.scale = "-1 1";
      t.appendChild(im); cll.appendChild(t);
    };
    const C = cfg.clouds || {};
    // (2026-11-26, owner: "we want clouds always moving": a crossing took 150 - 420 s, which reads as still)
    if (C.high) for (let i = 0; i < 5; i++) cloud(C.high, rand(170, 270), rand(48, 84), .95);
    if (C.low) for (let i = 0; i < 6; i++) cloud(C.low, rand(70, 130), rand(80, 140), .8);

    // the pines behind the hut
    for (const p of cfg.pines || []) {
      const im = img(p.src, "pine");
      Object.assign(im.style, { left: pct(p.x - p.h * p.aspect / 2, PW), top: pct(p.y - p.h, PH), width: pct(p.h * p.aspect, PW) });
      im.style.setProperty("--a", (p.sway || 1.1) + "deg");
      im.style.setProperty("--t", rand(3.6, 6.2).toFixed(1) + "s");
      im.style.setProperty("--d", (-rand(0, 6)).toFixed(1) + "s");
      root.appendChild(im);
    }

    // mid: the summit
    const mid = el("div", "ly");
    mid.appendChild(img(cfg.mid.src, "fill"));
    root.appendChild(mid);

    // props on the summit
    const props = el("div", "ly");
    root.appendChild(props);
    if (cfg.lift) lift(props, cfg.lift);
    if (cfg.flag) flag(props, cfg.flag);
    const S = cfg.sparkle;
    if (S && !RM) for (let i = 0; i < (S.n || 8); i++) {
      const g = el("i", "glint", { left: pct(rand(S.box[0], S.box[2]), PW), top: pct(rand(S.box[1], S.box[3]), PH) });
      g.style.setProperty("--s", rand(.55, 1.1).toFixed(2) + "%");
      g.style.setProperty("--t", rand(4.5, 9).toFixed(1) + "s");
      g.style.setProperty("--d", (-rand(0, 9)).toFixed(1) + "s");
      props.appendChild(g);
    }
    // under skyfx (its snow falls over all of this) and under a bonus plate (#bgalt, z-index 1)
    host.insertBefore(root, host.firstChild);

    // front: held to the screen's corners, in the plate's own camera layer
    if (near) for (const f of cfg.front || []) {
      const im = img(f.src, "lyfront");
      near.appendChild(im);
      parts.front.push({ im, f });
    }
    if (near) near.dataset.lyscene = mode;
  }

  // The lift: chairs ride the cable away from the hut and come back on the far side of it. `out` and `back` are the
  // two runs as points [x, y, size] in plate px (size: the chair's height there - it shrinks with distance).
  function lift(props, L) {
    const chairs = [];
    const n = L.chairs || 5;
    for (let i = 0; i < n; i++) {
      const im = img(L.src, "chair");
      props.appendChild(im);
      chairs.push({ im, u: i / n });
    }
    const runs = [L.out, L.back || L.out.slice().reverse().map(p => [p[0] + (L.gap || 30), p[1] - (L.gap || 30) * .2, p[2] * .92])];
    const lens = runs.map(r => r.slice(1).map((p, i) => Math.hypot(p[0] - r[i][0], p[1] - r[i][1])));
    const tot = lens.map(l => l.reduce((a, b) => a + b, 0));
    const at = (run, d) => {
      const r = runs[run], l = lens[run];
      let i = 0;
      while (i < l.length - 1 && d > l[i]) { d -= l[i]; i++; }
      const k = Math.max(0, Math.min(1, d / l[i]));
      return [0, 1, 2].map(j => r[i][j] + (r[i + 1][j] - r[i][j]) * k);
    };
    const secs = L.secs || 46, aspect = L.aspect || 1;
    loops.push(t => {
      for (const c of chairs) {
        const u = (c.u + t / 1000 / secs) % 1, run = u < .5 ? 0 : 1, v = (u < .5 ? u : u - .5) * 2;
        const [x, y, h] = at(run, v * tot[run]);
        const fade = Math.min(1, v / .04, (1 - v) / .04);
        const sw = Math.sin(t / 900 + c.u * 9) * 2.2;                   // a chair swings a little on its grip
        c.im.style.cssText = `left:${pct(x - h * aspect / 2, PW)};top:${pct(y, PH)};width:${pct(h * aspect, PW)};opacity:${fade.toFixed(2)};` +
          `transform-origin:50% 0;transform:rotate(${sw.toFixed(2)}deg);z-index:${run ? 0 : 1}`;
      }
    });
  }

  // The flag: its cloth drawn in upright strips, each lifted by a wave that runs out from the pole and grows toward
  // the free end.
  function flag(props, F) {
    const cv = el("canvas", "flag", { left: pct(F.x, PW), top: pct(F.y - F.h * .25, PH), width: pct(F.w * 1.08, PW) });
    const im = img(F.src);
    props.appendChild(cv);
    const N = 26;
    let g = null, cw = 0, ch = 0;
    const size = () => {
      const k = Math.max(.25, Math.min(1, (rect ? rect.s : .3) * Math.min(2, devicePixelRatio || 1)));
      cw = Math.max(16, Math.round(F.w * 1.08 * k)); ch = Math.max(16, Math.round(F.h * 1.5 * k));
      cv.width = cw; cv.height = ch; g = cv.getContext("2d");
    };
    size();
    loops.push((t, resized) => {
      if (resized) size();
      if (!im.complete || !im.naturalWidth) return;
      g.clearRect(0, 0, cw, ch);
      const w = cw / 1.08, h = ch / 1.5, sw = im.naturalWidth / N;
      for (let i = 0; i < N; i++) {
        const u = i / (N - 1);
        const lift = Math.sin(t / 260 - u * 5.2) * .13 * u + Math.sin(t / 610 - u * 2.1) * .06 * u;
        const squeeze = 1 - .05 * u * (1 + Math.sin(t / 260 - u * 5.2 + 1.2));
        g.drawImage(im, i * sw, 0, sw + .5, im.naturalHeight, u * w * squeeze * (N - 1) / N, h * .25 + lift * h, w / N * squeeze + .8, h);
      }
    });
    if (RM) im.addEventListener("load", () => { loops[loops.length - 1](0, true); }, { once: true });
  }

  // ---------------------------------------------------------------- layout
  function layout() {
    if (!root) return;
    rect = plateBox();
    Object.assign(root.style, { left: rect.x.toFixed(1) + "px", top: rect.y.toFixed(1) + "px", width: rect.w.toFixed(1) + "px", height: rect.h.toFixed(1) + "px" });
    // the front pieces: sized by the window's height, set into its corners
    const W = innerWidth, H = innerHeight;
    for (const { im, f } of parts.front) {
      // (an upright phone: by its width, so the two corners never meet)
      const h = f.h * Math.min(H, W * .75), w = h * f.aspect, ix = (f.inset ? f.inset[0] : 0) * W, iy = (f.inset ? f.inset[1] : 0) * H;
      const s = { width: w.toFixed(1) + "px", height: h.toFixed(1) + "px", left: "", right: "", top: "", bottom: "" };
      s[f.corner[1] === "l" ? "left" : "right"] = ix.toFixed(1) + "px";
      s[f.corner[0] === "t" ? "top" : "bottom"] = iy.toFixed(1) + "px";
      Object.assign(im.style, s);
      if (f.flip) im.style.scale = "-1 1";
    }
    resized = true;
    kick();
  }
  let resized = false;

  // ---------------------------------------------------------------- the frame: the lift, the flag
  function frame(t) {
    raf = 0;
    if (!live) return;
    const busy = loops.length && mode === "normal" && !RM;
    if (busy && t - last >= 32) {
      for (const f of loops) f(t, resized);
      resized = false; last = t;
    }
    if (busy) raf = requestAnimationFrame(frame);
  }
  function kick() { if (!raf && live && root) raf = requestAnimationFrame(frame); }

  // ---------------------------------------------------------------- api
  function start(h, n) {
    if (ready) return ready;
    host = h; near = n;
    ready = fetch(B + "layers.json").then(r => r.ok ? r.json() : Promise.reject(new Error("layers.json " + r.status))).then(c => {
      cfg = c; [PW, PH] = c.size || [3840, 2160];
      build(); layout();
      if (typeof ResizeObserver === "function") new ResizeObserver(layout).observe(host);
      addEventListener("resize", layout);
      document.addEventListener("visibilitychange", () => { live = !document.hidden; last = 0; kick(); });
      if (RM) for (const f of loops) f(0, true);
      // the sky's clouds and the hut's windows are ours now (skyfx keeps its own on a bonus plate)
      if (window.SkyFX && SkyFX.own) SkyFX.own({ clouds: true, windows: c.windows });
      scene(mode);
      return c;
    }).catch(e => { console.warn("layered scene unavailable:", e.message); return null; });
    return ready;
  }
  function scene(name) {
    mode = name === "zombie" || name === "midnight" || name === "nitro" ? name : "normal";
    if (root) root.classList.toggle("off", mode !== "normal");
    if (near) near.dataset.lyscene = mode;
    last = 0; kick();
  }
  const mood = name => (cfg && cfg.moods && (cfg.moods[name] || cfg.moods.normal)) || null;

  window.Layers = { start, layout, scene, mood, get config() { return cfg; }, get ready() { return ready; } };
})();
