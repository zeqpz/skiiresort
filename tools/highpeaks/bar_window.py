"""The loading bar's window, see-through again (owner, 2026-11-13: "make this bar full of gas"): the flat restyle
(restyle.py) drew frontend/assets/load/bar_frame.webp's tube window as solid black, which hid the fuel the page
fills in behind it (.lbtube under .lbframe). This floods the window from its centre over the near-black pixels and
clears them, with a 1 px feathered edge against the frame's ink, and prints the window's box as fractions of the
picture for the page's .lbtube.

    .venv/bin/python tools/highpeaks/bar_window.py
"""
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, 'frontend', 'assets', 'load', 'bar_frame.webp')
im = Image.open(P).convert('RGBA')
a = np.asarray(im).copy()
H, W = a.shape[:2]
dark = (a[..., :3].max(-1) < 40) & (a[..., 3] > 200)
lab, _ = ndimage.label(dark)
cy, cx = H // 2, W // 2
seed = lab[cy, cx] or np.bincount(lab[cy - 5:cy + 5, cx - 50:cx + 50].ravel())[1:].argmax() + 1
win = lab == seed
win = ndimage.binary_fill_holes(win)
ys, xs = np.nonzero(win)
alpha = Image.fromarray(np.where(win, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.8))
a[..., 3] = np.minimum(a[..., 3], np.asarray(alpha))
Image.fromarray(a).save(P, 'WEBP', quality=92, method=6)
print(f'window cleared: {int(win.sum())} px; left {xs.min() / W * 100:.1f}% width {(xs.max() - xs.min() + 1) / W * 100:.1f}% '
      f'top {ys.min() / H * 100:.1f}% height {(ys.max() - ys.min() + 1) / H * 100:.1f}%; picture {W}x{H}')
