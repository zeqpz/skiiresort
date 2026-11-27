/* Live cut-out character rigs (High Peaks, 2026-11-19; ported from Voodoo on Bourbon's charrig.js).

   A character made and animated in Blender (tools/highpeaks/yeti/yeti_rig.py) and packed by yeti_pack.py comes as a
   rig, not baked frames: its pieces (an atlas per density, a mesh per piece, 4 bone weights per vertex) and, for every
   clip, each bone's 2D transform on every frame Blender keyed (30 a second). The page poses the meshes itself every
   screen refresh, easing the bones between Blender's frames on a Catmull-Rom curve - smooth at 60, 120 or 165 Hz,
   and a few MB rather than hundreds of frames.

   Live effects (2026-11-20, owner: "the flame coming from the joint ... it's floating"): the joint's ember, the smoke
   curling off it, the puffs he exhales and the sweat on his brow are NOT keyed sprites. They hang off points on his
   bones (rig.json "points": a bone and a spot in the rest drawing) and are placed from the very bone transforms the
   meshes are skinned with, every frame - through Catmull-Rom easing and clip cross-fades alike - so the ember sits
   on the joint's lit tip, a wisp leaves from it and an exhale from his lips. Sparks and kicked-up snow are keyed in
   Blender (rig.json clips[].fx).

   CharRig.make({ host, base, flip, headroom, maxFps, reducedMotion }) -> Promise<player | null>
     host      the element he stands in: he is sized by its HEIGHT (his standing figure = height / headroom) and stands
               on its bottom edge, centred; his canvas runs past the box at the sides and above it (smoke, sparks,
               arms thrown up), never shrinking him
     base      the rig's folder ("assets/yeti/rig/")
     flip      mirror him (he faces a little to the viewer's left as drawn)
   player = { play(clip, {hold}), idle(), length(clip), has(clip), state(), resize(), destroy(), canvas,
              pose(clip, f), resume(), only(names), point(name) }   (the last four for QA)
     play     cuts to a clip from whatever pose is showing, the two poses eased across the rig's `cut` frames; a
              one-shot goes back to the idle by itself; a looping clip asked with {hold: true} loops until told
     idle     back to the idle loop (eased)
   null when Pixi or WebGL is not there, or the rig fails to load - the page carries on without him, nothing thrown,
   nothing in the console but one warning for a missing file. With reduced motion he stands still on his first pose. */
(function () {
  "use strict";
  const CR = (window.CharRig = {});

  const catmull = (p0, p1, p2, p3, t) => {
    const t2 = t * t, t3 = t2 * t;
    return .5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (3 * p1 - p0 - 3 * p2 + p3) * t3);
  };
  const ease = t => { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); };
  const image = url => new Promise((ok, no) => {
    const im = new Image();
    im.decoding = "async";
    im.onload = () => ok(im);
    im.onerror = () => no(new Error(url + " did not load"));
    im.src = url;
  });
  const bytes = url => fetch(url).then(r => { if (!r.ok) throw new Error(url + " -> HTTP " + r.status); return r.arrayBuffer(); });
  const webgl = () => {
    try {
      const c = document.createElement("canvas");
      return !!(c.getContext("webgl2") || c.getContext("webgl"));
    } catch (e) { return false; }
  };

  async function load(base, figurePx) {
    const r = await fetch(base + "rig.json");
    if (!r.ok) throw new Error(base + "rig.json -> HTTP " + r.status);
    const man = await r.json();
    const want = figurePx / man.rest_height;                 // texels per art px that draw him a texel per screen px
    const D = man.densities.find(d => d.d >= want) || man.densities[man.densities.length - 1];
    const [geo, clips, pages] = await Promise.all([bytes(base + man.geo), bytes(base + man.clips_bin),
      Promise.all(D.pages.map(p => image(base + p)))]);
    return { man, D, geo, clips: new Float32Array(clips), pages };
  }

  // the room his canvas has round his box: a fraction of the box's height each side, above and below
  const ROOM = { side: .42, top: .3, bottom: .12 };

  // The page scales its layout to the window (#app's --fit), so the host's layout height is not what the screen
  // shows: a phone drew him on a 2316 x 1916 antialiased buffer, from a 4096 x 2048 atlas, for a figure ~500 px
  // tall (2026-11-23: an iPhone showed smeared texture beside and under the board). His canvas and his atlas are
  // now sized by the pixels he really covers.
  const shownScale = host => {
    const h = host.clientHeight;
    const k = h ? host.getBoundingClientRect().height / h : 1;
    return k > 0 && isFinite(k) ? k : 1;
  };
  const MAX_DPR = 2;
  const resFor = host => Math.max(.5, Math.min(MAX_DPR, (window.devicePixelRatio || 1) * shownScale(host)));

  // his contact shadow: one soft disc, drawn flat on the snow under him
  let shadowCv = null;
  const shadowCanvas = () => {
    if (shadowCv) return shadowCv;
    const N = 128, cv = document.createElement("canvas");
    cv.width = cv.height = N;
    const g = cv.getContext("2d"), rg = g.createRadialGradient(N / 2, N / 2, 0, N / 2, N / 2, N / 2);
    rg.addColorStop(0, "rgba(255,255,255,1)");
    rg.addColorStop(.55, "rgba(255,255,255,.62)");
    rg.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = rg; g.fillRect(0, 0, N, N);
    return (shadowCv = cv);
  };

  // his shadow as the scene draws shadows: one flat ellipse with a crisp edge
  let flatCv = null;
  const flatShadowCanvas = () => {
    if (flatCv) return flatCv;
    const cv = document.createElement("canvas");
    cv.width = 512; cv.height = 96;
    const g = cv.getContext("2d");
    g.fillStyle = "#fff"; g.beginPath(); g.ellipse(256, 48, 252, 45, 0, 0, 6.2832); g.fill();
    return (flatCv = cv);
  };

  CR.make = async function ({ host, base = "assets/yeti/rig/", flip = false, headroom = 1.06, maxFps = 60, reducedMotion, hide = [], ground = null } = {}) {
    if (!host || typeof PIXI === "undefined" || !PIXI.MeshSimple || !PIXI.Application || !webgl()) return null;
    const still = reducedMotion !== undefined ? reducedMotion
      : !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
    let res = resFor(host);
    let R;
    try { R = await load(base, Math.max(80, host.clientHeight) / headroom * res); }
    catch (e) { console.warn("character rig failed to load:", e.message); return null; }
    const { man, D } = R;
    const B = man.bones.length, fps = man.fps;
    if (!man.clips.idle) return null;

    const stageEl = document.createElement("div");
    stageEl.className = "charstage";
    Object.assign(stageEl.style, { position: "absolute", pointerEvents: "none", left: "0", top: "0", width: "0", height: "0" });
    if (getComputedStyle(host).position === "static") host.style.position = "relative";
    host.appendChild(stageEl);
    const place = () => {
      const h = host.clientHeight, w = host.clientWidth;
      Object.assign(stageEl.style, { left: (-ROOM.side * h) + "px", top: (-ROOM.top * h) + "px",
        width: (w + 2 * ROOM.side * h) + "px", height: (h * (1 + ROOM.top + ROOM.bottom)) + "px" });
    };
    place();
    const app = new PIXI.Application();
    try {
      await app.init({ backgroundAlpha: 0, antialias: true, autoDensity: true, resolution: res, resizeTo: stageEl,
                       preference: "webgl", hello: false });
    } catch (e) { stageEl.remove(); return null; }
    app.ticker.maxFPS = maxFps;
    app.canvas.style.display = "block";
    stageEl.appendChild(app.canvas);
    let dirty = true;
    const touch = () => { dirty = true; };
    app.ticker.remove(app.render, app);
    app.ticker.add(() => { if (dirty) { dirty = false; app.render(); } }, null, PIXI.UPDATE_PRIORITY.LOW);

    // ---- the pieces: one mesh each, on the density's atlas pages
    const pages = R.pages.map(im => {
      const t = PIXI.Texture.from(im);
      t.source.autoGenerateMipmaps = true;
      t.source.style.minFilter = "linear"; t.source.style.mipmapFilter = "linear";
      return t;
    });
    const actor = new PIXI.Container();
    app.stage.addChild(actor);
    // the shadow he casts on the snow: under every piece, at his ground line, as wide as his mound
    const shade = new PIXI.Sprite(PIXI.Texture.from(shadowCanvas()));
    shade.anchor.set(.5);
    shade.tint = man.shadow_tint === undefined ? 0x16305e : man.shadow_tint;
    shade.alpha = .5;
    shade.width = man.art[0] * 1.2; shade.height = man.rest_height * .12;
    shade.position.set(man.cx, man.ground_y + man.rest_height * .006);
    actor.addChild(shade);
    const hideSet = new Set(hide);
    const parts = man.parts.map(p => {
      const fr = D.frames[p.tex], page = pages[fr[0]], pw = page.source.width, ph = page.source.height;
      const rest = new Float32Array(R.geo, p.o_pos, p.verts * 2);
      const uv0 = new Float32Array(R.geo, p.o_uv, p.verts * 2), uvs = new Float32Array(p.verts * 2);
      for (let i = 0; i < p.verts; i++) {
        uvs[2 * i] = (fr[1] + uv0[2 * i] * fr[3]) / pw;
        uvs[2 * i + 1] = (fr[2] + uv0[2 * i + 1] * fr[4]) / ph;
      }
      const mesh = new PIXI.MeshSimple({ texture: page, vertices: new Float32Array(rest), uvs,
        indices: new Uint16Array(new Uint16Array(R.geo, p.o_idx, p.tris * 3)) });   // 16-bit: every GL has them
      actor.addChild(mesh);
      return { p, mesh, rest, bi: new Uint8Array(R.geo, p.o_bi, p.verts * 4), bw: new Uint8Array(R.geo, p.o_bw, p.verts * 4),
               face: p.face ? man.faces.indexOf(p.face) : -1, hidden: hideSet.has(p.name) };
    });
    // The snow he stands in, when the scene gives him some (ground: { src, w, h, top } in art px; layers.js): a drift
    // drawn over his boots and the foot of his board, in place of a piece hidden with `hide` (his own outlined mound)
    // - so he stands IN the scene's snow, lit like it (tint), not on an island of his own.
    let groundSpr = null, flatShade = null;
    if (ground && ground.src) image(ground.src).then(im => {
      if (!alive) return;
      groundSpr = new PIXI.Sprite(PIXI.Texture.from(im));
      groundSpr.anchor.set(.5, 0);
      groundSpr.width = ground.w || man.art[0] * 1.42;
      groundSpr.height = ground.h || man.rest_height * .17;
      groundSpr.position.set(man.cx + (ground.dx || 0), ground.top !== undefined ? ground.top : man.ground_y - man.rest_height * .075);
      groundSpr.tint = light.ground;
      actor.addChildAt(groundSpr, actor.getChildIndex(fxLayer));
      // His shadow on that snow, drawn the way the scene draws its own: one flat, hard-edged pale-blue shape, multiplied
      // over the drift (its ink stays black), lying in front of his boots a little to his left - not a soft grey blur
      // (owner, 2026-11-23: "our character still doesn't blend well with the background").
      flatShade = new PIXI.Sprite(PIXI.Texture.from(flatShadowCanvas()));
      flatShade.anchor.set(.5);
      flatShade.blendMode = "multiply";
      flatShade.width = man.art[0] * 1.02; flatShade.height = man.rest_height * .068;
      flatShade.position.set(man.cx - man.art[0] * .045, man.ground_y + man.rest_height * .014);
      flatShade.tint = light.shade;
      actor.addChildAt(flatShade, actor.getChildIndex(fxLayer));
      shade.visible = false;
      touch();
    }).catch(() => { /* he keeps standing without it */ });
    const tex = key => {
      const fr = D.frames["fx_" + key];
      return fr ? new PIXI.Texture({ source: pages[fr[0]].source, frame: new PIXI.Rectangle(fr[1], fr[2], fr[3], fr[4]) }) : null;
    };
    // the keyed effects (sparks, snow): sprites off the atlas, pooled by Blender's object id
    const fxLayer = new PIXI.Container();
    actor.addChild(fxLayer);
    const additive = new Set(man.fx_add || []);
    const fxTex = man.fx.map(tex);
    const fxPool = new Map();
    const fxSprite = (id, kind) => {
      let s = fxPool.get(id);
      if (!s) {
        s = new PIXI.Sprite(); s.anchor.set(.5);
        if (additive.has(man.fx[kind])) s.blendMode = "add";
        fxLayer.addChild(s); fxPool.set(id, s);
      }
      return s;
    };
    // the live effects (ember, smoke, sweat): on bone points, every frame
    const liveLayer = new PIXI.Container();
    actor.addChild(liveLayer);
    const LT = { smoke: tex("smoke"), ember: tex("ember"), sweat: tex("sweat") };
    // (owner, 2026-11-27: "the smoke coming out the dude's mouth needs to look better and more realistic") His smoke is
    // made of a soft, wispy puff now (assets/fx/smoke_soft.webp - the bong's), many small ones at a time: a breath
    // is a stream of them leaving his mouth fast, slowing, curling apart and thinning as they rise, not three round
    // cartoon balls. Until that picture is in (or if it never comes) the atlas's own puff is used as before.
    if (PIXI.Assets && PIXI.Assets.load) PIXI.Assets.load("assets/fx/smoke_soft.webp").then(t => { if (t) LT.soft = t; }).catch(() => {});
    const PX = man.fx_px || {};
    const pts = {};
    for (const [k, v] of Object.entries(man.points || {})) pts[k] = { j: man.bones.indexOf(v.bone) * 6, x: v.at[0], y: v.at[1] };
    const ember = LT.ember && pts.tip ? new PIXI.Sprite(LT.ember) : null;
    if (ember) { ember.anchor.set(.5); ember.blendMode = "add"; liveLayer.addChild(ember); }

    // ---- posing
    const M = new Float32Array(B * 6), M2 = new Float32Array(B * 6), X = new PIXI.Matrix();
    const sample = (clip, f, out) => {
      const C = man.clips[clip], n = C.frames, base0 = C.o / 4, S = B * 6, d = R.clips;
      const i1 = Math.floor(f), t = f - i1;
      const at = k => base0 + (C.loop ? ((k % n) + n) % n : Math.max(0, Math.min(n - 1, k))) * S;
      const a1 = at(i1);
      if (t < 1e-4) { out.set(d.subarray(a1, a1 + S)); return; }
      const a0 = at(i1 - 1), a2 = at(i1 + 1), a3 = at(i1 + 2);
      for (let k = 0; k < S; k++) out[k] = catmull(d[a0 + k], d[a1 + k], d[a2 + k], d[a3 + k], t);
    };
    // a point of the rest drawing, carried by its bone in the pose now showing (art px)
    const pointAt = (name, dx = 0, dy = 0) => {
      const p = pts[name];
      if (!p) return null;
      const j = p.j, x = p.x + dx, y = p.y + dy;
      return { x: M[j] * x + M[j + 2] * y + M[j + 4], y: M[j + 1] * x + M[j + 3] * y + M[j + 5] };
    };
    const skin = () => {
      for (const q of parts) {
        if (!q.mesh.visible) continue;
        const v = q.mesh.vertices, rest = q.rest, bi = q.bi, bw = q.bw, n = rest.length / 2;
        for (let i = 0; i < n; i++) {
          const x = rest[2 * i], y = rest[2 * i + 1];
          let sx = 0, sy = 0;
          for (let k = 4 * i, e = k + 4; k < e; k++) {
            const w = bw[k];
            if (!w) continue;
            const j = bi[k] * 6;
            sx += w * (M[j] * x + M[j + 2] * y + M[j + 4]);
            sy += w * (M[j + 1] * x + M[j + 3] * y + M[j + 5]);
          }
          v[2 * i] = sx / 255; v[2 * i + 1] = sy / 255;
        }
      }
    };
    const drawFx = (C, f) => {
      for (const s of fxPool.values()) s.visible = false;
      const n = C.fx.length, i = Math.min(n - 1, Math.floor(f)), t = f - i;
      const now = C.fx[i] || [], nxt = C.fx[C.loop ? (i + 1) % n : Math.min(n - 1, i + 1)] || [];
      for (const dr of now) {
        const tx = fxTex[dr[0]];
        if (!tx) continue;
        const nb = t > 0 ? nxt.find(e => e[1] === dr[1]) : null;
        const g = k => nb ? dr[k] + (nb[k] - dr[k]) * t : dr[k];
        const s = fxSprite(dr[1], dr[0]);
        if (s.texture !== tx) s.texture = tx;
        const tw = tx.frame.width, th = tx.frame.height;
        X.set(g(2) / tw, g(3) / tw, g(4) / th, g(5) / th, g(6), g(7));
        s.setFromMatrix(X);
        s.alpha = g(8);
        s.visible = true;
      }
    };
    const glowAt = (clip, f) => {
      const E = man.clips[clip].ember;
      if (!E || !E.length) return .4;
      const n = E.length, i = Math.floor(f), t = f - i, C = man.clips[clip];
      const a = E[C.loop ? ((i % n) + n) % n : Math.min(n - 1, i)], b = E[C.loop ? ((i + 1) % n + n) % n : Math.min(n - 1, i + 1)];
      return a + (b - a) * t;
    };

    // ---- live particles: smoke off the tip, puffs out of his mouth, a bead of sweat sliding down his brow
    const particles = [];
    const pool = [];
    const sprite = (t, add) => {
      const s = pool.pop() || new PIXI.Sprite();
      s.texture = t; s.anchor.set(.5); s.blendMode = add ? "add" : "normal"; s.visible = true; s.tint = 0xffffff;
      liveLayer.addChildAt(s, 0);
      return s;
    };
    let seed = 7919, lastWisp = 0;
    const SMOKE_TINT = 0xD6DDE9;   // a touch of grey-blue: pure white smoke is lost against snow and his white fur
    const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
    const spawn = (kind, now) => {
      const soft = !!LT.soft;
      if (kind === "wisp1" && soft && pts.tip) {               // one fine puff of the thread
        const s = sprite(LT.soft); s.tint = SMOKE_TINT;
        particles.push({ s, kind: "wisp", soft, t0: now, life: 2100 + 900 * rnd(), from: null, sway: rnd() * 6.28, rise: 280 + 170 * rnd(),
                         drift: 20 + 50 * rnd(), size: [.1, .5 + .32 * rnd()], spin: (rnd() - .5) * 1.6, a: .5, curl: 8 + 22 * rnd() });
      } else if (kind === "wisp" && LT.smoke && pts.tip) {
        // off the joint's tip: a thin thread (two fine puffs a beat apart) that rises, drifts and curls wider as it goes
        for (let k = 0, n = soft ? 2 : 1; k < n; k++) {
          const s = sprite(soft ? LT.soft : LT.smoke);
          if (soft) s.tint = SMOKE_TINT;
          particles.push({ s, kind, soft, t0: now + 110 * k, life: (soft ? 2300 : 1700) + 700 * rnd(), from: null, sway: rnd() * 6.28, rise: soft ? 300 + 160 * rnd() : 200 + 90 * rnd(),
                           drift: 24 + 40 * rnd(), size: soft ? [.14, .7 + .3 * rnd()] : [.2, .72], spin: (rnd() - .5) * 1.2, a: soft ? .58 : .9, curl: soft ? 10 + 24 * rnd() : 14 });
        }
      } else if (kind === "exhale" && LT.smoke && pts.mouth) {
        // a breath out: a stream of soft puffs in a cone, each on its own line, quick at first
        for (let k = 0, n = soft ? 26 : 3; k < n; k++) {
          const s = sprite(soft ? LT.soft : LT.smoke);
          if (soft) s.tint = SMOKE_TINT;
          particles.push({ s, kind, soft, t0: now + (soft ? 34 : 120) * k, life: (soft ? 1900 : 1500) + (soft ? 1100 : 300) * rnd(), from: null, sway: rnd() * 6.28,
                           dx: soft ? 110 + 260 * rnd() : 70 + 60 * rnd(), dy: soft ? -(40 + 190 * rnd()) : -(90 + 80 * rnd()),
                           size: soft ? [.26 + .14 * rnd(), 1.5 + 1.1 * rnd()] : [.4, 1.35], spin: (rnd() - .5) * (soft ? 2.2 : 1.4), a: soft ? .5 + .22 * rnd() : .9, curl: soft ? 10 + 30 * rnd() : 10 });
        }
      } else if (kind === "sweat" && LT.sweat && pts.brow) {
        particles.push({ s: sprite(LT.sweat), kind, t0: now, life: 1450 });
      }
    };
    const stepParticles = now => {
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i], s = p.s, u = (now - p.t0) / p.life;
        if (u >= 1) { s.visible = false; liveLayer.removeChild(s); pool.push(s); particles.splice(i, 1); continue; }
        if (u < 0) { s.visible = false; continue; }
        s.visible = true;
        const fadeIn = Math.min(1, u / .12), fadeOut = p.soft ? (u < .28 ? 1 : Math.pow((1 - u) / .72, 1.3)) : (u < .55 ? 1 : (1 - u) / .45);
        if (p.kind === "sweat") {                            // slides down his brow, riding his head
          const q = pointAt("brow", 6 * u, 70 * u * u);
          s.position.set(q.x, q.y);
          s.scale.set((PX.sweat || 70) / s.texture.frame.width);
          s.alpha = Math.min(1, u / .15) * (u < .7 ? 1 : (1 - u) / .3);
          continue;
        }
        // a puff leaves FROM the point it belongs to: it rides the live point for its first moments, then is let go
        const live = pointAt(p.kind === "wisp" ? "tip" : "mouth");
        if (!p.from || u < .12) p.from = live;
        // soft smoke leaves fast and slows (it is pushed, then only drifts), and its curl widens as it thins
        const o = p.from, k = p.soft ? 1 - Math.pow(1 - u, 2.4) : ease((u - .0) / 1), curl = (p.curl ?? 12) * (p.soft ? .25 + u * 1.5 : 1);
        const g = p.size[0] + (p.size[1] - p.size[0]) * Math.sqrt(u);
        if (p.kind === "wisp") s.position.set(o.x + p.drift * k + curl * Math.sin(p.sway + 6 * u), o.y - p.rise * (p.soft ? u * (.55 + .45 * u) : k));
        else s.position.set(o.x + 25 + p.dx * k + curl * Math.sin(p.sway + 5 * u), o.y + p.dy * k - (p.soft ? 110 * u * u : 0));
        s.scale.set(g * (PX.smoke || 150) / s.texture.frame.width);
        s.rotation = p.spin * u;
        s.alpha = fadeIn * fadeOut * (p.a ?? .9);
      }
    };
    const emitBetween = (clip, f0, f1, now) => {          // the clip's live emits whose frame lies in (f0, f1]
      const E = man.clips[clip].emit;
      if (!E || still) return;
      for (const [fr, kind] of E) if (fr > f0 && fr <= f1) spawn(kind, now);
    };

    // the scene's light on him (tint): every piece multiplied by `body`, his drift by `ground`, eased over a moment
    const light = { body: 0xffffff, ground: 0xffffff, shade: 0xd2e6fa, from: null, to: null, t0: 0, ms: 0 };
    const rgb = c => [(c >> 16) & 255, (c >> 8) & 255, c & 255];
    const mixc = (a, b, k) => { const A = rgb(a), Bc = rgb(b); return (Math.round(A[0] + (Bc[0] - A[0]) * k) << 16) | (Math.round(A[1] + (Bc[1] - A[1]) * k) << 8) | Math.round(A[2] + (Bc[2] - A[2]) * k); };
    const relight = now => {
      if (light.to) {
        const k = light.ms > 0 ? Math.min(1, (now - light.t0) / light.ms) : 1, e = k * k * (3 - 2 * k);
        light.body = mixc(light.from.body, light.to.body, e); light.ground = mixc(light.from.ground, light.to.ground, e);
        light.shade = mixc(light.from.shade, light.to.shade, e);
        if (k >= 1) light.to = null;
      }
      for (const q of parts) q.mesh.tint = light.body;
      if (groundSpr) groundSpr.tint = light.ground;
      if (flatShade) flatShade.tint = light.shade;
      touch();
    };
    // Near snow: the scene's snow falls on a canvas behind the whole page, so every flake passed BEHIND him - one of
    // the things that made him look laid on top of the picture. A few of the nearest flakes fall over his own canvas,
    // in front of him, fading in and out at its edges so its box never shows.
    const flakeLayer = new PIXI.Container();
    actor.addChild(flakeLayer);
    const flakes = [];
    let flakeTex = null, lastFlake = 0, viewBox = null;
    let frnd = 48271;
    const fr01 = () => ((frnd = (frnd * 48271) % 2147483647) - 1) / 2147483646;
    const setSnow = n => {
      n = still ? 0 : Math.max(0, Math.min(40, n | 0));
      if (!flakeTex) {
        const cv = document.createElement("canvas"); cv.width = cv.height = 32;
        const g = cv.getContext("2d"); g.fillStyle = "#fff"; g.beginPath(); g.arc(16, 16, 14, 0, 6.2832); g.fill();
        flakeTex = PIXI.Texture.from(cv);
      }
      while (flakes.length < n) {
        const s = new PIXI.Sprite(flakeTex); s.anchor.set(.5); flakeLayer.addChild(s);
        const z = fr01();
        flakes.push({ s, u: fr01(), v: fr01(), r: 5 + z * 11, fall: .045 + z * .075, sway: fr01() * 6.28, sw: .5 + fr01() * .9, a: .55 + z * .4 });
      }
      flakes.forEach((p, i) => { p.s.visible = i < n; p.on = i < n; });
      touch();
    };
    const stepFlakes = now => {
      if (!flakes.length || !viewBox) return;
      const dt = Math.min(.1, (now - (lastFlake || now)) / 1000); lastFlake = now;
      const { x0, x1, y0, y1 } = viewBox, W2 = x1 - x0, H2 = y1 - y0;
      for (const p of flakes) {
        if (!p.on) continue;
        p.v += p.fall * dt; p.sway += p.sw * dt;
        if (p.v > 1) { p.v -= 1; p.u = fr01(); }
        const edge = Math.min(1, p.u / .1, (1 - p.u) / .1, p.v / .12, (1 - p.v) / .1);
        p.s.position.set(x0 + p.u * W2 + Math.sin(p.sway) * 34, y0 + p.v * H2);
        p.s.scale.set(p.r / 14);
        p.s.alpha = p.a * Math.max(0, edge);
      }
    };
    let shown = null, onlySet = null;
    const show = (clip, f, glow) => {
      const C = man.clips[clip];
      const fi = Math.max(0, Math.min(C.frames - 1, Math.round(f) % C.frames));
      const face = C.face[fi];
      for (const q of parts) q.mesh.visible = !q.hidden && (q.face < 0 || q.face === face);
      skin();
      drawFx(C, f);
      fxLayer.visible = liveLayer.visible = !onlySet;
      if (ember) {                                           // ON the joint's lit tip, glowing as the clip says
        const q = pointAt("tip"), g = glow === undefined ? glowAt(clip, f) : glow;
        const fl = 1 + .07 * Math.sin(performance.now() / 1000 * 9.3) + .04 * Math.sin(performance.now() / 1000 * 14.7 + 1.3);
        ember.position.set(q.x, q.y);
        ember.scale.set((.6 + .55 * g) * fl * (PX.ember || 72) / ember.texture.frame.width);
        ember.alpha = Math.min(1, .45 + .6 * g);
      }
      shown = { clip, f };
      touch();
    };

    // ---- the figure on its canvas: his ground line on the box's bottom edge, centred, sized by the box's height
    let fitting = false;
    const fit = () => {
      if (fitting) return;
      place();
      const h = host.clientHeight;
      if (!h) return;
      // the buffer follows the size he is shown at (the page's fit changes with the window)
      // ... and the canvas is always as big as his stage. (bug, 2026-11-23, owner: "our character's legs missing":
      // Pixi's resizeTo only follows WINDOW resizes, and reads the stage before the page has re-fitted - so after a
      // window was resized the canvas kept its old, smaller size while he was placed for the new one, and everything
      // below his waist fell off the bottom of it. The stage's own size is what the canvas takes, every fit.)
      const r2 = resFor(host), sw = stageEl.clientWidth, sh = stageEl.clientHeight;
      const resOff = Math.abs(r2 - res) / res > .08;
      if (sw > 0 && sh > 0 && (resOff || Math.abs(app.screen.width - sw) > 1 || Math.abs(app.screen.height - sh) > 1)) {
        if (resOff) res = r2;
        fitting = true;
        try { app.renderer.resize(sw, sh, res); } catch (e) { /* next resize */ }
        fitting = false;
      }
      const k = h / headroom / man.rest_height;
      actor.pivot.set(man.cx, man.ground_y);
      actor.scale.set(flip ? -k : k, k);
      actor.position.set(app.screen.width / 2, h * (1 + ROOM.top));
      // what of his drawing the canvas shows (art px): where the near snow falls
      viewBox = { x0: man.cx - app.screen.width / 2 / k, x1: man.cx + app.screen.width / 2 / k,
                  y0: man.ground_y - h * (1 + ROOM.top) / k, y1: man.ground_y + h * ROOM.bottom / k };
      touch();
    };
    let ro = null;
    if (window.ResizeObserver) { ro = new ResizeObserver(() => { fit(); }); ro.observe(host); }
    app.renderer.on("resize", fit);
    fit();

    // ---- the clock: the idle loops for ever; a one-shot plays once then eases back to the idle; a held loop loops
    const lengthOf = clip => (man.clips[clip].loop ? man.clips[clip].frames : man.clips[clip].frames - 1) * 1000 / fps;
    const cutOf = clip => (man.cut && (man.cut[clip] || man.cut["*"])) || (man.idle && man.idle.cut) || 8;
    let cur = { clip: "idle", t0: performance.now(), hold: false, last: -1 }, fade = null;
    const start = (clip, now, hold) => {
      fade = shown ? { clip: shown.clip, f: shown.f, t0: now, cut: cutOf(clip), glow: glowAt(shown.clip, shown.f) } : null;
      cur = { clip, t0: now, hold: !!hold, last: -1 };
    };
    const rawFrame = now => (now - cur.t0) * fps / 1000;
    const tick = () => {
      const now = performance.now();
      const C = man.clips[cur.clip];
      if (!C.loop && now - cur.t0 >= lengthOf(cur.clip)) start("idle", now, false);
      const C2 = man.clips[cur.clip], raw = rawFrame(now);
      const f = C2.loop ? raw % C2.frames : Math.max(0, Math.min(raw, C2.frames - 1));
      // the clip's live emits passed since the last frame (a loop's wrap counts round)
      if (C2.loop && cur.last >= 0 && f < cur.last) { emitBetween(cur.clip, cur.last, C2.frames, now); emitBetween(cur.clip, -1, f, now); }
      else emitBetween(cur.clip, cur.last, f, now);
      cur.last = f;
      let a = 0;
      if (fade) {
        a = 1 - (now - fade.t0) * fps / 1000 / fade.cut;
        if (a <= 0) { fade = null; a = 0; } else a = a * a * (3 - 2 * a);
      }
      sample(cur.clip, f, M);
      let glow = glowAt(cur.clip, f);
      if (fade) {
        sample(fade.clip, fade.f, M2);
        for (let k = 0; k < M.length; k++) M[k] += (M2[k] - M[k]) * a;
        glow += (fade.glow - glow) * a;
      }
      show(cur.clip, f, glow);
      if (light.to) relight(now);
      // the joint smokes all the time: a fine thread off its tip between the clip's own puffs (soft smoke only)
      if (LT.soft && !still && now - lastWisp > 230) { lastWisp = now; spawn("wisp1", now); }
      stepParticles(now);
      stepFlakes(now);
    };
    sample("idle", 0, M); show("idle", 0); app.render();
    let alive = true, frozen = false;
    if (!still) app.ticker.add(tick);
    const onVis = () => { if (document.hidden) app.ticker.stop(); else if (!frozen) { fit(); app.ticker.start(); } };
    document.addEventListener("visibilitychange", onVis);
    const thaw = () => { if (frozen) { frozen = false; if (!still && !document.hidden) app.ticker.start(); } };

    const player = {
      canvas: app.canvas, man,
      has: clip => !!man.clips[clip],
      length: clip => (man.clips[clip] ? lengthOf(clip) : 0),
      play(clip, { hold = false } = {}) {
        if (!alive || still || !man.clips[clip]) return false;
        thaw();
        start(clip, performance.now(), hold && man.clips[clip].loop);
        return true;
      },
      idle() {
        if (!alive || still) return false;
        thaw();
        if (cur.clip !== "idle") start("idle", performance.now(), false);
        return true;
      },
      state: () => ({ clip: cur.clip, hold: cur.hold, frame: shown ? +shown.f.toFixed(1) : 0, fading: !!fade,
                      density: D.d, still, particles: particles.length, res: +res.toFixed(3),
                      buffer: [app.canvas.width, app.canvas.height] }),
      // the atlas he was loaded with has gone soft for the size he is shown at now (a window grown a lot): remount
      stale: () => {
        const want = Math.max(80, host.clientHeight) / headroom * resFor(host) / man.rest_height;
        return want > D.d * 1.35 && man.densities.some(d => d.d > D.d);
      },
      resize: fit,
      // the scene's light: colours as 0xRRGGBB or "#rrggbb"; ms to ease over (0: at once)
      tint(body, groundC, ms = 700, shadeC) {
        if (!alive) return;
        const num = c => typeof c === "string" ? parseInt(c.replace("#", ""), 16) : c;
        const to = { body: body === undefined ? light.body : num(body), ground: groundC === undefined ? light.ground : num(groundC),
                     shade: shadeC === undefined ? light.shade : num(shadeC) };
        if (still || ms <= 0) { Object.assign(light, to); light.to = null; relight(0); app.render(); return; }
        light.from = { body: light.body, ground: light.ground, shade: light.shade }; light.to = to; light.t0 = performance.now(); light.ms = ms;
      },
      // the scene's snow falling in FRONT of him too (n near flakes over his canvas; 0: none)
      weather(n) { setSnow(n); },
      // QA: the clock stops and he is drawn on frame f of a clip until play() / idle() / resume()
      pose(clip, f) {
        if (!alive || !man.clips[clip]) return;
        frozen = true; app.ticker.stop(); fade = null;
        for (const p of particles) { p.s.visible = false; liveLayer.removeChild(p.s); pool.push(p.s); }
        particles.length = 0;
        sample(clip, f, M); show(clip, f); app.render();
      },
      resume() { thaw(); },
      // QA: draw only these pieces (part names; null = all) - the live and keyed effects are hidden meanwhile
      only(names) {
        onlySet = names ? new Set(names) : null;
        for (const q of parts) q.hidden = hideSet.has(q.p.name) || (!!onlySet && !onlySet.has(q.p.name));
        if (shown) { show(shown.clip, shown.f); app.render(); }
      },
      // QA: where a point is (art px) in the pose now drawn, and where the ember sprite is
      point: name => pointAt(name),
      emberAt: () => (ember ? { x: ember.position.x, y: ember.position.y, alpha: ember.alpha } : null),
      destroy() {
        if (!alive) return;
        alive = false;
        document.removeEventListener("visibilitychange", onVis);
        if (ro) ro.disconnect();
        try { app.destroy(true, { children: true, texture: true }); } catch (e) { /* already gone */ }
        stageEl.remove();
      },
    };
    return player;
  };
})();
