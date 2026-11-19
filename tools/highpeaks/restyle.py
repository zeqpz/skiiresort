"""Flat TV-cartoon restyle (owner, 2026-11-13: "regenerate the background, hud, buy bonus icon, 3 boxes intros, all
the graphics in the buy bonus hud ... keep the icons ... simple but detailed ... change any realistic / shaded
graphics like the win hud"). The symbols are the style: clean even black outlines, flat colour with one simple shadow
tone, no gloss, bevels, chrome, glow or realistic light.

    .venv/bin/python tools/highpeaks/restyle.py ui [names...]     the game's UI art (UI below), one at a time
    .venv/bin/python tools/highpeaks/restyle.py plates [names...] the scene plates (PLATES below)
    then compress_assets.py

Each picture is redrawn by the image model (tools/highpeaks/orgen.py) from two references: the picture itself (its
layout, its words, its colours) and art/highpeaks/work/restyle/style_ref.png (the symbols). The result is fitted back
exactly where the old one sat - its solid part contain-fitted into the old picture's solid part, on a canvas of the
old picture's size - so no layout in the game moves. The glossy originals are kept once in art/highpeaks/ui_glossy/
(plates: art/highpeaks/scene/plate_<n>.painted.png) and every run starts from them.
"""
import json, os, shutil, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orgen  # noqa: E402

A = os.path.join(ROOT, 'frontend', 'assets')
KEEP = os.path.join(ROOT, 'art', 'highpeaks', 'ui_glossy')
SC = os.path.join(ROOT, 'art', 'highpeaks', 'scene')
WORK = os.path.join(ROOT, 'art', 'highpeaks', 'work', 'restyle')
STYLE_REF = os.path.join(WORK, 'style_ref.png')
STYLE = ("in the flat TV-cartoon style of the second reference image: clean, even, confident black outlines, flat bright "
         "colours with at most one simple flat shadow tone per shape, simple but detailed shapes. No gloss, no shine "
         "streaks, no bevels, no chrome, no metallic sheen, no 3D lighting, no gradients, no glow, no realistic texture.")

# name -> (kind, words on it or None, what it is)  kind: 'cut' (transparent UI piece) | 'art' (opaque illustration)
UI = {
    'bonus_btn_bg': ('cut', None, 'the BUY BONUS button\'s backing: a small retro gas-pump-shaped sign with an eagle badge on top, a nozzle hanging on its left side and an empty dark display window'),
    'bonus_btn_text': ('cut', 'BUY BONUS', 'the BUY BONUS button lettering on its sign shape with a star and little wings'),
    'banner_box': ('cut', None, 'a long empty banner plate with rounded ends, an empty dark middle for text'),
    'big_win': ('cut', 'BIG WIN', 'the BIG WIN win-celebration lettering'),
    'mega_win': ('cut', 'MEGA WIN', 'the MEGA WIN win-celebration lettering'),
    'xtreme_win': ('cut', 'EPIC WIN', 'the EPIC WIN win-celebration lettering'),
    'total_win': ('cut', 'TOTAL WIN', 'the TOTAL WIN lettering'),
    'tier_bg': ('cut', None, 'an empty plaque for the win amount, with a burst of rays behind it'),
    'total_bg': ('cut', None, 'an empty rounded plaque for the total win amount'),
    'title_logo': ('cut', 'FALCOS', 'the game\'s title logo: the FALCOS gas station building on top of a sign reading FALCOS with a star and a fuel nozzle'),
    'load/bonus': ('art', None, 'a loading-screen card picture about big bonuses: casino chips, gems and cash bursting from a fuel nozzle at a night gas station'),
    'load/features': ('art', None, 'a loading-screen card picture about hot features: a lit flip-top lighter, a red gas pump and scratch tickets'),
    'load/max': ('art', None, 'a loading-screen card picture about the max win: a huge pickup truck with blazing headlights and blue exhaust flames, cash flying'),
    'load/card_frame': ('cut', None, 'an empty card frame with rounded corners and an empty white label panel at the bottom'),
    'load/title_bonus': ('cut', 'BIG BONUSES', 'the BIG BONUSES card title lettering'),
    'load/title_features': ('cut', 'HOT FEATURES', 'the HOT FEATURES card title lettering'),
    'load/title_max': ('cut', 'MAX WIN', 'the MAX WIN card title lettering'),
    'load/bar_frame': ('cut', 'E F', 'an empty loading bar shaped like a fuel gauge, a fuel nozzle at its left end, E at the left and F at the right'),
    'load/bar_fill': ('art', None, 'the loading bar\'s fill: orange fuel with bubbles under a blue band, seen side on'),
    'menu/chance': ('art', None, 'the FUEL CHANCE bonus picture: a fuel nozzle beside a big fuel gauge with its needle jumping, at a night gas station'),
    'menu/fillup': ('art', None, 'the FILL UP bonus picture: a fuel nozzle pouring colourful fuel drops into glowing cells'),
    'menu/premium': ('art', None, 'the PREMIUM bonus picture: a cartoon zombie cashier at a gas station counter under a green moon'),
    'menu/nitro': ('art', None, 'the NITRO SPIN bonus picture: a monster truck jumping past a gas station with checkered flags'),
    'menu/midnight': ('art', None, 'the MIDNIGHT RUN bonus picture: a winged emblem with a crescent moon over a gas station at night'),
    'menu/logo_chance': ('cut', 'FUEL CHANCE', 'the FUEL CHANCE bonus logo with a fuel gauge on top'),
    'menu/logo_fillup': ('cut', 'FILL UP', 'the FILL UP bonus logo with a fuel nozzle and little wings'),
    'menu/logo_premium_zombie': ('cut', 'PREMIUM', 'the PREMIUM bonus logo in dripping zombie-green letters'),
    'menu/logo_nitro': ('cut', 'NITRO SPIN', 'the NITRO SPIN bonus logo with flames'),
    'menu/logo_midnight': ('cut', 'MIDNIGHT RUN', 'the MIDNIGHT RUN bonus logo with a crescent moon and wings'),
    'fillup/backing': ('art', None, 'the FILL UP board\'s backing: a dark night-blue field with a warm orange fuel glow rising from the bottom and a few bubbles'),
    'fillup/cell': ('cut', None, 'an empty rounded-square glass cell for a fuel drop, dark inside with a warm orange bottom'),
    'fillup/gauge': ('cut', 'E F', 'a fuel gauge strip with a fuel-pump icon at the left, E and F, and three empty windows'),
}
PLATES = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp', 'nitro': 'scene/plate_nitro.webp',
          'midnight': 'scene/plate_midnight.webp'}
RATIOS = {'1:1': 1, '3:2': 1.5, '2:3': 2 / 3, '4:3': 4 / 3, '3:4': .75, '16:9': 16 / 9, '9:16': 9 / 16}


def aspect(w, h):
    return min(RATIOS, key=lambda k: abs(np.log(RATIOS[k] / (w / h))))


def style_ref():
    """The symbols, six of them on one transparent sheet: what every restyle is drawn like."""
    if os.path.exists(STYLE_REF):
        return STYLE_REF
    os.makedirs(WORK, exist_ok=True)
    src = os.path.join(ROOT, 'art', 'highpeaks', 'symbols_static')
    sheet = Image.new('RGBA', (1536, 1024))
    for i, s in enumerate(['H1', 'GP', 'L5', 'H2', 'ST', 'BS']):
        im = Image.open(os.path.join(src, s + '.png')).convert('RGBA').resize((500, 500), Image.LANCZOS)
        sheet.alpha_composite(im, ((i % 3) * 512 + 6, (i // 3) * 512 + 6))
    sheet.save(STYLE_REF)
    return STYLE_REF


def original(rel):
    keep = os.path.join(KEEP, rel + '.webp')
    if not os.path.exists(keep):
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        shutil.copyfile(os.path.join(A, rel + '.webp'), keep)
    return keep


def fit_into(new, old, cut):
    """The new picture placed where the old one sat, on a canvas of the old one's size."""
    W, H = old.size
    if not cut:
        return new.convert('RGB').resize((W, H), Image.LANCZOS)
    ob = old.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox() or (0, 0, W, H)
    nb = new.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox() or (0, 0, *new.size)
    pic = new.crop(nb)
    bw, bh = ob[2] - ob[0], ob[3] - ob[1]
    k = min(bw / pic.width, bh / pic.height)
    pic = pic.resize((max(1, round(pic.width * k)), max(1, round(pic.height * k))), Image.LANCZOS)
    out = Image.new('RGBA', (W, H))
    out.alpha_composite(pic, (ob[0] + (bw - pic.width) // 2, ob[1] + (bh - pic.height) // 2))
    return out


def restyle_ui(name):
    os.makedirs(WORK, exist_ok=True)
    kind, words, what = UI[name]
    keep = original(name)
    old = Image.open(keep).convert('RGBA')
    ref = os.path.join(WORK, name.replace('/', '_') + '_ref.png')
    old.save(ref)
    say = f' Keep the words exactly as they are: {words}.' if words else ' No words or letters on it.'
    if kind == 'cut':
        prompt = (f"Redraw the first reference image - {what} - as the same game UI piece: the same layout, outline shape "
                  f"and proportions, the same colours, {STYLE}{say} Fully transparent background, nothing else in the "
                  "picture.")
    else:
        prompt = (f"Redraw the first reference image - {what} - with the same subject, composition, framing and colours, "
                  f"{STYLE}{say} Fill the whole frame, no border.")
    job = dict(name='restyle_' + name.replace('/', '_'), prompt=prompt, aspect_ratio=aspect(*old.size),
               refs=[ref, style_ref()])
    if kind == 'cut':
        job['background'] = 'transparent'
    rec = orgen.generate(job)
    if 'error' in rec:
        print(name, 'FAILED', rec['error'][:160], flush=True)
        return False
    new = Image.open(os.path.join(ROOT, rec['file'])).convert('RGBA')
    fit_into(new, old, kind == 'cut').save(os.path.join(A, name + '.webp'), 'WEBP', quality=92, method=6)
    print(name, 'restyled', f'${rec.get("cost") or 0:.3f}', flush=True)
    return True


def restyle_plate(n):
    os.makedirs(WORK, exist_ok=True)
    src = os.path.join(SC, f'plate_{n}.png')
    keep = os.path.join(SC, f'plate_{n}.painted.png')
    if not os.path.exists(keep):
        shutil.copyfile(src, keep)
    ref = os.path.join(WORK, f'plate_{n}_ref.png')
    Image.open(keep).convert('RGB').resize((1920, 1080), Image.LANCZOS).save(ref)
    prompt = ("Redraw the first reference image - a gas station at night - as exactly the same scene: the same camera "
              "angle, the same composition, every building, sign, pump, house, tree, window, the canopy and its neon "
              f"sign, the wood and crates, the sky and the moon or clouds in the same place and at the same size, the same "
              f"colours and the same lighting mood - {STYLE} The wet forecourt keeps simple flat reflections. Keep every "
              "sign's words exactly as they are. No people, no cars.")
    rec = orgen.generate(dict(name=f'restyle_plate_{n}', prompt=prompt, aspect_ratio='16:9', size='3840x2160',
                              refs=[ref, style_ref()]))
    if 'error' in rec:
        print(n, 'FAILED', rec['error'][:160], flush=True)
        return False
    im = Image.open(os.path.join(ROOT, rec['file'])).convert('RGB').resize((3840, 2160), Image.LANCZOS)
    im.save(src)
    im.save(os.path.join(A, PLATES[n]), 'WEBP', quality=95, method=4)   # full size: compress_assets.py makes 2560 + _m
    print('plate', n, 'restyled', im.size, f'${rec.get("cost") or 0:.3f}', flush=True)
    return True


if __name__ == '__main__':
    what, names = sys.argv[1], sys.argv[2:]
    if what == 'ui':
        bad = [n for n in (names or UI) if not restyle_ui(n)]
    else:
        bad = [n for n in (names or PLATES) if not restyle_plate(n)]
    print('failed:', bad if bad else 'none')
