"""High Peaks peak pass (owner, 2026-11-19): install the new art from art/highpeaks/raw (art/highpeaks/jobs/peak_jobs.py).

    python tools/highpeaks/peak_install.py frames   peak_frame_{wide,sq} -> frontend/assets/frame_{wide,sq}.webp + .json
    python tools/highpeaks/peak_install.py plates   peak_plate[_powder|_night|_avalanche] -> bonus_wall / scene/plate_* (+ _m)
    python tools/highpeaks/peak_install.py win      peak_{big,mega,epic,total}_win, tier_bg, total_bg, banner_box, numerals

frames: the same log outline as before with a sign board on posts above the top log for the HIGH PEAKS logo. Each is
upscaled x4 (Real-ESRGAN anime, as gen_covers.py), trimmed to its ink, stretched until its glass opening has the board's
exact shape (1.283 upright, 1.4749 landscape), and its json gains "sign": the sign board's plain face as fractions of the
picture, where the page lays assets/logo.webp. Print the --fo-* / --sg-* to put in the stylesheet.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
A = os.path.join(ROOT, 'frontend', 'assets')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_covers import esrgan_x4

SHAPES = {'sq': 1.283, 'wide': 1.4749}
OUT_W = {'sq': 1600, 'wide': 1978}


def up4(im):
    """x4 with the alpha kept: the colour through Real-ESRGAN (on the frame's own colours bled into the clear parts, so
    no dark fringe comes in at the edge), the alpha resized and re-sharpened"""
    rgb = np.asarray(im.convert('RGB')).astype(np.float32)
    a = np.asarray(im.getchannel('A'))
    clear = a < 128
    if clear.any():   # bleed: every clear pixel takes the nearest solid pixel's colour
        idx = ndimage.distance_transform_edt(clear, return_distances=False, return_indices=True)
        rgb = rgb[idx[0], idx[1]]
    big = esrgan_x4(Image.fromarray(rgb.astype(np.uint8)))
    al = Image.fromarray(a).resize(big.size, Image.LANCZOS)
    al = al.point(lambda v: 0 if v < 40 else 255 if v > 215 else round((v - 40) * 255 / 175))
    big.putalpha(al)
    return big


def opening(im):
    a = np.asarray(im.getchannel('A')) < 24
    lab, _ = ndimage.label(a)
    h, w = a.shape
    k = lab[int(h * .66), w // 2]   # low in the picture: the sign sits over the top half
    ys, xs = np.nonzero(lab == k)
    x0, x1 = np.percentile(xs, 1), np.percentile(xs, 99)
    y0, y1 = np.percentile(ys, 1), np.percentile(ys, 99)
    return x0, y0, x1, y1


def woodmask(im):
    px = np.asarray(im.convert('RGBA')).astype(int)
    r, g, b, a = px[..., 0], px[..., 1], px[..., 2], px[..., 3]
    return (a > 200) & (r > 190) & (g > 130) & (g < 230) & (b < 160) & (r - b > 60)


def sign_face(im, y_open):
    """the sign board's plain light-wood face, above the top log: every tan plank up there, merged"""
    wood = woodmask(im)
    wood[int(y_open * .8):] = False
    wood = ndimage.binary_opening(wood, iterations=2)
    lab, n = ndimage.label(wood)
    if not n:
        raise SystemExit('no sign face found')
    idx = np.arange(1, n + 1)
    sizes = ndimage.sum(wood, lab, idx)
    cxs = np.array([c[1] for c in ndimage.center_of_mass(wood, lab, idx)])
    central = (cxs > im.width * .15) & (cxs < im.width * .85)          # not the log ends' tan rings
    ys, xs = np.nonzero(np.isin(lab, idx[central & (sizes > sizes[central].max() * .08)]))   # the planks, not specks
    return np.percentile(xs, 1), np.percentile(ys, 1), np.percentile(xs, 99), np.percentile(ys, 99)


def sink_sign(im, scale=.86, sink=.5):
    """The model stood the sign on two posts above the top log - a tall frame, so a smaller board. The sign is cut off
    its posts, shrunk a little and set DOWN onto the top log: its lower `sink` overlaps the log's snow (it reads as a
    sign board nailed to the front of the log), so the frame grows only by the sign's upper part."""
    a = np.asarray(im.getchannel('A')) > 24
    H, W = a.shape
    # the sign's planks: the tan wood in the picture's top part (the logs are a darker brown)
    # (above the top log - the first row the frame fills nearly edge to edge - and away from the log ends' tan rings)
    y_log = next(y for y in range(H) if a[y].mean() > .85)
    wood = ndimage.binary_opening(woodmask(im), iterations=2)
    wood[y_log:] = False
    lab, n = ndimage.label(wood)
    idx = np.arange(1, n + 1)
    sizes = ndimage.sum(wood, lab, idx)
    cxs = np.array([c[1] for c in ndimage.center_of_mass(wood, lab, idx)])
    central = (cxs > W * .15) & (cxs < W * .85)
    keep = idx[central & (sizes > sizes[central].max() * .08)]
    ys, xs = np.nonzero(np.isin(lab, keep))
    pad = round(W * .035)   # the sign's snow cap overhangs its planks
    cx0, cx1 = max(0, int(xs.min()) - pad), min(W, int(xs.max()) + pad)
    board_bot = int(ys.max()) + round(W * .012)                  # the sign board's own bottom edge (its outline)
    # under it, only the two posts, then the top log's snow: the first row the snow fills across the sign's width
    frac = a[:, int(xs.min()):int(xs.max())].mean(axis=1)
    y_snow = next(y for y in range(board_bot, H) if frac[y] > .6)
    board_bot = min(board_bot, y_snow)
    sign = im.crop((cx0, 0, cx1, board_bot))
    sign = sign.crop(sign.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox())
    base = im.copy()
    arr = np.asarray(base).copy()
    arr[:y_snow - 2, cx0:cx1, 3] = 0                             # the sign and its posts gone from the frame
    base = Image.fromarray(arr)
    sign = sign.resize((round(sign.width * scale), round(sign.height * scale)), Image.LANCZOS)
    sign_top = y_snow + round(sign.height * sink) - sign.height  # its bottom part over the log's snow
    lift = max(0, -sign_top)                                     # room the canvas needs above (the leaf and cone keep theirs)
    out = Image.new('RGBA', (W, H + lift))
    out.alpha_composite(base, (0, lift))
    out.alpha_composite(sign, ((W - sign.width) // 2, sign_top + lift))
    # loose bits of the old sign's outline left past the cleared columns: any small island of ink goes
    arr = np.asarray(out).copy()
    solid = arr[..., 3] > 24
    lab, n = ndimage.label(solid)
    if n > 1:
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        small = np.isin(lab, 1 + np.nonzero(sizes < sizes.max() * .004)[0])
        arr[ndimage.binary_dilation(small, iterations=2), 3] = 0
    out = Image.fromarray(arr)
    return out.crop(out.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox())


def frames():
    for name, aspect in SHAPES.items():
        im = Image.open(os.path.join(RAW, f'peak_frame_{name}.png')).convert('RGBA')
        im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox())
        im = sink_sign(up4(im))
        x0, y0, x1, y1 = opening(im)
        a0 = (x1 - x0) / (y1 - y0)
        if a0 > aspect:
            im = im.resize((im.width, round(im.height * a0 / aspect)), Image.LANCZOS)
        else:
            im = im.resize((round(im.width * aspect / a0), im.height), Image.LANCZOS)
        im = im.resize((OUT_W[name], round(im.height * OUT_W[name] / im.width)), Image.LANCZOS)
        x0, y0, x1, y1 = opening(im)
        sx0, sy0, sx1, sy1 = sign_face(im, y0)
        W, H = im.size
        op = [round(x0 / W, 5), round(y0 / H, 5), round(x1 / W, 5), round(y1 / H, 5)]
        sg = [round(sx0 / W, 5), round(sy0 / H, 5), round(sx1 / W, 5), round(sy1 / H, 5)]
        im.save(os.path.join(A, f'frame_{name}.webp'), 'WEBP', quality=90, method=6)
        json.dump({'frame_size': [W, H], 'opening': op, 'sign': sg, 'source': 'highpeaks peak pass (peak_install.py)'},
                  open(os.path.join(A, f'frame_{name}.json'), 'w'))
        print(name, (W, H), 'aspect', round((x1 - x0) / (y1 - y0), 4))
        print(f'  --fo-l: {op[0]:.5f}; --fo-t: {op[1]:.5f}; --fo-w: {op[2] - op[0]:.5f}; --fo-h: {op[3] - op[1]:.5f};')
        print(f'  --sg-l: {sg[0]:.5f}; --sg-t: {sg[1]:.5f}; --sg-w: {sg[2] - sg[0]:.5f}; --sg-h: {sg[3] - sg[1]:.5f};')


def cover(im, w, h):
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def plates():
    for src, dst in (('peak_plate', 'bonus_wall'), ('peak_plate_powder', 'scene/plate_zombie'),
                     ('peak_plate_night', 'scene/plate_midnight'), ('peak_plate_avalanche', 'scene/plate_nitro')):
        p = os.path.join(RAW, src + '.png')
        if not os.path.exists(p):
            print('missing', src); continue
        im = Image.open(p).convert('RGB')
        cover(im, 2560, 1440).save(os.path.join(A, dst + '.webp'), 'WEBP', quality=84, method=6)
        cover(im, 1600, 900).save(os.path.join(A, dst + '_m.webp'), 'WEBP', quality=82, method=6)
        print(src, '->', dst)


def trimmed(name, pad=8):
    im = Image.open(os.path.join(RAW, name + '.png')).convert('RGBA')
    bb = im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox()
    im = im.crop(bb)
    out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad))
    out.alpha_composite(im, (pad, pad))
    return out


def fit_w(im, w):
    if im.width < w * .9:
        im = up4(im)
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def win():
    for src, dst in (('peak_big_win', 'big_win'), ('peak_mega_win', 'mega_win'), ('peak_epic_win', 'xtreme_win'),
                     ('peak_total_win', 'total_win')):
        im = fit_w(trimmed(src), 1400)
        im.save(os.path.join(A, dst + '.webp'), 'WEBP', quality=88, method=6)
        print(src, '->', dst, im.size, round(im.width / im.height, 3))
    # the tier splash: the page cuts the headline to 1979:1101, so the splash is fitted INTO that box (centred)
    sp = fit_w(trimmed('peak_tier_bg', 0), 1600)
    W, H = 1600, round(1600 * 1101 / 1979)
    if sp.height > H:
        sp = sp.resize((round(sp.width * H / sp.height), H), Image.LANCZOS)
    box = Image.new('RGBA', (W, H)); box.alpha_composite(sp, ((W - sp.width) // 2, (H - sp.height) // 2))
    box.save(os.path.join(A, 'tier_bg.webp'), 'WEBP', quality=88, method=6)
    print('peak_tier_bg -> tier_bg', box.size)
    for src, dst, w in (('peak_total_bg', 'total_bg', 1400), ('peak_banner_box', 'banner_box', 1440)):
        im = fit_w(trimmed(src, 0), w)
        if dst == 'banner_box':   # the page draws it at 1440:293
            im = im.resize((1440, 293), Image.LANCZOS)
        im.save(os.path.join(A, dst + '.webp'), 'WEBP', quality=88, method=6)
        print(src, '->', dst, im.size)
    numerals()


def numerals():
    """the win figures' flat orange drop shadow turned icy blue (the numerals' white faces and ink keep): every orange
    pixel is re-tinted, its shading kept. Originals kept in art/highpeaks/work/peak/num_orange/."""
    num = os.path.join(A, 'num')
    keep = os.path.join(ROOT, 'art', 'highpeaks', 'work', 'peak', 'num_orange')
    os.makedirs(keep, exist_ok=True)
    for f in sorted(os.listdir(num)):
        src = os.path.join(keep, f)
        if not os.path.exists(src):
            Image.open(os.path.join(num, f)).save(src, 'WEBP', lossless=True)
        im = Image.open(src).convert('RGBA')
        px = np.asarray(im).astype(np.float32)
        r, g, b = px[..., 0], px[..., 1], px[..., 2]
        orange = (r > 150) & (r - b > 90) & (g < r - 30)
        lum = (r * .5 + g * .5) / 255.0                      # the orange's own light/dark, kept
        ice = np.array([46, 150, 245], np.float32)           # icy sky blue
        for i in range(3):
            px[..., i] = np.where(orange, np.clip(ice[i] * (lum / .62), 0, 255), px[..., i])
        Image.fromarray(px.astype(np.uint8)).save(os.path.join(num, f), 'WEBP', quality=90, method=6)
    print('numerals: orange shadow -> icy blue')


if __name__ == '__main__':
    for what in sys.argv[1:]:
        {'frames': frames, 'plates': plates, 'win': win}[what]()
