/* High Peaks: the yeti (2026-11-19) - an original cartoon yeti in ski gear with a joint, his snowboard stuck in the snow
   beside him. A live cut-out rig made in Blender (tools/highpeaks/yeti/), posed every frame by charrig.js.

   window.Yeti = {
     mount(hostEl, { flip, headroom, base, maxFps }) -> Promise<boolean>  false when he can't be shown (no WebGL/Pixi)
     react(name) -> boolean   "win" | "big_win" | "bonus" | "lose" | "anticipation" | "idle"
                              anticipation LOOPS (he leans in, sweats, grips his board) until react()/idle() is called;
                              the others play once and ease back into the idle. A smaller reaction never cuts a bigger
                              one short (bonus > big_win > lose > win); anticipation and idle always cut in.
     idle()                   back to the idle loop
     destroy()
     state()                  { clip, hold, frame, ... } for debugging
   }
   His box: he stands on the host element's bottom edge (the bottom of his snow mound), centred, his standing figure
   (pom-pom to snow) = the box's height / headroom; his canvas overflows the box (smoke, sparks, arms up) and takes no
   pointer events. As drawn he faces a little to the viewer's LEFT: put him right of the board, or pass flip: true.
   charReact in index.html can call Yeti.react(kind) directly. */
(function () {
  "use strict";
  const RANK = { win: 1, lose: 2, big_win: 3, bonus: 4 };
  let rig = null, rank = 0, until = 0, mounting = null;
  const Y = (window.Yeti = {});

  Y.mount = async (hostEl, opts = {}) => {
    if (rig) Y.destroy();
    if (!hostEl || !window.CharRig) return false;
    mounting = CharRig.make({ host: hostEl, base: opts.base || "assets/yeti/rig/", flip: !!opts.flip,
                              headroom: opts.headroom || 1.06, maxFps: opts.maxFps || 60 });
    try { rig = await mounting; } catch (e) { rig = null; }
    mounting = null;
    rank = 0; until = 0;
    return !!rig;
  };
  Y.react = name => {
    if (!rig) return false;
    if (name === "idle") return Y.idle();
    if (name === "anticipation") {
      rank = 0; until = 0;
      return rig.play("anticipation", { hold: true });
    }
    const r = RANK[name];
    if (!r) return false;
    const now = performance.now();
    if (now < until && r < rank) return false;     // a bigger reaction is still playing
    if (!rig.play(name)) return false;
    rank = r; until = now + rig.length(name);
    return true;
  };
  Y.idle = () => {
    if (!rig) return false;
    rank = 0; until = 0;
    return rig.idle();
  };
  Y.destroy = () => { if (rig) rig.destroy(); rig = null; rank = 0; until = 0; };
  Y.state = () => (rig ? rig.state() : null);
  Y.pose = (clip, f) => { if (rig) rig.pose(clip, f); };   // QA: the clock stops on a frame of a clip...
  Y.resume = () => { if (rig) rig.resume(); };               // ...until react() / idle() / resume()
  Y.only = names => { if (rig) rig.only(names); };          // QA: draw only these pieces
  Y.point = name => (rig ? rig.point(name) : null);          // QA: a bone point now (art px): tip, end, lips, mouth, brow
  Y.emberAt = () => (rig ? rig.emberAt() : null);            // QA: where the ember is drawn (art px)
})();
