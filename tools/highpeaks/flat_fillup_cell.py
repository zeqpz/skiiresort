"""FILL UP's fuel window, flat (owner, 2026-11-13: "on our bonus get rid of the realistic lighting on the metal"):
drawn, not generated - a rounded cell with an ink outline, a navy inside, a thin blue inner line and a flat orange
fuel band along its foot. No chrome, no glass reflections, no glow. The page nine-slices it into every FILL UP cell
(paintTiles: tileArt.cell), so its corners keep their shape in a tall cell.

    .venv/bin/python tools/highpeaks/flat_fillup_cell.py      -> frontend/assets/fillup/cell.webp (384 x 382)
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'frontend', 'assets', 'fillup', 'cell.webp')
W, H, K = 384, 382, 4
INK, NAVY, BLUE, ORANGE, ORANGE_DK = (12, 12, 18, 255), (20, 36, 94, 255), (47, 107, 255, 255), (255, 122, 26, 255), (217, 83, 10, 255)
im = Image.new('RGBA', (W * K, H * K))
d = ImageDraw.Draw(im)
s = lambda *v: [round(t * K) for t in v]
R, L = 58, 14
d.rounded_rectangle(s(2, 2, W - 3, H - 3), radius=R * K, fill=INK)
d.rounded_rectangle(s(2 + L, 2 + L, W - 3 - L, H - 3 - L), radius=(R - L) * K, fill=NAVY)
# the fuel band along the foot: flat orange with one darker flat tone under it, clipped to the cell's inside
band = Image.new('RGBA', im.size)
bd = ImageDraw.Draw(band)
bd.rectangle(s(0, H * .78, W, H), fill=ORANGE_DK)
bd.rectangle(s(0, H * .74, W, H * .86), fill=ORANGE)
mask = Image.new('L', im.size)
ImageDraw.Draw(mask).rounded_rectangle(s(2 + L, 2 + L, W - 3 - L, H - 3 - L), radius=(R - L) * K, fill=255)
im.paste(band, (0, 0), Image.composite(band.getchannel('A'), Image.new('L', im.size), mask))
d.line(s(2 + L, H * .74, W - 3 - L, H * .74), fill=INK, width=5 * K)
# a thin blue line just inside the ink
d.rounded_rectangle(s(2 + L + 7, 2 + L + 7, W - 3 - L - 7, H - 3 - L - 7), radius=(R - L - 7) * K, outline=BLUE, width=4 * K)
im.resize((W, H), Image.LANCZOS).save(OUT, 'WEBP', quality=92, method=6)
print('fillup cell drawn', (W, H))
