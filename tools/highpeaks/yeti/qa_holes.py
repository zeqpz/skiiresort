"""High Peaks yeti QA: see-through gaps in the arms, measured on the runtime's own pictures (qa_fixes.js draws each arm
alone, every frame of every clip, on a transparent page; and the whole figure every 3rd frame).

A gap between two pieces (upper arm / elbow / forearm / hand / shoulder) shows as pixels INSIDE the arm's outline that
are not opaque: fully transparent (a hole) or partly (a seam's feathered edge lying over nothing). So, per picture:
  solid   = alpha > 20;  inside = solid with its holes filled;  depth = how far a pixel is inside the outline
  hole    = inside but transparent                     (alpha <= 20)
  thin    = inside, deeper than 3 px, and not opaque   (alpha < 235)  - the anti-aliased rim (< 3 px deep) is skipped
For the whole figure the same is measured against the figure's outline (background showing through anywhere in him).
  python tools/highpeaks/yeti/qa_holes.py   -> a table on stdout, the worst frames' crops in qa/fix/worst/"""
import glob, os, sys
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FIX = os.path.join(ROOT, "art", "highpeaks", "yeti", "qa", "fix")
WORST = os.path.join(FIX, "worst")


def measure(path, near=None):
    a = np.asarray(Image.open(path).convert("RGBA"))[..., 3].astype(np.int16)
    solid = a > 20
    inside = ndimage.binary_fill_holes(solid)
    depth = ndimage.distance_transform_edt(inside)
    hole = inside & ~solid
    thin = inside & (a < 235) & (depth > 3)
    bad = hole | thin
    if near is not None:                                  # only what lies at / in the arms counts
        hole, thin, bad = hole & near, thin & near, bad & near
    lab, n = ndimage.label(bad)
    big = 0
    where = None
    if n:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        i = int(np.argmax(sizes))
        big = int(sizes[i])
        ys, xs = np.nonzero(lab == i + 1)
        where = (int(xs.mean()), int(ys.mean()))
    return int(hole.sum()), int(thin.sum()), big, where


def main():
    os.makedirs(WORST, exist_ok=True)
    for group in ("arm_r", "arm_l", "all"):
        files = sorted(glob.glob(os.path.join(FIX, group, "*.png")))
        if not files:
            continue
        per = defaultdict(list)
        for f in files:
            clip = os.path.basename(f).rsplit("_", 1)[0]
            near = None
            if group == "all":                            # the arms in this same frame, grown a little
                arms = [os.path.join(FIX, g, os.path.basename(f)) for g in ("arm_r", "arm_l")]
                m = np.zeros(np.asarray(Image.open(f)).shape[:2], bool)
                for q in arms:
                    if os.path.exists(q):                 # (the arm pictures share the corner, cut shorter)
                        aq = np.asarray(Image.open(q).convert("RGBA"))[..., 3] > 20
                        m[:aq.shape[0], :aq.shape[1]] |= aq[:m.shape[0], :m.shape[1]]
                near = ndimage.binary_dilation(m, iterations=6)
            per[clip].append((os.path.basename(f), *measure(f, near)))
        print(f"== {group}: {len(files)} pictures")
        flagged = []
        for clip, rows in per.items():
            worst = max(rows, key=lambda r: r[3])
            bad_frames = [r for r in rows if r[3] >= 12]
            print(f"   {clip:13s} frames {len(rows):3d}  worst blob {worst[3]:4d} px ({worst[0]}, hole {worst[1]}, thin {worst[2]}, at {worst[4]})"
                  f"  frames with a blob >= 12 px: {len(bad_frames)}")
            flagged += bad_frames
        for r in sorted(flagged, key=lambda r: -r[3])[:6]:
            im = Image.open(os.path.join(FIX, group, r[0])).convert("RGBA")
            x, y = r[4]
            crop = im.crop((x - 80, y - 80, x + 80, y + 80)).resize((320, 320), Image.NEAREST)
            bg = Image.new("RGBA", crop.size, (255, 0, 255, 255))
            bg.alpha_composite(crop)
            bg.convert("RGB").save(os.path.join(WORST, f"{group}_{r[0]}"))
        print(f"   flagged {len(flagged)}")


if __name__ == "__main__":
    main()
