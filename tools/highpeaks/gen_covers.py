"""High Peaks: the lobby art for engine.io - a 16:9 cover (3840x2160) and a 3:4 tile (3072x4096), each built from a
BACKGROUND and a FOREGROUND (owner, 2026-11-23: "make new 3x4 and 16x9 with foreground and background vibrant bright
colors"). That is also how the studio's Media Editor builds a tile: a bright background with no text, and one
transparent "key item" - a single main character - in the key focus area.

  background   the summit resort with nobody in it, loud and sunny: a sunburst sky, candy-bright peaks, the lodge, the
               lift, coins, leaves and snowflakes round the edges, the middle left calm for the character. One painted
               for each shape. NO text (owner rule from Power Outage, 2026-11-18: the lobby shows the name itself).
  foreground   the game's yeti, waist up, big enough to fill the focus box (a reviewer rejected a tile with two
               characters, and a small pre-shrunk foreground). Painted on flat magenta and cut out here.

usage:  python tools/highpeaks/gen_covers.py gen [bg_16x9|bg_3x4|fg_yeti ...]   paint (art/highpeaks/raw/cover_<name>[.vN].png)
        python tools/highpeaks/gen_covers.py build     -> media/bg_16x9.png, media/bg_3x4.png, media/fg_yeti.png (the
                                                          Media Editor's layers) and media/cover_16x9.png,
                                                          media/cover_3x4.png (+ .jpg): the two put together
The riders' covers of 2026-11-19 (a skier and a snowboarder) are in git history; the game's character is the yeti now.
"""
import concurrent.futures as cf, glob, json, os, sys
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orgen

ROOT = orgen.ROOT
RAW = orgen.RAW
MEDIA = os.path.join(ROOT, "media")
SCENE_REF = os.path.join(RAW, "layers_flat.png")                                   # the game's own summit scene
YETI_REF = os.path.join(ROOT, "art", "highpeaks", "yeti", "master", "yeti_master.png")
STYLE = ("Drawn in exactly the attached picture's flat 2D adult-animation sitcom cartoon style: thick clean black "
         "outlines, flat solid colours with simple hard-edged shadow shapes, no realistic lighting, no 3D rendering, no "
         "CGI, no airbrush, no photo texture. ")
NOTEXT = ("ABSOLUTELY NO text, NO letters, NO numbers, NO logos, NO words, NO signs with writing anywhere (any sign "
          "board is blank wood). ")
BG = ("The BACKGROUND plate of an online slot game's lobby art - scenery only: NO characters, NO people, NO animals, "
      "nobody in it. " + NOTEXT + STYLE +
      "Scene: the attached cartoon ski resort on a mountain summit on the brightest, sunniest day there ever was. A "
      "huge sunburst fills the sky: bold rays fanning out from behind the middle peak, alternating vivid sky blue and "
      "bright turquoise, with a warm yellow-white sun glow at their centre. Candy-bright snowy peaks in clean white with "
      "aqua and lilac-pink shadow shapes; rolling snow in white with pale turquoise shadows; snowy pine trees in fresh "
      "bright green; the cosy log lodge with its snowy roof and glowing warm yellow windows; the red chairlift running "
      "up the slope; a green flag on a pole. Scattered round the EDGES of the picture, big and bold: shiny gold coins, "
      "a few large purple coins with a gold rim and a white question mark (the only mark allowed), bright green "
      "cannabis leaves, white snowflakes, a few fat white cartoon clouds. The MIDDLE of the picture is kept calm and "
      "open - just sky rays and clean snow - because a character will be placed over it. Very saturated, very bright, "
      "happy colours: sky blue, turquoise, sunshine yellow, lime green, orange, purple, gold, snow white. Bright right "
      "out to every edge and corner: NO dark edges, NO vignette, NO night, NO black or navy areas, NO heavy shadow. "
      "Full-bleed, the picture runs off all four sides.")
FG = ("One cartoon character on a perfectly flat, plain, solid pure magenta background (#FF00FF) with nothing else in "
      "the picture: no scenery, no ground, no shadow on the background, no text, no border, no gradient - every "
      "background pixel the same magenta. The character is the yeti of the attached picture, the SAME character "
      "exactly - white shaggy fur, blue-grey face with a big dark blue nose, sleepy half-closed happy eyes, the orange "
      "knit beanie with a white pom-pom, purple ski goggles pushed up on the beanie, the lime-green puffer jacket open "
      "over his furry chest - " + STYLE.replace("the attached picture's", "that picture's") +
      "Shown from the WAIST UP, big, filling the picture: his head near the top, his body running off the BOTTOM edge "
      "of the picture (cut by the frame at the waist, no feet, no ground). A lively hero pose, leaning a little toward "
      "the viewer with a huge open-mouthed laugh: one arm thrown up high in a cheer with his fist in the air, the other "
      "hand holding his purple snowboard with yellow flames upright beside him so the top half of the board is in "
      "frame. Bold, bright, saturated colours; clean thick black outline all the way round him. No magenta or pink "
      "anywhere on the character.")
JOBS = {
    "bg_16x9": dict(prompt=BG + " Wide landscape composition: the lodge at the left, the chairlift at the right, the "
                    "peaks across the top, the open calm middle.", aspect_ratio="16:9", size="3840x2160", refs=[SCENE_REF]),
    "bg_3x4": dict(prompt=BG + " Tall portrait composition: the sunburst and the peaks in the top half, the lodge small "
                   "at one side, snow rolling down the bottom half, the open calm middle.", aspect_ratio="3:4",
                   size="2448x3264", refs=[SCENE_REF]),
    "fg_yeti": dict(prompt=FG, aspect_ratio="3:4", size="2448x3264", refs=[YETI_REF]),
}
SIZES = {"16x9": (3840, 2160), "3x4": (3072, 4096)}
# the yeti on each cover: his height as a share of the cover's, and where his middle and his bottom edge sit
PLACE = {"16x9": dict(h=.94, cx=.5, bottom=1.0), "3x4": dict(h=.74, cx=.5, bottom=1.0)}


def gen(name):
    j = dict(JOBS[name], name="cover_" + name)
    rec = orgen.generate(j)
    if rec.get("error") and j.get("size"):      # the model refused that size: let it pick one for the aspect
        j.pop("size")
        rec = orgen.generate(j)
    return rec


def latest(name):
    files = sorted(glob.glob(os.path.join(RAW, f"cover_{name}*.png")), key=os.path.getmtime)
    if not files:
        raise SystemExit(f"no art/highpeaks/raw/cover_{name}*.png - run `gen {name}` first")
    return files[-1]


def cover_fit(im, size):
    """Scale to cover `size` and crop the overhang off evenly (the model's frame is near the aspect, not always on it)."""
    W, H = size
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def key_figure(im):
    """A character painted on flat magenta -> RGBA. The scene's key (layers_install.key_magenta: "how magenta is it")
    would eat this character - his purple trousers, goggles and board are half-way to magenta - so this one goes by
    distance from the key colour, and only where the background really is: flat-magenta areas (a few stray pockets
    between an arm and the body included), plus a band of a few pixels round them where the ink's anti-aliased edge
    is un-mixed from the magenta it was blended with. Everything further in keeps alpha 1, whatever its colour."""
    from scipy import ndimage
    px = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    dist = np.sqrt(((px - np.array([1, 0, 1], np.float32)) ** 2).sum(-1))
    lab, n = ndimage.label(dist < .22)
    if n:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        ground = np.isin(lab, 1 + np.flatnonzero(sizes > px.shape[0] * px.shape[1] * 2e-5))   # not a speck inside him
    else:
        ground = np.zeros(dist.shape, bool)
    band = ndimage.binary_dilation(ground, iterations=5)
    a = np.where(ground, 0.0, np.where(band, np.clip((dist - .2) / .5, 0, 1), 1.0)).astype(np.float32)
    aa = np.maximum(a, .08)[..., None]
    col = np.clip((px - (1 - a[..., None]) * np.array([1, 0, 1], np.float32)) / aa, 0, 1)
    return Image.fromarray((np.dstack([col, a[..., None]]) * 255 + .5).astype(np.uint8), "RGBA")


def trim(im, pad=6):
    bb = im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    return im.crop((max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), bb[3]))   # the bottom: his own cut edge


def vivid(im, sat=1.12):
    """A touch more colour on a background (kept gentle: the paint is already loud)."""
    from PIL import ImageEnhance
    return ImageEnhance.Color(im).enhance(sat)


def compose(bg, fg, name):
    W, H = bg.size
    p = PLACE[name]
    h = round(H * p["h"])
    f = fg.resize((round(fg.width * h / fg.height), h), Image.LANCZOS)
    x, y = round(W * p["cx"] - f.width / 2), round(H * p["bottom"]) - h
    out = bg.convert("RGBA")
    # he is lifted off the scenery by a soft bright halo and a soft shadow under it - both from his own outline
    a = Image.new("L", (W, H), 0)
    a.paste(f.getchannel("A"), (x, y))
    glow = a.filter(ImageFilter.GaussianBlur(H * .022)).point(lambda v: min(255, int(v * 1.5)))
    out.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), (255, 255, 255)).split(), glow.point(lambda v: int(v * .7)))))
    shade = Image.new("L", (W, H), 0)
    shade.paste(f.getchannel("A"), (x + round(H * .008), y + round(H * .012)))
    shade = shade.filter(ImageFilter.GaussianBlur(H * .008))
    out.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), (20, 40, 110)).split(), shade.point(lambda v: int(v * .32)))))
    out.alpha_composite(f, (x, y))
    return out.convert("RGB")


def edge_report(im, name):
    """Reviewers reject dark edges: the mean brightness of the outer 4% frame, and of its darkest side."""
    g = np.asarray(im.convert("L")).astype(np.float32) / 255
    k = max(8, round(min(g.shape) * .04))
    sides = dict(top=g[:k].mean(), bottom=g[-k:].mean(), left=g[:, :k].mean(), right=g[:, -k:].mean())
    hsv = np.asarray(im.convert("HSV")).astype(np.float32) / 255
    return (f"{name}: {im.size[0]}x{im.size[1]} | mean brightness {g.mean():.2f}, saturation {hsv[..., 1].mean():.2f} | "
            f"edges " + ", ".join(f"{s} {v:.2f}" for s, v in sides.items()))


def build():
    os.makedirs(MEDIA, exist_ok=True)
    fg = trim(key_figure(Image.open(latest("fg_yeti"))))
    fg.save(os.path.join(MEDIA, "fg_yeti.png"), optimize=True)
    a = np.asarray(fg.getchannel("A"))
    print(f"fg_yeti: {fg.size[0]}x{fg.size[1]} | {100 * (a > 250).mean():.0f}% solid, {100 * (a < 5).mean():.0f}% clear, "
          f"{100 * ((a >= 5) & (a <= 250)).mean():.1f}% edge")
    for name, size in SIZES.items():
        bg = vivid(cover_fit(Image.open(latest("bg_" + name)).convert("RGB"), size))
        bg.save(os.path.join(MEDIA, f"bg_{name}.png"), optimize=True)
        print(edge_report(bg, "bg_" + name))
        im = compose(bg, fg, name)
        png = os.path.join(MEDIA, f"cover_{name}.png")
        im.save(png, optimize=True)
        im.save(png[:-4] + ".jpg", quality=92, optimize=True)
        print(edge_report(im, "cover_" + name), f"| {os.path.getsize(png) // 1024} KB")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "gen":
        names = args or list(JOBS)
        with cf.ThreadPoolExecutor(max_workers=len(names)) as ex:
            for rec in ex.map(gen, names):
                print(json.dumps(rec), flush=True)
    elif cmd == "build":
        build()
