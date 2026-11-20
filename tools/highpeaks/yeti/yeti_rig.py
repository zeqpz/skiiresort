"""High Peaks: the yeti as a 2D cut-out rig in Blender - his pieces (art/highpeaks/yeti/parts, yeti_parts.py) on a
skeleton, every clip keyed here, exported as a LIVE rig the game poses itself every screen refresh (frontend/yeti.js),
plus QA renders. Flat cartoon: every piece is an emission-lit picture on a grid mesh in the XZ plane, seen by an
orthographic camera - no 3D shading anywhere.

Skeleton (art px of the 1024 x 1536 master, y down; 100 art px = 1 Blender unit):
  root > hips > spine > chest (breathes) ; spine > belly (jiggles on landings)
  chest > neck > head > face (slides the features: a glance) ; head > hat (the beanie) > pom (the pom-pom, on a spring)
  chest > clav_l > upper_l > fore_l > hand_l   - IK: the hand rests on the snowboard (target on the root)
  chest > clav_r > upper_r > fore_r > hand_r   - FK, keyed angles: the joint arm is two pieces (upper arm behind
                                                 the head, forearm + hand in front of it), so the joint to his lips is
                                                 a forearm crossing over its upper arm, never a crumpled sleeve
  hips > thigh > shin > foot (IK to ankle targets on the root: the boots stay planted unless he jumps)
  root > board (the snowboard stuck in the snow)
The board hand and the boots keep their own angle in the world (no inherited turn); the joint hand turns with its
forearm. The board arm's IK lets go (influence keyed) when he throws his arms up.

Clips (30 fps): idle (8 s loop: breathing, weight shift, blinks, a glance, a slow puff on the joint and the exhale),
win, big_win, bonus, lose (one-shots that start and end on the rest pose) and anticipation (a 2 s LOOP the game holds
while it waits for the last FS: leaning in, wide-eyed, sweating, gripping the board).

In the live Blender (MCP):  import importlib.util,sys; spec=importlib.util.spec_from_file_location("yeti_rig", P);
  m=importlib.util.module_from_spec(spec); sys.modules["yeti_rig"]=m; spec.loader.exec_module(m); m.run(["build"]) ...
Headless:  blender -b --factory-startup --python tools/highpeaks/yeti/yeti_rig.py -- build,animate,export,render
-> art/highpeaks/yeti/rig_build/yeti_rig.blend, rig/ (rig.json, geo.bin, <clip>.bin), renders/<clip>/"""
import json, math, os, random, struct, sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
ART = os.path.join(ROOT, "art", "highpeaks", "yeti")
PARTS = os.path.join(ART, "parts")
FX = os.path.join(ART, "fx")
OUT = os.path.join(ART, "rig_build")
META = json.load(open(os.path.join(PARTS, "parts.json")))
K = META["scale"]                                 # plate px per art px
W_PX, H_PX = META["art"]                          # 1024 x 1536
FPS = 30
RES = (640, 960)
ORTHO = 16.4
CAM_Z = -0.2
GROUND = 1509                                     # art px: the snow mound's lowest line
TOP = 46                                          # the pom-pom's top

CLIPS = {"idle": (240, True), "anticipation": (60, True), "win": (60, False), "big_win": (120, False),
         "bonus": (150, False), "lose": (90, False)}
FACES = ["neutral"] + list(META["faces"])
TIP = (950, 437)                                  # the joint's lit tip: the ember's centre (art px, on hand_r)
JOINT_END = (789.5, 502.7)                        # the joint's mouth end, drawn on out of his fist (yeti_parts joint)
LIPS = (565, 472)                                 # the pursed lips of the "puff" face (on the face bone)
MOUTH = (500, 480)                                # where an exhale leaves his (open) mouth
BROW = (585, 300)                                 # where the sweat bead starts
# a hit on the joint: frames (in, hold from, hold to, out) where the joint's end is put ON his lips (contact())
CONTACT = {"idle": [(106, 116, 142, 152)]}


def u(x, y):
    return ((x - W_PX / 2) / 100.0, (H_PX / 2 - y) / 100.0)


def art(X, Z):
    return (100 * X + W_PX / 2, H_PX / 2 - 100 * Z)


ELBOW_R = (762, 715)                              # the centre of the joint arm's elbow ring (art px)

# name, head, tail, parent, options (art px)
BONES = [
    ("root", (512, 1509), (512, 1449), None, {}),
    ("hips", (520, 1060), (520, 1000), "root", {}),
    ("spine", (520, 1000), (520, 820), "hips", {"connect": True}),
    ("chest", (520, 820), (515, 620), "spine", {"connect": True}),
    ("belly", (520, 880), (520, 980), "spine", {}),
    ("neck", (515, 620), (500, 560), "chest", {"connect": True, "noscale": True}),
    ("head", (500, 560), (470, 300), "neck", {"connect": True}),
    ("face", (480, 420), (480, 360), "head", {}),
    ("hat", (450, 290), (370, 130), "head", {}),
    ("pom", (330, 150), (310, 70), "hat", {}),
    ("clav_l", (480, 600), (380, 545), "chest", {"noscale": True}),
    ("upper_l", (380, 545), (150, 640), "clav_l", {"connect": True}),
    ("fore_l", (150, 640), (135, 750), "upper_l", {"connect": True}),
    ("hand_l", (135, 750), (140, 840), "fore_l", {"connect": True, "norot": True, "noscale": True}),
    ("clav_r", (560, 600), (660, 575), "chest", {"noscale": True}),
    # the elbow turns about the MIDDLE of the round ring at the bend (2026-11-20): the forearm piece's ring then turns
    # in place over the upper arm's end, so no see-through wedge opens at the elbow however far it bends
    ("upper_r", (660, 575), ELBOW_R, "clav_r", {"connect": True}),
    ("fore_r", ELBOW_R, (860, 630), "upper_r", {"connect": True}),
    ("hand_r", (860, 630), (860, 470), "fore_r", {"connect": True, "noscale": True}),
    ("thigh_l", (400, 1030), (345, 1200), "hips", {}),
    ("shin_l", (345, 1200), (320, 1330), "thigh_l", {"connect": True}),
    ("foot_l", (320, 1330), (270, 1440), "shin_l", {"connect": True, "norot": True, "noscale": True}),
    ("thigh_r", (640, 1030), (690, 1200), "hips", {}),
    ("shin_r", (690, 1200), (720, 1330), "thigh_r", {"connect": True}),
    ("foot_r", (720, 1330), (760, 1440), "shin_r", {"connect": True, "norot": True, "noscale": True}),
    ("board", (128, 1460), (128, 790), "root", {}),
    ("ik_l", (320, 1330), (320, 1270), "root", {}),
    ("ik_r", (720, 1330), (720, 1270), "root", {}),
    ("ik_hand_l", (135, 750), (135, 690), "root", {}),
]
BONE = {b[0]: b for b in BONES}
DEFORM = [b[0] for b in BONES if not b[0].startswith("ik_")]
CELL = {"board": 22, "snow": 24, "leg_l": 12, "leg_r": 12, "body": 12, "arm_l": 10, "arm_r_up": 10, "arm_r_lo": 10,
        "head": 10, "face": 10}


# ---------------------------------------------------------------- weights

def seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / max(1e-9, dx * dx + dy * dy)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy), t


def soft(p, names, sigma):
    w = {}
    for n in names:
        d, _ = seg(p, BONE[n][1], BONE[n][2])
        w[n] = math.exp(-(d / sigma) ** 2)
    s = sum(w.values()) or 1.0
    return {k: v / s for k, v in w.items()}


def smooth(e0, e1, v):
    t = max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def norm(w):
    w = {k: v for k, v in w.items() if v > 1e-4}
    s = sum(w.values()) or 1.0
    return {k: v / s for k, v in w.items()}


ELBOW_CUT = [(712, 380), (712, 566), (722, 596), (720, 622), (705, 652), (678, 688), (663, 740), (674, 786), (698, 822)]
HINGE = 0                                                     # art px of the forearm piece hinged to the upper arm (off:
                                                              # the elbow turns about its ring's middle, see ELBOW_R; the
                                                              # hinge only stretched the forearm's edge into a smear)


def cut_dist(x, y):
    """How far (art px) a point lies from the elbow cut (yeti_parts.ELBOW_CUT), only counting its elbow stretch (below
    the cuff: the cuff itself rides the hand)."""
    best = 1e9
    for a, b in zip(ELBOW_CUT[4:], ELBOW_CUT[5:]):
        d, _ = seg((x, y), a, b)
        best = min(best, d)
    return best


def weights(part, x, y):
    p = (x, y)
    if part == "board":
        return {"board": 1.0}
    if part == "snow":
        return {"root": 1.0}
    if part in ("head", "face"):
        wn = .6 * smooth(540, 600, y)                         # the ruff's lowest tufts lean on the neck
        pom = smooth(88, 62, math.hypot(x - 318, y - 100))
        yl = 320 - .3 * (x - 280)                             # the beanie's lower edge (rising to the right)
        hat = smooth(yl + 26, yl - 26, y) * (1 - pom)
        f = .9 * math.exp(-((x - 485) / 115.0) ** 2 - ((y - 425) / 95.0) ** 2) * max(0.0, 1 - hat - pom)
        hd = max(0.0, 1 - pom - hat - f)
        return norm({"neck": wn, "head": hd * (1 - wn), "hat": hat * (1 - wn), "pom": pom * (1 - wn), "face": f * (1 - wn)})
    if part in ("leg_l", "leg_r"):
        s = part[-1]
        top = smooth(1000, 1060, y)
        kn = smooth(1150, 1240, y)
        ka = smooth(1285, 1335, y)                            # the boot is rigid: all foot
        return norm({"hips": 1 - top, f"thigh_{s}": top * (1 - kn), f"shin_{s}": top * kn * (1 - ka), f"foot_{s}": top * ka})
    if part == "body":
        kc, ks = smooth(660, 760, y), smooth(900, 990, y)
        w = {"chest": 1 - kc, "spine": kc * (1 - ks), "hips": kc * ks}
        cl = (1 - smooth(300, 390, x)) * (1 - smooth(560, 650, y)) * .85
        cr = smooth(645, 735, x) * (1 - smooth(560, 650, y)) * .85
        kn = (1 - smooth(500, 548, y)) * smooth(400, 440, x) * (1 - smooth(600, 640, x)) * .7
        wb = .55 * math.exp(-((x - 520) / 120.0) ** 2 - ((y - 935) / 90.0) ** 2)
        rest = max(0.0, 1 - cl - cr - kn - wb)
        w = {k: v * rest for k, v in w.items()}
        w.update(clav_l=cl, clav_r=cr, neck=kn, belly=wb)
        return norm(w)
    if part == "arm_l":
        d = math.hypot(x - 380, y - 545)
        if d < 75:
            k = smooth(75, 20, d)
            return norm({"upper_l": 1 - .6 * k, "clav_l": .6 * k})
        if y > 715 and x < 280:                               # the cuff and the hand
            k = smooth(715, 770, y)
            w = soft(p, ["upper_l", "fore_l"], 40)
            return norm({kk: v * (1 - k) for kk, v in w.items()} | {"hand_l": k})
        return soft(p, ["upper_l", "fore_l"], 40)
    if part == "arm_r_up":                                    # shoulder to elbow: rigid on the upper arm
        d = math.hypot(x - 660, y - 575)
        k = smooth(75, 20, d)
        return norm({"upper_r": 1 - .6 * k, "clav_r": .6 * k})
    if part == "arm_r_lo":                                    # the elbow ring and forearm, then the cuff, hand, joint
        k = smooth(668, 616, y)
        w = {"fore_r": 1 - k, "hand_r": k}
        # the hinge: within HINGE art px of the cut the piece rides the upper arm, so its cut edge never lifts off
        # the upper piece (no see-through wedge opens at the elbow, whichever way it bends)
        d = cut_dist(x, y)
        hz = (1 - smooth(4, HINGE, d)) if HINGE else 0.0
        if hz > 0:
            w = {kk: v * (1 - hz) for kk, v in w.items()}
            w["upper_r"] = w.get("upper_r", 0) + hz
        return norm(w)
    raise KeyError(part)


# ---------------------------------------------------------------- scene

def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.actions,
                 bpy.data.cameras, bpy.data.lights):
        for b in list(coll):
            coll.remove(b)


def setup():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    try:
        sc.eevee.taa_render_samples = 8
    except AttributeError:
        pass
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ORTHO
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    cam.location = (0, -30, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    if sc.world is None:
        sc.world = bpy.data.worlds.new("world")


def load(path):
    im = bpy.data.images.get(os.path.basename(path)) or bpy.data.images.load(path)
    im.alpha_mode = "STRAIGHT"
    return im


def material(name, path, strength=1.0):
    """Emission (the art is flat) with the texture's alpha, times a keyable 'fade'."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = load(path)
    tex.interpolation = "Cubic"
    tex.extension = "CLIP"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    fade = nt.nodes.new("ShaderNodeValue")
    fade.name = "fade"
    fade.outputs[0].default_value = 1.0
    am = nt.nodes.new("ShaderNodeMath")
    am.operation = "MULTIPLY"
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], am.inputs[0])
    nt.links.new(fade.outputs[0], am.inputs[1])
    nt.links.new(am.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def build_rig():
    ad = bpy.data.armatures.new("yeti")
    arm = bpy.data.objects.new("yeti", ad)
    bpy.context.scene.collection.objects.link(arm)
    for ob in list(bpy.context.view_layer.objects):
        if ob is not None and ob.name in bpy.data.objects:
            ob.select_set(False)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, par, opt in BONES:
        b = ad.edit_bones.new(name)
        hx, hz = u(*h)
        tx, tz = u(*t)
        b.head, b.tail = (hx, 0, hz), (tx, 0, tz)
        b.align_roll((0, -1, 0))          # local Z faces the camera: a turn about Z stays in the picture plane
        b.use_deform = name in DEFORM
    for name, h, t, par, opt in BONES:
        if par:
            eb = ad.edit_bones[name]
            eb.parent = ad.edit_bones[par]
            eb.use_connect = bool(opt.get("connect"))
            if opt.get("norot"):
                eb.use_inherit_rotation = False
            if opt.get("noscale"):
                eb.inherit_scale = "NONE"
    bpy.ops.object.mode_set(mode="OBJECT")
    ad.display_type = "STICK"
    arm.show_in_front = True
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    for chain, target in ((("thigh_l", "shin_l"), "ik_l"), (("thigh_r", "shin_r"), "ik_r"),
                          (("upper_l", "fore_l"), "ik_hand_l")):
        for nm in chain:
            pb = arm.pose.bones[nm]
            pb.lock_ik_x = pb.lock_ik_y = True
            pb.ik_stretch = .04
        c = arm.pose.bones[chain[1]].constraints.new("IK")
        c.target, c.subtarget = arm, target
        c.chain_count = 2
        c.use_tail = True
        c.use_stretch = True
    return arm


def grid_mesh(name, path, box_plate, cell, wfn, depth, arm, mat):
    """A mesh fitted to a part's pixels: a grid of `cell` art px over its box, only the cells with ink (and a ring
    round them), UVs onto the part's texture, weights from wfn."""
    import numpy as np
    img = load(path)
    tw, th = img.size
    arr = np.empty(tw * th * 4, np.float32)
    img.pixels.foreach_get(arr)
    alpha = arr[3::4].reshape(th, tw)[::-1]                # top row first
    x0, y0, w, h = [v / K for v in box_plate]
    nx, ny = max(1, math.ceil(w / cell)), max(1, math.ceil(h / cell))
    used = set()
    for j in range(ny):
        r0, r1 = int(j * cell * K), min(th, int(math.ceil((j + 1) * cell * K)))
        row = alpha[r0:r1]
        if not row.size:
            continue
        for i in range(nx):
            c0, c1 = int(i * cell * K), min(tw, int(math.ceil((i + 1) * cell * K)))
            blk = row[:, c0:c1]
            if blk.size and blk.max() > .01:
                used.add((i, j))
    ring = {(i + di, j + dj) for (i, j) in used for di in (-1, 0, 1) for dj in (-1, 0, 1)}
    used = {(i, j) for (i, j) in ring if 0 <= i < nx and 0 <= j < ny}
    vid, verts, uvs, faces = {}, [], [], []

    def v(i, j):
        if (i, j) not in vid:
            ax = x0 + min(i * cell, w)
            ay = y0 + min(j * cell, h)
            vid[(i, j)] = len(verts)
            X, Z = u(ax, ay)
            verts.append((X, 0.0, Z))
            uvs.append(((ax - x0) / w, 1 - (ay - y0) / h))
        return vid[(i, j)]

    for (i, j) in sorted(used):
        faces.append((v(i, j + 1), v(i + 1, j + 1), v(i + 1, j), v(i, j)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0, depth, 0)
    groups = {}
    for vi, (X, _, Z) in enumerate(verts):
        ax, ay = art(X, Z)
        for bn, wt in wfn(ax, ay).items():
            if wt < .004:
                continue
            g = groups.get(bn) or ob.vertex_groups.new(name=bn)
            groups[bn] = g
            g.add([vi], wt, "REPLACE")
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    ob.parent = arm
    return ob


FX_KINDS = (("snowpuff", 8, 220), ("spark", 16, 110))          # keyed here; smoke / ember / sweat are live (LIVE_FX)
LIVE_FX = {"smoke": 150, "ember": 72, "sweat": 70}              # sprite sizes, art px
EMITS = {}                                                     # clip -> [[frame, kind]] (kinds: wisp, exhale, sweat)


def set_fade(ob, f, v):
    s = ob.active_material.node_tree.nodes["fade"].outputs[0]
    s.default_value = v
    s.keyframe_insert("default_value", frame=f)


def build():
    clear()
    setup()
    arm = build_rig()
    parts = {}
    for i, nm in enumerate(META["order"]):
        path = os.path.join(PARTS, nm + ".png")
        depth = .4 - i * .05                               # back to front, toward the camera
        parts[nm] = grid_mesh(nm, path, META["parts"][nm]["box"], CELL[nm], lambda x, y, n=nm: weights(n, x, y),
                              depth, arm, material(nm, path))
    faces = {}
    hd = .4 - META["order"].index("head") * .05 - .01
    for f, info in META["faces"].items():
        path = os.path.join(PARTS, f"face_{f}.png")
        ob = grid_mesh("face_" + f, path, info["box"], CELL["face"], lambda x, y: weights("face", x, y), hd, arm,
                       material("face_" + f, path))
        set_fade(ob, 0, 0.0)
        faces[f] = ob
    faces["neutral"] = parts["head"]
    fx = {}
    for kind, n, size in FX_KINDS:
        fx[kind] = []
        for i in range(n):
            me = bpy.data.meshes.new(f"{kind}_{i}")
            s = size / 200.0
            me.from_pydata([(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)], [], [(0, 1, 2, 3)])
            uvl = me.uv_layers.new(name="UVMap")
            for li, uv in zip(me.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
                uvl.data[li].uv = uv
            me.materials.append(material(f"{kind}_{i}", os.path.join(FX, kind + ".png")))
            ob = bpy.data.objects.new(f"{kind}_{i}", me)
            bpy.context.scene.collection.objects.link(ob)
            ob.location = (0, -1.0 - .01 * i - (.5 if kind == "ember" else 0), 0)
            ob["fx"] = kind
            ob["fx_size"] = size
            set_fade(ob, 0, 0.0)
            fx[kind].append(ob)
    os.makedirs(OUT, exist_ok=True)
    return arm, parts, faces, fx


# ---------------------------------------------------------------- keys

class Spring:
    def __init__(self, freq, zeta):
        self.w, self.z = 2 * math.pi * freq, zeta
        self.x = self.v = 0.0

    def snap(self, target):
        self.x, self.v = target, 0.0
        return target

    def step(self, target, dt=1 / FPS, sub=8):
        for _ in range(sub):
            h = dt / sub
            a = self.w * self.w * (target - self.x) - 2 * self.z * self.w * self.v
            self.v += a * h
            self.x += self.v * h
        return self.x


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def kf(x, *keys):
    """Pose to pose on a shape-preserving cubic (PCHIP) through the keys (frame, value[, "i"]): through a key on the
    way without slowing, round an extreme at rest; held before the first key and after the last; a key tagged "i" is
    an impact (falls onto it gathering speed and stops dead)."""
    n = len(keys)
    if x <= keys[0][0]:
        return keys[0][1]
    if x >= keys[-1][0]:
        return keys[-1][1]
    k = 0
    while x > keys[k + 1][0]:
        k += 1
    x0, y0 = keys[k][0], keys[k][1]
    x1, y1 = keys[k + 1][0], keys[k + 1][1]
    h = max(1e-9, x1 - x0)
    t = (x - x0) / h
    if len(keys[k + 1]) > 2 and keys[k + 1][2] == "i":
        return y0 + (y1 - y0) * t ** 2.2

    def slope(j):
        if j <= 0 or j >= n - 1:
            return 0.0
        if (len(keys[j]) > 2 and keys[j][2] == "i") or (len(keys[j + 1]) > 2 and keys[j + 1][2] == "i"):
            return 0.0
        ha, hb = keys[j][0] - keys[j - 1][0], keys[j + 1][0] - keys[j][0]
        da, db = (keys[j][1] - keys[j - 1][1]) / max(1e-9, ha), (keys[j + 1][1] - keys[j][1]) / max(1e-9, hb)
        if da * db <= 0:
            return 0.0
        w1, w2 = 2 * hb + ha, hb + 2 * ha
        return (w1 + w2) / (w1 / da + w2 / db)
    m0, m1 = slope(k) * h, slope(k + 1) * h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1


def bump(t, a, b):
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


def bump_e(t, a, b):
    return ease(bump(t, a, b))


def dwell(s):
    return s * (1.35 - .35 * s * s)


def breath_curve(th, k=.45):
    return .5 - .5 * math.cos(th - k * math.sin(th))


CHANNELS = ("sx bob pelvis sp ch breath clav_l clav_r head face_x face_y hat "
            "wl_x wl_y hl ul fl ikl ur fr hr lift_l lift_r step_l step_r foot_l foot_r board ember").split()
REST = {c: 0.0 for c in CHANNELS}
REST.update(ember=.4, ikl=1.0)
# the joint arm's poses (upper, fore, hand: degrees, + = counter-clockwise), solved for its wrist: the joint's end on
# his lips with the elbow dropped to his belly; raised up and out to his right (clear of his face: the forearm piece
# is drawn over the head); held high, out to the right; clutched to his chest; let drop
ARM_R = {"puff": (-55.4, 112.3, -4.0), "raise": (79.8, -85.4, 10.0), "high": (93.2, -85.4, 0.0),
         "hold": (-54.2, 56.9, -8.0), "drop": (-17.1, -6.4, 4.0)}
ARM_L_UP = (-110.0, -50.0, -165.0)                    # the board arm thrown up (upper, fore, hand's world turn): the
                                                      # upper arm does the lifting, the elbow bends gently (a tight bend
                                                      # squeezed the sleeve's inner ink into a see-through smear)


def arm_r(c, pose_name, w):
    u_, f_, h_ = ARM_R[pose_name]
    c["ur"] += u_ * w
    c["fr"] += f_ * w
    c["hr"] += h_ * w


def hop(i, t0, h=80, air=12, dip=24):
    """One jump at frame t0: a crouch, up `h` px for `air` frames, an impact landing and a squash. -> bob (+ = down)."""
    return kf(i, (t0 - 10, 0), (t0 - 2, dip), (t0 + 4, -h * .9), (t0 + air * .5 + 2, -h), (t0 + air + 4, 0, "i"),
              (t0 + air + 8, dip * .9), (t0 + air + 16, -4), (t0 + air + 22, 0))


def drive(name, i, n):
    """The animator's channels for frame i: degrees for turns (+ = counter-clockwise on screen: an upright bone leans
    LEFT, a hanging bone swings RIGHT), art px for moves (+y = down). He faces a little to the viewer's left, where
    the board will be."""
    c = dict(REST)
    p = i / n
    if name == "idle":
        a = 2 * math.pi * p
        br = breath_curve(4 * math.pi * p)                     # two breaths a loop
        c["breath"] = br
        c["sx"] = 7 * dwell(math.sin(a))
        c["bob"] = 3 * br + 2.5 * (1 - math.cos(2 * a)) / 2
        c["pelvis"] = 1.6 * math.sin(a)
        c["sp"] = -1.1 * math.sin(a - .35)
        c["ch"] = -.9 * math.sin(a - .7) + 1.2 * br
        c["clav_l"] = -2.2 * br
        c["clav_r"] = 2.2 * br
        c["head"] = 2.2 * math.sin(a + .9) + kf(i, (24, 0), (38, 3.5), (66, 3.5), (80, 0), (186, 0), (198, -3), (222, -3), (234, 0))
        c["face_x"] = kf(i, (24, 0), (36, -9), (66, -9), (78, 0), (186, 0), (196, 8), (222, 8), (232, 0))
        c["face_y"] = kf(i, (100, 0), (118, -3), (140, -3), (160, 0))
        # the puff: the joint to his lips (the elbow drops to his belly), a long draw, back down
        arm_r(c, "puff", kf(i, (88, 0), (116, 1), (142, 1), (170, 0)))
        c["hr"] += kf(i, (116, 0), (124, 3), (134, -2), (142, 0))
        c["head"] += kf(i, (98, 0), (116, -3.5), (140, -3.5), (160, 0))
        c["ember"] = .4 + .6 * bump_e(i, 112, 150) + .08 * math.sin(2 * math.pi * 6 * p)
        c["wl_y"] = 1.5 * br
    elif name == "anticipation":
        a = 2 * math.pi * p
        shake = math.sin(2 * math.pi * 12 * p)                 # a nervous tremble: 6 a second, loop-safe
        br = .5 - .5 * math.cos(2 * math.pi * 4 * p)           # quick shallow breaths
        c["breath"] = .6 * br
        c["sx"] = -20 + 2.0 * shake
        c["bob"] = 18 + 2 * br
        c["pelvis"] = 2.5
        c["sp"] = 6.0 + .5 * shake
        c["ch"] = 7.0 + .8 * br
        c["clav_l"] = -5.0 - 1.4 * br
        c["clav_r"] = 5.0 + 1.4 * br
        c["head"] = 6.5 + 1.0 * math.sin(a) + .6 * shake
        c["face_x"] = -14
        c["face_y"] = -2
        # he leans his weight onto the board: it tips toward him (about its buried tail) and his hand rides its top
        c["board"] = 2.2 + .5 * shake
        c["wl_x"] = -24 + 1.5 * shake
        c["wl_y"] = 8 + 2 * shake                               # gripping it
        c["hl"] = 4 + 1.5 * shake
        arm_r(c, "hold", 1.0)
        c["hr"] += 1.5 * shake
        c["ember"] = .45 + .1 * math.sin(2 * math.pi * 3 * p)
    elif name == "win":
        c["bob"] = kf(i, (0, 0), (7, 10), (16, -16), (26, 5), (36, 0))
        c["head"] = kf(i, (0, 0), (9, -5), (19, 6), (30, -2), (40, 0))
        c["ch"] = kf(i, (0, 0), (10, -3), (22, 3), (36, 0))
        arm_r(c, "raise", kf(i, (0, 0), (14, 1), (40, 1), (56, 0)))
        c["hr"] += kf(i, (14, 0), (20, 12), (27, -10), (34, 8), (40, 0))
        c["clav_r"] = kf(i, (0, 0), (14, 8), (40, 8), (56, 0))
        c["ember"] = .4 + .6 * bump_e(i, 8, 48)
    elif name in ("big_win", "bonus"):
        hops = (20, 66) if name == "big_win" else (18, 58, 98)
        end = 100 if name == "big_win" else 128
        bob = 0.0
        for k, t0 in enumerate(hops):
            bob += hop(i, t0, 95 if k == 0 else 70)
        c["bob"] = bob
        up = kf(i, (0, 0), (12, 0), (22, 1), (end - 12, 1), (end + 8, 0))
        c["lift_l"] = c["lift_r"] = max(0.0, -bob) * .96
        c["ikl"] = 1 - up                                       # the board arm lets go of the board and goes up
        c["ul"], c["fl"], c["hl"] = ARM_L_UP[0] * up, ARM_L_UP[1] * up, ARM_L_UP[2] * up
        arm_r(c, "high", up)
        c["clav_l"] = -10 * up
        c["clav_r"] = 10 * up
        dance = math.sin(2 * math.pi * (i - 24) / 22) * kf(i, (24, 0), (34, 1), (end - 16, 1), (end, 0))
        c["ch"] = 5 * dance
        c["sp"] = 3 * dance
        c["pelvis"] = -3 * dance
        c["sx"] = 8 * dance
        c["hr"] = 14 * dance
        c["hl"] += 10 * dance
        c["ul"] += 6 * dance
        c["head"] = -4 * dance + kf(i, (30, 0), (40, -5), (end - 10, -5), (end, 0))
        c["face_y"] = kf(i, (30, 0), (40, -6), (end - 10, -6), (end, 0))
        c["board"] = kf(i, (14, 0), (20, 4), (28, -3), (36, 1.5), (44, 0))
        c["ember"] = .4 + .6 * up
        c["foot_l"] = -6 * up * (c["lift_l"] > 4)
        c["foot_r"] = 6 * up * (c["lift_r"] > 4)
    elif name == "lose":
        c["bob"] = kf(i, (0, 0), (12, -6), (24, 4), (40, 12), (70, 12), (88, 0))
        c["clav_l"] = kf(i, (0, 0), (12, -9), (22, -9), (34, 6), (70, 6), (88, 0))
        c["clav_r"] = kf(i, (0, 0), (12, 9), (22, 9), (34, -6), (70, -6), (88, 0))
        c["head"] = kf(i, (0, 0), (12, 3), (24, -2), (36, -5), (70, -5), (88, 0))
        c["face_y"] = kf(i, (0, 0), (20, 0), (34, 10), (70, 10), (88, 0))
        c["ch"] = kf(i, (0, 0), (14, -2), (34, 3), (70, 3), (88, 0))
        c["sp"] = kf(i, (0, 0), (34, 2), (70, 2), (88, 0))
        c["breath"] = kf(i, (0, 0), (10, .9), (20, .9), (40, -.6), (70, -.4), (88, 0))
        arm_r(c, "raise", kf(i, (0, 0), (12, .35), (22, .35), (34, 0)))
        arm_r(c, "drop", kf(i, (22, 0), (40, 1), (70, 1), (88, 0)))
        c["wl_y"] = kf(i, (0, 0), (34, 8), (70, 8), (88, 0))
        c["ember"] = .3
    return c


def face_keys(name, n):
    """frame -> face, for the clip (one head drawn at a time)."""
    if name == "idle":
        return {0: "neutral", 52: "blink", 57: "neutral", 116: "puff", 143: "neutral", 205: "blink", 210: "neutral"}
    if name == "anticipation":
        return {0: "nervous"}
    if name == "win":
        return {0: "neutral", 6: "cheer", 46: "neutral"}
    if name == "big_win":
        return {0: "neutral", 8: "cheer", 42: "laugh", 92: "cheer", 108: "neutral"}
    if name == "bonus":
        return {0: "neutral", 6: "cheer", 36: "laugh", 76: "cheer", 96: "laugh", 128: "cheer", 140: "neutral"}
    if name == "lose":
        return {0: "neutral", 6: "nervous", 26: "sad", 78: "blink", 82: "sad", 86: "neutral"}
    return {0: "neutral"}


# ---------------------------------------------------------------- keying

def run_clip(arm, name, f0):
    """Key one clip at frames f0.. (bones only: faces and effects come after, off the keyed pose)."""
    n, loop = CLIPS[name]
    S = {"head": Spring(2.2, .5), "face_x": Spring(2.8, .6), "face_y": Spring(2.8, .6), "hat": Spring(2.6, .45),
         "pom": Spring(2.0, .22), "belly": Spring(3.2, .25)}
    prev = None
    frames = list(range(n)) if loop else list(range(n + 1))
    passes = ([("pre", i) for i in frames] * 2 if loop else []) + [("key", i) for i in frames]
    for kind, i in passes:
        c = drive(name, i, n)
        turn = c["pelvis"] + c["sp"] + c["ch"]
        first = prev is None
        if first:
            prev = {"bob": c["bob"], "sx": c["sx"], "head": c["head"] - .5 * turn, "vb": 0.0}
        vb = (c["bob"] - prev["bob"]) * FPS
        vx = (c["sx"] - prev["sx"]) * FPS
        go = (lambda sp, v: sp.snap(v)) if first else (lambda sp, v: sp.step(v))
        h = go(S["head"], c["head"] - .5 * turn)               # the big head stays level-ish, a moment late
        dh = (h - prev["head"]) * FPS
        fxs = go(S["face_x"], c["face_x"])
        fys = go(S["face_y"], c["face_y"])
        hat = go(S["hat"], c["hat"] - .02 * dh)
        pom = go(S["pom"], -.06 * dh - .03 * vx + .02 * vb)
        bel = go(S["belly"], .0016 * (vb - prev["vb"]) * FPS / 10)
        prev.update(bob=c["bob"], sx=c["sx"], head=h, vb=vb)
        if kind != "key":
            continue
        lim = lambda v, L: L * math.tanh(v / L)
        s = dict(head=h, face_x=fxs, face_y=fys, hat=hat, pom=lim(pom, 28.0), belly=lim(bel, .08))
        if not loop:                                           # the last frames settle exactly onto the rest pose
            w = ease((n - i) / 10.0)
            for ch in CHANNELS:
                c[ch] = REST[ch] + (c[ch] - REST[ch]) * w
            s = {k: v * w for k, v in s.items()}
        pose(arm, f0 + i, c, s)
        TRACK.setdefault(name, []).append(c["ember"])
    return n


TRACK = {}


def pose(arm, f, c, s):
    P = arm.pose.bones
    R = math.radians

    def rot(nm, deg):
        P[nm].rotation_euler = (0, 0, R(deg))

    for pb in P:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    P["hips"].location = (c["sx"] / 100, -c["bob"] / 100, 0)  # hips bone points up: local x = right, local y = up
    rot("hips", c["pelvis"])
    rot("spine", c["sp"])
    rot("chest", c["ch"])
    b = c["breath"]
    P["chest"].scale = (1 + .022 * b, 1 + .03 * b, 1)
    P["belly"].scale = (1 - .5 * s["belly"], 1 + s["belly"], 1)
    rot("clav_l", c["clav_l"])
    rot("clav_r", c["clav_r"])
    rot("neck", .4 * s["head"])
    rot("head", .6 * s["head"])
    P["face"].location = (s["face_x"] / 100, -s["face_y"] / 100, 0)
    rot("hat", s["hat"])
    rot("pom", s["pom"])
    rot("hand_l", c["hl"])
    rot("upper_l", c["ul"])                                   # (only seen as the IK lets go)
    rot("fore_l", c["fl"])
    rot("upper_r", c["ur"])
    rot("fore_r", c["fr"])
    rot("hand_r", c["hr"])
    # the board hand's wrist target is on the root: it stays on the board while he sways
    P["ik_hand_l"].location = (c["wl_x"] / 100, -c["wl_y"] / 100, 0)
    ik = P["fore_l"].constraints["IK"]
    ik.influence = max(0.0, min(1.0, c["ikl"]))
    ik.keyframe_insert("influence", frame=f)
    P["ik_l"].location = (c["step_l"] / 100, c["lift_l"] / 100, 0)
    P["ik_r"].location = (c["step_r"] / 100, c["lift_r"] / 100, 0)
    rot("foot_l", c["foot_l"])
    rot("foot_r", c["foot_r"])
    rot("board", c["board"])
    for pb in P:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_euler", frame=f)
        pb.keyframe_insert("scale", frame=f)


def fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        return [fc for L in act.layers for s in L.strips for cb in s.channelbags for fc in cb.fcurves]


def linear_keys():
    for idb in list(bpy.data.objects) + [m.node_tree for m in bpy.data.materials if m.node_tree]:
        ad = idb.animation_data
        if not (ad and ad.action):
            continue
        for fc in fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def bone_pt(arm, bn, p):
    """Where art point p (in the rest drawing) is right now, carried by bone bn: art px."""
    ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pb = ae.pose.bones[bn]
    m = ae.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    X, Z = u(*p)
    v = m @ Vector((X, 0, Z))
    return art(v.x, v.z)


def place(ob, x, y, f, scale=1.0, spin=0.0, alpha=1.0):
    X, Z = u(x, y)
    ob.location = (X, ob.location.y, Z)
    ob.scale = (scale, 1, scale)
    ob.rotation_euler = (0, math.radians(spin), 0)
    ob.keyframe_insert("location", frame=f)
    ob.keyframe_insert("scale", frame=f)
    ob.keyframe_insert("rotation_euler", frame=f)
    set_fade(ob, f, alpha)


def effects(arm, faces, fx, name, f0, rng):
    """Faces, the ember on the joint's tip, smoke, sparks, snow and sweat - off the keyed pose (frame_set reads it)."""
    sc = bpy.context.scene
    n, loop = CLIPS[name]
    frames = list(range(n)) if loop else list(range(n + 1))
    keys = face_keys(name, n)
    cur = "neutral"
    for i in frames:
        cur = keys.get(i, cur)
        if not loop and i >= n - 2:
            cur = "neutral"
        for f, ob in faces.items():
            set_fade(ob, f0 + i, 1.0 if f == cur else 0.0)
    tips, mouths, boots = {}, {}, {}
    for i in frames:
        sc.frame_set(f0 + i)
        tips[i] = bone_pt(arm, "hand_r", TIP)
        mouths[i] = bone_pt(arm, "face", MOUTH)
        boots[i] = (bone_pt(arm, "foot_l", (290, 1440)), bone_pt(arm, "foot_r", (740, 1440)))
    used = {k: 0 for k in fx}
    live = EMITS.setdefault(name, [])

    def emit(kind, fs, fe, path, spin=0.0, grow=(1, 1), fade_in=.12):
        if fs > frames[-1]:
            return
        fe = min(fe, frames[-1]) if not loop else fe
        obs = fx[kind]
        ob = obs[used[kind] % len(obs)]
        used[kind] += 1
        set_fade(ob, f0 + fs - 1, 0.0)
        r0 = rng.uniform(0, 360)
        for f in range(fs, fe + 1):
            tt = (f - fs) / max(1, fe - fs)
            x, y = path(tt)
            g = grow[0] + (grow[1] - grow[0]) * tt
            a = min(1.0, tt / fade_in) if fade_in else 1.0
            a *= 1.0 if tt < .6 else (1 - tt) / .4
            # a loop's effect that runs past its end wraps round to its start
            ff = f0 + (f % n if loop else f)
            place(ob, x, y, ff, g, r0 + spin * tt, max(0.0, a))
        set_fade(ob, f0 + ((fe + 1) % n if loop else fe + 1), 0.0)

    def wisp(i, *a, **k):                                   # live: a curl of smoke off the joint's tip
        live.append([i, "wisp"])

    def exhale(i, *a, **k):                                 # live: three puffs out of his mouth
        live.append([i, "exhale"])

    def burst(i, cx, cy, count, reach=(180, 320), dur=26):
        for k in range(count):
            ang = 2 * math.pi * k / count + rng.uniform(-.3, .3)
            r = rng.uniform(*reach)
            emit("spark", i, i + dur, lambda t, ang=ang, r=r: (cx + r * math.cos(ang) * (1 - (1 - t) ** 2),
                                                               cy + r * math.sin(ang) * (1 - (1 - t) ** 2) + 40 * t * t),
                 260, (.5, 1.1), .05)

    def kick(i):
        for (bx, by), side in zip(boots[min(i, frames[-1])], (-1, 1)):
            emit("snowpuff", i, i + 22, lambda t, bx=bx, by=by, side=side: (bx + side * 90 * t, by - 20 - 50 * t + 60 * t * t),
                 side * 30, (.4, 1.1), .05)

    if name == "idle":
        for i in (8, 52, 186, 222):
            wisp(i)
        exhale(150)
    elif name == "anticipation":
        wisp(14)
        live.append([4, "sweat"])
    elif name == "win":
        x, y = tips[16]
        burst(14, x, y, 6, (110, 210), 24)
        wisp(30)
    elif name in ("big_win", "bonus"):
        hops = (20, 66) if name == "big_win" else (18, 58, 98)
        for k, t0 in enumerate(hops):
            x, y = bone_pt_frame = mouths[min(t0 + 6, frames[-1])]
            burst(t0 + 2, x + 40, y - 330, 12 if k == 0 else 9, (200, 360))     # over his head, not on his face
            kick(t0 + 16)
        x, y = tips[30]
        wisp(30, 260, 60, (.3, .9))
        exhale(min(frames[-1] - 50, 84 if name == "big_win" else 112))
    elif name == "lose":
        exhale(42, 56)
    live.sort()


def world_angle(ae, bn):
    """A bone's direction in the picture (radians, counter-clockwise from screen right)."""
    pb = ae.pose.bones[bn]
    m = ae.matrix_world @ pb.matrix
    y = m.col[1]
    return math.atan2(y.z, y.x)


def head_pt(ae, bn):
    pb = ae.pose.bones[bn]
    v = ae.matrix_world @ pb.matrix.col[3].to_3d()
    return art(v.x, v.z)


CONTACT_LOG = {}
CONTACT_PICK = {}


def _rot(v, deg):
    """v (art px, y down) turned counter-clockwise on screen by deg."""
    r = math.radians(deg)
    return (v[0] * math.cos(r) + v[1] * math.sin(r), -v[0] * math.sin(r) + v[1] * math.cos(r))


def _state(arm, f):
    bpy.context.scene.frame_set(f)
    ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return (head_pt(ae, "upper_r"), head_pt(ae, "fore_r"), head_pt(ae, "hand_r"),
            bone_pt(arm, "hand_r", JOINT_END), bone_pt(arm, "face", LIPS))


REACH = 95.0                                          # art px shoulder to wrist he holds a joint to his lips at
PALM = (835, 548)                                     # the middle of his fist (art px, on hand_r)


def contact(arm, name, f0):
    """Through each hit of the clip, put the joint's mouth end ON his lips: the hand turns (one turn for the whole hit,
    chosen so his wrist sits a comfortable REACH from the shoulder - the lips are close to it), and the upper arm and
    forearm are re-solved (two bones, the same bend) so the wrist lands where that hand puts the end on the lips;
    blended in and out over the window's ramps. Re-keys upper_r / fore_r / hand_r."""
    log = []
    for (a, b, c, d) in CONTACT.get(name, []):
        # the hand's turn for this hit, chosen at the middle of the hold from the hand AS IT IS there (its keyed turn
        # included): the joint points up and away from his face (15-40 deg above level, to his right of the lips),
        # his fist sits right of / below his lips (never over them), his wrist a comfortable reach from the shoulder
        fm = f0 + (b + c) // 2
        S, E, Wr, J, L = _state(arm, fm)
        Tp, Pm = bone_pt(arm, "hand_r", TIP), bone_pt(arm, "hand_r", PALM)
        v = (J[0] - Wr[0], J[1] - Wr[1])
        tv, pv0 = (Tp[0] - J[0], Tp[1] - J[1]), (Pm[0] - J[0], Pm[1] - J[1])
        best = None
        for dth in range(-90, 91):
            vv = _rot(v, dth)
            T = (L[0] - vv[0], L[1] - vv[1])
            td = _rot(tv, dth)
            elev = math.degrees(math.atan2(-td[1], td[0]))           # the joint's angle above level, to his right = 0
            pv = _rot(pv0, dth)
            Lu, Lf = math.dist(S, E), math.dist(E, Wr)
            rd = math.dist(S, T)
            if not (abs(Lu - Lf) + 4 <= rd <= Lu + Lf - 4):         # out of the arm's reach: the end would miss his lips
                continue
            cost = (abs(rd - REACH) + .3 * abs(dth) + 3 * max(0.0, abs(elev - 27) - 14)
                    + 4 * max(0.0, 30 - pv[0]) + 4 * max(0.0, 0 - pv[1]))
            if best is None or cost < best[0]:
                best = (cost, dth, round(elev, 1), round(math.dist(S, T), 1), tuple(round(q) for q in pv))
        CONTACT_PICK[name] = best
        dth = best[1]
        for i in range(a, d + 1):
            w = ease((i - a) / max(1, b - a)) if i < b else (ease((d - i) / max(1, d - c)) if i > c else 1.0)
            P = arm.pose.bones
            # 1. turn the hand (about the wrist) by its share of the hit's turn
            bpy.context.scene.frame_set(f0 + i)
            P["hand_r"].rotation_euler.z += math.radians(w * dth)
            P["hand_r"].keyframe_insert("rotation_euler", frame=f0 + i)
            for _ in range(3):
                S, E, Wr, J, L = _state(arm, f0 + i)
                T = (Wr[0] + w * (L[0] - J[0]), Wr[1] + w * (L[1] - J[1]))
                Lu, Lf = math.dist(S, E), math.dist(E, Wr)
                dist = max(1e-6, math.dist(S, T))
                dd = min(max(dist, abs(Lu - Lf) + 1), Lu + Lf - 1)
                ux, uy = (T[0] - S[0]) / dist, (T[1] - S[1]) / dist
                aa = (Lu * Lu - Lf * Lf + dd * dd) / (2 * dd)
                hh = math.sqrt(max(0.0, Lu * Lu - aa * aa))
                px, py = S[0] + aa * ux, S[1] + aa * uy
                En = min([(px - hh * uy, py + hh * ux), (px + hh * uy, py - hh * ux)],
                         key=lambda e: math.dist(e, E) - .5 * e[1])              # nearest the keyed elbow, and low
                Tn = (S[0] + dd * ux, S[1] + dd * uy)
                ang = lambda p_, q_: math.atan2(-(q_[1] - p_[1]), q_[0] - p_[0])
                wrap = lambda r: (r + math.pi) % (2 * math.pi) - math.pi
                dU = wrap(ang(S, En) - ang(S, E))
                dF = wrap(ang(En, Tn) - ang(E, Wr))
                bpy.context.scene.frame_set(f0 + i)
                P["upper_r"].rotation_euler.z += dU
                P["fore_r"].rotation_euler.z += dF - dU
                P["hand_r"].rotation_euler.z -= dF                      # the hand keeps its turn in the picture
                for bn in ("upper_r", "fore_r", "hand_r"):
                    P[bn].keyframe_insert("rotation_euler", frame=f0 + i)
            S, E, Wr, J, L = _state(arm, f0 + i)
            log.append((i, round(w, 2), round(math.dist(J, L), 2), round(math.dist(S, Wr), 1)))
        log.append(("turn", dth))
    CONTACT_LOG[name] = log
    return log


STARTS = {}


def animate(arm, faces, fx):
    rng = random.Random(4242)
    f = 1
    for c in CLIPS:
        STARTS[c] = f
        f += CLIPS[c][0] + 20
    for c in CLIPS:
        run_clip(arm, c, STARTS[c])
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, f
    for c in CLIPS:
        contact(arm, c, STARTS[c])
    for c in CLIPS:
        effects(arm, faces, fx, c, STARTS[c], rng)
    linear_keys()
    json.dump(STARTS, open(os.path.join(OUT, "starts.json"), "w"))


# ---------------------------------------------------------------- export: the live rig

def to_art(m):
    m00, m02, m03 = m[0][0], m[0][2], m[0][3]
    m20, m22, m23 = m[2][0], m[2][2], m[2][3]
    cx, cy = W_PX / 2, H_PX / 2
    a, cc = m00, -m02
    b, d = -m20, m22
    tx = 100 * m03 + cx - a * cx - cc * cy
    ty = cy - 100 * m23 - b * cx - d * cy
    return a, b, cc, d, tx, ty


def fx_affine(m, size):
    k = 100 * size
    return (k * m[0][0], -k * m[2][0], -k * m[0][2], k * m[2][2], 100 * m[0][3] + W_PX / 2, H_PX / 2 - 100 * m[2][3])


def export(arm, parts, faces, fx):
    """rig/rig.json + geo.bin (every part's mesh in art px, UVs, triangles, 4 bone weights per vertex) + <clip>.bin
    (per frame, per deforming bone, its 2D affine in art px, float32)."""
    sc = bpy.context.scene
    dst = os.path.join(OUT, "rig")
    os.makedirs(dst, exist_ok=True)
    for old in os.listdir(dst):
        os.remove(os.path.join(dst, old))
    bones = DEFORM
    bidx = {b: i for i, b in enumerate(bones)}
    geo = bytearray()
    out_parts = []

    def mesh_out(ob, tex, box, extra):
        me = ob.data
        names = {g.index: g.name for g in ob.vertex_groups}
        vs, uvs = [], [None] * len(me.vertices)
        uvl = me.uv_layers[0].data
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvs[me.loops[li].vertex_index] = tuple(uvl[li].uv)
        bi, bw = [], []
        for v in me.vertices:
            vs += list(art(v.co.x, v.co.z))
            ws = sorted(((g.weight, names[g.group]) for g in v.groups if g.weight > .004), reverse=True)[:4]
            tot = sum(w for w, _ in ws) or 1.0
            q = [int(round(255 * w / tot)) for w, _ in ws]
            if q:
                q[0] += 255 - sum(q)
            ids = [bidx[nm] for _, nm in ws]
            while len(q) < 4:
                q.append(0)
                ids.append(0)
            bi += ids
            bw += q
        tris = []
        for poly in me.polygons:
            vv = list(poly.vertices)
            tris += [vv[0], vv[1], vv[2], vv[0], vv[2], vv[3]]
        rec = dict(extra, name=ob.name, tex=tex, box=box, verts=len(me.vertices), tris=len(tris) // 3)
        rec["o_pos"] = len(geo); geo.extend(struct.pack(f"<{len(vs)}f", *vs))
        rec["o_uv"] = len(geo); geo.extend(struct.pack(f"<{2 * len(uvs)}f", *[c for uv in uvs for c in (uv[0], 1 - uv[1])]))
        rec["o_idx"] = len(geo); geo.extend(struct.pack(f"<{len(tris)}H", *tris))
        while len(geo) % 4:
            geo.append(0)
        rec["o_bi"] = len(geo); geo.extend(bytes(bi))
        rec["o_bw"] = len(geo); geo.extend(bytes(bw))
        while len(geo) % 4:
            geo.append(0)
        return rec

    for nm in META["order"]:
        box = [v / K for v in META["parts"][nm]["box"]]
        out_parts.append(mesh_out(parts[nm], nm, box, {"face": "neutral"} if nm == "head" else {}))
        if nm == "head":
            for f, ob in faces.items():
                if f != "neutral":
                    out_parts.append(mesh_out(ob, "face_" + f, [v / K for v in META["faces"][f]["box"]], {"face": f}))
    open(os.path.join(dst, "geo.bin"), "wb").write(bytes(geo))
    clips = {}
    fx_names = [k for k, _, _ in FX_KINDS]
    for c, (n, loop) in CLIPS.items():
        nf = n if loop else n + 1
        buf = bytearray()
        face_track, fx_draws = [], []
        for k in range(nf):
            sc.frame_set(STARTS[c] + k)
            dg = bpy.context.evaluated_depsgraph_get()
            ae = arm.evaluated_get(dg)
            for bn in bones:
                pb = ae.pose.bones[bn]
                m = ae.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
                buf.extend(struct.pack("<6f", *to_art(m)))
            cur = 0
            for fi, f in enumerate(FACES[1:], 1):
                ob = faces.get(f)
                if ob and ob.active_material.evaluated_get(dg).node_tree.nodes["fade"].outputs[0].default_value > .5:
                    cur = fi
            face_track.append(cur)
            draws, oid = [], 0
            for kind, obs in fx.items():
                for ob in obs:
                    oid += 1
                    a = ob.active_material.evaluated_get(dg).node_tree.nodes["fade"].outputs[0].default_value
                    if a <= .003:
                        continue
                    mw = ob.evaluated_get(dg).matrix_world
                    aa = fx_affine(mw, 2 * ob["fx_size"] / 200.0)
                    draws.append([fx_names.index(kind), oid] + [round(v, 3) for v in aa] + [round(a, 3)])
            fx_draws.append(draws)
        open(os.path.join(dst, f"{c}.bin"), "wb").write(bytes(buf))
        glow = [round(max(0.0, min(1.0, v)), 3) for v in TRACK[c][:nf]]
        clips[c] = {"frames": nf, "loop": loop, "face": face_track, "fx": fx_draws, "ember": glow, "emit": EMITS.get(c, [])}
        print(f"CLIP {c:13s} frames {nf:3d}", flush=True)
    meta = {"version": 1, "fps": FPS, "art": [W_PX, H_PX], "cx": W_PX / 2, "ground_y": GROUND, "top_y": TOP,
            "rest_height": GROUND - TOP, "bones": bones, "parts": out_parts, "faces": FACES, "fx": fx_names,
            "fx_add": ["ember"], "fx_px": dict({k: s for k, _, s in FX_KINDS}, **LIVE_FX), "live_fx": list(LIVE_FX),
            # live effects hang off these points (art px in the rest drawing, carried by the bone)
            "points": {"tip": {"bone": "hand_r", "at": list(TIP)}, "end": {"bone": "hand_r", "at": list(JOINT_END)},
                       "lips": {"bone": "face", "at": list(LIPS)}, "mouth": {"bone": "face", "at": list(MOUTH)},
                       "brow": {"bone": "head", "at": list(BROW)}},
            "idle": {"rate": 1.0, "cut": 8}, "hold": ["anticipation"], "cut": {"anticipation": 12, "*": 8},
            "clips": clips}
    json.dump(meta, open(os.path.join(dst, "rig.json"), "w"), separators=(",", ":"))
    print("EXPORT", dst, "bones", len(bones), "parts", len(out_parts), "geo", len(geo), flush=True)


# ---------------------------------------------------------------- QA renders

def render(clips, step=6):
    sc = bpy.context.scene
    ren = os.path.join(OUT, "renders")
    for c in clips:
        n, loop = CLIPS[c]
        d = os.path.join(ren, c)
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        for k in range(0, n if loop else n + 1, step):
            sc.frame_set(STARTS[c] + k)
            sc.render.filepath = os.path.join(d, f"{k:04d}.png")
            bpy.ops.render.render(write_still=True)
    print("RENDERED", clips, flush=True)


# ---------------------------------------------------------------- driver

STATE = {}


def objects():
    arm = bpy.data.objects["yeti"]
    parts = {nm: bpy.data.objects[nm] for nm in META["order"]}
    faces = {f: bpy.data.objects["face_" + f] for f in META["faces"]}
    faces["neutral"] = parts["head"]
    fx = {k: [bpy.data.objects[f"{k}_{i}"] for i in range(n)] for k, n, _ in FX_KINDS}
    return arm, parts, faces, fx


def run(steps, clips=None, step=6):
    if "build" in steps:
        STATE["objs"] = build()
    arm, parts, faces, fx = STATE.get("objs") or objects()
    if not STARTS and os.path.exists(os.path.join(OUT, "starts.json")):
        STARTS.update(json.load(open(os.path.join(OUT, "starts.json"))))
    if "animate" in steps:
        animate(arm, faces, fx)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "yeti_rig.blend"))
    if "export" in steps:
        export(arm, parts, faces, fx)
    if "render" in steps:
        render(clips or list(CLIPS), step)


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    run((args[0] if args else "build,animate,export,render").split(","), args[1].split(",") if len(args) > 1 and args[1] else None,
        int(args[2]) if len(args) > 2 else 6)
