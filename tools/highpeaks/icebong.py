"""High Peaks - the ICE BONG's picture (owner, 2026-11-23: the column-multiplier symbol is "just an ice bong ... facing
directly forward"; it takes the Snow Cannon's place, symbol id GP).

    python tools/highpeaks/icebong.py
    blender -b --python tools/highpeaks/blender/symrig.py -- GP
    python tools/highpeaks/blender_pack.py GP && python tools/highpeaks/align_clips.py && python tools/highpeaks/centre_symbols.py

The bong is ONE drawing: the SVG in frontend/icebong.js, which the page also shows big when the symbol fires. This
photographs its still version (frontend/icebong_test.html?shot=1, in headless Chrome on a clear page) and writes

    art/highpeaks/symbols_static/GP.png      1024 x 1024, the picture symrig.py rigs and animates
    frontend/assets/flat/GP.webp             400 x 400, the flat icon (rules screen, first seconds, reduced motion)

and prints where the drawing's points landed in the picture (px), for symrig.py's SPEC["GP"].
"""
import os, subprocess, sys, tempfile
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE = os.path.join(ROOT, 'frontend', 'icebong_test.html')
OUT = os.path.join(ROOT, 'art', 'highpeaks', 'symbols_static', 'GP.png')
FLAT = os.path.join(ROOT, 'frontend', 'assets', 'flat', 'GP.webp')
BROWSERS = [r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
SHOT = 1600                       # the window photographed (the bong is 94% of its height)
# points of the drawing (its own 200 x 470 box: frontend/icebong.js ICON_H) that the rig wants
BOX = (200, 470)
POINTS = {'foot': (100, 456), 'flask': (100, 342), 'neck': (100, 165), 'rim': (100, 50), 'top': (100, 30), 'bowl': (100, 248),
          'wisp0': (100, 222), 'wisp1': (103, 192), 'wisp2': (106, 162), 'glint_flask': (62, 318), 'glint_tube': (75, 120)}


def photograph():
    exe = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not exe:
        sys.exit('no Chrome or Edge found')
    tmp = os.path.join(tempfile.mkdtemp(prefix='icebong_'), 'shot.png')
    url = 'file:///' + PAGE.replace('\\', '/') + '?shot=1'
    subprocess.run([exe, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
                    f'--window-size={SHOT},{SHOT}', '--default-background-color=00000000', '--virtual-time-budget=1500',
                    f'--screenshot={tmp}', url], check=True, capture_output=True, timeout=120)
    return Image.open(tmp).convert('RGBA')


if __name__ == '__main__':
    shot = photograph()
    bb = shot.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox()
    assert bb, 'the photograph is empty'
    pic = shot.crop(bb)
    k = 1000 / max(pic.size)                                       # its longer side 1000 px in a 1024 square
    pic = pic.resize((round(pic.size[0] * k), round(pic.size[1] * k)), Image.LANCZOS)
    im = Image.new('RGBA', (1024, 1024))
    ox, oy = (1024 - pic.size[0]) // 2, (1024 - pic.size[1]) // 2
    im.alpha_composite(pic, (ox, oy))
    im.save(OUT)
    flat = Image.new('RGBA', (400, 400))
    f = pic.copy(); f.thumbnail((372, 372), Image.LANCZOS)
    flat.alpha_composite(f, ((400 - f.size[0]) // 2, (400 - f.size[1]) // 2))
    flat.save(FLAT, 'WEBP', quality=90, method=6, alpha_quality=95)
    # the drawing's box in the photograph: 94vh tall, BOX's shape, centred
    dh = SHOT * .94; s = dh / BOX[1]; dx0 = SHOT / 2 - BOX[0] / 2 * s; dy0 = SHOT / 2 - BOX[1] / 2 * s
    pts = {n: (round(((x * s + dx0) - bb[0]) * k + ox), round(((y * s + dy0) - bb[1]) * k + oy)) for n, (x, y) in POINTS.items()}
    print('wrote', OUT, im.size, '| ink box', im.getchannel('A').getbbox())
    print('wrote', FLAT)
    print('points', pts)
