"""High Peaks symbol animations, RIGGED (owner, 2026-11-23: "icon animations when they win, idle, drop, and disappear
need to be better ... instead of manually doing it use a plugin or tool to rig").

Until now every symbol was one flat picture scaled up and down (tools/highpeaks/static_symbols.py: a 16% swell for a
win, a shrink-and-fade to leave, one still frame at rest). Here each picture is a real 2D rig in Blender:

  * the picture (art/highpeaks/symbols_static/<ID>.png, cropped to its ink and fitted to the icon like the static
    sheets were) on a mesh cut to its alpha,
  * a skeleton from SPEC: a spine from its foot (or the point it hangs from) through the body, and a chain for every
    part that should lag and swing (a pom-pom, a wisp of steam, a drip of cheese, a flame, a hanger...),
  * skinned by Blender's automatic weights (bone heat), and
  * every loose part simulated by the Jiggle Physics add-on (extensions.blender.org, `jiggle_physics`) and BAKED to
    keys, so overlap and follow-through are physics, not typed numbers.

Clips (30 fps, flat emission, orthographic, rendered with EEVEE; frames + clip.json for tools/highpeaks/blender_pack.py):

  land  12 f  the moment of contact (CSS drops the tile and squashes the cell): the body's wobble and settle, every
              loose part flopping forward and springing back, two puffs of snow kicked out at its foot
  idle  32 f  (packed as 16 at 15 fps) a breath and a slow sway, the loose parts swinging, a glint of light popping
              on its highlight - starts and ends on the rest pose
  hit   28 f  the win, a move of its own per symbol (SPEC[id]["hit"]): a coin flips, the beanie's pom-pom boings, the
              pizza swings on its crust with its cheese stretching, the lighter flares, the snow cannon fires, the
              joint and the bong puff, the tickets swing on their hangers... with anticipation, a jump, a squash on
              landing and an elastic settle, sparkles in the symbol's colours
  burn  20 f  leaving the board: a shake and a white flash, then the picture itself breaks into shards with the
              item's own debris (snow, crumbs, cheese, smoke, glass, sparks) - nothing is left on the last frame

No line of light sweeps across a picture and nothing is left lying in the cell (owner, 2026-11-13).

Live Blender (MCP):
    import importlib.util, sys; P = r'<repo>/tools/highpeaks/blender/symrig.py'
    spec = importlib.util.spec_from_file_location('symrig', P); m = importlib.util.module_from_spec(spec)
    sys.modules['symrig'] = m; spec.loader.exec_module(m); m.render_symbol('L4')
Headless (do not pass --factory-startup: the add-on lives in the user profile):
    blender -b --python tools/highpeaks/blender/symrig.py -- L4 L5        (ids; none = all)
    blender -b --python tools/highpeaks/blender/symrig.py -- --clips hit,burn H1
then  python tools/highpeaks/blender_pack.py && python tools/highpeaks/align_clips.py && python tools/highpeaks/centre_symbols.py
"""
import json, math, os, random, sys, zlib

import bpy, bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, 'art', 'highpeaks', 'symbols_static')
OUT = os.path.join(ROOT, 'art', 'highpeaks', 'renders', 'flat')
PX = 30                      # render px per icon unit (the densest sheet is 20)
FPS = 30
FILL = 10.0                  # the picture's longer side, icon units
CLIPS = {'land': (12, 12), 'idle': (32, 12), 'hit': (28, 13), 'burn': (20, 13)}   # frames, box (icon units)
INK = (0.047, 0.047, 0.07, 1)
GRID = 34                    # mesh cells along the picture's longer side
SAMPLES = 16
JIGGLE = 'bl_ext.user_default.jiggle_physics'

# jiggle presets: angle elasticity (how hard it springs back to its pose), length elasticity (1 = never stretches),
# air drag, gravity (x the scene's)
JIG = {
    'stiff': dict(angle=.72, length=.97, drag=.26, gravity=0.0),
    'soft':  dict(angle=.5, length=.95, drag=.18, gravity=0.0),
    'pom':   dict(angle=.5, length=.9, drag=.15, gravity=0.0),
    'rope':  dict(angle=.34, length=.95, drag=.13, gravity=.2),
    'wisp':  dict(angle=.4, length=.93, drag=.22, gravity=-.05),    # smoke, steam, flame: they rise
}

W, G, O, B = '#FFFFFF', '#FFD23C', '#FF7A1A', '#4F9BFF'
# Each symbol (px of its 1024 picture, y down):
#   spine   the body's chain, from the point it stands on (or hangs from, hang=True) to its far end
#   parts   loose chains: (name, parent spine index, [points], jiggle preset, idle sway deg, win kick deg)
#   hit     its win move; glint  where a glint of light pops (idle, win); spark the win's sparkle colours
#   debris  what it breaks into: (shape, colours, count); puff  where smoke / steam / snow leaves it (win)
SPEC = {
    # H1 is a pair of crossed SKIS (2026-11-23, owner: "make the normal bong icon skis"; the ice bong is GP)
    'H1': dict(spine=[(512, 990), (512, 700), (512, 420), (512, 70)], hit='carve', glint=[(170, 90), (800, 80)],
               parts=[('strapL', 2, [(120, 320), (60, 430)], 'soft', 8, 16), ('strapR', 2, [(905, 320), (965, 430)], 'soft', 8, 16)],
               puff=dict(at=[(250, 950), (780, 950)], kind='flake', cols=[W, '#DCEBFF'], n=8),
               spark=[W, '#FF5B66', G], debris=[('shard', ['#F01E28', '#FF8A1E', '#FFD23C'], 14), ('flake', [W, '#DCEBFF'], 12), ('spark', [G, W], 8)]),
    'H2': dict(spine=[(512, 1000), (512, 700), (512, 380), (512, 230)], hit='wobble', glint=[(300, 520), (690, 120)],
               parts=[('heap', 3, [(512, 230), (512, 110), (512, 20)], 'pom', 4, 10)],
               spark=[W, '#7CFF5B', G], debris=[('crumb', ['#58C431', '#8BE04A', '#3F9A22'], 18), ('shard', ['#BFF5D0', '#7FE0A0'], 10), ('spark', [W, G], 8)]),
    'H3': dict(spine=[(500, 960), (585, 660), (665, 350), (750, 60)], hit='carve', glint=[(700, 120), (590, 480)],
               parts=[('spray', 0, [(430, 930), (310, 860), (230, 790)], 'soft', 8, 20)],
               puff=dict(at=[(380, 900)], kind='flake', cols=[W, '#DCEBFF'], n=12),
               spark=[W, '#C77BFF', G], debris=[('flake', [W, '#DCEBFF'], 16), ('shard', ['#8A2BE2', '#B86BFF', '#F5A623'], 10), ('spark', [G, W], 8)]),
    'H4': dict(spine=[(512, 885), (512, 640), (512, 400), (512, 150)], hit='nod', glint=[(250, 480), (720, 540), (330, 250)],
               parts=[('earL', 1, [(120, 640), (15, 640)], 'stiff', 2, 8), ('earR', 1, [(900, 640), (1010, 640)], 'stiff', 2, 8)],
               spark=[W, '#39C6FF', O], debris=[('shard', ['#31B7F5', '#1F7FD9', W], 14), ('shard', ['#F27B21', '#19B5A5'], 8), ('flake', [W], 8), ('spark', [W, G], 6)]),
    'L1': dict(spine=[(460, 1005), (460, 800), (470, 600), (490, 420)], hit='puff', glint=[(270, 730), (440, 430)],
               parts=[('steam', 3, [(560, 340), (600, 230), (565, 130), (640, 40)], 'wisp', 10, 18),
                      ('handle', 1, [(700, 720), (850, 720)], 'stiff', 2, 7)],
               puff=dict(at=[(580, 300)], kind='smoke', cols=[W, '#E3E6EC'], n=6),
               spark=[W, '#FF5B66', G], debris=[('drop', ['#6B3A1E', '#8A4B26'], 14), ('chunk', [W, '#F3E6D8'], 6), ('shard', ['#E3262B', '#FF5B66'], 10), ('smoke', [W], 4)]),
    'L2': dict(spine=[(150, 985), (340, 815), (545, 640), (745, 465)], hit='puff', glint=[(430, 640), (760, 430)],
               parts=[('smoke', 3, [(770, 385), (735, 255), (830, 150), (850, 40)], 'wisp', 11, 20)],
               puff=dict(at=[(770, 400)], kind='smoke', cols=['#DDE2EA', '#B9C0CA'], n=8),
               spark=[W, O, G], debris=[('smoke', ['#DDE2EA', '#B9C0CA'], 8), ('spark', [O, G, '#FFF2B8'], 12), ('flake', [W, '#E6E9EE'], 12)]),
    'L3': dict(spine=[(512, 965), (512, 690), (512, 400), (512, 110)], hit='wobble', glint=[(300, 170), (600, 250)],
               parts=[], spark=[W, '#7CFF5B', G],
               debris=[('crumb', ['#6B3A1E', '#8A4B26', '#4A2412'], 22), ('chunk', ['#7A4424', '#5A2F16'], 7), ('crumb', ['#58C431'], 6)]),
    'L4': dict(spine=[(512, 1005), (512, 800), (512, 560), (512, 360)], hit='bounce', glint=[(330, 520), (430, 150)],
               parts=[('pom', 3, [(512, 350), (512, 190), (512, 40)], 'pom', 6, 16)],
               spark=[W, '#2BD9C5', G], debris=[('smoke', [W, '#EEF3FA'], 9), ('confetti', ['#27C2B0', W, '#17968A'], 16), ('flake', [W], 8)]),
    'L5': dict(spine=[(640, 150), (500, 420), (350, 660), (190, 900)], hang=True, hit='swing', glint=[(330, 290), (700, 130)],
               parts=[('drip1', 3, [(190, 880), (170, 990)], 'rope', 6, 14), ('drip2', 2, [(560, 640), (545, 810)], 'rope', 7, 16),
                      ('drip3', 1, [(650, 560), (665, 700)], 'rope', 7, 16), ('drip4', 2, [(390, 790), (375, 885)], 'rope', 6, 14)],
               spark=[W, G, '#FF5B66'], debris=[('drop', ['#FFD400', '#FFB300'], 16), ('coin', ['#E3262B', '#B81D22'], 6), ('crumb', ['#E8912A', '#C9741C'], 12)]),
    'ZP': dict(spine=[(510, 1010), (510, 780), (510, 540), (480, 350)], hit='flare', glint=[(390, 650), (400, 420)],
               parts=[('flame', 3, [(500, 320), (510, 190), (545, 40)], 'wisp', 9, 12)],
               puff=dict(at=[(520, 150)], kind='flame', cols=[O, G, '#FFF2B8'], n=8),
               spark=[W, O, G], debris=[('flame', [O, G, '#FFF2B8'], 12), ('spark', [G, '#FFF6CF'], 10), ('smoke', ['#9AA0AA', '#C7CBD2'], 6), ('shard', ['#7CFF5B', '#C9CED6'], 6)]),
    'ST': dict(spine=[(512, 70), (512, 330), (512, 630), (512, 930)], hang=True, hit='swing', glint=[(250, 320), (760, 300)],
               parts=[], spark=[W, '#2BD9C5', G], debris=[('confetti', ['#33C3B8', G, W], 18), ('flake', ['#C9CED6', '#E6E9EE'], 12), ('spark', [W, G], 6)]),
    'GT': dict(spine=[(512, 60), (512, 330), (512, 630), (512, 940)], hang=True, hit='swing', glint=[(250, 320), (790, 320)],
               parts=[], spark=[W, G, '#FF5B66'], debris=[('confetti', ['#F5C518', '#FFE58A', '#FF4D5E'], 18), ('flake', ['#FFE58A', '#F5C518'], 12), ('spark', ['#FFF6CF', W], 8)]),
    # the ICE BONG (2026-11-23; was the snow cannon): tools/highpeaks/icebong.py prints these points
    'GP': dict(spine=[(489, 998), (489, 768), (489, 552), (489, 100)], hit='puff', glint=[(331, 679), (426, 259)],
               parts=[('wisp', 1, [(683, 643), (689, 582), (695, 521)], 'wisp', 12, 20)],
               puff=dict(at=[(679, 640), (489, 44)], kind='smoke', cols=['#F4FAFF', '#D3E6F5'], n=7),
               spark=[W, '#7FD4FF', G], debris=[('shard', ['#BDE8FC', '#6DC0EE', '#EAF9FF'], 16), ('flake', [W, '#DCEBFF'], 10), ('drop', ['#38C6E8', '#1FA6D6'], 8), ('smoke', ['#EDF6FD'], 5)]),
    'FDG': dict(spine=[(512, 995), (512, 720), (520, 430), (565, 150)], hit='pulse', glint=[(690, 290), (330, 660)],
                parts=[('curl', 3, [(590, 150), (650, 35)], 'soft', 8, 16)],
                spark=[W, '#7CFF5B', O], debris=[('crumb', ['#39D62A', '#7CF55A', '#2A9E1F'], 20), ('spark', [W, O], 8), ('drop', ['#7ED957'], 6)]),
    'FDA': dict(spine=[(512, 965), (512, 720), (520, 450), (560, 180)], hit='pulse', glint=[(1000, 130), (140, 330), (160, 930)],
                parts=[('leafL', 3, [(320, 270), (230, 180)], 'soft', 7, 14), ('leafR', 2, [(880, 400), (990, 300)], 'soft', 7, 14)],
                spark=[W, G, O], debris=[('crumb', ['#FF9F1A', '#FFC24D', '#D97A0A'], 20), ('spark', [W, G], 10), ('drop', ['#FFD166'], 6)]),
    'FDR': dict(spine=[(512, 985), (512, 720), (520, 450), (560, 170)], hit='pulse', glint=[(380, 310), (700, 420)],
                parts=[('tuft', 3, [(570, 210), (600, 60)], 'soft', 8, 16)],
                spark=[W, '#FF5B66', G], debris=[('crumb', ['#E3262B', '#FF5B66', '#B81D22'], 20), ('spark', [W, O], 10), ('drop', ['#FF8A95'], 6)]),
    'BS': dict(spine=[(512, 1000), (512, 680), (512, 350), (512, 30)], hit='spin', glint=[(300, 190), (780, 760)],
               parts=[], spark=[W, G, '#7CFF5B'], debris=[('shard', ['#FFC400', '#FFE27A', '#2FB84A'], 14), ('spark', ['#FFF6CF', G], 14)]),
    'DS': dict(spine=[(512, 1000), (512, 680), (512, 350), (512, 30)], hit='spin', glint=[(300, 190), (780, 760)],
               parts=[], spark=[W, '#39C6FF', G], debris=[('shard', ['#19B8F0', '#C9CED6', '#0B0B12'], 14), ('spark', [W, '#BFE9FF', G], 14)]),
}
SYMBOLS = list(SPEC)


def hexc(h, a=1.0):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in srgb]   # object colour is linear
    return (*lin, a)


def ease_out(t): return 1 - (1 - t) ** 3
def ease_in(t): return t ** 2
def smooth(t): t = clamp(t); return t * t * (3 - 2 * t)
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def span(t, a, b): return clamp((t - a) / (b - a))                   # 0-1 across [a, b]
def spring(u, freq, damp): return math.exp(-damp * u) * math.cos(2 * math.pi * freq * u)
def swing(u, freq, damp): return math.exp(-damp * u) * math.sin(2 * math.pi * freq * u)


# ---------------------------------------------------------------- scene
def scene():
    sc = bpy.data.scenes.get('HPSym') or bpy.data.scenes.new('HPSym')
    if bpy.context.window:
        bpy.context.window.scene = sc
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
    for o in list(sc.collection.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials, bpy.data.cameras):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    r = sc.render
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            r.engine = eng
            break
        except TypeError:
            continue
    r.film_transparent = True
    r.fps = FPS
    r.filter_size = 1.0
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.compression = 30
    r.resolution_percentage = 100
    try:
        sc.eevee.taa_render_samples = SAMPLES
    except Exception:
        pass
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except Exception:
        pass
    sc.view_settings.exposure = 0
    sc.view_settings.gamma = 1
    sc.gravity = (0, 0, -9.81)
    cam_d = bpy.data.cameras.new('SymCam')
    cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new('SymCam', cam_d)
    sc.collection.objects.link(cam)
    cam.location = (0, -50, 0)                # the picture stands in the XZ plane (gravity is -Z); the camera looks along +Y
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    stage = bpy.data.objects.new('Stage', None)   # effect pieces are built flat in XY: the stage stands them up
    sc.collection.objects.link(stage)
    stage.rotation_euler = (math.radians(90), 0, 0)
    return sc, stage


def flat_material(name='Flat'):
    """Emission of the object's own colour, its alpha the object colour's alpha (every piece keys its own obj.color)."""
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
    """The picture, flat: its own colour, mixed to white by the object colour's red (the break's flash); its alpha
    times the object colour's alpha."""
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
    info = N('ShaderNodeObjectInfo')
    sepc = N('ShaderNodeSeparateColor')
    mixc = N('ShaderNodeMix'); mixc.data_type = 'RGBA'
    mixc.inputs['B'].default_value = (1, 1, 1, 1)
    em = N('ShaderNodeEmission')
    a_mul = N('ShaderNodeMath'); a_mul.operation = 'MULTIPLY'
    tr = N('ShaderNodeBsdfTransparent')
    mix = N('ShaderNodeMixShader')
    out = N('ShaderNodeOutputMaterial')
    L = nt.links.new
    L(uv.outputs['UV'], tex.inputs['Vector'])
    L(info.outputs['Color'], sepc.inputs[0])
    L(sepc.outputs['Red'], mixc.inputs['Factor'])
    L(tex.outputs['Color'], mixc.inputs['A'])
    L(mixc.outputs['Result'], em.inputs['Color'])
    L(tex.outputs['Alpha'], a_mul.inputs[0]); L(info.outputs['Alpha'], a_mul.inputs[1])
    L(a_mul.outputs[0], mix.inputs['Fac'])
    L(tr.outputs[0], mix.inputs[1]); L(em.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs['Surface'])
    return m


# ---------------------------------------------------------------- the picture: a mesh cut to its alpha
def icon(sc, sid):
    img = bpy.data.images.load(os.path.join(SRC, sid + '.png'), check_existing=True)
    img.alpha_mode = 'STRAIGHT'
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    a = px[3::4].reshape(h, w)                                   # row 0 is the picture's bottom
    ys, xs = np.nonzero(a > .03)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    k = FILL / max(x1 - x0, y1 - y0)                              # units per px: contain-fitted, centred (static_symbols.fitted)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    step = max(x1 - x0, y1 - y0) / GRID
    nx, ny = int(math.ceil((x1 - x0) / step)) + 2, int(math.ceil((y1 - y0) / step)) + 2
    gx0, gy0 = x0 - step, y0 - step
    occ = np.zeros((ny, nx), bool)
    for j in range(ny):
        ya, yb = int(max(0, gy0 + j * step)), int(min(h, gy0 + (j + 1) * step))
        for i in range(nx):
            xa, xb = int(max(0, gx0 + i * step)), int(min(w, gx0 + (i + 1) * step))
            if yb > ya and xb > xa and a[ya:yb, xa:xb].max() > .03:
                occ[j, i] = True
    grown = occ.copy()                                            # one cell of margin: the ink's soft edge is never cut
    grown[1:, :] |= occ[:-1, :]; grown[:-1, :] |= occ[1:, :]; grown[:, 1:] |= occ[:, :-1]; grown[:, :-1] |= occ[:, 1:]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    verts = {}

    def vert(i, j):
        if (i, j) not in verts:
            X, Y = gx0 + i * step, gy0 + j * step
            v = bm.verts.new(((X - cx) * k, 0, (Y - cy) * k))
            verts[(i, j)] = (v, (X / w, Y / h))
        return verts[(i, j)]
    for j in range(ny):
        for i in range(nx):
            if not grown[j, i]:
                continue
            cs = [vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)]
            f = bm.faces.new([c[0] for c in cs])
            for lp, c in zip(f.loops, cs):
                lp[uvl].uv = c[1]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.index_update()
    me = bpy.data.meshes.new('Icon')
    solid = [v[0].index for (i, j), v in verts.items()
             if any(0 <= jj < ny and 0 <= ii < nx and occ[jj, ii] for jj in (j - 1, j) for ii in (i - 1, i))]
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('Icon', me)
    sc.collection.objects.link(ob)
    ob.data.materials.append(icon_material(img))
    ob.color = (0, 0, 0, 1)
    info = dict(k=k, cx=cx, cy=cy, h=h, w=(x1 - x0) * k, hh=(y1 - y0) * k, solid=solid)
    return ob, info


def U(info, p):
    """A point of the picture (px, y down) in the scene (XZ)."""
    return Vector(((p[0] - info['cx']) * info['k'], 0, ((info['h'] - p[1]) - info['cy']) * info['k']))


# ---------------------------------------------------------------- the skeleton, skinned by bone heat
def skeleton(sc, sid, ob, info):
    S = SPEC[sid]
    ad = bpy.data.armatures.new('Rig')
    arm = bpy.data.objects.new('Rig', ad)
    sc.collection.objects.link(arm)
    for o in sc.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    names = []
    pts = [U(info, p) for p in S['spine']]
    for i in range(len(pts) - 1):
        b = eb.new('s%d' % i)
        b.head, b.tail = pts[i], pts[i + 1]
        if i:
            b.parent = eb['s%d' % (i - 1)]; b.use_connect = True
        names.append(b.name)
    jig = {}
    last = 's%d' % (len(pts) - 2)
    jig[last] = 'stiff'                                             # the far end of the body follows through
    for name, par, ppts, preset, _idle, _kick in S.get('parts', []):
        q = [U(info, p) for p in ppts]
        for i in range(len(q) - 1):
            b = eb.new('%s%d' % (name, i))
            b.head, b.tail = q[i], q[i + 1]
            b.parent = eb['%s%d' % (name, i - 1)] if i else eb['s%d' % min(par, len(pts) - 2)]
            b.use_connect = bool(i)
            jig[b.name] = preset
            names.append(b.name)
    for b in eb:
        b.align_roll(Vector((0, -1, 0)))                           # local Z at the camera: rotation_euler.z turns it in the picture
    bpy.ops.object.mode_set(mode='OBJECT')
    # automatic weights (bone heat)
    for o in sc.objects:
        o.select_set(False)
    ob.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    heat = sum(1 for v in ob.data.vertices if v.groups)
    if heat < len(ob.data.vertices):                               # islands bone heat could not reach: the nearest bone
        segs = [(n, arm.data.bones[n].head_local.copy(), arm.data.bones[n].tail_local.copy()) for n in names]
        for n in names:
            if n not in ob.vertex_groups:
                ob.vertex_groups.new(name=n)
        for v in ob.data.vertices:
            if v.groups:
                continue
            best, bd = None, 1e9
            for n, a_, b_ in segs:
                ab = b_ - a_
                t = clamp((v.co - a_).dot(ab) / max(1e-9, ab.length_squared))
                d = (v.co - (a_ + ab * t)).length
                if d < bd:
                    best, bd = n, d
            ob.vertex_groups[best].add([v.index], 1.0, 'REPLACE')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    return arm, names, jig, dict(heat=heat, verts=len(ob.data.vertices))


def jiggle_on(sc, arm, jig):
    import addon_utils
    if not hasattr(bpy.types.Scene, 'jiggle'):
        addon_utils.enable(JIGGLE, default_set=False)
    sc.jiggle.enable = True
    arm.jiggle.enable = True
    arm.jiggle.mute = False
    for name, preset in jig.items():
        pb, p = arm.pose.bones[name], JIG[preset]
        pb.jiggle.enable = True
        pb.jiggle_angle_elasticity = p['angle']
        pb.jiggle_length_elasticity = p['length']
        pb.jiggle_air_drag = p['drag']
        pb.jiggle_gravity = p['gravity']
        pb.jiggle_blend = 1.0


def key(pb, f, rot=0., sx=1., sy=1., x=0., y=0.):
    pb.rotation_euler = (0, 0, rot)
    pb.scale = (sx, sy, 1)
    pb.location = (x, y, 0)
    pb.keyframe_insert('rotation_euler', frame=f)
    pb.keyframe_insert('scale', frame=f)
    pb.keyframe_insert('location', frame=f)


def bake_jiggle(sc, arm, jig, n, settle=5):
    """Simulate the loose parts over the clip and bake them to keys (the add-on's own bake); then ease the baked
    motion onto the keyed pose over the last frames, so the clip ends exactly on the rest pose, and keep it in the
    picture's plane."""
    if not jig:
        return
    for o in sc.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    sc.frame_start, sc.frame_end = 0, n - 1
    sc.frame_set(0)
    bpy.ops.object.mode_set(mode='POSE')
    keyed = {}
    act = arm.animation_data.action
    for fc in act.fcurves:                                          # what was keyed, before the bake overwrites it
        keyed[(fc.data_path, fc.array_index)] = [fc.evaluate(f) for f in range(n)]
    arm.jiggle.freeze = False
    sc.jiggle.loop = False
    sc.jiggle.preroll = 20
    sc.jiggle.bake_overwrite = True
    sc.jiggle.bake_nla = False
    try:
        bpy.ops.armature.jiggle_bake()
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
    act = arm.animation_data.action
    for fc in act.fcurves:
        bone = fc.data_path.split('"')[1] if '"' in fc.data_path else None
        if bone not in jig:
            continue
        prop = fc.data_path.rsplit('.', 1)[-1]
        base = keyed.get((fc.data_path, fc.array_index))
        flat = (prop == 'rotation_euler' and fc.array_index != 2) or (prop == 'location' and fc.array_index == 2) \
            or (prop == 'scale' and fc.array_index == 2)
        for kp in fc.keyframe_points:
            f = int(round(kp.co.x))
            if not 0 <= f < n:
                continue
            rest = base[f] if base else (1.0 if prop == 'scale' else 0.0)
            if flat:
                kp.co.y = 1.0 if prop == 'scale' else 0.0
            else:
                e = 1 - smooth(span(f, n - 1 - settle, n - 1))
                kp.co.y = rest + (kp.co.y - rest) * e
            kp.handle_left.y = kp.handle_right.y = kp.co.y
        fc.update()
    arm.jiggle.freeze = True                                        # the keys play back as baked


# ---------------------------------------------------------------- effect pieces (flat colour + ink outline)
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
    elif kind in ('confetti', 'flake'):
        wv, hv = {'confetti': (.9, .5), 'flake': (.7, .55)}[kind]
        pts = [(-wv, -hv), (wv, -hv), (wv, hv), (-wv, hv)]
        if kind == 'flake':
            pts = [(-wv, -hv * .6), (wv * .4, -hv), (wv, hv * .3), (-wv * .3, hv)]
    elif kind in ('shard', 'chunk'):
        n = rnd.choice([3, 4, 5])
        for i in range(n):
            a = 2 * math.pi * i / n + rnd.uniform(-.4, .4)
            pts.append((math.cos(a) * rnd.uniform(.6, 1.1), math.sin(a) * rnd.uniform(.6, 1.1)))
    elif kind in ('spark', 'glint'):                              # a four-point star
        thin = .32 if kind == 'spark' else .2
        for i in range(8):
            a = 2 * math.pi * i / 8
            rr = 1 if i % 2 == 0 else thin
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
    elif kind == 'flame':
        for i in range(16):
            a = 2 * math.pi * i / 16
            rr = 1 + .5 * max(0, math.sin(a)) ** 3
            pts.append((math.cos(a) * .7 * (1 - .4 * max(0, math.sin(a))), math.sin(a) * rr))
    vs = [bm.verts.new((x, y, 0)) for x, y in pts]
    bm.faces.new(vs)
    me = bpy.data.meshes.new(kind)
    bm.to_mesh(me); bm.free()
    return me


def piece(sc, stage, kind, colour, rnd, depth=1.0, ink=True):
    """A flat effect piece (in the stage's XY; depth > 0 is in front of the picture), an ink outline behind it."""
    me = shape_mesh(kind, rnd)
    ob = bpy.data.objects.new('fx_' + kind, me)
    sc.collection.objects.link(ob)
    ob.parent = stage
    ob.data.materials.append(flat_material())
    ob.color = hexc(colour, 0)
    ob.location.z = depth
    ob['ink'] = ''
    if ink:
        o2 = bpy.data.objects.new('fx_' + kind + '_ink', me)
        sc.collection.objects.link(o2)
        o2.data.materials.append(flat_material())
        o2.parent = ob
        o2.scale = (1.3, 1.3, 1)
        o2.location = (0, 0, -.02)
        o2.color = (*INK[:3], 0)
        ob['ink'] = o2.name
    return ob


def key_piece(ob, f, loc, rot, sc_, alpha):
    ob.location = (loc[0], loc[1], ob.location.z)
    ob.rotation_euler = (0, 0, rot)
    ob.scale = (sc_, sc_, 1)
    c = list(ob.color); c[3] = alpha; ob.color = c
    for p in ('location', 'rotation_euler', 'scale', 'color'):
        ob.keyframe_insert(p, frame=f)
    if ob['ink']:
        ink = bpy.data.objects[ob['ink']]
        ink.color = (*INK[:3], alpha)
        ink.keyframe_insert('color', frame=f)


def P2(info, p):
    """A picture point (px) in the stage's XY."""
    v = U(info, p)
    return (v.x, v.z)


def glints(sc, stage, info, S, n, windows, rnd, size=.75):
    """A glint of light on the picture's highlight: a white star that pops, turns a little and is gone."""
    for i, (a, b) in enumerate(windows):
        if i >= len(S.get('glint', [])):
            break
        x, y = P2(info, S['glint'][i])
        g = piece(sc, stage, 'glint', W, rnd, 2.5, ink=False)
        for f in range(n):
            t = f / (n - 1)
            u = span(t, a, b)
            on = a <= t <= b
            s = size * math.sin(u * math.pi) ** .7 if on else 0
            key_piece(g, f, (x, y), .5 * u, max(.001, s), 1.0 if on else 0.0)


def puffs(sc, stage, n, at, f0, rnd, side=1.0, kind='puff', col='#F4F8FF', count=1, rise=.5, out=1.6, size=.55, life=9):
    for i in range(count):
        p = piece(sc, stage, kind, col, rnd, .6)
        dx = side * (out * rnd.uniform(.75, 1.15)); dy = rise * rnd.uniform(.5, 1.2)
        t0 = f0 + i * .7
        for f in range(n):
            u = clamp((f - t0) / life)
            a = 0 if f < t0 or u >= 1 else .92 * (1 - u) ** 1.3
            s_ = size * (.35 + .75 * ease_out(u))
            lim = CLIPS['land'][1] / 2 - .3 - s_ * 1.35                     # inside the landing's box
            key_piece(p, f, (clamp(at[0] + dx * ease_out(u), -lim, lim), at[1] + dy * ease_out(u)), .6 * side * u, max(.001, s_), a)


def emit(sc, stage, info, S, n, f0, rnd, strength=1.0):
    """What leaves the symbol on its win: smoke or steam curling up, snow thrown, a flame's licks."""
    e = S.get('puff')
    if not e:
        return
    for at in e['at']:
        x0, y0 = P2(info, at)
        for i in range(e['n']):
            kind = e['kind']
            col = e['cols'][i % len(e['cols'])]
            p = piece(sc, stage, 'smoke' if kind == 'smoke' else kind, col, rnd, 1.6 + i * .01)
            t0 = f0 + rnd.uniform(0, 7)
            life = rnd.uniform(9, 14)
            if kind == 'flake':
                ang = rnd.uniform(math.radians(15), math.radians(165)); sp = rnd.uniform(2.2, 4.4) * strength
                vx, vy, g, sz, spin = math.cos(ang) * sp, math.sin(ang) * sp, 9.0, rnd.uniform(.22, .42), rnd.uniform(-6, 6)
            elif kind == 'flame':
                vx, vy, g, sz, spin = rnd.uniform(-1.2, 1.2), rnd.uniform(2.5, 4.5), -2.0, rnd.uniform(.35, .6), 0
            else:
                vx, vy, g, sz, spin = rnd.uniform(-.9, 1.1), rnd.uniform(1.6, 3.0), -1.5, rnd.uniform(.4, .7), rnd.uniform(-1.5, 1.5)
            for f in range(n):
                tt = max(0, f - t0) / FPS
                u = clamp((f - t0) / life)
                x = x0 + vx * tt + (.25 * math.sin(tt * 9 + i) if kind == 'smoke' else 0)
                y = y0 + vy * tt - .5 * g * tt * tt
                a = 0 if f < t0 or u >= 1 else (1 - u) ** 1.1 * (.9 if kind != 'smoke' else .8)
                s_ = sz * ((.5 + 1.0 * u) if kind == 'smoke' else (1 - .5 * u)) * min(1, (f - t0 + 1) / 2)
                lim = CLIPS['hit'][1] / 2 - .35 - s_ * 1.35                 # inside its clip's box
                key_piece(p, f, (clamp(x, -lim, lim), clamp(y, -lim, lim)), spin * tt, max(.001, s_), a)


def sparkles(sc, stage, S, n, t0, rnd, count=12, reach=(4.4, 5.9)):
    cols = S.get('spark', [W, G, O])
    for i in range(count):
        p = piece(sc, stage, 'spark', cols[i % len(cols)], rnd, 2.0 + i * .01)
        ang = 2 * math.pi * i / count + rnd.uniform(-.22, .22)
        dist = rnd.uniform(*reach); ts = t0 + rnd.uniform(0, .08); size = rnd.uniform(.3, .58)
        spin = rnd.uniform(-3, 3)
        for f in range(n):
            t = f / (n - 1)
            u = clamp((t - ts) / (.52 + .1 * (i % 3)))
            a = 0 if t < ts or u >= 1 else (1 - u) ** .7
            sz = size * math.sin(min(1, u * 2.4) * math.pi / 2) * (1 - .55 * u)
            d = 1.6 + (dist - 1.6) * ease_out(u)
            key_piece(p, f, (math.cos(ang) * d, math.sin(ang) * d), spin * u, max(.001, sz), a)


# ---------------------------------------------------------------- the clips
def chain(arm, name):
    out, i = [], 0
    while (name + str(i)) in arm.pose.bones:
        out.append(arm.pose.bones[name + str(i)]); i += 1
    return out


def key_parts(arm, S, f, fn):
    """Each loose chain's keyed lead (the physics follows it): fn(part index, link index, idle amp, kick amp) -> rot"""
    for pi, (name, _par, _pts, _preset, idle_a, kick_a) in enumerate(S.get('parts', [])):
        for li, pb in enumerate(chain(arm, name)):
            v = fn(pi, li, math.radians(idle_a), math.radians(kick_a))
            if isinstance(v, tuple):                               # (turn, wide, long): only the first link is scaled - a
                key(pb, f, v[0], v[1] if li == 0 else 1, v[2] if li == 0 else 1)   # scale runs down the chain by itself
            else:
                key(pb, f, v)


def clip_land(sc, stage, arm, info, S, n, rnd):
    sp = chain(arm, 's')
    hang = S.get('hang')
    for f in range(n):
        t = f / (n - 1)
        last = f == n - 1
        k = 0 if last else spring(t, 1.55, 4.4)                      # the body's own squash, in step with the cell's
        if hang:                                                    # it lands hanging: it swings on its hook
            key(sp[0], f, 0 if last else math.radians(6) * swing(t, 1.5, 3.6), 1 - .02 * k, 1 + .03 * k)
        else:
            key(sp[0], f, 0 if last else math.radians(2.2) * swing(t, 1.7, 4.2), 1 + .07 * k, 1 - .09 * k)
        for i, pb in enumerate(sp[1:], 1):                          # each link a couple of frames behind the one under it
            u = max(0, t - .07 * i)
            w_ = 0 if last else swing(u, 1.7, 3.8) * (0 if t < .07 * i else 1)
            key(pb, f, math.radians((3.2 if not hang else 4.5) * i) * w_, 1, 1 if last else 1 - .045 * spring(u, 1.6, 4.2) * (1 if u > 0 else 0))
        key_parts(arm, S, f, lambda pi, li, ia, ka: 0 if last else -ka * .9 * swing(max(0, t - .05 * (li + 1)), 1.9, 3.4) * (1 if pi % 2 == 0 else -1))
    if not hang:                                                    # two puffs of snow kicked out at its foot
        foot = P2(info, S['spine'][0])
        base = (foot[0], -info['hh'] / 2 + .35)
        for side in (-1, 1):
            puffs(sc, stage, n, (base[0] + side * info['w'] * .28, base[1]), 0.5, rnd, side, count=2, rise=.55, out=1.25, size=.5, life=9)


def clip_idle(sc, stage, arm, info, S, n, rnd):
    sp = chain(arm, 's')
    hang = S.get('hang')
    for f in range(n):
        t = f / n                                                   # a cycle: frame n would be frame 0
        w_ = .5 - .5 * math.cos(2 * math.pi * t)                    # 0 -> 1 -> 0, at rest at both ends
        s1 = math.sin(2 * math.pi * t) * w_
        if f == n - 1:
            w_ = s1 = 0
        if hang:
            key(sp[0], f, math.radians(4.5) * s1, 1, 1 + .02 * w_)
        else:
            key(sp[0], f, math.radians(1.8) * s1, 1 - .024 * w_, 1 + .05 * w_)
        for i, pb in enumerate(sp[1:], 1):
            lag = math.sin(2 * math.pi * (t - .06 * i)) * w_ if f < n - 1 else 0
            key(pb, f, math.radians(2.6 * i) * lag, 1, 1 + .014 * w_)
        key_parts(arm, S, f, lambda pi, li, ia, ka: 1.6 * ia * math.sin(2 * math.pi * (2 * t - .12 * li) + pi * 1.3) * w_ * (1 + .35 * li))
    glints(sc, stage, info, S, n, [(.2, .52), (.5, .82)], rnd, size=.8)


def root_pop(t, hang, amp=1.0, J=.6, ST=1.1):
    """The win's body: (y, uniform scale, sx, sy, lean). Anticipation .0-.16, launch -.34, air -.56, landing -.68,
    settle. J is how high it jumps and ST how tall it stretches: what its clip's box has room for (clip_hit)."""
    if hang:                                                        # it cannot jump: a hard swing and a swell
        u = span(t, .0, .14)
        if t < .14:
            return 0, 1 - .03 * smooth(u), 1, 1, math.radians(-6) * smooth(u) * amp
        u = (t - .14) / .86
        return 0, 1 + .07 * math.sin(math.pi * span(t, .14, .6)) ** 1.2, 1, 1 + .04 * math.sin(math.pi * span(t, .14, .5)), \
            math.radians(14) * amp * math.exp(-3.1 * u) * math.sin(2 * math.pi * 2.05 * u - .46)
    if t < .16:
        u = smooth(t / .16)
        return 0, 1, 1 + .13 * u, 1 - .16 * u, math.radians(-3.5) * u * amp
    if t < .34:
        u = ease_out((t - .16) / .18)
        return J * .8 * u * amp, 1, lerp(1.13, 2 - ST, u), lerp(.84, ST, u), math.radians(lerp(-3.5, 2.5, u)) * amp
    if t < .56:
        u = (t - .34) / .22
        arc = math.sin(math.pi * (.5 + .5 * u))                     # the top of the arc, coming down
        return amp * J * (.8 + .2 * math.sin(math.pi * u) - .45 * u * u), 1 + .04 * math.sin(math.pi * u), lerp(2 - ST, .98, u), lerp(ST, 1.03, u), math.radians(2.5) * arc * amp
    if t < .68:
        u = (t - .56) / .12
        return amp * J * .35 * (1 - ease_in(u)), 1, lerp(.98, 1.15, smooth(u)), lerp(1.03, .85, smooth(u)), 0
    u = (t - .68) / .32
    k = spring(u, 1.7, 4.6)
    return 0, 1, 1 + .15 * k, 1 - .15 * k, 0


def clip_hit(sc, stage, arm, info, S, n, rnd):
    sp = chain(arm, 's')
    hang, move = S.get('hang'), S['hit']
    amp = {'spin': .75, 'pulse': .55, 'flare': .7, 'blast': .45, 'carve': .8, 'nod': .7}.get(move, 1.0)
    # what the clip's box leaves it: its top may reach LIMIT (the box is 6.5 up from the icon's centre)
    LIMIT = CLIPS['hit'][1] / 2 - .7
    foot = U(info, S['spine'][0]).z
    tall = info['hh'] / 2 - foot                                    # foot to the picture's top, at rest
    room = LIMIT - info['hh'] / 2
    J = clamp(room * .5, .25, 1.0)
    ST = clamp((LIMIT - J * .8 - foot) / max(1e-6, tall), 1.03, 1.17)
    for f in range(n):
        t = f / (n - 1)
        last = f == n - 1
        y, s, sx, sy, lean = root_pop(t, hang, amp, J, ST)
        rot = lean
        air = span(t, .16, .62)
        bend = [0.0] * len(sp)                                       # the spine's own curve, per link
        if move == 'spin':                                           # the coin flips twice in the air, never showing its back
            th = 2 * math.pi * smooth(air)
            sx *= max(.07, abs(math.cos(th)))
        elif move == 'wobble':                                       # a jelly rock from side to side
            wob = math.sin(2 * math.pi * 2.5 * span(t, .12, .9)) * (1 - span(t, .12, .95)) ** .8
            bend = [math.radians(5.5 * (i + 1)) * wob for i in range(len(sp))]
            rot += math.radians(3.5) * wob
        elif move == 'carve':                                        # the board swings into a carve and back
            rot += math.radians(-17) * math.sin(math.pi * span(t, .1, .42)) + math.radians(14) * math.sin(math.pi * span(t, .4, .78))
            bend = [math.radians(4 * i) * math.sin(2 * math.pi * span(t, .1, .8)) for i in range(len(sp))]
        elif move == 'nod':                                          # the goggles tip up, then nod
            rot += math.radians(-9) * math.sin(math.pi * span(t, .12, .44)) + math.radians(7) * math.sin(math.pi * span(t, .44, .8))
        elif move == 'pulse':                                        # a bud throbs twice
            s *= 1 + .11 * math.sin(math.pi * span(t, .14, .44)) ** 2 + .08 * math.sin(math.pi * span(t, .46, .76)) ** 2
            bend = [math.radians(2.5 * i) * math.sin(2 * math.pi * 2 * span(t, .14, .8)) * (1 - span(t, .14, .9)) for i in range(len(sp))]
        elif move == 'blast':                                        # the cannon kicks back as it fires
            kick = math.sin(math.pi * span(t, .26, .5)) ** .6 if t > .26 else 0
            rot += math.radians(5.5) * kick - math.radians(3) * smooth(span(t, .08, .26)) * (1 - span(t, .26, .34))
        elif move == 'swing':
            bend = [math.radians(3.2 * i) * math.sin(2 * math.pi * 2 * span(t, .14, 1) - .9) * (1 - span(t, .14, 1)) for i in range(len(sp))]
        elif move in ('bounce', 'puff', 'flare'):
            bend = [math.radians(2.6 * i) * swing(max(0, t - .56), 2.2, 3.5) * (1 if t > .56 else 0) for i in range(len(sp))]
        if last:
            y, s, sx, sy, rot, bend = 0, 1, 1, 1, 0, [0.0] * len(sp)
        key(sp[0], f, rot + bend[0], s * sx, s * sy, 0, y)
        for i, pb in enumerate(sp[1:], 1):
            key(pb, f, bend[i], 1, 1)

        def part(pi, li, ia, ka, t=t, last=last):
            if last:
                return 0
            name = S['parts'][pi][0]
            lead = -ka * math.sin(math.pi * span(t, .0, .2)) + ka * 1.2 * math.sin(math.pi * span(t, .16, .5)) \
                - ka * .9 * swing(max(0, t - .56), 2.0, 3.2) * (1 if t > .56 else 0)
            lead *= (1 if pi % 2 == 0 else -1) * (1 + .3 * li)
            if name == 'flame':                                      # the lighter flares: the flame stands tall and fat
                fl = math.sin(math.pi * span(t, .14, .8)) ** .7
                return (lead * .5, 1 + .22 * fl, 1 + .42 * fl)
            if name.startswith('drip'):                              # the cheese stretches as the slice swings
                st = math.sin(math.pi * span(t, .14, .62)) ** .8
                return (lead, 1 - .1 * st, 1 + .6 * st)
            if name == 'pom':                                        # the pom-pom squashes, then boings tall
                return (lead, 1 + .2 * math.sin(math.pi * span(t, .0, .18)) - .1 * math.sin(math.pi * span(t, .18, .5)),
                        1 - .22 * math.sin(math.pi * span(t, .0, .18)) + .16 * math.sin(math.pi * span(t, .18, .5)))
            if name == 'blast':                                      # the snow leaves the barrel
                bl = math.sin(math.pi * span(t, .26, .72)) ** .6 if t > .26 else 0
                return (lead, 1 + .22 * bl, 1 + .3 * bl)
            if name == 'barrel':
                return math.radians(7) * (math.sin(math.pi * span(t, .26, .5)) if t > .26 else 0) - math.radians(4) * math.sin(math.pi * span(t, .06, .26))
            if name in ('smoke', 'steam'):
                pf = math.sin(math.pi * span(t, .2, .8))
                return (lead, 1 + .16 * pf, 1 + .26 * pf)
            if name == 'heap':
                hp = math.sin(math.pi * span(t, .18, .5))
                return (lead, 1 + .08 * hp, 1 + .3 * hp)
            return lead
        key_parts(arm, S, f, part)
    sparkles(sc, stage, S, n, .2, rnd)
    glints(sc, stage, info, S, n, [(.2, .5), (.34, .64), (.5, .8)], rnd, size=.85)
    emit(sc, stage, info, S, n, n * (.3 if move == 'blast' else .22), rnd)


def shards(sc, ob, n, at, rnd, count=13):
    """The picture itself in pieces: its mesh split round random seeds, each piece its own object showing its part
    of the picture, thrown out from the centre, turning, falling and shrinking to nothing."""
    me = ob.data
    xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    seeds = [Vector((rnd.uniform(min(xs), max(xs)), 0, rnd.uniform(min(zs), max(zs)))) for _ in range(count)]
    for i in range(count):
        bm = bmesh.new(); bm.from_mesh(me)
        drop = [fc for fc in bm.faces if min(range(count), key=lambda j: (fc.calc_center_median() - seeds[j]).length_squared) != i]
        bmesh.ops.delete(bm, geom=drop, context='FACES')
        if not bm.faces:
            bm.free(); continue
        c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        for v in bm.verts:
            v.co -= c
        m2 = bpy.data.meshes.new('shard'); bm.to_mesh(m2); bm.free()
        sh = bpy.data.objects.new('shard', m2)
        sc.collection.objects.link(sh)
        sh.data.materials.append(ob.active_material)
        d = Vector((c.x, c.z))
        d = d.normalized() if d.length > .05 else Vector((rnd.uniform(-1, 1), 1)).normalized()
        T = (n - 1 - at) / FPS
        reach = max(.15, CLIPS['burn'][1] / 2 - 1.5 - max(abs(c.x), abs(c.z)) * 1.08)   # as far as its box lets it fly
        speed = min(4.6, reach / (T * .72)) * rnd.uniform(.6, 1.0); spin = rnd.uniform(-7, 7); g = 5
        for f in range(n):
            tt = max(0, f - at) / FPS
            if f < at:
                x, z, a, s_, r = c.x * 1.08, c.z * 1.08, 0, 1.08, 0
            else:
                u = (f - at) / (n - 1 - at)
                x = c.x * 1.08 + d.x * speed * tt
                z = c.z * 1.08 + d.y * speed * tt + .9 * tt - .5 * g * tt * tt
                a = 1 if u < .22 else clamp(1 - (u - .22) / .5)
                s_ = 1.08 * (1 - .72 * u); r = spin * tt
            sh.location = (x, -.2 - i * .01, z); sh.rotation_euler = (0, r, 0); sh.scale = (s_, 1, s_)
            sh.color = (.8 if f <= at + 1 else 0, 0, 0, a)
            for p in ('location', 'rotation_euler', 'scale', 'color'):
                sh.keyframe_insert(p, frame=f)


def debris(sc, stage, kind, cols, count, n, at, rnd):
    rise = kind in ('flame', 'smoke', 'bubble')
    for i in range(count):
        col = cols[i % len(cols)]
        size = {'drop': (.3, .6), 'bubble': (.16, .34), 'coin': (.4, .6), 'crumb': (.14, .34), 'shard': (.26, .5),
                'chunk': (.34, .52), 'spark': (.28, .52), 'flame': (.45, .8), 'smoke': (.38, .66), 'confetti': (.26, .44),
                'flake': (.24, .46)}[kind]
        p = piece(sc, stage, kind, col, rnd, 1.5 + i * .002)
        ang = rnd.uniform(0, 2 * math.pi) if not rise else rnd.uniform(math.radians(40), math.radians(140))
        speed = rnd.uniform(3.2, 6.6) * (.5 if rise else 1)
        g = -4 if rise else rnd.uniform(11, 16)
        sz = rnd.uniform(*size); spin = rnd.uniform(-8, 8) if kind not in ('drop', 'flame', 'smoke', 'bubble') else 0
        t0 = at + rnd.uniform(0, 2); life = rnd.uniform(.6, .92) * (n - 1 - at)
        x0, y0 = rnd.uniform(-1.6, 1.6), rnd.uniform(-1.6, 1.6)
        for f in range(n):
            tt = max(0, f - t0) / FPS
            u = clamp((f - t0) / life)
            vx, vy = math.cos(ang) * speed, math.sin(ang) * speed + (2.2 if not rise else 0)
            x, y = x0 + vx * tt, y0 + vy * tt - .5 * g * tt * tt
            a = 0 if f < t0 or u >= 1 else (1 - u) ** (1.4 if kind in ('spark', 'flake') else .9) * (1 - smooth(span(f, n - 5, n - 2)))
            s_ = sz * (1 + (.8 * u if kind == 'smoke' else -.4 * u)) * (min(1, (f - t0 + 1) / 2) if f >= t0 else .01)
            rot = spin * tt
            if kind == 'drop':
                rot = math.atan2(vy - g * tt, vx) - math.pi / 2
            key_piece(p, f, (x, y), rot, max(.001, s_), a)


def clip_burn(sc, stage, arm, ob, info, S, n, rnd):
    sp = chain(arm, 's')
    BREAK = 5
    for f in range(n):
        if f < BREAK:                                               # a shiver, a swell and a white flash
            u = f / BREAK
            key(sp[0], f, math.radians(4) * math.sin(f * 2.4) * u, 1 + .08 * smooth(u), 1 + .08 * smooth(u), .16 * u * math.sin(f * 3.1), 0)
            ob.color = (.8 * u ** 2, 0, 0, 1)
        else:
            key(sp[0], f, 0, 1.08, 1.08)
            ob.color = (.8, 0, 0, 0)
        ob.keyframe_insert('color', frame=f)
        for pb in sp[1:]:
            key(pb, f, math.radians(2) * math.sin(f * 2.9) * (f / BREAK if f < BREAK else 0))
        key_parts(arm, S, f, lambda pi, li, ia, ka: ka * .5 * math.sin(f * 2.6 + pi) * (f / BREAK if f < BREAK else 0))
    shards(sc, ob, n, BREAK, rnd)
    for kind, cols, count in S['debris']:
        debris(sc, stage, kind, cols, count, n, BREAK, rnd)


def fit_box(sc, ob, arm, info, n, limit):
    """Keep the picture inside its clip's box: where a frame's stretch, swing or loose part would reach past
    `limit` (icon units from the centre), the whole symbol is eased back by that much - a lower jump, never a cut
    edge. Measured on the deformed mesh's solid vertices, frame by frame; returns the biggest shift."""
    fit = bpy.data.objects.new('Fit', None)
    sc.collection.objects.link(fit)
    arm.parent = fit
    need = []
    for f in range(n):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        mw = oe.matrix_world
        xs, zs = [], []
        for i in info['solid']:
            p = mw @ me.vertices[i].co
            xs.append(p.x); zs.append(p.z)
        oe.to_mesh_clear()
        x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
        s = min(1.0, 2 * limit / max(1e-6, x1 - x0), 2 * limit / max(1e-6, z1 - z0))
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        x0, x1, z0, z1 = cx + (x0 - cx) * s, cx + (x1 - cx) * s, cz + (z0 - cz) * s, cz + (z1 - cz) * s
        dx = limit - x1 if x1 > limit else (-limit - x0 if x0 < -limit else 0.0)
        dz = limit - z1 if z1 > limit else (-limit - z0 if z0 < -limit else 0.0)
        need.append((dx, dz, s, cx, cz))

    def soften(vals, worst):
        m = [worst(vals[max(0, i - 2):i + 3]) for i in range(n)]                 # reach a couple of frames early and late
        k = (1, 2, 3, 2, 1)
        out = []
        for i in range(n):
            acc = sum(k[j] * m[min(n - 1, max(0, i + j - 2))] for j in range(5)) / 9
            out.append(worst([acc, vals[i]]))                                    # never less than the frame needs
        return out
    far = lambda v: max(v, key=abs)
    dxs = soften([q[0] for q in need], far)
    dzs = soften([q[1] for q in need], far)
    ss = soften([q[2] for q in need], min)
    for f in range(n):
        s = ss[f]
        cx, cz = need[f][3], need[f][4]
        fit.scale = (s, s, s)
        fit.location = (dxs[f] + cx * (1 - s), 0, dzs[f] + cz * (1 - s))
        if f in (0, n - 1):
            fit.scale = (1, 1, 1); fit.location = (0, 0, 0)
        fit.keyframe_insert('location', frame=f); fit.keyframe_insert('scale', frame=f)
    return round(max(max(abs(a), abs(b)) for a, b in zip(dxs, dzs)), 2)


# ---------------------------------------------------------------- build + render
def build(sid, clip):
    """One symbol, one clip, ready to render: returns (scene, stats)."""
    n, box = CLIPS[clip]
    S = SPEC[sid]
    sc, stage = scene()
    ob, info = icon(sc, sid)
    arm, names, jig, stats = skeleton(sc, sid, ob, info)
    jiggle_on(sc, arm, jig)
    rnd = random.Random(zlib.crc32(f'{sid}:{clip}'.encode()))
    if clip == 'land':
        clip_land(sc, stage, arm, info, S, n, rnd)
    elif clip == 'idle':
        clip_idle(sc, stage, arm, info, S, n, rnd)
    elif clip == 'hit':
        clip_hit(sc, stage, arm, info, S, n, rnd)
    else:
        clip_burn(sc, stage, arm, ob, info, S, n, rnd)
    bake_jiggle(sc, arm, jig, n)
    stats['fit'] = fit_box(sc, ob, arm, info, n, box / 2 - .32) if clip != 'burn' else 0
    for o in sc.objects:                                           # every frame is keyed: no easing between keys
        adt = o.animation_data
        if adt and adt.action:
            for fc in adt.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
    sc.camera.data.ortho_scale = box
    sc.render.resolution_x = sc.render.resolution_y = int(box * PX)
    sc.frame_start, sc.frame_end = 0, n - 1
    stats.update(bones=len(names), jiggle=len(jig), clip=clip, frames=n, box=box)
    return sc, stats


def render_symbol(sid, clips=None):
    out_all = []
    for clip in (clips or CLIPS):
        sc, stats = build(sid, clip)
        n, box = CLIPS[clip]
        out = os.path.join(OUT, sid, clip)
        os.makedirs(out, exist_ok=True)
        for old in os.listdir(out):
            if old.endswith('.png'):
                os.remove(os.path.join(out, old))
        sc.render.filepath = os.path.join(out, '')
        bpy.ops.render.render(animation=True)
        json.dump({'frames': n, 'fps': FPS, 'box': [-box / 2, -box / 2, box, box], 'px': PX}, open(os.path.join(out, 'clip.json'), 'w'))
        out_all.append(stats)
        print('rendered', sid, clip, stats, flush=True)
    return out_all


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    clips = None
    if '--clips' in argv:
        i = argv.index('--clips'); clips = argv[i + 1].split(','); del argv[i:i + 2]
    for s in (argv or SYMBOLS):
        render_symbol(s, clips)
