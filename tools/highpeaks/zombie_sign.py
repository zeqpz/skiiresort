"""PREMIUM's canopy sign in the base game's colours, flickering like it (owner, 2026-11-16: "make this the color it is
during the normal spins. and just make it flicker like the normal one").

The zombie plate's FALCOS neon was lime green (FAL) and red (COS, the underline). Each tube is a region of the plate
bounded by the art's ink; every tube region of the sign is found (not ink, holding a white-hot core, green or red),
and repainted with the lit plate's own tube colours, picked by how deep each pixel sits across its tube (edge to centre line) (the lit
plate's tubes measured the same way: a cream-white body with a thin orange rim). The anti-aliased ring between the
tube and its ink is blended from ink to the rim colour by its brightness, so no green or red fringe is left.

The flicker is the base game's: the L and the S are the failing letters. Their off state (the tube unlit, measured
from the lit plate's sign_off overlay the same way) is cut as two pieces, zsign_off_l / zsign_off_s, which
index.html's Scene runs through SceneFX's fault episodes while PREMIUM plays.

    .venv/bin/python tools/highpeaks/zombie_sign.py       (then the plate's webps are written here too)

Re-runnable: it starts from art/highpeaks/scene/plate_zombie.greensign.png, kept on the first run.
"""
import json, os, shutil
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC = os.path.join(ROOT, 'art', 'highpeaks', 'scene')
A = os.path.join(ROOT, 'frontend', 'assets')
BOX = (0, 0, 1152, 768)
INK_V = .22
FAULTY = {'l': (522, 331), 's': (860, 413)}   # the lit plate's letter centres (sign_letters.py); the zombie's sit near


def hsv(a):
    v = a.max(2); mn = a.min(2); s = np.where(v > 0, (v - mn) / np.maximum(v, 1e-6), 0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]; d = np.maximum(v - mn, 1e-6)
    h = np.where(v == r, ((g - b) / d) % 6, np.where(v == g, (b - r) / d + 2, (r - g) / d + 4)) / 6
    return h, s, v


def tubes(a, want):
    """The sign's tube regions: not ink, a white-hot core, and (want) the tube's colour."""
    h, s, v = hsv(a)
    ink = v < INK_V
    lab, n = ndimage.label(~ink)
    idx = np.arange(1, n + 1)
    size = ndimage.sum(np.ones_like(ink), lab, idx)
    core = (v > .9) & (s < .3)
    hc = ndimage.sum(core, lab, idx)
    coloured = want(h, s, v) & ~core
    col = ndimage.sum(coloured, lab, idx)
    keep = [i for i, sz, c, k in zip(idx, size, hc, col) if 300 < sz < 60000 and c > .1 * sz and k > .15 * sz]
    return np.isin(lab, keep), lab


BINS = 24


def depth(mask, lab=None):
    """Each pixel's depth into its tube, 0 at the edge and 1 on the tube's centre line: its distance from the edge
    over the deepest distance in its own region (so a thin tube and a thick one are painted alike)."""
    d = ndimage.distance_transform_edt(mask)
    if lab is None:
        lab, _ = ndimage.label(mask)
    ids = np.arange(1, lab.max() + 1)
    deep = np.zeros(lab.max() + 1)
    deep[1:] = ndimage.maximum(d, lab, ids)
    rel = np.where(mask, d / np.maximum(deep[lab], 1), 0)
    return np.minimum((rel * BINS).astype(int), BINS - 1)


def profile(a, mask):
    """The mean colour of the mask's pixels by their depth into the tube."""
    b = depth(mask)
    prof = np.zeros((BINS, 3))
    for k in range(BINS):
        m = mask & (b == k)
        prof[k] = a[m].mean(0) if m.any() else prof[k - 1]
    return prof


def paint(a, mask, prof):
    out = a.copy()
    b = depth(mask)
    out[mask] = prof[b[mask]]
    # the ring between tube and ink: from the ink to the rim colour by brightness
    ring = ndimage.binary_dilation(mask, iterations=3) & ~mask
    v = a.max(2)
    edge_v = max(.3, prof[0].max())
    t = np.clip((v - .05) / (edge_v - .05), 0, 1)[ring][:, None]
    out[ring] = a[ring].min(1, keepdims=True) * (1 - t) + prof[0] * t
    return out, ring


def main():
    src, keep = os.path.join(SC, 'plate_zombie.png'), os.path.join(SC, 'plate_zombie.greensign.png')
    if not os.path.exists(keep):
        shutil.copyfile(src, keep)
    plate = Image.open(keep).convert('RGB')
    lit = np.asarray(Image.open(os.path.join(SC, 'plate_lit.png')).convert('RGB').crop(BOX)).astype(np.float32) / 255
    off = np.asarray(Image.open(os.path.join(SC, 'sign_off.png')).convert('RGBA')).astype(np.float32) / 255
    z = np.asarray(plate.crop(BOX)).astype(np.float32) / 255

    lit_m, _ = tubes(lit, lambda h, s, v: (s > .3) & ((h < .12) | (h > .95)) & (v > .5))   # cream tubes, orange rims
    p_lit = profile(lit, lit_m)
    off_rgb = off[..., :3] * off[..., 3:] + lit * (1 - off[..., 3:])                      # the sign switched off
    p_off = profile(off_rgb, lit_m)

    green_or_red = lambda h, s, v: (s > .45) & (v > .4) & (((h > .18) & (h < .42)) | (h < .04) | (h > .95))
    z_m, lab = tubes(z, green_or_red)
    new, ring = paint(z, z_m, p_lit)
    plate.paste(Image.fromarray((np.clip(new, 0, 1) * 255).astype(np.uint8)), BOX[:2])
    plate.save(src)
    print('tube px repainted:', int(z_m.sum()))

    # the failing letters' off pieces: the letter's tube regions nearest its centre, painted unlit
    cfg_p = os.path.join(A, 'scene', 'scene.json')
    cfg = json.load(open(cfg_p))
    cfg['zombie_layers'] = {}
    comp = np.unique(lab[z_m])
    cy, cx = np.array(ndimage.center_of_mass(z_m, lab, comp)).T
    offimg, _ = paint(z, z_m, p_off)
    for k, (x, y) in FAULTY.items():
        d = np.hypot(cx - x, cy - y)
        near = comp[d < 70] if (d < 70).any() else comp[[int(np.argmin(d))]]
        m = np.isin(lab, near)
        m = ndimage.binary_dilation(m, iterations=3)
        alpha = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
        piece = Image.fromarray((np.clip(offimg, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
        piece.putalpha(alpha)
        bb = alpha.point(lambda q: 255 if q > 4 else 0).getbbox()
        piece.crop(bb).save(os.path.join(A, 'scene', f'zsign_off_{k}.webp'), 'WEBP', quality=88, method=6, alpha_quality=95)
        cfg['zombie_layers'][f'zsign_off_{k}'] = {'rect': [bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]]}
        print(f'zsign_off_{k}:', bb, 'regions', len(near))
    json.dump(cfg, open(cfg_p, 'w'), indent=1)

    # the plate's webps, as compress_assets writes them (2560 wide; the phone twin 1600)
    for out, w in (('plate_zombie.webp', 2560), ('plate_zombie_m.webp', 1600)):
        im = plate.resize((w, round(w * plate.height / plate.width)), Image.LANCZOS)
        im.save(os.path.join(A, 'scene', out), 'WEBP', quality=82, method=6)
    print('plate_zombie webps written')


if __name__ == '__main__':
    main()
