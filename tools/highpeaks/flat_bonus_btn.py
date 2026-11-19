"""The BUY BONUS button, simple and flat (owner, 2026-11-13: "make the bonus icon look less like AI and more simple"):
drawn, not generated - the two pictures the page stacks for it (.bonusbtn::before / ::after):

  bonus_btn_bg.webp    a chunky cartoon key (2026-11-16, "make this look better"): thick ink outline, flat orange with a
                       lighter top, standing on a darker orange lip, a blue keyline inside, a white shine, two sparkles
  bonus_btn_text.webp  BUY (yellow) over BONUS (white) in bold Fredoka (the HUD's face), ink outline and a flat drop

Same canvas sizes as before (950 x 632, 1140 x 749), so the button lays out exactly as it did.

    .venv/bin/python tools/highpeaks/flat_bonus_btn.py
"""
import math, os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'frontend', 'assets')
FONT = os.path.join(ROOT, 'art', 'highpeaks', 'fonts', 'fredoka.ttf')
INK, ORANGE, ORANGE_HI, ORANGE_LO = (12, 12, 18, 255), (255, 122, 26, 255), (255, 158, 70, 255), (196, 74, 8, 255)
WHITE, BLUE, YELLOW = (255, 255, 255, 255), (31, 69, 184, 255), (255, 210, 60, 255)
K = 2


def font(px):
    f = ImageFont.truetype(FONT, px * K)
    try:
        f.set_variation_by_axes([700, 100])
    except Exception:
        pass
    return f


def star(d, cx, cy, r, s, fill, ink, line):
    """A four-pointed comic sparkle: ink outline, then the fill."""
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * .34
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(s(*[c for p in pts for c in p]), fill=ink)
    inner = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rr = (r - line) if i % 2 == 0 else (r - line) * .3
        inner.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(s(*[c for p in inner for c in p]), fill=fill)


def plate(W=950, H=632):
    """A chunky cartoon key (owner, 2026-11-16: "make this look better"): a face with a lighter top, standing on a
    darker orange lip (the key's depth, so it reads as something to press), a white shine on the top left, a thin
    blue keyline inside the ink (the board frame's stripe) and a sparkle on the corner."""
    im = Image.new('RGBA', (W * K, H * K))
    d = ImageDraw.Draw(im)
    s = lambda *v: [round(t * K) for t in v]
    x0, y0, x1, y1, r, L, LIP = 40, 64, W - 40, H - 112, 118, 22, 36
    d.rounded_rectangle(s(x0, y0 + LIP, x1, y1 + LIP), radius=r * K, fill=INK)                    # the lip, inked
    d.rounded_rectangle(s(x0 + L, y0 + LIP + L, x1 - L, y1 + LIP - L), radius=(r - L) * K, fill=ORANGE_LO)
    d.rounded_rectangle(s(x0, y0, x1, y1), radius=r * K, fill=INK)                                # the face
    d.rounded_rectangle(s(x0 + L, y0 + L, x1 - L, y1 - L), radius=(r - L) * K, fill=ORANGE)
    top = Image.new('RGBA', im.size)                                                             # its lighter top
    ImageDraw.Draw(top).rounded_rectangle(s(x0 + L, y0 + L, x1 - L, y1 - L), radius=(r - L) * K, fill=ORANGE_HI)
    cut = Image.new('L', im.size)
    ImageDraw.Draw(cut).rectangle(s(0, 0, W, y0 + (y1 - y0) * .46), fill=255)
    im.paste(top, (0, 0), Image.composite(top.getchannel('A'), Image.new('L', im.size), cut))
    k = 14                                                                                       # the blue keyline
    d.rounded_rectangle(s(x0 + L + k, y0 + L + k, x1 - L - k, y1 - L - k), radius=(r - L - k) * K, outline=BLUE, width=9 * K)
    d.rounded_rectangle(s(x0 + 92, y0 + 52, x0 + 300, y0 + 84), radius=16 * K, fill=WHITE)           # the shine
    d.ellipse(s(x0 + 318, y0 + 52, x0 + 350, y0 + 84), fill=WHITE)
    star(d, x1 - 26, y0 + 18, 64, s, WHITE, INK, 13)                                             # the sparkle
    star(d, x1 - 112, y0 - 18, 30, s, YELLOW, INK, 9)
    return im.resize((W, H), Image.LANCZOS)


def lettering(W=1140, H=749, top='BUY'):
    im = Image.new('RGBA', (W * K, H * K))
    d = ImageDraw.Draw(im)
    for word, size, cy, fill in ((top, 186, .30, YELLOW), ('BONUS', 262, .63, WHITE)):
        f = font(size)
        sw = 24 * K
        bb = d.textbbox((0, 0), word, font=f, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x, y = W * K / 2 - tw / 2 - bb[0], cy * H * K - th / 2 - bb[1]
        d.text((x, y + 16 * K), word, font=f, fill=INK, stroke_width=sw, stroke_fill=INK)   # flat drop, straight down
        d.text((x, y), word, font=f, fill=fill, stroke_width=sw, stroke_fill=INK)
    return im.resize((W, H), Image.LANCZOS)


if __name__ == '__main__':
    plate().save(os.path.join(A, 'bonus_btn_bg.webp'), 'WEBP', quality=92, method=6)
    lettering().save(os.path.join(A, 'bonus_btn_text.webp'), 'WEBP', quality=92, method=6)
    # social mode (Stake.US) may not say BUY: GET BONUS (approval guideline [77])
    lettering(top='GET').save(os.path.join(A, 'bonus_btn_text_social.webp'), 'WEBP', quality=92, method=6)
    print('BUY BONUS drawn')
