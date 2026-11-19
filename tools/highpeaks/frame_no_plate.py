"""The board frame without its FALCOS title plate (owner, 2026-11-17: "remove this so you can see the falcos sign in the
back"): the plate painted on the frame's top edge is cleared from both frame pictures (frontend/assets/frame_wide.webp,
frame_sq.webp) and the frame's straight top edge is drawn back where the plate covered it, copied from a column of
that edge just left of the plate. Originals kept as art/highpeaks/work/frame_<name>.with_plate.webp; re-runs start there.

    .venv/bin/python tools/highpeaks/frame_no_plate.py
"""
import os, shutil
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'frontend', 'assets')
W = os.path.join(ROOT, 'art', 'highpeaks', 'work')
for name in ('frame_wide', 'frame_sq'):
    out = os.path.join(A, name + '.webp')
    keep = os.path.join(W, name + '.with_plate.webp')
    if not os.path.exists(keep):
        shutil.copyfile(out, keep)
    a = np.asarray(Image.open(keep).convert('RGBA')).copy()
    al = a[..., 3] > 30
    H, Wd = al.shape
    top = int(np.argmax(al[:, int(Wd * .12)]))          # the border's top row, clear of the plate
    ys, xs = np.nonzero(al[:top])
    x0, x1 = xs.min() - 6, xs.max() + 6                   # the plate's span, a little margin
    depth = top + 120                                     # down through the border's whole top edge
    ref = a[:depth, x0 - 30:x0 - 29]                       # one column of the straight top edge, left of the plate
    a[:depth, x0:x1 + 1] = np.repeat(ref, x1 + 1 - x0, axis=1)
    Image.fromarray(a).save(out, 'WEBP', quality=90, method=6, alpha_quality=100)
    print(f'{name}: plate cleared over x {x0}-{x1}, edge redrawn to row {depth}')
