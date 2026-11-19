"""Two faulty letters in the canopy's FALCOS neon (owner, 2026-11-12: "make the falcos sign that flickers. only have a
couple letters flicker but make it seem like a realistic flicker").

    .venv/bin/python tools/highpeaks/sign_letters.py        (flat_scene.py runs it, after writing sign_off.png)

The neon-off overlay (art/highpeaks/scene/sign_off.png, laid over the plate's canopy) is cut into one piece per faulty
letter: the letter's white-hot tube cores are found on the lit plate (connected strokes), grown by the glow's reach,
kept clear of the other letters' tubes, and feathered - so switching a piece on darkens that letter and its glow
only. Writes frontend/assets/scene/sign_off_<l>.webp and their rects into scene.json; scenefx.js flickers them.
The whole overlay (sign_off) stays for the big-win stutter.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recolour import hsv  # noqa: E402

SC = os.path.join(ROOT, 'art', 'highpeaks', 'scene')
A = os.path.join(ROOT, 'frontend', 'assets', 'scene')
# the letters' tube cores, by where each stroke's centre lies (plate px); the faulty two are cut out
LETTERS = {'f': (281, 222), 'a': (418, 288), 'l': (522, 331), 'c': (640, 343), 'o': (755, 378), 's': (860, 413)}   # the flat plate (2026-11-13)
FAULTY = ('l', 's')
GLOW, KEEP_OFF = 38, 10          # px the glow reaches round a tube; px kept clear round the other letters' tubes

plate = np.asarray(Image.open(os.path.join(SC, 'plate_lit.png')).convert('RGB').crop((0, 0, 1152, 768))).astype(np.float32) / 255
off = Image.open(os.path.join(SC, 'sign_off.png')).convert('RGBA')
h, s, v = hsv(plate)
core = (v > .93) & (s < .35)
lab, _ = ndimage.label(core)
n = lab.max()
idx = np.arange(1, n + 1)
size = ndimage.sum(core, lab, idx)
cy, cx = np.array(ndimage.center_of_mass(core, lab, idx)).T
big = size > 800                 # the letters' strokes (the canopy's lights and the underline are elsewhere)
strokes = {}
for k, (x, y) in LETTERS.items():
    d = np.where(big, np.hypot(cx - x, cy - y), 1e9)
    strokes[k] = lab == idx[int(np.argmin(d))]
others_all = np.zeros_like(core)
for m in strokes.values():
    others_all |= m
cfg_p = os.path.join(A, 'scene.json')
cfg = json.load(open(cfg_p))
for k in FAULTY:
    mine = ndimage.binary_dilation(strokes[k], iterations=GLOW)
    others = ndimage.binary_dilation(others_all & ~strokes[k], iterations=KEEP_OFF)
    m = Image.fromarray(((mine & ~others) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    piece = off.copy()
    piece.putalpha(Image.fromarray((np.asarray(off.getchannel('A')).astype(np.float32) * np.asarray(m) / 255).astype(np.uint8)))
    bb = piece.getchannel('A').point(lambda a: 255 if a > 4 else 0).getbbox()
    piece.crop(bb).save(os.path.join(A, f'sign_off_{k}.webp'), 'WEBP', quality=88, method=6, alpha_quality=95)
    cfg['layers'][f'sign_off_{k}'] = {'rect': [bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]]}
    print(f'sign_off_{k}: {bb}')
json.dump(cfg, open(cfg_p, 'w'), indent=1)
