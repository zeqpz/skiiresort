"""Centre every symbol's picture in its cell (owner, 2026-11-10: "make each symbol perfectly center in their own
cells"): each clip's box hangs a little lower than the icon (more room under it for the landing squash and the
particles), so a symbol's picture sat up to 12% of a cell low. This measures where the picture's solid part sits in
its resting pose (the landing clip's last frame) and writes the shift that puts it dead centre into
frontend/assets/sym/manifest.json as symbols[id].centre = [dx, dy] (rig units: the icon is 100 across). The board
canvas (boardgl.js) and the page's own fallback (symLay) add it. Re-run after packing new symbol sheets.

    .venv/bin/python tools/highpeaks/centre_symbols.py
"""
import json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYM = os.path.join(ROOT, 'frontend', 'assets', 'sym')
man = json.load(open(os.path.join(SYM, 'manifest.json')))
dens = sorted(man['densities'])[-1]
d = 'd%d' % round(dens * 10)
for sid, v in man['symbols'].items():
    sh, clip = v['sheets'][d]['land'], v['clips']['land']
    f = clip['frames'] - 1
    im = Image.open(os.path.join(SYM, d, f'{sid}_land.webp')).convert('RGBA')
    x0, y0 = (f % sh['cols']) * sh['w'], (f // sh['cols']) * sh['h']
    bb = im.crop((x0, y0, x0 + sh['w'], y0 + sh['h'])).getchannel('A').point(lambda a: 255 if a > 128 else 0).getbbox()
    bx, icon = clip['box'], v['icon']
    cx = (bx[0] + icon[0] / 2) * 10 + (bb[0] + bb[2]) / 2 / sh['w'] * bx[2] * 10
    cy = (bx[1] + icon[1] / 2) * 10 + (bb[1] + bb[3]) / 2 / sh['h'] * bx[3] * 10
    v['centre'] = [round(icon[0] * 5 - cx, 2), round(icon[1] * 5 - cy, 2)]
    print(f'{sid:4s} shift {v["centre"]}')
json.dump(man, open(os.path.join(SYM, 'manifest.json'), 'w'), separators=(',', ':'))
