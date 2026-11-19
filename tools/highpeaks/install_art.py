"""Install the generated High Peaks art (art/highpeaks/raw/*.png) into frontend/assets at the sizes the game reads.

    .venv/bin/python tools/highpeaks/install_art.py [plates] [ui] [syms]

plates  the scene plates (base / FRESH POWDER / BLACK DIAMOND / AVALANCHE), the snow-cloud strip, and the old gas-station
        sign overlays (sign patches, flicker letters) blanked to transparent - the lodge has no neon to flicker
ui      the bonus-buy card art and logos, the loading screen's three cards and titles, the jackpot plaques, the game logo
syms    the symbols: art/highpeaks/symbols_static/<ID>.png (cut from raw), then tools/highpeaks/static_symbols.py builds
        the board's sheets and the flat icons
"""
import os, subprocess, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
A = os.path.join(ROOT, 'frontend', 'assets')


def raw(name):
    return Image.open(os.path.join(RAW, name + '.png'))


def save(im, rel, q=86):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p, 'WEBP', quality=q, method=6)


def cover(im, w, h):
    """Scale and centre-crop to exactly w x h."""
    k = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def fit_alpha(im, w, h):
    """A transparent picture trimmed to its content and fitted inside w x h (aspect kept, centred)."""
    im = im.convert('RGBA')
    bb = im.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox()
    if bb:
        im = im.crop(bb)
    k = min(w / im.width, h / im.height)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    out = Image.new('RGBA', (w, h))
    out.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out


def blank(rel):
    p = os.path.join(A, rel)
    w, h = Image.open(p).size
    Image.new('RGBA', (w, h)).save(p, 'WEBP', lossless=True)


def plates():
    for src, dst in (('plate_base', 'bonus_wall'), ('plate_premium', 'scene/plate_zombie'),
                     ('plate_midnight', 'scene/plate_midnight'), ('plate_nitro', 'scene/plate_nitro')):
        im = raw(src).convert('RGB')
        save(cover(im, 2560, 1440), dst + '.webp', 84)
        save(cover(im, 1600, 900), dst + '_m.webp', 82)
    c = raw('clouds_snow').convert('RGBA')
    bb = c.getchannel('A').getbbox()
    c = c.crop((0, bb[1], c.width, bb[3]))
    save(cover(c, 2048, 384), 'scene/clouds_zombie.webp')
    for f in os.listdir(os.path.join(A, 'scene')):
        if f.startswith(('signpatch_', 'sign_off', 'zsign_off')):
            blank(os.path.join('scene', f))


UI = {   # raw name: (asset, w, h, kind)
    'menu_chance': ('menu/chance.webp', 640, 363, 'cover'),
    'menu_nitro': ('menu/nitro.webp', 427, 640, 'cover'),
    'menu_fillup': ('menu/fillup.webp', 427, 640, 'cover'),
    'menu_premium': ('menu/premium.webp', 427, 640, 'cover'),
    'menu_midnight': ('menu/midnight.webp', 427, 640, 'cover'),
    'load_features': ('load/features.webp', 427, 640, 'cover'),
    'load_bonus': ('load/bonus.webp', 427, 640, 'cover'),
    'load_max': ('load/max.webp', 427, 640, 'cover'),
    'logo_chance': ('menu/logo_chance.webp', 600, 216, 'alpha'),
    'logo_fillup': ('menu/logo_fillup.webp', 600, 224, 'alpha'),
    'logo_premium': ('menu/logo_premium_zombie.webp', 600, 202, 'alpha'),
    'logo_nitro': ('menu/logo_nitro.webp', 600, 194, 'alpha'),
    'logo_midnight': ('menu/logo_midnight.webp', 600, 172, 'alpha'),
    'title_features': ('load/title_features.webp', 560, 285, 'alpha'),
    'title_bonus': ('load/title_bonus.webp', 560, 315, 'alpha'),
    'title_max': ('load/title_max.webp', 560, 318, 'alpha'),
    'logo_game': ('logo.webp', 1200, 400, 'alpha'),
    'jp_mini': ('jackpot/mini.webp', 480, 160, 'alpha'),
    'jp_minor': ('jackpot/minor.webp', 480, 160, 'alpha'),
    'jp_major': ('jackpot/major.webp', 480, 160, 'alpha'),
    'jp_grand': ('jackpot/grand.webp', 480, 160, 'alpha'),
}


def ui():
    for name, (dst, w, h, kind) in UI.items():
        if not os.path.exists(os.path.join(RAW, name + '.png')):
            print('missing', name); continue
        im = raw(name)
        save(cover(im.convert('RGB'), w, h) if kind == 'cover' else fit_alpha(im, w, h), dst)


SYM_IDS = 'H1 H2 H3 H4 L1 L2 L3 L4 L5 ZP ST GT GP FDG FDA FDR BS DS'.split()


def syms():
    out = os.path.join(ROOT, 'art', 'highpeaks', 'symbols_static')
    os.makedirs(out, exist_ok=True)
    for sid in SYM_IDS + ['JP']:
        src = 'sym_H1_bong' if sid == 'H1' else 'sym_' + sid
        if not os.path.exists(os.path.join(RAW, src + '.png')):
            print('missing', src); continue
        fit_alpha(raw(src), 1024, 1024).save(os.path.join(out, sid + '.png'))
    fit_alpha(raw('sym_JP'), 320, 320).save(os.path.join(A, 'jackpot', 'q.webp'), 'WEBP', quality=90)
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'highpeaks', 'static_symbols.py'), *SYM_IDS], check=True)


if __name__ == '__main__':
    what = sys.argv[1:] or ['plates', 'ui', 'syms']
    os.makedirs(os.path.join(A, 'jackpot'), exist_ok=True)
    for w in what:
        globals()[w]()
        print('installed', w)
