"""PREMIUM's drifting clouds (owner, 2026-11-10: "make the clouds move in the background of the abandon bonus").

    .venv/bin/python tools/highpeaks/make_clouds.py     -> frontend/assets/scene/clouds_zombie.webp

A seamless strip of night cloud, made from noise (no generated art): 1/f noise built in the frequency domain is
periodic by construction, so the strip tiles left to right without a seam and can slide forever. Pale green-grey
(the zombie sky's moonlit haze), its alpha from the noise - wisps, gaps and a few thicker banks - and fading out
toward the strip's foot so it melts into the plate above the rooftops. The page slides two copies of it across the
sky band on the compositor (.zclouds in index.html).
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST = os.path.join(ROOT, 'frontend', 'assets', 'scene', 'clouds_zombie.webp')
W, H = 2048, 384
rng = np.random.default_rng(1110)


def noise(beta, stretch):
    fx = np.fft.fftfreq(W)[None, :] * stretch, np.fft.fftfreq(H)[:, None]
    f = np.sqrt(fx[0] ** 2 + fx[1] ** 2); f[0, 0] = 1
    spec = (rng.normal(size=(H, W)) + 1j * rng.normal(size=(H, W))) / f ** beta
    spec[0, 0] = 0
    n = np.real(np.fft.ifft2(spec))
    return (n - n.mean()) / n.std()


n = .7 * noise(1.6, .45) + .3 * noise(1.1, .6)          # broad banks, stretched sideways, plus finer wisps
a = np.clip((n - .15) / 1.6, 0, 1) ** 1.3                 # gaps of clear sky between them
yy = np.linspace(0, 1, H)[:, None]
a *= np.clip(1 - (yy - .55) / .45, 0, 1) ** 1.5           # thinning out toward the foot
a *= .2 + .8 * np.clip(yy / .12, 0, 1)                    # and a little at the very top
lit = np.clip(.75 + .25 * noise(1.8, .5), 0, 1.2)[..., None]
rgb = np.array([170, 205, 160], np.float32)[None, None, :] * lit
img = np.dstack([np.clip(rgb, 0, 255), a[..., None] * 255]).astype(np.uint8)
Image.fromarray(img).save(DST, 'WEBP', quality=72, alpha_quality=70, method=6)
print(DST, os.path.getsize(DST) // 1024, 'KB')
