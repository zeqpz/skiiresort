"""The win numerals as CHUNKS OF ICE (owner, 2026-11-23: "make the win font different and fit the theme better, make
it ice chunks").

    python tools/highpeaks/ice_numerals.py [OUT_DIR]        (default: frontend/assets/num, in place)

frontend/assets/num/<0-9, comma, dot, x>.webp - the figures the big win counts, the bonus total and the free-spin
card are set in - redrawn as blocks cut from ice, in the game's flat cartoon hand:

  * a chunky rounded figure with its curves cut into straight chamfers (an opening by an octagon), so it reads as
    hewn, not printed;
  * its face broken into flat facets (a Voronoi of a few points) in ice blues, lit from the upper left, with a white
    line where two facets meet, a crack and a hard white glint;
  * a cap of snow lying on every top edge, with a pale-blue shade under it;
  * the thick ink outline and the flat deep-blue drop the old figures had, so they sit on the win art as before.

Each is fitted into the old numeral's solid part on a canvas of the old numeral's size, so every amount lays out
exactly as it did (flat_numerals.py did the same when it drew the white ones). The white figures it replaces are kept
in art/highpeaks/ui_flat/num/ the first time this runs. Deterministic: the same picture every run.
"""
import os, random, shutil, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NUM = os.path.join(ROOT, 'frontend', 'assets', 'num')
KEEP = os.path.join(ROOT, 'art', 'highpeaks', 'ui_flat', 'num')
FONTS = [r'C:\Windows\Fonts\ARLRDBD.TTF', '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf']
GLYPH = {**{str(d): str(d) for d in range(10)}, 'comma': ',', 'dot': '.', 'x': 'x'}
INK = (12, 12, 18)
DROP = (30, 99, 200)             # the flat deep-blue drop under the figure
ICE = [(244, 252, 255), (222, 244, 255), (193, 233, 252), (158, 218, 247), (120, 197, 239), (86, 172, 226), (62, 148, 212)]
SNOW, SNOW_SHADE = (255, 255, 255), (197, 226, 248)
S = 4                            # drawn at 4x, then shrunk


def octagon(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (np.abs(x) + np.abs(y) <= r * 1.42) & (np.abs(x) <= r) & (np.abs(y) <= r)


def figure_mask(ch, box_w, box_h):
    """The figure, fitted into box_w x box_h (px at 1x), as a 4x mask cut into chamfers."""
    font = ImageFont.truetype(next(f for f in FONTS if os.path.exists(f)), 400)
    l, t, r, b = font.getbbox(ch)
    im = Image.new('L', (r - l + 80, b - t + 80), 0)
    ImageDraw.Draw(im).text((40 - l, 40 - t), ch, font=font, fill=255)
    im = im.crop(im.getbbox())
    k = min(box_w * S / im.size[0], box_h * S / im.size[1])
    im = im.resize((max(4, round(im.size[0] * k)), max(4, round(im.size[1] * k))), Image.LANCZOS)
    m = np.asarray(im) > 127
    rad = max(3, round(min(m.shape) * .035))
    m = np.pad(m, rad * 3)
    cut = ndimage.binary_opening(m, structure=octagon(rad * 2))        # corners and curves become straight cuts
    cut = ndimage.binary_closing(cut, structure=octagon(rad))
    cut = cut | ndimage.binary_erosion(m, iterations=rad)               # never thinner than the figure's own stem
    ys, xs = np.nonzero(cut)
    return cut[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def chunk(ch, size, solid):
    """One figure on a `size` canvas, its solid part filling the box `solid` (x0, y0, x1, y1)."""
    rnd = random.Random(sum(ord(c) * (i + 3) for i, c in enumerate(ch)) + 17)
    W, H = size[0] * S, size[1] * S
    bw, bh = solid[2] - solid[0], solid[3] - solid[1]
    stroke = max(4, round(min(size) * .058)) * S
    shift = (round(size[0] * .075) * S, round(size[1] * .085) * S)
    m = figure_mask(ch, bw - (2 * stroke + shift[0]) / S, bh - (2 * stroke + shift[1]) / S)
    mh, mw = m.shape
    ox, oy = solid[0] * S + stroke, solid[1] * S + stroke
    M = np.zeros((H, W), bool)
    hh, ww = min(mh, H - oy), min(mw, W - ox)
    M[oy:oy + hh, ox:ox + ww] = m[:hh, :ww]
    yy, xx = np.mgrid[0:H, 0:W]

    # ---- facets: a Voronoi of a few points inside the figure, each a flat ice blue by where it faces
    ys, xs = np.nonzero(M)
    n = 9 if ch not in ',.' else 3
    order = list(range(len(ys))); rnd.shuffle(order)
    seeds = []
    for i in order[:4000]:                                              # spread them out
        p = (int(xs[i]), int(ys[i]))
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > (min(mw, mh) * .3) ** 2 for q in seeds):
            seeds.append(p)
        if len(seeds) >= n:
            break
    tree = cKDTree(np.array(seeds, float))
    _, lab = tree.query(np.column_stack([xx.ravel(), yy.ravel()]), k=1)
    lab = lab.reshape(H, W)
    rgb = np.zeros((H, W, 3), np.float32)
    cx, cy = ox + mw / 2, oy + mh / 2
    for i, (sx, sy) in enumerate(seeds):
        lit = ((cx - sx) / mw + (cy - sy) / mh) * .9 + rnd.uniform(-.28, .28)      # upper left is lit
        idx = int(np.clip(round(2.6 - lit * 4.2), 0, len(ICE) - 1))
        rgb[lab == i] = ICE[idx]
    edge = np.zeros((H, W), bool)                                       # where two facets meet: a white line
    edge[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    edge[1:, :] |= lab[1:, :] != lab[:-1, :]
    edge = ndimage.binary_dilation(edge, iterations=S // 2 + 1) & M
    rgb[edge] = rgb[edge] * .25 + np.array([255, 255, 255], np.float32) * .75

    # ---- a cap of snow on every top edge, lumpy underneath, a pale shade below it
    top = M & ~np.roll(M, 1, axis=0)                                     # pixels with nothing solid above
    top[0, :] = False
    capd = mh * (.13 if ch not in ',.' else .3)
    wave = (1 + .38 * np.sin(xx[0] / (mw * .085) + rnd.uniform(0, 6))) * capd
    depth = np.full((H, W), 1e9, np.float32)
    run = np.zeros(W, np.float32)
    live = np.zeros(W, bool)
    for y in range(H):                                                   # march down from each top edge
        run = np.where(top[y], 0, run + 1)
        live = (live | top[y]) & M[y] & (run < wave * 1.5)
        depth[y] = np.where(live, run, 1e9)
    cap = M & (depth < wave)
    shade = M & (depth >= wave) & (depth < wave + capd * .28)
    rgb[shade] = rgb[shade] * .45 + np.array(SNOW_SHADE, np.float32) * .55
    rgb[cap] = SNOW

    face = Image.fromarray(rgb.astype(np.uint8), 'RGB')
    d = ImageDraw.Draw(face)
    glint = Image.new('L', (W, H), 0)
    if ch not in ',.':                                                   # a crack and a hard glint
        x0, y0 = ox + mw * rnd.uniform(.45, .7), oy + mh * rnd.uniform(.4, .55)
        pts = [(x0, y0)]
        for _ in range(3):
            pts.append((pts[-1][0] + rnd.uniform(-.12, .12) * mw, pts[-1][1] + rnd.uniform(.07, .13) * mh))
        d.line(pts, fill=(255, 255, 255), width=2 * S, joint='curve')
        gx, gy = ox + mw * .2, oy + mh * .3
        ImageDraw.Draw(glint).polygon([(gx, gy), (gx + mw * .1, gy - mh * .05), (gx + mw * .06, gy + mh * .16), (gx - mw * .03, gy + mh * .2)], fill=235)
    glint = Image.fromarray((np.asarray(glint) * (M & ~cap)).astype(np.uint8))
    face_a = Image.fromarray((M * 255).astype(np.uint8))

    # ---- compose: the blue drop (inked), the figure's ink, its face
    grow = lambda mask, px: ndimage.binary_dilation(mask, structure=octagon(px))
    ink = grow(M, stroke)
    drop_fill = np.zeros_like(M)
    drop_fill[shift[1]:, shift[0]:] = M[:H - shift[1], :W - shift[0]]
    drop_ink = grow(drop_fill, stroke)
    out = np.zeros((H, W, 4), np.uint8)
    for mask, col in ((drop_ink, INK), (drop_fill, DROP), (ink, INK)):
        out[mask] = (*col, 255)
    im = Image.fromarray(out, 'RGBA')
    im.paste(face, (0, 0), face_a)
    im.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), glint)
    return im.resize(size, Image.LANCZOS)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else NUM
    os.makedirs(out, exist_ok=True)
    if out == NUM and not os.path.isdir(KEEP):                           # the white figures, kept once
        os.makedirs(KEEP)
        for f in os.listdir(NUM):
            shutil.copy2(os.path.join(NUM, f), os.path.join(KEEP, f))
    src = KEEP if os.path.isdir(KEEP) else NUM                           # always fitted to the original figures
    for name, ch in GLYPH.items():
        old = Image.open(os.path.join(src, name + '.webp')).convert('RGBA')
        solid = old.getchannel('A').point(lambda a: 255 if a > 128 else 0).getbbox() or (0, 0, *old.size)
        im = chunk(ch, old.size, solid)
        im.save(os.path.join(out, name + '.webp'), 'WEBP', quality=92, method=6, alpha_quality=95)
        print(f'{name:6s} {old.size} solid {solid}')
