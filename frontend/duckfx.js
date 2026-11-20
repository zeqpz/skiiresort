// High Peaks: the duck - the main character standing by the board (owner, 2026-11-18). Modelled, rigged and animated
// in Blender (tools/highpeaks/blender: duck_build.py, duck_anim.py, duck_render.py), packed into sheets by
// tools/highpeaks/pack_duck.py: assets/duck/duck.json + assets/duck/<clip>_<n>.webp.
//
// It plays one clip at a time on a canvas, on ones (24 fps). Between events it idles: a
// few loops of breathing and droopy blinks, then a routine at random - looking over at the reels, rolling a joint,
// smoking it, a bong rip - each pulling the gear out and putting it away again. Game events cut in with a reaction:
//   Duck.react("win")    a hop and a wing pump (a cluster pays)
//   Duck.react("mult")   whoa (a multiplier lands, a feature fires)
//   Duck.react("bonus")  a happy dance (a bonus triggers, a big win, a jackpot)
//   Duck.react("tease")  a shrug (a teased bonus that never came, a small bonus total)
//   Duck.bonus(on)       in a bonus round it bobs to the music instead of smoking
// A stronger reaction is never cut short by a weaker one. Sheets load lazily, idle first; nothing runs while the tab is
// hidden; with reduced motion it holds the first idle frame. Every clip starts and ends on the same rest pose, so they
// chain cleanly; when a reaction cuts in mid-clip, the frame it cut from fades out over the new one (FADE ms).
(function () {
  "use strict";
  const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const BASE = "assets/duck/";
  const RANK = { win: 1, tease: 1, mult: 2, bonus: 3 };
  const ROUTINES = [["look", 3], ["roll", 2], ["smoke", 2], ["bong", 2]];
  const FADE = 160;
  let meta = null, cv = null, g = null, el = null, ghost = null, gg = null, ghostT = -1;
  const sheets = {};          // clip -> [ImageBitmap | Image] once loaded
  let clip = "idle", f = 0, t0 = 0, raf = 0, live = true, loopsLeft = 2, inBonus = false, rank = 0;

  const pickRoutine = () => {
    const pool = inBonus ? [["look", 1]] : ROUTINES;
    let r = Math.random() * pool.reduce((a, [, w]) => a + w, 0);
    for (const [n, w] of pool) if ((r -= w) <= 0) return n;
    return pool[0][0];
  };
  const baseLoop = () => (inBonus ? "bonusidle" : "idle");

  function load(name) {
    if (sheets[name] || !meta || !meta.clips[name]) return sheets[name] && sheets[name].ready;
    const c = meta.clips[name];
    const rec = { imgs: [], ready: null };
    sheets[name] = rec;
    rec.ready = Promise.all(c.sheets.map(async (file, i) => {
      const im = new Image();
      im.src = BASE + file;
      await im.decode();
      rec.imgs[i] = typeof createImageBitmap === "function" ? await createImageBitmap(im).catch(() => im) : im;
    })).then(() => { rec.ok = true; }).catch(e => console.warn("duck sheet:", e.message));
    return rec.ready;
  }
  const ready = name => sheets[name] && sheets[name].ok;

  function play(name, r = 0, cut = false) {
    if (!meta || !meta.clips[name]) return;
    if (cut && f > 2 && ghost) {           // cutting in mid-clip: keep the frame we leave, to fade it out
      if (ghost.width !== cv.width || ghost.height !== cv.height) { ghost.width = cv.width; ghost.height = cv.height; }
      gg.clearRect(0, 0, ghost.width, ghost.height);
      gg.drawImage(cv, 0, 0);
      ghostT = performance.now();
    }
    load(name);
    clip = name; f = 0; t0 = performance.now(); rank = r;
    if (name === "idle" || name === "bonusidle") loopsLeft = 1 + Math.floor(Math.random() * 3);
  }

  function next() {
    rank = 0;
    if (clip === "idle" || clip === "bonusidle") {
      if (--loopsLeft > 0) { play(clip); return; }
      const r = pickRoutine();
      if (ready(r)) { play(r); return; }
      load(r);
      play(baseLoop());
      return;
    }
    play(baseLoop());
  }

  function draw() {
    const c = meta.clips[clip], rec = sheets[clip];
    if (!rec || !rec.ok) {   // not loaded yet: the idle's first frame if that is in
      if (clip !== "idle" && ready("idle")) { const k = clip; clip = "idle"; draw(); clip = k; }
      return;
    }
    const si = Math.floor(f / c.per_sheet), i = f % c.per_sheet, im = rec.imgs[si];
    if (!im) return;
    g.clearRect(0, 0, cv.width, cv.height);
    if (ghostT >= 0) {
      const k = (performance.now() - ghostT) / FADE;
      if (k >= 1) ghostT = -1;
      else {
        g.globalAlpha = Math.min(1, .35 + .65 * k);
        g.drawImage(im, (i % c.cols) * meta.w, Math.floor(i / c.cols) * meta.h, meta.w, meta.h, 0, 0, cv.width, cv.height);
        g.globalAlpha = 1 - k;
        g.drawImage(ghost, 0, 0);
        g.globalAlpha = 1;
        return;
      }
    }
    g.drawImage(im, (i % c.cols) * meta.w, Math.floor(i / c.cols) * meta.h, meta.w, meta.h, 0, 0, cv.width, cv.height);
  }

  function step(now) {
    raf = 0;
    if (!live) return;
    const c = meta.clips[clip];
    if (ready(clip)) {
      const nf = Math.floor((now - t0) / 1000 * meta.fps);
      if (nf >= c.frames) { next(); }
      else if (nf !== f) { f = nf; }
    } else {
      t0 = now;   // hold the clock until its sheet is in
    }
    draw();
    raf = requestAnimationFrame(step);
  }
  const kick = () => { if (!raf && live && !RM) raf = requestAnimationFrame(step); };

  function size() {
    if (!cv || !el) return;
    const r = el.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(1, Math.round(el.clientWidth * dpr)), h = Math.max(1, Math.round(el.clientHeight * dpr));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; if (meta) draw(); }
    return r;
  }

  async function start(host) {
    el = host;
    if (!el) return;
    cv = document.createElement("canvas");
    cv.setAttribute("aria-hidden", "true");
    el.appendChild(cv);
    g = cv.getContext("2d");
    ghost = document.createElement("canvas");
    gg = ghost.getContext("2d");
    try { meta = await fetch(BASE + "duck.json").then(r => r.ok ? r.json() : Promise.reject(new Error("duck.json " + r.status))); }
    catch (e) { console.warn("duck unavailable:", e.message); el.hidden = true; return; }
    el.style.aspectRatio = `${meta.w} / ${meta.h}`;
    size();
    if (typeof ResizeObserver === "function") new ResizeObserver(size).observe(el);
    await load("idle");
    play("idle");
    draw();
    // the rest in the background, the reactions first
    for (const n of ["win", "mult", "bonus", "tease", "look", "bonusidle", "roll", "smoke", "bong"]) await load(n);
    document.addEventListener("visibilitychange", () => { live = !document.hidden; t0 = performance.now() - f / meta.fps * 1000; kick(); });
    kick();
  }

  function react(kind) {
    if (!meta || !meta.clips[kind] || RM) return;
    if ((RANK[kind] || 0) < rank) return;   // a bigger reaction is still playing
    play(kind, RANK[kind] || 0, true);
    kick();
  }
  function bonus(on) {
    inBonus = !!on;
    if (rank === 0) play(baseLoop(), 0, true);
  }

  window.Duck = { start, react, bonus };
})();
