"""High Peaks: the yeti cut into puppet pieces, each piece REDRAWN whole by the image model.

The master drawing (art/highpeaks/yeti/master/yeti_master.v2.png, 1024 x 1536 = the art px every rig coordinate is
in) is one picture: the arms lie over the jacket, the head's fur ruff over the collar, the jacket hem over the trousers,
the hand over the snowboard, the boots on the snow. Each SHEET (one model call: one piece, or two that sit apart, like
the two arms) is drawn again from a LAYOUT - the master cropped round its pieces, everything else faded back - with the
whole figure as its style, so what one piece hid of another is real drawing (the shoulder caps, the trousers up to the
hip, the board's whole top, the snow under the boots, a neck stub under the ruff). The redraw is laid back over the
master by SIFT + RANSAC (orleans' doc_regen fit) and cut into its pieces (each pixel goes to the piece whose outline on
the master it lies deepest inside, or nearest to).

The reaction faces are ONE sheet: six copies of the new head in a 3 x 2 grid, each with only its expression changed,
each laid back onto the head by SIFT.

Image calls run one at a time (shared OpenRouter credit): 6 sheets + 1 face sheet.

  layout [sheet,..]  art/highpeaks/yeti/regen/<sheet>_layout.png, _trusted.png, .json
  gen    [sheet,..]  <sheet>_raw.png (OpenRouter via orgen.py; the key is never printed)
  faces              faces_raw.png
  fit    [sheet,..]  -> art/highpeaks/yeti/parts/<part>.png + parts.json (box in PLATE px = art px x K)
  fitfaces           -> parts/face_<name>.png
  trim               the neck stub under the ruff cut off every head (the body's chest fur fills behind it)
  joint              the joint drawn on past his fingers on the mouth side (arm_r_lo): as drawn its end hid in his
                     fist, so with the end on his lips the fingers covered them; now it sticks out of the fist to his lips
  splitarm           the joint arm cut in two along the ink ring at the elbow: arm_r_up (shoulder to elbow, drawn
                     behind the head) and arm_r_lo (elbow ring, forearm, hand and joint, in front of it) - a folded
                     arm (the joint to his lips) is then a forearm crossing over its upper arm, not a crumpled sleeve
  sheet              regen/_sheet.png (master | rebuilt figure), regen/_figure.png, regen/_faces.png
usage: python tools/highpeaks/yeti/yeti_parts.py layout|gen|faces|fit|fitfaces|trim|sheet [names]"""
import json, os, sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import orgen

ROOT = orgen.ROOT
ART = os.path.join(ROOT, "art", "highpeaks", "yeti")
MASTER = os.path.join(ART, "master", "yeti_master.v2.png")
WORK = os.path.join(ART, "regen")
PARTS_DIR = os.path.join(ART, "parts")
K = 2.0                                     # plate px per art px
W_ART, H_ART = 1024, 1536
CANVAS = {"2:3": (1024, 1536), "3:2": (1536, 1024), "1:1": (1024, 1024)}
MARGIN = .07

# back to front
ORDER = ["board", "snow", "leg_l", "leg_r", "body", "arm_l", "arm_r_up", "head", "arm_r_lo"]

# every piece's generous outline on the master (art px)
POLY = {
    "head": [(230, 30), (430, 30), (630, 110), (650, 280), (730, 320), (735, 460), (690, 540), (650, 610),
             (560, 640), (460, 630), (370, 600), (300, 540), (265, 430), (270, 330), (225, 250), (215, 130)],
    "body": [(195, 470), (450, 470), (520, 560), (640, 470), (850, 470), (870, 1090), (180, 1090)],
    "arm_l": [(450, 490), (400, 455), (250, 480), (110, 580), (45, 670), (25, 770), (60, 845), (240, 845),
              (250, 760), (290, 735), (380, 720), (440, 690)],
    "arm_r": [(640, 500), (720, 520), (780, 600), (790, 560), (760, 420), (820, 390), (880, 400), (990, 410),
              (990, 470), (930, 520), (960, 640), (930, 790), (800, 820), (700, 800), (650, 700)],
    "leg_l": [(215, 990), (530, 990), (535, 1110), (470, 1250), (445, 1300), (450, 1460), (160, 1460),
              (185, 1280), (215, 1110)],
    "leg_r": [(520, 990), (830, 990), (830, 1260), (880, 1460), (585, 1460), (595, 1290), (555, 1160),
              (520, 1100)],
    "board": [(25, 760), (230, 760), (235, 1475), (25, 1475)],
    "snow": [(15, 1370), (1000, 1370), (1000, 1530), (15, 1530)],
}
SHEETS = {
    "head": ("1:1", ["head"],
             "Draw: his HEAD ONLY - the red-orange knit beanie with its white pom-pom, the ski goggles with the "
             "mirrored purple lens pushed up on the beanie, his pale blue-grey face with the same heavy-lidded stoned "
             "eyes, big round dark-blue nose and wide open happy grin with two small lower fangs, the white fur tufts on "
             "his cheeks and the shaggy white fur ruff round his face, ending under his chin in a ring of pointed fur "
             "tufts. Below the ruff draw a short stub of white furry neck, ending in a flat cut. NO jacket, NO collar, "
             "NO shoulders, NO body, NO arms, NO hands, NO joint, NO smoke."),
    "body": ("2:3", ["body"],
             "Draw: his TORSO ONLY - the unzipped bright lime-green puffer jacket (both front panels with their "
             "puffy quilted rings, the grey zips down both open edges, the patch pocket, the hem) and his shaggy white "
             "furry chest and round belly showing between the open panels, the belly fur ending in pointed tufts at "
             "the bottom. NO head: at the top, the jacket's collar round the bottom of the white chest fur, and a short "
             "stub of white furry neck. NO arms: each SHOULDER ends in a smooth ROUNDED cap of puffy lime-green jacket "
             "where the sleeve was taken off (no stump of an arm). NO legs, NO trousers."),
    "arms": ("3:2", ["arm_l", "arm_r"],
             "Draw: his TWO ARMS ONLY, each exactly where it is in image 2, with the empty space of his body left "
             "between them. The arm on the viewer's LEFT: the puffy lime-green quilted jacket sleeve curving down and "
             "out from the shoulder, the white fur cuff, the big furry four-fingered hand with pale blue-grey skin, its "
             "fingers curled over as if resting on top of something (do NOT draw the snowboard: the hand is empty). The "
             "arm on the viewer's RIGHT: the puffy lime-green sleeve bent at the elbow (the elbow at the bottom, the "
             "forearm rising), the white fur cuff, the big furry hand raised, holding the lit joint between two fingers "
             "(a thin white rolled joint with a glowing orange tip) - but NO smoke at all. Each sleeve was cut off at "
             "the shoulder: COMPLETE its top end as a smooth rounded puffy shoulder cap. NO body, NO jacket front, NO "
             "zips, NO head."),
    "legs": ("3:2", ["leg_l", "leg_r"],
             "Draw: his TWO LEGS ONLY, each exactly where it is in image 2: the baggy purple ski trouser legs with "
             "their cargo pockets and the chunky orange snowboard boots with grey buckles. The tops of the legs are "
             "hidden in image 2 by the jacket and the belly fur: DRAW each thigh as clean purple trouser right up to a "
             "flat top edge at the hip. NO snow under the boots, NO jacket, NO fur, NO snowboard."),
    "board": ("2:3", ["board"],
              "Draw: the SNOWBOARD ONLY, standing upright exactly as in image 2: a bright yellow snowboard with purple "
              "flame graphics seen from the front, its rounded nose at the top. In image 2 a furry hand covers its top: "
              "do NOT draw the hand - draw the board's whole rounded top end. Draw its whole rounded tail at the "
              "bottom. NO snow, NO hand."),
    "snow": ("3:2", ["snow"],
             "Draw: the SNOW MOUND ONLY, exactly as in image 2: a low wide rounded mound of white snow with pale "
             "icy-blue shade shapes and a black outline. In image 2 two boots and a snowboard stand on it: do NOT draw "
             "them - draw the whole top of the mound, clean snow where they stood. NO boots, NO board, NO character."),
}
STYLE = ("STYLE - match image 1 exactly: a flat 2D adult-animation sitcom cartoon, thick clean black ink outlines of "
         "the same weight as in image 1, flat solid colour fills with one simple hard-edged darker shade, crisp sharp "
         "vector-quality linework at high resolution: no blur, no smudges, no gradients, no airbrush, no glow, no "
         "texture, no 3D rendering. Transparent background. Draw ONLY what is asked: no other body parts, no other "
         "characters, no text, no ground, no shadow, no border.")
HEADER = ("Image 1 is the whole character (an original cartoon yeti in ski gear) for style and colour. Image 2 is "
          "cut out of that drawing so he can be animated as a puppet (everything that is not wanted is faded out). "
          "REDRAW the wanted piece(s) cleanly at high quality: the same shapes, the same pose and angle, the SAME SIZE "
          "AND POSITION on the canvas (it must lie exactly over image 2), the same colours. ")
# the face sheet: 3 x 2, read left to right, top row first
FACES = [
    ("blink", "both eyes fully CLOSED in a slow relaxed blink (curved closed eyelid lines), the same happy grin"),
    ("puff", "taking a puff: lips pursed into a small round O as if drawing on a joint, cheeks puffed out a little, "
             "eyes half closed and blissful"),
    ("cheer", "ecstatic: a huge wide open toothy grin, eyes wide open and sparkling with small round pupils, eyebrows "
              "raised high"),
    ("nervous", "nervous, on the edge of his seat: eyes popped WIDE open staring, tiny pupils, mouth a tight wobbly "
                "clenched grimace showing teeth, one bead of sweat on his forehead under the beanie"),
    ("sad", "deflated and disappointed: droopy half-closed eyes looking down, mouth a wobbly frown, eyebrows tilted "
            "up in the middle"),
    ("laugh", "laughing hard: eyes squeezed shut into happy crescents, mouth wide open"),
]


def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


def poly_mask(poly, size=(W_ART, H_ART), k=1.0):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon([(x * k, y * k) for x, y in poly], fill=255)
    return np.asarray(m) > 0


def layout(sheet):
    """The master cropped round the sheet's pieces, all else faded to a ghost, on the model's canvas; the TRUSTED
    picture (only the pieces) for the fit; where it sits (s canvas px per art px, offset, the crop's box)."""
    aspect, members, _ = SHEETS[sheet]
    m = rgba(MASTER)
    inside = np.zeros((H_ART, W_ART), bool)
    xs, ys = [], []
    for p in members:
        inside |= poly_mask(POLY[p])
        xs += [q[0] for q in POLY[p]]
        ys += [q[1] for q in POLY[p]]
    x0, y0, x1, y1 = max(0, min(xs)), max(0, min(ys)), min(W_ART, max(xs)), min(H_ART, max(ys))
    faded = m.copy()
    faded[~inside, 3] *= .18
    crop = Image.fromarray(faded[y0:y1, x0:x1].astype(np.uint8), "RGBA")
    cw, ch = CANVAS[aspect]
    s = min(cw * (1 - 2 * MARGIN) / crop.width, ch * (1 - 2 * MARGIN) / crop.height)
    w, h = round(crop.width * s), round(crop.height * s)
    ox, oy = (cw - w) // 2, (ch - h) // 2
    can = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    can.paste(crop.resize((w, h), Image.LANCZOS), (ox, oy))
    tr = m.copy()
    tr[~inside, 3] = 0
    trc = Image.fromarray(tr[y0:y1, x0:x1].astype(np.uint8), "RGBA").resize((w, h), Image.LANCZOS)
    trusted = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    trusted.paste(trc, (ox, oy))
    return can, trusted, {"s": s, "ox": ox, "oy": oy, "box": [x0, y0, x1 - x0, y1 - y0], "canvas": [cw, ch]}


def full_ref():
    p = os.path.join(WORK, "_full.png")
    if not os.path.exists(p):
        os.makedirs(WORK, exist_ok=True)
        Image.open(MASTER).convert("RGBA").save(p)
    return p


def make_layout(sheet):
    os.makedirs(WORK, exist_ok=True)
    can, trusted, info = layout(sheet)
    can.save(os.path.join(WORK, sheet + "_layout.png"))
    trusted.save(os.path.join(WORK, sheet + "_trusted.png"))
    json.dump(info, open(os.path.join(WORK, sheet + "_layout.json"), "w"))


def _gen(path_name, prompt, aspect, refs):
    orgen.RAW = WORK
    rec = orgen.generate(dict(name=path_name, prompt=prompt, aspect_ratio=aspect, background="transparent", refs=refs))
    if rec.get("error"):
        return f"FAIL {path_name} {rec['error'][:200]}"
    out = os.path.join(ROOT, rec["file"])
    want = os.path.join(WORK, path_name + ".png")
    if os.path.abspath(out) != os.path.abspath(want):     # keep the newest as <name>.png, older ones as .oldN
        n = 1
        while os.path.exists(os.path.join(WORK, f"{path_name}.old{n}.png")):
            n += 1
        os.replace(want, os.path.join(WORK, f"{path_name}.old{n}.png"))
        os.replace(out, want)
    return f"OK {path_name} {rec.get('cost')}"


def gen(sheet):
    make_layout(sheet)
    return _gen(sheet + "_raw", HEADER + SHEETS[sheet][2] + " " + STYLE, SHEETS[sheet][0],
                [full_ref(), os.path.join(WORK, sheet + "_layout.png")])


def faces():
    src = os.path.join(WORK, "head_raw.png")
    lines = "; ".join(f"({i + 1}) {d}" for i, (_, d) in enumerate(FACES))
    p = ("The attached image is a cartoon yeti's head. Draw a SHEET of SIX copies of EXACTLY this head in a neat grid "
         "of 3 columns and 2 rows, every copy the same size and facing the same way, evenly spaced with a clear gap "
         "between them, on a fully transparent background. Each copy keeps the same beanie and pom-pom, the same "
         "goggles, the same fur ruff and cheek tufts, the same outlines and colours - only the facial expression "
         "(eyes, eyelids, eyebrows, mouth) changes. Read left to right, top row first: " + lines + ". Crisp clean flat "
         "cartoon linework, flat colour, no other changes, no labels, no numbers, no text, no smoke, no other "
         "characters.")
    return _gen("faces_raw", p, "3:2", [src])


def over(im, bg=128.0):
    a = im[..., 3:4] / 255.
    return ((im[..., :3] * a + bg * (1 - a)) @ np.float32([.3, .59, .11])).clip(0, 255).astype(np.uint8)


def similar(raw, lay, nfeat=8000):
    sift = cv2.SIFT_create(nfeatures=nfeat, contrastThreshold=.02)
    g0, g1 = over(raw), over(lay)
    k0, d0 = sift.detectAndCompute(g0, (raw[..., 3] > 40).astype(np.uint8) * 255)
    k1, d1 = sift.detectAndCompute(g1, (lay[..., 3] > 40).astype(np.uint8) * 255)
    if d0 is None or d1 is None or len(k0) < 8 or len(k1) < 8:
        return None, 0, 0
    good = [m for m, n in cv2.BFMatcher(cv2.NORM_L2).knnMatch(d0, d1, k=2) if m.distance < .8 * n.distance]
    if len(good) < 8:
        return None, len(good), 0
    src = np.float32([k0[m.queryIdx].pt for m in good])
    dst = np.float32([k1[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=6, maxIters=8000,
                                         confidence=.999)
    return M, len(good), int(inl.sum()) if inl is not None else 0


def bbox_fit(raw, lay, by_width=False):
    def bb(a):
        ys, xs = np.nonzero(a[..., 3] > 60)
        return xs.min(), ys.min(), xs.max(), ys.max()
    x0, y0, x1, y1 = bb(raw)
    u0, v0, u1, v1 = bb(lay)
    if by_width:                                   # boots stand on the mound in the layout: its width and its foot
        k = (u1 - u0) / (x1 - x0)
        return np.float32([[k, 0, (u0 + u1) / 2 - k * (x0 + x1) / 2], [0, k, v1 - k * y1]])
    k = ((u1 - u0) / (x1 - x0) + (v1 - v0) / (y1 - y0)) / 2
    return np.float32([[k, 0, (u0 + u1) / 2 - k * (x0 + x1) / 2], [0, k, (v0 + v1) / 2 - k * (y0 + y1) / 2]])


def tidy(im):
    a = im[..., 3]
    near = ndimage.binary_dilation(a > 128, iterations=3)
    im[..., 3] = np.where(near, a, 0)
    return im


BBOX = ("snow",)                            # a plain shape: laid box on box (by its width, bottoms aligned)
NUDGE = {}                                  # sheet -> (scale, dx, dy) in layout-canvas px about its middle


def warp_to_plate(im, P, pad=8):
    """A canvas picture (float RGBA) through P (canvas px -> PLATE px): the crop round its ink, and that crop's box."""
    ys, xs = np.nonzero(im[..., 3] > 8)
    corners = np.float32([[xs.min(), ys.min(), 1], [xs.max(), ys.min(), 1], [xs.min(), ys.max(), 1], [xs.max(), ys.max(), 1]])
    pc = corners @ P.T
    x0, y0 = int(np.floor(pc[:, 0].min())) - pad, int(np.floor(pc[:, 1].min())) - pad
    x1, y1 = int(np.ceil(pc[:, 0].max())) + pad, int(np.ceil(pc[:, 1].max())) + pad
    W, H = x1 - x0, y1 - y0
    Q = P.copy()
    Q[:, 2] -= [x0, y0]
    Q *= 2
    pm = im.copy()
    pm[..., :3] *= pm[..., 3:4] / 255.
    big = cv2.warpAffine(pm, Q, (W * 2, H * 2), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
    out = cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
    al = out[..., 3:4].clip(0, 255)
    out[..., :3] = np.where(al > 1, out[..., :3] * 255. / np.maximum(al, 1), 0)
    return out.clip(0, 255), [int(x0), int(y0), int(W), int(H)]


def fit_sheet(sheet):
    raw = tidy(rgba(os.path.join(WORK, sheet + "_raw.png")))
    info = json.load(open(os.path.join(WORK, sheet + "_layout.json")))
    trusted = rgba(os.path.join(WORK, sheet + "_trusted.png"))
    cw, ch = info["canvas"]
    if raw.shape[1] != cw or raw.shape[0] != ch:
        raw = cv2.resize(raw, (cw, ch), interpolation=cv2.INTER_AREA)
    M, n_good, n_in = (None, 0, 0) if sheet in BBOX else similar(raw, trusted)
    how = f"sift {n_in}/{n_good}"
    if M is None or n_in < 12 or not (.4 < float(np.hypot(M[0][0], M[1][0])) < 2.5):
        M, how = bbox_fit(raw, trusted, sheet == "snow"), f"bbox (sift {n_in}/{n_good})"
    M = np.float32(M)
    if sheet in NUDGE:
        k, dx, dy = NUDGE[sheet]
        c = np.float32([cw / 2, ch / 2])
        M[:, :2] *= k
        M[:, 2] = (M[:, 2] - c) * k + c + np.float32([dx, dy])
    s, ox, oy = info["s"], info["ox"], info["oy"]
    bx, by = info["box"][:2]
    P = np.float32([[M[0, 0] / s, M[0, 1] / s, (M[0, 2] - ox) / s + bx],
                    [M[1, 0] / s, M[1, 1] / s, (M[1, 2] - oy) / s + by]]) * K
    json.dump({"P": P.tolist(), "canvas": [cw, ch]}, open(os.path.join(WORK, sheet + "_fit.json"), "w"))
    out, box = warp_to_plate(raw, P)
    return out, box, f"{how}  scale {float(np.hypot(M[0, 0], M[1, 0])):.3f} turn {float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))):+.2f}"


def split(out, box, members):
    """The fitted sheet into its pieces: every inked pixel to the piece whose master outline it lies deepest inside
    (or, outside them all, nearest to). -> {part: (picture, box)}"""
    if len(members) == 1:
        return {members[0]: (out, box)}
    x0, y0, W, H = box
    sd = []
    for p in members:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([(x * K - x0, y * K - y0) for x, y in POLY[p]], fill=255)
        m = np.asarray(m) > 0
        sd.append(np.where(m, ndimage.distance_transform_edt(m), -ndimage.distance_transform_edt(~m)))
    owner = np.argmax(np.stack(sd), 0)
    res = {}
    for i, p in enumerate(members):
        im = out.copy()
        im[owner != i, 3] = 0
        ys, xs = np.nonzero(im[..., 3] > 8)
        a, b, c, d = xs.min() - 6, ys.min() - 6, xs.max() + 7, ys.max() + 7
        a, b = max(0, a), max(0, b)
        res[p] = (im[b:d, a:c], [int(x0 + a), int(y0 + b), int(c - a), int(d - b)])
    return res


def meta_path():
    return os.path.join(PARTS_DIR, "parts.json")


def load_meta():
    p = meta_path()
    if os.path.exists(p):
        return json.load(open(p))
    return {"art": [W_ART, H_ART], "scale": K, "size": [int(W_ART * K), int(H_ART * K)], "order": ORDER,
            "parts": {}, "faces": {}}


def fit(names):
    os.makedirs(PARTS_DIR, exist_ok=True)
    meta = load_meta()
    for sheet in names:
        if not os.path.exists(os.path.join(WORK, sheet + "_raw.png")):
            print("no raw for", sheet)
            continue
        out, box, note = fit_sheet(sheet)
        print(f"{sheet:6s} {note}", flush=True)
        for p, (im, b) in split(out, box, SHEETS[sheet][1]).items():
            Image.fromarray(im.astype(np.uint8), "RGBA").save(os.path.join(PARTS_DIR, p + ".png"))
            meta["parts"][p] = {"box": b}
            print(f"   {p:6s} box {b}", flush=True)
    json.dump(meta, open(meta_path(), "w"), indent=1)


def fit_faces():
    """Cut the face sheet into its six heads (the grid's cells, each trimmed to its ink) and lay each onto the head
    piece by SIFT (similarity), then onto the plate through the head sheet's own fit."""
    sheet = tidy(rgba(os.path.join(WORK, "faces_raw.png")))
    head = tidy(rgba(os.path.join(WORK, "head_raw.png")))
    P = np.float32(json.load(open(os.path.join(WORK, "head_fit.json")))["P"])
    H, W = sheet.shape[:2]
    meta = load_meta()
    meta["faces"] = {}
    lab, n = ndimage.label(ndimage.binary_dilation(sheet[..., 3] > 40, iterations=6))
    blobs = sorted(((ndimage.sum(np.ones_like(lab), lab, i), i) for i in range(1, n + 1)), reverse=True)[:6]
    cells = []
    for _, i in blobs:
        ys, xs = np.nonzero(lab == i)
        cells.append((ys.min(), xs.min(), ys.max(), xs.max(), i))
    cells.sort(key=lambda c: (round((c[0] + c[2]) / 2 / (H / 2)), (c[1] + c[3]) / 2))   # rows, then left to right
    for (name, _), (ya, xa, yb, xb, i) in zip(FACES, cells):
        cut = sheet.copy()
        cut[lab != i, 3] = 0
        cut = cut[ya:yb + 1, xa:xb + 1]
        M, n_good, n_in = similar(cut, head, 6000)
        if M is None or n_in < 10:
            print(f"face {name}: sift {n_in}/{n_good} - bbox", flush=True)
            M = bbox_fit(cut, head)
        M = np.float32(M)
        # cut px -> head canvas px (M) -> plate (P)
        A = np.vstack([P, [0, 0, 1]]) @ np.vstack([M, [0, 0, 1]])
        out, box = warp_to_plate(cut, A[:2])
        Image.fromarray(out.astype(np.uint8), "RGBA").save(os.path.join(PARTS_DIR, f"face_{name}.png"))
        meta["faces"][name] = {"box": box}
        print(f"face {name:8s} box {box}  sift {n_in}/{n_good}  scale {float(np.hypot(M[0, 0], M[1, 0])):.3f}", flush=True)
    json.dump(meta, open(meta_path(), "w"), indent=1)


NECK_CUT = (415, 590, 604)                 # art px: x from, x to, and the line under the ruff's tufts


def trim():
    """The model drew a flat-cut neck stub under the ruff, outline and all: it lay over the chest fur as a box.
    Cut it off every head (feathered over 3 px); the body's own chest fur is drawn behind."""
    meta = load_meta()
    x0, x1, yc = [v * K for v in NECK_CUT]
    for key, rec in [("head", meta["parts"]["head"])] + [(f"face_{f}", r) for f, r in meta["faces"].items()]:
        path = os.path.join(PARTS_DIR, key + ".png")
        im = rgba(path)
        bx, by = rec["box"][:2]
        H, W = im.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]
        yy, xx = yy + by, xx + bx
        cut = np.clip((yy - yc) / (3 * K), 0, 1) * ((xx > x0) & (xx < x1))
        im[..., 3] *= 1 - cut
        Image.fromarray(im.astype(np.uint8), "RGBA").save(path)
        print("trimmed", key)


# the left edge of the ink ring round the elbow (art px), top to bottom: right of it is the forearm piece. It runs
# LEFT of the fur cuff (2026-11-20: it cut through the cuff, and a sliver of it was in neither piece - the see-through
# notch at the cuff as he lifts the joint)
ELBOW_CUT = [(712, 380), (712, 566), (722, 596), (720, 622), (705, 652), (678, 688), (663, 740), (674, 786), (698, 822)]
UP_OVERLAP = 64                            # art px of the forearm's ring the upper piece keeps under it (a deep
                                           # underlay: whatever the elbow does, sleeve shows there, never sky)


def sleeve_underlay(out, im, up, lo, near):
    """The upper piece's underlay made SOLID (owner, 2026-11-20: "the arms have a spot that glitches and shows
    transparency in between"): under the forearm the upper piece used to keep only the sleeve's own pixels and drop the
    cuff's white fur - so as the forearm folded up to his lips, the strip where the cuff had been was empty and the sky
    showed through in the crook (idle frames ~95 and ~162, lose, big_win). Now everything of the arm inside that strip
    is flat sleeve green, with the arm's ink along its own outline, so the crook only ever shows sleeve."""
    rgb = im[..., :3]
    inside = im[..., 3] > 128
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV)
    limeish = inside & (hsv[..., 0] > 25) & (hsv[..., 0] < 45) & (hsv[..., 1] > 140) & (hsv[..., 2] > 170)
    lime = np.median(rgb[limeish], axis=0) if limeish.any() else np.array([181, 230, 29], np.float32)
    strip = lo & near & inside
    rim = ndimage.distance_transform_edt(inside) <= 4.5 * K      # the arm's own outline, kept as ink
    out[strip & ~rim, :3] = lime
    out[strip & rim, :3] = (12, 12, 18)
    out[strip, 3] = 255 * up[strip]                               # its far edge stays feathered (up's soft edge)
    return out


def splitarm(only_up=False):
    meta = load_meta()
    rec = meta["parts"]["arm_r"]
    im = rgba(os.path.join(PARTS_DIR, "arm_r.png"))
    bx, by, W, H = rec["box"]
    poly = [(x * K - bx, y * K - by) for x, y in ELBOW_CUT] + [((ELBOW_CUT[-1][0] + 400) * K - bx, ELBOW_CUT[-1][1] * K - by),
                                                                ((ELBOW_CUT[0][0] + 400) * K - bx, ELBOW_CUT[0][1] * K - by)]
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    lo = np.asarray(m) > 0
    depth = ndimage.distance_transform_edt(lo)            # how far inside the forearm's side of the cut
    near = depth <= UP_OVERLAP * K
    soft = np.clip((UP_OVERLAP * K - depth) / (3 * K), 0, 1)   # the overlap's far edge feathered
    yy, xx = np.mgrid[0:H, 0:W]
    # the upper piece never carries a scrap of the cuff or the hand (white fur, pale skin) - but it does keep the green
    # sleeve and its ink under the cuff, so the seam there shows sleeve, never sky, while the forearm turns
    pale = (im[..., :3].min(-1) > 150) | ((im[..., 2] > im[..., 1] + 10) & (im[..., 0] > 120))
    cuff = ((yy + by) < 645 * K) & ((xx + bx) > 728 * K) & pale
    up = np.where(lo, soft, 1.0) * np.where(near | ~lo, 1, 0) * np.where(cuff & ~lo, 0, 1)
    for name, keep in (("arm_r_lo", lo.astype(np.float32)), ("arm_r_up", up)):
        if only_up and name == "arm_r_lo":
            continue
        out = im.copy()
        out[..., 3] *= keep
        if name == "arm_r_up":
            out = sleeve_underlay(out, im, up, lo, near)
        ys, xs = np.nonzero(out[..., 3] > 8)
        a, b, c, d = max(0, xs.min() - 6), max(0, ys.min() - 6), xs.max() + 7, ys.max() + 7
        Image.fromarray(out[b:d, a:c].astype(np.uint8), "RGBA").save(os.path.join(PARTS_DIR, name + ".png"))
        meta["parts"][name] = {"box": [int(bx + a), int(by + b), int(c - a), int(d - b)]}
        print(name, meta["parts"][name]["box"])
    meta["order"] = ORDER
    json.dump(meta, open(meta_path(), "w"), indent=1)


# the joint (art px): its end as drawn (in the fist) and its lit tip; it is drawn on JOINT_EXT px further out of the fist
J_END, J_TIP = (845, 480), (950, 437)
JOINT_EXT = 60
# its cross-section, offsets (art px) across it on the side normal (-uy, ux): ink, light paper, shaded paper, ink
J_INK_A, J_LIGHT, J_SHADE, J_INK_B = (-13.5, -8.5), (-8.5, .5), (.5, 5.5), (5.5, 10.5)


def joint():
    """Draw the joint on, out of the fist toward his mouth: the same paper, shade and ink as the drawn joint, over the
    fingers it now crosses, ending in a rounded end. Idempotent from arm_r_lo_drawn.png (the piece before this)."""
    import math
    meta = load_meta()
    rec = meta["parts"]["arm_r_lo"]
    src = os.path.join(PARTS_DIR, "arm_r_lo_drawn.png")
    if not os.path.exists(src):
        Image.open(os.path.join(PARTS_DIR, "arm_r_lo.png")).save(src)
    base = Image.open(src).convert("RGBA")
    bx, by = rec["box"][:2]
    ux, uy = J_TIP[0] - J_END[0], J_TIP[1] - J_END[1]
    L = math.hypot(ux, uy)
    ux, uy = ux / L, uy / L
    nx, ny = -uy, ux
    SS = 4
    layer = Image.new("RGBA", (base.width * SS, base.height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    t0, t1 = -JOINT_EXT, 14                           # from the new end to a little over the drawn joint (it blends in)

    def P(t, s_):
        x, y = J_END[0] + ux * t + nx * s_, J_END[1] + uy * t + ny * s_
        return ((x * K - bx) * SS, (y * K - by) * SS)

    def band(a, b, col, cap=True):
        d.polygon([P(t0, a), P(t1, a), P(t1, b), P(t0, b)], fill=col)
        if cap:                                       # the rounded end
            c = P(t0, (a + b) / 2)
            r = abs(b - a) / 2 * K * SS
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=col)
    ink, light, shade = (2, 2, 3, 255), (253, 244, 219, 255), (206, 198, 176, 255)
    band(J_INK_A[0], J_INK_B[1], ink)                 # the whole width in ink, then the paper inside it
    band(J_LIGHT[0], J_SHADE[1], light, cap=False)
    band(J_SHADE[0], J_SHADE[1], shade, cap=False)
    # the paper's own rounded end, inside the ink
    c = P(t0 + 1.5, (J_LIGHT[0] + J_SHADE[1]) / 2)
    r = (J_SHADE[1] - J_LIGHT[0]) / 2 * K * SS
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=light)
    layer = layer.resize(base.size, Image.LANCZOS)
    out = Image.alpha_composite(base, layer)
    out.save(os.path.join(PARTS_DIR, "arm_r_lo.png"))
    end = (J_END[0] - ux * JOINT_EXT, J_END[1] - uy * JOINT_EXT)
    print("joint drawn on to", tuple(round(v, 1) for v in end))


def figure(face=None, order=None):
    meta = load_meta()
    Wp, Hp = meta["size"]
    can = Image.new("RGBA", (Wp, Hp), (0, 0, 0, 0))
    for nm in order or meta["order"]:
        use_face = nm == "head" and face
        rec = meta["faces"].get(face) if use_face else meta["parts"].get(nm)
        if not rec:
            continue
        im = Image.open(os.path.join(PARTS_DIR, (f"face_{face}" if use_face else nm) + ".png")).convert("RGBA")
        tmp = Image.new("RGBA", (Wp, Hp), (0, 0, 0, 0))
        tmp.paste(im, tuple(rec["box"][:2]))
        can = Image.alpha_composite(can, tmp)
    return can


def sheet_img():
    a = Image.open(MASTER).convert("RGBA").resize((512, 768), Image.LANCZOS)
    fig = figure()
    fig.save(os.path.join(WORK, "_figure.png"))
    b = fig.resize((512, 768), Image.LANCZOS)
    sh = Image.new("RGBA", (1024, 768), (110, 160, 220, 255))
    sh.alpha_composite(a, (0, 0))
    sh.alpha_composite(b, (512, 0))
    sh.convert("RGB").save(os.path.join(WORK, "_sheet.png"))
    meta = load_meta()
    if meta["faces"]:
        heads = []
        for f in [None] + list(meta["faces"]):
            fg = figure(f).crop((int(200 * K), 0, int(780 * K), int(700 * K))).resize((290, 350), Image.LANCZOS)
            heads.append(fg)
        fs = Image.new("RGBA", (290 * len(heads), 350), (110, 160, 220, 255))
        for i, h in enumerate(heads):
            fs.alpha_composite(h, (i * 290, 0))
        fs.convert("RGB").save(os.path.join(WORK, "_faces.png"))
    print("sheet", os.path.join(WORK, "_sheet.png"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    full_ref()
    if cmd == "layout":
        for p in names or list(SHEETS):
            make_layout(p)
            print("layout", p)
    elif cmd == "gen":                             # one call at a time: the OpenRouter credit is shared
        for p in names or list(SHEETS):
            print(gen(p), flush=True)
    elif cmd == "faces":
        print(faces(), flush=True)
    elif cmd == "fit":
        fit(names or list(SHEETS))
        sheet_img()
    elif cmd == "fitfaces":
        fit_faces()
        sheet_img()
    elif cmd == "splitarm":
        splitarm()
        sheet_img()
    elif cmd == "underlay":                        # only the upper piece again (its solid sleeve underlay); the forearm
        splitarm(only_up=True)                     # piece and its drawn-on joint stay as they are
        sheet_img()
    elif cmd == "joint":
        joint()
        sheet_img()
    elif cmd == "trim":
        trim()
        sheet_img()
    elif cmd == "sheet":
        sheet_img()
    else:
        print(__doc__)
