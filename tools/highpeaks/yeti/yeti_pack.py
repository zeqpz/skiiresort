"""Pack the yeti's live rig for the game: art/highpeaks/yeti/rig_build/rig/ (yeti_rig.py export) ->
frontend/assets/yeti/rig/:
  rig.json         bones, parts (mesh offsets into geo.bin), faces, fx kinds, clips (face track, fx draws, offset
                   into clips.bin, loop / hold) and, per density, its atlas pages and where each picture sits
  geo.bin          every part's mesh
  clips.bin        every clip's bone transforms back to back (float32: frames x bones x 6)
  d<NNN>/p<k>.webp the atlas pages per density (texels per art px), parts + faces + fx sprites, shelf-packed with a
                   gutter so mipmaps never bleed
The game picks the smallest density that draws the standing figure at a texel per screen pixel.
usage: python tools/highpeaks/yeti/yeti_pack.py"""
import json, os, shutil

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SRC = os.path.join(ROOT, "art", "highpeaks", "yeti", "rig_build", "rig")
PARTS = os.path.join(ROOT, "art", "highpeaks", "yeti", "parts")
FX = os.path.join(ROOT, "art", "highpeaks", "yeti", "fx")
DST = os.path.join(ROOT, "frontend", "assets", "yeti", "rig")
DENSITIES = [.375, .5, .75, 1.0]
FX_GROW = 1.5                               # a sprite is packed at its size x the most it grows
GUTTER = 6


def shelf_pack(rects, width):
    out, x, y, shelf = {}, 0, 0, 0
    for key, w, h in sorted(rects, key=lambda r: -r[2]):
        if x + w > width:
            x, y, shelf = 0, y + shelf + GUTTER, 0
        out[key] = (x, y)
        x += w + GUTTER
        shelf = max(shelf, h)
    return out, y + shelf


def pages_for(rects):
    left = list(rects)
    pages = []
    while left:
        for size in (1024, 2048, 4096):
            pos, h = shelf_pack(left, size)
            if h <= size:
                pages.append((size, 1 << max(0, (h - 1)).bit_length(), pos))
                left = []
                break
        else:
            pos, h = shelf_pack(left, 4096)
            hs = dict((r[0], r[2]) for r in left)
            keep = {k: p for k, p in pos.items() if p[1] + hs[k] <= 4096}
            pages.append((4096, 4096, keep))
            left = [r for r in left if r[0] not in keep]
    return pages


def main():
    rig = json.load(open(os.path.join(SRC, "rig.json")))
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)
    shutil.copyfile(os.path.join(SRC, "geo.bin"), os.path.join(DST, "geo.bin"))
    blob = bytearray()
    for c, C in rig["clips"].items():
        C["o"] = len(blob)
        blob.extend(open(os.path.join(SRC, f"{c}.bin"), "rb").read())
        assert len(blob) - C["o"] == C["frames"] * len(rig["bones"]) * 24, c
    open(os.path.join(DST, "clips.bin"), "wb").write(bytes(blob))
    rig["geo"], rig["clips_bin"] = "geo.bin", "clips.bin"
    srcs = {}
    for p in rig["parts"]:
        srcs[p["tex"]] = (os.path.join(PARTS, p["tex"] + ".png"), p["box"][2], p["box"][3])
    for k in rig["fx"] + rig.get("live_fx", []):
        s = rig["fx_px"][k] * FX_GROW
        srcs["fx_" + k] = (os.path.join(FX, k + ".png"), s, s)
    ims = {k: Image.open(path).convert("RGBA") for k, (path, _, _) in srcs.items()}
    rig["densities"] = []
    total_all = 0
    for d in DENSITIES:
        tag = f"d{int(round(d * 1000)):04d}"
        os.makedirs(os.path.join(DST, tag))
        sized = {}
        for k, (path, w, h) in srcs.items():
            im = ims[k]
            tw, th = max(2, round(w * d)), max(2, round(h * d))
            if k.startswith("fx_"):
                s = min(tw / im.width, th / im.height, 1.0)
                tw, th = max(2, round(im.width * s)), max(2, round(im.height * s))
            sized[k] = im.resize((tw, th), Image.LANCZOS)
        pages = pages_for([(k, im.width, im.height) for k, im in sized.items()])
        frames, files, total = {}, [], 0
        for pi, (pw, ph, pos) in enumerate(pages):
            page = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            for k, (x, y) in pos.items():
                page.paste(sized[k], (x, y))
                frames[k] = [pi, x, y, sized[k].width, sized[k].height]
            name = f"{tag}/p{pi}.webp"
            page.save(os.path.join(DST, name), "WEBP", quality=88, alpha_quality=100, method=6)
            files.append(name)
            total += os.path.getsize(os.path.join(DST, name))
        rig["densities"].append({"d": d, "pages": files, "frames": frames})
        total_all += total
        print(tag, [f"{pw}x{ph}" for pw, ph, _ in pages], f"{total / 1e6:.2f} MB", flush=True)
    json.dump(rig, open(os.path.join(DST, "rig.json"), "w"), separators=(",", ":"))
    verts = sum(p["verts"] for p in rig["parts"])
    sz = lambda f: os.path.getsize(os.path.join(DST, f))
    print("rig.json", sz("rig.json"), "geo", sz("geo.bin"), "clips", len(blob), "verts", verts, "bones", len(rig["bones"]),
          f"atlases {total_all / 1e6:.2f} MB (one density is loaded)")


if __name__ == "__main__":
    main()
