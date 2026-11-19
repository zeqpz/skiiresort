"""The canopy's FALCOS neon made smaller, so the whole word sits left of the board while playing (owner, 2026-11-17:
"make the full falcos neon sign fit between the board" -> "Shrink the sign"), on every plate - and its flicker rebuilt
for the new letters.

  * art/highpeaks/raw/neon_lit_small.png: the normal plate's canopy crop with the neon at ~70%, its left end in place,
    ending left of the pillar; neon_<zombie|midnight|nitro>_small.png restyled from it with each scene's own look
    (PREMIUM keeps the base game's cream/orange tubes, as zombie_sign.py made it); *_small_off.png: the lit and
    PREMIUM signs switched off.
  * Each plate takes the edit where it changed in the canopy zone (the old big letters gone, the new small ones in).
  * The neon-off overlays are cut again from the switched-off edits: sign_off (the whole sign, for the big-win
    stutter), sign_off_l / sign_off_s (the two faulty letters, scenefx.js) and PREMIUM's zsign_off_l / zsign_off_s
    (index.html's Scene); their rects go into scene.json (plate px, 3840 wide).

    .venv/bin/python tools/highpeaks/neon_small.py
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'highpeaks'))
from compress_assets import encode, PLATE_Q, PLATE_W_M   # noqa: E402

A = os.path.join(ROOT, 'frontend', 'assets')
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
W = os.path.join(ROOT, 'art', 'highpeaks', 'work', 'neon')
CROP = 1000                     # the edits are of the plate's top-left 1000 x 1000 (2560-wide plate)
ZONE = (0, 20, 720, 470)        # crop px: the canopy's front, where the neon was and is
K = 1.5                         # 2560 -> 3840 plate px (scene.json)
PLATES = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp', 'midnight': 'scene/plate_midnight.webp',
          'nitro': 'scene/plate_nitro.webp'}


def load(name):
    return Image.open(os.path.join(RAW, name)).convert('RGB').resize((CROP, CROP), Image.LANCZOS)


def zone_mask(shape):
    z = np.zeros(shape, bool)
    z[ZONE[1]:ZONE[3], ZONE[0]:ZONE[2]] = True
    return z


# 1. the plates
edits = {}
for name, rel in PLATES.items():
    p = os.path.join(A, rel)
    keep = os.path.join(W, f'before_{name}.webp')
    if not os.path.exists(keep):
        Image.open(p).save(keep, 'WEBP', lossless=True)
    plate = Image.open(keep).convert('RGB')
    region = plate.crop((0, 0, CROP, CROP))
    edit = load(f'neon_{name}_small.png')
    d = np.abs(np.asarray(edit, np.int16) - np.asarray(region, np.int16)).max(axis=2) > 36
    m = ndimage.binary_dilation(ndimage.binary_opening(d, iterations=1), iterations=16) & zone_mask(d.shape)
    alpha = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    region.paste(edit, (0, 0), alpha)
    plate.paste(region, (0, 0))
    encode(plate, p, PLATE_Q, 100)
    encode(plate.resize((PLATE_W_M, round(plate.height * PLATE_W_M / plate.width)), Image.LANCZOS), p[:-5] + '_m.webp', PLATE_Q, 100)
    edits[name] = np.asarray(region)
    print(f'{name}: neon blended')


# 2. the neon-off overlays
def overlay(lit, off):
    """the off edit where it differs from the lit plate (the tubes and their glow), as RGBA, crop px"""
    d = np.abs(np.asarray(off, np.int16) - lit.astype(np.int16)).max(axis=2) > 22
    d &= zone_mask(d.shape)
    d = ndimage.binary_dilation(ndimage.binary_opening(d, iterations=1), iterations=3)
    a = np.asarray(Image.fromarray((d * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)))
    rgba = np.dstack([np.asarray(off), a]).astype(np.uint8)
    return rgba


def letters(lit, off):
    """the neon's letters left to right: each a mask of its white-hot tube core (the underline swoosh left out) -
    bright on the lit sign AND changed when it is switched off, so the stars and the canopy's lights are not taken"""
    changed = np.abs(np.asarray(off, np.int16) - lit.astype(np.int16)).max(axis=2) > 40
    core = (lit.min(axis=2) > 200) & changed & zone_mask(lit.shape[:2])
    core = ndimage.binary_opening(core, iterations=1)
    lab, n = ndimage.label(ndimage.binary_dilation(core, iterations=2))
    parts = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        size = (lab[sl] == i + 1).sum()
        if size < 60 or w > 2.0 * h:   # specks, the long low swoosh and the canopy's stripe
            continue
        parts.append((sl[1].start, lab == i + 1))
    parts.sort(key=lambda t: t[0])
    return [m for _, m in parts]


def cut(rgba, mine, others, grow=22, keep_off=8):
    """one letter's piece of the off overlay: its tube grown by the glow's reach, clear of the other letters"""
    reach = ndimage.binary_dilation(mine, iterations=grow)
    if others is not None:
        reach &= ~ndimage.binary_dilation(others, iterations=keep_off)
    a = rgba[..., 3].astype(np.float32) * np.asarray(Image.fromarray((reach * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    ys, xs = np.nonzero(a > 2)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    piece = np.dstack([rgba[y0:y1, x0:x1, :3], a[y0:y1, x0:x1].astype(np.uint8)])
    return Image.fromarray(piece), (x0, y0, x1, y1)


def to3840(img, box):
    x0, y0, x1, y1 = box
    rect = [round(x0 * K), round(y0 * K), round((x1 - x0) * K), round((y1 - y0) * K)]
    return img.resize((rect[2], rect[3]), Image.LANCZOS), rect


scene_p = os.path.join(A, 'scene', 'scene.json')
scene = json.load(open(scene_p))
for name, prefix, key in (('lit', 'sign_off', 'layers'), ('zombie', 'zsign_off', 'zombie_layers')):
    lit = edits[name]
    off = load(f'neon_{name}_small_off.png')
    rgba = overlay(lit, off)
    ls = letters(lit, off)
    print(f'{name}: {len(ls)} letters found')
    assert len(ls) == 6, 'expected the six letters of FALCOS'
    allm = np.logical_or.reduce(ls)
    out = {}
    if name == 'lit':   # the whole sign off, for the big-win stutter: the canopy's top-left 768 x 512 (1152 x 768 at 3840)
        whole = Image.fromarray(rgba[:512, :768])
        img, rect = to3840(whole, (0, 0, 768, 512))
        img.save(os.path.join(A, 'scene', 'sign_off.webp'), 'WEBP', quality=88, method=6, alpha_quality=95)
        out['sign_off'] = {'rect': rect}
    for idx, tag in ((2, 'l'), (5, 's')):   # F A L C O S: the L and the S fail
        others = allm & ~ls[idx]
        piece, box = cut(rgba, ls[idx], others)
        img, rect = to3840(piece, box)
        img.save(os.path.join(A, 'scene', f'{prefix}_{tag}.webp'), 'WEBP', quality=88, method=6, alpha_quality=95)
        out[f'{prefix}_{tag}'] = {'rect': rect}
    scene[key] = out
    print(name, out)
json.dump(scene, open(scene_p, 'w'), indent=1)
