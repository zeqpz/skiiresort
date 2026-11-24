"""High Peaks - the layered scene's art, installed (owner, 2026-11-23: "a foreground, midground and background ...
dynamic and animated", "blend the yeti with the background").

    python tools/highpeaks/layers_install.py            the generated layers (art/highpeaks/jobs/layers_jobs.py) when
                                                        art/highpeaks/raw/layer_back.png + layer_mid.png are there,
                                                        otherwise the PROVISIONAL cut of the peak plate (below)
    python tools/highpeaks/layers_install.py --provisional      force the provisional cut
    python tools/highpeaks/layers_install.py --selftest         the magenta key, checked on a made-up picture

-> frontend/assets/scene/layers/  back.webp, mid.webp (+ _m, 1600 wide), the sprites, layers.json (what frontend/layers.js
   reads: where everything stands in plate px, how far each layer drifts, each scene's light on the yeti)
-> frontend/assets/yeti/drift.webp   the drift of snow his boots and board stand in (charrig.js `ground`)

Generated layers: layer_back is the far layer as it is; layer_mid was drawn on flat magenta (the model gives 4K only
for an opaque picture) and is keyed here - alpha from each pixel's distance to magenta, the pink spill taken out of
the edge pixels. Sprites are trimmed to their ink.

Provisional (no generated layers yet): the back is the peak plate itself and the mid is only its snow floor, cut a
little under the ridge with a soft edge, so the two are the same picture at rest and nothing slides (the back's drift
is 0 until there is a real far layer). The foreground rocks are the plate's own, cut out by their ink outline.
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
A = os.path.join(ROOT, 'frontend', 'assets')
OUT = os.path.join(A, 'scene', 'layers')
PW, PH = 3840, 2160
DIM = (7, 11, 24)            # the scene's dim (index.html #bgwall::after) and how strong it is where the yeti stands
DIM_AT_YETI = .21
BODY_MATCH = .86           # how far his own colours go toward the scene's light (1: his white = the snow's white)
# the base plate and each bonus scene's plate (index.html Scene.PLATES): where the light on the yeti is read from
PLATES = {'normal': 'peak_plate.png', 'zombie': 'peak_plate_powder.png', 'midnight': 'peak_plate_night.png',
          'nitro': 'peak_plate_avalanche.png'}
SNOW_BOX = (2500, 1500, 3400, 1760)   # the open patch of snow right of the board, where he stands (plate px)


def raw(name):
    """The newest version of a raw picture (orgen.py writes name.png, name.v2.png ...), or None."""
    best, bv = None, 0
    for f in os.listdir(RAW):
        if f == name + '.png':
            v = 1
        elif f.startswith(name + '.v') and f.endswith('.png') and f[len(name) + 2:-4].isdigit():
            v = int(f[len(name) + 2:-4])
        else:
            continue
        if v > bv:
            best, bv = os.path.join(RAW, f), v
    return best


def save(im, name, q=88, small=None):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + '.webp')
    kw = dict(quality=q, method=6)
    if im.mode == 'RGBA':
        kw['alpha_quality'] = 92
    im.save(p, 'WEBP', **kw)
    if small:
        s = im.resize((small, round(im.size[1] * small / im.size[0])), Image.LANCZOS)
        s.save(os.path.join(OUT, name + '_m.webp'), 'WEBP', **kw)
    return os.path.getsize(p)


def trim(im, pad=4):
    bb = im.getchannel('A').point(lambda a: 255 if a > 10 else 0).getbbox()
    if not bb:
        return im
    bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.size[0], bb[2] + pad), min(im.size[1], bb[3] + pad))
    return im.crop(bb)


# ---------------------------------------------------------------- the magenta key
def key_magenta(im):
    """A picture drawn on flat #FF00FF -> RGBA. Alpha rises with the distance from magenta (the ink outline against
    the ground is a soft step, so the edge keeps its anti-aliasing); edge pixels have the magenta they were mixed
    with taken back out."""
    px = np.asarray(im.convert('RGB')).astype(np.float32) / 255
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    # how magenta a pixel is: red and blue both high above green
    mag = np.clip(np.minimum(r, b) - g, 0, 1)
    a = np.clip(1 - mag / .82, 0, 1)
    a = np.where(a > .97, 1.0, np.where(a < .06, 0.0, a))
    # un-mix: pixel = a * colour + (1 - a) * magenta
    aa = np.maximum(a, .08)[..., None]
    col = (px - (1 - a[..., None]) * np.array([1, 0, 1], np.float32)) / aa
    col = np.clip(col, 0, 1)
    out = np.dstack([col, a[..., None]])
    return Image.fromarray((out * 255 + .5).astype(np.uint8), 'RGBA')


def selftest():
    plate = Image.open(os.path.join(RAW, 'peak_plate.png')).convert('RGB').crop((0, 900, 1600, 1800))
    m = Image.new('L', plate.size, 0)
    ImageDraw.Draw(m).polygon([(0, 560), (500, 300), (1600, 420), (1600, 900), (0, 900)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.2))
    comp = Image.composite(plate, Image.new('RGB', plate.size, (255, 0, 255)), m)
    k = key_magenta(comp)
    a = np.asarray(k.getchannel('A')).astype(np.float32) / 255
    want = np.asarray(m).astype(np.float32) / 255
    inside = want > .99
    err_col = np.abs(np.asarray(k.convert('RGB')).astype(int) - np.asarray(plate).astype(int))[inside].max()
    print('alpha mean abs error', round(float(np.abs(a - want).mean()), 4), '| worst colour error inside', int(err_col),
          '| solid kept', round(float((a[inside] > .97).mean()), 4), '| ground cleared', round(float((a[want < .01] < .03).mean()), 4))


# ---------------------------------------------------------------- the light on the yeti, per scene
FLAKES = {'normal': 9, 'zombie': 22, 'midnight': 8, 'nitro': 13}   # near flakes falling in front of him, per scene


def snow_light(path):
    """Where the yeti stands, on one plate: the colour of lit snow (the bright end of that patch, its drift lines and
    rocks left out) and of the plate's own flat shadow shapes on it (the darker snow tones)."""
    im = np.asarray(Image.open(path).convert('RGB').resize((PW, PH), Image.LANCZOS).crop(SNOW_BOX)).reshape(-1, 3).astype(np.float32)
    lum = im @ np.array([.3, .59, .11], np.float32)
    lit = im[lum >= np.percentile(lum, 70)].mean(0)
    lo, hi = np.percentile(lum, 12), np.percentile(lum, 34)
    sat = im.max(1) - im.min(1)
    band = im[(lum >= lo) & (lum <= hi) & (lum > 110) & (sat < 90)]            # shaded snow, not rock or ink
    shade = band.mean(0) if len(band) > 50 else lit * np.array([.82, .9, .98], np.float32)
    return lit, shade


def moods():
    """Each scene's light where the yeti stands, as charrig.js wants it:
      ground  x the drift's white: the lit snow as the page shows it (under the scene's dim)
      body    x his own colours: the same light and the same dim, most of the way - so his white fur is the snow's
              white, not a brighter one (he was full-bright on a dimmed scene: laid on top of it, not standing in it)
      shade   x the snow, for his flat shadow: the plate's own shadow tone over its lit snow"""
    out = {}
    navy = np.array(DIM, np.float32) / 255
    hx = lambda v: '#%02x%02x%02x' % tuple(int(round(float(x) * 255)) for x in np.clip(v, 0, 1))
    for name, f in PLATES.items():
        p = os.path.join(RAW, f)
        if not os.path.exists(p):
            continue
        lit, shade = snow_light(p)
        c = lit / 255
        seen = c * (1 - DIM_AT_YETI) + navy * DIM_AT_YETI                         # lit snow as the page shows it
        body = 1 - BODY_MATCH * (1 - seen)
        # (the patch he stands on is nearly all lit snow, so the plate's shadow tone is not reliably in it: the ratio of
        # the scene's drawn shadow shapes to its snow, #cbe2fa over #f6faff)
        ratio = np.array([.80, .885, .975], np.float32)
        out[name] = dict(ground=hx(seen), body=hx(body), shade=hx(ratio), snow=hx(c), flakes=FLAKES.get(name, 9))
    return out

# ---------------------------------------------------------------- the drift the yeti stands in
def drift(w=1500, h=380, seed=11):
    """A low drift of snow: lumpy on top with an ink line along the top only, pale-blue shadow shapes, its foot faded
    out so it sinks into whatever snow floor is under it."""
    S = 2
    W, H = w * S, h * S
    rnd = random.Random(seed)
    humps = [(c + rnd.uniform(-.04, .04), rnd.uniform(.07, .11), rnd.uniform(.5, 1.0)) for c in (.14, .31, .5, .68, .86)]

    def top(x):                                   # 0-1 across -> height 0-1
        u = x / W
        env = math.sin(math.pi * u) ** .55
        y = .34 + sum(a * math.exp(-((u - c) / s_) ** 2) for c, s_, a in humps) * .62
        return env * min(1.0, y)
    xs = list(range(0, W + 1, 6))
    line = [(x, H * .62 - top(x) * H * .5) for x in xs]
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(line + [(W, H), (0, H)], fill=(246, 250, 255, 255))
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for i in range(6):                            # flat pale-blue shadow shapes, under the humps
        cx, cy = rnd.uniform(.12, .88) * W, H * rnd.uniform(.56, .72)
        rw, rh = rnd.uniform(.07, .16) * W, rnd.uniform(.035, .06) * H
        ds.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(203, 226, 250, 255))
    for i in range(9):                            # short curved texture lines
        cx, cy = rnd.uniform(.1, .9) * W, H * rnd.uniform(.5, .78)
        rw = rnd.uniform(.03, .07) * W
        ds.arc([cx - rw, cy - rw * .28, cx + rw, cy + rw * .28], 200, 340, fill=(170, 205, 245, 255), width=5 * S)
    body = im.getchannel('A')
    im.alpha_composite(Image.composite(sh, Image.new('RGBA', (W, H), (0, 0, 0, 0)), body))
    d = ImageDraw.Draw(im)
    d.line(line, fill=(18, 18, 26, 255), width=9 * S, joint='curve')
    # the ink thins to nothing at the two ends, and the foot fades away
    a = np.asarray(im.getchannel('A')).astype(np.float32) / 255
    yy = np.linspace(0, 1, H)[:, None]
    xx = np.linspace(0, 1, W)[None, :]
    foot = np.clip((.985 - yy) / .3, 0, 1) ** 1.2
    ends = np.clip(np.minimum(xx, 1 - xx) / .09, 0, 1) ** .8
    im.putalpha(Image.fromarray((a * foot * ends * 255).astype(np.uint8)))
    return im.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- provisional: cut from the peak plate
RIDGE = [(0, 1540), (350, 1520), (1000, 1486), (1400, 1466), (1900, 1466), (2400, 1450), (2800, 1436), (3050, 1430),
         (3300, 1462), (3840, 1520)]
ROCKS = {'rock_l': (220, 1580, 810, 1840), 'rock_r': (3070, 1590, 3650, 1885)}


def cut_object(plate, box):
    """An object standing on the snow, by its ink: everything in the box that the snow round it cannot reach."""
    im = plate.crop(box).convert('RGB')
    px = np.asarray(im).astype(int)
    lum = px @ np.array([.3, .59, .11])
    sat = px.max(2) - px.min(2)
    snow = (lum > 185) & (px[..., 2] >= px[..., 0] - 4)            # white and pale-blue: the floor
    lab, n = ndimage.label(snow)
    edge = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    edge.discard(0)
    outside = np.isin(lab, list(edge))
    solid = ndimage.binary_fill_holes(~outside)
    solid = ndimage.binary_opening(solid, iterations=2)
    lab2, n2 = ndimage.label(solid)
    if n2 > 1:                                                      # the biggest piece is the object
        sizes = ndimage.sum(solid, lab2, range(1, n2 + 1))
        solid = lab2 == (1 + int(np.argmax(sizes)))
    a = Image.fromarray((solid * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))
    out = im.convert('RGBA'); out.putalpha(a)
    return trim(out)


def provisional():
    plate = Image.open(os.path.join(RAW, 'peak_plate.png')).convert('RGB')
    assert plate.size == (PW, PH), plate.size
    save(plate, 'back', small=1600)
    m = Image.new('L', (PW, PH), 0)
    ImageDraw.Draw(m).polygon(RIDGE + [(PW, PH), (0, PH)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(14))
    mid = plate.convert('RGBA'); mid.putalpha(m)
    save(mid, 'mid', small=1600)
    front = []
    for name, box in ROCKS.items():
        spr = cut_object(plate, box)
        save(spr, name, q=90)
        front.append(dict(src=name + '.webp', corner='bl' if name.endswith('_l') else 'br', h=.2, aspect=round(spr.size[0] / spr.size[1], 4),
                          inset=[.015, -.02], drift=[10, 3], period=23 if name.endswith('_l') else 29))
    return dict(provisional=True, back=dict(src='back.webp', drift=[0, 0], period=46, bleed=1.0),
                mid=dict(src='mid.webp'), pines=[], flag=None, lift=None, front=front,
                windows=[[755, 1170, 190, 130], [515, 1158, 90, 100]],
                clouds=dict(high=[40, 380], low=None), sparkle=dict(box=[900, 1520, 3700, 2100], n=10))


def generated():
    back = Image.open(raw('layer_back')).convert('RGB').resize((PW, PH), Image.LANCZOS)
    save(back, 'back', small=1600)
    mid = key_magenta(Image.open(raw('layer_mid')).convert('RGB').resize((PW, PH), Image.LANCZOS))
    save(mid, 'mid', q=90, small=1600)
    cfg = dict(provisional=False, back=dict(src='back.webp', drift=[0, 0]), mid=dict(src='mid.webp'),
               pines=[], flag=None, lift=None, front=[], windows=[], clouds=dict(high=[40, 420], low=[620, 1180]),
               sparkle=dict(box=[900, 1520, 3700, 2100], n=10))
    sprites = {}
    for name, rawname, target in (('spr_pine', 'spr_pine', 760), ('spr_flag', 'spr_flag', 400), ('fg_drift', 'fg_drift', 900),
                                  ('fg_bough', 'fg_bough', 900), ('chair', 'spr_chair', 260)):
        p = raw(rawname)
        if not p:
            continue
        spr = trim(Image.open(p).convert('RGBA'))
        k = target / max(spr.size)
        spr = spr.resize((max(1, round(spr.size[0] * k)), max(1, round(spr.size[1] * k))), Image.LANCZOS)
        save(spr, name, q=90)
        sprites[name + '.webp'] = spr
    # where the pines, the flag, the lift's cable and the hut's windows are was read off the new picture by hand
    # (art/highpeaks/jobs/layers_places.json); each sprite's shape is filled in here
    places = os.path.join(ROOT, 'art', 'highpeaks', 'jobs', 'layers_places.json')
    if os.path.exists(places):
        P = json.load(open(places))
        P.pop('_', None)
        asp = lambda src: round(sprites[src].size[0] / sprites[src].size[1], 4)
        for p in P.get('pines', []):
            p['aspect'] = asp(p['src'])
        for f in P.get('front', []):
            f['aspect'] = asp(f['src'])
        if P.get('flag'):
            P['flag']['h'] = round(P['flag']['w'] / asp(P['flag']['src']))
        if P.get('lift'):
            P['lift']['aspect'] = asp(P['lift']['src'])
        cfg.update(P)
    # the whole picture, flat: what shows before the layers are up and wherever the plate is used as one image
    # (the loading screen, reduced motion): back, pines, summit, flag
    flat = back.convert('RGBA')
    for p in cfg.get('pines', []):
        spr = sprites[p['src']]
        w = round(p['h'] * p['aspect'])
        flat.alpha_composite(spr.resize((w, p['h']), Image.LANCZOS), (round(p['x'] - w / 2), p['y'] - p['h']))
    flat.alpha_composite(mid)
    if cfg.get('flag'):
        F = cfg['flag']
        flat.alpha_composite(sprites[F['src']].resize((F['w'], F['h']), Image.LANCZOS), (F['x'], F['y']))
    flat = flat.convert('RGB')
    flat.save(os.path.join(A, 'bonus_wall.webp'), 'WEBP', quality=86, method=6)
    flat.resize((1600, 900), Image.LANCZOS).save(os.path.join(A, 'bonus_wall_m.webp'), 'WEBP', quality=86, method=6)
    flat.save(os.path.join(RAW, 'layers_flat.png'))
    return cfg

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    have = raw('layer_back') and raw('layer_mid') and '--provisional' not in sys.argv
    cfg = generated() if have else provisional()
    cfg['size'] = [PW, PH]
    if have and os.path.exists(os.path.join(RAW, 'layers_flat.png')):
        PLATES['normal'] = 'layers_flat.png'
    cfg['moods'] = moods()
    cfg['dim_at_yeti'] = DIM_AT_YETI
    # the yeti's drift: the generated one when there is one, else drawn here
    yd = raw('yeti_drift') if '--generated-drift' in sys.argv else None   # (the generated one came out a thin sliver)
    if yd and have:
        d = trim(Image.open(yd).convert('RGBA'))
        d = d.resize((1500, round(d.size[1] * 1500 / d.size[0])), Image.LANCZOS)
        a = np.asarray(d.getchannel('A')).astype(np.float32)
        yy = np.linspace(0, 1, d.size[1])[:, None]
        d.putalpha(Image.fromarray((a * np.clip((.985 - yy) / .3, 0, 1) ** 1.2).astype(np.uint8)))
    else:
        d = drift()
    d.save(os.path.join(A, 'yeti', 'drift.webp'), 'WEBP', quality=90, method=6, alpha_quality=95)
    cfg['yeti_drift'] = dict(src='assets/yeti/drift.webp', size=list(d.size))
    json.dump(cfg, open(os.path.join(OUT, 'layers.json'), 'w'), indent=1)
    print('provisional' if cfg['provisional'] else 'generated', '->', OUT)
    for f in sorted(os.listdir(OUT)):
        print(f'  {f:22s} {os.path.getsize(os.path.join(OUT, f)) / 1024:8.0f} KB')
    print('moods', json.dumps(cfg['moods']))
