"""High Peaks QA: moments of the real game, photographed in headless Chrome while they play (the stdlib DevTools
driver of Documents/fallslotsga/tools/review/cdp.py, imported read-only). The mock RGS must be running on :8755.

    python tools/highpeaks/qa_shots.py OUT_DIR SCENARIO [WxH]

Scenarios:
  bong      the ice bong fires in a column (index.html pumpShow): its drop, the rip, the multiplier landing
  bongmax   the same, WHITEOUT
  scene     the game at rest (the layered scene, the yeti)
  menu      the Bonus Buy menu open
  win       a board of win amounts (.winpop) and the win numerals

Each writes OUT_DIR/<scenario>_<n>.png and prints the page's console errors.
"""
import json, os, sys, time

CDP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "fallslotsga", "tools", "review")
URL = "http://localhost:8755/index.html?sessionID=qa{n}&rgs_url=http://localhost:8755&lang=en&device=desktop"
ENTER = "(() => { const el = document.elementFromPoint(innerWidth / 2, innerHeight * .83); el && el.click(); return true; })()"
PUMP = ("(() => {{ window.__ps = 0; const R = {reel}, M = {mult}; pumpShow({{ reel: R, row: 3, grade: '{grade}', mult: M, "
        "cells: M ? [1, 2, 3, 4, 5].map(row => ({{ reel: R, row, from: 1, to: M }})) : [], burned: [1, 2, 4, 5].map(row => ({{ reel: R, row }})) }})"
        ".then(r => {{ window.__ps = 1; setTimeout(() => {{ r.dial.remove(); r.glow.remove(); }}, 1500); }}).catch(e => {{ window.__ps = String(e && e.stack || e); }}); return true; }})()")


def main():
    out, scen = sys.argv[1], sys.argv[2]
    w, h = (int(v) for v in (sys.argv[3] if len(sys.argv) > 3 else "1280x620").split("x"))
    sys.path.insert(0, CDP_DIR)
    import cdp
    os.makedirs(out, exist_ok=True)
    b = cdp.Browser(w, h)
    n = [0]

    def shot():
        p = os.path.join(out, f"{scen}_{n[0]}.png"); n[0] += 1
        b.shot(p)
        return p
    try:
        b.js("window.__errs = []; addEventListener('error', e => window.__errs.push(String(e.message)));")
        url = URL.format(n=int(time.time()) % 100000)
        if scen.startswith("replay"):
            url = ("http://localhost:8755/index.html?replay=true&game=highpeaks&version=1&mode=base&event=" + scen[6:] +
                   "&amount=1000000&rgs_url=http://localhost:8755&lang=en&device=desktop")
        b.open(url, settle=1.0)
        b.js("window.__errs = window.__errs || []; addEventListener('error', e => window.__errs.push(String(e.message)));")
        if not b.wait("typeof state !== 'undefined' && !!document.querySelector('.cell')", 60):
            raise RuntimeError("the game never came up")
        time.sleep(5)
        b.js(ENTER)
        time.sleep(1.2 if scen.startswith("replay") else 6)
        if scen in ("bong", "bongmax"):
            mx = scen == "bongmax"
            b.js(PUMP.format(reel=4, grade="fulltank" if mx else "plus", mult=0 if mx else 16))
            for wait in (.12, .12, .12, .14, .3, .45, .45, .45, .5, .6):
                time.sleep(wait)
                shot()
            print("pumpShow:", b.js("window.__ps"))
        elif scen.startswith("replay"):      # replayID: a real book played back (base mode), a shot every .6 s for 15 s
            b.js("(() => { const p = [...document.querySelectorAll('button')].find(x => /^play$/i.test(x.textContent.trim())); p && p.click(); return !!p; })()")
            for _ in range(25):
                time.sleep(.6)
                shot()
        elif scen == "scene":
            shot()
        elif scen == "menu":
            b.js("(document.querySelector('.bonusbtn') || {}).click && document.querySelector('.bonusbtn').click()")
            time.sleep(1.6)
            shot()
        elif scen == "win":
            b.js("(() => { const P = (r, y) => ({ reel: r, row: y + 1 }); placeWinChip([P(1, 1), P(2, 1)], 1250000, 1); placeWinChip([P(4, 3), P(5, 3)], 48600000, 8); return true; })()")
            for wait in (.5, .9, 1.2):
                time.sleep(wait)
                shot()
        elif scen == "alert":                # the alert strip (RAPID ON/OFF and the rest): where it sits and what it measures
            b.js("notice('<b>RAPID ON</b> \\u2014 spins play fast', false, 6000)")
            time.sleep(.6)
            shot()
            print("alert:", json.dumps(b.js(
                "(() => { const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(v => Math.round(v)); };"
                " const n = document.getElementById('notice'), c = getComputedStyle(n), h = document.querySelector('.hudbar, #hud, .hud');"
                " return { notice: r(n), frame: r(document.getElementById('paintframe')), hud: h ? r(h) : null, bg: c.backgroundColor, font: c.fontFamily.slice(0, 30), border: c.border }; })()")))
            b.js("notice('<b>Connection lost</b> \\u2014 check your network and try again', true, 6000)")
            time.sleep(.6)
            shot()
        elif scen == "cam":                  # a camera move, held: does the yeti go with the mountain, behind the foreground?
            print("yeti:", json.dumps(b.js(
                "(() => { const y = document.getElementById('yetiBox'), f = document.querySelector('.lyfront');"
                " return { parent: y.parentElement.id, z: getComputedStyle(y).zIndex, frontZ: f && getComputedStyle(f).zIndex, fronts: document.querySelectorAll('.lyfront').length,"
                " yetiBeforeFront: !!(f && (y.compareDocumentPosition(f) & 4)) }; })()")))
            shot()
            rect = "(() => { const b = document.getElementById('yetiBox').getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(v => +v.toFixed(1)); })()"
            print("yeti at rest:", b.js(rect))
            b.js("Cam.trigger([...document.querySelectorAll('.cell')].slice(0, 3), true)")      # the game's own biggest move
            time.sleep(1.3)
            print("yeti in the bonus-trigger move:", b.js(rect))
            shot()
            b.js("Cam.reset()")
            # the same thing made big enough to see in a picture: the scene layer panned, rolled and zoomed by hand
            b.js("document.getElementById('camfar').style.transform = 'translate(-46px, 20px) rotate(2deg) scale(1.14)'")
            time.sleep(.4)
            shot()
            # and what a spin does to the background now (it used to hop): the wall's animations while the reels turn
            b.js("document.getElementById('camfar').style.transform = ''")
            b.js("(() => { const s = document.querySelector('.spinbtn, #spin, [data-act=spin]'); s && s.click(); return !!s; })()")
            time.sleep(.25)
            print("background on spin:", json.dumps(b.js("(() => { const w = document.getElementById('bgwall'); return { cls: w.className, anims: w.getAnimations().map(a => a.animationName || 'web'), boardPop: document.getElementById('board').classList.contains('pop') }; })()")))
        print("errors:", json.dumps(b.js("window.__errs")))
        print("shots:", n[0], "->", out)
    finally:
        b.close()


if __name__ == "__main__":
    main()
