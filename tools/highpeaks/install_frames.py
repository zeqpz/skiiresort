"""Fit the generated log frames (art/highpeaks/raw/frame_{sq,wide}.png) to the board's two glass shapes and write
frontend/assets/frame_{sq,wide}.webp + .json (the opening as fractions of the picture: the page's --fo-*).

The inside of a generated frame is transparent but never exactly the glass's aspect: the picture is stretched on one
axis until its opening is (a few % at most), then trimmed to the frame's ink.
"""
import json, os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHAPES = {'sq': 1.283, 'wide': 1.4749}
OUT_W = {'sq': 1600, 'wide': 1978}


def opening(im):
    a = np.asarray(im.getchannel('A')) < 24
    lab, _ = ndimage.label(a)
    h, w = a.shape
    k = lab[h // 2, w // 2]
    ys, xs = np.nonzero(lab == k)
    # the opening's inner box: rows / columns that are clear across most of the span (log edges wobble)
    x0, x1 = np.percentile(xs, 1), np.percentile(xs, 99)
    y0, y1 = np.percentile(ys, 1), np.percentile(ys, 99)
    return x0, y0, x1, y1


for name, aspect in SHAPES.items():
    im = Image.open(os.path.join(ROOT, 'art', 'highpeaks', 'raw', f'frame_{name}.png')).convert('RGBA')
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox())
    x0, y0, x1, y1 = opening(im)
    a0 = (x1 - x0) / (y1 - y0)
    if a0 > aspect:
        im = im.resize((im.width, round(im.height * a0 / aspect)), Image.LANCZOS)
    else:
        im = im.resize((round(im.width * aspect / a0), im.height), Image.LANCZOS)
    k = OUT_W[name] / im.width
    im = im.resize((OUT_W[name], round(im.height * k)), Image.LANCZOS)
    x0, y0, x1, y1 = opening(im)
    W, H = im.size
    op = [round(x0 / W, 5), round(y0 / H, 5), round(x1 / W, 5), round(y1 / H, 5)]
    im.save(os.path.join(ROOT, 'frontend', 'assets', f'frame_{name}.webp'), 'WEBP', quality=90, method=6)
    json.dump({'frame_size': [W, H], 'opening': op, 'source': 'highpeaks log frame'},
              open(os.path.join(ROOT, 'frontend', 'assets', f'frame_{name}.json'), 'w'))
    print(name, (W, H), 'opening', op, 'aspect', round((x1 - x0) / (y1 - y0), 4),
          f'--fo-l: {op[0]:.5f}; --fo-t: {op[1]:.5f}; --fo-w: {op[2] - op[0]:.5f}; --fo-h: {op[3] - op[1]:.5f};')
