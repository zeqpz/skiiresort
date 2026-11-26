"""The ice bong's flame, as fire (owner, 2026-11-23: "make the flame for the bowl more realistic").

    python tools/highpeaks/flame_sheet.py       -> frontend/assets/fx/flame.webp

The bowl's flame was three flat orange cartoon tongues with ink outlines. This is a real one: 12 frames of a flame,
128 x 192 each, side by side in one row (1536 x 192), that loop without a seam - frontend/icebong.js steps through
them (CSS steps(12)).

How: a teardrop of heat (hot and wide at the bowl, thinning to a point), eaten away from the top and the sides by two
layers of noise that scroll UP through it - the fine one twice as fast - and swayed by a slow third; the noise tiles
top to bottom and each frame moves it a twelfth of its height, so frame 13 is frame 1. Heat becomes colour on a fire
ramp (deep red at the edge, orange, yellow, a white-hot core) and the alpha thins toward the edge, so it has no outline.
Deterministic (seeded).
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'frontend', 'assets', 'fx', 'flame.webp')
N, FW, FH, SS = 12, 128, 192, 2
W, H = FW * SS, FH * SS
rng = np.random.default_rng(710)
RAMP = [(0.00, (120, 10, 0)), (0.18, (215, 40, 0)), (0.42, (255, 118, 8)), (0.66, (255, 200, 50)), (0.86, (255, 240, 170)), (1.0, (255, 255, 240))]


def noise(gw, gh):
    """Smooth noise 0-1 that tiles top to bottom and side to side, W x H."""
    g = rng.random((gh, gw)).astype(np.float32)
    im = Image.fromarray((np.tile(g, (3, 3)) * 255).astype(np.uint8)).resize((W * 3, H * 3), Image.BICUBIC)
    return np.asarray(im).astype(np.float32)[H:2 * H, W:2 * W] / 255


def frame(f, coarse, fine, sway):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    s1, s2 = int(round(f * H / N)), int(round(2 * f * H / N))
    up = lambda a, s: np.roll(a, -s, axis=0)                       # the noise travels up through the flame
    v = 1 - yy / H                                                 # 0 at the bowl, 1 at the tip
    lean = (up(sway, s1) - .5) * .55 * v ** 1.2                    # the whole flame leans, more toward its tip
    u = (xx - W / 2) / (W / 2) - lean
    # its foot is ROUND, not a flat cut (owner, 2026-11-24: "make the bottom of the flame rounded and not just cut
    # off"): over the lowest sixth the teardrop closes on a circle's arc to nothing, and the last rows fade out
    foot = np.clip(v / .17, 0, 1)
    width = np.maximum((.6 * (1 - v) ** .8 + .03) * np.sqrt(1 - (1 - foot) ** 2), 1e-3)
    core = np.clip(1 - (np.abs(u) / width) ** 2, 0, 1)
    heat = core ** .8 * (1 - v) ** .62 * 1.12
    eat = (up(coarse, s1) * .62 + up(fine, s2) * .38)
    heat = heat - eat * (.2 + 1.3 * v) - .08 * (1 - core)
    heat = np.clip(heat, 0, 1) * np.clip(v / .035, 0, 1)
    xs = np.array([r[0] for r in RAMP], np.float32)
    rgb = np.stack([np.interp(heat, xs, np.array([r[1][c] for r in RAMP], np.float32)) for c in range(3)], -1)
    alpha = np.clip(heat * 3.0, 0, 1) ** .9
    im = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), 'RGBA')
    return im.resize((FW, FH), Image.LANCZOS)


if __name__ == '__main__':
    coarse, fine, sway = noise(4, 5), noise(9, 12), noise(2, 3)
    sheet = Image.new('RGBA', (FW * N, FH))
    frames = [frame(f, coarse, fine, sway) for f in range(N)]
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * FW, 0))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT, 'WEBP', quality=88, method=6, alpha_quality=92)
    a = [np.asarray(fr).astype(np.float32) for fr in frames]
    step = float(np.mean([np.abs(a[i + 1] - a[i]).mean() for i in range(N - 1)]))
    seam = float(np.abs(a[0] - a[-1]).mean())
    print('flame.webp', sheet.size, os.path.getsize(OUT) // 1024, 'KB | frame-to-frame change %.2f, last-to-first %.2f (a clean loop: about equal)' % (step, seam))
