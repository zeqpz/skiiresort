"""The board's frame, flat and simple (owner, 2026-11-13: "the falcos outline for our board still doesnt look appealing
it should be simple and dont make it a neon sign outline"). Drawn, not generated, so its geometry is exact:

  * one rounded band round the glass: thick ink outline outside and in, an orange band, a thin blue stripe on its
    inner edge - flat colours, no light, no gloss (the symbols' and the HUD's look)
  * on top, centred, a simple badge: FALCOS in bold Fredoka (the HUD's face), orange with an ink outline, on a blue
    plate with an ink outline - sitting ON the band and rising above it, never reaching into the glass

    .venv/bin/python tools/highpeaks/flat_frame.py        -> art/highpeaks/raw/board_frame_flat_{sq,wide}.png
    .venv/bin/python tools/highpeaks/compress_assets.py   -> frame_sq / frame_wide .webp + .json (then the page's --fo-*)

Two shapes of glass, as before: 1.283:1 (frame_sq, the upright phone board) and 1.4749:1 (frame_wide, landscape).
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
FONT = os.path.join(ROOT, 'art', 'highpeaks', 'fonts', 'fredoka.ttf')     # unpacked from frontend/assets/fredoka.woff2
INK, ORANGE, ORANGE_SH, BLUE, WHITE = (12, 12, 18, 255), (255, 122, 26, 255), (217, 83, 10, 255), (31, 69, 184, 255), (255, 255, 255, 255)
SHAPES = {'sq': 1.283, 'wide': 1.4749}
OW = 2000                     # the glass opening's width, px
BAND, LINE, STRIPE = 64, 9, 14
R_IN = 70                     # the glass's corner radius
K = 2                         # drawn at 2x, shrunk: smooth edges


def frame(aspect):
    ow, oh = OW, round(OW / aspect)
    badge_h = 230
    top_pad = badge_h - BAND // 2                                 # room above the band for the badge
    W = ow + 2 * (BAND + LINE)
    H = oh + 2 * (BAND + LINE) + top_pad
    im = Image.new('RGBA', (W * K, H * K))
    d = ImageDraw.Draw(im)
    x0, y0 = 0, top_pad                                           # the frame's outer box
    x1, y1 = W, H
    s = lambda *v: [round(t * K) for t in v]
    r_out = R_IN + BAND + LINE
    # outside in: ink, orange band, its lower half a touch darker (one flat shadow tone), blue stripe, ink, glass
    d.rounded_rectangle(s(x0, y0, x1 - 1, y1 - 1), radius=r_out * K, fill=INK)
    d.rounded_rectangle(s(x0 + LINE, y0 + LINE, x1 - 1 - LINE, y1 - 1 - LINE), radius=(r_out - LINE) * K, fill=ORANGE)
    inner = (x0 + LINE + BAND, y0 + LINE + BAND, x1 - 1 - LINE - BAND, y1 - 1 - LINE - BAND)
    d.rounded_rectangle(s(inner[0] - STRIPE - LINE // 2, inner[1] - STRIPE - LINE // 2, inner[2] + STRIPE + LINE // 2,
                          inner[3] + STRIPE + LINE // 2), radius=(R_IN + STRIPE) * K, fill=INK)
    d.rounded_rectangle(s(inner[0] - STRIPE, inner[1] - STRIPE, inner[2] + STRIPE, inner[3] + STRIPE), radius=(R_IN + STRIPE) * K, fill=BLUE)
    d.rounded_rectangle(s(inner[0] - LINE // 2, inner[1] - LINE // 2, inner[2] + LINE // 2, inner[3] + LINE // 2), radius=(R_IN + 4) * K, fill=INK)
    d.rounded_rectangle(s(*inner), radius=R_IN * K, fill=(0, 0, 0, 0))
    # the badge
    font = ImageFont.truetype(FONT, 150 * K)
    try:
        font.set_variation_by_axes([700, 100])
    except Exception:
        pass
    text = 'FALCOS'
    tb = d.textbbox((0, 0), text, font=font, stroke_width=12 * K)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    pw, ph = tw / K + 120, badge_h - 20
    cx = W / 2
    bx0, by0 = cx - pw / 2, 10
    bx1, by1 = cx + pw / 2, 10 + ph
    d.rounded_rectangle(s(bx0, by0 + 10, bx1, by1 + 10), radius=46 * K, fill=INK)        # its flat shadow
    d.rounded_rectangle(s(bx0, by0, bx1, by1), radius=46 * K, fill=INK)
    d.rounded_rectangle(s(bx0 + LINE, by0 + LINE, bx1 - LINE, by1 - LINE), radius=(46 - LINE) * K, fill=BLUE)
    d.rounded_rectangle(s(bx0 + LINE + 10, by0 + LINE + 10, bx1 - LINE - 10, by1 - LINE - 10), radius=(36 - LINE) * K,
                        outline=(255, 255, 255, 110), width=4 * K)
    tx, ty = cx * K - tw / 2 - tb[0], (by0 + by1) / 2 * K - th / 2 - tb[1]
    d.text((tx + 8 * K, ty + 9 * K), text, font=font, fill=INK, stroke_width=12 * K, stroke_fill=INK)    # drop
    d.text((tx, ty), text, font=font, fill=ORANGE, stroke_width=12 * K, stroke_fill=INK)
    return im.resize((W, H), Image.LANCZOS)


if __name__ == '__main__':
    os.makedirs(RAW, exist_ok=True)
    for name, aspect in SHAPES.items():
        im = frame(aspect)
        im.save(os.path.join(RAW, f'board_frame_flat_{name}.png'))
        print(name, im.size)
