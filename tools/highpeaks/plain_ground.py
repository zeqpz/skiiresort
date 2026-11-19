"""The forecourt as plain concrete (owner, 2026-11-13: "remove all the colors on the concrete"): the wet ground's
coloured reflection streaks taken out of all four plates. Each plate's ground band (y 1400-2160) was edited in three
1280-wide tiles (art/highpeaks/work/ground/<plate>_<t>.png -> art/highpeaks/raw/ground_<plate>_<t>.png); only what an
edit changed is blended back, below the forecourt's top, with a soft edge. Run after flat_scene.py (it rewrites the
plates from plate_<n>.flat.png), then compress_assets.py.

    .venv/bin/python tools/highpeaks/plain_ground.py
"""
import os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC = os.path.join(ROOT, 'art', 'highpeaks', 'scene')
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
A = os.path.join(ROOT, 'frontend', 'assets')
OUT = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp', 'nitro': 'scene/plate_nitro.webp', 'midnight': 'scene/plate_midnight.webp'}
TOP = 1500            # above the forecourt's top only where an edit changed something (the far kerb's streaks)
for n, out in OUT.items():
    src = os.path.join(SC, f'plate_{n}.png')
    keep = os.path.join(SC, f'plate_{n}.reflect.png')      # the plate with its reflections, kept once: re-runnable
    if not os.path.exists(keep):
        Image.open(src).save(keep)
    pl = Image.open(keep).convert('RGB')
    a = np.asarray(pl).astype(np.float32)
    H, W = a.shape[:2]
    def mode(px):                                          # the most common colour (quantised to 8 levels)
        q = (px // 8).astype(np.int32)
        key = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
        k = np.bincount(key).argmax()
        return px[key == k].mean(axis=0)
    band = a[1750:2160].reshape(-1, 3)
    base = mode(band)                                      # the concrete's own colour in this plate
    mask = np.zeros((H, W), bool)
    ink = np.zeros((H, W), bool)
    for t in range(3):
        x0 = t * 1280
        region = a[1400:2160, x0:x0 + 1280]
        edit = np.asarray(Image.open(os.path.join(RAW, f'ground_{n}_{t}.png')).convert('RGB').resize((1280, 760), Image.LANCZOS)).astype(np.float32)
        eground = mode(edit[350:].reshape(-1, 3))           # what this edit painted the ground
        to_ground = np.abs(edit - eground).max(axis=2) < 34 # the edit made it plain ground...
        was_off = np.abs(region - base).max(axis=2) > 30    # ...where the plate had something else (a streak)
        d = to_ground & was_off
        d = ndimage.binary_opening(d, iterations=1)
        d[:TOP - 1400] = False
        mask[1400:2160, x0:x0 + 1280] = d
        ink[1400:2160, x0:x0 + 1280] = edit.max(axis=2) < 45
    mask = ndimage.binary_closing(mask, iterations=2) & ~ink
    mask = ndimage.binary_dilation(mask, iterations=1) & (np.abs(a - base).max(axis=2) > 12)
    mask[:TOP] = False
    # the streaks' thin edges the edit drew as lines: pixels next to a removed streak, in one of the streaks' own
    # colours (their palette: the colours of what was removed), not dark ink
    removed = a[mask]
    if len(removed) > 100:
        q = (removed // 24).astype(np.int32)
        keys, counts = np.unique(q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2], return_counts=True)
        pal = keys[counts > counts.sum() * .001]
        hull = ndimage.binary_dilation(mask, iterations=16)
        hull[:TOP] = False
        qa = (a // 24).astype(np.int32)
        ka = qa[..., 0] * 4096 + qa[..., 1] * 64 + qa[..., 2]
        streaky = np.isin(ka, pal) & (a.max(axis=2) > 70) & (np.abs(a - base).max(axis=2) > 30)
        mask |= ndimage.binary_dilation(hull & streaky, iterations=1) & hull & (a.max(axis=2) > 60)
    fill = np.empty_like(a); fill[:] = base
    soft = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)[..., None] / 255
    a = a * (1 - soft) + fill * soft
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    im.save(src)
    im.save(os.path.join(A, out), 'WEBP', quality=95, method=4)
    print(n, 'reflections replaced:', int(mask.sum()), 'px with', base.astype(int))
