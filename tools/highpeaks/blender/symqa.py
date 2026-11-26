"""QA contact sheets for the rigged symbol renders (tools/highpeaks/blender/symrig.py).

    python tools/highpeaks/blender/symqa.py OUT_DIR [IDS...] [--cell 150] [--every 1]

For each symbol: one PNG, a row per clip (land, idle, hit, burn), every frame on a dark tile with the clip's box
drawn, and a red edge on any frame whose picture touches the box (it would be cut off on the board). Prints, per
clip: frames touching the edge, whether the last frame of land / idle / hit equals the rest pose (land's last
frame), whether the first frame of hit / burn does (they cut in on it), and whether burn's last frame is empty.
"""
import json, os, sys
from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REN = os.path.join(ROOT, 'art', 'highpeaks', 'renders', 'flat')
CLIPS = ('land', 'idle', 'hit', 'burn')
args = sys.argv[1:]
cell = int(args.pop(args.index('--cell') + 1)) if '--cell' in args else 150
every = int(args.pop(args.index('--every') + 1)) if '--every' in args else 1
args = [a for a in args if not a.startswith('--')]
out, ids = args[0], args[1:] or sorted(d for d in os.listdir(REN) if os.path.isdir(os.path.join(REN, d)) and not d.startswith('_'))
os.makedirs(out, exist_ok=True)


def frames(sid, clip):
    d = os.path.join(REN, sid, clip)
    return [Image.open(os.path.join(d, f)).convert('RGBA') for f in sorted(os.listdir(d)) if f.endswith('.png')], json.load(open(os.path.join(d, 'clip.json')))


def edge(im, tol=24):
    a = im.getchannel('A'); w, h = a.size; m = 2
    strips = [a.crop((0, 0, w, m)), a.crop((0, h - m, w, h)), a.crop((0, 0, m, h)), a.crop((w - m, 0, w, h))]
    return max(s.getextrema()[1] for s in strips) > tol


for sid in ids:
    rows, report = [], []
    rest = None
    for clip in CLIPS:
        fr, meta = frames(sid, clip)
        if clip == 'land':
            rest = fr[-1]
        touching = [i for i, im in enumerate(fr) if edge(im)]
        note = f'{clip}: {len(fr)}f box {meta["box"][2]}'
        if touching:
            note += f' EDGE at {touching}'
        if clip in ('idle', 'hit') and rest is not None:
            a, b = fr[-1], rest
            if a.size != b.size:                                  # a bigger box: compare the centre
                o = (a.size[0] - b.size[0]) // 2
                a = a.crop((o, o, o + b.size[0], o + b.size[1])) if o > 0 else a
            diff = ImageChops.difference(a.convert('RGBA'), b.convert('RGBA')).getextrema()
            worst = max(hi for _lo, hi in diff)
            note += f' | end-vs-rest max diff {worst}'
        if clip in ('hit', 'burn') and rest is not None:          # a clip cuts in on the rest pose: its first frame must be it
            a, b = fr[0], rest
            o = (a.size[0] - b.size[0]) // 2
            a = a.crop((o, o, o + b.size[0], o + b.size[1])) if o > 0 else a
            note += f' | start-vs-rest max diff {max(hi for _lo, hi in ImageChops.difference(a, b).getextrema())}'
        if clip == 'burn':
            note += f' | last frame alpha max {fr[-1].getchannel("A").getextrema()[1]}'
        report.append(note)
        scale = cell / fr[0].size[0] * (meta['box'][2] / 12)       # one scale for every clip: a unit is a unit
        tiles = []
        for i, im in enumerate(fr):
            if i % every and i != len(fr) - 1:
                continue
            s = max(8, round(im.size[0] * scale))
            t = Image.new('RGBA', (s, s), (34, 44, 70, 255))
            t.alpha_composite(im.resize((s, s), Image.LANCZOS))
            d = ImageDraw.Draw(t)
            d.rectangle([0, 0, s - 1, s - 1], outline=(255, 60, 60, 255) if i in touching else (90, 100, 130, 255))
            d.text((3, 2), str(i), fill=(255, 255, 0, 255))
            tiles.append(t)
        rows.append(tiles)
    W = max(sum(t.size[0] for t in r) for r in rows)
    H = sum(r[0].size[1] for r in rows)
    sheet = Image.new('RGB', (W, H), (16, 20, 34))
    y = 0
    for r in rows:
        x = 0
        for t in r:
            sheet.paste(t.convert('RGB'), (x, y)); x += t.size[0]
        y += r[0].size[1]
    sheet.save(os.path.join(out, sid + '.png'))
    print(sid, ' || '.join(report))
