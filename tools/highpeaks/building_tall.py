"""The store building taller, its FALCOS sign higher and centred on the screen, the wood stack right of the crate gone
(owner, 2026-11-17: "can you make the building taller so the sign is more twords the top", "remove the pile of wood
on the right side of the trash can", "make the big falcos on the building be centered to the screen").

The normal scene's building crop was edited in steps (art/highpeaks/raw/building_lit_tall -> _nowood -> _center.png), and
each themed scene's was restyled from the result with the theme's own crop as the look (building_<zombie|midnight|
nitro>.png), as tools/highpeaks/pump_align.py did for the pump. This blends into every plate only:
  * the top band - the raised blue fascia with the lettering and the taller wall under it, from where the building
    starts (right of the canopy roof) to the right edge, down to just under the ceiling lights;
  * the spot the wood stack stood on.
So each theme keeps its own doors, windows and shop. Writes the plates (2560) and their phone twins (_m, 1600).

    .venv/bin/python tools/highpeaks/building_tall.py      (after tools/highpeaks/pump_align.py; it starts from the plates
                                                          pump_align.py wrote, kept as art/highpeaks/work/building/before_*)
"""
import os, shutil, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'highpeaks'))
from compress_assets import encode, PLATE_Q, PLATE_W_M   # noqa: E402

A = os.path.join(ROOT, 'frontend', 'assets')
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
W = os.path.join(ROOT, 'art', 'highpeaks', 'work', 'building')
BOX = (640, 0, 2560, 1080)            # the building's crop on a 2560-wide plate
BAND = (100, 0, 1920, 505)            # crop px: from the building's left end (the canopy roof ends there) to the right edge
WOOD = (900, 830, 1225, 1080)         # crop px: where the wood stack stood
PLATES = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp', 'midnight': 'scene/plate_midnight.webp',
          'nitro': 'scene/plate_nitro.webp'}
EDITS = {'lit': 'building_lit_center.png', 'zombie': 'building_zombie.png', 'midnight': 'building_midnight.png',
         'nitro': 'building_nitro.png'}


def mask(size):
    w, h = size
    band = Image.new('L', size, 0)
    band.paste(255, (BAND[0], BAND[1], BAND[2], BAND[3] - 18))
    band = band.filter(ImageFilter.GaussianBlur(1.5))   # a crisp corner at the building's left end
    a = np.asarray(band, np.float32)
    # the band's foot fades over the wall, just under the ceiling lights
    ys = np.arange(h, dtype=np.float32)[:, None]
    foot = np.clip((BAND[3] - ys) / 36, 0, 1)
    a = np.where(ys > BAND[3] - 36, np.minimum(a, foot * 255), a)
    wood = Image.new('L', size, 0)
    wood.paste(255, (WOOD[0] + 14, WOOD[1] + 14, WOOD[2] - 14, WOOD[3]))
    wood = np.asarray(wood.filter(ImageFilter.GaussianBlur(7)), np.float32)
    return Image.fromarray(np.maximum(a, wood).astype(np.uint8))


for name, rel in PLATES.items():
    out = os.path.join(A, rel)
    before = os.path.join(W, f'before_{name}.webp')
    if not os.path.exists(before):
        shutil.copyfile(out, before)
    plate = Image.open(before).convert('RGB')
    region = plate.crop(BOX)
    edit = Image.open(os.path.join(RAW, EDITS[name])).convert('RGB').resize(region.size, Image.LANCZOS)
    m = mask(region.size)
    region.paste(edit, (0, 0), m)
    plate.paste(region, BOX[:2])
    encode(plate, out, PLATE_Q, 100)
    small = plate.resize((PLATE_W_M, round(plate.height * PLATE_W_M / plate.width)), Image.LANCZOS)
    encode(small, out[:-5] + '_m.webp', PLATE_Q, 100)
    print(f'{name}: building blended -> {rel} (+ _m)')
