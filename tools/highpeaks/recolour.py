"""White, orange and blue (owner, 2026-11-12: "make the designs white orange and blue. dont mess with the symbols").

    .venv/bin/python tools/highpeaks/recolour.py            (then compress_assets.py)

Hue only: every pixel keeps its saturation and brightness, so highlights, glows, chrome and shading stay as drawn.

  UI art (the win lettering and its backdrops, the banner, BUY BONUS, the title logo, the win numerals, the loading
  bar and cards' frames): red -> blue, gold/yellow -> orange, cream -> near white. The originals are kept once in
  art/highpeaks/ui_red/ and every run starts from them, so it can re-run.
  The bonus menu art and logos (each mode's own colours) and the symbols are not touched.

The scene's red (the canopy and its FALCOS neon, the pump) is recoloured by clear_scene.py (recolour_lit), and the
canopy's neon-off overlay (scene/sign_off) here with the same rule, so the two stay one picture.
"""
import sys as _sys
if __name__ == "__main__" and "--force" not in _sys.argv:   # SUPERSEDED 2026-11-13 by restyle.py / flat_scene.py (flat TV-cartoon style): it rewrites the glossy UI and the painted sign_off
    _sys.exit("superseded by tools/highpeaks/restyle.py and flat_scene.py - re-running would bring the old look back (--force to run anyway)")

import os, shutil
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'frontend', 'assets')
KEEP = os.path.join(ROOT, 'art', 'highpeaks', 'ui_red')
UI = ['banner_box', 'big_win', 'mega_win', 'xtreme_win', 'total_win', 'tier_bg', 'total_bg', 'bonus_btn_bg',
      'bonus_btn_text', 'title_logo'] + [f'num/{n}' for n in list('0123456789') + ['comma', 'dot', 'x']] + \
     ['load/bar_fill', 'load/bar_frame', 'load/card_frame', 'load/title_bonus', 'load/title_features', 'load/title_max']
BLUE, ORANGE, CANOPY_ORANGE = 218., 30., 24.


def hsv(a):
    rgb = a[..., :3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, np.where(mx > 0, d / (mx + 1e-6), 0), mx


def rgb(h, s, v):
    c = v * s
    x = c * (1 - np.abs((h / 60) % 2 - 1))
    m = v - c
    z = 0 * c
    k = (h // 60).astype(int) % 6
    out = np.zeros(h.shape + (3,))
    for i, (p, q, t) in enumerate([(c, x, z), (x, c, z), (z, c, x), (z, x, c), (x, z, c), (c, z, x)]):
        sel = k == i
        for ch, val in enumerate((p, q, t)):
            out[..., ch] = np.where(sel, val + m, out[..., ch])
    return out


def red_mask(h, s, smin=.25):
    return ((h >= 330) | (h < 18)) & (s > smin)


def recolour_ui(im):
    a = np.asarray(im.convert('RGBA')).astype(np.float32) / 255
    h, s, v = hsv(a)
    red, gold = red_mask(h, s), (h >= 30) & (h < 70) & (s > .45)
    cream = (h >= 18) & (h < 70) & (s <= .45) & (v > .55)
    h = np.where(red, BLUE, np.where(gold, ORANGE, h))
    s = np.where(cream, s * .35, s)
    a[..., :3] = rgb(h, s, v)
    return Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))


def recolour_canopy(a, box=None):
    """The canopy (fascia and FALCOS neon): red -> orange, in place on a float RGB(A) array; box limits it."""
    sub = a if box is None else a[box[1]:box[3], box[0]:box[2]]
    h, s, v = hsv(sub)
    m = red_mask(h, s, .2)
    sub[..., :3] = np.where(m[..., None], rgb(np.where(m, CANOPY_ORANGE, h), s, v), sub[..., :3])


def recolour_pump(a, box):
    """The pump, its pillar's stripes and the bollards: red -> blue, in place."""
    sub = a[box[1]:box[3], box[0]:box[2]]
    h, s, v = hsv(sub)
    m = red_mask(h, s, .3)
    sub[..., :3] = np.where(m[..., None], rgb(np.where(m, BLUE, h), s, v), sub[..., :3])


if __name__ == '__main__':
    for n in UI:
        p = os.path.join(A, n + '.webp')
        k = os.path.join(KEEP, n + '.webp')
        if not os.path.exists(p):
            print('missing', n); continue
        if not os.path.exists(k):
            os.makedirs(os.path.dirname(k), exist_ok=True)
            shutil.copyfile(p, k)
        recolour_ui(Image.open(k)).save(p, 'WEBP', quality=92, method=6, alpha_quality=95)
    print('ui:', len(UI), 'pictures white / orange / blue')
    # the canopy's neon-off overlay, the same rule as the plate's canopy (clear_scene.py recolour_lit)
    so = os.path.join(ROOT, 'art', 'highpeaks', 'scene', 'sign_off.png')
    k = os.path.join(KEEP, 'sign_off.png')
    if not os.path.exists(k):
        os.makedirs(KEEP, exist_ok=True); shutil.copyfile(so, k)
    a = np.asarray(Image.open(k).convert('RGBA')).astype(np.float32) / 255
    recolour_canopy(a)
    out = Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))
    out.save(so)
    out.save(os.path.join(A, 'scene', 'sign_off.webp'), 'WEBP', quality=88, method=6, alpha_quality=95)
    print('scene/sign_off: canopy orange')
