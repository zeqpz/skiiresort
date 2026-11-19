"""FUEL CHANCE's gauge reads green to red (owner, 2026-11-13: "the fuel chance is going from red to green instead of
green to red"): in the bonus menu's FUEL CHANCE picture (frontend/assets/menu/chance.webp) the gauge's coloured arc
is mirrored in hue - red <-> green through the same yellow - inside the arc's ring only (the red needle at the hub and
the red nozzle are left as they are). Starts from the restyle's original kept in art/highpeaks/ui_glossy/ if a copy of
the flat picture is there, else from the current file, kept once as art/highpeaks/ui_flat/menu/chance.webp.

    .venv/bin/python tools/highpeaks/chance_gauge.py      (then compress_assets.py)
"""
import os, shutil, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recolour import hsv, rgb  # noqa: E402

P = os.path.join(ROOT, 'frontend', 'assets', 'menu', 'chance.webp')
KEEP = os.path.join(ROOT, 'art', 'highpeaks', 'ui_flat', 'menu', 'chance.webp')
CX, CY, R0, R1 = .503, .54, .27, .43        # the gauge's hub and the arc's ring, as fractions of the picture's height
if not os.path.exists(KEEP):
    os.makedirs(os.path.dirname(KEEP), exist_ok=True)
    shutil.copyfile(P, KEEP)
im = Image.open(KEEP).convert('RGBA')
a = np.asarray(im).astype(np.float32) / 255
H, W = a.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
d = np.hypot(xx - CX * W, yy - CY * H) / H
ring = (d > R0) & (d < R1) & (yy < CY * H + .02 * H)
h, s, v = hsv(a)
h = np.where(h > 330, h - 360, h)
ang = np.degrees(np.arctan2(CY * H - yy, xx - CX * W))          # degrees above the hub's right
needle = (ang > 15) & (ang < 36)                                 # the needle points up-right at ~25 degrees: left red
# along the needle the arc was green and the needle red: there only the green turns (to red), the needle stays
arc = ring & (s > .35) & (h > -30) & (h < 140) & (v > .3) & (~needle | ((h > 60) & (h < 140)))
h2 = np.where(arc, 118 - h, h) % 360
a[..., :3] = np.where(arc[..., None], rgb(h2, s, v), a[..., :3])
Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)).save(P, 'WEBP', quality=92, method=6)
print('gauge arc mirrored:', int(arc.sum()), 'px')
