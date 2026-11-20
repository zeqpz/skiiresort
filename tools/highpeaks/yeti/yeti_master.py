"""High Peaks: the yeti's master drawing (the whole figure, posed for a cut-out rig), by the image model.

  python tools/highpeaks/yeti/yeti_master.py [n]     -> art/highpeaks/yeti/master/yeti_master[.vN].png (n variants)

Style refs: the game's own skier and snowboarder sprites (flat adult-animation sitcom cartoon). The figure is ORIGINAL:
no existing yeti / abominable snowman character, no other characters, no text."""
import concurrent.futures as cf, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import orgen

ROOT = orgen.ROOT
orgen.RAW = os.path.join(ROOT, "art", "highpeaks", "yeti", "master")
REFS = [os.path.join(ROOT, "art", "highpeaks", "raw", n) for n in ("spr_boarder.png", "spr_skier.png")]

CHAR = (
    "an ORIGINAL cartoon yeti beast: big, broad and pear-shaped with short sturdy legs, covered in shaggy white fur "
    "drawn as simple scalloped tufts with pale icy-blue shadow shapes; a big round goofy friendly face of pale "
    "blue-grey skin, a wide happy stoned grin showing two small blunt lower fangs, heavy-lidded relaxed eyes, a big "
    "round dark-blue nose, a tuft of fur on each cheek. He wears ski gear: an UNZIPPED bright lime-green puffer ski "
    "jacket (open at the front so his furry white chest and belly show), purple baggy ski pants, chunky orange "
    "snowboard boots, a red-orange knit beanie with a white pom-pom, and ski goggles with a mirrored purple lens "
    "pushed up onto the front of the beanie. His hands are big furry four-fingered mitts with pale blue-grey palms.")
POSE = (
    "POSE (it will be cut into pieces and animated as a puppet, so keep the limbs clear of the body): standing on a "
    "small rounded mound of snow, facing the viewer, turned just slightly toward the viewer's left. Feet planted a "
    "little wider than his hips, both boots fully visible, toes pointing slightly outward. The arm on the viewer's "
    "RIGHT is bent at the elbow, held out from his side, the hand raised to about his shoulder height holding a lit "
    "joint between two fingers (a thin white rolled joint with a glowing orange tip and a thin grey curl of smoke). "
    "The arm on the viewer's LEFT hangs relaxed and a little away from his body, its hand resting on the top end of a "
    "snowboard that stands upright, planted tail-down in the snow mound just beside him on the viewer's left (a bright "
    "yellow snowboard with purple flame graphics, seen from the front, its nose up near his waist height). There is "
    "a clear gap of empty background between each arm and his body and between his legs.")
STYLE = (
    "STYLE - match the attached pictures exactly: a flat 2D adult-animation sitcom cartoon, thick clean black ink "
    "outlines of even weight, flat solid colour fills with one simple hard-edged darker shade, no gradients, no "
    "airbrush, no glow haze, no texture, no 3D rendering, no CGI, crisp vector-quality linework at high resolution. "
    "Full body, the whole figure, the snow mound and the snowboard inside the frame with a margin, centred, on a "
    "fully TRANSPARENT background. Only this one character - no other characters, no text, no logos, no letters.")


def job(i):
    return orgen.generate(dict(name="yeti_master", prompt="Draw " + CHAR + " " + POSE + " " + STYLE,
                               aspect_ratio="2:3", background="transparent", refs=REFS))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with cf.ThreadPoolExecutor(n) as ex:
        for rec in ex.map(job, range(n)):
            print(json.dumps(rec), flush=True)
