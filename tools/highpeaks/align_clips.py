"""Every clip lined up on the symbol's rest pose (owner, 2026-11-12: "if you stare at the symbols long enough they do
a weird glitch"): a resting symbol shows the landing clip's last frame (index.html symRest), and every 8-20 s it plays
its idle cycle - but the idle sheets were packed with the picture sitting somewhere else in the clip's box than the
landing's (up to 11% of the icon on L3), so the symbol jumped as the idle started and jumped back as it ended. The
same can hold for the hit and burn clips as they cut in.

This measures, for each symbol and clip, where the clip's first frame sits against the rest pose (alpha centroid at
the densest sheet, in the clip's own box) and moves the clip's box in frontend/assets/sym/manifest.json by that much,
so frame 0 lands exactly on the rest pose. The board canvas (boardgl.js) and the page's fallback (symLay) both place
a clip by its box, so nothing else changes. Idempotent: a clip already in place is moved by ~0.

    .venv/bin/python tools/highpeaks/align_clips.py         (re-run after packing new symbol sheets, before centre_symbols.py)
"""
import json, os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYM = os.path.join(ROOT, 'frontend', 'assets', 'sym')
CLIPS = ('idle', 'hit', 'burn')
man = json.load(open(os.path.join(SYM, 'manifest.json')))
dens = sorted(man['densities'])[-1]
D = 'd%d' % round(dens * 10)
PX = 10 * dens   # sheet px per box unit (the icon is 10 box units across)


def centroid(sid, clip, f):
    """The frame's solid part's centre, in box units of the symbol's own space (the clip's box placed)."""
    v = man['symbols'][sid]
    sh, bx = v['sheets'][D][clip], v['clips'][clip]['box']
    im = Image.open(os.path.join(SYM, D, f'{sid}_{clip}.webp')).convert('RGBA')
    x0, y0 = (f % sh['cols']) * sh['w'], (f // sh['cols']) * sh['h']
    a = np.asarray(im.crop((x0, y0, x0 + sh['w'], y0 + sh['h'])).getchannel('A')) > 128
    ys, xs = np.nonzero(a)
    # sheet px -> box units: the sheet frame spans the box
    return np.array([bx[0] + (xs.mean() + .5) / sh['w'] * bx[2], bx[1] + (ys.mean() + .5) / sh['h'] * bx[3]])


for sid, v in man['symbols'].items():
    land = v['clips']['land']
    rest = centroid(sid, 'land', land['frames'] - 1)
    out = []
    for clip in CLIPS:
        c = v['clips'].get(clip)
        if not c:
            continue
        d = rest - centroid(sid, clip, 0)
        c['box'][0] = round(c['box'][0] + d[0], 4)
        c['box'][1] = round(c['box'][1] + d[1], 4)
        out.append(f'{clip} {d[0]:+.2f},{d[1]:+.2f}')
    print(f'{sid:4s} moved (box units, icon = 10): ' + '  '.join(out))
json.dump(man, open(os.path.join(SYM, 'manifest.json'), 'w'), separators=(',', ':'))
