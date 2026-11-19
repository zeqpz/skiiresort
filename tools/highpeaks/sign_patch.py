"""The building's FALCOS lettering hidden while playing (owner, 2026-11-17: "remove the background of the sign covered by
the board but only on the playing screen"): for each scene a transparent picture the size of its plate, holding only
the plain fascia where the lettering is (an edit of the plate's building crop with the letters taken out:
art/highpeaks/raw/signpatch_<scene>.png). The stylesheet lays it over the scene as a second background layer, same size
and place, only while the game is being played (not on the loading screen or a bonus intro).

    .venv/bin/python tools/highpeaks/sign_patch.py   ->  frontend/assets/scene/signpatch_<scene>.webp (+ _m)
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'highpeaks'))
from compress_assets import encode, PLATE_W_M   # noqa: E402

A = os.path.join(ROOT, 'frontend', 'assets')
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
BOX = (640, 0, 2560, 1080)            # the building crop the edits were made from (2560-wide plate)
ZONE = (220, 70, 1020, 370)           # crop px: where the lettering (and PREMIUM's hanging S) is
PLATES = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp', 'midnight': 'scene/plate_midnight.webp',
          'nitro': 'scene/plate_nitro.webp'}

for name, rel in PLATES.items():
    plate = Image.open(os.path.join(A, rel)).convert('RGB')
    region = plate.crop(BOX)
    edit = Image.open(os.path.join(RAW, f'signpatch_{name}.png')).convert('RGB').resize(region.size, Image.LANCZOS)
    d = np.abs(np.asarray(edit, np.int16) - np.asarray(region, np.int16)).max(axis=2) > 40
    zone = np.zeros_like(d); zone[ZONE[1]:ZONE[3], ZONE[0]:ZONE[2]] = True
    m = ndimage.binary_dilation(ndimage.binary_opening(d & zone, iterations=1), iterations=14) & zone
    alpha = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
    layer = Image.new('RGBA', plate.size, (0, 0, 0, 0))
    piece = edit.convert('RGBA'); piece.putalpha(alpha)
    layer.paste(piece, BOX[:2])
    out = os.path.join(A, 'scene', f'signpatch_{name}.webp')
    encode(layer, out, 90, 90)
    small = layer.resize((PLATE_W_M, round(layer.height * PLATE_W_M / layer.width)), Image.LANCZOS)
    encode(small, out[:-5] + '_m.webp', 90, 90)
    print(name, os.path.getsize(out), 'bytes')
