"""Pack the duck's Blender renders (art/highpeaks/renders/duck/<clip>/NNNN.png) into the game's sheets.

    .venv/bin/python tools/highpeaks/pack_duck.py

* the main duck's clips -> frontend/assets/duck/<clip>_<n>.webp + duck.json. Every clip is cut to ONE box (the union
  of every clip's drawn pixels, so the duck never jumps between clips), scaled to W px wide, on ones (every frame,
  24 fps: since the 2026-11-20 polish pass, for the smoother motion).
* the skiers (ski, board) -> frontend/assets/scene/duck_ski.webp / duck_board.webp + .json: a strip of 24 frames each
  (they loop as they come down the run), cut to their own box, H px tall.
"""
import json, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, 'art', 'highpeaks', 'renders', 'duck')
CLIPS = json.load(open(os.path.join(ROOT, 'art', 'highpeaks', 'blender', 'clips.json')))['clips']
OUT = os.path.join(ROOT, 'frontend', 'assets', 'duck')
SCENE = os.path.join(ROOT, 'frontend', 'assets', 'scene')
MAIN = [c for c in CLIPS if c not in ('ski', 'board')]
W, STEP, MAXW, MAXH = 300, 1, 4096, 4096
Q = 70
SKI_H = 150


def frames(clip):
    d = os.path.join(REN, clip)
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.png')]


def union_box(paths):
    box = None
    for p in paths:
        b = Image.open(p).getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
        if b:
            box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    return box


def main():
    os.makedirs(OUT, exist_ok=True)
    allp = [p for c in MAIN for p in frames(c)]
    x0, y0, x1, y1 = union_box(allp)
    pad = 6
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad
    k = W / (x1 - x0)
    w, h = W, round((y1 - y0) * k)
    cols = MAXW // w
    rows = MAXH // h
    per = cols * rows
    meta = {'fps': 24 / STEP, 'w': w, 'h': h, 'clips': {}}
    total = 0
    for c in MAIN:
        fr = frames(c)[::STEP]
        sheets = []
        for si in range(0, len(fr), per):
            chunk = fr[si:si + per]
            r = (len(chunk) + cols - 1) // cols
            sheet = Image.new('RGBA', (cols * w if len(chunk) >= cols else len(chunk) * w, r * h))
            for i, p in enumerate(chunk):
                im = Image.open(p).convert('RGBA').crop((x0, y0, x1, y1)).resize((w, h), Image.LANCZOS)
                sheet.paste(im, ((i % cols) * w, (i // cols) * h))
            name = f'{c}_{si // per}.webp'
            sheet.save(os.path.join(OUT, name), 'WEBP', quality=Q, method=6)
            total += os.path.getsize(os.path.join(OUT, name))
            sheets.append(name)
        meta['clips'][c] = {'frames': len(fr), 'cols': cols, 'per_sheet': per, 'sheets': sheets, 'loop': CLIPS[c]['loop']}
    json.dump(meta, open(os.path.join(OUT, 'duck.json'), 'w'), indent=1)
    print(f'duck: {len(meta["clips"])} clips, frame {w}x{h}, {total / 1e6:.1f} MB')

    for c in ('ski', 'board'):
        fr = frames(c)
        bx = union_box(fr)
        bx = (max(0, bx[0] - 4), max(0, bx[1] - 4), bx[2] + 4, bx[3] + 4)
        kk = SKI_H / (bx[3] - bx[1])
        fw = round((bx[2] - bx[0]) * kk)
        strip = Image.new('RGBA', (fw * len(fr), SKI_H))
        for i, p in enumerate(fr):
            im = Image.open(p).convert('RGBA').crop(bx).resize((fw, SKI_H), Image.LANCZOS)
            strip.paste(im, (i * fw, 0))
        strip.save(os.path.join(SCENE, f'duck_{c}.webp'), 'WEBP', quality=85, method=6)
        json.dump({'w': fw, 'h': SKI_H, 'frames': len(fr), 'fps': 24}, open(os.path.join(SCENE, f'duck_{c}.json'), 'w'))
        print(c, fw, 'x', SKI_H, len(fr), 'frames', os.path.getsize(os.path.join(SCENE, f'duck_{c}.webp')) // 1024, 'KB')


if __name__ == '__main__':
    main()
