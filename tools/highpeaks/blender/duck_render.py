"""Render every duck clip to PNG frames, in a background Blender:

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/highpeaks/blender/duck_render.py [-- clip ...]

Rebuilds the duck (duck_build.py + duck_anim.py), saves art/highpeaks/blender/duck.blend, then renders each clip in
clips.json to art/highpeaks/renders/duck/<clip>/NNNN.png (transparent). The main duck faces a little toward the
reels (DuckCam, 512x640); the skiers are rendered smaller with their own jacket colours: "ski" from the side
(SkiCam), "board" from the front (the board across the screen, the rider travelling left).
"""
import bpy, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
exec(open(os.path.join(HERE, "duck_build.py")).read())
exec(open(os.path.join(HERE, "duck_anim.py")).read())
scn = bpy.context.scene
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "art", "highpeaks", "blender", "duck.blend"))
clips = json.load(open(os.path.join(ROOT, "art", "highpeaks", "blender", "clips.json")))["clips"]
want = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(clips)
arm = bpy.data.objects["DuckRig"]

def jacket(base, shade):
    m = bpy.data.materials["hp_jacket"]
    ramp = next(n for n in m.node_tree.nodes if n.type == "VALTORGB")
    ramp.color_ramp.elements[0].color = hexc(shade); ramp.color_ramp.elements[1].color = hexc(base)

for name in want:
    c = clips[name]
    if name == "ski":
        scn.camera = bpy.data.objects["SkiCam"]; arm.rotation_euler = (0, 0, 0)
        scn.render.resolution_x = scn.render.resolution_y = 384
        jacket("#FF7A1A", "#C4500A")
    elif name == "board":
        scn.camera = bpy.data.objects["DuckCam"]; arm.rotation_euler = (0, 0, 0)
        scn.render.resolution_x = scn.render.resolution_y = 384
        bpy.data.objects["DuckCam"].data.ortho_scale = 2.4
        jacket("#FF4FA3", "#B8236E")
    else:
        scn.camera = bpy.data.objects["DuckCam"]; arm.rotation_euler = (0, 0, math.radians(-22))
        bpy.data.objects["DuckCam"].data.ortho_scale = 2.5
        scn.render.resolution_x, scn.render.resolution_y = 512, 640
        jacket("#7B3FE4", "#4E24A6")
    scn.frame_start, scn.frame_end = c["start"], c["end"]
    out = os.path.join(ROOT, "art", "highpeaks", "renders", "duck", name)
    os.makedirs(out, exist_ok=True)
    scn.render.filepath = os.path.join(out, "")
    bpy.ops.render.render(animation=True)
    print("rendered", name, c["frames"], "frames", flush=True)
