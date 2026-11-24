"""High Peaks - the layered scene (owner, 2026-11-23: "redo the background, we want a foreground, midground and
background and make them dynamic and animated", and "blend the yeti with the background").

    python art/highpeaks/jobs/layers_jobs.py            -> art/highpeaks/jobs/layers.json
    python tools/highpeaks/orgen.py art/highpeaks/jobs/layers.json
    python tools/highpeaks/layers_install.py            -> frontend/assets/scene/layers/

The same mountain-top world as the peak pass's plate (art/highpeaks/raw/peak_plate.png, the reference for every job),
drawn as separate depth layers so they can slide against each other and each have a life of its own:

  layer_back    sky and the sea of far peaks, the cloud sea and the valley village - no summit, no sky clouds
                (the clouds are sprites that drift)
  layer_mid     the summit we stand on: its snow floor, the lift hut, the trail sign, the lift's cable and towers
                (NO chairs: they ride the cable as sprites), the cairn and its bare flag pole (the flag is a sprite
                that waves) - on a flat magenta ground that layers_install.py keys out (the image model gives 4K only
                for an opaque picture)
  fg_drift      a close snow drift with rocks for the bottom corners of the screen (mirrored for the other side)
  fg_bough      a snow-laden pine bough reaching in from a top corner
  spr_pine      a snowy pine (they stand behind the hut and sway)
  spr_flag      the summit flag's cloth
  yeti_drift    the low drift of snow the yeti's boots and board sink into (in place of his outlined mound)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = open(os.path.join(HERE, 'style.txt'), encoding='utf-8').read().strip()
DETAIL = (' Crisp clean ink lines, small texture lines in the snow, rock and wood, flat cartoon colours, readable at a '
          'glance. Exactly the reference picture\'s drawing style, line weight and colours.')
REF = ['art/highpeaks/raw/peak_plate.png']
NOPE = ' No people, no animals, no characters, no text, no letters, no numbers, no logos.'
KEY = ('Everything that is not part of the described objects is one perfectly flat, even, pure magenta colour '
       '(#FF00FF) with no shading, no gradient, no texture and no shadow on it - it will be removed later. Nothing in '
       'the drawing itself is magenta, pink or purple.')

JOBS = [
    dict(name='layer_back', aspect_ratio='16:9', size='3840x2160', refs=REF, prompt=(
        'Slot-game background, the FAR layer only, full-bleed wide landscape. A view from very high up, looking out '
        'over a sea of snowy mountain peaks in many layers fading paler and bluer into the distance, exactly like the '
        'distant mountains of the reference picture. Fluffy white clouds float between the peaks, and a tiny ski '
        'village with pine woods and a frozen blue lake lies far down in a valley a little right of the centre. The '
        'top third of the picture is a clear bright blue sky that is completely EMPTY - no clouds in the sky at all, '
        'no sun - a flat bright blue with one slightly paler flat band just above the peaks. The mountains, cloud sea '
        'and valley carry on all the way DOWN to the very bottom edge of the picture: the bottom third is more snowy '
        'ridges and banks of cloud seen from above. There is NO foreground at all: no summit ground, no snow floor, '
        'no hut, no sign post, no chairlift, no trees in front, no flag, no rocks in front.' + NOPE + DETAIL)),
    dict(name='layer_mid', aspect_ratio='16:9', size='3840x2160', refs=REF, prompt=(
        'One layer of a slot-game background, drawn exactly like the summit foreground of the reference picture and '
        'in the same places, with everything behind it replaced by flat magenta. The layer: the broad, flat snowy TOP '
        'OF THE MOUNTAIN we stand on, filling the whole bottom third of the picture from edge to edge - deep clean '
        'snow with soft blue-shaded drifts and a few grey rocks poking through, its far edge a gently bumpy ridge line '
        'about two thirds of the way down the picture, the rocky ridge falling away at the far left and far right '
        'edges. Standing on it at the LEFT: a wooden trail sign post with a green circle plate, a blue square plate '
        'and a black diamond plate (no writing), and a small wooden chairlift top-station hut with a thick snow roof, '
        'a warm yellow window, a door, and a big red horizontal lift wheel under its eave; from the wheel a thin dark '
        'lift cable runs out to the right and DOWN, over two grey steel lift towers that step down and away below the '
        'ridge. The cable is EMPTY: no chairs, no gondolas, nothing hanging on it. Standing on it at the far RIGHT: a '
        'little cairn of grey stones with snow on them and a tall bare wooden flag POLE with a small gold ball on top '
        '- NO flag, no cloth on the pole. Between them, right of the centre, a wide open EMPTY patch of flat snow. '
        'There are NO trees and NO pine trees anywhere, NO clouds, NO sky and NO distant mountains: ' + KEY + NOPE + DETAIL)),
    dict(name='fg_drift', aspect_ratio='1:1', background='transparent', refs=REF, prompt=(
        'A single foreground object for a slot-game scene on a fully transparent background, nothing else: a big, '
        'close-up rounded SNOW DRIFT seen from the side, the kind that sits in the bottom-left corner of the screen '
        'very near the camera. It is tallest at its left edge (about two thirds of the picture\'s height) and slopes '
        'down in soft lumpy humps to nothing at the bottom-right corner. Deep clean snow with flat pale-blue shadow '
        'shapes and a few curved texture lines, two chunky dark grey rocks with thick snow caps half buried in it, and '
        'a few small tufts of dry grass poking out. A thick black outline along its top edge only; it runs off the '
        'left and bottom edges of the picture. It is a little deeper and bluer in tone than the snow in the reference '
        '(it is in the foreground shade). Everything else fully transparent.' + NOPE + DETAIL)),
    dict(name='fg_bough', aspect_ratio='1:1', background='transparent', refs=REF, prompt=(
        'A single foreground object for a slot-game scene on a fully transparent background, nothing else: the end of '
        'a big PINE TREE BOUGH reaching in from the top-left corner of the picture toward the middle, very near the '
        'camera: two or three dark green needle branches fanned out and drooping, each loaded with thick lumps of '
        'white snow with pale-blue shadow shapes, a couple of small brown pine cones, a few icicles hanging from the '
        'snow. The same flat cartoon pine drawing as the snowy pine trees in the reference picture. The branch starts '
        'off the top-left corner; nothing touches the right or bottom edges. Everything else fully transparent.' + NOPE + DETAIL)),
    dict(name='spr_pine', aspect_ratio='2:3', background='transparent', refs=REF, prompt=(
        'A single object on a fully transparent background, nothing else: one tall snowy cartoon PINE TREE exactly '
        'like the pine trees in the reference picture - dark green tiers of needles, every tier loaded with thick '
        'white snow with pale-blue shadow shapes, a pointed snowy top, a short brown trunk at the bottom. The whole '
        'tree, centred, from its tip to the bottom of its trunk, standing straight up. No ground, no snow floor, no '
        'shadow under it. Everything else fully transparent.' + NOPE + DETAIL)),
    dict(name='spr_flag', aspect_ratio='1:1', background='transparent', refs=REF, prompt=(
        'A single object on a fully transparent background, nothing else: the CLOTH of a small rectangular flag, '
        'exactly like the green flag in the reference picture: bright green cloth with a darker green hem shape, a '
        'big lime-green cannabis leaf with a yellow-green outline in its middle, thick black outline. The cloth hangs '
        'almost flat, wider than tall (about 3 wide to 2 tall), its left edge perfectly straight and vertical (that '
        'edge is tied to a pole that is NOT drawn), its right edge with a small swallow-tail notch. NO pole, no rope, '
        'no ball. It fills most of the picture. Everything else fully transparent.' + NOPE + DETAIL)),
    dict(name='yeti_drift', aspect_ratio='16:9', background='transparent', refs=REF, prompt=(
        'A single object on a fully transparent background, nothing else: a long, LOW, wide drift of snow seen from '
        'the side, the kind that piles up around someone\'s boots - about six times as wide as it is tall, a soft '
        'lumpy top edge with three or four gentle humps, highest in the middle and tapering away to thin points at '
        'its left and right ends. Clean white snow exactly like the snow floor of the reference picture, with flat '
        'pale-blue shadow shapes and a few short curved texture lines. A thick black outline along its TOP edge only: '
        'its bottom edge has NO outline - it is perfectly flat and straight and simply ends, so it can sit on a snow '
        'floor of the same colour. Centred, with clear space all round. Everything else fully transparent.' + NOPE + DETAIL)),
]
for j in JOBS:
    j['prompt'] += '\n\n' + STYLE
json.dump(JOBS, open(os.path.join(HERE, 'layers.json'), 'w'), indent=1)
print(len(JOBS), 'jobs ->', os.path.join(HERE, 'layers.json'))
