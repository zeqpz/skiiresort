"""High Peaks yeti QA: see-through gaps, measured with qa_holes.py's own test (holes and thin spots INSIDE an outline)
on Blender's pictures of the Rigify rig: each arm alone and the whole figure on a clear page, twice the QA size
(yeti_rigify.py -- arms "" <step>  ->  rig_build/qa_arms/<arm_r|arm_l|all>/<clip>/NNNN.png).
  python tools/highpeaks/yeti/qa_holes_rig.py   -> a table; the worst crops in rig_build/qa_arms/worst/"""
import glob, os, sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from qa_holes import measure

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
QA = os.path.join(ROOT, "art", "highpeaks", "yeti", "rig_build", "qa_arms")
WORST = os.path.join(QA, "worst")


def main():
    os.makedirs(WORST, exist_ok=True)
    for old in glob.glob(os.path.join(WORST, "*.png")):
        os.remove(old)
    for group in ("arm_r", "arm_l", "all"):
        clips = sorted(d for d in os.listdir(os.path.join(QA, group))) if os.path.isdir(os.path.join(QA, group)) else []
        print(f"== {group}")
        flagged = []
        for clip in clips:
            rows = []
            for f in sorted(glob.glob(os.path.join(QA, group, clip, "*.png"))):
                near = None
                if group == "all":                             # only what lies at / in the arms and legs' joints counts
                    m = None
                    for g in ("arm_r", "arm_l"):
                        q = os.path.join(QA, g, clip, os.path.basename(f))
                        if os.path.exists(q):
                            a = np.asarray(Image.open(q).convert("RGBA"))[..., 3] > 20
                            m = a if m is None else (m | a)
                    near = ndimage.binary_dilation(m, iterations=8) if m is not None else None
                rows.append((f, *measure(f, near)))
            if not rows:
                continue
            worst = max(rows, key=lambda r: r[3])
            bad = [r for r in rows if r[3] >= 12]
            print(f"   {clip:13s} frames {len(rows):3d}  worst blob {worst[3]:4d} px ({os.path.basename(worst[0])}, hole {worst[1]}, thin {worst[2]}, at {worst[4]})"
                  f"  frames with a blob >= 12 px: {len(bad)}")
            flagged += [(clip, r) for r in bad]
        for clip, r in sorted(flagged, key=lambda q: -q[1][3])[:6]:
            im = Image.open(r[0]).convert("RGBA")
            x, y = r[4]
            crop = im.crop((x - 90, y - 90, x + 90, y + 90)).resize((360, 360), Image.NEAREST)
            bg = Image.new("RGBA", crop.size, (255, 0, 255, 255))
            bg.alpha_composite(crop)
            bg.convert("RGB").save(os.path.join(WORST, f"{group}_{clip}_{os.path.basename(r[0])}"))
        print(f"   flagged {len(flagged)}")


if __name__ == "__main__":
    main()
