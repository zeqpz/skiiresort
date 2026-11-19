"""Shrink the Falcos front end's assets (frontend/assets) for download and decode - re-run after any install.

  .venv/bin/python tools/highpeaks/compress_assets.py [--dry] [--force] [--jobs N]

What it does (each step skips files it already wrote - tools/highpeaks/compress_state.json keeps the hash of
every output, so a re-run only touches newly installed art and never re-encodes its own output twice):

  1. sound masters  - frontend/assets/*.wav move to art/highpeaks/sfx_masters/ (the game plays the .ogg/.aac)
  2. unused art     - files nothing in the front end names (PRUNE) are removed
  3. symbol sheets  - the d24 density is dropped (d16 is sharp at DPR 2: the board canvas draws at <= 2x);
                      d10/d12/d16 re-encoded at SYM_Q / SYM_AQ; manifest.json updated (densities, bytes)
  4a. scene loops  - fx_woman / fx_cashier cropped to what they show (cashier at half size, 15 fps): ~270 MB
                      of decoded frames -> ~30 MB (scene.json updated; marked "packed": 2)
  4. scene plates   - the 3840x2160 plates become 2560 wide, plus a <name>_m.webp 1600 wide variant that
                      the stylesheet picks on phones / small windows (index.html: --wall-img, PLATES)
  5. everything else (never the HUD's own art: HUD) - downscaled to MAX_SIDE (2x the largest size it is ever drawn at 1600x900; the
                      app is scaled to fit, so this is 1600x900 at DPR 2 / 3200x1800 at DPR 1) and
                      re-encoded as lossy WebP (alpha kept where the picture has any)
  6. the board frame - art/highpeaks/raw/board_frame_flat_sq.png (flat_frame.py) trimmed to frame_sq.webp and its
                      glass opening measured into frame_sq.json; otherwise frame_sq is built from
                      board_frame_v3.png's slim bezel + topper at the board's squarer shape
                      + frame_wide.webp/json from board_frame_flat_wide.png, for landscape
  7. FILL UP art    - art/highpeaks/raw/fillup_{backing,cell2,gauge}.png (when they exist) -> assets/fillup/
"""
import hashlib, io, json, os, shutil, sys
from concurrent.futures import ProcessPoolExecutor
from PIL import Image
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = os.path.join(ROOT, 'frontend', 'assets')
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'raw')
MASTERS = os.path.join(ROOT, 'art', 'highpeaks', 'sfx_masters')
STATE = os.path.join(ROOT, 'tools', 'highpeaks', 'compress_state.json')
DRY = '--dry' in sys.argv
FORCE = '--force' in sys.argv
JOBS = int(next((a.split('=')[1] for a in sys.argv if a.startswith('--jobs=')), os.cpu_count() or 4))

Q, AQ = 80, 85                 # UI art
SYM_Q, SYM_AQ = 78, 80         # symbol sheets (checked at 3x zoom: no visible change; aq < 75 rings the glow)
PLATE_Q = 78
DROP_DENSITIES = ['d24']   # d16 is back, with d20 (owner, 2026-11-16: "why does the symbol look so blurry"): d12 was soft on a full screen and in the bonus
PLATES = ['bonus_wall.webp', 'scene/plate_nitro.webp', 'scene/plate_zombie.webp', 'scene/plate_midnight.webp']
PLATE_W, PLATE_W_M = 2560, 1600
FRAME_MAX = 1600               # the board frame is drawn ~700-1100 px wide
FRAME_WIDE_MAX = 1800          # the landscape frame, up to ~950 px wide at 1600x900 (DPR 2)
# never named by the front end (checked 2026-11-10); install_game.py copies some of them back
PRUNE = ['frame.webp', 'xbonus_text.webp', 'win_box.webp', 'feature_box.webp', 'logo_premium.webp',
         'logo_fillup.webp', 'menu/logo_premium.webp', 'bonus', 'frame_75.webp', 'frame_75.json', 'plate_grey.webp']
# longest side allowed (px) - 2x the most it is drawn at 1600x900 (measured in the page); default DEFAULT_MAX
DEFAULT_MAX = 1600
MAX_SIDE = {
    'title_logo.webp': 720, 'bonus_panel.webp': 1800, 'info_panel.webp': 1800, 'tier_bg.webp': 1600,
    'big_win.webp': 1400, 'mega_win.webp': 1400, 'xtreme_win.webp': 1400, 'total_win.webp': 1400,
    'total_bg.webp': 1400, 'banner_box.webp': 1200,
    'intro_letters/glow.webp': 2000, 'intro_letters/swash.webp': 1600, 'intro_letters/': 640,
    'load/bar_frame.webp': 1260, 'load/bar_fill.webp': 900, 'load/card_frame.webp': 900,
    'load/bonus.webp': 640, 'load/features.webp': 640, 'load/max.webp': 640, 'load/title_': 560,
    'menu/logo_': 600, 'menu/': 640,
    'num/': 240, 'flat/': 320, 'frame_sq.webp': 1600, 'fillup/': 1400,
}
# the HUD (bottom bar, its buttons and icons, the Buy Bonus button) is never touched (owner rule)
HUD = ('hud_', 'icon_', 'bet_', 'skip_btn', 'spin_plate', 'spin_btn_arrows', 'ui_box', 'bonus_btn_', 'fx/')   # fx/: the Blender effect sheets keep their frame size (blender_pack.py --fx)
# drawn as they are (scene overlays are placed in plate px by scene.json)
KEEP_SIZE = ('scene/', 'intro_letters/tm')


def sha(path):
    with open(path, 'rb') as fh:
        return hashlib.sha1(fh.read()).hexdigest()


state = {}
if os.path.exists(STATE) and not FORCE:
    state = json.load(open(STATE))


def done(rel):
    p = os.path.join(F, rel)
    return os.path.exists(p) and state.get(rel) == sha(p)


def mark(rel):
    state[rel] = sha(os.path.join(F, rel))


def encode(im, path, q, aq):
    """Lossy WebP; alpha only if the picture uses it. Returns the bytes written (or that would be)."""
    has_alpha = im.mode in ('RGBA', 'LA', 'P') and im.convert('RGBA').getchannel('A').getextrema()[0] < 255
    im = im.convert('RGBA' if has_alpha else 'RGB')
    b = io.BytesIO()
    im.save(b, 'WEBP', quality=q, method=6, alpha_quality=aq)
    data = b.getvalue()
    if not DRY:
        with open(path, 'wb') as fh:
            fh.write(data)
    return len(data)


def shrink_one(args):
    rel, maxside, q, aq = args
    p = os.path.join(F, rel)
    before = os.path.getsize(p)
    im = Image.open(p)
    im.load()
    if maxside and max(im.size) > maxside:
        k = maxside / max(im.size)
        im = im.convert('RGBA').resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    tmp = p + '.tmp'
    after = encode(im, tmp, q, aq)
    if DRY:
        return rel, before, after, im.size
    if after < before or maxside:   # never keep a bigger file unless it was downscaled
        os.replace(tmp, p)
    else:
        os.remove(tmp); after = before
    return rel, before, after, im.size


def step_masters():
    wavs = [n for n in os.listdir(F) if n.endswith('.wav')]
    if not wavs:
        return
    os.makedirs(MASTERS, exist_ok=True)
    total = 0
    for n in wavs:
        total += os.path.getsize(os.path.join(F, n))
        if not DRY:
            shutil.move(os.path.join(F, n), os.path.join(MASTERS, n))
    print(f'masters: {len(wavs)} .wav ({total / 1e6:.1f} MB) -> art/highpeaks/sfx_masters/')


def step_prune():
    for rel in PRUNE:
        p = os.path.join(F, rel)
        if os.path.isdir(p):
            print('prune', rel + '/'); DRY or shutil.rmtree(p)
        elif os.path.exists(p):
            print('prune', rel); DRY or os.remove(p)
        state.pop(rel, None)


def step_symbols(pool):
    sym = os.path.join(F, 'sym')
    man_p = os.path.join(sym, 'manifest.json')
    if not os.path.exists(man_p):
        return
    man = json.load(open(man_p))
    for d in DROP_DENSITIES:
        if os.path.isdir(os.path.join(sym, d)):
            print('drop density', d); DRY or shutil.rmtree(os.path.join(sym, d))
        for s in man['symbols'].values():
            s['sheets'].pop(d, None)
        dv = int(d[1:]) / 10
        man['densities'] = [x for x in man['densities'] if abs(x - dv) > 1e-6]
    jobs = []
    for d in sorted(os.listdir(sym)):
        if not os.path.isdir(os.path.join(sym, d)):
            continue
        for n in sorted(os.listdir(os.path.join(sym, d))):
            rel = f'sym/{d}/{n}'
            if n.endswith('.webp') and not done(rel):
                jobs.append((rel, 0, SYM_Q, SYM_AQ))
    b0 = b1 = 0
    for rel, before, after, _ in pool.map(shrink_one, jobs):
        b0 += before; b1 += after
        if not DRY:
            mark(rel)
            _, d, n = rel.split('/')
            sid, clip = n[:-5].rsplit('_', 1)
            sh = man['symbols'].get(sid, {}).get('sheets', {}).get(d, {}).get(clip)
            if sh is not None:
                sh['bytes'] = after
    if jobs:
        print(f'symbols: {len(jobs)} sheets {b0 / 1e6:.1f} -> {b1 / 1e6:.1f} MB')
    if not DRY:
        json.dump(man, open(man_p, 'w'), separators=(',', ':'))


def step_plates(pool):
    jobs = []
    for rel in PLATES:
        p = os.path.join(F, rel)
        if not os.path.exists(p):
            continue
        m = rel[:-5] + '_m.webp'
        if done(rel) and done(m):
            continue
        im = Image.open(p).convert('RGB')
        b0 = os.path.getsize(p)
        if im.width < PLATE_W and os.path.exists(os.path.join(F, m)):
            continue
        big = im.resize((PLATE_W, round(im.height * PLATE_W / im.width)), Image.LANCZOS) if im.width > PLATE_W else im
        small = im.resize((PLATE_W_M, round(im.height * PLATE_W_M / im.width)), Image.LANCZOS)
        a = encode(big, p, PLATE_Q, 100)
        b = encode(small, os.path.join(F, m), PLATE_Q, 100)
        print(f'plate {rel}: {b0 / 1e3:.0f}K -> {a / 1e3:.0f}K (+ _m {b / 1e3:.0f}K)')
        if not DRY:
            mark(rel); mark(m)


# The scene's Blender loops (scenefx.js) held every frame decoded: fx_woman 300x340 x 240 and fx_cashier
# 480x370 x 240 = ~270 MB of pixels, more than a phone's decoded-image cache, so the browser kept throwing the
# sheets away and decoding them again (200-340 ms main-thread stalls every 1-3 s at 4x CPU, measured 2026-11-10).
# Repacked: each loop cropped to what any of its frames ever shows (the rect in scene.json moves with it), the
# glints and glass reflection at half size and 15 fps (FX_SCALE / FX_STEP), on as few sheets as fit 4096 px.
FX_SCALE = {'fx_cashier': .5}
FX_STEP = {'fx_cashier': 2}


def step_scene_fx():
    sp = os.path.join(F, 'scene', 'scene.json')
    if not os.path.exists(sp):
        return
    cfg = json.load(open(sp))
    if cfg.get('packed') == 2:
        return
    for name, d in cfg['layers'].items():
        if not d.get('sheets'):
            continue
        sheets = [Image.open(os.path.join(F, 'scene', n)).convert('RGBA') for n in d['sheets']]
        frames = []
        for f in range(d['frames']):
            si, i = divmod(f, d['per_sheet'])
            x, y = (i % d['cols']) * d['w'], (i // d['cols']) * d['h']
            frames.append(sheets[si].crop((x, y, x + d['w'], y + d['h'])))
        step = FX_STEP.get(name, 1)
        frames = frames[::step]
        U = None
        for fr in frames:
            a = np.array(fr.getchannel('A')) > 4
            U = a if U is None else (U | a)
        ys, xs = np.where(U)
        x0, y0 = max(0, xs.min() - 2), max(0, ys.min() - 2)
        x1, y1 = min(d['w'], xs.max() + 3), min(d['h'], ys.max() + 3)
        k = FX_SCALE.get(name, 1)
        cw, ch = x1 - x0, y1 - y0
        fw, fh = max(1, round(cw * k)), max(1, round(ch * k))
        cols = max(1, 4096 // fw)
        per = cols * max(1, 4096 // fh)
        names = []
        for si in range(0, len(frames), per):
            chunk = frames[si:si + per]
            rows = -(-len(chunk) // cols)
            sheet = Image.new('RGBA', (min(len(chunk), cols) * fw, rows * fh), (0, 0, 0, 0))
            for j, fr in enumerate(chunk):
                c = fr.crop((x0, y0, x1, y1))
                if k != 1:
                    c = c.resize((fw, fh), Image.LANCZOS)
                sheet.paste(c, ((j % cols) * fw, (j // cols) * fh))
            n = f'{name}_{len(names)}.webp'
            names.append(n)
            encode(sheet, os.path.join(F, 'scene', n + '.new'), Q, 85)
        for old in d['sheets']:
            if not DRY: os.remove(os.path.join(F, 'scene', old))
        for n in names:
            if not DRY: os.replace(os.path.join(F, 'scene', n + '.new'), os.path.join(F, 'scene', n)); mark('scene/' + n)
        rx, ry, rw, rh = d['rect']
        sx, sy = rw / d['w'], rh / d['h']
        before = d['w'] * d['h'] * d['frames']
        d.update({'rect': [round(rx + x0 * sx, 2), round(ry + y0 * sy, 2), round(cw * sx, 2), round(ch * sy, 2)],
                  'frames': len(frames), 'fps': d['fps'] / step, 'w': fw, 'h': fh, 'cols': cols, 'per_sheet': per, 'sheets': names})
        print(f'scene {name}: {before / 1e6:.1f} -> {fw * fh * len(frames) / 1e6:.1f} Mpx decoded ({len(names)} sheet(s), {fw}x{fh} x {len(frames)} @ {d["fps"]:g} fps)')
    cfg['packed'] = 2
    if not DRY:
        json.dump(cfg, open(sp, 'w'), indent=1)


def step_ui(pool):
    jobs = []
    for root, dirs, files in os.walk(F):
        r = os.path.relpath(root, F)
        if r.startswith(('sym', 'spine')):
            continue
        for n in files:
            if not n.endswith('.webp'):
                continue
            rel = n if r == '.' else f'{r}/{n}'
            if rel in PLATES or rel.endswith('_m.webp') or rel.startswith(HUD) or done(rel):
                continue
            if rel.startswith(KEEP_SIZE):
                ms = 0
            else:
                pre = sorted((k for k in MAX_SIDE if k.endswith(('/', '_')) and rel.startswith(k)), key=len)
                ms = MAX_SIDE.get(rel) or (MAX_SIDE[pre[-1]] if pre else DEFAULT_MAX)
            jobs.append((rel, ms, Q, AQ))
    b0 = b1 = 0
    for rel, before, after, size in pool.map(shrink_one, jobs):
        b0 += before; b1 += after
        if before != after:
            print(f'  {rel:42s} {before / 1e3:6.0f}K -> {after / 1e3:6.0f}K {size[0]}x{size[1]}')
        if not DRY:
            mark(rel)
    if jobs:
        print(f'ui: {len(jobs)} files {b0 / 1e6:.2f} -> {b1 / 1e6:.2f} MB')


def opening(a):
    """The frame's glass opening (fractions of the image): the transparent hole round the centre."""
    h, w = a.shape
    cy, cx = int(h * .55), w // 2
    solid = a > 128
    l = next(i for i in range(cx, -1, -1) if solid[cy, i])
    r = next(i for i in range(cx, w) if solid[cy, i])
    t = next(i for i in range(cy, -1, -1) if solid[i, cx - int(w * .3)])
    b = next(i for i in range(cy, h) if solid[i, cx - int(w * .3)])
    return [(l + 1) / w, (t + 1) / h, r / w, b / h]


def step_frame():
    # the flat frame (owner, 2026-11-13: simple, not a neon sign; flat_frame.py) when it is built
    flat = os.path.join(RAW, 'board_frame_flat_sq.png'), os.path.join(RAW, 'board_frame_flat_wide.png')
    if all(os.path.exists(p) for p in flat):
        one_frame('frame_sq', flat[0], FRAME_MAX)
        one_frame('frame_wide', flat[1], FRAME_WIDE_MAX)
        return
    print('frame: art/highpeaks/raw/board_frame_flat_{sq,wide}.png missing - run tools/highpeaks/flat_frame.py')


def one_frame(name, sq, fmax):
    dst = os.path.join(F, name + '.webp')
    src_tag = ('sq:' + sha(sq) if os.path.exists(sq) else 'v3') + f'@{fmax}'
    if state.get(name + '.src') == src_tag and done(name + '.webp'):
        return
    if os.path.exists(sq):
        im = Image.open(sq).convert('RGBA')
        bb = im.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox()
        im = im.crop(bb)
    else:
        raise SystemExit(f'{sq}: missing')
    o = opening(np.array(im.getchannel('A')))
    if max(im.size) > fmax:
        k = fmax / max(im.size)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    n = encode(im, dst, Q, 90)
    meta = {'frame_size': list(im.size), 'opening': [round(x, 5) for x in o], 'source': src_tag[:2]}
    if not DRY:
        json.dump(meta, open(os.path.join(F, name + '.json'), 'w'))
        mark(name + '.webp'); state[name + '.src'] = src_tag
    print(f'{name} ({src_tag[:2]}): {im.size} opening {meta["opening"]} aspect '
          f'{(o[2] - o[0]) * im.width / ((o[3] - o[1]) * im.height):.3f} {n / 1e3:.0f}K')


def step_fillup():
    # (fillup_cell.png came out as a badge, not a tile: only its plain replacement, fillup_cell2.png, is used)
    names = {'fillup_backing': 1400, 'fillup_cell2': 384, 'fillup_gauge': 1200}
    os.makedirs(os.path.join(F, 'fillup'), exist_ok=True)
    for n, ms in names.items():
        src = os.path.join(RAW, n + '.png')
        rel = f'fillup/{n[7:].rstrip("2")}.webp'
        if not os.path.exists(src):
            continue
        if os.path.exists(os.path.join(ROOT, 'art', 'highpeaks', 'ui_glossy', rel)):
            continue    # redrawn flat (restyle.py / flat_fillup_cell.py, 2026-11-13): never re-installed from the glossy raw
        tag = sha(src)
        if state.get(rel + '.src') == tag and done(rel):
            continue
        im = Image.open(src).convert('RGBA')
        bb = im.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox()
        if bb: im = im.crop(bb)
        if max(im.size) > ms:
            k = ms / max(im.size); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        b = encode(im, os.path.join(F, rel), Q, 90)
        print(f'fillup {rel}: {im.size} {b / 1e3:.0f}K')
        if not DRY:
            mark(rel); state[rel + '.src'] = tag


def total(path):
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(path) for f in fs)


if __name__ == '__main__':
    t0 = total(F)
    with ProcessPoolExecutor(JOBS) as pool:
        step_masters()
        step_prune()
        step_frame()
        step_fillup()
        step_scene_fx()
        step_plates(pool)
        step_symbols(pool)
        step_ui(pool)
    if not DRY:
        json.dump(state, open(STATE, 'w'), indent=0, sort_keys=True)
    print(f'frontend/assets: {t0 / 1e6:.1f} MB -> {total(F) / 1e6:.1f} MB')
