"""The win numerals, flat (owner, 2026-11-13: "change any realistic / shaded graphics like the win hud").

    .venv/bin/python tools/highpeaks/flat_numerals.py

frontend/assets/num/<0-9, comma, dot, x>.webp redrawn as flat cartoon figures to match the symbols: a white face,
a thick black outline and a flat orange drop shadow (outlined too), in a rounded bold face. Each is fitted into the
old numeral's solid part on a canvas of the old numeral's size, so the win amounts lay out exactly as before. The
glossy originals are kept in art/highpeaks/ui_glossy/num/ (restyle.py keeps the rest of the UI there).
"""
import os, shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NUM = os.path.join(ROOT, 'frontend', 'assets', 'num')
KEEP = os.path.join(ROOT, 'art', 'highpeaks', 'ui_glossy', 'num')
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'
GLYPH = {**{str(d): str(d) for d in range(10)}, 'comma': ',', 'dot': '.', 'x': 'x'}
FACE, INK, SHADOW = (255, 255, 255, 255), (12, 12, 18, 255), (255, 122, 26, 255)
S = 4                     # drawn at 4x, then shrunk: smooth edges


def figure(ch):
    size = 300 * S
    font = ImageFont.truetype(FONT, size)
    pad, stroke, shift = 60 * S, 15 * S, (26 * S, 30 * S)
    w, h = size + 2 * pad, int(size * 1.35) + 2 * pad
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    at = (pad + 10 * S, pad)
    d.text((at[0] + shift[0], at[1] + shift[1]), ch, font=font, fill=SHADOW, stroke_width=stroke, stroke_fill=INK)
    d.text(at, ch, font=font, fill=FACE, stroke_width=stroke, stroke_fill=INK)
    return im.crop(im.getchannel('A').getbbox())


os.makedirs(KEEP, exist_ok=True)
for name, ch in GLYPH.items():
    p, k = os.path.join(NUM, name + '.webp'), os.path.join(KEEP, name + '.webp')
    if not os.path.exists(k):
        shutil.copyfile(p, k)
    old = Image.open(k).convert('RGBA')
    ob = old.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()
    pic = figure(ch)
    bw, bh = ob[2] - ob[0], ob[3] - ob[1]
    # the digits fill the old height (a figure row reads at one height); a comma / dot / x fits its own box
    kk = bh / pic.height if name.isdigit() else min(bw / pic.width, bh / pic.height)
    pic = pic.resize((max(1, round(pic.width * kk)), max(1, round(pic.height * kk))), Image.LANCZOS)
    out = Image.new('RGBA', old.size)
    x = ob[0] + (bw - pic.width) // 2
    out.alpha_composite(pic, (max(0, min(old.width - pic.width, x)), ob[1] + (bh - pic.height) // 2))
    out.save(p, 'WEBP', quality=92, method=6)
    print(name, old.size)
