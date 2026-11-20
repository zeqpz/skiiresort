"""High Peaks: the lobby covers for engine.io's Media page - 16:9 (3840x2160) and 3:4 (3072x4096).

The image model paints the key art from the game's own flat-cartoon art (the lodge plate, the skier, the snowboarder,
the jackpot ? coin). NO text at all - no title, no letters (owner rule from Power Outage, 2026-11-18: the lobby shows
the name itself) - and no 3D characters (owner, 2026-11-19: the game is flat adult-animation cartoon).

usage:  python tools/highpeaks/gen_covers.py gen [16x9|3x4 ...]   paint (art/highpeaks/raw/cover_<aspect>[.vN].png)
        python tools/highpeaks/gen_covers.py build [file16x9 file3x4]   -> media/cover_16x9.png, media/cover_3x4.png (+ .jpg)
"""
import concurrent.futures as cf, glob, json, os, sys
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orgen

ROOT = orgen.ROOT
RAW = orgen.RAW
MEDIA = os.path.join(ROOT, "media")
REFS = [os.path.join(RAW, n) for n in ("plate_base2.png", "spr_skier.png", "spr_boarder.png", "sym_JP.png")]
SCENE = (
    "Key art for an online slot game's lobby cover. ABSOLUTELY NO text, NO letters, NO numbers, NO logos, NO words, NO "
    "signs with writing anywhere in the picture (the lodge's sign board is blank wood). Original characters only - the "
    "two in the attached pictures: the goofy skier in the orange puffer jacket, purple goggles and striped bobble hat, "
    "and the laid-back snowboarder in the purple jacket and green beanie - no characters from any existing TV show, "
    "film or game, no real brands. Drawn in exactly the attached pictures' flat 2D adult-animation sitcom cartoon "
    "style: thick clean black outlines, flat solid colours with simple hard-edged shadow shapes, no realistic lighting, "
    "no 3D rendering, no CGI, no airbrush, no glow haze. Scene: a sunny cartoon ski resort high in snowy mountains, "
    "the attached background: the big log lodge with its snowy roof and stone chimney, snowy pine trees, the red "
    "chairlift, the groomed run. The skier and the snowboarder burst toward the viewer mid-air off a snow kicker, "
    "grinning wildly, big sprays of powder snow behind them. Around them fly shiny gold coins, a few big purple coins "
    "with a gold rim marked with a white question mark (the attached coin - the only mark allowed), small green "
    "cannabis leaves and snowflakes. Bright blue sky with a couple of fat white cartoon clouds. Fun, high energy, bold "
    "shapes that read at thumbnail size, punchy colours: sky blue, snow white, orange, purple, lime green, gold.")
JOBS = {
    "16x9": dict(prompt=SCENE + " Wide landscape composition: the two riders big in the centre and right of centre, the "
                 "lodge and the chairlift behind them, the peaks across the top.", aspect_ratio="16:9", size=(3840, 2160)),
    "3x4": dict(prompt=SCENE + " Tall portrait composition: the snowboarder big in the middle flying over the camera, "
                "the skier just below and to the left, the lodge and the peaks behind and above them.", aspect_ratio="3:4",
                size=(3072, 4096)),
}


def gen(name):
    j = JOBS[name]
    return orgen.generate(dict(name="cover_" + name, prompt=j["prompt"], aspect_ratio=j["aspect_ratio"], refs=REFS))


def latest(name):
    files = sorted(glob.glob(os.path.join(RAW, f"cover_{name}*.png")), key=os.path.getmtime)
    return files[-1] if files else None


def esrgan_x4(im):
    """Real-ESRGAN x4 (the anime model: flat cartoon colour and clean ink lines) when realesrgan-ncnn-vulkan is here -
    REALESRGAN=<exe>, or ../ClaudeRoblox/.tools/realesrgan beside the repo (the Windows PC). Without it: plain resize."""
    import subprocess, tempfile
    exe = os.environ.get("REALESRGAN") or os.path.join(os.path.dirname(ROOT), "ClaudeRoblox", ".tools", "realesrgan",
                                                       "realesrgan-ncnn-vulkan.exe")
    if not os.path.exists(exe):
        return im
    with tempfile.TemporaryDirectory() as td:
        a, b = os.path.join(td, "in.png"), os.path.join(td, "out.png")
        im.save(a)
        r = subprocess.run([exe, "-i", a, "-o", b, "-n", "realesrgan-x4plus-anime", "-s", "4", "-f", "png"],
                           cwd=os.path.dirname(exe), capture_output=True, text=True)
        if r.returncode or not os.path.exists(b):
            raise RuntimeError("Real-ESRGAN failed: " + r.stderr[-300:])
        return Image.open(b).convert("RGB")


def build(name, src=None):
    src = src or latest(name)
    W, H = JOBS[name]["size"]
    im = esrgan_x4(Image.open(src).convert("RGB"))
    # cover-fit to the exact size (the model's frame is close to the aspect, not always on it), then a light sharpen
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H)).filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    os.makedirs(MEDIA, exist_ok=True)
    png = os.path.join(MEDIA, f"cover_{name}.png")
    im.save(png, optimize=True)
    im.save(png[:-4] + ".jpg", quality=92, optimize=True)
    return f"{os.path.relpath(src, ROOT)} -> media/cover_{name}.png ({W}x{H}, {os.path.getsize(png) // 1024} KB)"


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "gen":
        names = args or list(JOBS)
        with cf.ThreadPoolExecutor(max_workers=len(names)) as ex:
            for rec in ex.map(gen, names):
                print(json.dumps(rec), flush=True)
    elif cmd == "build":
        srcs = args or [None, None]
        for name, src in zip(JOBS, srcs):
            print(build(name, src))
