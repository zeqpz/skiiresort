"""High Peaks yeti: the little effect sprites his clips throw (drawn here, flat cartoon, no model call):
smoke (a grey puff from the joint and his exhale), ember (the joint's glowing tip), spark (a yellow 4-point star),
snowpuff (snow kicked up when he lands), sweat (a bead on his brow while he waits for the last FS).

  python tools/highpeaks/yeti/yeti_fx.py   -> art/highpeaks/yeti/fx/<kind>.png"""
import math, os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(ROOT, "art", "highpeaks", "yeti", "fx")
SS = 4                                            # drawn this many times bigger, then averaged down


def canvas(size):
    return Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))


def done(im, size, name):
    im = im.resize((size, size), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    im.save(os.path.join(OUT, name + ".png"))
    print(name, im.size)


def blob(circles, size, fill, shade, ink, line):
    """A cartoon cloud: circles unioned, an ink outline round the union, a shade shape along its lower edge."""
    S = size * SS
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    for cx, cy, r in circles:
        d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=255)
    import numpy as np
    from scipy import ndimage
    far = ndimage.distance_transform_edt(np.asarray(mask) < 128)
    grow = Image.fromarray((np.clip(line * S + .5 - far, 0, 1) * 255).astype(np.uint8), "L")   # the ink: line x size wide
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    im.paste(Image.new("RGBA", (S, S), ink), (0, 0), grow)
    im.paste(Image.new("RGBA", (S, S), fill), (0, 0), mask)
    sh = Image.new("L", (S, S), 0)
    ds = ImageDraw.Draw(sh)
    for cx, cy, r in circles:                     # the shade: each circle's lower part, inside the cloud
        ds.ellipse([(cx - r * .9) * S, (cy - r * .25) * S, (cx + r * .9) * S, (cy + r * 1.05) * S], fill=255)
    hollow = Image.new("L", (S, S), 0)
    dh = ImageDraw.Draw(hollow)
    for cx, cy, r in circles:
        dh.ellipse([(cx - r * .95) * S, (cy - r * 1.1) * S, (cx + r * .7) * S, (cy + r * .55) * S], fill=255)
    from PIL import ImageChops
    sh = ImageChops.multiply(ImageChops.subtract(sh, hollow), mask)
    im.paste(Image.new("RGBA", (S, S), shade), (0, 0), sh)
    return im


def smoke():
    c = [(.5, .58, .22), (.33, .6, .16), (.67, .6, .17), (.42, .42, .17), (.6, .42, .15), (.5, .7, .14)]
    done(blob(c, 256, (236, 241, 247, 255), (196, 206, 220, 255), (92, 100, 116, 255), .018), 256, "smoke")


def snowpuff():
    c = [(.5, .6, .2), (.3, .64, .15), (.7, .64, .15), (.4, .45, .15), (.62, .46, .14), (.18, .7, .09), (.82, .7, .09)]
    done(blob(c, 256, (255, 255, 255, 255), (196, 222, 255, 255), (20, 24, 40, 255), .02), 256, "snowpuff")


def ember():
    S = 128 * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = im.load()
    for y in range(S):
        for x in range(S):
            r = math.hypot(x - S / 2, y - S / 2) / (S / 2)
            if r >= 1:
                continue
            core = max(0.0, 1 - r / .28)
            glow = max(0.0, 1 - r) ** 2
            a = min(1.0, core + .75 * glow)
            col = (255, int(150 + 105 * core), int(40 + 170 * core))
            px[x, y] = col + (int(255 * a),)
    done(im, 128, "ember")


def spark():
    S = 128 * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for k in range(8):
        a = math.pi / 4 * k - math.pi / 2
        r = .46 if k % 2 == 0 else .14
        pts.append((S / 2 + r * S * math.cos(a), S / 2 + r * S * math.sin(a)))
    d.polygon(pts, fill=(20, 20, 30, 255))
    inner = [(S / 2 + (x - S / 2) * .8, S / 2 + (y - S / 2) * .8) for x, y in pts]
    d.polygon(inner, fill=(255, 225, 77, 255))
    hl = [(S / 2 + (x - S / 2) * .38, S / 2 + (y - S / 2) * .38 - S * .03) for x, y in pts]
    d.polygon(hl, fill=(255, 250, 210, 255))
    done(im, 128, "spark")


def sweat():
    S = 96 * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def drop(k, col):
        cx, cy, r = S * .5, S * .66, S * .21 * k
        top = (cx, cy - r * 2.3)
        d.polygon([top, (cx - r * .93, cy - r * .35), (cx + r * .93, cy - r * .35)], fill=col)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    drop(1.18, (27, 58, 102, 255))
    drop(1.0, (124, 200, 255, 255))
    d.ellipse([S * .4, S * .6, S * .48, S * .7], fill=(235, 248, 255, 255))
    done(im, 96, "sweat")


if __name__ == "__main__":
    smoke(); snowpuff(); ember(); spark(); sweat()
