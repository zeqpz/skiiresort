"""High Peaks: the duck - model, rig, toon materials, props, camera and light (owner, 2026-11-18: "we want a duck that
stands by the board thats the main character ... create them in a skeleton ... have the duck in skii wear and appear
high").

Run inside Blender (Blender MCP or the Text editor):  exec(open(".../tools/highpeaks/blender/duck_build.py").read())

Builds a scene "Duck": an armature "DuckRig" (root, hips, spine, chest, neck, head, jaw, lid.L/R, shoulder / upper_arm /
forearm / hand .L/.R, thigh / shin / foot .L/.R, tail) and the duck made of smooth primitives, each part rigidly bound
to its bone (the cartoon way: clean shapes, no weight painting). Flat toon shading (two tones, hard edge) plus an ink
outline (inverted hull), to match the game's flat cartoon art. Props (papers, bud, joint, lighter + flame, bong,
smoke puffs) are parented to the hands / head and shown only while a clip uses them. duck_anim.py makes the clips.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix, Euler

S = "Duck"
if bpy.context.window is None:          # background Blender (duck_render.py): build in the context scene itself
    scn = bpy.context.scene
    scn.name = S
    for o in list(scn.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:                                   # a live Blender: a scene of its own, the user's scenes left alone
    if S in bpy.data.scenes:
        old = bpy.data.scenes[S]
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.scenes.remove(old)
    scn = bpy.data.scenes.new(S)
    bpy.context.window.scene = scn
col = scn.collection

# ------------------------------------------------------------------ materials
def hexc(h, a=1.0):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)

MATS = {}
def toon(name, base, shade, emit=False, hi=None):
    key = "hp_" + name
    if key in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[key])
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    if emit:
        em.inputs["Color"].default_value = hexc(base)
        em.inputs["Strength"].default_value = 1.0
    else:
        dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
        s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        e = ramp.color_ramp.elements
        e[0].position, e[0].color = 0.0, hexc(shade)
        e[1].position, e[1].color = 0.32, hexc(base)
        if hi:                                   # a third, lit tone: the drake's iridescent sheen
            e3 = ramp.color_ramp.elements.new(0.66); e3.color = hexc(hi)
        nt.links.new(dif.outputs[0], s2r.inputs[0])
        nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    MATS[name] = m
    return m

INK = bpy.data.materials.get("hp_ink") or bpy.data.materials.new("hp_ink")
INK.use_nodes = True
_nt = INK.node_tree
for n in list(_nt.nodes):
    _nt.nodes.remove(n)
_o = _nt.nodes.new("ShaderNodeOutputMaterial"); _e = _nt.nodes.new("ShaderNodeEmission")
_e.inputs["Color"].default_value = hexc("#0A0A0F"); _nt.links.new(_e.outputs[0], _o.inputs[0])
INK.use_backface_culling = True

# a drake mallard (owner, 2026-11-20: "make the duck a drake mallard"): a glossy green head, a yellow bill with a dark
# nail, a white neck ring, orange feet, a white tail with the drake's black curl
toon("head", "#20A35B", "#0C5A37", hi="#5BEBB0")
toon("bill", "#F2D23A", "#C29E1A")
toon("nail", "#3A3A2A", "#232318")
toon("feet", "#FF8A1F", "#D25A0A")
toon("ring", "#FFFFFF", "#C9D2DE")
toon("curl", "#1A1D24", "#0B0C10")
toon("jacket", "#7B3FE4", "#4E24A6")
toon("trim", "#8CE33A", "#55A81E")
toon("beanie", "#E8323C", "#A81C24")
toon("pom", "#FFFFFF", "#C9D6E6")
toon("scarf", "#FFB21A", "#D9820A")
toon("pants", "#2B3E8F", "#1A2766")
toon("glove", "#8CE33A", "#55A81E")
toon("sclera", "#FFC9C9", "#E8A0A0")      # a little bloodshot
toon("pupil", "#141018", "#141018")
toon("lens", "#5BC8FF", "#2F86C9")
toon("frame", "#F4F4F4", "#AEB8C6")
toon("white", "#F4F4F4", "#C6CCD6")
toon("bud", "#5CC23A", "#2F7D1D")
toon("lighter", "#3BD6C6", "#1F8F84")
toon("metal", "#C9CED6", "#8A909A")
toon("glass", "#7FE0A0", "#3FA86A")
toon("smoke", "#E9EEF2", "#B8C2CC")
toon("ember", "#FF6A1A", "#FF6A1A", emit=True)
toon("flame", "#FFC83D", "#FFC83D", emit=True)
toon("flame2", "#FF7A1A", "#FF7A1A", emit=True)
toon("tongue", "#FF6F86", "#D9465E")
toon("ski", "#FF3B6B", "#B81E45")
toon("board", "#22D3EE", "#1290A6")

# ------------------------------------------------------------------ armature
arm_data = bpy.data.armatures.new("DuckRigData")
arm = bpy.data.objects.new("DuckRig", arm_data)
col.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
B = {}
def bone(name, head, tail, parent=None, roll=0.0):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail, b.roll = Vector(head), Vector(tail), roll
    if parent:
        b.parent = B[parent]
        b.use_connect = False
    B[name] = b
    return b

bone("root", (0, 0, 0), (0, -.25, 0))
bone("hips", (0, 0, .40), (0, 0, .62), "root")
bone("spine", (0, 0, .62), (0, 0, .80), "hips")
bone("chest", (0, 0, .80), (0, 0, .98), "spine")
bone("neck", (0, 0, .98), (0, 0, 1.08), "chest")
bone("head", (0, 0, 1.08), (0, 0, 1.40), "neck")
bone("jaw", (0, -.16, 1.10), (0, -.36, 1.07), "head")
for s, x in (("L", 1), ("R", -1)):
    bone(f"lid.{s}", (x * .092, -.20, 1.215), (x * .092, -.31, 1.215), "head")
    bone(f"shoulder.{s}", (x * .14, 0, .95), (x * .27, 0, .93), "chest")
    bone(f"upper_arm.{s}", (x * .27, 0, .93), (x * .38, -.05, .68), f"shoulder.{s}")
    bone(f"forearm.{s}", (x * .38, -.05, .68), (x * .41, -.14, .44), f"upper_arm.{s}")
    bone(f"hand.{s}", (x * .41, -.14, .44), (x * .42, -.19, .35), f"forearm.{s}")
    bone(f"thigh.{s}", (x * .13, 0, .42), (x * .14, -.01, .22), "hips")
    bone(f"shin.{s}", (x * .14, -.01, .22), (x * .14, 0, .07), f"thigh.{s}")
    bone(f"foot.{s}", (x * .14, 0, .07), (x * .14, -.20, .02), f"shin.{s}")
bone("tail", (0, .28, .52), (0, .42, .64), "hips")
bone("pom", (0, .05, 1.52), (0, .06, 1.62), "head")       # the pom-pom wobbles on its own (follow-through)
# IK: a wrist target and an elbow pole per arm, both riding the chest (so the hands follow the body)
for s, x in (("L", 1), ("R", -1)):
    bone(f"tgt.{s}", (x * .41, -.14, .44), (x * .41, -.14, .54), "chest")
    bone(f"pole.{s}", (x * .75, .45, .78), (x * .75, .45, .88), "chest")
bone("prop.ground", (.9, 0, 0), (.9, -.2, 0), "root")   # a bong set down beside the duck, etc.
bpy.ops.object.mode_set(mode="POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
for s in ("L", "R"):
    ik = arm.pose.bones[f"forearm.{s}"].constraints.new("IK")
    ik.target, ik.subtarget = arm, f"tgt.{s}"
    ik.pole_target, ik.pole_subtarget = arm, f"pole.{s}"
    ik.pole_angle = math.radians(-90)
    ik.chain_count = 2
bpy.ops.object.mode_set(mode="OBJECT")
arm.data.display_type = "STICK"
arm.show_in_front = True

def bone_mat(name):
    """World matrix of a bone's HEAD in rest pose, axes: Y along the bone."""
    b = arm.data.bones[name]
    return arm.matrix_world @ b.matrix_local

# ------------------------------------------------------------------ meshes
def ellipsoid_bm(r, seg=28, ring=18):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * r[0], v.co.y * r[1], v.co.z * r[2]))
    return bm

def cyl_bm(r1, r2, depth, seg=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=depth)
    return bm

def torus_bm(R, r, seg=36, ring=12):
    bm = bmesh.new()
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for j in range(ring):
            b = 2 * math.pi * j / ring
            bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    bm.verts.ensure_lookup_table()
    for i in range(seg):
        for j in range(ring):
            a, b2 = i * ring + j, ((i + 1) % seg) * ring + j
            c, d = ((i + 1) % seg) * ring + (j + 1) % ring, i * ring + (j + 1) % ring
            bm.faces.new((bm.verts[a], bm.verts[b2], bm.verts[c], bm.verts[d]))
    return bm

def box_bm(dx, dy, dz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dx, v.co.y * dy, v.co.z * dz))
    return bm

PARTS = []
def part(name, bm, mat, world, bone_name, outline=.010, smooth=True, sub=1, parent_obj=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    o.data.materials.append(MATS[mat] if isinstance(mat, str) else mat)
    o.data.materials.append(INK)
    if sub:
        sm = o.modifiers.new("sub", "SUBSURF"); sm.levels = sub; sm.render_levels = sub
    if outline:
        so = o.modifiers.new("ink", "SOLIDIFY")
        so.thickness = outline; so.offset = 1.0; so.use_flip_normals = True; so.material_offset = 1
        so.use_rim = False
    if parent_obj is not None:
        o.parent = parent_obj
        o.matrix_world = world
    elif bone_name:
        o.parent = arm; o.parent_type = "BONE"; o.parent_bone = bone_name
        o.matrix_world = world
    else:
        o.matrix_world = world
    PARTS.append(o)
    return o

T = Matrix.Translation
def along(bone_name, frac=.5):
    """A matrix at the bone (head + frac of its length), axes: the bone's."""
    b = arm.data.bones[bone_name]
    m = bone_mat(bone_name)
    return m @ T((0, b.length * frac, 0))
def at(p, rx=0, ry=0, rz=0):
    return T(p) @ Euler((math.radians(rx), math.radians(ry), math.radians(rz))).to_matrix().to_4x4()

bpy.context.view_layer.update()

# body: belly (hips) and chest (chest) in the jacket, a lime hem, a zip
part("belly", ellipsoid_bm((.36, .32, .27)), "jacket", at((0, 0, .58)), "hips")
part("chestpart", ellipsoid_bm((.31, .28, .23)), "jacket", at((0, -.01, .84)), "chest")
part("hem", torus_bm(.305, .028), "trim", at((0, 0, .47)), "hips", sub=0, outline=.006)
part("zip", box_bm(.018, .02, .30), "trim", at((0, -.305, .66), rx=-8), "spine", outline=.006, sub=0)
part("tail", ellipsoid_bm((.10, .15, .07)), "ring", at((0, .33, .60), rx=-35), "tail")
# the drake curl: a black feather curling up and over off the top of the tail
bm = torus_bm(.055, .016)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < -.02 and v.co.y < 0], context="VERTS")
part("tailcurl", bm, "curl", at((0, .45, .72), ry=90, rx=10), "tail", sub=0, outline=.006)
# neck + scarf
part("neckpart", ellipsoid_bm((.15, .14, .12)), "head", at((0, -.02, 1.02)), "neck")
part("neckring", torus_bm(.198, .026), "ring", at((0, -.02, 1.075), rx=-4), "neck", sub=0, outline=.006)
part("scarf", torus_bm(.165, .055), "scarf", at((0, -.01, 1.0), rx=-6), "chest", sub=0)
part("scarf_tail", box_bm(.07, .035, .20), "scarf", at((.10, -.17, .88), rx=-12, rz=-14), "chest", outline=.008)
# head
part("headball", ellipsoid_bm((.25, .245, .24)), "head", at((0, -.02, 1.22)), "head")
part("bill_top", ellipsoid_bm((.135, .15, .05)), "bill", at((0, -.31, 1.13), rx=6), "head")
part("bill_nail", ellipsoid_bm((.034, .024, .016)), "nail", at((0, -.445, 1.142), rx=6), "head", outline=.005)
part("bill_low", ellipsoid_bm((.115, .13, .035)), "bill", at((0, -.29, 1.075), rx=4), "jaw")
part("tongue", ellipsoid_bm((.06, .07, .02)), "tongue", at((0, -.30, 1.09)), "jaw", outline=0)
for s, x in (("L", 1), ("R", -1)):
    part(f"eye.{s}", ellipsoid_bm((.082, .06, .092)), "sclera", at((x * .092, -.215, 1.215), rz=x * 8), "head", outline=.009)
    part(f"pupil.{s}", ellipsoid_bm((.032, .016, .034)), "pupil", at((x * .086, -.272, 1.200)), "head", outline=0)
    # the upper lid: a cap over the top of the eye, half shut (the lid bone turns it further down or up)
    bm = ellipsoid_bm((.089, .066, .099))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -.004], context="VERTS")
    part(f"lid.{s}", bm, "head", at((x * .092, -.215, 1.215), rx=-22, rz=x * 8), f"lid.{s}", outline=.009)
    # sleeves, gloves, thumbs
    part(f"sleeve_up.{s}", ellipsoid_bm((.078, .16, .078)), "jacket", along(f"upper_arm.{s}"), f"upper_arm.{s}")
    part(f"sleeve_lo.{s}", ellipsoid_bm((.07, .145, .07)), "jacket", along(f"forearm.{s}"), f"forearm.{s}")
    part(f"cuff.{s}", torus_bm(.062, .022), "trim", along(f"forearm.{s}", .95) @ Matrix.Rotation(math.radians(90), 4, "X"), f"forearm.{s}", sub=0)
    part(f"glove.{s}", ellipsoid_bm((.075, .09, .06)), "glove", along(f"hand.{s}", .45), f"hand.{s}")
    part(f"thumb.{s}", ellipsoid_bm((.03, .045, .03)), "glove", along(f"hand.{s}", .3) @ T((-x * .06, 0, -.03)) @ Matrix.Rotation(math.radians(-x * 30), 4, "Z"), f"hand.{s}", outline=.008)
    # legs, feet
    part(f"pantleg.{s}", ellipsoid_bm((.10, .13, .10)), "pants", along(f"thigh.{s}"), f"thigh.{s}")
    part(f"shinpart.{s}", ellipsoid_bm((.035, .09, .035)), "feet", along(f"shin.{s}"), f"shin.{s}", outline=.008)
    foot = ellipsoid_bm((.11, .16, .035))
    part(f"footpart.{s}", foot, "feet", along(f"foot.{s}", .5) @ T((0, 0, -.01)), f"foot.{s}", outline=.008)
# beanie: a cap over the top of the head, a folded band, a pom-pom; goggles pushed up on it
bm = ellipsoid_bm((.262, .258, .25))
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < .02], context="VERTS")
part("beanie", bm, "beanie", at((0, .0, 1.33), rx=-12), "head")
part("beanie_band", torus_bm(.235, .042), "beanie", at((0, .0, 1.355), rx=-12), "head", sub=0)
part("pompom", ellipsoid_bm((.075, .075, .07)), "pom", at((0, .06, 1.60)), "pom")
part("goggle_strap", torus_bm(.25, .018), "frame", at((0, .0, 1.44), rx=-16), "head", sub=0, outline=.006)
for s, x in (("L", 1), ("R", -1)):
    part(f"goggle.{s}", ellipsoid_bm((.075, .03, .055)), "lens", at((x * .075, -.225, 1.47), rx=-30), "head", outline=.008)
    part(f"goggle_rim.{s}", torus_bm(.07, .014), "frame", at((x * .075, -.232, 1.47), rx=60), "head", sub=0, outline=.005)

# ------------------------------------------------------------------ props (hidden until a clip shows them)
PROPS = {}
def prop(name, bm, mat, world, bone_name, outline=.006, sub=1):
    o = part(name, bm, mat, world, bone_name, outline=outline, sub=sub)
    o.hide_render = True; o.hide_viewport = False
    PROPS[name] = o
    return o
hR, hL = "hand.R", "hand.L"
# joint in the right glove: a slim cone, the ember at its far tip
jw = along(hR, .9) @ Matrix.Rotation(math.radians(90), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "Y")
prop("joint", cyl_bm(.014, .026, .22), "white", jw @ T((0, 0, .09)), hR)
prop("ember", ellipsoid_bm((.024, .024, .016)), "ember", jw @ T((0, 0, .205)), hR, outline=0)
# lighter in the left glove, its flame above it
lw = along(hL, .7) @ T((0, -.02, .0))
prop("lighter", box_bm(.065, .038, .12), "lighter", lw @ T((0, 0, .03)), hL, sub=0)
prop("lighter_top", box_bm(.065, .038, .025), "metal", lw @ T((0, 0, .102)), hL, sub=0, outline=.005)
fl = ellipsoid_bm((.026, .026, .065))
prop("flame", fl, "flame", lw @ T((0, 0, .175)), hL, outline=.005)
prop("flame_core", ellipsoid_bm((.013, .013, .032)), "flame2", lw @ T((0, -.006, .155)), hL, outline=0)
# rolling papers (right) and the bud / grinder pinch (left)
prop("papers", box_bm(.12, .005, .07), "white", along(hR, .8) @ T((0, -.02, .02)), hR, sub=0, outline=.004)
prop("bud_pinch", ellipsoid_bm((.04, .04, .036)), "bud", along(hL, .9), hL, outline=.005)
# the bong in the left glove: base bulb, tube, mouthpiece rim, downstem and bowl on the camera side
bw = along(hL, .6) @ Matrix.Rotation(math.radians(-90), 4, "X")   # upright in the glove
prop("bong_base", ellipsoid_bm((.085, .085, .075)), "glass", bw @ T((0, 0, -.16)), hL)
prop("bong_tube", cyl_bm(.036, .036, .34), "glass", bw @ T((0, 0, .02)), hL, sub=0)
prop("bong_rim", torus_bm(.04, .01), "glass", bw @ T((0, 0, .19)), hL, sub=0, outline=.004)
prop("bong_stem", cyl_bm(.009, .009, .12), "metal", bw @ T((.0, -.07, -.13)) @ Matrix.Rotation(math.radians(55), 4, "X"), hL, sub=0, outline=.004)
prop("bong_bowl", cyl_bm(.012, .028, .04), "metal", bw @ T((0, -.12, -.09)) @ Matrix.Rotation(math.radians(55), 4, "X"), hL, sub=0, outline=.004)
prop("bong_weed", ellipsoid_bm((.022, .022, .01)), "bud", bw @ T((0, -.128, -.075)), hL, outline=0)
prop("bowl_glow", ellipsoid_bm((.02, .02, .008)), "ember", bw @ T((0, -.128, -.07)), hL, outline=0)
# a second lighter for the bong (the left glove holds the bong)
lr = along(hR, .7)
prop("lighterR", box_bm(.065, .038, .12), "lighter", lr @ T((0, 0, .03)), hR, sub=0)
prop("lighterR_top", box_bm(.065, .038, .025), "metal", lr @ T((0, 0, .102)), hR, sub=0, outline=.005)
prop("flameR", ellipsoid_bm((.026, .026, .065)), "flame", lr @ T((0, 0, .175)), hR, outline=.005)
prop("flameR_core", ellipsoid_bm((.013, .013, .032)), "flame2", lr @ T((0, -.006, .155)), hR, outline=0)
# ski gear for the skiing ducks: skis under the feet, poles in the gloves, or one snowboard under both feet
for s, x in (("L", 1), ("R", -1)):
    prop(f"ski.{s}", box_bm(.07, .95, .018), "ski", at((x * .14, -.06, .0)), f"foot.{s}", sub=0)            # level
    prop(f"skitip.{s}", ellipsoid_bm((.035, .07, .03)), "ski", at((x * .14, -.55, .025), rx=-25), f"foot.{s}", outline=.005)
    pw = along(f"hand.{s}", .5) @ Matrix.Rotation(math.radians(-15), 4, "X")
    prop(f"skipole.{s}", cyl_bm(.009, .009, .85), "metal", pw @ T((0, .38, 0)) @ Matrix.Rotation(math.radians(90), 4, "X"), f"hand.{s}", sub=0, outline=.004)
prop("snowboard", box_bm(.30, 1.05, .022), "board", at((0, 0, .0), rz=90), "root", sub=0)
# smoke puffs: free objects (no bone) the clips fly out of the bill
for i in range(8):
    o = part(f"puff{i}", ellipsoid_bm((.09, .09, .085)), "smoke", at((0, -.4, 1.1)), None, outline=.006)
    o.hide_render = True
    PROPS[f"puff{i}"] = o

# ------------------------------------------------------------------ camera, light, render
cam_d = bpy.data.cameras.new("DuckCam"); cam_d.type = "ORTHO"; cam_d.ortho_scale = 2.5
cam = bpy.data.objects.new("DuckCam", cam_d); col.objects.link(cam)
cam.location = (0, -6, 1.0); cam.rotation_euler = (math.radians(90), 0, 0)
# the skiers' camera: from the duck's left side, so a skier faces (and travels) screen left
ski_d = bpy.data.cameras.new("SkiCam"); ski_d.type = "ORTHO"; ski_d.ortho_scale = 2.6
skic = bpy.data.objects.new("SkiCam", ski_d); col.objects.link(skic)
skic.location = (6, 0, .75); skic.rotation_euler = (math.radians(90), 0, math.radians(90))
scn.camera = cam
sun_d = bpy.data.lights.new("DuckSun", "SUN"); sun_d.energy = 3.0; sun_d.angle = math.radians(2)
sun = bpy.data.objects.new("DuckSun", sun_d); col.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(-30), math.radians(-25))
# the duck faces a little toward the board (it stands right of the reels, so it turns to its right = screen left)
arm.rotation_euler = (0, 0, math.radians(-22))
r = scn.render
r.engine = "BLENDER_EEVEE"
r.film_transparent = True
r.resolution_x, r.resolution_y, r.resolution_percentage = 512, 640, 100
r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGBA"
r.fps = 24
scn.view_settings.view_transform = "Standard"
scn.view_settings.look = "None"
if scn.world is None:
    scn.world = bpy.data.worlds.new("DuckWorld")
scn.world.use_nodes = True
bg = scn.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (1, 1, 1, 1); bg.inputs["Strength"].default_value = 0.0
try:
    scn.eevee.taa_render_samples = 16
except Exception:
    pass
print("built", len(PARTS), "parts,", len(PROPS), "props,", len(arm.pose.bones), "bones")
