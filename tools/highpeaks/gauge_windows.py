"""FILL UP's fuel gauge shows its fuel (owner, 2026-11-16: "make these like how many spins you have"): the flat gauge
art (frontend/assets/fillup/gauge.webp) came with its three glass windows painted solid black, over the fuel bars the
page draws behind it (.fgauge > i) - so the gauge always read empty. This cuts the windows open: each window's dark
interior (the three big near-black regions inside the gauge) is made see-through, its ink edge kept (the region
shrunk by EDGE px, feathered), and prints the windows' boxes in % for the page's .fgauge > i rules.

    .venv/bin/python tools/highpeaks/gauge_windows.py
"""
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'frontend', 'assets', 'fillup', 'gauge.webp')
EDGE = 4

im = Image.open(P).convert('RGBA')
a = np.asarray(im).copy()
H, W = a.shape[:2]
dark = (a[..., :3].max(2) < 40) & (a[..., 3] > 200)
lab, n = ndimage.label(dark)
wins = []
for i, sl in enumerate(ndimage.find_objects(lab)):
    m = lab == i + 1
    h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    # a window: big, wider than tall, and in the gauge's middle band (not its outline, not the pump icon at the left)
    if m.sum() > 15000 and w > h and sl[1].start > W * .25 and sl[0].start > H * .2:
        wins.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop, m))
hole = np.zeros((H, W), bool)
for *_, m in wins:
    hole |= ndimage.binary_erosion(ndimage.binary_fill_holes(m), iterations=EDGE)
alpha = Image.fromarray((hole * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))
a[..., 3] = (a[..., 3].astype(np.float32) * (1 - np.asarray(alpha, np.float32) / 255)).astype(np.uint8)
Image.fromarray(a).save(P, 'WEBP', quality=90, method=6, alpha_quality=100)
for x0, y0, x1, y1, _ in sorted(wins, key=lambda w: w[0]):
    print(f'left {x0 / W * 100:.2f}%  top {y0 / H * 100:.2f}%  width {(x1 - x0) / W * 100:.2f}%  height {(y1 - y0) / H * 100:.2f}%')
