"""Write the High Peaks art job lists (tools/highpeaks/orgen.py reads them)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = open(os.path.join(HERE, 'style.txt')).read().strip()
REF = 'art/highpeaks/raw/sym_H1_bong.png'
ICON = ("A single slot-machine symbol icon on a fully transparent background: {}. Centred, fills about 85% of the "
        "square, nothing else in the picture{}. Match the drawing style of the reference image exactly (outline weight, "
        "flat colours, cartoon proportions) but draw only the object described.\n\n" + STYLE)

SYMS = {
    'H2': ("a chunky cartoon glass stash jar stuffed and overflowing with bright green fluffy cannabis buds, a shiny gold screw "
           "lid with a leaf emblem, a little snow on the lid", ', no text'),
    'H3': ("a cartoon snowboard standing up at a jaunty angle, bright purple with a big lime-green cannabis leaf graphic, "
           "orange bindings, a puff of snow kicking off its tail", ', no text'),
    'H4': ("chunky cartoon ski goggles with a thick orange-and-teal strap, a big glossy mirrored lens showing a reflection of "
           "a snowy mountain peak", ', no text'),
    'L1': ("a fat red ceramic mug of hot cocoa with a tall swirl of whipped cream, two marshmallows and curls of steam", ', no text'),
    'L2': ("a fat hand-rolled cartoon joint, white paper, a glowing orange ember tip and a curly wisp of grey smoke", ', no text'),
    'L3': ("a thick square chocolate brownie with fudgy crumbs and one small green cannabis leaf on top", ', no text'),
    'L4': ("a knitted winter beanie hat, teal and white stripes, a huge fluffy white pom-pom and a small green leaf patch", ', no text'),
    'L5': ("a cheesy cartoon pizza slice with pepperoni and gooey stretching cheese (the munchies)", ', no text'),
    'ZP': ("a cartoon disposable lighter, lime green body with a little leaf print, a big bright orange-yellow flame on top", ', no text'),
    'ST': ("a ski lift pass ticket on a little wire hanger, teal card with a silver scratch-off panel half scratched showing a "
           "big question mark, the word SCRATCH! in bold cartoon letters at the top", ''),
    'GT': ("a GOLDEN ski lift pass ticket on a little wire hanger, shiny gold card with sparkles and a tiny crown, a silver "
           "scratch-off panel half scratched showing a big question mark, the word SCRATCH! in bold cartoon letters at the top", ''),
    'GP': ("a cartoon snowmaking snow cannon: a big round yellow fan barrel on a red stand with wheels, blasting a spray of "
           "snowflakes forward", ', no text'),
    'FDG': ("one plump fluffy bright-green cannabis bud (a nug) with orange hairs and a couple of tiny white sparkles", ', no text'),
    'FDA': ("one plump fluffy cannabis bud (a nug) coloured warm golden amber, glittering with sparkles", ', no text'),
    'FDR': ("one plump fluffy cannabis bud (a nug) coloured hot crimson red with a little fiery glow around it", ', no text'),
    'BS': ("a round golden token coin with a thick rim: in the middle a snowy mountain peak with a green cannabis leaf above "
           "it, and the bold cartoon letters FS across the front in white with a black outline", ''),
    'DS': ("a ski-trail BLACK DIAMOND token: a black diamond shape on a round icy-blue coin with a silver rim, little stars, "
           "and the bold cartoon letters XFS across the front in white with a black outline", ''),
    'JP': ("a big round mystery coin, deep purple face with a thick shiny gold rim, a huge bold white question mark ? in the "
           "middle with a black outline, a few sparkles around it", ''),
}
syms = [dict(name=f'sym_{k}', aspect_ratio='1:1', background='transparent', refs=[REF], prompt=ICON.format(*v))
        for k, v in SYMS.items()]

LOGO = ("A slot-game title logo on a fully transparent background: the words \"{}\" in huge chunky bubbly cartoon letters "
        "with a thick black outline, {}. Wide horizontal layout, the letters fill the frame edge to edge, the spelling must be "
        "exactly \"{}\", nothing else in the picture.\n\n" + STYLE)
LOGOS = {
    'logo_game': ('HIGH PEAKS', 'icy white-and-sky-blue letters capped with dripping snow, a small green cannabis leaf dotting the I, a snowy mountain peak behind the words'),
    'logo_chance': ('HIGHER CHANCE', 'HIGHER in lime green and CHANCE in sunny yellow, little puffs of smoke around the letters'),
    'logo_fillup': ('STASH', 'bright green letters with gold trim, a few cartoon buds tumbling off the letters'),
    'logo_premium': ('FRESH POWDER', 'white snowy letters with icy blue shading, snowflakes and snow spray'),
    'logo_nitro': ('AVALANCHE SPIN', 'electric blue letters crashing with a wave of snow, lightning bolts'),
    'logo_midnight': ('BLACK DIAMOND', 'black and deep purple letters with silver rims, a small black diamond ski sign and stars'),
    'title_features': ('HOT FEATURES', 'HOT in orange with flames, FEATURES in cream white, stacked on two lines'),
    'title_bonus': ('BIG BONUSES', 'BIG in lime green, BONUSES in cream white, stacked on two lines'),
    'title_max': ('MAX WIN', 'MAX in icy blue, WIN in cream white, stacked on two lines'),
    'jp_mini': ('MINI', 'bright lime-green letters on a rounded pill-shaped green plaque with a white rim'),
    'jp_minor': ('MINOR', 'sky-blue letters on a rounded pill-shaped blue plaque with a white rim'),
    'jp_major': ('MAJOR', 'purple letters on a rounded pill-shaped purple plaque with a white rim'),
    'jp_grand': ('GRAND', 'shiny gold letters on a rounded pill-shaped gold plaque with sparkles and a tiny crown'),
}
logos = [dict(name=k, aspect_ratio='16:9' if k.startswith(('logo', 'jp')) else '16:9', background='transparent',
              prompt=LOGO.format(w, d, w)) for k, (w, d) in LOGOS.items()]

CARD = ("Slot-game bonus-buy card artwork, full-bleed, no text, no letters, no logos: {}. Bold, busy, colourful composition "
        "that fills the whole frame, set in a cartoon snowy mountain ski resort.\n\n" + STYLE)
CARDS = {
    'menu_chance': ('16:9', "a grinning cartoon cannabis-leaf mascot wearing ski goggles rides a chairlift up a snowy peak, a big round gauge dial beside it with its needle swinging into the green, puffs of smoke"),
    'menu_nitro': ('2:3', "a gigantic cartoon avalanche of snow roaring down the mountain with a laughing snowboarder surfing the front of it, lightning bolts, chunks of snow flying"),
    'menu_fillup': ('2:3', "a giant glass stash jar on the snow filling up with glowing green, gold and red cannabis buds raining down from the sky, a cosy ski lodge behind"),
    'menu_premium': ('2:3', "a goofy cartoon snowboarder carving through deep fresh powder snow, a huge white spray of snow, big snowflakes falling, bright blue sky"),
    'menu_midnight': ('2:3', "a night ski run under a big moon and green northern lights, a black diamond trail sign in the foreground, a skier with a glowing headlamp"),
    'load_features': ('2:3', "a pile of cartoon game pieces on the snow: a lime-green lighter with a big flame, a yellow snow cannon blasting snow, a teal lift pass ticket and a purple mystery coin with a question mark"),
    'load_bonus': ('2:3', "a stash jar spilling glowing cannabis buds, golden coins with snowy peaks and a black diamond coin, bursting out of the snow"),
    'load_max': ('2:3', "a huge avalanche of gold coins and green cannabis buds pouring down a snowy mountain, sparkles everywhere"),
}
cards = [dict(name=k, aspect_ratio=a, prompt=CARD.format(d)) for k, (a, d) in CARDS.items()]

json.dump(syms, open(os.path.join(HERE, 'syms.json'), 'w'), indent=1)
json.dump(logos + cards, open(os.path.join(HERE, 'ui.json'), 'w'), indent=1)
print(len(syms), len(logos), len(cards))
