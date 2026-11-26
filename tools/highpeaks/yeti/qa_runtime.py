"""High Peaks yeti QA in the REAL runtime (frontend/charrig.js + yeti.js on the packed rig), no node needed: a local
static server on frontend/ (127.0.0.1 only), headless Chrome over the DevTools protocol (the stdlib driver of
Documents/fallslotsga/tools/review/cdp.py, imported read-only), frontend/yeti_test.html.
  * the rig mounts, every clip exists, the console is clean
  * the runtime's own points against Blender's (rig_build/qa_points.json): tip, end, lips on every frame; the ember on
    the tip; the joint's end on his lips through the hold
  * frame pacing while each clip plays (requestAnimationFrame deltas: fps, worst frame) and through cross-fades
  * screenshots of key poses of every clip -> art/highpeaks/yeti/rig_build/runtime/<clip>_<frame>.png
  python tools/highpeaks/yeti/qa_runtime.py [--base http://localhost:8755]"""
import functools, http.server, json, os, socket, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FRONT = os.path.join(ROOT, "frontend")
BUILD = os.path.join(ROOT, "art", "highpeaks", "yeti", "rig_build")
OUT = os.path.join(BUILD, "runtime")
CDP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "fallslotsga", "tools", "review")
SHOTS = {"idle": [0, 60, 96, 104, 108, 112, 116, 128, 142, 148, 152, 158, 166, 180], "anticipation": [0, 15, 30, 45], "win": [6, 13, 24, 31, 44],
         "big_win": [9, 16, 22, 35, 59, 87, 108], "bonus": [9, 20, 26, 37, 62, 86, 110, 114, 122], "lose": [7, 20, 33, 50, 70]}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Quiet, directory=FRONT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def main():
    sys.path.insert(0, CDP_DIR)
    import cdp
    os.makedirs(OUT, exist_ok=True)
    for old in os.listdir(OUT):
        os.remove(os.path.join(OUT, old))
    qp = json.load(open(os.path.join(BUILD, "qa_points.json")))
    base = sys.argv[sys.argv.index("--base") + 1].rstrip("/") if "--base" in sys.argv else None
    srv = None
    if not base:                                               # (--base: a server that already serves frontend/, e.g.
        srv, port = serve()                                    # the game's mock on http://localhost:8755 - none started)
        base = f"http://127.0.0.1:{port}"
    print("page:", base + "/yeti_test.html")
    b = cdp.Browser(1100, 1500)
    try:
        b.open(f"{base}/yeti_test.html?size=qa", settle=1.0)
        if not b.wait("window.__yetiReady !== undefined", 60):
            raise RuntimeError("the test page never mounted him")
        print("mounted:", b.js("window.__yetiReady"), "| state", json.dumps(b.js("Yeti.state()")))
        print("renderer:", b.js("(() => { const c = document.createElement('canvas'); const g = c.getContext('webgl'); "
                                "const e = g && g.getExtension('WEBGL_debug_renderer_info'); return e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'n/a'; })()"))
        # ---- points: the runtime against Blender
        worst = {"tip": 0.0, "end": 0.0, "lips": 0.0, "ember": 0.0}
        n = 0
        for c, rows in qp["points"].items():
            got = b.js("(() => { const out = []; for (let f = 0; f < %d; f++) { Yeti.pose('%s', f); const t = Yeti.point('tip'), e = Yeti.point('end'), "
                       "l = Yeti.point('lips'), m = Yeti.emberAt(); out.push([t.x, t.y, e.x, e.y, l.x, l.y, m.x, m.y]); } return out; })()" % (len(rows), c))
            for r, g in zip(rows, got):
                n += 1
                for k, name in enumerate(("tip", "end", "lips")):
                    worst[name] = max(worst[name], ((g[2 * k] - r[2 * k]) ** 2 + (g[2 * k + 1] - r[2 * k + 1]) ** 2) ** .5)
                worst["ember"] = max(worst["ember"], ((g[6] - g[0]) ** 2 + (g[7] - g[1]) ** 2) ** .5)
        print(f"points on {n} posed frames: runtime vs Blender worst tip {worst['tip']:.4f}, end {worst['end']:.4f}, lips {worst['lips']:.4f} art px; "
              f"ember off the tip worst {worst['ember']:.4f}")
        for (a, hb, hc, d) in qp["contact"].get("idle", []):
            gaps = b.js("(() => { const out = []; for (let f = %d; f <= %d; f += .5) { Yeti.pose('idle', f); const e = Yeti.point('end'), l = Yeti.point('lips'); "
                        "out.push(Math.hypot(e.x - l.x, e.y - l.y)); } return out; })()" % (hb, hc))
            print(f"the puff: joint end to lips through the hold {hb}-{hc}, whole and half frames (the runtime's Catmull-Rom): max {max(gaps):.3f} art px")
        # ---- screenshots of key poses (on a flat blue: a see-through sliver in his white fur would not show on white)
        b.js("document.documentElement.style.background = document.body.style.background = 'rgb(58,96,150)'")
        for c, frames in SHOTS.items():
            for f in frames:
                b.js(f"Yeti.pose('{c}', {f})")
                time.sleep(.12)
                b.shot(os.path.join(OUT, f"{c}_{f:03d}.png"))
        try:                                                    # the puff side by side: arm and head close up
            from PIL import Image, ImageDraw
            fs = [f for f in SHOTS["idle"] if 96 <= f <= 180]
            box, cols = (330, 330, 880, 1000), 6
            w, h = box[2] - box[0], box[3] - box[1]
            sheet = Image.new("RGB", (w * cols, h * ((len(fs) + cols - 1) // cols)), (58, 96, 150))
            dr = ImageDraw.Draw(sheet)
            for j, f in enumerate(fs):
                x, y = (j % cols) * w, (j // cols) * h
                sheet.paste(Image.open(os.path.join(OUT, f"idle_{f:03d}.png")).convert("RGB").crop(box), (x, y))
                dr.text((x + 6, y + 4), f"runtime idle {f}", fill=(255, 255, 0))
            sheet.save(os.path.join(OUT, "_puff_sheet.png"))
            print("the puff in the runtime:", os.path.join(OUT, "_puff_sheet.png"))
        except ImportError:
            pass
        # ---- pacing: each clip played live, then a chain of cuts
        pace = """(async () => {
          Yeti.resume();
          const run = async (name, ms) => {
            Yeti.react(name);
            const d = []; let last = performance.now(); const t0 = last;
            while (performance.now() - t0 < ms) { await new Promise(ok => requestAnimationFrame(ok)); const now = performance.now(); d.push(now - last); last = now; }
            d.sort((x, y) => x - y);
            const sum = d.reduce((x, y) => x + y, 0);
            return [name, d.length, +(1000 * d.length / sum).toFixed(1), +d[Math.floor(d.length * .5)].toFixed(2), +d[Math.floor(d.length * .95)].toFixed(2), +d[d.length - 1].toFixed(2)];
          };
          const out = [];
          for (const [nm, ms] of [["idle", 4000], ["win", 2200], ["anticipation", 2500], ["lose", 3200], ["big_win", 4200], ["bonus", 5200], ["idle", 1500]]) out.push(await run(nm, ms));
          return out;
        })()"""
        b.ws.events.clear()
        rows = b.js(pace)
        print("pacing while playing (requestAnimationFrame; the player's own ticker is capped at 60):")
        for nm, cnt, fps, p50, p95, mx in rows:
            print(f"  {nm:13s} {cnt:4d} frames  {fps:6.1f} fps  frame ms p50 {p50} p95 {p95} worst {mx}")
        print("state after:", json.dumps(b.js("Yeti.state()")))
        errs = [e for e in b.console() if "GPU stall" not in e and "swiftshader" not in e.lower()]
        print("console:", " | ".join(errs) if errs else "clean")
    finally:
        b.close()
        if srv:
            srv.shutdown()


if __name__ == "__main__":
    main()
