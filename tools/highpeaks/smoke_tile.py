"""The ice bong's smoke, as smoke (owner, 2026-11-23: "make the smoke more realistic").

    python tools/highpeaks/smoke_tile.py        -> frontend/assets/fx/smoke.webp  (+ smoke_soft.webp)

The smoke in the tall bong (frontend/icebong.js tall()) was a flat white fill with round cartoon puffs. This makes what
it is drawn from now:

  smoke.webp        256 x 512, white with its density in the alpha: billows and curling wisps from layered noise
                    (broad billows, finer curls, thin ridged streaks pulled upward), TILEABLE top to bottom and side
                    to side, so two copies can scroll up the tube for ever at different speeds without a seam
  smoke_soft.webp   128 x 128, one soft puff (a noisy radial falloff) for the hit leaving the rim

Deterministic (seeded): the same pictures every run.
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'frontend', 'assets', 'fx')
W, H = 256, 512
rng = np.random.default_rng(420)


def noise(gw, gh):
    """Smooth periodic noise, 0-1: a gw x gh grid of random values, wrapped and resampled up to W x H."""
    g = rng.random((gh, gw)).astype(np.float32)
    t = np.tile(g, (3, 3))
    im = Image.fromarray((t * 255).astype(np.uint8)).resize((W * 3, H * 3), Image.BICUBIC)
    a = np.asarray(im).astype(np.float32) / 255
    return a[H:2 * H, W:2 * W]


def warp(a, dx, dy):
    """Pull a field about by two others (periodic): what gives smoke its curl."""
    yy, xx = np.mgrid[0:H, 0:W]
    return a[(yy + dy.astype(int)) % H, (xx + dx.astype(int)) % W]


def tile():
    big = noise(3, 4) * .55 + noise(5, 7) * .3 + noise(9, 14) * .15           # billows
    curl = noise(8, 10) * .6 + noise(16, 22) * .4                              # finer turns
    # ridged streaks, drawn out upward: thin bright filaments where a field crosses its middle
    r = noise(7, 5) * .6 + noise(14, 9) * .4
    ridge = 1 - np.abs(r - .5) * 2
    ridge = np.clip((ridge - .5) / .5, 0, 1) ** 1.8                              # soft filaments, not hard lines
    # curl the billows and the streaks by the same slow fields
    dx = (noise(4, 5) - .5) * 70
    dy = (noise(4, 5) - .5) * 90
    big = warp(big, dx, dy)
    ridge = warp(ridge, dx * .6, dy * .6)
    dens = np.clip((big - .36) / .42, 0, 1) ** 1.25                              # thick in places, clear in others
    dens = dens * (.55 + .45 * curl) + ridge * .2
    a = np.clip(dens, 0, 1) ** .9
    shade = .9 + .1 * warp(curl, dx, dy)                                         # a little body: not one flat white
    rgb = np.stack([shade * 247, shade * 250, shade * 255], -1)
    im = Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), 'RGBA')
    # a touch of blur, wrapped so the tile still joins itself: smoke has no hard edge anywhere
    from PIL import ImageFilter
    big3 = Image.new('RGBA', (W * 3, H * 3))
    for i in range(3):
        for j in range(3):
            big3.paste(im, (i * W, j * H))
    return big3.filter(ImageFilter.GaussianBlur(2.2)).crop((W, H, 2 * W, 2 * H))


def puff(n=128):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
    g = rng.random((9, 9)).astype(np.float32)
    nz = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)).astype(np.float32) / 255
    a = np.clip(1 - d * (1.02 + .32 * (nz - .5)), 0, 1) ** 1.6
    rgb = np.full((n, n, 3), 250, np.float32)
    return Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), 'RGBA')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    t = tile()
    t.save(os.path.join(OUT, 'smoke.webp'), 'WEBP', quality=86, method=6, alpha_quality=90)
    puff().save(os.path.join(OUT, 'smoke_soft.webp'), 'WEBP', quality=86, method=6, alpha_quality=90)
    a = np.asarray(t.getchannel('A')).astype(np.float32)
    seam_v = float(np.abs(a[0] - a[-1]).mean()), float(np.abs(a[0] - a[1]).mean())
    seam_h = float(np.abs(a[:, 0] - a[:, -1]).mean()), float(np.abs(a[:, 0] - a[:, 1]).mean())
    print('smoke.webp', t.size, os.path.getsize(os.path.join(OUT, 'smoke.webp')) // 1024, 'KB | alpha mean', round(float(a.mean()) / 255, 3),
          '| top-bottom seam step %.1f (a normal row step is %.1f) | side seam %.1f (normal %.1f)' % (*seam_v, *seam_h))
