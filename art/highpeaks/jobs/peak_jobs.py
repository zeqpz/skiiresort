"""High Peaks - the mountain-top pass (owner, 2026-11-19): "better artwork, higher quality / slightly more detailed, the
background on top of a mountain, keep the same outline for the board but redo it with an area for the HIGH PEAKS
logo", and "redo all the win artwork and make it fit the theme".

    python art/highpeaks/jobs/peak_jobs.py plate|frames|win|bonus   -> art/highpeaks/jobs/peak_<what>.json
    python tools/highpeaks/orgen.py art/highpeaks/jobs/peak_<what>.json

No people, no characters in the plates (the yeti is a rig of his own and stands on the summit's empty right patch).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = open(os.path.join(HERE, 'style.txt'), encoding='utf-8').read().strip()
DETAIL = (' Higher quality and a little more detailed than before: crisp clean ink lines, more small texture lines in the '
          'snow, rock and wood, more depth layers - but still flat cartoon colours, readable at a glance.')

SUMMIT = (
    'Slot-game background scene, full-bleed wide landscape, drawn in exactly the reference picture\'s flat cartoon style. '
    'We are standing ON THE VERY TOP OF A HUGE SNOWY MOUNTAIN. The foreground is the summit\'s broad, flat snowy top, '
    'spread across the whole bottom third of the picture: deep clean snow with soft blue-shaded drifts, a few grey rocks '
    'poking through, the rocky snowy ridge falling away steeply at the far left and far right edges. Behind and FAR BELOW '
    'us: a sea of other snowy mountain peaks in layers fading into the distance, fluffy white clouds floating between the '
    'peaks BELOW the summit, a tiny ski village far down in a valley. Above: a bright blue sky with a few fat white '
    'cartoon clouds high up. LEFT part of the summit: a wooden trail sign post with green circle, blue square and black '
    'diamond plates (no writing), a small wooden chairlift top-station hut with a thick snow roof and the end of a red '
    'chairlift cable, two snowy pine trees. RIGHT part of the summit: a wide OPEN, EMPTY patch of flat snow (a character '
    'will stand there later - keep it clear), and behind it at the far right a summit flag pole with a small green flag '
    'with a cannabis leaf on it, and a little cairn of stones. CENTRE: keep the middle simple - sky, distant peaks and the '
    'snowy summit floor - the slot board will cover it. No people, no animals, no characters, no text, no letters, no '
    'numbers, no logos, no signs with writing anywhere.')

MOODS = {
    'powder': 'FRESH POWDER: a soft pink-and-lavender sky, heavy fluffy snow falling, extra-deep fresh powder piled '
              'high on every roof, rock, tree and sign, sparkling snow crystals in the air.',
    'night': 'BLACK DIAMOND night: a deep navy starry sky with a big bright moon and swirling green-and-purple northern '
             'lights over the peaks, the hut\'s window glowing warm, a lantern pooling light on the snow, the black '
             'diamond plate on the trail sign glowing.',
    'avalanche': 'AVALANCHE: a dramatic orange-and-purple sunset sky, a huge cartoon avalanche of snow thundering down '
                 'the neighbouring big peak in the background with cartoon lightning bolts; the summit we stand on is '
                 'safe and calm.',
}

FRAME = (
    'Redraw the reference picture - a slot-game board frame made of chunky cartoon logs on a fully transparent '
    'background - keeping EXACTLY the same frame outline in the same place and at the same size: the same rectangle '
    'and proportions, the same thin side logs, the same round log ends at the four corners, the same snow along the '
    'top log, and the same completely EMPTY, fully transparent inside (nothing at all drawn inside the frame). Make it '
    'higher quality and a little more detailed: bark texture lines and knots in the wood, growth rings on the log ends, '
    'the snow on the top log deeper with soft blue shading and a few sparkles, a few more icicles, a small green '
    'cannabis leaf and a pinecone with pine sprigs in the top corners. NEW: centred on the top log, in the empty space '
    'above it, a big wide wooden SIGN BOARD made of horizontal planks with a thick snow cap on its top edge and a little '
    'snow on its ends, standing on the top log on two short wooden posts. The sign board\'s face is plain light wood '
    'and completely BLANK - no text, no letters, no logo, no picture on it (a logo goes on it later). The sign is about '
    '{w} of the frame\'s width, about three times as wide as it is tall, and it never reaches down into the inside of '
    'the frame. Everything outside the frame and the sign is fully transparent.')

WIN = (
    'Slot-game win title lettering on a fully transparent background, nothing else: the words "{text}" on one line in '
    'huge chunky rounded bold cartoon letters in exactly the attached HIGH PEAKS logo\'s lettering style - letters made '
    'of {ink}, a thick white snow cap dripping over the top of every letter with tiny icicles, a thick even black '
    'outline, a flat {drop} drop extrusion under the letters, {extra}. The lettering fills the picture\'s width with a '
    'small margin. No background, no plate, no banner, no other words.')
TIERS = {
    'big_win': ('BIG WIN', 'bright icy sky-blue ice with a lighter blue highlight', 'deep navy blue', 'a few small white sparkles'),
    'mega_win': ('MEGA WIN', 'bright lime-green ice with a lighter green highlight', 'deep forest green',
                 'a few small white sparkles and two tiny green cannabis leaves tucked at the ends'),
    'epic_win': ('EPIC WIN', 'glowing violet-and-magenta aurora ice with a pale lilac highlight', 'deep purple',
                 'small stars and northern-light streaks around it'),
    'total_win': ('TOTAL WIN', 'shiny warm gold with a pale yellow highlight', 'deep orange-brown',
                  'a few small white sparkles'),
}

SPLASH = (
    'A bright burst splash for behind a slot-game win title, on a fully transparent background, nothing else: a wide '
    'explosion of white powder snow bursting outwards from the centre in chunky cartoon puffs, with an icy sky-blue '
    'starburst of rays behind it, a jagged snowy mountain-peak silhouette band across its middle, snowflakes and small '
    'gold sparkles flying out at the edges. Wide oval overall shape, about 1.8 times as wide as tall, flat cartoon '
    'colours (white, icy blue, a touch of gold), thick black outline round the outer shape. The centre is calm and plain '
    'white-blue snow so lettering laid over it reads clearly. No text, no letters, no numbers.')
PLATE = (
    'A wide empty sign for a slot game\'s win amount, on a fully transparent background, nothing else: a long rounded '
    'wooden plank sign, about {r} times as wide as tall, with a thick white snow cap along its top edge with small '
    'icicles and a little snow on its ends, and a big dark navy-blue painted panel filling its face (plain and EMPTY - '
    'numbers are laid on it later), a thick even black outline. Flat cartoon colours. No text, no letters, no numbers.')


def job(name, prompt, aspect, refs=None, background=None, size=None):
    j = dict(name=name, prompt=prompt + DETAIL + '\n\n' + STYLE, aspect_ratio=aspect)
    if refs: j['refs'] = refs
    if background: j['background'] = background
    if size: j['size'] = size
    return j


def build(what):
    if what == 'plate':
        return [job('peak_plate', SUMMIT, '16:9', ['art/highpeaks/raw/plate_base2.png'], size='3840x2160')]
    if what == 'bonus':
        lead = ('Redraw the reference scene exactly - the same mountain summit, hut, trail sign, pines, flag, cairn, '
                'peaks and valley, all in the same places, the same framing and camera (do not zoom in), the same empty '
                'snow patch on the right, the same cartoon style - but change the mood: ')
        return [job('peak_plate_' + k, lead + v + ' No people, no characters, no text.', '16:9', ['art/highpeaks/raw/peak_plate.png'],
                    size='3840x2160') for k, v in MOODS.items()]
    if what == 'frames':
        return [job('peak_frame_wide', FRAME.format(w='45%'), '1:1', ['art/highpeaks/work/peak/frame_wide_ref.png'], 'transparent'),
                job('peak_frame_sq', FRAME.format(w='55%'), '3:4', ['art/highpeaks/work/peak/frame_sq_ref.png'], 'transparent')]
    if what == 'win':
        jobs = [job('peak_' + k, WIN.format(text=t, ink=i, drop=d, extra=e), '16:9', ['frontend/assets/logo.webp'], 'transparent')
                for k, (t, i, d, e) in TIERS.items()]
        jobs.append(job('peak_tier_bg', SPLASH, '16:9', None, 'transparent'))
        jobs.append(job('peak_total_bg', PLATE.format(r='three'), '16:9', None, 'transparent'))
        jobs.append(job('peak_banner_box', PLATE.format(r='five'), '16:9', None, 'transparent'))
        return jobs
    raise SystemExit('plate | bonus | frames | win')


if __name__ == '__main__':
    for what in sys.argv[1:]:
        out = os.path.join(HERE, f'peak_{what}.json')
        json.dump(build(what), open(out, 'w', encoding='utf-8'), indent=1)
        print(out)
