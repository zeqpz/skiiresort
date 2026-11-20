"""High Peaks: take the Blender-rendered duck out of the game (owner, 2026-11-19: "get rid of the 3d characters another
AI accidentally generated those - they don't fit the game theme").

The duck by the board (duckfx.js, #duck) and the skiing ducks on the slope (skyfx.js duck_ski / duck_board strips)
were 3D renders; the game is flat adult-animation cartoon. The slope keeps its flat-cartoon skier and snowboarder
sprites (assets/scene/skier.webp, boarder.webp), which skyfx.js already drew whenever a duck strip was missing.
The reaction hooks (charReact etc.) stay as no-ops, as they were before the duck.

Exact-string edits; every one must match once. Run from the repo root:  python tools/highpeaks/remove_duck.py
"""
import pathlib, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FE = ROOT / "frontend"


def edit(path, pairs):
    p = FE / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            sys.exit(f"{path}: expected 1 match, found {n}: {old[:90]!r}")
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8", newline="\n")


edit("index.html", [
    # the duck's stylesheet (the bonus counter's railside placement under it stays: it reads well without the duck)
    ("""  /* ---------- High Peaks: the duck by the board (duckfx.js) ---------- */
  /* upright screens: the jackpot row moves left and the duck stands on the snowy top log at the right, off the reels */
  .duck { position: absolute; z-index: 7; pointer-events: none; aspect-ratio: 300 / 372;
    right: 1%; bottom: calc(100% - 150px); height: 250px; filter: drop-shadow(0 8px 10px rgba(0, 0, 0, .35)); }
  html:not(.railside) .jpbar { justify-content: flex-start; padding-left: 12px; }
  html.railside .duck { right: auto; left: calc(100% - 34px); bottom: 30px; height: 64%; }
  .duck canvas { width: 100%; height: 100%; display: block; }
  /* beside the board the bonus counter sits at the top of the glass now: the duck stands at the bottom */
""",
     """  /* ---------- High Peaks: the bonus counter beside the board sits at the top of the glass ---------- */
"""),
    ("""    <div class="duck" id="duck" aria-hidden="true"></div>\n""", ""),
    ("""<script src="duckfx.js"></script>\n""", ""),
    ("""if (window.Duck) Duck.start($("duck"));        // High Peaks: the duck by the board (duckfx.js)\n""", ""),
    ("""// High Peaks: the duck (duckfx.js) answers them: a win -> a hop, a big win -> a dance, a tease -> a shrug
const CHAR_REACT = { win: "win", big_win: "bonus", lose: "tease" };
let charReact = kind => { if (window.Duck && CHAR_REACT[kind]) Duck.react(CHAR_REACT[kind]); }, charEnter = () => {}, charExit = () => {};""",
     """// (High Peaks, 2026-11-19: the Blender duck that answered them is gone - it was 3D in a flat cartoon game)
let charReact = () => {}, charEnter = () => {}, charExit = () => {};"""),
    ("""    if (window.Duck) Duck.react("mult");   // whoa\n""", ""),
    ("""    if (window.Duck) Duck.react("bonus");\n""", ""),
    ("""      if (window.Duck) Duck.bonus(true);   // bobs to the bonus music\n""", ""),
    ("""  if (window.Duck) Duck.bonus(false);\n""", ""),
])

edit("skyfx.js", [
    ("""  // the skiing ducks: Blender-animated loops (tools/highpeaks/pack_duck.py), one strip of frames each
  const strips = {};
  function strip(name) {
    if (!strips[name]) {
      const st = strips[name] = { im: pic(name), meta: null };
      fetch(B + name + ".json").then(r => r.ok ? r.json() : null).then(m => { st.meta = m; }).catch(() => {});
    }
    return strips[name];
  }
""", ""),
    ("""        const st = strip("duck_" + r.who), m = st.meta;
        if (m && ok(st.im)) {   // the animated duck, on its own clock
          const fi = Math.floor((t - r.t0) / 1000 * m.fps) % m.frames;
          sprite(st.im, x + carve, y, RIDER_H * k * 1.1, { flip: x2 > x, anchorY: .9, alpha: Math.min(1, u * 8), src: [fi * m.w, 0, m.w, m.h] });
        } else {
          sprite(pic(r.who === "ski" ? "skier" : "boarder"), x + carve, y, RIDER_H * k, { flip: x2 > x, anchorY: .85, alpha: Math.min(1, u * 8) });
        }
""",
     """        sprite(pic(r.who === "ski" ? "skier" : "boarder"), x + carve, y, RIDER_H * k, { flip: x2 > x, anchorY: .85, alpha: Math.min(1, u * 8) });
"""),
    ("""    strip("duck_ski"); strip("duck_board");\n""", ""),
])

# the duck's code and frames (and the Blender pipeline that made them: git history keeps it)
for rel in ["frontend/duckfx.js", "frontend/assets/duck", "frontend/assets/scene/duck_ski.webp", "frontend/assets/scene/duck_ski.json",
            "frontend/assets/scene/duck_board.webp", "frontend/assets/scene/duck_board.json", "tools/highpeaks/pack_duck.py",
            "tools/highpeaks/blender/duck_build.py", "tools/highpeaks/blender/duck_anim.py", "tools/highpeaks/blender/duck_render.py",
            "art/highpeaks/blender"]:
    p = ROOT / rel
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()
print("duck removed")
