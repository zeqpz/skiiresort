"""Every scene's gas pump in the same spot and at the same size (owner, 2026-11-17: "you see how all 3 gas stations are
in diffrent spots and diffrent sizes. i like how they are all diffrently themed but make them all in the exact same spot
and the exact same size", then "remove the red poles next to the pump" and "make the pump bigger").

The normal scene's pump area was edited first (art/highpeaks/raw/pumpalign_lit_big.png: the poles gone, the pump ~45%
bigger, standing where it stood), and each themed scene's pump area was restyled from THAT picture (layout kept, the
theme's look taken from the scene's own crop): pumpalign_<zombie|midnight|nitro>_big.png. This blends each edit into
its scene - everything the edit changed in the crop, feathered, fading out towards the crop's edges - and writes the
game's plates (2560 wide) and their phone twins (_m, 1600 wide) at compress_assets.py's settings.

    .venv/bin/python tools/highpeaks/pump_align.py

It works on the game's own plates (frontend/assets), which carry later touches the 3840 sources in art/highpeaks/scene do
not; the originals are kept beside the edits as art/highpeaks/work/pumpalign/before_<name>.webp, and a re-run starts from them.
"""
import os, shutil, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'highpeaks'))
from compress_assets import encode, PLATE_Q, PLATE_W_M   # noqa: E402

A = os.path.join(ROOT, 'frontend', 'assets')
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
W = os.path.join(ROOT, 'art', 'highpeaks', 'work', 'pumpalign')
BOX = (150, 450, 1000, 1300)   # the pump's area on a 2560-wide plate (the crop the edits were made from)
PLATES = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp', 'midnight': 'scene/plate_midnight.webp',
          'nitro': 'scene/plate_nitro.webp'}


# only the pump's own zone is taken from the edit, so the house, the shop window and the door stay the scene's own
# (taking the whole crop doubled their edges): a tall narrow band round the pump, the pillar and where the old pump
# stood, widening only at ground level for the island, on the plain forecourt (crop px, left/top/right/bottom)
UPPER = (132, 96, 548, 650)
ISLAND = (92, 628, 618, 778)
FEATHER = 10


RIGHT = (548, 96, 700, 778)   # right of the pillar, where the old pumps and their poles stood: taken only where it differs


def mask_of(edit, region):
    w, h = region.size
    m = Image.new('L', (w, h), 0)
    for x0, y0, x1, y1 in (UPPER, ISLAND):
        m.paste(255, (x0 + FEATHER, y0 + FEATHER, x1 - FEATHER, y1 - FEATHER))
    d = np.abs(np.asarray(edit, np.float32) - np.asarray(region, np.float32)).max(axis=2) / 255 > .16
    d = ndimage.binary_dilation(ndimage.binary_opening(d, iterations=2), iterations=10)
    band = np.zeros_like(d)
    band[RIGHT[1]:RIGHT[3], RIGHT[0] - FEATHER:RIGHT[2]] = True
    r = Image.fromarray(((d & band) * 255).astype(np.uint8))
    m = Image.fromarray(np.maximum(np.asarray(m), np.asarray(r)))
    return m.filter(ImageFilter.GaussianBlur(FEATHER / 2))


for name, rel in PLATES.items():
    out = os.path.join(A, rel)
    before = os.path.join(W, f'before_{name}.webp')
    if not os.path.exists(before):
        shutil.copyfile(out, before)
    plate = Image.open(before).convert('RGB')
    assert plate.width == 2560, (rel, plate.size)
    region = plate.crop(BOX)
    src = 'pumpalign_lit_big.png' if name == 'lit' else f'pumpalign_{name}_big.png'
    edit = Image.open(os.path.join(RAW, src)).convert('RGB').resize(region.size, Image.LANCZOS)
    m = mask_of(edit, region)
    region.paste(edit, (0, 0), m)
    plate.paste(region, BOX[:2])
    encode(plate, out, PLATE_Q, 100)
    small = plate.resize((PLATE_W_M, round(plate.height * PLATE_W_M / plate.width)), Image.LANCZOS)
    encode(small, out[:-5] + '_m.webp', PLATE_Q, 100)
    m.save(os.path.join(W, f'mask_{name}.png'))
    print(f'{name}: pump blended -> {rel} (+ _m)')
