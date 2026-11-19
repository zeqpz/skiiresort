"""Falcos symbol animations, made and rendered in Blender (owner, 2026-11-13: "make the icon animations detailed and
aesthetic ... we want icons to break unique for each item they are and leave food residue / drink residue / soda
residue / gasoline residue etc. Blender is open create all the animations ... strictly in blender and animate them
and render them in the best quality").

Run inside Blender (the MCP's execute_blender_code, or Blender's Text editor):
    exec(open('/.../tools/highpeaks/blender/flatanim.py').read()); render_symbol('L1')          # one symbol, all clips
    exec(...); [render_symbol(s) for s in SYMBOLS]                                          # all of them
then outside Blender:  .venv/bin/python tools/highpeaks/blender_pack.py   (sheets + manifest for the game)

Each symbol is its flat comic picture (art/highpeaks/symbols_static/<ID>.png) on a plane in a scene of its own
("FalcosFX"), seen by an orthographic camera, everything flat-shaded (emission, Standard view transform) so the
colours stay the picture's own; every effect piece is a flat shape with an ink outline, like the art. Real keyframed
animation, rendered with EEVEE at twice the densest sheet's resolution (32 px a unit; the icon is 10 units):

  land  14 f  falls in stretched, squashes on contact with two dust puffs, rebounds and settles on the rest pose
  idle  48 f  a gentle bob and breath with a slight sway, a shine sweeping across once - starts and ends at rest
  hit   30 f  the win: an anticipation dip, a big elastic pop, a shine sweep, a ring shockwave and a burst of
              sparkle stars in the brand colours, back to rest
  burn  34 f  the break, unique to the item: a wind-up shake and white flash, the picture shatters into shards that
              fly and spin out, its own debris bursts (coins and bills, soda / slushie / gasoline splash, crumbs and
              sprinkles, flame and smoke, confetti, glitter...) and its residue splashes into the cell (a puddle, a pile
              of crumbs, a mustard splat, a scorch mark...) and fades away before the clip ends - nothing is left behind

Frames go to art/highpeaks/renders/flat/<ID>/<clip>/0000.png ... with a clip.json (frames, fps, box in icon units).
"""
import bpy, bmesh, json, math, os, random, zlib
from mathutils import Vector

ROOT = '/Users/drewabbott/Documents/Falcos'
SRC = os.path.join(ROOT, 'art', 'highpeaks', 'symbols_static')
OUT = os.path.join(ROOT, 'art', 'highpeaks', 'renders', 'flat')
PX = 32                      # render px per icon unit (the densest sheet is 16)
FPS = 30
CLIPS = {'land': (14, 12), 'idle': (48, 12), 'hit': (30, 16), 'burn': (34, 20)}   # frames, box (icon units)
INK = (0.047, 0.047, 0.07, 1)

# the debris each item breaks into, and the residue it leaves: (pieces, colours) - see DEBRIS / RESIDUE builders
PROFILE = {
    'H1': dict(debris=[('coin', ['#F5C518', '#FFE58A'], 14), ('bill', ['#5DBB63', '#3E9A4A'], 8)], residue=('pile_coins', ['#F5C518', '#FFE58A'])),
    'H2': dict(debris=[('shard', ['#C9CED6', '#8E96A3'], 12), ('spark', ['#FFF6CF', '#FFC94D'], 10)], residue=('scatter', ['#B9C0CA', '#8E96A3'])),
    'H3': dict(debris=[('drop', ['#F2A33A', '#B86BFF', '#FFD166'], 18)], residue=('puddle_gas', ['#B5742A', '#F2A33A', '#B86BFF'])),
    'H4': dict(debris=[('drop', ['#F2A33A', '#FFD166', '#B86BFF'], 20), ('shard', ['#2F6BFF', '#1F45B8'], 6)], residue=('puddle_gas', ['#B5742A', '#F2A33A', '#B86BFF'])),
    'L1': dict(debris=[('drop', ['#7ED957', '#B8F23A'], 16), ('bubble', ['#E9FFD6'], 12), ('shard', ['#2F6BFF', '#C9CED6'], 6)], residue=('puddle', ['#6CC24A', '#B8F23A'])),
    'L2': dict(debris=[('chip', ['#FF4D5E', '#4DA3FF', '#FFFFFF'], 18), ('drop', ['#FF4D5E', '#4DA3FF'], 10)], residue=('puddle_two', ['#FF4D5E', '#4DA3FF'])),
    'L3': dict(debris=[('crumb', ['#E8B06A', '#C98A45'], 14), ('drop', ['#FFD23C'], 10), ('chunk', ['#D9534F'], 4)], residue=('splat', ['#FFD23C', '#E8B06A'])),
    'L4': dict(debris=[('chip', ['#FFD166', '#F2B84B'], 16), ('crumb', ['#FFE08A', '#E8B06A'], 14)], residue=('pile_crumbs', ['#FFD166', '#E8B06A'])),
    'L5': dict(debris=[('crumb', ['#E8B06A', '#C98A45'], 12), ('sprinkle', ['#FF4D5E', '#4DA3FF', '#FFD23C', '#7ED957', '#B86BFF'], 22), ('drop', ['#FF7EB6'], 6)], residue=('smear', ['#FF7EB6', '#E8B06A'])),
    'ZP': dict(debris=[('flame', ['#FF7A1A', '#FFD23C', '#FFF2B8'], 14), ('smoke', ['#9AA0AA', '#C7CBD2'], 8), ('spark', ['#FFD23C', '#FFF6CF'], 10)], residue=('scorch', ['#2A2324', '#4A3B36'])),
    'ST': dict(debris=[('confetti', ['#33C3B8', '#FFD23C', '#FFFFFF'], 18), ('flake', ['#C9CED6', '#E6E9EE'], 14)], residue=('scatter', ['#C9CED6', '#33C3B8'])),
    'GT': dict(debris=[('confetti', ['#F5C518', '#FFE58A', '#FF4D5E'], 18), ('flake', ['#FFE58A', '#F5C518'], 14), ('spark', ['#FFF6CF'], 8)], residue=('glitter', ['#F5C518', '#FFE58A'])),
    'GP': dict(debris=[('drop', ['#F2A33A', '#FFD166', '#B86BFF'], 18), ('shard', ['#D9534F', '#C9CED6'], 8)], residue=('puddle_gas', ['#B5742A', '#F2A33A', '#B86BFF'])),
    'FDG': dict(debris=[('drop', ['#7ED957', '#B8F23A', '#E9FFD6'], 22)], residue=('puddle', ['#6CC24A', '#B8F23A'])),
    'FDA': dict(debris=[('drop', ['#FFA640', '#FFD166', '#FFF2B8'], 22)], residue=('puddle', ['#E8892A', '#FFD166'])),
    'FDR': dict(debris=[('drop', ['#FF4D5E', '#FF8A95', '#FFD6DA'], 22)], residue=('puddle', ['#D9343F', '#FF8A95'])),
    'BS': dict(debris=[('shard', ['#E23B3B', '#F5C518'], 12), ('spark', ['#FFF6CF', '#FFD23C'], 14)], residue=('glitter', ['#F5C518', '#FFFFFF'])),
    'DS': dict(debris=[('shard', ['#7A1F2B', '#C9CED6'], 12), ('spark', ['#D9C6FF', '#FFFFFF', '#FFD23C'], 14)], residue=('glitter', ['#B9A6FF', '#FFFFFF'])),
}
SYMBOLS = list(PROFILE)


def hexc(h, a=1.0):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in srgb]   # object colour is linear
    return (*lin, a)


def ease_out(t): return 1 - (1 - t) ** 3
def ease_in(t): return t ** 2
def smooth(t): return t * t * (3 - 2 * t)
def clamp(x, a=0., b=1.): return max(a, min(b, x))


# ---------------------------------------------------------------- the scene
def scene():
    sc = bpy.data.scenes.get('FalcosFX') or bpy.data.scenes.new('FalcosFX')
    bpy.context.window.scene = sc
    for o in list(sc.collection.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    r = sc.render
    r.engine = 'BLENDER_EEVEE'
    r.film_transparent = True
    r.fps = FPS
    r.filter_size = 1.0
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.compression = 40
    try:
        sc.eevee.taa_render_samples = 64
    except Exception:
        pass
    for vt in ('Standard',):
        try:
            sc.view_settings.view_transform = vt
            sc.view_settings.look = 'None'
        except Exception:
            pass
    sc.view_settings.exposure = 0
    sc.view_settings.gamma = 1
    cam_d = bpy.data.cameras.new('FXCam')
    cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new('FXCam', cam_d)
    sc.collection.objects.link(cam)
    cam.location = (0, 0, 50)
    sc.camera = cam
    return sc


def flat_material(name):
    """Emission of the object's own colour, its alpha from the object colour's alpha: one material for every
    effect piece (each keyframes its own obj.color)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        m.blend_method = 'BLEND'
    nt = m.node_tree
    nt.nodes.clear()
    info = nt.nodes.new('ShaderNodeObjectInfo')
    em = nt.nodes.new('ShaderNodeEmission')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(info.outputs['Color'], em.inputs['Color'])
    nt.links.new(info.outputs['Alpha'], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return m


def icon_material(img):
    """The picture, flat: emission of its colour; alpha its own alpha x the object colour's alpha; mixed to white by
    the object colour's red (the break's flash) and by a moving diagonal band (the shine, `shine` value 0-1)."""
    m = bpy.data.materials.new('Icon')
    m.use_nodes = True
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        m.blend_method = 'BLEND'
    nt = m.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    tex = N('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Cubic'; tex.extension = 'CLIP'
    uv = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ')
    add = N('ShaderNodeMath'); add.operation = 'ADD'
    half = N('ShaderNodeMath'); half.operation = 'MULTIPLY'; half.inputs[1].default_value = .5
    shine = N('ShaderNodeValue'); shine.name = 'shine'; shine.outputs[0].default_value = -1
    sub = N('ShaderNodeMath'); sub.operation = 'SUBTRACT'
    ab = N('ShaderNodeMath'); ab.operation = 'ABSOLUTE'
    band = N('ShaderNodeMapRange'); band.interpolation_type = 'SMOOTHSTEP'
    band.inputs['From Min'].default_value = .07; band.inputs['From Max'].default_value = 0.0
    band.inputs['To Min'].default_value = 0; band.inputs['To Max'].default_value = .55
    info = N('ShaderNodeObjectInfo')
    sepc = N('ShaderNodeSeparateColor')
    tot = N('ShaderNodeMath'); tot.operation = 'ADD'; tot.use_clamp = True
    mixc = N('ShaderNodeMix'); mixc.data_type = 'RGBA'
    mixc.inputs['B'].default_value = (1, 1, 1, 1)
    em = N('ShaderNodeEmission')
    a_mul = N('ShaderNodeMath'); a_mul.operation = 'MULTIPLY'
    tr = N('ShaderNodeBsdfTransparent')
    mix = N('ShaderNodeMixShader')
    out = N('ShaderNodeOutputMaterial')
    L = nt.links.new
    L(uv.outputs['UV'], tex.inputs['Vector'])
    L(uv.outputs['UV'], sep.inputs[0])
    L(sep.outputs['X'], add.inputs[0]); L(sep.outputs['Y'], add.inputs[1])
    L(add.outputs[0], half.inputs[0])
    L(half.outputs[0], sub.inputs[0]); L(shine.outputs[0], sub.inputs[1])
    L(sub.outputs[0], ab.inputs[0]); L(ab.outputs[0], band.inputs['Value'])
    L(info.outputs['Color'], sepc.inputs[0])
    L(band.outputs['Result'], tot.inputs[0]); L(sepc.outputs['Red'], tot.inputs[1])
    L(tot.outputs[0], mixc.inputs['Factor'])
    L(tex.outputs['Color'], mixc.inputs['A'])
    L(mixc.outputs['Result'], em.inputs['Color'])
    L(tex.outputs['Alpha'], a_mul.inputs[0]); L(info.outputs['Alpha'], a_mul.inputs[1])
    L(a_mul.outputs[0], mix.inputs['Fac'])
    L(tr.outputs[0], mix.inputs[1]); L(em.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs['Surface'])
    return m


def grid_plane(name, w, h, n=48):
    """A w x h plane in n x n quads, UV 0-1, centred on the origin."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=n, y_segments=n, size=.5)
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            lp[uv].uv = (co.x + .5, co.y + .5)
    for v in bm.verts:
        v.co.x *= w; v.co.y *= h
    bm.to_mesh(me); bm.free()
    return me


def icon(sid, sc):
    img = bpy.data.images.load(os.path.join(SRC, sid + '.png'), check_existing=True)
    img.alpha_mode = 'STRAIGHT'
    w, h = img.size
    k = 10 / max(w, h)                         # contain: the longer side across the icon (10 units)
    me = grid_plane('Icon', w * k, h * k)
    ob = bpy.data.objects.new('Icon', me)
    sc.collection.objects.link(ob)
    ob.data.materials.append(icon_material(img))
    ob.color = (0, 0, 0, 1)
    return ob, img, (w * k, h * k)


# ---------------------------------------------------------------- effect shapes (flat colour + ink outline)
def shape_mesh(kind, rnd):
    bm = bmesh.new()
    pts = []
    if kind in ('coin', 'bubble', 'crumb', 'smoke', 'puff'):
        n = 18 if kind in ('coin', 'bubble') else 9
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = 1 if kind in ('coin', 'bubble') else 1 + rnd.uniform(-.25, .2)
            pts.append((math.cos(a) * rr, math.sin(a) * rr * (1 if kind != 'coin' else .82)))
    elif kind == 'drop':
        for i in range(20):
            a = 2 * math.pi * i / 20
            rr = 1 - .45 * max(0, math.sin(a)) ** 6
            pts.append((math.cos(a) * rr * .8, math.sin(a) * rr + (.55 * max(0, math.sin(a)) ** 12)))
    elif kind in ('bill', 'confetti', 'sprinkle', 'flake'):
        wv, hv = {'bill': (1.4, .7), 'confetti': (.9, .5), 'sprinkle': (1.0, .28), 'flake': (.7, .55)}[kind]
        pts = [(-wv, -hv), (wv, -hv), (wv, hv), (-wv, hv)]
        if kind == 'flake':
            pts = [(-wv, -hv * .6), (wv * .4, -hv), (wv, hv * .3), (-wv * .3, hv)]
    elif kind in ('shard', 'chip', 'chunk'):
        n = rnd.choice([3, 4, 5])
        for i in range(n):
            a = 2 * math.pi * i / n + rnd.uniform(-.4, .4)
            pts.append((math.cos(a) * rnd.uniform(.6, 1.1), math.sin(a) * rnd.uniform(.6, 1.1)))
    elif kind == 'spark':
        for i in range(8):
            a = 2 * math.pi * i / 8
            rr = 1 if i % 2 == 0 else .32
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
    elif kind == 'burst':                                        # a cartoon starburst: 14 rays
        for i in range(28):
            a = 2 * math.pi * i / 28
            rr = 1 if i % 2 == 0 else .62
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
    elif kind == 'flame':
        for i in range(16):
            a = 2 * math.pi * i / 16
            rr = 1 + .5 * max(0, math.sin(a)) ** 3
            pts.append((math.cos(a) * .7 * (1 - .4 * max(0, math.sin(a))), math.sin(a) * rr))
    if kind == 'ring':                                           # an annulus: the win's shockwave
        n = 40
        outer = [bm.verts.new((math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
        inner = [bm.verts.new((.8 * math.cos(2 * math.pi * i / n), .8 * math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((outer[i], outer[j], inner[j], inner[i]))
    else:
        vs = [bm.verts.new((x, y, 0)) for x, y in pts]
        bm.faces.new(vs)
    me = bpy.data.meshes.new(kind)
    bm.to_mesh(me); bm.free()
    return me


def piece(sc, kind, colour, rnd, size, z=1.0):
    """A flat effect piece with an ink outline behind it (both fade with the piece's colour alpha)."""
    me = shape_mesh(kind, rnd)
    ob = bpy.data.objects.new(kind, me)
    sc.collection.objects.link(ob)
    ob.data.materials.append(flat_material('Flat'))
    ob.color = hexc(colour, 0)
    ink = bpy.data.objects.new(kind + '_ink', me)
    sc.collection.objects.link(ink)
    ink.data.materials.append(flat_material('Flat'))
    ink.parent = ob
    ink.scale = (1.28, 1.28, 1)
    ink.location = (0, 0, -.01)
    ink.color = (*INK[:3], 0)
    ob.scale = (size, size, 1)
    ob.location.z = z
    ob['ink'] = ink.name
    return ob


def key_piece(ob, f, loc, rot, sc_, alpha, colour=None):
    ob.location = (loc[0], loc[1], ob.location.z)
    ob.rotation_euler = (0, 0, rot)
    ob.scale = (sc_, sc_, 1)
    c = list(ob.color)
    if colour is not None:
        c[:3] = colour[:3]
    c[3] = alpha
    ob.color = c
    ob.keyframe_insert('location', frame=f); ob.keyframe_insert('rotation_euler', frame=f)
    ob.keyframe_insert('scale', frame=f); ob.keyframe_insert('color', frame=f)
    ink = bpy.data.objects[ob['ink']]
    ink.color = (*INK[:3], alpha)
    ink.keyframe_insert('color', frame=f)


def key_icon(ob, f, x=0., y=0., rot=0., sx=1., sy=1., flash=0., alpha=1., shine=-1.):
    """The icon at frame f; scale is about its foot (it squashes on the ground, not in mid-air)."""
    h = ob['h']
    ob.location = (x, y - h / 2 * (1 - sy), 0)
    ob.rotation_euler = (0, 0, rot)
    ob.scale = (sx, sy, 1)
    ob.color = (flash, 0, 0, alpha)
    for p in ('location', 'rotation_euler', 'scale', 'color'):
        ob.keyframe_insert(p, frame=f)
    node = ob.active_material.node_tree.nodes['shine']
    # no shine band sweeping across the picture (owner, 2026-11-13: "make it to where lines dont go accross the symbol")
    shine = -1
    node.outputs[0].default_value = shine
    node.outputs[0].keyframe_insert('default_value', frame=f)


# ---------------------------------------------------------------- the clips
def clip_land(sc, ob, n):
    for f in range(n):
        t = f / (n - 1)
        if t < .35:                       # falling in, stretched
            u = t / .35
            y, sx, sy = 3.2 * (1 - ease_in(u)), .9, 1.14
        elif t < .55:                      # contact: squash
            u = (t - .35) / .2
            y, sx, sy = 0, .9 + .26 * math.sin(u * math.pi / 2), 1.14 - .3 * math.sin(u * math.pi / 2)
        else:                              # rebound and settle (a damped spring onto rest)
            u = (t - .55) / .45
            k = math.exp(-4.5 * u) * math.cos(u * math.pi * 2.2)
            y, sx, sy = 0, 1 + .16 * k, 1 - .16 * k
        if f == n - 1:
            y, sx, sy = 0, 1, 1
        key_icon(ob, f, 0, y, 0, sx, sy)
    rnd = random.Random(7)
    for side in (-1, 1):                   # two dust puffs at the contact
        p = piece(sc, 'puff', '#E9E4D8', rnd, .1, .5)
        for f in range(n):
            t = f / (n - 1)
            u = clamp((t - .38) / .5)
            a = 0 if t < .38 else .85 * (1 - u)
            key_piece(p, f, (side * (2.6 + 2.2 * ease_out(u)), -4.6 + .5 * ease_out(u)), 0, .35 + .45 * ease_out(u), a)


def clip_idle(sc, ob, n):
    for f in range(n):
        t = f / n                          # a seamless cycle: frame n would be frame 0
        w = math.sin(2 * math.pi * t)
        b = .5 - .5 * math.cos(2 * math.pi * t)
        shine = -1 if not (.35 <= t <= .75) else -.15 + 1.3 * smooth((t - .35) / .4)
        key_icon(ob, f, 0, .28 * b, math.radians(2.2) * math.sin(4 * math.pi * t) * b, 1 + .025 * b, 1 + .035 * b, shine=shine)
    key_icon(ob, n - 1, 0, 0, 0, 1, 1)     # the last frame is the rest pose exactly


def clip_hit(sc, ob, n, rnd):
    for f in range(n):
        t = f / (n - 1)
        if t < .12:                         # anticipation: a little dip
            u = t / .12; s = 1 - .06 * smooth(u); r = 0
        elif t < .4:                        # the pop, overshooting
            u = (t - .12) / .28; s = .94 + .34 * ease_out(u); r = math.radians(6) * math.sin(u * math.pi)
        else:                               # elastic settle back to rest
            u = (t - .4) / .6; k = math.exp(-4 * u) * math.cos(u * math.pi * 3); s = 1 + .28 * k; r = math.radians(-4) * k
        if f == n - 1:
            s, r = 1, 0
        shine = -1 if not (.18 <= t <= .7) else -.15 + 1.3 * smooth((t - .18) / .52)
        key_icon(ob, f, 0, 0, r, s, s, shine=shine)
    # the payoff behind the icon: a starburst that bursts in and turns as it fades, and two shockwave rings
    burst = piece(sc, 'burst', '#FFD23C', rnd, .1, -.6)
    inner = piece(sc, 'burst', '#FFF6CF', rnd, .1, -.55)
    rings = [piece(sc, 'ring', c, rnd, .1, -.5 + .01 * i) for i, c in enumerate(('#FF7A1A', '#FFFFFF'))]
    for r_ in rings:
        bpy.data.objects[r_['ink']].hide_render = True          # bright rings, no ink (they read as light)
    for f in range(n):
        t = f / (n - 1)
        u = clamp((t - .14) / .62)
        a = 0 if t < .14 else (1 - u) ** 1.2
        key_piece(burst, f, (0, 0), .8 * u, max(.01, 5.6 * ease_out(min(1, u * 2.2)) * (1 + .06 * math.sin(u * 9))), a)
        key_piece(inner, f, (0, 0), -.6 * u, max(.01, 3.9 * ease_out(min(1, u * 2.4))), a * .95)
        for i, r_ in enumerate(rings):
            ui = clamp((t - .16 - .06 * i) / .5)
            ai = 0 if t < .16 + .06 * i else .95 * (1 - ui) ** 1.6
            key_piece(r_, f, (0, 0), 0, 1.5 + 6.6 * ease_out(ui), ai)
    cols = ['#FFFFFF', '#FFD23C', '#FF7A1A', '#4F9BFF']
    for i in range(16):                                       # the sparkle burst
        p = piece(sc, 'spark', cols[i % 4], rnd, .1, 2)
        ang = 2 * math.pi * i / 16 + rnd.uniform(-.2, .2)
        dist = rnd.uniform(5.6, 7.6); t0 = rnd.uniform(.16, .26); size = rnd.uniform(.5, .9)
        spin = rnd.uniform(-3, 3)
        for f in range(n):
            t = f / (n - 1)
            u = clamp((t - t0) / (1 - t0))
            a = 0 if t < t0 else (1 - u) ** .8
            sz = size * (math.sin(min(1, u * 2.2) * math.pi / 2)) * (1 - .4 * u)
            key_piece(p, f, (math.cos(ang) * dist * ease_out(u), math.sin(ang) * dist * ease_out(u)), spin * u, max(.01, sz), a)


def clip_burn(sc, ob, n, sid, rnd):
    prof = PROFILE[sid]
    wv, hv = ob['w'], ob['h']
    BREAK = 7                                                  # the frame it comes apart
    for f in range(n):
        if f < BREAK:                                          # wind-up: swell, shake, flash white
            u = f / BREAK
            jit = .22 * u * math.sin(f * 2.7)
            key_icon(ob, f, jit, 0, math.radians(3) * math.sin(f * 1.9) * u, 1 + .09 * smooth(u), 1 + .09 * smooth(u), flash=.75 * u ** 2)
        else:
            key_icon(ob, f, 0, 0, 0, 1.09, 1.09, flash=.75, alpha=0)
    shards(sc, ob, n, BREAK, rnd)
    for kind, cols, count in prof['debris']:
        debris(sc, kind, cols, count, n, BREAK, rnd)
    # (no residue any more - owner, 2026-11-13: "get rid of the fx you made where it just has a flat icon on the
    # ground left behind"; residue() is kept for reference, unused)


def shards(sc, ob, n, at, rnd, count=14):
    """The picture itself in pieces: the icon's grid split into Voronoi cells round random seeds, each its own object
    (UVs kept, so each shows its part of the picture), flying out from the centre, spinning, falling, fading."""
    seeds = [Vector((rnd.uniform(-.5, .5) * ob['w'], rnd.uniform(-.5, .5) * ob['h'])) for _ in range(count)]
    src = ob.data
    for i, s in enumerate(seeds):
        bm = bmesh.new(); bm.from_mesh(src)
        drop = [fc for fc in bm.faces if min(range(count), key=lambda j: (fc.calc_center_median().xy - seeds[j]).length_squared) != i]
        bmesh.ops.delete(bm, geom=drop, context='FACES')
        if not bm.faces:
            bm.free(); continue
        c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        for v in bm.verts:
            v.co -= c
        me = bpy.data.meshes.new('shard'); bm.to_mesh(me); bm.free()
        sh = bpy.data.objects.new('shard', me)
        sc.collection.objects.link(sh)
        sh.data.materials.append(ob.active_material)
        d = c.xy.normalized() if c.xy.length > .01 else Vector((rnd.uniform(-1, 1), 1)).normalized()
        speed = rnd.uniform(7, 11); spin = rnd.uniform(-6, 6); g = 22
        for f in range(n):
            tt = max(0, f - at) / FPS
            if f < at:
                pos, a, s_, r = c.xy * 1.09, 0, 1.09, 0
            else:
                pos = c.xy * 1.09 + d * speed * tt + Vector((0, 3.5 * tt - .5 * g * tt * tt))
                a = clamp(1 - (f - at) / (n - at - 6)); s_ = 1.09 * (1 - .35 * (f - at) / (n - at)); r = spin * tt
            sh.location = (pos.x, pos.y, .2); sh.rotation_euler = (0, 0, r); sh.scale = (s_, s_, 1)
            sh.color = (.75 if f <= at + 1 else 0, 0, 0, a)
            for p in ('location', 'rotation_euler', 'scale', 'color'):
                sh.keyframe_insert(p, frame=f)


def debris(sc, kind, cols, count, n, at, rnd):
    """The item's own debris: a burst from the centre under gravity (liquids arc and fall, flames and smoke rise,
    sparks and glitter streak out and twinkle), each piece fading as it goes."""
    rise = kind in ('flame', 'smoke', 'bubble')
    for i in range(count):
        col = cols[i % len(cols)]
        size = {'drop': (.35, .7), 'bubble': (.18, .4), 'coin': (.45, .7), 'bill': (.5, .75), 'chip': (.4, .75),
                'crumb': (.15, .35), 'sprinkle': (.3, .45), 'shard': (.3, .6), 'chunk': (.4, .6), 'spark': (.3, .6),
                'flame': (.6, 1.1), 'smoke': (.7, 1.3), 'confetti': (.3, .5), 'flake': (.3, .55)}[kind]
        p = piece(sc, kind, col, rnd, .1, 1.5 + i * .001)
        ang = rnd.uniform(0, 2 * math.pi) if not rise else rnd.uniform(math.radians(50), math.radians(130))
        speed = rnd.uniform(6, 12) * (.55 if rise else 1)
        g = -6 if rise else rnd.uniform(18, 26)
        sz = rnd.uniform(*size); spin = rnd.uniform(-8, 8) if kind not in ('drop', 'flame', 'smoke', 'bubble') else 0
        t0 = at + rnd.uniform(0, 3); life = rnd.uniform(.55, .85) * (n - at)
        for f in range(n):
            tt = max(0, f - t0) / FPS
            u = clamp((f - t0) / life)
            vx, vy = math.cos(ang) * speed, math.sin(ang) * speed + (2.5 if not rise else 0)
            x, y = vx * tt, vy * tt - .5 * g * tt * tt
            a = 0 if f < t0 else (1 - u) ** (1.4 if kind in ('spark', 'flake') else .9)
            s_ = sz * (1 + (1.2 * u if kind == 'smoke' else 0)) * (min(1, (f - t0 + 1) / 2) if f >= t0 else .01)
            rot = spin * tt
            if kind == 'drop':                                   # a drop points along its flight
                rot = math.atan2(vy - g * tt, vx) - math.pi / 2
            key_piece(p, f, (x, y), rot, max(.01, s_), a)


def residue(sc, spec, n, at, rnd):
    """What the item leaves: small spatters, droplets and bits scattered over the lower half of the cell in its
    colours - never one flat shape (owner, 2026-11-13: one wide puddle "its like it got smooshed", the symbol
    squashed flat). Each pops in with a little splash as the debris lands, and all of it is gone before the clip
    ends (owner: "there is a peice of the bottom still there")."""
    kind, cols = spec
    shape = {'pile_coins': 'coin', 'pile_crumbs': 'crumb', 'scatter': 'flake', 'glitter': 'spark'}.get(kind, 'crumb')
    liquid = shape == 'crumb' and kind not in ('pile_crumbs',)
    count = 14 if liquid else 16
    for i in range(count):
        col = cols[i % len(cols)]
        if kind == 'smear' and i % 3 == 2:                       # the donut: sprinkles among the frosting spots
            col = ('#FF4D5E', '#4DA3FF', '#FFD23C', '#7ED957', '#B86BFF')[i % 5]
        if kind == 'scorch' and i % 4 == 3:                      # the lighter: a few embers among the char
            col = '#FF7A1A'
        x = rnd.uniform(-3.8, 3.8)
        y = rnd.uniform(-4.2, -.6)
        if liquid:
            w = rnd.uniform(.28, .7) if i % 3 else rnd.uniform(.12, .25)     # splotches and droplets
            h = w * rnd.uniform(.7, 1.0)
        else:
            w = rnd.uniform(.35, .55) if shape == 'coin' else rnd.uniform(.16, .34)
            h = w * (.8 if shape == 'coin' else 1)
        p = piece(sc, shape if not liquid else ('bubble' if w < .26 else 'crumb'), col, rnd, .1, .4 + i * .002)
        t0 = at + 4 + rnd.uniform(0, 6)
        rot = rnd.uniform(0, 6.28)
        for f in range(n):
            u = clamp((f - t0) / 4)
            out = smooth(clamp((f - (n - 12)) / 8))
            a = 0 if f < t0 else 1 - out
            grow = ease_out(u) * (1 + .18 * math.sin(u * math.pi))
            p.location = (x, y, p.location.z)
            p.rotation_euler = (0, 0, rot)
            p.scale = (max(.01, w * grow * (1 - .3 * out)), max(.01, h * grow * (1 - .3 * out)), 1)
            c = list(p.color); c[3] = a; p.color = c
            for prop in ('location', 'rotation_euler', 'scale', 'color'):
                p.keyframe_insert(prop, frame=f)
            ink = bpy.data.objects[p['ink']]; ink.color = (*INK[:3], a); ink.keyframe_insert('color', frame=f)


# ---------------------------------------------------------------- render
def render_symbol(sid, clips=None):
    for clip in (clips or CLIPS):
        n, box = CLIPS[clip]
        sc = scene()
        ob, img, (w, h) = icon(sid, sc)
        ob['w'], ob['h'] = w, h
        rnd = random.Random(zlib.crc32(f'{sid}:{clip}'.encode()))
        {'land': lambda: clip_land(sc, ob, n), 'idle': lambda: clip_idle(sc, ob, n),
         'hit': lambda: clip_hit(sc, ob, n, rnd), 'burn': lambda: clip_burn(sc, ob, n, sid, rnd)}[clip]()
        for o in sc.objects:                                   # every frame keyed: hold, no easing between keys
            ad = o.animation_data
            if ad and ad.action:
                for fc in getattr(ad.action, 'fcurves', []):
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'CONSTANT'
        sc.camera.data.ortho_scale = box
        sc.render.resolution_x = sc.render.resolution_y = box * PX
        sc.render.resolution_percentage = 100
        sc.frame_start, sc.frame_end = 0, n - 1
        out = os.path.join(OUT, sid, clip)
        os.makedirs(out, exist_ok=True)
        for f in os.listdir(out):
            if f.endswith('.png'):
                os.remove(os.path.join(out, f))
        sc.render.filepath = os.path.join(out, '')
        bpy.ops.render.render(animation=True, scene=sc.name)
        json.dump({'frames': n, 'fps': FPS, 'box': [-box / 2, -box / 2, box, box], 'px': PX},
                  open(os.path.join(out, 'clip.json'), 'w'))
        print(f'{sid} {clip}: {n} frames at {box * PX}px', flush=True)
