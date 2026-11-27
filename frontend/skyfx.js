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
  const SMOKE = false;
  const CHIMNEY = [652, 742], PUFF = 150, PUFF_EVERY = 900, PUFF_LIFE = 5200;
  let WINDOWS = [[755, 1170, 190, 130], [515, 1158, 90, 100]];
  let layered = false;          // layers.js draws the base scene's clouds (between its far and middle layers)
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
  const ok = im => !!im && (im.getContext ? im.width > 0 : im.complete && im.naturalWidth > 0);   // a picture, or a canvas made from one

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
  // (owner, 2026-11-26: "make all of the backgrounds actually dynamic, all of the different featured ones as well - we
  // want clouds always moving, thunder moving, anything dynamic moving / animated", and "we want the northern lights
  // moving as well in the sky") Every scene has weather of its own now, all of it IN the picture (nothing slides):
  //   every scene     clouds crossing the sky all the time, in two depths (they used to take three minutes to cross);
  //                   the snow leans with a wind that gusts
  //   the day         now and then a few birds cross high up
  //   FRESH POWDER    a blizzard: the snow driven sideways, banks of fog rolling along the far ridge
  //   BLACK DIAMOND   the NORTHERN LIGHTS: three curtains of light waving across the sky, their rays shimmering;
  //                   stars that twinkle, a shooting star now and then, the moon's halo breathing
  //   AVALANCHE       a storm: fast dark clouds, LIGHTNING forking out of them (a new place each time) and lighting
  //                   the sky, its thunder after it, and powder boiling up off the slide
  const SKYCFG = {
    normal:   { speed: 1,   alpha: .92, tint: null,             wind: [0, 40, 6000] },
    zombie:   { speed: 1.5, alpha: .8,  tint: ["#EDE7F8", .55], wind: [150, 90, 2700] },
    midnight: { speed: .85, alpha: .5,  tint: ["#5A6DB8", .8],  wind: [0, 25, 7000] },
    nitro:    { speed: 2.8, alpha: .85, tint: ["#5E2A84", .82], wind: [-280, 90, 1900] },
  };
  const tints = {};
  const stars = [], bolts = [], dust = [], fog = [], birds = [];
  let nextBolt = 1800, nextShoot = 5000, shoot = null, nextDust = 0, nextBirds = 9000, auroraTex = null;
  function seed() {
    for (let i = 0; i < 8; i++) clouds.push(newCloud(true));
    for (let i = 0; i < 160; i++) flakes.push(newFlake(true));
    for (let i = 0; i < 44; i++) stars.push({ x: rand(0, PW), y: rand(10, PH * .24), r: rand(5, 13), sp: rand(.8, 2.6), ph: rand(0, 6.28) });
    for (let i = 0; i < 4; i++) fog.push({ x: rand(-800, PW), y: rand(PH * .2, PH * .31), w: rand(1300, 2100), v: rand(55, 110), a: rand(.16, .28) });
  }
  function newCloud(anywhere) {
    const far = Math.random() < .45;   // the far ones are smaller, slower, fainter
    return { x: anywhere ? rand(-400, PW) : -520, y: rand(SKY[0], SKY[1] * (far ? .7 : 1)), v: rand(38, 86) * (far ? .55 : 1), k: rand(.7, 1.25) * (far ? .6 : 1), far, flip: Math.random() < .5 };
  }
  function newFlake(anywhere) {
    const z = Math.random();   // depth: near flakes are bigger, faster, brighter
    return { x: rand(0, PW), y: anywhere ? rand(0, PH) : rand(-60, -10), r: 3 + z * 9, v: 40 + z * 110, sway: rand(0, 6.28),
             sw: rand(.4, 1.2), a: .45 + z * .5, z };
  }
  // a sprite washed with a colour (a cloud for a night sky, for a storm), made once
  function tinted(name, tint) {
    const im = pic(name);
    if (!tint) return im;
    const key = name + tint[0] + tint[1];
    if (tints[key]) return tints[key];
    if (!ok(im)) return null;
    const c = document.createElement("canvas"); c.width = im.naturalWidth; c.height = im.naturalHeight;
    const x = c.getContext("2d");
    x.drawImage(im, 0, 0); x.globalCompositeOperation = "source-atop"; x.globalAlpha = tint[1]; x.fillStyle = tint[0]; x.fillRect(0, 0, c.width, c.height);
    return (tints[key] = c);
  }
  // a soft bank of mist (no outline: fog is not a cloud)
  let mistTex = null;
  function mist() {
    if (mistTex) return mistTex;
    const c = document.createElement("canvas"); c.width = 256; c.height = 96;
    const x = c.getContext("2d");
    for (const [cx, cy, r, a] of [[128, 52, 60, .9], [70, 56, 44, .75], [190, 54, 46, .75], [30, 60, 30, .5], [228, 60, 30, .5]]) {
      const gr = x.createRadialGradient(cx, cy, 0, cx, cy, r);
      gr.addColorStop(0, `rgba(255, 255, 255, ${a})`); gr.addColorStop(1, "rgba(255, 255, 255, 0)");
      x.fillStyle = gr; x.fillRect(0, 0, 256, 96);
    }
    return (mistTex = c);
  }
  // one ray of the northern lights: nothing at its top, violet, then green burning brightest at its foot
  function aurora() {
    if (auroraTex) return auroraTex;
    auroraTex = [["rgba(170, 90, 255, 0)", "rgba(165, 95, 255, .5)", "rgba(70, 255, 150, .85)", "rgba(200, 255, 220, 1)"],
                 ["rgba(255, 110, 220, 0)", "rgba(210, 110, 255, .45)", "rgba(110, 230, 255, .75)", "rgba(220, 250, 255, .95)"]].map(cols => {
      const c = document.createElement("canvas"); c.width = 4; c.height = 256;
      const x = c.getContext("2d"), gr = x.createLinearGradient(0, 0, 0, 256);
      gr.addColorStop(0, cols[0]); gr.addColorStop(.42, cols[1]); gr.addColorStop(.8, cols[2]); gr.addColorStop(.93, cols[3]); gr.addColorStop(1, cols[0]);
      x.fillStyle = gr; x.fillRect(0, 0, 4, 256);
      return c;
    });
    return auroraTex;
  }
  const RIBBONS = [  // where each curtain hangs (share of the plate's height), how it snakes and how tall its rays are
    { y: .125, a1: .034, k1: 1.7, w1: .16, a2: .016, k2: 4.9, w2: .27, h: .135, tex: 0, p: 0, gain: 1 },
    { y: .195, a1: .028, k1: 2.3, w1: -.13, a2: .014, k2: 6.1, w2: .22, h: .11, tex: 1, p: 2.1, gain: .7 },
    { y: .075, a1: .022, k1: 1.2, w1: .1,  a2: .012, k2: 3.7, w2: -.31, h: .095, tex: 0, p: 4.4, gain: .8 },
  ];
  // a fork of lightning: from a cloud down to the far ridge, jagged, with a branch or two
  function bolt(t) {
    const x0 = rand(.46, .97) * PW, y0 = rand(.05, .13) * PH, x1 = x0 + rand(-.09, .09) * PW, y1 = rand(.2, .31) * PH;
    const jag = (ax, ay, bx, by, n, d) => {
      let pts = [[ax, ay], [bx, by]];
      for (let k = 0; k < n; k++) {
        const out = [pts[0]];
        for (let i = 1; i < pts.length; i++) {
          const [px, py] = pts[i - 1], [qx, qy] = pts[i];
          out.push([(px + qx) / 2 + rand(-d, d), (py + qy) / 2 + rand(-d * .35, d * .35)], pts[i]);
        }
        pts = out; d *= .55;
      }
      return pts;
    };
    const main = jag(x0, y0, x1, y1, 5, 110), lines = [main];
    for (let k = 0, n = Math.random() < .7 ? 2 : 1; k < n; k++) {
      const from = main[Math.floor(rand(.2, .7) * main.length)];
      lines.push(jag(from[0], from[1], from[0] + rand(-.07, .07) * PW, from[1] + rand(.04, .1) * PH, 4, 60));
    }
    bolts.push({ t0: t, life: rand(300, 420), lines, x: x0 });
    // its thunder, a moment after - quieter than the game, and not every time (window.sfx: index.html)
    if (typeof window.sfx === "function" && !document.hidden && Math.random() < .65) {
      setTimeout(() => { try { window.sfx("thunder", rand(.9, 1.12), { vol: rand(.45, .85), pan: (x0 / PW - .5) * 1.3 }); } catch (e) { /* no sound is no harm */ } }, rand(140, 460));
    }
  }

  // ---------------------------------------------------------------- drawing
  function sprite(im, x, y, h, { flip = false, alpha = 1, anchorY = .5, src = null, stretch = 1 } = {}) {
    if (!ok(im)) return;
    const [sx, sy, sw, sh] = src || [0, 0, im.naturalWidth || im.width, im.naturalHeight || im.height];
    const w = h * sw / sh * stretch;
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
    const base = mode === "normal", C = SKYCFG[mode] || SKYCFG.normal, s = t / 1000;

    // ---- the night: the northern lights, stars, the moon (under the clouds)
    if (mode === "midnight") {
      g.save();
      g.globalCompositeOperation = "lighter";
      const tex = aurora(), W = 30;
      for (const r of RIBBONS) {
        const breath = .72 + .28 * Math.sin(s * .13 + r.p);
        for (let x = -W; x < PW; x += W) {
          const u = x / PW;
          const y = PH * (r.y + r.a1 * Math.sin(u * r.k1 * 6.2832 + s * r.w1 + r.p) + r.a2 * Math.sin(u * r.k2 * 6.2832 - s * r.w2));
          const h = PH * r.h * (.68 + .32 * Math.sin(u * 9 + s * .23 + r.p));
          const ray = (.5 + .5 * Math.sin(u * 46 + s * 1.25 + r.p)) * (.55 + .45 * Math.sin(u * 15 - s * .7 + r.p * 2));
          const edge = Math.min(1, u * 9, (1 - u) * 9) * Math.max(.12, Math.min(1, (Math.abs(u - .731) - .035) * 14));   // thin at the sides; behind the moon, not across it
          g.globalAlpha = Math.max(0, r.gain * breath * (.3 + .7 * ray) * edge);
          g.drawImage(tex[r.tex], x, y - h, W + 1, h);
        }
      }
      // the moon's halo
      const mx = PW * .731, my = PH * .097, mr = PW * .085;
      const gr = g.createRadialGradient(mx, my, mr * .25, mx, my, mr);
      gr.addColorStop(0, `rgba(255, 250, 215, ${(.16 + .06 * Math.sin(s * .7)).toFixed(3)})`); gr.addColorStop(1, "rgba(255, 250, 215, 0)");
      g.globalAlpha = 1; g.fillStyle = gr; g.fillRect(mx - mr, my - mr, mr * 2, mr * 2);
      // stars that twinkle
      g.fillStyle = "#fff";
      for (const st of stars) {
        const a = Math.max(0, Math.sin(s * st.sp + st.ph)) ** 3;
        if (a < .03) continue;
        g.globalAlpha = a * .9;
        g.fillRect(st.x - st.r, st.y - 1.2, st.r * 2, 2.4); g.fillRect(st.x - 1.2, st.y - st.r, 2.4, st.r * 2);
      }
      // a shooting star
      if (!RM && !shoot && t > nextShoot) { shoot = { t0: t, x: rand(.15, .8) * PW, y: rand(.02, .12) * PH, dir: Math.random() < .5 ? -1 : 1 }; nextShoot = t + rand(6000, 15000); }
      if (shoot) {
        const u = (t - shoot.t0) / 620;
        if (u >= 1) shoot = null;
        else {
          const hx = shoot.x + shoot.dir * u * 1300, hy = shoot.y + u * 420, tail = 320 * Math.sin(Math.PI * u);
          const lg = g.createLinearGradient(hx, hy, hx - shoot.dir * tail, hy - tail * .32);
          lg.addColorStop(0, "rgba(255, 255, 255, .95)"); lg.addColorStop(1, "rgba(255, 255, 255, 0)");
          g.globalAlpha = 1; g.strokeStyle = lg; g.lineWidth = 6; g.lineCap = "round";
          g.beginPath(); g.moveTo(hx, hy); g.lineTo(hx - shoot.dir * tail, hy - tail * .32); g.stroke();
        }
      }
      g.restore();
    }

    // ---- the storm: the sky lit by its lightning (under the clouds, so they stand dark against it)
    let lit = 0;
    if (mode === "nitro") {
      if (!RM && t > nextBolt) { bolt(t); nextBolt = t + (Math.random() < .28 ? rand(160, 320) : rand(2200, 6200)); }
      for (let i = bolts.length - 1; i >= 0; i--) {
        const b = bolts[i], u = (t - b.t0) / b.life;
        if (u >= 1) { bolts.splice(i, 1); continue; }
        b.now = u < .2 ? 1 : u < .33 ? .14 : u < .55 ? .82 : Math.max(0, (1 - u) / .45) * .8;   // a flash, a dip, a second, gone
        lit = Math.max(lit, b.now);
      }
      if (lit > 0) {
        g.save(); g.globalCompositeOperation = "lighter";
        const gr = g.createLinearGradient(0, 0, 0, PH * .4);
        gr.addColorStop(0, `rgba(255, 236, 190, ${(.3 * lit).toFixed(3)})`); gr.addColorStop(1, "rgba(255, 236, 190, 0)");
        g.fillStyle = gr; g.fillRect(0, 0, PW, PH * .4);
        g.fillStyle = `rgba(255, 255, 255, ${(.05 * lit).toFixed(3)})`; g.fillRect(0, 0, PW, PH);
        g.restore();
      }
    } else if (bolts.length) bolts.length = 0;

    // ---- clouds, always crossing (on the layered day scene they are layers.js's, under the summit)
    const cloud = tinted("cloud", C.tint);
    if (!(layered && base) && cloud) {
      for (const c of clouds) {
        c.x += c.v * C.speed * dt;
        if (c.x > PW + 520) Object.assign(c, newCloud(false));
        sprite(cloud, c.x, c.y, 200 * c.k, { alpha: C.alpha * (c.far ? .6 : 1), flip: c.flip });
      }
    }

    // ---- the storm's lightning itself, over the clouds it comes out of
    if (lit > 0) {
      g.save(); g.globalCompositeOperation = "lighter"; g.lineJoin = "round"; g.lineCap = "round";
      for (const b of bolts) {
        if (!b.now) continue;
        for (const [wd, al, col] of [[34, .13, "#B88CFF"], [13, .4, "#FFE9A8"], [5, 1, "#FFFBE6"]]) {
          g.globalAlpha = al * b.now; g.strokeStyle = col;
          b.lines.forEach((pts, li) => {
            g.lineWidth = wd * (li ? .55 : 1);
            g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
            for (let k = 1; k < pts.length; k++) g.lineTo(pts[k][0], pts[k][1]);
            g.stroke();
          });
        }
      }
      g.restore();
    }

    // ---- the blizzard's fog rolling along the far ridge; the slide's powder boiling up
    const white = pic("cloud");
    if (mode === "zombie") for (const f of fog) {
      f.x += f.v * dt;
      if (f.x > PW + f.w) { f.x = -f.w; f.y = rand(PH * .2, PH * .31); }
      sprite(mist(), f.x, f.y, f.w * .3, { alpha: f.a * 2.2 });
    }
    if (mode === "nitro") {
      if (!RM && t > nextDust) { dust.push({ t0: t, x: rand(.47, .8) * PW, y: rand(.3, .43) * PH, vx: rand(-110, -30), vy: rand(-70, -20), life: rand(1800, 3000), k: rand(.6, 1.3), flip: Math.random() < .5 }); nextDust = t + rand(150, 320); }
      for (let i = dust.length - 1; i >= 0; i--) {
        const d = dust[i], u = (t - d.t0) / d.life;
        if (u >= 1) { dust.splice(i, 1); continue; }
        sprite(white, d.x + d.vx * u * d.life / 1000, d.y + d.vy * u * d.life / 1000, (70 + 170 * u) * d.k, { alpha: .5 * Math.sin(Math.PI * u), flip: d.flip });
      }
    } else if (dust.length) dust.length = 0;

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

      // a few birds, high up, now and then
      if (!RM && t > nextBirds) {
        const dir = Math.random() < .5 ? -1 : 1, y0 = rand(.05, .17) * PH, n = 3 + Math.floor(Math.random() * 3), v = rand(170, 250);
        for (let i = 0; i < n; i++) birds.push({ x: (dir > 0 ? -80 : PW + 80) - dir * i * rand(70, 120), y: y0 + rand(-45, 45) + i * 18, v: dir * v, r: rand(13, 20), ph: rand(0, 6.28), sp: rand(9, 12) });
        nextBirds = t + rand(14000, 30000);
      }
      g.save(); g.strokeStyle = "#1B2A4A"; g.lineCap = "round"; g.lineJoin = "round"; g.globalAlpha = .85;
      for (let i = birds.length - 1; i >= 0; i--) {
        const b = birds[i];
        b.x += b.v * dt;
        if (b.x < -200 || b.x > PW + 200) { birds.splice(i, 1); continue; }
        const flap = Math.sin(s * b.sp + b.ph) * b.r * .7, y = b.y + Math.sin(s * 1.3 + b.ph) * 10;
        g.lineWidth = b.r * .32;
        g.beginPath(); g.moveTo(b.x - b.r * 1.5, y - flap); g.quadraticCurveTo(b.x - b.r * .6, y - flap * .2 - b.r * .25, b.x, y);
        g.quadraticCurveTo(b.x + b.r * .6, y - flap * .2 - b.r * .25, b.x + b.r * 1.5, y - flap); g.stroke();
      }
      g.restore();

      // chimney smoke - off (owner, 2026-11-23: "remove the little tree above the grand"): on a landscape screen the
      // jackpot board stands in front of the hut, so the green puffs rose from behind GRAND like a bush growing on it
      if (SMOKE && t > nextPuff) { puffs.push({ t0: t, dx: rand(-20, 20), spin: rand(-.3, .3) }); nextPuff = t + PUFF_EVERY * rand(.7, 1.3); }
      for (let i = puffs.length - 1; i >= 0; i--) {
        const p = puffs[i], u = (t - p.t0) / PUFF_LIFE;
        if (u >= 1) { puffs.splice(i, 1); continue; }
        const x = CHIMNEY[0] + p.dx + u * 260 + Math.sin(u * 5) * 30, y = CHIMNEY[1] - u * 520;
        const a = u < .12 ? u / .12 : 1 - (u - .12) / .88;
        sprite(pic("puff"), x, y, PUFF * (.35 + u * 1.1), { alpha: .85 * a, anchorY: .6 });
      }
    } else if (birds.length) birds.length = 0;

    // spindrift: a gust lifts a sheet of loose snow off the summit and blows it across, low and fast
    if (!RM && t > nextGust) {
      const y0 = rand(GROUND[0], GROUND[1] - 160), dir = C.wind[0] ? Math.sign(C.wind[0]) : (Math.random() < .5 ? -1 : 1), n = 70;
      for (let i = 0; i < n; i++) drift.push({ t0: t + rand(0, 700), ms: GUST_MS * rand(.7, 1.15), y: y0 + rand(-90, 90),
        x0: dir > 0 ? rand(-500, 900) : rand(PW - 900, PW + 500), v: dir * rand(900, 1500), r: rand(2.5, 6.5),
        lift: rand(30, 150), ph: rand(0, 6.28) });
      nextGust = t + rand(...GUST_GAP) * (base || mode === "midnight" ? 1 : .5);   // a blizzard and a storm gust twice as often
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

    // snow, over everything of ours: it leans with the wind, and the wind gusts
    const heavy = mode === "zombie" ? 1 : mode === "nitro" ? .8 : .55;
    const wind = C.wind[0] + C.wind[1] * Math.sin(t / C.wind[2]) + C.wind[1] * .4 * Math.sin(t / (C.wind[2] * .37));
    g.fillStyle = "#fff";
    for (let i = 0; i < flakes.length; i++) {
      const f = flakes[i];
      if (i / flakes.length > heavy) continue;
      f.y += f.v * dt * (mode === "zombie" ? 1.25 : 1); f.sway += f.sw * dt;
      f.x += wind * (.45 + .75 * f.z) * dt;
      if (f.x < -40) f.x += PW + 80; else if (f.x > PW + 40) f.x -= PW + 80;
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
    (SMOKE ? ["cloud", "puff"] : ["cloud"]).forEach(pic);
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

  // layers.js takes over what it draws in depth: the base scene's clouds, and where the hut's windows are in its art
  function own({ clouds: c, windows } = {}) {
    layered = !!c;
    if (Array.isArray(windows)) WINDOWS = windows;
  }

  window.SkyFX = { start, layout, scene, own };
})();
