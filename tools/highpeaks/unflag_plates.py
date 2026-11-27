"""High Peaks: take the painted flag off the three bonus plates (2026-11-27).

    python tools/highpeaks/unflag_plates.py

The bonus scenes' plates (frontend/assets/scene/plate_zombie|midnight|nitro[_m].webp) were painted with the old green
flag on the pole. The flag is one waving sprite over every scene now (frontend/layers.js: the Colorado-style one,
assets/scene/layers/spr_flag.webp), so the painted one has to go or it shows round the edges of the moving one. This
finds the green cloth beside the pole (in the box the flag stands in), and fills it from what is round it - sky and far
peaks - by diffusion. The pole stays. What is left is a soft patch of scenery that the waving flag covers.
Run once: a plate without green cloth there is left alone.
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCENE = os.path.join(ROOT, 'frontend', 'assets', 'scene')
BOX = (.893, .245, 1.0, .41)          # where the flag flies, as shares of the plate (x0, y0, x1, y1)


def unflag(path):
    im = Image.open(path).convert('RGB')
    W, H = im.size
    x0, y0, x1, y1 = round(BOX[0] * W), round(BOX[1] * H), round(BOX[2] * W), round(BOX[3] * H)
    a = np.asarray(im).astype(np.float32)
    box = a[y0:y1, x0:x1]
    r, g, b = box[..., 0], box[..., 1], box[..., 2]
    green = (g > b + 38) & (g > r * .93) & (g > 70)
    lab, n = ndimage.label(green)
    if not n:
        return None
    sizes = ndimage.sum(green, lab, range(1, n + 1))
    cloth = np.isin(lab, 1 + np.flatnonzero(sizes > .004 * green.size))
    if cloth.sum() < .03 * green.size:
        return None                                              # no flag painted here (already taken off)
    k = max(3, round(W / 320))                                   # the ink round the cloth, and a margin
    near = ndimage.binary_dilation(cloth, iterations=k)
    dark = box.max(-1) < 95
    mask = ndimage.binary_dilation(cloth | (near & dark), iterations=max(2, k // 2))
    mask = ndimage.binary_fill_holes(mask)
    left = np.flatnonzero(cloth.any(0))[0]
    mask[:, :max(0, left - 1)] = False                           # not the pole
    out = box.copy()
    out[mask] = box[~mask].mean(0)
    for _ in range(600):                                         # fill from the edges inward
        avg = (np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 4
        out[mask] = avg[mask]
    a[y0:y1, x0:x1] = out
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path, 'WEBP', quality=90, method=6)
    return int(mask.sum()), (x0, y0, x1, y1)


if __name__ == '__main__':
    for name in ('zombie', 'midnight', 'nitro'):
        for suf in ('', '_m'):
            p = os.path.join(SCENE, f'plate_{name}{suf}.webp')
            print(os.path.basename(p), unflag(p) or 'no painted flag found: left alone', os.path.getsize(p) // 1024, 'KB')
