"""What the generator is asked for. Each entry: raw name -> (prompt, takes, kind).
Every prompt is prefixed with PREFIX. The kind drives the high-pass / low-pass / event cut in clean.py."""

PREFIX = 'Sound effect only, no voice, no music: '

S = {
    # ---- symbol win foley ----
    'reg_bell':     ('an antique brass cash register, one warm soft bell ding and the cash drawer rolling open, close up, quiet room', 8, 'foley'),
    'reg_drawer':   ('a cash register drawer sliding open with a soft wooden thunk and a gentle bell ring, close up, quiet room', 6, 'foley'),
    'keys':         ('a small bunch of car keys gently jingling once in a hand, soft metallic jingle, close up, quiet room', 8, 'foley'),
    'nozzle':       ('a petrol pump nozzle trigger clicking once, followed by a small soft liquid gurgle, close up, quiet room', 8, 'foley'),
    'jerry':        ('a finger tapping a metal jerry can twice, then a little liquid slosh inside, soft, close up, quiet room', 8, 'foley'),
    'soda':         ('a soda can being opened, one crisp tab crack followed by a short soft fizz, close up, quiet room', 8, 'foley'),
    'slushie':      ('ice crystals rattling softly in a plastic slushie cup shaken once, gentle, close up, quiet room', 8, 'foley'),
    'sizzle':       ('a hot dog sausage briefly sizzling on a hot grill roller, short soft warm sizzle, close up', 6, 'noisy'),
    'chips':        ('a bag of potato chips crinkled softly once by a hand, short, close up, quiet room', 8, 'noisy'),
    'pop':          ('a single soft bouncy rubbery pop, like a gentle cork boop, cute and round, close up, quiet room', 8, 'foley'),
    # ---- features ----
    'zippo':        ('a metal zippo lighter lid flicked open with a click, the wheel struck, and a soft small flame whoosh, close up, quiet room', 8, 'foley'),
    'whoomp':       ('a soft warm low whoomp of a small fire igniting and spreading for a moment, gentle, muffled, no crackle', 8, 'whoosh'),
    'scratch':      ('a coin scratching a lottery scratch card, three quick short scratches, close up, quiet room', 8, 'noisy'),
    'counter':      ('an old mechanical gas pump counter, number wheels rolling and ticking quickly then stopping, close up, quiet room', 8, 'foley'),
    'burn':         ('a small piece of paper burning away quickly with a soft crackle and a gentle poof, close up, quiet room', 8, 'noisy'),
    'drip':         ('a single drop of liquid falling into a glass bottle, a soft glassy plink, close up, quiet room', 8, 'foley'),
    'suck':         ('a soft whoosh of liquid sucked up a tube ending in a gentle round gloop, close up, quiet room', 8, 'whoosh'),
    'ratchet':      ('a small dashboard dial winding up with three soft mechanical ratchet clicks, close up, quiet room', 8, 'foley'),
    'dial_click':   ('a single soft mechanical click of a small car dashboard dial, close up, quiet room', 6, 'foley'),
    'coin':         ('a single coin landing softly on a wooden counter and settling, close up, quiet room', 8, 'foley'),
    'thud':         ('a deep soft muffled thud of a heavy token landing on felt, low and dark, close up, quiet room', 6, 'foley'),
    # ---- the original game's sounds, remade for Falcos (2026-11-10): HUD, board foley, ident ----
    'reg_key':      ('an old cash register key pressed once, a soft round mechanical clack, close up, quiet room', 8, 'foley'),
    'dash_btn':     ('a soft car dashboard push button pressed once, a gentle muted plastic click, close up, quiet room', 8, 'foley'),
    'toggle_sw':    ('a small car dashboard toggle switch flicked once, a soft muted click, close up, quiet room', 6, 'foley'),
    'rubber':       ('a soft rubber mallet hitting a wooden counter once, a short dull rubbery thunk, close up, quiet room', 8, 'foley'),
    'stamp':        ('a rubber stamp pressed down hard on an ink pad on a wooden desk, one soft heavy thump, close up, quiet room', 6, 'foley'),
    'coins_pour':   ('a handful of coins poured gently into a cash register tray, a soft warm jingle settling, close up, quiet room', 6, 'foley'),
    'coin_clink':   ('two coins dropped softly into a cash register drawer, one small gentle clink, close up, quiet room', 6, 'foley'),
    'key_drop':     ('a single car key on a small ring dropped softly onto a wooden counter, a short gentle metallic clink, close up, quiet room', 12, 'foley'),
    'nozzle_set':   ('a petrol pump nozzle hung back into its holder, one soft muted metal clunk, close up, quiet room', 6, 'foley'),
    'can_set':      ('a full drink can set down on a wooden counter, one soft hollow metallic tock, close up, quiet room', 6, 'foley'),
    'cup_set':      ('a paper cup set down softly on a wooden counter, one soft dull thump, close up, quiet room', 6, 'foley'),
    'bag_drop':     ('a small bag of potato chips dropped onto a counter, one soft crinkly plop, close up, quiet room', 6, 'noisy'),
    'card_drop':    ('a lottery scratch card tossed onto a wooden counter, one soft papery slap, close up, quiet room', 6, 'noisy'),
    'car_pass':     ('a car passing by slowly on a quiet night road, one soft smooth whoosh, distant, no horn', 6, 'whoosh'),
    'neon_on':      ('a large neon sign switching on at night, a soft heavy relay clunk followed by a warm low electric hum, close up', 6, 'foley'),
    'pump_start':   ('an old gas pump handle lifted with a soft clunk and the pump motor whirring up briefly, close up, quiet night', 6, 'foley'),
    'blinker':      ('a car turn signal indicator relay ticking softly four times, tick tock, close up, inside a quiet car', 4, 'foley'),
}


def jobs():
    for name, (p, n, kind) in S.items():
        yield name, PREFIX + p, n, kind
