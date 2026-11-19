"""The flat base scene's finishing touches (owner, 2026-11-13), after `restyle.py plates lit`:

  window   the shop window seen as someone on the pavement really would: shelf fronts across the bottom, the floor
           hidden until the back of the store - on every plate (art/highpeaks/raw/flat_window_<n>.png, edits of its crop)
  pump     (base plate) a realistic free-standing pump left of the pillar (art/highpeaks/raw/flat_pump_lit.png)
  sign     the canopy's FALCOS neon switched off (art/highpeaks/raw/flat_signoff_lit.png, an edit of the canopy
           crop): written as art/highpeaks/scene/sign_off.png - only what the edit changed, feathered - for the
           big-win stutter, and cut into the two faulty letters by sign_letters.py

    .venv/bin/python tools/highpeaks/flat_scene.py        (then compress_assets.py)

Re-runnable: it starts from the restyled plates kept as art/highpeaks/scene/plate_<n>.flat.png on the first run.
"""
import os, shutil, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC = os.path.join(ROOT, 'art', 'highpeaks', 'scene')
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
A = os.path.join(ROOT, 'frontend', 'assets')
WINDOW_BOX, WINDOW_AREA = (2688, 576, 3840, 1440), (2850, 640, 3840, 1430)
SIGN_BOX = (0, 0, 1152, 768)
PUMP_BOX, PUMP_AREA_TOP = (300, 760, 1220, 2140), 860   # the pump's crop (art/highpeaks/work/pump/crop.png)
PLAQUE = (360, 1328, 426, 1382)                       # the house's "29": kept as it is


def changed(edit, region, thr=.08, grow=6, blur=5):
    d = np.abs(np.asarray(edit, np.float32) - np.asarray(region, np.float32)).max(axis=2) / 255 > thr
    m = ndimage.binary_closing(ndimage.binary_opening(d, iterations=1), iterations=4)
    m = ndimage.binary_dilation(m, iterations=grow)
    return Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))


OUT = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp', 'nitro': 'scene/plate_nitro.webp',
       'midnight': 'scene/plate_midnight.webp'}
for n, out in OUT.items():
    src, keep = os.path.join(SC, f'plate_{n}.png'), os.path.join(SC, f'plate_{n}.flat.png')
    if not os.path.exists(keep):
        shutil.copyfile(src, keep)
    pl = Image.open(keep).convert('RGB')
    # the window: what changed inside the window's area (each plate's own edit, in its own light)
    box = WINDOW_BOX
    region = pl.crop(box)
    edit = Image.open(os.path.join(RAW, f'flat_window_{n}.png')).convert('RGB').resize(region.size, Image.LANCZOS)
    m = np.asarray(changed(edit, region, .14, 10, 6)).copy()
    x0, y0, x1, y1 = (WINDOW_AREA[0] - box[0], WINDOW_AREA[1] - box[1], WINDOW_AREA[2] - box[0], WINDOW_AREA[3] - box[1])
    keep_out = np.ones_like(m, bool); keep_out[y0:y1, x0:x1] = False
    m[keep_out] = 0
    region.paste(edit, (0, 0), Image.fromarray(m))
    pl.paste(region, box[:2])
    if n == 'lit':
        # the pump: a realistic free-standing dispenser on its island, left of the canopy pillar and clear of it
        # (owner, 2026-11-13: "the gas pump looks unrealistic and is on the wrong side of the pillar and shouldnt be
        # connected to the pillar") - everything the edit changed, except the house's "29" plaque, which it lost
        pb = PUMP_BOX
        region = pl.crop(pb)
        edit = Image.open(os.path.join(RAW, 'flat_pump_lit_red.png')).convert('RGB').resize(region.size, Image.LANCZOS)
        m = np.asarray(changed(edit, region, .12, 8, 5)).copy()
        m[:PUMP_AREA_TOP - pb[1]] = 0
        px0, py0, px1, py1 = (PLAQUE[0] - pb[0], PLAQUE[1] - pb[1], PLAQUE[2] - pb[0], PLAQUE[3] - pb[1])
        m[max(0, py0):py1, max(0, px0):px1] = 0
        region.paste(edit, (0, 0), Image.fromarray(m))
        pl.paste(region, pb[:2])
        print('lit: free-standing pump blended')
    pl.save(src)
    pl.save(os.path.join(A, out), 'WEBP', quality=95, method=4)
    print(f'{n}: eye-level window blended')
    if n == 'lit':
        plate = pl

# the sign off: the edit where it differs from the lit plate, as an overlay
canopy = plate.crop(SIGN_BOX)
off = Image.open(os.path.join(RAW, 'flat_signoff_lit.png')).convert('RGB').resize(canopy.size, Image.LANCZOS)
ov = off.convert('RGBA')
ov.putalpha(changed(off, canopy, .1, 8, 6))
ov.save(os.path.join(SC, 'sign_off.png'))
ov.save(os.path.join(A, 'scene', 'sign_off.webp'), 'WEBP', quality=88, method=6, alpha_quality=95)
print('sign_off: written')
subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'highpeaks', 'sign_letters.py')], check=True)
# and the forecourt as plain concrete (plain_ground.py): every run of this rebuilds the plates, so it follows
for f in os.listdir(SC):
    if f.endswith('.reflect.png'):
        os.remove(os.path.join(SC, f))
subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'highpeaks', 'plain_ground.py')], check=True)
