"""High Peaks yeti QA: contact sheets of the Blender stills (rig_build/renders/<clip>/NNNN.png) on a flat colour, each
frame labelled, so a clip's poses can be judged side by side.
  python tools/highpeaks/yeti/qa_sheet.py [clip ...] [--cols 6] [--sub renders] [--frames 0,6,12]
-> art/highpeaks/yeti/rig_build/<sub>/sheets/<clip>_<k>.png"""
import glob, os, sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BUILD = os.path.join(ROOT, "art", "highpeaks", "yeti", "rig_build")


def main():
    args = sys.argv[1:]
    opt = {"--cols": "6", "--sub": "renders", "--frames": "", "--rows": "2", "--bg": "58,96,150"}
    clips = []
    while args:
        a = args.pop(0)
        if a in opt:
            opt[a] = args.pop(0)
        else:
            clips.append(a)
    ren = os.path.join(BUILD, opt["--sub"])
    cols, rows = int(opt["--cols"]), int(opt["--rows"])
    bg = tuple(int(v) for v in opt["--bg"].split(",")) + (255,)
    out = os.path.join(ren, "sheets")
    os.makedirs(out, exist_ok=True)
    for clip in clips or sorted(d for d in os.listdir(ren) if os.path.isdir(os.path.join(ren, d)) and d not in ("sheets", "zoom")):
        files = sorted(f for f in glob.glob(os.path.join(ren, clip, "*.png")) if os.path.basename(f)[:4].isdigit())
        if opt["--frames"]:
            want = {int(v) for v in opt["--frames"].split(",")}
            files = [f for f in files if int(os.path.basename(f)[:4]) in want]
        for old in glob.glob(os.path.join(out, clip + "_*.png")):
            os.remove(old)
        per = cols * rows
        for k in range(0, len(files), per):
            ims = [Image.open(f).convert("RGBA") for f in files[k:k + per]]
            w, h = ims[0].size
            r = (len(ims) + cols - 1) // cols
            sheet = Image.new("RGBA", (cols * w, r * h), bg)
            dr = ImageDraw.Draw(sheet)
            for j, im in enumerate(ims):
                x, y = (j % cols) * w, (j // cols) * h
                sheet.alpha_composite(im, (x, y))
                dr.text((x + 6, y + 4), f"{clip} {int(os.path.basename(files[k + j])[:4])}", fill=(255, 255, 255, 255))
                dr.line([(x, y), (x, y + h)], fill=(0, 0, 0, 60))
            path = os.path.join(out, f"{clip}_{k // per}.png")
            sheet.convert("RGB").save(path)
            print(path)


if __name__ == "__main__":
    main()
