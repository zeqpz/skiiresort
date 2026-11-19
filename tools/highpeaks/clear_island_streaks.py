"""The coloured streaks on the pavement just under the pump island's foot are painted out (owner, 2026-11-17: "remove
these colors down there") - on every plate. Under the island's black outline, in each column, any pixel that does not
match that column's pavement further down is replaced by the pavement a little below it; the outline and the island
are left alone. Writes the plates (2560) and their phone twins (_m, 1600).

    .venv/bin/python tools/highpeaks/clear_island_streaks.py      (after pump_align.py and building_tall.py)
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'highpeaks'))
from compress_assets import encode, PLATE_Q, PLATE_W_M   # noqa: E402

A = os.path.join(ROOT, 'frontend', 'assets')
X0, X1 = 300, 800          # the island's span on a 2560-wide plate
Y_EDGE = (1140, 1240)      # where its black foot outline can be
Y_END = 1262               # the streaks end above this row
REF = (1275, 1320)         # the pavement under it, the colour each column should be
SHIFT = 48                 # replacement pixels come from this far below
PLATES = ['bonus_wall.webp', 'scene/plate_zombie.webp', 'scene/plate_midnight.webp', 'scene/plate_nitro.webp']

# The island's foot: the same shape on every plate (pump_align.py put the same island in each), measured once on the
# normal scene's grey pavement, where its black outline stands out plainly (a night scene's navy pavement, and the
# streaks' own black outlines, would fool the measuring there)
lit = np.asarray(Image.open(os.path.join(A, PLATES[0])).convert('RGB')).astype(np.int16)
FOOT = {}
for x in range(X0, X1):
    dark = np.nonzero(lit[Y_EDGE[0]:Y_EDGE[1], x].max(axis=1) < 40)[0]
    if len(dark):
        FOOT[x] = Y_EDGE[0] + dark.max() + 3            # just under the outline

for rel in PLATES:
    p = os.path.join(A, rel)
    im = Image.open(p).convert('RGB')
    a = np.asarray(im).astype(np.int16).copy()
    mask = np.zeros(a.shape[:2], bool)
    for x, top in FOOT.items():
        ref = np.median(a[REF[0]:REF[1], x], axis=0)
        diff = np.abs(a[top:Y_END, x] - ref).max(axis=1)
        mask[top:Y_END, x] = diff > 34
    # grow the marks a little so their soft edges go too, never up into the outline
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    mask = np.asarray(m) > 0
    ys, xs = np.nonzero(mask)
    a[ys, xs] = a[ys + SHIFT, xs]
    out = Image.fromarray(a.astype(np.uint8))
    # soften the patched pixels into their neighbours
    soft = out.filter(ImageFilter.GaussianBlur(1.2))
    alpha = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))
    out = Image.composite(soft, out, alpha)
    encode(out, p, PLATE_Q, 100)
    small = out.resize((PLATE_W_M, round(out.height * PLATE_W_M / out.width)), Image.LANCZOS)
    encode(small, p[:-5] + '_m.webp', PLATE_Q, 100)
    print(f'{rel}: {int(mask.sum())} streak pixels painted out')
