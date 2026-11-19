"""The landscape board frame (frontend/assets/frame_wide.webp) widened for wider cells (owner, 2026-11-17: "make it
wider"): the frame's middle third - its top and bottom edges run straight there - is stretched, so the rounded
corners keep their shape, and frame_wide.json's glass opening is worked out again. CELL_W must match the
stylesheet's landscape --cell-w; the script prints the --fo-l / --fo-w to put beside it.

    .venv/bin/python tools/highpeaks/widen_frame.py        (starts from art/highpeaks/work/frame_wide.134.webp, the 134 px cut)
"""
import json, os, shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'frontend', 'assets')
W = os.path.join(ROOT, 'art', 'highpeaks', 'work')
OLD_CELL, CELL_W, GAP = 134, 150, 6
src = os.path.join(W, 'frame_wide.134.webp')
if not os.path.exists(src):
    shutil.copyfile(os.path.join(A, 'frame_wide.webp'), src)
    shutil.copyfile(os.path.join(A, 'frame_wide.json'), os.path.join(W, 'frame_wide.134.json'))
im = Image.open(src).convert('RGBA')
meta = json.load(open(os.path.join(W, 'frame_wide.134.json')))
w, h = im.size
l, t, r, b = meta['opening']
grid = lambda c: 7 * (c + 10) + 6 * GAP
open_w = (r - l) * w                                      # the glass opening, in frame px
grow = round(open_w * (grid(CELL_W) + 12) / (grid(OLD_CELL) + 12) - open_w)
x0, x1 = w // 3, 2 * w // 3                               # the straight middle section
mid = im.crop((x0, 0, x1, h)).resize((x1 - x0 + grow, h), Image.LANCZOS)
out = Image.new('RGBA', (w + grow, h))
out.paste(im.crop((0, 0, x0, h)), (0, 0))
out.paste(mid, (x0, 0))
out.paste(im.crop((x1, 0, w, h)), (x1 + grow, 0))
out.save(os.path.join(A, 'frame_wide.webp'), 'WEBP', quality=90, method=6, alpha_quality=100)
W2 = w + grow
opening = [round(l * w / W2, 5), t, round(1 - (1 - r) * w / W2, 5), b]
meta.update(frame_size=[W2, h], opening=opening)
json.dump(meta, open(os.path.join(A, 'frame_wide.json'), 'w'))
print(f'frame_wide: {w} -> {W2} px wide; --fo-l: {opening[0]}; --fo-w: {round(opening[2] - opening[0], 5)}')
