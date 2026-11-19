"""High Peaks: the duck's clips, keyed on one timeline (run in Blender after duck_build.py).

    exec(open(".../tools/highpeaks/blender/duck_anim.py").read())

Every clip owns a frame range (CLIPS, written to art/highpeaks/blender/clips.json) and starts and ends on the same
neutral pose, so the game can chain them in any order. 24 fps. The hands are placed with IK (a wrist target per arm,
riding the chest); a held prop is aimed by turning the glove so the prop points where it should (aim()). Props are
shown and hidden with hide_render keys (constant).

Idles: idle (breathing, droopy blinks, a slow sway - loops), look (turns to the reels, a slow nod), roll (pulls out
papers and a bud, sprinkles, rolls, licks, admires, puts it away), smoke (joint + lighter out, lights it, a long
hit, holds, exhales, a lazy grin, puts them away), bong (bong from behind, lighter out, two dud sparks then a light,
bubbling pull, a big cloud and a cough, puts it all away).
Reactions: win (a hop and a wing pump), mult (whoa: eyes wide, leans back), bonus (a happy dance), bonusidle (bobs to
the bonus music - loops), tease (a shrug).
Skiers: ski (crouched, poles - loops) and board (sideways on a snowboard - loops), rendered from the side camera.
"""
import bpy, math, random, json, os
from mathutils import Vector, Matrix, Euler

random.seed(7)
scn = bpy.data.scenes["Duck"]
if bpy.context.window is not None:
    bpy.context.window.scene = scn
arm = bpy.data.objects["DuckRig"]
PB = arm.pose.bones
AW = arm.matrix_world.to_3x3()
REST_T = {s: arm.data.bones[f"tgt.{s}"].head_local.copy() for s in "LR"}
PROPN = ["joint", "ember", "lighter", "lighter_top", "flame", "flame_core", "papers", "bud_pinch",
         "bong_base", "bong_tube", "bong_rim", "bong_stem", "bong_bowl", "bong_weed", "bowl_glow",
         "lighterR", "lighterR_top", "flameR", "flameR_core", "ski.L", "ski.R", "skitip.L", "skitip.R",
         "skipole.L", "skipole.R", "snowboard"] + [f"puff{i}" for i in range(8)]
GROUP = {"joint": ["joint"], "ember": ["ember"], "lighter": ["lighter", "lighter_top"], "flame": ["flame", "flame_core"],
         "papers": ["papers"], "bud": ["bud_pinch"], "bong": ["bong_base", "bong_tube", "bong_rim", "bong_stem", "bong_bowl", "bong_weed"],
         "bowlglow": ["bowl_glow"], "lighterR": ["lighterR", "lighterR_top"], "flameR": ["flameR", "flameR_core"],
         "skis": ["ski.L", "ski.R", "skitip.L", "skitip.R", "skipole.L", "skipole.R"], "board": ["snowboard"]}

# ------------------------------------------------------------------ reset
arm.animation_data_clear()
for pb in PB:
    pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
for n in PROPN:
    o = bpy.data.objects[n]
    o.animation_data_clear(); o.hide_render = True; o.scale = (1, 1, 1) if not n.startswith("puff") else o.scale
    if n.startswith("puff"):
        o.scale = (1, 1, 1)
for n in ("flame", "flame_core", "flameR", "flameR_core", "ember", "bowl_glow"):
    bpy.data.objects[n].scale = (1, 1, 1)
for n in PROPN:   # every prop starts hidden: a first "show" key must not hold backwards over the clips before it
    o = bpy.data.objects[n]; o.hide_render = True; o.keyframe_insert("hide_render", frame=0)

# ------------------------------------------------------------------ keying helpers
R = math.radians
def key(b, f, rot=None, loc=None, scale=None):
    pb = PB[b]
    if rot is not None:
        pb.rotation_euler = [R(v) for v in rot]; pb.keyframe_insert("rotation_euler", frame=f)
    if loc is not None:
        pb.location = loc; pb.keyframe_insert("location", frame=f)
    if scale is not None:
        pb.scale = scale; pb.keyframe_insert("scale", frame=f)

def wrist(s, f, p):
    d = Vector(p) - REST_T[s]
    key(f"tgt.{s}", f, loc=(d.x, d.z, -d.y))

def aim(s, f, prop, d_arm, spin=0.0):
    """Turn the glove at frame f so `prop`'s local +Z points along d_arm (armature space)."""
    scn.frame_set(f)
    hb = PB[f"hand.{s}"]
    hb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    o = bpy.data.objects[prop]
    z0 = (o.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    want = (AW @ Vector(d_arm)).normalized()
    q = z0.rotation_difference(want)
    if spin:
        q = Matrix.Rotation(R(spin), 3, want).to_quaternion() @ q
    Bw = (arm.matrix_world @ hb.matrix).to_3x3().normalized()
    Rl = Bw.inverted() @ q.to_matrix() @ Bw
    hb.rotation_euler = Rl.to_euler("XYZ")
    hb.keyframe_insert("rotation_euler", frame=f)

def wrist_at(s, f):
    scn.frame_set(f)
    l = PB[f"tgt.{s}"].location
    return REST_T[s] + Vector((l[0], -l[2], l[1]))

def reach(f, s, obj, goal, aim_args=None, iters=5):
    """Move the wrist at frame f until `obj` (in that glove) sits on goal() (a world point), re-aiming as it goes."""
    for _ in range(iters):
        if aim_args:
            aim(s, f, *aim_args)
        scn.frame_set(f)
        d = goal() - bpy.data.objects[obj].matrix_world.translation
        if d.length < .004:
            break
        wrist(s, f, wrist_at(s, f) + AW.inverted() @ d)

def wpt(name, off=(0, 0, 0)):
    return lambda: bpy.data.objects[name].matrix_world @ Vector(off)

def show(f, groups, on=True):
    for g in groups:
        for n in GROUP.get(g, [g]):
            o = bpy.data.objects[n]
            o.hide_render = not on
            o.keyframe_insert("hide_render", frame=f)

def pose(f, **k):
    """Key the named channels at frame f. Rotations in degrees: chest spine hips neck head (x nod/bend forward,
    y turn: - = toward the reels / screen left, z tilt), jaw (x: - opens), lid (x: + opens, - shuts; or lidL/lidR),
    shoulders shL/shR, hR/hL glove rotations; hipsloc (x, up, -fwd); hipscale / chestscale; wR/wL wrist positions
    (armature space: x right of the duck = screen right, -y = toward the camera, z up)."""
    for b in ("chest", "spine", "hips", "neck", "head", "jaw", "tail"):
        if b in k:
            key(b, f, rot=k[b])
    if "lid" in k:
        k.setdefault("lidL", k["lid"]); k.setdefault("lidR", k["lid"])
    for s in "LR":
        if f"lid{s}" in k:
            key(f"lid.{s}", f, rot=(k[f"lid{s}"], 0, 0))
        if f"w{s}" in k:
            wrist(s, f, k[f"w{s}"])
        if f"h{s}" in k:
            key(f"hand.{s}", f, rot=k[f"h{s}"])
        if f"sh{s}" in k:
            key(f"shoulder.{s}", f, rot=k[f"sh{s}"])
        for leg in ("thigh", "shin", "foot"):
            if f"{leg}{s}" in k:
                key(f"{leg}.{s}", f, rot=k[f"{leg}{s}"])
    if "hipsloc" in k:
        key("hips", f, loc=k["hipsloc"])
    if "hipscale" in k:
        key("hips", f, scale=k["hipscale"])
    if "chestscale" in k:
        key("chest", f, scale=k["chestscale"])

NEUTRAL = dict(chest=(5, 0, 0), spine=(0, 0, 0), hips=(0, 0, 0), neck=(0, 0, 0), head=(-3, -10, 3), jaw=(0, 0, 0), tail=(0, 0, 0),
               lid=-12, wR=(-.40, -.20, .56), wL=(.40, -.20, .56), hR=(0, 0, 0), hL=(0, 0, 0), shL=(0, 0, 0), shR=(0, 0, 0),
               hipsloc=(0, 0, 0), hipscale=(1, 1, 1), chestscale=(1, 1, 1),
               thighL=(0, 0, 0), thighR=(0, 0, 0), shinL=(0, 0, 0), shinR=(0, 0, 0), footL=(0, 0, 0), footR=(0, 0, 0))
def neutral(f, **over):
    d = dict(NEUTRAL); d.update(over)
    pose(f, **d)

def flicker(names, f0, f1, lo=.75, hi=1.25):
    for f in range(f0, f1 + 1, 2):
        for n in names:
            o = bpy.data.objects[n]
            k = random.uniform(lo, hi)
            o.scale = (1 + (k - 1) * .4, 1 + (k - 1) * .4, k); o.keyframe_insert("scale", frame=f)

def bill_tip(f):
    scn.frame_set(f)
    o = bpy.data.objects["bill_top"]
    return o.matrix_world @ Vector((0, -.13, -.02))

def puff(i, f0, dur=42, size=1.0, drift=(.18, 0, .55)):
    o = bpy.data.objects[f"puff{i}"]
    p0 = bill_tip(f0)
    dv = AW @ Vector(drift)
    o.hide_render = True; o.keyframe_insert("hide_render", frame=f0 - 1)
    o.hide_render = False; o.keyframe_insert("hide_render", frame=f0)
    o.hide_render = True; o.keyframe_insert("hide_render", frame=f0 + dur + 1)
    for t, sc in ((0, .18), (.35, .95), (.7, 1.15), (1.0, .02)):
        f = f0 + round(t * dur)
        o.location = p0 + dv * t + Vector((math.sin(t * 5 + i) * .04, 0, 0))
        o.scale = (sc * size,) * 3
        o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)

CLIPS = {}
cursor = [1]
def clip(name, length, loop=False):
    s = cursor[0]
    CLIPS[name] = {"start": s, "end": s + length - 1, "frames": length, "loop": loop}
    cursor[0] = s + length + 4
    return s

# ------------------------------------------------------------------ idles
s = clip("idle", 96, loop=True)
neutral(s); neutral(s + 95)
for i, f in enumerate(range(s, s + 96, 24)):        # breathing: four slow breaths
    pose(f + 10, chestscale=(1.025, 1.02, 1.03), chest=(3, 0, 0))
    pose(f + 22, chestscale=(1, 1, 1), chest=(5, 0, 0))
pose(s + 30, head=(-1, -4, 6)); pose(s + 66, head=(-5, -14, 0))     # a slow sway of the head
pose(s + 40, lid=-12); pose(s + 46, lid=-34); pose(s + 52, lid=-30); pose(s + 60, lid=-12)   # a heavy, slow blink
pose(s + 70, jaw=(0, 0, 0)); pose(s + 76, jaw=(-6, 0, 0)); pose(s + 82, jaw=(0, 0, 0))     # smacks its bill

s = clip("look", 84)
neutral(s); neutral(s + 83)
pose(s + 14, head=(4, -38, 6), chest=(6, -8, 0), lid=-4)                # turns to the reels, eyes a little wider
pose(s + 30, head=(10, -40, 4)); pose(s + 40, head=(2, -38, 6)); pose(s + 50, head=(10, -40, 4))   # slow nods
pose(s + 58, head=(4, -36, 6), lid=-14)
pose(s + 72, head=(-3, -10, 3), chest=(5, 0, 0), lid=-12)

s = clip("roll", 192)
neutral(s); neutral(s + 191)
pocketR, pocketL = (-.16, -.30, .78), (.16, -.30, .74)
pose(s + 10, wR=(-.34, -.26, .66), wL=(.34, -.26, .64), chest=(8, 0, 0))
pose(s + 20, wR=pocketR, wL=pocketL, head=(14, -6, 0))                  # into the jacket
show(s + 22, ["papers", "bud"])
pose(s + 34, wR=(-.10, -.46, .80), wL=(.12, -.44, .86), head=(22, -4, 4), chest=(10, 0, 0), lid=-20)
aim("R", s + 34, "papers", (1, -.2, .15), spin=90)
for j in range(4):                                                      # sprinkles the bud over the paper
    f = s + 40 + j * 7
    pose(f, wL=(.06, -.45, .88)); pose(f + 4, wL=(.05, -.45, .84))
show(s + 70, ["bud"], False)
pose(s + 72, wL=(.04, -.46, .80), head=(24, -2, 0))
for j in range(5):                                                      # rolls it between the gloves
    f = s + 76 + j * 6
    pose(f, wR=(-.07, -.47, .80), wL=(.05, -.46, .79), chest=(10, 2, 0)); pose(f + 3, wR=(-.09, -.45, .81), wL=(.03, -.48, .80), chest=(10, -2, 0))
show(s + 106, ["papers"], False); show(s + 106, ["joint"])
aim("R", s + 106, "joint", (1, -.25, .1))
pose(s + 110, wR=(-.08, -.40, 1.00), head=(8, -6, 0), chest=(10, 0, 0), wL=(.30, -.25, .66), lid=-16)   # up to the bill: a lick
aim("R", s + 110, "joint", (1, -.3, 0))
pose(s + 114, jaw=(-14, 0, 0)); pose(s + 116, wR=(.02, -.41, 1.00)); pose(s + 120, wR=(-.12, -.40, 1.00)); pose(s + 124, jaw=(0, 0, 0))
pose(s + 134, wR=(-.32, -.40, 1.18), head=(-6, -22, 10), lid=-2, chest=(2, 0, 0))   # holds it up and admires it
aim("R", s + 134, "joint", (.3, -.2, 1))
pose(s + 150, head=(-4, -18, 8), lid=-10)
pose(s + 160, wR=pocketR, head=(12, -6, 0), chest=(8, 0, 0))             # into the pocket for later
show(s + 162, ["joint"], False)
pose(s + 176, wR=(-.36, -.24, .60), wL=(.36, -.24, .60))

s = clip("smoke", 228)
neutral(s); neutral(s + 227)
pose(s + 10, wR=(-.34, -.26, .66), wL=(.34, -.26, .64), chest=(8, 0, 0), head=(10, -8, 0))
pose(s + 20, wR=pocketR, wL=pocketL)
show(s + 22, ["joint", "lighter"])
pose(s + 36, wR=(-.07, -.40, 1.00), head=(4, -6, 2), chest=(10, 0, 0), wL=(.10, -.48, .97), lid=-18)
aim("R", s + 36, "joint", (-1, -.45, -.08)); aim("L", s + 36, "lighter", (0, -.1, 1))
pose(s + 44, wL=(-.10, -.52, .90))                                     # the lighter to the tip
reach(s + 44, "L", "flame", wpt("ember", (0, 0, -.01)), aim_args=("lighter", (-.1, -.1, 1)))
pose(s + 74, wL=wrist_at("L", s + 44)); aim("L", s + 74, "lighter", (-.1, -.1, 1))
for f, on in ((48, True), (50, False), (53, True)):                     # flick, miss, flick
    show(s + f, ["flame"], on)
flicker(["flame", "flame_core"], s + 48, s + 74)
show(s + 60, ["ember"])
pose(s + 50, lid=-30, chestscale=(1.0, 1.0, 1.0))
pose(s + 72, chestscale=(1.06, 1.05, 1.07), chest=(0, 0, 0), head=(-6, -6, 2), lid=-36)    # a long pull
show(s + 75, ["flame"], False)
pose(s + 80, wL=(.38, -.22, .62)); aim("L", s + 80, "lighter", (0, 0, 1))
pose(s + 84, wR=(-.24, -.40, .82)); aim("R", s + 84, "joint", (-.7, -.5, .6))   # joint away from the bill
pose(s + 100, lid=-38, head=(-8, -6, 2))                                # holds it in
pose(s + 104, jaw=(-10, 0, 0), chestscale=(1.0, 1.0, 1.0), head=(-14, -10, 6))   # and lets it out
for i in range(6):
    puff(i, s + 105 + i * 6, dur=46, size=.62 + i * .06, drift=(.36, -.06, .3))
pose(s + 140, jaw=(0, 0, 0), chest=(-2, 0, 0), head=(-12, -14, 10), lid=-26)      # blissed out, leaning back
pose(s + 150, head=(-6, -12, 6)); pose(s + 158, head=(-10, -14, 9)); pose(s + 166, head=(-5, -12, 5))   # a lazy nod
pose(s + 180, wR=pocketR, wL=pocketL, chest=(8, 0, 0), head=(12, -6, 0), lid=-14)  # puts them away
show(s + 184, ["joint", "ember", "lighter"], False)
pose(s + 200, wR=(-.36, -.24, .60), wL=(.36, -.24, .60))

s = clip("bong", 264)
neutral(s); neutral(s + 263)
pose(s + 12, wL=(.46, .05, .60), chest=(6, 10, 0), head=(6, 20, 0))      # reaches behind for the bong
pose(s + 22, wL=(.42, .26, .52))
show(s + 24, ["bong"])
aim("L", s + 24, "bong_tube", (0, 0, 1))
pose(s + 40, wL=(.10, -.38, .74), chest=(6, 0, 0), head=(8, -6, 0)); aim("L", s + 40, "bong_tube", (0, 0, 1))
pose(s + 50, wR=pocketR); show(s + 54, ["lighterR"])
pose(s + 66, wR=(-.02, -.56, .72), head=(26, -4, 0), chest=(14, 0, 0), wL=(.06, -.34, .70), lid=-24)   # bill to the mouthpiece
def _bill_now():
    return bpy.data.objects["bill_low"].matrix_world @ Vector((0, -.05, -.03))
reach(s + 66, "L", "bong_rim", _bill_now, aim_args=("bong_tube", (-.05, .1, 1)))
pose(s + 118, wL=wrist_at("L", s + 66)); aim("L", s + 118, "bong_tube", (-.05, .1, 1))
reach(s + 66, "R", "flameR", wpt("bong_bowl", (0, 0, .02)), aim_args=("lighterR", (.15, -.15, 1)))
pose(s + 118, wR=wrist_at("R", s + 66)); aim("R", s + 118, "lighterR", (.15, -.15, 1))
for f, on in ((72, True), (73, False), (77, True), (78, False), (82, True)):     # two dud sparks, then it lights
    show(s + f, ["flameR"], on)
flicker(["flameR", "flameR_core"], s + 82, s + 118)
show(s + 86, ["bowlglow"])
for j in range(8):                                                      # a long bubbling pull
    pose(s + 86 + j * 4, chestscale=(1 + .008 * j, 1 + .007 * j, 1 + .009 * j))
pose(s + 118, lid=-40)
show(s + 119, ["flameR"], False); show(s + 121, ["bowlglow"], False)
pose(s + 126, wR=(-.38, -.22, .62), head=(10, -6, 0), chest=(6, 0, 0)); aim("R", s + 126, "lighterR", (0, 0, 1))
pose(s + 134, wL=(.36, -.28, .62), head=(-10, -10, 4)); aim("L", s + 134, "bong_tube", (0, 0, 1))
pose(s + 138, jaw=(-14, 0, 0), chestscale=(1, 1, 1), head=(-18, -10, 8))   # a big cloud
for i in range(8):
    puff(i, s + 139 + i * 4, dur=50, size=.75 + i * .06, drift=(.42, -.08, .34))
pose(s + 172, jaw=(0, 0, 0))
for j, f in enumerate((176, 180, 184)):                                  # a cough
    pose(s + f, chest=(16, 0, 0), head=(14, -6, 0), jaw=(-10, 0, 0), lid=-30); pose(s + f + 2, chest=(4, 0, 0), head=(0, -8, 2), jaw=(0, 0, 0))
pose(s + 196, lid=-26, head=(-6, -10, 6))
pose(s + 210, wL=(.46, .05, .60), wR=pocketR, chest=(6, 10, 0), head=(6, 20, 0))   # bong back behind, lighter away
pose(s + 222, wL=(.42, .26, .52)); show(s + 222, ["bong"], False); show(s + 214, ["lighterR"], False)
pose(s + 240, wL=(.36, -.24, .60), wR=(-.36, -.24, .60), chest=(5, 0, 0), head=(-3, -10, 3))

# ------------------------------------------------------------------ reactions
s = clip("win", 44)
neutral(s); neutral(s + 43)
pose(s + 6, hipsloc=(0, -.03, 0), hipscale=(1.04, 1.04, .94), lid=-2)     # dips
pose(s + 14, hipsloc=(0, .10, 0), hipscale=(.97, .97, 1.05), wR=(-.30, -.20, 1.30), head=(-10, -10, 0), jaw=(-12, 0, 0))   # hops, wing up
pose(s + 22, hipsloc=(0, 0, 0), hipscale=(1.04, 1.04, .95), wR=(-.34, -.22, 1.10))
pose(s + 28, wR=(-.30, -.20, 1.28), hipscale=(1, 1, 1)); pose(s + 34, wR=(-.36, -.22, .90), jaw=(0, 0, 0))

s = clip("mult", 48)
neutral(s); neutral(s + 47)
pose(s + 6, lid=24, head=(-14, -20, 0), chest=(-8, 0, 0), jaw=(-16, 0, 0), wR=(-.32, -.36, 1.06), wL=(.32, -.36, 1.06))   # whoa
pose(s + 12, head=(-16, -26, 6)); pose(s + 18, head=(-14, -14, -6)); pose(s + 24, head=(-16, -24, 6))   # shakes its head
pose(s + 32, lid=8, jaw=(-6, 0, 0))

s = clip("bonus", 108)
neutral(s); neutral(s + 107)
for j in range(2):                                                      # two jumps, both wings up
    f = s + 4 + j * 22
    pose(f, hipsloc=(0, -.04, 0), hipscale=(1.05, 1.05, .93))
    pose(f + 9, hipsloc=(0, .16, 0), hipscale=(.96, .96, 1.06), wR=(-.34, -.18, 1.38), wL=(.34, -.18, 1.38), jaw=(-18, 0, 0), lid=20, head=(-14, -6, 0))
    pose(f + 18, hipsloc=(0, 0, 0), hipscale=(1.04, 1.04, .95))
for j in range(6):                                                      # then a shimmy
    f = s + 50 + j * 8
    sgn = 1 if j % 2 else -1
    pose(f, hips=(0, sgn * 16, 0), chest=(4, -sgn * 10, 0), head=(-6, sgn * 18, sgn * 8), hipscale=(1, 1, 1),
         wR=(-.40 - .05 * sgn, -.30, .96 + .1 * sgn), wL=(.40 - .05 * sgn, -.30, .96 - .1 * sgn), jaw=(-10, 0, 0), lid=10)

s = clip("bonusidle", 48, loop=True)
neutral(s, lid=-4); neutral(s + 47, lid=-4)
for j in range(4):                                                      # bobs to the beat
    f = s + j * 12
    pose(f + 6, hipsloc=(0, -.02, 0), head=(10, -10, (j % 2) * 8 - 4), wR=(-.42, -.26, .66), wL=(.42, -.26, .66))
    pose(f + 12 if j < 3 else s + 47, hipsloc=(0, 0, 0), head=(-3, -10, 3), wR=(-.40, -.20, .56), wL=(.40, -.20, .56))

s = clip("tease", 44)
neutral(s); neutral(s + 43)
pose(s + 10, shL=(0, 0, 12), shR=(0, 0, -12), wR=(-.52, -.30, .74), wL=(.52, -.30, .74), head=(-4, -10, 14), jaw=(-4, 0, 0))   # a shrug
pose(s + 24, shL=(0, 0, 10), shR=(0, 0, -10), head=(-2, -10, 12))
pose(s + 34, shL=(0, 0, 0), shR=(0, 0, 0))

# ------------------------------------------------------------------ skiers (side camera, loops)
def knees(a, sway=0, spread=0):
    """Bent knees with the feet kept flat: thigh +a, shin -2a, foot +a; the hips drop to keep the feet down."""
    drop = .30 * (1 - math.cos(R(a)))
    return dict(thighL=(a, 0, spread), thighR=(a, 0, -spread), shinL=(-2 * a, 0, 0), shinR=(-2 * a, 0, 0),
                footL=(a, 0, -spread), footR=(a, 0, spread), hipsloc=(0, -drop, 0))

s = clip("ski", 24, loop=True)
show(s, ["skis"])
for t, a, sw, pump in ((0, 34, -5, 0), (6, 40, 0, 1), (12, 34, 5, 0), (18, 40, 0, -1), (23, 34, -5, 0)):
    pose(s + t, chest=(24, sw, 0), spine=(8, 0, 0), head=(-26, 0, -sw), lid=-8, jaw=(0, 0, 0), hips=(0, sw, sw * .6),
         wR=(-.30, -.52 + .04 * pump, .62), wL=(.30, -.52 - .04 * pump, .62), hR=(-50, 0, 0), hL=(-50, 0, 0), **knees(a))
show(s + 24, ["skis"], False)

s = clip("board", 24, loop=True)
show(s, ["board"])
for t, a, sw in ((0, 28, -8), (12, 34, 8), (23, 28, -8)):
    pose(s + t, chest=(10, sw * .5, sw), head=(0, -34, -sw * .5), lid=-14, jaw=(0, 0, 0), hips=(0, 0, sw * .6),
         wR=(-.70, -.10, .78 + sw * .01), wL=(.70, -.10, .78 - sw * .01), **knees(a, spread=14))
show(s + 24, ["board"], False)

# ------------------------------------------------------------------ finish
def tidy(obj):
    ad = obj.animation_data
    act = ad.action if ad else None
    if not act:
        return
    curves = []
    try:
        curves = list(act.fcurves)
    except AttributeError:   # Blender 5: layered actions
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += list(bag.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            if fc.data_path == "hide_render":
                kp.interpolation = "CONSTANT"
            else:
                kp.interpolation = "BEZIER"; kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()
tidy(arm)
for n in PROPN:
    tidy(bpy.data.objects[n])
scn.frame_start, scn.frame_end = 1, cursor[0]
out = "/Users/drewabbott/Documents/HighPeaks/art/highpeaks/blender"
os.makedirs(out, exist_ok=True)
json.dump({"fps": 24, "clips": CLIPS}, open(os.path.join(out, "clips.json"), "w"), indent=1)
scn.frame_set(1)
print("clips:", {k: (v["start"], v["end"]) for k, v in CLIPS.items()})
