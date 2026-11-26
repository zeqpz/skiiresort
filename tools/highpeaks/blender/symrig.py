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
  hit   28 f  the WIN: every symbol has a move of its own (the mv_* / fx_* pairs, HIT), posed frame to frame like an
              animator's keys - anticipation, the action, an overshoot, a settle - with its loose parts leading or
              trailing and an accent thrown off it at the right frame. The skis do a helicopter (a full turn in the
              air) and stomp; the jar's heap springs out; the board pops an ollie into a rooster tail; the goggles
              pop and double-take; the cocoa sloshes; the joint jabs and its cherry flares; the brownie stomps and
              quivers; the beanie's pom-pom boings; the pizza swings and its cheese stretches; the lighter flicks;
              the silver ticket is scratched, the gold one yanked on its string; the ice bong bubbles and rips;
              the three buds throb, shimmy and hop; the FS coin is tossed and flips, the XFS coin spins like a wheel.
              The paying symbols' premiums and the coins move biggest; the lows are quicker and smaller.
  burn  20 f  the EXIT (clip_burn): it FREEZES AND SHATTERS. A squash and a swell as frost grows in over it from its
              edges (0-3), it tightens and cracks (4), a white freeze flash (5), then it bursts (6-18): the picture
              itself in straight-edged inked shards thrown out from a break point of its own (BURN), turning, falling
              and shrinking to nothing, chips of ice and of its own stuff past them, powder snow rolling out behind.
              Frame 19 is empty; nothing fades out as a ghost and nothing is left lying.

Both clips were reviewed as "could be improved" by the Engine reviewer (2026-11-24): the win was one shared jump with
a different wiggle on top, and the exit a white fade into grid-stepped pieces that barely moved. Frame counts, fps
and boxes are as they were: index.html times a round by them (winClipMs, burnCells).

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
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, 'art', 'highpeaks', 'symbols_static')
OUT = os.environ.get('HP_SYMRIG_OUT') or os.path.join(ROOT, 'art', 'highpeaks', 'renders', 'flat')   # (a scratch folder, for trying a move)
PX = 30                      # render px per icon unit (the densest sheet is 20)
FPS = 30
FILL = 10.0                  # the picture's longer side, icon units
CLIPS = {'land': (12, 12), 'idle': (32, 12), 'hit': (28, 13), 'burn': (20, 13)}   # frames, box (icon units)
INK = (0.047, 0.047, 0.07, 1)
FROST = .86                  # how far a frozen picture's colours go to ice (the rest of its own colour shows through)
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
    'H1': dict(spine=[(512, 990), (512, 700), (512, 420), (512, 70)], hit='heli', glint=[(170, 90), (800, 80)],
               parts=[('strapL', 2, [(120, 320), (60, 430)], 'soft', 8, 16), ('strapR', 2, [(905, 320), (965, 430)], 'soft', 8, 16)],
               puff=dict(at=[(250, 950), (780, 950)], kind='flake', cols=[W, '#DCEBFF'], n=8),
               spark=[W, '#FF5B66', G], debris=[('shard', ['#F01E28', '#FF8A1E', '#FFD23C'], 14), ('flake', [W, '#DCEBFF'], 12), ('spark', [G, W], 8)]),
    'H2': dict(spine=[(512, 1000), (512, 700), (512, 380), (512, 230)], hit='jar', glint=[(300, 520), (690, 120)],
               parts=[('heap', 3, [(512, 230), (512, 110), (512, 20)], 'pom', 4, 10)],
               spark=[W, '#7CFF5B', G], debris=[('crumb', ['#58C431', '#8BE04A', '#3F9A22'], 18), ('shard', ['#BFF5D0', '#7FE0A0'], 10), ('spark', [W, G], 8)]),
    'H3': dict(spine=[(500, 960), (585, 660), (665, 350), (750, 60)], hit='ollie', glint=[(700, 120), (590, 480)],
               parts=[('spray', 0, [(430, 930), (310, 860), (230, 790)], 'soft', 8, 20)],
               puff=dict(at=[(380, 900)], kind='flake', cols=[W, '#DCEBFF'], n=12),
               spark=[W, '#C77BFF', G], debris=[('flake', [W, '#DCEBFF'], 16), ('shard', ['#8A2BE2', '#B86BFF', '#F5A623'], 10), ('spark', [G, W], 8)]),
    'H4': dict(spine=[(512, 885), (512, 640), (512, 400), (512, 150)], hit='take', glint=[(250, 480), (720, 540), (330, 250)],
               parts=[('earL', 1, [(120, 640), (15, 640)], 'stiff', 2, 8), ('earR', 1, [(900, 640), (1010, 640)], 'stiff', 2, 8)],
               spark=[W, '#39C6FF', O], debris=[('shard', ['#31B7F5', '#1F7FD9', W], 14), ('shard', ['#F27B21', '#19B5A5'], 8), ('flake', [W], 8), ('spark', [W, G], 6)]),
    'L1': dict(spine=[(460, 1005), (460, 800), (470, 600), (490, 420)], hit='slosh', glint=[(270, 730), (440, 430)],
               parts=[('steam', 3, [(560, 340), (600, 230), (565, 130), (640, 40)], 'wisp', 10, 18),
                      ('handle', 1, [(700, 720), (850, 720)], 'stiff', 2, 7)],
               puff=dict(at=[(580, 300)], kind='smoke', cols=[W, '#E3E6EC'], n=6),
               spark=[W, '#FF5B66', G], debris=[('drop', ['#6B3A1E', '#8A4B26'], 14), ('chunk', [W, '#F3E6D8'], 6), ('shard', ['#E3262B', '#FF5B66'], 10), ('smoke', [W], 4)]),
    'L2': dict(spine=[(150, 985), (340, 815), (545, 640), (745, 465)], hit='drag', glint=[(430, 640), (760, 430)],
               parts=[('smoke', 3, [(770, 385), (735, 255), (830, 150), (850, 40)], 'wisp', 11, 20)],
               puff=dict(at=[(770, 400)], kind='smoke', cols=['#DDE2EA', '#B9C0CA'], n=8),
               spark=[W, O, G], debris=[('smoke', ['#DDE2EA', '#B9C0CA'], 8), ('spark', [O, G, '#FFF2B8'], 12), ('flake', [W, '#E6E9EE'], 12)]),
    'L3': dict(spine=[(512, 965), (512, 690), (512, 400), (512, 110)], hit='stomp', glint=[(300, 170), (600, 250)],
               parts=[], spark=[W, '#7CFF5B', G],
               debris=[('crumb', ['#6B3A1E', '#8A4B26', '#4A2412'], 22), ('chunk', ['#7A4424', '#5A2F16'], 7), ('crumb', ['#58C431'], 6)]),
    'L4': dict(spine=[(512, 1005), (512, 800), (512, 560), (512, 360)], hit='boing', glint=[(330, 520), (430, 150)],
               parts=[('pom', 3, [(512, 350), (512, 190), (512, 40)], 'pom', 6, 16)],
               spark=[W, '#2BD9C5', G], debris=[('smoke', [W, '#EEF3FA'], 9), ('confetti', ['#27C2B0', W, '#17968A'], 16), ('flake', [W], 8)]),
    'L5': dict(spine=[(640, 150), (500, 420), (350, 660), (190, 900)], hang=True, hit='swing', glint=[(330, 290), (700, 130)],
               parts=[('drip1', 3, [(190, 880), (170, 990)], 'rope', 6, 14), ('drip2', 2, [(560, 640), (545, 810)], 'rope', 7, 16),
                      ('drip3', 1, [(650, 560), (665, 700)], 'rope', 7, 16), ('drip4', 2, [(390, 790), (375, 885)], 'rope', 6, 14)],
               spark=[W, G, '#FF5B66'], debris=[('drop', ['#FFD400', '#FFB300'], 16), ('coin', ['#E3262B', '#B81D22'], 6), ('crumb', ['#E8912A', '#C9741C'], 12)]),
    'ZP': dict(spine=[(510, 1010), (510, 780), (510, 540), (480, 350)], hit='flick', glint=[(390, 650), (400, 420)],
               parts=[('flame', 3, [(500, 320), (510, 190), (545, 40)], 'wisp', 9, 12)],
               puff=dict(at=[(520, 150)], kind='flame', cols=[O, G, '#FFF2B8'], n=8),
               spark=[W, O, G], debris=[('flame', [O, G, '#FFF2B8'], 12), ('spark', [G, '#FFF6CF'], 10), ('smoke', ['#9AA0AA', '#C7CBD2'], 6), ('shard', ['#7CFF5B', '#C9CED6'], 6)]),
    'ST': dict(spine=[(512, 70), (512, 330), (512, 630), (512, 930)], hang=True, hit='scratch', glint=[(250, 320), (760, 300)],
               parts=[], spark=[W, '#2BD9C5', G], debris=[('confetti', ['#33C3B8', G, W], 18), ('flake', ['#C9CED6', '#E6E9EE'], 12), ('spark', [W, G], 6)]),
    'GT': dict(spine=[(512, 60), (512, 330), (512, 630), (512, 940)], hang=True, hit='yank', glint=[(250, 320), (790, 320)],
               parts=[], spark=[W, G, '#FF5B66'], debris=[('confetti', ['#F5C518', '#FFE58A', '#FF4D5E'], 18), ('flake', ['#FFE58A', '#F5C518'], 12), ('spark', ['#FFF6CF', W], 8)]),
    # the ICE BONG (2026-11-23; was the snow cannon): tools/highpeaks/icebong.py prints these points
    # (2026-11-24: the picture is the new bong - a straight tube, the collar bowl in the middle, a chamber and a foot;
    # the old one's drawn wisp over a side bowl is gone, so it has no loose part)
    'GP': dict(spine=[(511, 996), (511, 737), (511, 334), (511, 72)], hit='rip', glint=[(425, 682), (455, 231)],
               parts=[],
               puff=dict(at=[(511, 500), (511, 30)], kind='smoke', cols=['#F4FAFF', '#D3E6F5'], n=7),
               spark=[W, '#7FD4FF', G], debris=[('shard', ['#BDE8FC', '#6DC0EE', '#EAF9FF'], 16), ('flake', [W, '#DCEBFF'], 10), ('drop', ['#38C6E8', '#1FA6D6'], 8), ('smoke', ['#EDF6FD'], 5)]),
    'FDG': dict(spine=[(512, 995), (512, 720), (520, 430), (565, 150)], hit='throb', glint=[(690, 290), (330, 660)],
                parts=[('curl', 3, [(590, 150), (650, 35)], 'soft', 8, 16)],
                spark=[W, '#7CFF5B', O], debris=[('crumb', ['#39D62A', '#7CF55A', '#2A9E1F'], 20), ('spark', [W, O], 8), ('drop', ['#7ED957'], 6)]),
    'FDA': dict(spine=[(512, 965), (512, 720), (520, 450), (560, 180)], hit='shimmy', glint=[(1000, 130), (140, 330), (160, 930)],
                parts=[('leafL', 3, [(320, 270), (230, 180)], 'soft', 7, 14), ('leafR', 2, [(880, 400), (990, 300)], 'soft', 7, 14)],
                spark=[W, G, O], debris=[('crumb', ['#FF9F1A', '#FFC24D', '#D97A0A'], 20), ('spark', [W, G], 10), ('drop', ['#FFD166'], 6)]),
    'FDR': dict(spine=[(512, 985), (512, 720), (520, 450), (560, 170)], hit='hops', glint=[(380, 310), (700, 420)],
                parts=[('tuft', 3, [(570, 210), (600, 60)], 'soft', 8, 16)],
                spark=[W, '#FF5B66', G], debris=[('crumb', ['#E3262B', '#FF5B66', '#B81D22'], 20), ('spark', [W, O], 10), ('drop', ['#FF8A95'], 6)]),
    'BS': dict(spine=[(512, 1000), (512, 680), (512, 350), (512, 30)], hit='flip', glint=[(300, 190), (780, 760)],
               parts=[], spark=[W, G, '#7CFF5B'], debris=[('shard', ['#FFC400', '#FFE27A', '#2FB84A'], 14), ('spark', ['#FFF6CF', G], 14)]),
    'DS': dict(spine=[(512, 1000), (512, 680), (512, 350), (512, 30)], hit='wheel', glint=[(300, 190), (780, 760)],
               parts=[], spark=[W, '#39C6FF', G], debris=[('shard', ['#19B8F0', '#C9CED6', '#0B0B12'], 14), ('spark', [W, '#BFE9FF', G], 14)]),
}
# How each one SHATTERS as it leaves (clip_burn): n  shards round its middle and round its outside; at  the point
# the break runs out from (px; none = its middle) - what hangs breaks from its hook and drops, what stands breaks
# from low down and jumps; bias  a push on every shard (x, y units a second); g  how hard they fall; puffs / chips
# lumps of powder snow and chips of ice.
BURN = {
    'H1': dict(n=(4, 8), at=(512, 560), chips=12, puffs=7),            # the skis: from where they cross, out along all four
    'H2': dict(n=(3, 7), at=(512, 640)),                               # the jar: from its belly
    'H3': dict(n=(3, 6), at=(560, 760), bias=(.6, 2.4)),               # the board: from its tail, up its length
    'H4': dict(n=(4, 7), at=(512, 520), bias=(0., 1.0), g=11.),        # the goggles: both lenses out sideways
    'L1': dict(n=(3, 6), at=(460, 760), bias=(0., 2.2)),               # the mug: from its foot, the cream thrown up
    'L2': dict(n=(2, 6), at=(330, 820), bias=(1.2, 1.8), chips=8),     # the joint: from its twisted end, along it
    'L3': dict(n=(4, 7), at=(512, 620), g=16.),                        # the brownie: heavy, it crumbles
    'L4': dict(n=(3, 7), at=(512, 760), bias=(0., 2.6)),               # the beanie: from its band, the pom-pom up
    'L5': dict(n=(3, 7), at=(640, 150), bias=(-.6, -.4), g=17.),       # the pizza: off its crust, down
    'ZP': dict(n=(2, 6), at=(510, 700), bias=(0., 2.0), chips=8, puffs=5),
    'ST': dict(n=(3, 7), at=(512, 80), bias=(0., -.6), g=17.),         # the tickets: off their hangers
    'GT': dict(n=(4, 7), at=(512, 80), bias=(0., -.6), g=17., chips=12),
    'GP': dict(n=(2, 7), at=(511, 737), bias=(0., 1.8), chips=12, puffs=5),   # the ice bong: its bulb bursts, the neck jumps
    'FDG': dict(n=(3, 7), at=(512, 600)),
    'FDA': dict(n=(4, 7), at=(512, 560), bias=(0., 2.2)),
    'FDR': dict(n=(3, 8), at=(512, 640), g=15.),
    'BS': dict(n=(4, 9), chips=13, puffs=7),                           # the coins: from dead centre, all round
    'DS': dict(n=(5, 8), chips=13, puffs=7),
}
for _sid, _plan in BURN.items():
    SPEC[_sid]['burn'] = _plan
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
    """The picture, flat: its own colour, its alpha times the object colour's alpha. The object colour's other
    channels are the exit's (clip_burn): GREEN is how far frost has grown in over it from its edges (0 none, 1 all
    of it; a hard crystalline front, not a fade), BLUE ices the whole of it evenly (the shards), RED mixes it to
    white (the freeze flash). Iced, a colour goes to the ice ramp by its lightness - ink stays ink, so the frozen
    picture is still the cartoon, in ice."""
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
    # the picture in ice: a ramp over its lightness
    bw = N('ShaderNodeRGBToBW')
    ramp = N('ShaderNodeValToRGB')
    stops = [(0, '#0C0C12'), (.02, '#16406F'), (.17, '#56A9E6'), (.5, '#B4E2FA'), (1, '#FFFFFF')]
    el = ramp.color_ramp.elements
    while len(el) < len(stops):
        el.new(.5)
    for e_, (pos, col) in zip(el, stops):
        e_.position = pos; e_.color = hexc(col)
    L(tex.outputs['Color'], bw.inputs[0]); L(bw.outputs[0], ramp.inputs[0])
    # where the frost has reached: far from the middle first, its front broken up by crystal cells
    dist = N('ShaderNodeVectorMath'); dist.operation = 'LENGTH'
    vor = N('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 1.25
    front = N('ShaderNodeMath'); front.operation = 'MULTIPLY_ADD'; front.inputs[1].default_value = .145   # dist x .145 + cells x .45
    cells = N('ShaderNodeMath'); cells.operation = 'MULTIPLY'; cells.inputs[1].default_value = .45
    thr = N('ShaderNodeMath'); thr.operation = 'MULTIPLY_ADD'; thr.inputs[1].default_value = -1.62; thr.inputs[2].default_value = 1.52
    reach = N('ShaderNodeMath'); reach.operation = 'GREATER_THAN'
    iced = N('ShaderNodeMath'); iced.operation = 'ADD'; iced.use_clamp = True
    how = N('ShaderNodeMath'); how.operation = 'MULTIPLY'; how.inputs[1].default_value = FROST
    mixi = N('ShaderNodeMix'); mixi.data_type = 'RGBA'
    L(uv.outputs['Object'], dist.inputs[0]); L(uv.outputs['Object'], vor.inputs['Vector'])
    L(vor.outputs['Distance'], cells.inputs[0])
    L(dist.outputs['Value'], front.inputs[0]); L(cells.outputs[0], front.inputs[2])
    L(sepc.outputs['Green'], thr.inputs[0])
    L(front.outputs[0], reach.inputs[0]); L(thr.outputs[0], reach.inputs[1])
    L(reach.outputs[0], iced.inputs[0]); L(sepc.outputs['Blue'], iced.inputs[1])
    L(iced.outputs[0], how.inputs[0])
    L(how.outputs[0], mixi.inputs['Factor']); L(tex.outputs['Color'], mixi.inputs['A']); L(ramp.outputs['Color'], mixi.inputs['B'])
    L(sepc.outputs['Red'], mixc.inputs['Factor'])
    L(mixi.outputs['Result'], mixc.inputs['A'])
    L(mixc.outputs['Result'], em.inputs['Color'])
    L(tex.outputs['Alpha'], a_mul.inputs[0]); L(info.outputs['Alpha'], a_mul.inputs[1])
    L(a_mul.outputs[0], mix.inputs['Fac'])
    L(tr.outputs[0], mix.inputs[1]); L(em.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs['Surface'])
    return m


def ink_material(icon_mat):
    """Ink, wherever the picture is: the picture's alpha (times the object colour's) in the outline's black - a
    shard's rim, so a crack is a black line on the picture and nothing off it."""
    img = next(nd.image for nd in icon_mat.node_tree.nodes if nd.type == 'TEX_IMAGE')
    m = bpy.data.materials.new('IconInk')
    m.use_nodes = True
    try:
        m.surface_render_method = 'BLENDED'
    except Exception:
        m.blend_method = 'BLEND'
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    tex = N('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Cubic'; tex.extension = 'CLIP'
    uv = N('ShaderNodeTexCoord')
    info = N('ShaderNodeObjectInfo')
    em = N('ShaderNodeEmission'); em.inputs['Color'].default_value = INK
    a_mul = N('ShaderNodeMath'); a_mul.operation = 'MULTIPLY'
    tr = N('ShaderNodeBsdfTransparent')
    mix = N('ShaderNodeMixShader')
    out = N('ShaderNodeOutputMaterial')
    L(uv.outputs['UV'], tex.inputs['Vector'])
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
    info = dict(k=k, cx=cx, cy=cy, h=h, iw=w, w=(x1 - x0) * k, hh=(y1 - y0) * k, solid=solid, a=a)
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
    if kind in ('coin', 'bubble', 'crumb', 'smoke', 'puff', 'snow'):
        n = 18 if kind in ('coin', 'bubble', 'snow') else 9
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = 1 if kind in ('coin', 'bubble', 'snow') else 1 + rnd.uniform(-.25, .2)
            pts.append((math.cos(a) * rr, math.sin(a) * rr * (1 if kind != 'coin' else .82)))
    elif kind == 'cloud':                                         # a lump of powder snow, of vapour: round, scalloped
        lobes, ph = rnd.choice([5, 6]), rnd.uniform(0, 6.3)
        for i in range(48):
            a = 2 * math.pi * i / 48
            rr = .88 + .12 * abs(math.cos(lobes * a / 2 + ph)) ** .6
            pts.append((math.cos(a) * rr, math.sin(a) * rr * .9))
    elif kind == 'burst':                                         # the flash of a break: a ragged many-pointed star
        for i in range(22):
            a = 2 * math.pi * (i + rnd.uniform(-.18, .18)) / 22
            rr = rnd.uniform(.78, 1.0) if i % 2 == 0 else rnd.uniform(.36, .5)
            pts.append((math.cos(a) * rr, math.sin(a) * rr))
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
    elif kind in ('spark', 'glint', 'twinkle'):                   # a four-point star
        thin = {'spark': .32, 'glint': .2, 'twinkle': .3}[kind]
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


def piece(sc, stage, kind, colour, rnd, depth=1.0, ink=True, ink_depth=None, rim=None):
    """A flat effect piece (in the stage's XY; depth > 0 is in front of the picture), an ink outline behind it.
    ink_depth puts the outline at a depth of its own (every lump of a cloud's outline under every lump: one outline
    round the cloud); rim keeps the outline that wide (icon units) whatever size the piece is keyed to."""
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
        o2.location = (0, 0, -.02 if ink_depth is None else ink_depth - depth)
        o2.color = (*INK[:3], 0)
        ob['ink'] = o2.name
    ob['rim'] = rim or 0.0
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
        if ob['rim']:
            k_ = min(2.0, 1 + ob['rim'] / max(sc_, .05))
            ink.scale = (k_, k_, 1)
            ink.keyframe_insert('scale', frame=f)


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


# ---------------------------------------------------------------- pose to pose, and what flies
D = math.radians
ALT = (0, -1, 1, -.9, 1, -1, .85, -1, .9, -.75, .55, -.3, .12)      # a buzz: one flip a frame, dying away


def K(f, keys):
    """A value at frame f through (frame, value[, ease]) keys - an animator's pose-to-pose curve. The ease belongs to
    the stretch ARRIVING at its key: 'io' (the default) leaves the last pose gently and settles into this one, 'in'
    speeds up into it (a fall, a landing), 'out' arrives slowing down (a launch, a pop), 'lin' is even."""
    if f <= keys[0][0]:
        return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if f <= b[0]:
            u = (f - a[0]) / (b[0] - a[0])
            e = b[2] if len(b) > 2 else 'io'
            u = smooth(u) if e == 'io' else ease_in(u) if e == 'in' else ease_out(u) if e == 'out' else u
            return lerp(a[1], b[1], u)
    return keys[-1][1]


def shake(f, f0, period, decay):
    """A wobble that starts at frame f0 and dies away: -1..1."""
    return math.exp(-decay * (f - f0)) * math.sin(2 * math.pi * (f - f0) / period) if f >= f0 else 0.0


def buzz(f, f0):
    i = int(f - f0)
    return ALT[i] if 0 <= i < len(ALT) else 0.0


def key_obj(o, f, rot=0., s=1., x=0., z=0.):
    """The whole rig about the icon's centre: a turn in the picture's plane (+ is anticlockwise, as the bones'),
    a swell, a move (x right, z up)."""
    o.rotation_euler = (0, -rot, 0)
    o.scale = (s, s, s)
    o.location = (x, 0, z)
    for p in ('location', 'rotation_euler', 'scale'):
        o.keyframe_insert(p, frame=f)


def spray(sc, stage, n, rnd, kind, cols, count, at, f0, ang=(0, 360), speed=(3., 5.), g=9., size=(.35, .55), life=(9, 13),
          stagger=2., spin=6., drag=0., grow=0., depth=2.0, jitter=(.25, .25), ring=False, r0=(0., 0.), ink=True,
          ink_depth=None, fade=.3, box=13., parent=None):
    """Pieces thrown from a point (stage XY): `count` of `kind` in `cols`, leaving at frame f0 (+ up to `stagger`),
    at `ang` degrees (0 right, 90 up; ring=True spreads them evenly round the circle) and `speed` units a second,
    slowed by `drag`, pulled down by `g` (negative: it rises). Each pops in over two frames, lives `life` frames
    (growing by `grow` - smoke, powder) and shrinks to nothing over the end of it, so nothing fades out as a ghost
    and nothing is left behind. r0 starts them that far out along their own way. Kept inside the clip's box."""
    made = []
    ph = rnd.uniform(0, 360)
    for i in range(count):
        p = piece(sc, stage, kind, cols[i % len(cols)], rnd, depth + i * .004, ink=ink, ink_depth=ink_depth, rim=.11)
        if parent is not None:
            p.parent = parent
        a = D(ph + 360 * (i + rnd.uniform(-.25, .25)) / count if ring else rnd.uniform(*ang))
        v = rnd.uniform(*speed)
        ca, sa = math.cos(a), math.sin(a)
        rr = rnd.uniform(*r0)
        x0, y0 = at[0] + rnd.uniform(-jitter[0], jitter[0]) + ca * rr, at[1] + rnd.uniform(-jitter[1], jitter[1]) + sa * rr
        t0 = f0 + rnd.uniform(0, stagger); L = rnd.uniform(*life); sz = rnd.uniform(*size); sp_ = rnd.uniform(-spin, spin)
        r_ = rnd.uniform(0, 6.3)
        for f in range(n):
            k_ = f - t0
            if k_ < 0 or k_ >= L or f == n - 1:
                key_piece(p, f, (x0, y0), 0, .001, 0)
                continue
            tt, u = k_ / FPS, k_ / L
            e = (1 - math.exp(-drag * tt)) / drag if drag else tt
            x, y = x0 + ca * v * e, y0 + sa * v * e - .5 * g * tt * tt
            pop = .55 + .55 * k_ if k_ < 1 else 1.1 - .1 * (k_ - 1) if k_ < 2 else 1.0
            s_ = sz * pop * (1 + grow * u) * (1 - span(u, .55, 1) ** 1.6)
            rot = math.atan2(sa * v * math.exp(-drag * tt) - g * tt, ca * v * math.exp(-drag * tt)) - math.pi / 2 if kind == 'drop' else r_ + sp_ * tt
            lim = box / 2 - .34 - s_ * 1.25
            key_piece(p, f, (clamp(x, -lim, lim), clamp(y, -lim, lim)), rot, max(.001, s_), 1 - span(u, 1 - fade, 1) ** 2)
        made.append(p)
    return made


def star(sc, stage, n, rnd, at, f0, life=7, size=1.2, col=W, depth=2.7, parent=None, ink=True, turn=.7):
    """A cartoon glint: a four-point star that pops (past its size, back), turns a little and snaps shut. Not a line
    of light crossing the picture: it stays on its spot. `parent`: an anchor() riding the picture."""
    g = piece(sc, stage, 'twinkle', col, rnd, depth, ink=ink, rim=.11)
    if parent is not None:
        g.parent = parent
    for f in range(n):
        u = (f - f0) / life
        on = 0 <= u < 1 and f < n - 1
        s = size * K(u, [(0, .3), (.3, 1.15, 'out'), (.5, 1.0), (1, 0, 'in')]) if on else 0
        key_piece(g, f, at, turn * u if on else 0, max(.001, s), 1.0 if on else 0.0)
    return g


class FX:
    """What a clip's effects are made with: the scene, the rig and where a point of the picture is at a frame."""
    def __init__(self, sc, stage, arm, info, S, n, rnd, box):
        self.sc, self.stage, self.arm, self.info, self.S, self.n, self.rnd, self.box = sc, stage, arm, info, S, n, rnd, box
        self.anchors = {}

    def at(self, px, f=None, bone='s0'):
        """A picture point (px) in the stage's XY: at rest, or where the keyed rig has carried it at frame f."""
        v = U(self.info, px)
        if f is not None:
            self.sc.frame_set(int(round(f)))
            pb = self.arm.pose.bones[bone]
            v = self.arm.matrix_world @ pb.matrix @ self.arm.data.bones[bone].matrix_local.inverted() @ v
        return (v.x, v.z)

    def anchor(self, bone='s0'):
        """An empty riding a bone, standing as the stage stands: a piece parented to it stays on the picture."""
        if bone not in self.anchors:
            a = bpy.data.objects.new('anchor_' + bone, None)
            self.sc.collection.objects.link(a)
            b = self.arm.data.bones[bone]
            a.parent = self.arm; a.parent_type = 'BONE'; a.parent_bone = bone
            a.matrix_parent_inverse = (b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
            a.rotation_euler = (D(90), 0, 0)
            self.anchors[bone] = a
        return self.anchors[bone]

    def spray(self, kind, cols, count, at, f0, **kw):
        kw.setdefault('box', self.box)
        if kind not in ('cloud', 'smoke', 'puff', 'flame') and 'size' in kw:   # a symbol is 60-110 px on a phone: the small
            kw['size'] = (kw['size'][0] * BOLD, kw['size'][1] * BOLD)          # bits are drawn bold enough to be seen there
        if not kw.get('drag') and kw.get('g', 9.) > 0 and 'speed' in kw:       # and what is thrown is thrown hard: it leaves
            kw['speed'] = (kw['speed'][0] * SNAP, kw['speed'][1] * SNAP)       # fast and far, an arc and not a slow float
            kw['g'] = kw.get('g', 9.) * 1.25
        return spray(self.sc, self.stage, self.n, self.rnd, kind, cols, count, at, f0, **kw)

    def star(self, px, f0, life=7, size=1.2, col=W, bone='s1', **kw):
        """A glint on a point of the picture, riding it."""
        x, y = P2(self.info, px)
        size = max(.3, min(size, (self.box / 2 - .4 - max(abs(x), abs(y)) * 1.13) / 1.15))   # near the picture's edge: as big as
        return star(self.sc, self.stage, self.n, self.rnd, (x, y), f0, life, size, col, parent=self.anchor(bone), **kw)   # the box has room for

    def snow(self, x, y, f0, side, count=2, flakes=4, size=(.5, .75)):
        """Snow kicked up from the ground at (x, y), to one side: lumps of powder, and flakes thrown over them."""
        a = (8, 50) if side > 0 else (130, 172)
        self.spray('cloud', [W, '#EAF3FF'], count, (x, y), f0, ang=a, speed=(4, 6.5), g=2, drag=5, size=size, life=(7, 10),
                   stagger=1, spin=1.5, grow=.5, depth=.6, ink_depth=.5)
        if flakes:
            self.spray('snow', [W, '#DCEBFF'], flakes, (x, y), f0, ang=(25, 80) if side > 0 else (100, 155), speed=(5.5, 9), g=19,
                       size=(.24, .4), life=(8, 11), depth=1.6)


# ---------------------------------------------------------------- the win: every symbol its own move
# A move is its pose at frame f of 28: the root bone (rot, sx across, sy along, y along - about the point the symbol
# stands on or hangs from), the spine's own curve (bend, per link), the whole rig about the icon's centre (orot, os,
# ox, oz) and its loose parts' leads (parts: name -> turn or (turn, wide, long); the physics follows the lead; a part
# the move does not name trails the body by itself). Anticipation, the action, an overshoot, a settle - and the
# clip's box (13 units for a picture of 10) is the stage, so the big ones turn, flip and swell where a jump has no room.
def mv_heli(f):        # H1 the skis: a crouch, a wind-up, a HELICOPTER - one full turn in the air - and a stomped landing
    return dict(sx=K(f, [(0, 1), (4, 1.13), (7, .93, 'out'), (10, 1), (17, 1), (19, 1.17, 'in'), (22, .95), (25, 1.02), (27, 1)]),
                sy=K(f, [(0, 1), (4, .82), (7, 1.12, 'out'), (10, 1), (17, 1), (19, .8, 'in'), (22, 1.07), (25, .98), (27, 1)]),
                orot=D(K(f, [(0, 0), (4, 20), (6, 9, 'in'), (17, -348, 'lin'), (19, -373, 'out'), (22, -355), (25, -360)])),
                os=K(f, [(0, 1), (5, 1), (9, .85), (15, .85), (18, 1.0, 'in'), (20, 1.09, 'out'), (23, .98), (26, 1)]),
                oz=K(f, [(0, 0), (5, 0), (11, .3, 'out'), (17, 0, 'in')]))


def mv_jar(f):         # H2 the jar: pressure builds, the heap of bud springs out of its neck like a jack-in-the-box
    wob = shake(f, 11, 6.5, .17)
    return dict(sx=K(f, [(0, 1), (5, 1.14), (8, 1.08), (11, .95, 'out'), (14, 1.03), (17, .99), (20, 1)]),
                sy=K(f, [(0, 1), (5, .82), (8, .9), (11, 1.06, 'out'), (14, .97), (17, 1.02), (20, 1)]),
                oz=K(f, [(0, 0), (5, 0), (8, .5, 'out'), (11, 0, 'in')]),
                rot=D(3) * wob, bend=[D(2.6 * (i + 1)) * wob for i in range(3)],
                parts=dict(heap=(D(K(f, [(0, 0), (8, 0), (11, 10), (14, -8), (17, 5), (20, -2.5), (23, 0)])),
                                 K(f, [(0, 1), (5, 1.2), (8, .84, 'out'), (11, 1.12), (14, .96), (17, 1.02), (20, 1)]),
                                 K(f, [(0, 1), (5, .6), (8, 1.55, 'out'), (11, .88), (14, 1.16), (17, .96), (20, 1.02), (23, 1)]))))


def mv_ollie(f):       # H3 the snowboard: presses its tail, pops an ollie flexing like a bow, lands in a rooster tail
    r = lambda q: K(q, [(0, 0), (5, -12), (9, 16, 'out'), (13, 7), (16, -7, 'in'), (19, 3.5), (22, -1.2), (25, 0)])
    return dict(rot=D(r(f)), bend=[D(.5 * i) * (r(f - 2) - r(f)) for i in range(3)],
                sy=K(f, [(0, 1), (5, .89), (9, 1.06, 'out'), (13, 1), (16, .9, 'in'), (19, 1.04), (22, .99), (25, 1)]),
                sx=K(f, [(0, 1), (5, 1.12), (9, .95, 'out'), (13, 1), (16, 1.12, 'in'), (19, .97), (22, 1.01), (25, 1)]),
                oz=K(f, [(0, 0), (5, 0), (10, .75, 'out'), (15, 0, 'in')]))


def mv_take(f):        # H4 the goggles: shrink back, pop out big, a double-take from side to side
    return dict(os=K(f, [(0, 1), (4, .84), (8, 1.17, 'out'), (11, 1.1), (19, 1.1), (23, .97), (26, 1)]),
                orot=D(K(f, [(0, 0), (4, 3), (8, -5), (11, 11), (14, -10), (17, 6.5), (20, -3.5), (23, 1.2), (25, 0)])),
                sx=K(f, [(0, 1), (4, 1.07), (8, .95, 'out'), (11, 1)]), sy=K(f, [(0, 1), (4, .88), (8, 1.08, 'out'), (11, 1)]))


def mv_slosh(f):       # L1 the cocoa: tips back, sloshes forward with a hop, rocks to rest; the steam stands tall
    r = lambda q: K(q, [(0, 0), (4, 8), (8, -10, 'out'), (12, 6), (16, -3.5), (20, 1.5), (23, 0)])
    return dict(rot=D(r(f)), bend=[0, D(.25) * (r(f - 2) - r(f)), D(.5) * (r(f - 2) - r(f))],
                sx=K(f, [(0, 1), (4, 1.1), (8, .97, 'out'), (12, 1.06), (15, .99), (18, 1)]),
                sy=K(f, [(0, 1), (4, .88), (8, 1.0, 'out'), (12, .94), (15, 1.01), (18, 1)]),
                parts=dict(steam=(D(.8) * (r(f - 2) - r(f)), K(f, [(0, 1), (4, .85), (9, 1.4, 'out'), (15, 1.12), (21, 1)]),
                                  K(f, [(0, 1), (4, .7), (9, 1.22, 'out'), (14, 1.08), (21, 1)]))))


def mv_drag(f):        # L2 the joint: draws back along its own length, jabs forward, the cherry flares
    return dict(y=K(f, [(0, 0), (5, -.62), (8, .55, 'out'), (12, -.14), (16, .04), (19, 0)]),
                sy=K(f, [(0, 1), (5, .9), (8, 1.07, 'out'), (12, .98), (16, 1)]),
                sx=K(f, [(0, 1), (5, 1.16), (8, .92, 'out'), (12, 1.05), (16, 1)]),
                rot=D(K(f, [(0, 0), (5, 5), (8, -6, 'out'), (12, 3), (16, -1.5), (20, 0)])),
                parts=dict(smoke=(D(K(f, [(0, 0), (5, -14), (9, 18, 'out'), (13, -9), (17, 4), (21, 0)])),
                                  K(f, [(0, 1), (5, .8), (9, 1.5, 'out'), (15, 1.15), (21, 1)]),
                                  K(f, [(0, 1), (5, .65), (9, 1.18, 'out'), (14, 1.06), (21, 1)]))))


def mv_stomp(f):       # L3 the brownie: squats flat, hops, lands HEAVY and quivers like a jelly
    wob = shake(f, 13, 6, .2)
    return dict(sx=K(f, [(0, 1), (5, 1.11), (8, .94, 'out'), (11, 1), (13, 1.16, 'in'), (16, .94), (19, 1.05), (22, .98), (25, 1)]),
                sy=K(f, [(0, 1), (5, .8), (8, 1.1, 'out'), (11, 1), (13, .76, 'in'), (16, 1.1), (19, .95), (22, 1.02), (25, 1)]),
                oz=K(f, [(0, 0), (5, 0), (9, .8, 'out'), (12.4, 0, 'in')]),
                bend=[D(2.4 * (i + 1)) * wob for i in range(3)])


def mv_boing(f):       # L4 the beanie: squashes down on its pom-pom, which springs up tall and wags on its thread
    sway = shake(f, 8, 7, .15)
    return dict(sx=K(f, [(0, 1), (5, 1.1), (8, .95, 'out'), (11, 1.04), (14, .98), (17, 1)]),
                sy=K(f, [(0, 1), (5, .84), (8, .97, 'out'), (11, 1.03), (14, .98), (17, 1)]),
                rot=D(-4) * sway, bend=[0, D(-2) * sway, D(-3) * sway],
                parts=dict(pom=(D(19) * shake(f, 8, 6, .13),
                                K(f, [(0, 1), (5, 1.32), (8, .84, 'out'), (11, 1.14), (14, .94), (17, 1.03), (20, 1)]),
                                K(f, [(0, 1), (5, .58), (8, 1.36, 'out'), (11, .86), (14, 1.12), (17, .96), (20, 1)]))))


def mv_swing(f):       # L5 the pizza: swings on its crust, the cheese stretching long at the end of each swing
    r = lambda q: K(q, [(0, 0), (4, -8), (9, 15), (14, -11), (18, 6), (22, -2.5), (25, 0)])
    st = K(f, [(0, 1), (4, 1.08), (9, 1.6), (11.5, 1.1), (14, 1.45), (16, 1.05), (18, 1.22), (22, 1.02), (25, 1)])
    return dict(rot=D(r(f)), bend=[0, D(.3) * (r(f - 2) - r(f)), D(.55) * (r(f - 2) - r(f))],
                parts={'*': (D(1.1) * (r(f - 2) - r(f)), 1 - .1 * (st - 1), st)})


def mv_flick(f):       # ZP the lighter: the thumb comes down, it sparks, the flame jumps up fat and flickers
    fl = K(f, [(0, 0), (6, 0), (7, 1), (19, 1), (24, 0)])
    return dict(sx=K(f, [(0, 1), (4, 1.13), (6, .96, 'out'), (9, 1.07), (19, 1.06), (23, 1)]),
                sy=K(f, [(0, 1), (4, .85), (6, .98, 'out'), (9, .9), (19, .92), (23, 1)]),
                rot=D(2.5) * shake(f, 6, 5, .2),
                parts=dict(flame=(D(7) * math.sin(f * 2.1) * fl,
                                  K(f, [(0, 1), (4, .75), (6, 1.75, 'out'), (9, 1.35), (12, 1.6), (15, 1.3), (18, 1.45), (21, 1.12), (24, 1)]),
                                  K(f, [(0, 1), (4, .5), (6, 1.3, 'out'), (8, 1.12), (10, 1.27), (12, 1.1), (14, 1.24), (16, 1.08), (18, 1.18), (21, 1.04), (24, 1)]))))


def mv_scratch(f):     # ST the silver ticket: it is SCRATCHED - a hard shiver, foil flying off - then it pops and swings
    env = K(f, [(0, 0), (3, 1), (11, 1), (14, 0)])
    return dict(ox=.34 * buzz(f, 2), rot=D(3.5) * buzz(f, 3) + D(9) * shake(f, 15, 8, .2),
                os=K(f, [(0, 1), (3, .95), (12, .93), (16, 1.14, 'out'), (20, 1.02), (23, .99), (26, 1)]),
                sy=1 + .03 * env)


def mv_yank(f):        # GT the gold ticket: yanked up on its string, drops, bounces like a yo-yo and swings out
    return dict(oz=K(f, [(0, 0), (4, -.3), (7, .62, 'out'), (11, -.26, 'in'), (14, .1), (17, 0)]),
                sy=K(f, [(0, 1), (4, 1.07), (7, .92, 'out'), (11, 1.1, 'in'), (14, .97), (17, 1.01), (20, 1)]),
                sx=K(f, [(0, 1), (4, .95), (7, 1.07, 'out'), (11, .93, 'in'), (14, 1.02), (17, 1)]),
                rot=D(K(f, [(0, 0), (7, 0), (10, 9), (14, -7.5), (18, 4.5), (22, -2), (25, 0)])),
                os=K(f, [(0, 1), (9, 1), (12, 1.07, 'out'), (16, 1.03), (22, 1)]))


def mv_rip(f):         # GP the ice bong: it bubbles and swells at the bulb, then RIPS - the neck springs up, vapour pours out
    return dict(ox=.085 * buzz(f, 1),
                sx=K(f, [(0, 1), (8, 1.1), (10, 1.17), (12, .93, 'out'), (15, 1.05), (18, .98), (21, 1.01), (24, 1)]),
                sy=K(f, [(0, 1), (8, .93), (10, .82), (12, .98, 'out'), (15, .9), (20, .93), (24, 1)]),
                rot=D(2.5) * shake(f, 12, 6, .2),
                parts=dict(wisp=(D(14) * shake(f, 11, 6, .15), K(f, [(0, 1), (11, 1), (14, 1.5, 'out'), (20, 1.1), (24, 1)]),
                                 K(f, [(0, 1), (11, 1), (14, 1.7, 'out'), (20, 1.15), (24, 1)]))))


def mv_throb(f):       # FDG the green bud: a heartbeat - lub, DUB - swelling from its middle
    return dict(os=K(f, [(0, 1), (3, .89), (6, 1.19, 'out'), (9, 1.0), (10, .97), (13, 1.14, 'out'), (16, .98), (19, 1.03), (22, 1)]),
                rot=D(K(f, [(0, 0), (6, -4), (9, 1), (13, 4), (16, -1), (20, 0)])),
                bend=[0, D(K(f, [(0, 0), (6, 3), (10, -1), (13, -3), (17, 1), (21, 0)])), D(K(f, [(0, 0), (6, 5), (10, -2), (13, -5), (17, 2), (21, 0)]))])


def mv_shimmy(f):      # FDA the amber bud: swells up and shakes itself like a maraca, its stars going off one by one
    return dict(os=K(f, [(0, 1), (4, .9), (8, 1.12, 'out'), (18, 1.1), (22, .98), (25, 1)]),
                orot=D(K(f, [(0, 0), (4, 3), (6, -10), (8, 10), (10, -9), (12, 9), (14, -7), (16, 5.5), (18, -3.5), (20, 1.8), (22, 0)])))


def mv_hops(f):        # FDR the red bud: a little hop to one side, a big one to the other, a stomp
    return dict(sx=K(f, [(0, 1), (3, 1.1), (5, .95, 'out'), (8, 1.1, 'in'), (10, .94, 'out'), (13, 1.02), (15, 1), (17, 1.17, 'in'), (20, .95), (23, 1.02), (26, 1)]),
                sy=K(f, [(0, 1), (3, .88), (5, 1.05, 'out'), (8, .88, 'in'), (10, 1.07, 'out'), (13, .96), (15, 1), (17, .8, 'in'), (20, 1.07), (23, .98), (26, 1)]),
                oz=K(f, [(0, 0), (3, 0), (5.5, .4, 'out'), (8, 0, 'in'), (12.5, .95, 'out'), (16.4, 0, 'in')]),
                rot=D(K(f, [(0, 0), (3, 0), (5.5, 5), (8, 0), (12.5, -7), (16.4, 0)])))


def mv_flip(f):        # BS the FS coin: tossed - a crouch, up, it flips over twice (never showing a back), lands and swells
    flip = max(.07, abs(math.cos(2 * math.pi * smooth(span(f, 6, 17)))))
    return dict(sx=flip * K(f, [(0, 1), (5, 1.14), (7, .93, 'out'), (10, 1), (17, 1), (19, 1.17, 'in'), (22, .95), (25, 1.02), (27, 1)]),
                sy=K(f, [(0, 1), (5, .82), (7, 1.08, 'out'), (10, 1), (17, 1), (19, .8, 'in'), (22, 1.07), (25, .98), (27, 1)]),
                oz=K(f, [(0, 0), (5, 0), (11, .95, 'out'), (18, 0, 'in')]),
                os=K(f, [(0, 1), (5, 1), (9, .9), (15, .9), (19, 1.0), (21, 1.1, 'out'), (24, .99), (27, 1)]))


def mv_wheel(f):       # DS the XFS coin: winds back, spins once round like a wheel of fortune, swelling, and locks in
    return dict(orot=D(K(f, [(0, 0), (5, 28), (7, 12, 'in'), (16, -344, 'lin'), (18, -374, 'out'), (21, -354), (24, -360)])),
                os=K(f, [(0, 1), (5, .9), (9, 1.12, 'out'), (16, 1.15), (18, 1.19), (21, .97), (24, 1.01), (27, 1)]))


# ...and its accent: what flies off it, timed to the move (c: FX)
def fx_heli(c):
    for side, px in ((-1, (250, 950)), (1, (780, 950))):
        x, y = c.at(px)
        c.snow(x, y, 18, side, count=2, flakes=5, size=(.55, .8))
    c.spray('spark', c.S['spark'], 6, (0, 0), 7, ring=True, r0=(3.6, 4.6), speed=(4, 7), drag=4, g=0, size=(.4, .62), life=(6, 8), stagger=8)
    c.star((170, 90), 19, 7, 1.35); c.star((800, 80), 21, 7, 1.1)


def fx_jar(c):
    top = c.at((512, 130), 8, 'heap0')
    c.spray('crumb', ['#58C431', '#8BE04A', '#3F9A22'], 9, top, 7.5, ang=(20, 160), speed=(6, 10), g=21, size=(.32, .5), life=(8, 11), jitter=(1.2, .3), stagger=1.5)
    c.spray('snow', [W, '#DCEBFF'], 5, top, 7.5, ang=(15, 165), speed=(3.5, 6), g=17, size=(.24, .38), life=(8, 11), jitter=(1.5, .3))
    c.star((300, 520), 12, 7, 1.15)


def fx_ollie(c):
    x, y = c.at((390, 930))
    c.spray('cloud', [W, '#EAF3FF'], 1, (x, y), 8, ang=(150, 175), speed=(3, 4), g=2, drag=5, size=(.45, .6), life=(6, 8), grow=.5, depth=.6)
    c.spray('cloud', [W, '#EAF3FF'], 4, (x, y), 15, ang=(118, 172), speed=(6, 10), g=2, drag=5, size=(.65, 1.0), life=(8, 11), grow=.5, depth=.6,
            ink_depth=.5, stagger=1.5)
    c.spray('snow', [W, '#DCEBFF'], 10, (x, y), 15, ang=(95, 160), speed=(7, 12), g=19, size=(.28, .46), life=(8, 11), stagger=2)
    c.star((700, 120), 10, 7, 1.15, bone='s2')


def fx_take(c):
    c.star((300, 440), 8.5, 8, 1.6); c.star((730, 470), 14, 7, 1.25)
    c.spray('spark', c.S['spark'], 6, (0, 0), 7.5, ring=True, r0=(3.6, 4.6), speed=(5, 8), drag=5, g=0, size=(.42, .66), life=(7, 9), stagger=1)


def fx_slosh(c):
    for px, a in (((270, 520), (100, 140)), ((650, 520), (40, 80))):   # the cocoa slops out over both sides of the rim
        c.spray('drop', ['#7A4424', '#9A5A30'], 3, c.at(px, 8, 's1'), 8, ang=a, speed=(6, 9), g=21, size=(.34, .48), life=(8, 10.5), jitter=(.5, .15), stagger=1.5)
    c.star((270, 730), 13, 7, 1.05)


def fx_drag(c):
    tip = c.at((770, 430), 8, 's2')
    c.spray('spark', [O, G, '#FFF2B8'], 7, tip, 8, ang=(-35, 100), speed=(8, 13), drag=4, g=9, size=(.42, .62), life=(7, 10), stagger=1.5)
    c.spray('cloud', ['#DDE2EA', '#C4CAD3'], 3, (tip[0] + .1, tip[1] + .4), 9, ang=(100, 165), speed=(5, 8), g=-2.5, drag=3, size=(.45, .62), life=(9, 12), grow=.8,
            stagger=6, spin=1.5, depth=1.8)


def fx_stomp(c):
    x, y = c.at((512, 965))
    c.spray('crumb', ['#B97A45', '#8A4B26', '#D29A62'], 7, c.at((512, 330)), 13, ang=(55, 125), speed=(7, 10.5), g=21, size=(.32, .48), life=(8, 11), jitter=(3.2, .3))
    for side in (-1, 1):
        c.snow(x + side * 4.0, y + .35, 13, side, count=2, flakes=3, size=(.45, .62))
    c.star((300, 170), 15, 7, 1.05)


def fx_boing(c):
    c.spray('snow', [W, '#EEF3FA'], 9, c.at((512, 150)), 7.5, ring=True, r0=(1.9, 2.4), speed=(3.5, 6.5), g=21, size=(.26, .42), life=(9, 12), stagger=2)
    c.spray('spark', [W, '#2BD9C5', G], 3, c.at((512, 170)), 8, ang=(30, 150), speed=(3, 5), drag=3, g=0, size=(.4, .55), life=(7, 9), jitter=(2., .5), stagger=3)


def fx_swing(c):
    for f0, a in ((9, (-45, 15)), (14, (165, 225))):
        c.spray('drop', ['#FFD400', '#FFB300'], 3, c.at((200, 930), f0, 's2'), f0, ang=a, speed=(5, 8), g=19, size=(.36, .5), life=(7, 9.5), stagger=1)
    c.spray('crumb', ['#E8912A', '#C9741C'], 4, c.at((640, 200)), 9, ang=(200, 340), speed=(2, 4), g=14, size=(.24, .36), life=(7, 9), jitter=(1.5, .3), stagger=5)
    c.star((330, 290), 11, 7, 1.0)


def fx_flick(c):
    base = c.at((505, 300), 6, 's2')
    for a in ((5, 55), (125, 175)):
        c.spray('spark', [G, '#FFF6CF', O], 4, base, 5.5, ang=a, speed=(7, 12), drag=3, g=10, size=(.4, .6), life=(7, 10), stagger=1.5)
    c.spray('flame', [O, G], 4, (base[0], base[1] + 1.2), 8, ang=(35, 145), speed=(3, 5), g=-3, size=(.4, .58), life=(6, 8), stagger=10, spin=0)


def fx_scratch(c):
    c.spray('confetti', ['#C9CED6', '#F2F4F7', '#FFD23C'], 12, c.at((512, 560)), 3, ang=(10, 170), speed=(8, 13), g=22, size=(.3, .46), life=(8, 11),
            jitter=(1.7, .6), stagger=9, spin=10)
    c.star((512, 520), 16, 8, 1.5); c.star((250, 320), 19, 6, .95)


def fx_yank(c):
    c.spray('spark', [G, '#FFF6CF', W], 8, (0, 0), 9.5, ring=True, r0=(3.3, 4.1), speed=(5, 8), drag=5, g=0, size=(.5, .75), life=(8, 11), stagger=1.5)
    c.star((250, 320), 12, 7, 1.3); c.star((790, 320), 16, 7, 1.05)


def fx_rip(c):
    c.spray('bubble', ['#EAF9FF', '#BDE8FC'], 6, c.at((511, 770)), 1, ang=(78, 102), speed=(3, 5), g=-2, size=(.2, .34), life=(5, 8), jitter=(.9, .5), stagger=8, depth=1.2)
    mouth = c.at((511, 60), 12, 's2')
    for a in ((-12, 38), (142, 192)):
        c.spray('cloud', ['#F4FAFF', '#D3E6F5'], 4, mouth, 11.5, ang=a, speed=(7, 11), drag=3.2, g=10, size=(.45, .68), life=(10, 14), grow=.8,
                stagger=4, spin=1.5, depth=1.8, ink_depth=1.7)
    c.spray('smoke', ['#F4FAFF'], 2, c.at((511, 470), 12, 's1'), 12, ang=(60, 120), speed=(2.5, 4), g=-2, size=(.35, .5), life=(8, 11), grow=.8, stagger=3, spin=1.5)
    c.spray('spark', [W, '#7FD4FF'], 4, (0, 0), 12, ring=True, r0=(3.2, 4.2), speed=(4, 6), drag=5, g=0, size=(.4, .6), life=(7, 9), stagger=2)
    c.star((425, 682), 13.5, 7, 1.15)


def fx_throb(c):
    for f0, k in ((5.5, 7), (12.5, 5)):
        c.spray('crumb', ['#39D62A', '#7CF55A', '#2A9E1F'], k, (0, 0), f0, ring=True, r0=(3.0, 3.9), speed=(5, 8), drag=4, g=7, size=(.3, .46), life=(7, 9), stagger=1)
    c.star((690, 290), 6, 7, 1.25); c.star((330, 660), 13, 6, 1.05)


def fx_shimmy(c):
    for i, px in enumerate([(880, 240), (170, 340), (190, 900)]):    # by its painted stars (inside them: the shake swings its corners out)
        c.star(px, 8 + 3 * i, 7, .95, col=G)
    c.spray('crumb', ['#FF9F1A', '#FFC24D', '#D97A0A'], 9, (0, -1.5), 7, ang=(180, 360), speed=(4, 7), g=16, size=(.3, .44), life=(8, 11), jitter=(3., 1.5), stagger=10,
            depth=-.6)


def fx_hops(c):
    x, y = c.at((512, 985))
    for f0, k, v, sz in ((8, 2, (4.5, 6.5), (.3, .44)), (17, 4, (6, 9), (.38, .6))):
        for side in (-1, 1):
            c.spray('spark', [O, '#FF5B66', G], k, (x + side * 2.4, y + .5), f0, ang=(20, 65) if side > 0 else (115, 160), speed=v, g=15, size=sz, life=(6, 9), stagger=1)
    for side in (-1, 1):
        c.snow(x + side * 2.8, y + .3, 17, side, count=1, flakes=0, size=(.45, .6))
    c.star((380, 310), 19, 7, 1.15)


def fx_flip(c):
    c.spray('spark', [G, '#FFF6CF', W], 10, (0, 0), 18.5, ring=True, r0=(3.9, 4.5), speed=(5, 8), drag=5, g=0, size=(.5, .75), life=(7, 9), stagger=1)
    x, y = c.at((512, 1000))
    for side in (-1, 1):
        c.snow(x + side * 2.6, y + .3, 18.5, side, count=1, flakes=0, size=(.45, .6))
    c.star((300, 190), 20, 7, 1.45); c.star((780, 760), 22.5, 5, 1.0)


def fx_wheel(c):
    c.spray('shard', ['#BFE9FF', '#39C6FF', W], 9, (0, 0), 7, ring=True, r0=(4.3, 4.8), speed=(4, 6.5), drag=5, g=0, size=(.32, .5), life=(5, 7), stagger=9, spin=9)
    c.star((300, 190), 19, 7, 1.45); c.star((780, 760), 21.5, 5.5, 1.0)


HIT = dict(heli=(mv_heli, fx_heli), jar=(mv_jar, fx_jar), ollie=(mv_ollie, fx_ollie), take=(mv_take, fx_take),
           slosh=(mv_slosh, fx_slosh), drag=(mv_drag, fx_drag), stomp=(mv_stomp, fx_stomp), boing=(mv_boing, fx_boing),
           swing=(mv_swing, fx_swing), flick=(mv_flick, fx_flick), scratch=(mv_scratch, fx_scratch), yank=(mv_yank, fx_yank),
           rip=(mv_rip, fx_rip), throb=(mv_throb, fx_throb), shimmy=(mv_shimmy, fx_shimmy), hops=(mv_hops, fx_hops),
           flip=(mv_flip, fx_flip), wheel=(mv_wheel, fx_wheel))


def clip_hit(sc, stage, arm, info, S, n, rnd, jig):
    sp = chain(arm, 's')
    move, accent = HIT[S['hit']]
    poses = [move(f) if f < n - 1 else {} for f in range(n)]          # the last frame is the rest pose, exactly
    turn = [p.get('rot', 0) + p.get('orot', 0) for p in poses]
    lift = [p.get('oz', 0) + 2 * (p.get('sy', 1) - 1) for p in poses]
    for f, p in enumerate(poses):
        bend = p.get('bend', ())
        key(sp[0], f, p.get('rot', 0) + (bend[0] if bend else 0), p.get('sx', 1), p.get('sy', 1), 0, p.get('y', 0))
        for i, pb in enumerate(sp[1:], 1):
            key(pb, f, bend[i] if i < len(bend) else 0, 1, 1)
        key_obj(arm, f, p.get('orot', 0), p.get('os', 1), p.get('ox', 0), p.get('oz', 0))
        parts = p.get('parts', {})

        def part(pi, li, ia, ka, f=f, parts=parts):
            if f == n - 1:
                return 0
            v = parts.get(S['parts'][pi][0], parts.get('*'))
            if v is not None and li:                                # posed by the move: each link a beat behind the last
                late = move(max(0, f - 1.3 * li)).get('parts', {})
                v = late.get(S['parts'][pi][0], late.get('*'))
            if v is None:                                           # not in the move: it trails the body's turn, and
                side = 1 if pi % 2 == 0 else -1                    # flaps as the body rises and falls
                return (clamp(-.7 * (turn[f] - turn[max(0, f - 2)]), -1.5 * ka, 1.5 * ka)
                        + ka * side * clamp(-1.3 * (lift[f] - lift[max(0, f - 2)]), -1, 1)) * (1 + .3 * li)
            if isinstance(v, tuple):
                return (v[0] * (1 + .3 * li), v[1], v[2])
            return v * (1 + .3 * li)
        key_parts(arm, S, f, part)
    posed = set().union(*(p.get('parts', {}) for p in poses))        # a part the move poses itself (a stretch, a spring) is
    for name, *_ in S.get('parts', []):                            # keyed, not simulated: the physics throws a part that is
        if name in posed or '*' in posed:                          # being scaled out of the picture's plane
            for pb in chain(arm, name):
                pb.jiggle.enable = False
                jig.pop(pb.name, None)
    sc.jiggle.enable = False                                        # (the effects look where the keyed rig is: no physics yet)
    accent(FX(sc, stage, arm, info, S, n, rnd, CLIPS['hit'][1]))
    sc.jiggle.enable = True


# ---------------------------------------------------------------- the exit: frozen, cracked, shattered
ICE = ['#EAF9FF', '#BDE8FC', '#6DC0EE']
CRACK, FLASH, BREAK = 4, 5, 6        # burn frames: the cracks show, the freeze flashes white, it bursts
SNAP = 1.6                           # ...and thrown this much harder
BOLD = 1.35                          # the sizes below were set on a big preview: what flies is this much bigger
RIM = .1                             # half a crack's ink line, icon units (the pictures' outlines are ~.15)


def clip_poly(poly, px, pz, nx, nz):
    """The part of a convex polygon on the near side of the line through P with normal N: (p - P) . N <= 0."""
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        da = (a[0] - px) * nx + (a[1] - pz) * nz
        db = (b[0] - px) * nx + (b[1] - pz) * nz
        if da <= 0:
            out.append(a)
        if (da < 0 < db) or (db < 0 < da):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def poly_object(sc, name, poly, origin, info, mat):
    """A flat polygon of the picture's plane (XZ) about `origin`, carrying the picture where it lies."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    fc = bm.faces.new([bm.verts.new((x - origin[0], 0, z - origin[1])) for x, z in poly])
    for lp, (x, z) in zip(fc.loops, poly):
        lp[uvl].uv = ((x / info['k'] + info['cx']) / info['iw'], (z / info['k'] + info['cy']) / info['h'])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def ice_shards(sc, ob, info, plan, rnd):
    """The picture cut into shards: the cells round seeds set in two rings (a few round the middle, more round the
    outside - cracks running out from a point, as a sheet of ice breaks), every edge straight. Each shard is two
    flat polygons carrying the picture: its cell in ink (so every crack is a black line, and only where the picture
    is), and the cell a rim narrower in the picture's own (frozen) colours on top. A shard turns about the middle
    of the picture it holds (c), and r is how far that picture reaches from there."""
    a, k = info['a'], info['k']
    ih, iw = a.shape
    w2, h2 = info['w'] / 2, info['hh'] / 2

    def solid(x, z):
        X, Y = int(x / k + info['cx']), int(z / k + info['cy'])
        return 0 <= X < iw and 0 <= Y < ih and a[Y, X] > .5
    seeds = []
    for count, rad in zip(plan['n'], (.3, .76)):
        ph = rnd.uniform(0, 2 * math.pi)
        for i in range(count):
            ang = ph + 2 * math.pi * (i + rnd.uniform(-.25, .25)) / count
            rr = rad * rnd.uniform(.82, 1.12)
            x, z = math.cos(ang) * rr * w2, math.sin(ang) * rr * h2
            for _ in range(16):                                     # onto the picture: in towards its middle
                if solid(x, z):
                    break
                x, z = x * .88 + rnd.uniform(-.2, .2), z * .88 + rnd.uniform(-.2, .2)
            if solid(x, z) and all((x - q[0]) ** 2 + (z - q[1]) ** 2 > 1.0 for q in seeds):
                seeds.append((x, z))
    tries = 0
    while len(seeds) < sum(plan['n']) - 1 and tries < 400:          # a picture with a hollow middle: anywhere on it
        tries += 1
        x, z = rnd.uniform(-w2, w2) * .9, rnd.uniform(-h2, h2) * .9
        if solid(x, z) and all((x - q[0]) ** 2 + (z - q[1]) ** 2 > 1.8 for q in seeds):
            seeds.append((x, z))
    # what each cell holds of the picture: every 6th pixel goes to its nearest seed
    ys, xs = np.nonzero(a[::6, ::6] > .5)
    px = np.stack([(xs * 6 - info['cx']) * k, (ys * 6 - info['cy']) * k], 1)
    sd = np.array(seeds)
    own = ((px[:, None, :] - sd[None, :, :]) ** 2).sum(2).argmin(1)
    rect = [(-w2 - .15, -h2 - .15), (w2 + .15, -h2 - .15), (w2 + .15, h2 + .15), (-w2 - .15, h2 + .15)]
    ink_mat = ink_material(ob.active_material)
    out = []
    for i, s in enumerate(seeds):
        mine = px[own == i]
        if len(mine) < 6:
            continue
        cell, inner = rect, rect
        for j, q in enumerate(seeds):
            if i == j or len(inner) < 3:
                continue
            dx, dz = q[0] - s[0], q[1] - s[1]
            ln = math.hypot(dx, dz)
            nx, nz, mx, mz = dx / ln, dz / ln, (s[0] + q[0]) / 2, (s[1] + q[1]) / 2
            cell = clip_poly(cell, mx, mz, nx, nz)
            inner = clip_poly(inner, mx - nx * RIM, mz - nz * RIM, nx, nz)
        if len(inner) < 3 or len(cell) < 3:
            continue
        c = (float(mine[:, 0].mean()), float(mine[:, 1].mean()))
        sh = poly_object(sc, 'shard', inner, c, info, ob.active_material)
        ink = poly_object(sc, 'shard_ink', cell, c, info, ink_mat)
        ink.parent = sh
        ink.location = (0, .004, 0)                                 # a hair behind its own shard, in front of the last
        r = float(np.sqrt(((mine - np.array(c)) ** 2).sum(1).max())) + .12
        out.append(dict(ob=sh, ink=ink, c=c, r=r))
    return out


def clip_burn(sc, stage, arm, ob, info, S, n, rnd):
    """It freezes and shatters. 0-3: a squash and a swell as frost grows in over it from its edges (the picture's own
    lines kept, its colours gone to ice); 4: it tightens and the cracks show; 5: it clenches smaller still in a white
    freeze flash; 6 on: it BURSTS - a ragged flash behind it, the shards thrown out fast from the break point,
    turning, hanging, falling and shrinking to nothing (never fading: no ghosts), chips of ice and of the symbol's
    own stuff flung past them, powder snow rolling out in a ring. 19 is empty."""
    plan = dict(n=(3, 7), at=None, bias=(0., 1.6), g=15., puffs=6, chips=10)
    plan.update(S.get('burn', {}))
    sp = chain(arm, 's')
    c = FX(sc, stage, arm, info, S, n, rnd, CLIPS['burn'][1])
    S4, S5 = .96, .87
    for f in range(n):
        live = 0 < f < CRACK
        key(sp[0], f, D(1.6) * buzz(f, 0) if live else 0,
            K(f, [(0, 1), (2, 1.1), (3, .97)]) if live else 1, K(f, [(0, 1), (2, .87), (3, 1.09)]) if live else 1)
        for pb in sp[1:]:
            key(pb, f, D(1.5) * buzz(f, 0) if live else 0)
        key_parts(arm, S, f, lambda pi, li, ia, ka: ka * .5 * buzz(f, 0) * (1 if pi % 2 == 0 else -1) if live else 0)
        key_obj(arm, f, 0, K(f, [(0, 1), (2, 1.0), (3, 1.05)]) if f < CRACK else 1)
        ob.color = (0, K(f, [(0, 0), (1, .5, 'lin'), (2, .74, 'lin'), (3, 1, 'lin')]), 0, 1 if f < CRACK else 0)
        ob.keyframe_insert('color', frame=f)
    # frost crystals pop on it as it freezes
    a, k = info['a'], info['k']
    for i in range(3):
        for _ in range(60):
            x, z = rnd.uniform(-info['w'], info['w']) * .36, rnd.uniform(-info['hh'], info['hh']) * .36
            if a[int(z / k + info['cy']), int(x / k + info['cx'])] > .5:
                break
        star(sc, stage, n, rnd, (x, z), .6 + i * .8, life=4.4, size=rnd.uniform(.8, 1.1), col=W, ink=False)
    # the shards
    o = U(info, plan['at']) if plan['at'] else Vector((0, 0, 0))
    LIM = CLIPS['burn'][1] / 2 - .34
    R = max(info['w'], info['hh']) / 2
    DRAG = 3.4
    shs = ice_shards(sc, ob, info, plan, rnd)
    for i, sh in enumerate(shs):
        cx, cz = sh['c']
        d = Vector((cx - o.x, cz - o.z))
        dist = d.length
        d = d.normalized() if dist > .3 else Vector((rnd.uniform(-1, 1), rnd.uniform(.2, 1))).normalized()
        last = rnd.uniform(16.2, 18.4)
        v = rnd.uniform(11, 15) * (.45 + .55 * min(1, dist / R))
        spin = rnd.uniform(3, 8) * rnd.choice((-1, 1))
        r = sh['r']

        def path(m, end):
            pts = []
            for f in range(BREAK, n):
                tt = (f - BREAK + 1) / FPS
                u = clamp((f - BREAK + 1) / (end - BREAK + 1))
                e = (1 - math.exp(-DRAG * tt)) / DRAG
                s_ = S5 * (1 - .2 * ease_out(span(u, 0, .4))) * (1 - span(u, .45, 1) ** 1.6)   # smaller as it flies off, then to nothing
                pts.append((cx * S5 + d.x * .1 + (d.x * v * m + plan['bias'][0]) * e,
                            cz * S5 + d.y * .1 + (d.y * v * m + plan['bias'][1]) * e - .5 * plan['g'] * tt * tt, s_, spin * tt))
            return pts
        inside = lambda pts: all(abs(x) + r * s_ <= LIM and abs(z) + r * s_ <= LIM for x, z, s_, _r in pts)
        # as fast as its box lets it go, and it keeps going: a shard that would reach the edge of its box is gone by
        # then (it shrinks out sooner), so nothing slows to a stop in the air and nothing slides along an edge
        for m in (1, .88, .76, .64, .52, .4, .3, .2, .1, 0):
            end = last
            pts = path(m, end)
            while not inside(pts) and end > BREAK + 6.6:
                end -= .6
                pts = path(m, end)
            if inside(pts):
                break
        y = -1.0 - i * .012
        for f in range(n):
            if f < CRACK or f == n - 1 or f - BREAK + 1 >= end - BREAK + 1:
                x, z, s_, rot, al, fl = cx, cz, .001, 0, 0, 0
            elif f == CRACK:
                x, z, s_, rot, al, fl = cx * S4 + d.x * .03, cz * S4 + d.y * .03, S4, 0, 1, 0
            elif f == FLASH:
                x, z, s_, rot, al, fl = cx * S5 + d.x * .04, cz * S5 + d.y * .04, S5, 0, 1, .93
            else:
                x, z, s_, rot = pts[f - BREAK]
                lim = max(0, LIM - r * s_)
                x, z, al, fl = clamp(x, -lim, lim), clamp(z, -lim, lim), 1, (.42, .06)[f - BREAK] if f - BREAK < 2 else 0
            o_ = sh['ob']
            o_.location = (x, y, z); o_.rotation_euler = (0, -rot, 0); o_.scale = (s_, 1, s_)
            o_.color = (fl, 0, 1, al)                               # iced through and through (blue: icon_material)
            for p in ('location', 'rotation_euler', 'scale', 'color'):
                o_.keyframe_insert(p, frame=f)
            sh['ink'].color = (0, 0, 0, al)
            sh['ink'].keyframe_insert('color', frame=f)
    at = (o.x * S5, o.z * S5)
    # the flash of the break: a ragged star of ice-light behind it, three frames
    fl = piece(sc, stage, 'burst', '#DFF4FF', rnd, .3, ink=False)
    lim = LIM - .05
    for f in range(n):
        s_ = {FLASH: 3.3, BREAK: 4.9, BREAK + 1: 5.6}.get(f, 0)
        s_ = min(s_, lim - abs(at[0]), lim - abs(at[1])) if s_ else 0
        key_piece(fl, f, at, .25 * (f - FLASH), max(.001, s_), 1.0 if s_ else 0.0)
    # powder snow rolling out behind the shards, chips of ice and of the symbol's own stuff flung past them
    own = [c_ for c_ in S.get('spark', []) if c_ not in (W, G)] or [G]
    c.spray('cloud', [W, '#EAF3FF'], plan['puffs'], at, BREAK - .5, ring=True, r0=(1.2, 2.4), speed=(8, 12), drag=4.5, g=-1., size=(.55, .9),
            grow=.5, life=(8.5, 11.2), stagger=1, spin=1.2, depth=.5, ink_depth=.4, jitter=(.3, .3))
    c.spray('shard', ICE + own, plan['chips'], at, BREAK - .6, ring=True, r0=(.8, 2.6), speed=(10, 16), drag=3.2, g=16, size=(.3, .5),
            life=(8, 11.6), stagger=.8, spin=11, depth=3.0, jitter=(.4, .4))
    kind, cols, _cnt = S['debris'][0]
    if kind in ('shard', 'smoke', 'flake'):                          # (more ice, or smoke, says nothing new: its next)
        kind, cols, _cnt = next((q for q in S['debris'] if q[0] not in ('shard', 'smoke', 'flake')), ('snow', [W, '#DCEBFF'], 0))
    c.spray(kind, cols, 7, at, BREAK - .4, ring=True, r0=(.5, 2.4), speed=(8, 13), drag=3.2, g=18, size=(.28, .44), life=(8, 11.4),
            stagger=1, spin=9, depth=3.2, jitter=(.4, .4))
    for i in range(4):                                              # and a few flakes that hang and twinkle out
        ang = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(3.4, 4.9)
        star(sc, stage, n, rnd, (math.cos(ang) * rr, math.sin(ang) * rr), BREAK + 1.5 + i * 1.3, life=rnd.uniform(5, 6.2),
             size=rnd.uniform(.75, 1.05), col=W, ink=False, depth=3.5)


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
        clip_hit(sc, stage, arm, info, S, n, rnd, jig)
    else:
        clip_burn(sc, stage, arm, ob, info, S, n, rnd)
        jig.clear()                                                 # three frames of shiver, keyed: no physics, so its
        arm.jiggle.enable = False                                   # first frame is the rest pose to the pixel (a hanging
        sc.jiggle.enable = False                                    # part's sag showed as a twitch as the clip cut in)
    bake_jiggle(sc, arm, jig, n)
    stats['fit'] = fit_box(sc, ob, arm, info, n, box / 2 - .32)   # (the exit too: its swell before the break stays in its box)
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
