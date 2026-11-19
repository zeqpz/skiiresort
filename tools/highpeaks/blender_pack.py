"""Pack the Blender renders into the game's symbol sheets (after tools/highpeaks/blender/flatanim.py, 2026-11-13).

    .venv/bin/python tools/highpeaks/blender_pack.py [IDS...]
    .venv/bin/python tools/highpeaks/align_clips.py && .venv/bin/python tools/highpeaks/centre_symbols.py
    .venv/bin/python tools/highpeaks/compress_assets.py

art/highpeaks/renders/flat/<ID>/<clip>/NNNN.png (+ clip.json: frames, fps, box in icon units, px a unit) become
frontend/assets/sym/d<density>/<ID>_<clip>.webp grids at every density the manifest lists (each frame resampled from
the 2x render), and the symbol's manifest entry gets the clips (frames, fps, loop, box) and the sheets - the format
the board canvas (boardgl.js) and the page's fallback already play. The idle loops; the rest play once.

    .venv/bin/python tools/highpeaks/blender_pack.py --fx       the effects (tools/highpeaks/blender/flatfx.py)
art/highpeaks/renders/flat/_fx/<name>/ become frontend/assets/fx/<name>.webp (a grid of frames at FX_SIZE) + <name>.json
(frames, fps, cols, w, h) for the page's spriteFx player.
"""
import io, json, math, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, 'art', 'highpeaks', 'renders', 'flat')
SYM = os.path.join(ROOT, 'frontend', 'assets', 'sym')
CLIPS = ('land', 'idle', 'hit', 'burn')

FX_SIZE = {'winburst': (640, 360)}   # (the fire / firecell sprites: retired 2026-11-13, the simple CSS fire is back)
if '--fx' in sys.argv:
    FXD = os.path.join(ROOT, 'frontend', 'assets', 'fx')
    os.makedirs(FXD, exist_ok=True)
    for name, (w, h) in FX_SIZE.items():
        d = os.path.join(REN, '_fx', name)
        meta = json.load(open(os.path.join(d, 'clip.json')))
        fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
        cols = max(1, min(len(fs), 4096 // w))
        sheet = Image.new('RGBA', (cols * w, math.ceil(len(fs) / cols) * h))
        for i, f in enumerate(fs):
            sheet.alpha_composite(Image.open(os.path.join(d, f)).convert('RGBA').resize((w, h), Image.LANCZOS), ((i % cols) * w, (i // cols) * h))
        sheet.save(os.path.join(FXD, name + '.webp'), 'WEBP', quality=86, method=6, alpha_quality=92)
        json.dump({'frames': len(fs), 'fps': meta['fps'], 'cols': cols, 'w': w, 'h': h}, open(os.path.join(FXD, name + '.json'), 'w'))
        print('fx', name, sheet.size, len(fs), 'frames')
    sys.exit(0)
man = json.load(open(os.path.join(SYM, 'manifest.json')))
ids = sys.argv[1:] or sorted(d for d in os.listdir(REN) if os.path.isdir(os.path.join(REN, d)) and not d.startswith('_'))
for sid in ids:
    e = {'icon': [10.0, 10.0], 'clips': {}, 'sheets': {}}
    frames = {}
    for clip in CLIPS:
        d = os.path.join(REN, sid, clip)
        meta = json.load(open(os.path.join(d, 'clip.json')))
        fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
        assert len(fs) == meta['frames'], (sid, clip, len(fs))
        frames[clip] = [Image.open(os.path.join(d, f)).convert('RGBA') for f in fs]
        fps = meta['fps']
        if clip == 'idle':                       # (2026-11-13, lag) the idle plays at .575 speed: every other frame,
            frames[clip] = frames[clip][::2]     # at half the rate, is the same motion in half the sheet
            fps = fps / 2
        e['clips'][clip] = {'frames': len(frames[clip]), 'fps': fps, 'loop': clip == 'idle', 'box': meta['box']}
    for dens in man['densities']:
        dk = 'd%d' % round(dens * 10)
        e['sheets'][dk] = {}
        for clip in CLIPS:
            box = e['clips'][clip]['box'][2]
            size = round(box * 10 * dens)          # sheet px a frame: box units x 10 x density (d16: 16 px a unit)
            n = len(frames[clip])
            cols = max(1, min(n, 4096 // size))
            sheet = Image.new('RGBA', (cols * size, math.ceil(n / cols) * size))
            for i, im in enumerate(frames[clip]):
                sheet.alpha_composite(im.resize((size, size), Image.LANCZOS), ((i % cols) * size, (i // cols) * size))
            buf = io.BytesIO()
            sheet.save(buf, 'WEBP', quality=88, method=6, alpha_quality=95)
            open(os.path.join(SYM, dk, f'{sid}_{clip}.webp'), 'wb').write(buf.getvalue())
            e['sheets'][dk][clip] = {'w': size, 'h': size, 'cols': cols, 'bytes': len(buf.getvalue())}
    man['symbols'][sid] = e
    print(sid, ', '.join(f'{d} {v["idle"]["w"]}/{v["burn"]["w"]}px' for d, v in e['sheets'].items()), flush=True)
json.dump(man, open(os.path.join(SYM, 'manifest.json'), 'w'), separators=(',', ':'))
