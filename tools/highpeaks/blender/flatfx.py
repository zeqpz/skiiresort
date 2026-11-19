"""Falcos effect animations, made and rendered in Blender (owner, 2026-11-13: "make the fx more aesthetic and
detailed ... we want the lighter fx to be better ... make the win animations for dopamine"). Same flat look as the
symbols (flatanim.py's flat shapes with ink outlines, emission, Standard view): run inside Blender after flatanim.py
    exec(open('.../flatanim.py').read()); exec(open('.../flatfx.py').read()); render_winburst()
then  .venv/bin/python tools/highpeaks/blender_pack.py --fx

  winburst  40 f loop, 16:9: the big-win celebration - gold coins fountaining up and flipping, confetti in the
            brand colours tumbling down and sparkles twinkling, every piece wrapping round so the loop is seamless
Frames to art/highpeaks/renders/flat/_fx/<name>/NNNN.png + clip.json.
"""
import bpy, json, math, os, random

FX_OUT = os.path.join(OUT, '_fx')


def _render(sc, name, n, w_units, h_units, px):
    for o in sc.objects:
        o.hide_render = o.hide_render
    sc.camera.data.ortho_scale = max(w_units, h_units)
    sc.render.resolution_x, sc.render.resolution_y = round(w_units * px), round(h_units * px)
    sc.render.resolution_percentage = 100
    sc.frame_start, sc.frame_end = 0, n - 1
    out = os.path.join(FX_OUT, name)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith('.png'):
            os.remove(os.path.join(out, f))
    sc.render.filepath = os.path.join(out, '')
    bpy.ops.render.render(animation=True, scene=sc.name)
    json.dump({'frames': n, 'fps': FPS, 'size': [sc.render.resolution_x, sc.render.resolution_y],
               'units': [w_units, h_units]}, open(os.path.join(out, 'clip.json'), 'w'))
    print(f'{name}: {n} frames at {sc.render.resolution_x}x{sc.render.resolution_y}', flush=True)


def render_winburst(n=40):
    sc = scene()
    rnd = random.Random(2026)
    W, H = 64, 36
    L = n / FPS                                              # the loop's length in seconds: every path wraps on it

    def wrap(v, lo, hi):
        return lo + (v - lo) % (hi - lo)
    # gold coins fountaining up from the bottom and flipping: each on its own phase of the loop
    for i in range(26):
        c = piece(sc, 'coin', rnd.choice(['#F5C518', '#FFD23C', '#FFE58A']), rnd, .1, 1 + i * .002)
        # launched from all along the bottom, high over the screen, back down by the loop's end (seamless)
        ph = rnd.uniform(0, 1); x0 = rnd.uniform(-W / 2 + 4, W / 2 - 4); vx = rnd.uniform(-8, 8)
        vy = rnd.uniform(75, 95); g = 2 * vy / L
        sz = rnd.uniform(1.2, 2.0); flip = rnd.uniform(5, 9)
        for f in range(n):
            tt = ((f / n + ph) % 1) * L
            x, y = x0 + vx * tt, -H / 2 - 3 + vy * tt - .5 * g * tt * tt
            c.location = (wrap(x, -W / 2, W / 2), y, c.location.z)
            c.rotation_euler = (0, 0, .4 * math.sin(tt * 3 + i))
            c.scale = (max(.05, sz * abs(math.cos(tt * flip + i))), sz, 1)        # flipping: its width turns
            col = list(c.color); col[3] = 1; c.color = col
            for prop in ('location', 'rotation_euler', 'scale', 'color'):
                c.keyframe_insert(prop, frame=f)
            ink = bpy.data.objects[c['ink']]; ink.color = (*INK[:3], 1); ink.keyframe_insert('color', frame=f)
    # confetti tumbling down
    cols = ['#FF7A1A', '#4F9BFF', '#FFFFFF', '#FFD23C', '#FF4D5E', '#7ED957']
    for i in range(46):
        p = piece(sc, 'confetti', cols[i % len(cols)], rnd, .1, 2 + i * .002)
        x0 = rnd.uniform(-W / 2, W / 2); ph = rnd.uniform(0, 1); fall = H + 6; sway = rnd.uniform(1, 3); sp = rnd.uniform(-6, 6)
        sz = rnd.uniform(.5, .8); turns = rnd.choice([1, 2])
        for f in range(n):
            u = (f / n + ph) % 1
            key_piece(p, f, (x0 + sway * math.sin(2 * math.pi * (u * turns) + i), H / 2 + 3 - fall * u),
                      2 * math.pi * turns * u * (1 if sp > 0 else -1), sz, 1)
            p.scale = (sz, max(.05, sz * abs(math.cos(2 * math.pi * turns * u + i))), 1); p.keyframe_insert('scale', frame=f)
    # sparkles twinkling in place
    for i in range(18):
        s = piece(sc, 'spark', rnd.choice(['#FFFFFF', '#FFF6CF', '#FFD23C']), rnd, .1, 3)
        x0, y0 = rnd.uniform(-W / 2 + 2, W / 2 - 2), rnd.uniform(-H / 2 + 2, H / 2 - 2); ph = rnd.uniform(0, 1); sz = rnd.uniform(.6, 1.2)
        for f in range(n):
            u = (f / n + ph) % 1
            tw = max(0, math.sin(2 * math.pi * u * 2)) ** 2
            key_piece(s, f, (x0, y0), u * 3, max(.01, sz * tw), 1 if tw > .02 else 0)
    _render(sc, 'winburst', n, W, H, 15)

