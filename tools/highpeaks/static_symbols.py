"""Static PNG symbols (owner, 2026-11-12: the nine regular symbols "look so basic and AI" - redrawn in an inked-comic
style, and "static PNGs": no Blender animation, one picture each, scaled up smoothly when it wins).

    .venv/bin/python tools/highpeaks/static_symbols.py [IDS...]      (default: every art/highpeaks/symbols_static/<ID>.png)
    .venv/bin/python tools/highpeaks/align_clips.py && .venv/bin/python tools/highpeaks/centre_symbols.py

Each art/highpeaks/symbols_static/<ID>.png (a transparent picture of the symbol, any size, ideally ~1024 square) is
fitted into the symbol's square like CSS object-fit: contain (its longer side across the icon, centred, aspect
kept) and written as the four clips the board plays, at every density in frontend/assets/sym/manifest.json - so the
board canvas (boardgl.js), the 2D fallback, and every game timing that waits on a clip's length work unchanged:

  land   12 frames: arrives a little stretched, squashes, settles - its LAST frame is the rest pose (scale 1)
  idle    1 frame:  the rest pose (no idle motion)
  hit    30 frames: a smooth eased swell to HIT_SCALE and back - the win
  burn   24 frames: a short swell, then shrinks and fades away

plus frontend/assets/flat/<ID>.webp (the rules screen, the first seconds, reduced motion). The manifest's entry for
the symbol is rewritten (clips, boxes, sheets; "static": true).
"""
import io, json, math, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'art', 'highpeaks', 'symbols_static')
A = os.path.join(ROOT, 'frontend', 'assets')
SYM = os.path.join(A, 'sym')
BOX = 12.0            # the clips' square box, in icon units (the icon is 10): room for the win's swell
FILL = 10.0           # the picture's longer side at rest, in icon units: the whole icon
HIT_SCALE = 1.16
FPS = 30
Q = 88


def ease(t):          # smooth in and out
    return .5 - .5 * math.cos(math.pi * max(0., min(1., t)))


def land(f, n):       # (scale x, scale y, alpha)
    t = f / (n - 1)
    if f == n - 1:
        return 1., 1., 1.
    k = math.exp(-5 * t) * math.cos(2.6 * math.pi * t)   # a damped squash: stretched on arrival, squashed, settling
    return 1 - .12 * k, 1 + .14 * k, min(1., .55 + 3 * t)


def hit(f, n):
    s = 1 + (HIT_SCALE - 1) * math.sin(math.pi * ease(f / (n - 1)))
    return s, s, 1.


def burn(f, n):
    t = f / (n - 1)
    if t < .3:
        s = 1 + .1 * ease(t / .3)
        return s, s, 1.
    u = ease((t - .3) / .7)
    s = 1.1 * (1 - .85 * u)
    return s, s, 1 - u


CLIPS = {'land': (12, land, False), 'idle': (1, lambda f, n: (1., 1., 1.), True), 'hit': (30, hit, False), 'burn': (24, burn, False)}


def fitted(src, px):
    """The picture contain-fitted: its longer side FILL icon units at px sheet px a unit (object-fit: contain)."""
    bb = src.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, *src.size)
    pic = src.crop(bb)
    k = FILL * px / max(pic.size)
    return pic, k


def frame(pic, k, size, sx, sy, alpha):
    w, h = max(1, round(pic.width * k * sx)), max(1, round(pic.height * k * sy))
    im = pic.resize((w, h), Image.LANCZOS)
    if alpha < 1:
        a = im.getchannel('A').point(lambda v: round(v * alpha))
        im.putalpha(a)
    out = Image.new('RGBA', (size, size))
    out.alpha_composite(im, ((size - w) // 2, (size - h) // 2))
    return out


def webp(im, path):
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=Q, method=6, alpha_quality=95)
    open(path, 'wb').write(buf.getvalue())
    return len(buf.getvalue())


man = json.load(open(os.path.join(SYM, 'manifest.json')))
ids = [a for a in sys.argv[1:]] or sorted(os.path.splitext(f)[0] for f in os.listdir(SRC) if f.endswith('.png'))
for sid in ids:
    src = Image.open(os.path.join(SRC, sid + '.png')).convert('RGBA')
    e = {'icon': [10.0, 10.0], 'static': True, 'clips': {}, 'sheets': {}}
    for c, (n, _, loop) in CLIPS.items():
        e['clips'][c] = {'frames': n, 'fps': FPS, 'loop': loop, 'box': [-BOX / 2, -BOX / 2, BOX, BOX]}
    for dens in man['densities']:
        d = 'd%d' % round(dens * 10)
        px = 10 * dens                    # sheet px per icon unit
        size = round(BOX * px)
        pic, k = fitted(src, px)
        e['sheets'][d] = {}
        for c, (n, fn, _) in CLIPS.items():
            cols = max(1, min(n, 4096 // size))
            rows = math.ceil(n / cols)
            sheet = Image.new('RGBA', (cols * size, rows * size))
            for f in range(n):
                sheet.alpha_composite(frame(pic, k, size, *fn(f, n)), ((f % cols) * size, (f // cols) * size))
            nb = webp(sheet, os.path.join(SYM, d, f'{sid}_{c}.webp'))
            e['sheets'][d][c] = {'w': size, 'h': size, 'cols': cols, 'bytes': nb}
    # the flat icon: the picture contain-fitted in 400 x 400 with a little margin
    pic, _ = fitted(src, 1)
    k = 376 / max(pic.size)
    flat = Image.new('RGBA', (400, 400))
    im = pic.resize((round(pic.width * k), round(pic.height * k)), Image.LANCZOS)
    flat.alpha_composite(im, ((400 - im.width) // 2, (400 - im.height) // 2))
    webp(flat, os.path.join(A, 'flat', sid + '.webp'))
    old = man['symbols'].get(sid, {})
    for keep in ('centre',):
        if keep in old:
            e[keep] = old[keep]
    man['symbols'][sid] = e
    print(sid, 'static:', ', '.join(f'{d} {s["land"]["w"]}px' for d, s in e['sheets'].items()))
json.dump(man, open(os.path.join(SYM, 'manifest.json'), 'w'), separators=(',', ':'))
