"""High Peaks: more sounds, and sounds of what the game IS (owner, 2026-11-26: "the sound fx could be more dynamic
depending on value, speed, amount, etc and add more sounds so they are less repetitive").

    python tools/highpeaks/sfx/dynamics.py            (numpy, scipy, soundfile; ffmpeg found on the machine - see ffmpeg())

Synthesised here, no generation call and no cost. The board's foley was Falcos's (a gas station: coins, chains, cans,
metal) and every winning symbol left with the same three "crack and clatter" takes. These are the mountain's:

  ice_break    x6   a symbol freezing and SHATTERING: a bright snap, a cluster of glassy pings, a soft low knock and
                    the shards tinkling away to both sides (the exit clip's sound; was sfx_break)
  ice_mult     x4   a cell multiplier landing: a frosty glass ding on D6 with a breath of air (the page pitches it by
                    the multiplier's value, so x2 ... x64 climb the scale)
  land_snow    x4   something soft landing in snow: a low thump and a little crunch
  land_wood    x3   skis, a board: a hollow wooden knock
  land_glass   x3   a jar, goggles, the bong, a mug: a clink
  land_cloth   x3   a beanie, a joint, a slice: a soft pat
  snow_whoosh  x3   a tumble's refill coming down: air and powder
  bong_rip     x3   the ice bong being hit: water bubbling hard under the draw of air
  bong_out     x2   the hit let go: a soft breath of smoke, the water settling
  thunder      x3   AVALANCHE's storm: a crack and its rumble rolling off

Each take has its own seed (grain positions, partials, lengths), so a run of them never loops; the page adds pitch,
level and left-right placement on top (index.html sfx(name, rate, { vol, pan })).

Delivered like the other sets: Opus .ogg (96 kb/s) and AAC .aac (128 kb/s) in frontend/assets, the WAV master in
art/highpeaks/sfx_masters. Loudness: BS.1770 K-weighted, ungated (these are a quarter of a second long), then a peak
ceiling of -6.5 dBFS.
"""
import glob, os, subprocess, sys
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, lfilter

SR = 48000
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
ASSETS = os.path.join(ROOT, 'frontend', 'assets')
MASTERS = os.path.join(ROOT, 'art', 'highpeaks', 'sfx_masters')


def ffmpeg():
    """An ffmpeg to encode with: $HP_FFMPEG, the imageio-ffmpeg package if this Python has it, or the copy another of
    the studio's projects already keeps in its venv."""
    if os.environ.get('HP_FFMPEG'):
        return os.environ['HP_FFMPEG']
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    home = os.path.expanduser('~')
    for pat in ('projects/*/.venv*/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg*', 'Documents/*/.venv*/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg*',
                'Documents/*/.venv*/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg*'):
        hit = sorted(glob.glob(os.path.join(home, pat)))
        if hit:
            return hit[0]
    sys.exit('no ffmpeg: set HP_FFMPEG, or pip install imageio-ffmpeg')


# ------------------------------------------------------------------ building blocks (all mono, float)
def t_(dur):
    return np.arange(int(dur * SR)) / SR


def env(n, att, tau):
    t = np.arange(n) / SR
    a = np.where(t < att, .5 - .5 * np.cos(np.pi * np.clip(t / max(att, 1e-6), 0, 1)), 1.0)
    return a * np.exp(-np.maximum(0, t - att) / tau)


def noise(rng, dur, lo, hi, att, tau, order=2):
    n = int(dur * SR)
    sos = butter(order, [lo, hi], 'bandpass', fs=SR, output='sos')
    return sosfilt(sos, rng.standard_normal(n)) * env(n, att, tau)


def ping(f, dur, tau, att=.001, partials=((1, 1), (2.76, .3), (5.4, .12)), settle=.02):
    t = t_(dur)
    ph = 2 * np.pi * np.cumsum(f * (1 + settle * np.exp(-t / .008))) / SR
    return sum(g * np.sin(r * ph) * np.exp(-t / (tau / (1 + .6 * i))) for i, (r, g) in enumerate(partials)) * env(len(t), att, tau)


def knock(f0, f1, dur, tau):
    t = t_(dur)
    f = f0 * (f1 / f0) ** np.clip(t / dur, 0, 1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), .002, tau)


class Mix:
    """A stereo canvas: place a mono sound at a time, a level and a place left to right (-1 .. 1)."""
    def __init__(self, dur):
        self.x = np.zeros((int(dur * SR), 2))

    def add(self, s, at=0.0, gain=1.0, pan=0.0):
        i = int(at * SR); n = min(len(s), len(self.x) - i)
        if n <= 0:
            return
        a = (pan + 1) * np.pi / 4
        self.x[i:i + n, 0] += s[:n] * gain * np.cos(a) * 1.4142
        self.x[i:i + n, 1] += s[:n] * gain * np.sin(a) * 1.4142


# ------------------------------------------------------------------ the sounds
def ice_break(seed):
    rng = np.random.default_rng(900 + seed)
    m = Mix(.62)
    base = rng.uniform(2300, 3400)
    m.add(noise(rng, .03, 3200, 11000, .0004, .006), 0, .9)                               # the snap
    m.add(noise(rng, .09, 700, 2600, .001, .022), .002, .45)                              # the body cracking through
    m.add(knock(rng.uniform(170, 210), rng.uniform(95, 120), .12, .04), 0, .5)            # a low knock under it
    for k in range(rng.integers(3, 6)):                                                   # the ice ringing: a cluster of pings
        m.add(ping(base * rng.uniform(.7, 1.9), .22, rng.uniform(.03, .075)), rng.uniform(0, .018), rng.uniform(.25, .5), rng.uniform(-.5, .5))
    n = rng.integers(9, 15)                                                               # the shards tinkling away
    for k in range(n):
        at = .04 + .42 * rng.random() ** 1.7
        m.add(ping(rng.uniform(3200, 8200), .09, rng.uniform(.012, .035), partials=((1, 1), (2.3, .25))), at, .3 * (1 - at) ** 1.5 * rng.uniform(.5, 1), rng.uniform(-.9, .9))
    m.add(noise(rng, .3, 2500, 9000, .01, .09), .03, .12)                                 # a breath of powder
    return m.x


def ice_mult(seed):
    rng = np.random.default_rng(1300 + seed)
    m = Mix(.55)
    f = 1174.66                                                                           # D6
    parts = [((1, 1), (2.76, .3), (5.4, .1)), ((1, 1), (2.0, .35), (3.01, .2), (4.2, .08)), ((1, 1), (2.76, .2), (4.07, .22)), ((1, 1), (1.5, .3), (2.76, .25), (6.1, .06))][seed % 4]
    m.add(ping(f, .5, rng.uniform(.11, .16), partials=parts, settle=.012), .004, .9)
    m.add(ping(f * 2, .3, .05, partials=((1, 1), (2.76, .2))), .004, .22, rng.uniform(-.3, .3))
    m.add(noise(rng, .05, 2500, 9000, .004, .012), 0, .3)                                 # the frost of its attack
    m.add(noise(rng, .25, 1800, 7000, .02, .07), .01, .07)
    return m.x


def land_snow(seed):
    rng = np.random.default_rng(1700 + seed)
    m = Mix(.3)
    m.add(knock(rng.uniform(120, 150), rng.uniform(60, 78), .16, rng.uniform(.035, .05)), 0, .9)
    m.add(noise(rng, .14, 180, 1100, .003, rng.uniform(.03, .045)), 0, .7)
    for k in range(rng.integers(3, 6)):                                                   # the crunch
        m.add(noise(rng, .025, 900, 3800, .0006, .005), .008 + rng.random() * .07, rng.uniform(.12, .25), rng.uniform(-.4, .4))
    return m.x


def land_wood(seed):
    rng = np.random.default_rng(2100 + seed)
    m = Mix(.26)
    f = rng.uniform(380, 470)
    for r, g, tau in ((1, 1, .03), (2.32, .5, .02), (3.9, .3, .013), (5.6, .14, .008)):
        m.add(ping(f * r * rng.uniform(.98, 1.02), .2, tau, partials=((1, 1),), settle=0), 0, g * .6)
    m.add(noise(rng, .012, 1500, 6000, .0003, .003), 0, .45)
    m.add(knock(150, 105, .08, .02), 0, .35)
    return m.x


def land_glass(seed):
    rng = np.random.default_rng(2500 + seed)
    m = Mix(.34)
    f = rng.uniform(1700, 2300)
    m.add(ping(f, .3, rng.uniform(.04, .07)), 0, .7)
    m.add(ping(f * rng.uniform(1.45, 1.62), .25, .035), .003, .4, rng.uniform(-.4, .4))
    m.add(ping(f * rng.uniform(2.3, 2.6), .18, .02, partials=((1, 1),)), .001, .2, rng.uniform(-.4, .4))
    m.add(noise(rng, .01, 3000, 10000, .0003, .002), 0, .35)
    return m.x


def land_cloth(seed):
    rng = np.random.default_rng(2900 + seed)
    m = Mix(.22)
    m.add(noise(rng, .12, 250, 1900, .004, rng.uniform(.02, .032)), 0, .9)
    m.add(knock(rng.uniform(150, 185), 95, .08, .022), 0, .4)
    m.add(noise(rng, .05, 1500, 5000, .004, .012), .004, .18, rng.uniform(-.3, .3))
    return m.x


def snow_whoosh(seed):
    rng = np.random.default_rng(3300 + seed)
    dur = rng.uniform(.38, .46)
    n = int(dur * SR); t = np.arange(n) / SR
    raw = rng.standard_normal((n, 2))
    # a band of air sliding DOWN as the powder falls: three fixed bands, cross-faded from the highest to the lowest
    bands = [(1900, 7000), (1000, 3600), (450, 1700)]
    u = t / dur
    gains = [np.clip(1 - u * 2.2, 0, 1), np.clip(1 - np.abs(u - .45) * 2.6, 0, 1), np.clip((u - .35) * 2.0, 0, 1)]
    out = sum(sosfilt(butter(2, bd, 'bandpass', fs=SR, output='sos'), raw, axis=0) * g[:, None] for bd, g in zip(bands, gains))
    e = np.sin(np.pi * np.clip(u, 0, 1)) ** 1.4 * np.exp(-t / (dur * .9))
    return out * e[:, None] * .5


def bubble(rng, f0, dur):
    """One bubble: a sine that rises in pitch as it shrinks, a fast attack and a short ring."""
    t = t_(dur)
    f = f0 * (1 + .7 * (t / dur) ** .8)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), .002, dur * .45)


def bong_rip(seed):
    """The bong being hit (owner, 2026-11-26: "add a bong bubbling / hitting sound when we get the bong smoke"): water
    bubbling hard for a second and a bit - small quick bubbles over slower deep glugs - with the draw of air over it,
    swelling as the smoke climbs."""
    rng = np.random.default_rng(3700 + seed)
    dur = 1.3
    m = Mix(dur)
    swell = lambda at: .35 + .65 * min(1.0, at / .5)
    at = .02
    while at < dur - .12:                                                                 # the quick bubbles
        m.add(bubble(rng, rng.uniform(300, 760), rng.uniform(.022, .05)), at, rng.uniform(.35, .7) * swell(at), rng.uniform(-.5, .5))
        at += rng.uniform(.014, .042)
    at = .0
    while at < dur - .2:                                                                  # the deep glugs under them
        m.add(bubble(rng, rng.uniform(120, 210), rng.uniform(.06, .1)), at, rng.uniform(.5, .85) * swell(at), rng.uniform(-.25, .25))
        at += rng.uniform(.07, .13)
    n = int(dur * SR); t = np.arange(n) / SR                                              # the draw: air through the water
    air = sosfilt(butter(2, [450, 2600], 'bandpass', fs=SR, output='sos'), rng.standard_normal(n))
    air *= (.25 + .75 * np.clip(t / .7, 0, 1)) * np.clip((dur - t) / .12, 0, 1) * (1 + .35 * np.sin(2 * np.pi * rng.uniform(17, 24) * t))
    m.add(air, 0, .16)
    low = sosfilt(butter(2, [70, 190], 'bandpass', fs=SR, output='sos'), rng.standard_normal(n)) * np.clip(t / .3, 0, 1) * np.clip((dur - t) / .15, 0, 1)
    m.add(low, 0, .5)                                                                     # the chamber rumbling
    return m.x


def bong_out(seed):
    """The hit let go: a long soft breath of smoke out of the mouthpiece, and the water settling."""
    rng = np.random.default_rng(4100 + seed)
    dur = .85
    n = int(dur * SR); t = np.arange(n) / SR
    m = Mix(dur)
    raw = rng.standard_normal(n)
    hi = sosfilt(butter(2, [900, 4200], 'bandpass', fs=SR, output='sos'), raw) * np.clip(1 - t / .5, 0, 1)
    lo = sosfilt(butter(2, [300, 1400], 'bandpass', fs=SR, output='sos'), raw) * np.clip(t / .25, 0, 1)
    m.add((hi + lo) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** .7 * np.exp(-t / .38), 0, .5)
    for k in range(rng.integers(3, 6)):                                                   # a last few bubbles
        m.add(bubble(rng, rng.uniform(260, 520), rng.uniform(.03, .05)), .03 + rng.random() * .3, rng.uniform(.15, .3), rng.uniform(-.4, .4))
    return m.x


def thunder(seed):
    """AVALANCHE's storm: a crack up in the clouds and the rumble rolling away after it (kept low and soft - it plays
    under a round, again and again)."""
    rng = np.random.default_rng(4500 + seed)
    dur = rng.uniform(1.7, 2.1)
    n = int(dur * SR); t = np.arange(n) / SR
    m = Mix(dur)
    m.add(noise(rng, .12, 250, 1800, .002, .03), .0, .5, rng.uniform(-.4, .4))            # the crack
    m.add(noise(rng, .2, 120, 700, .004, .06), .03, .5)
    rum = sosfilt(butter(3, [32, 150], 'bandpass', fs=SR, output='sos'), rng.standard_normal(n))
    roll = 1 + .6 * np.sin(2 * np.pi * rng.uniform(2.2, 3.4) * t + rng.uniform(0, 6)) + .4 * np.sin(2 * np.pi * rng.uniform(5, 8) * t)
    m.add(rum * roll * np.clip(t / .05, 0, 1) * np.exp(-t / (dur * .42)), .02, 1.0)
    m.add(knock(rng.uniform(70, 90), 40, .5, .2), .03, .6)
    return m.x


SETS = [  # stem, takes, loudness target (LUFS), maker
    ('ice_break', 6, -21.0, ice_break), ('ice_mult', 4, -24.0, ice_mult), ('land_snow', 4, -26.0, land_snow),
    ('land_wood', 3, -26.0, land_wood), ('land_glass', 3, -26.5, land_glass), ('land_cloth', 3, -27.0, land_cloth),
    ('snow_whoosh', 3, -25.0, snow_whoosh),
    ('bong_rip', 3, -22.0, bong_rip), ('bong_out', 2, -24.0, bong_out), ('thunder', 3, -24.0, thunder),
]


# ------------------------------------------------------------------ mastering and delivery
def lufs(x):
    """BS.1770 K-weighted loudness, ungated (two biquads at 48 kHz, then the mean square of both channels)."""
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)
    return -0.691 + 10 * np.log10(np.mean(y ** 2, axis=0).sum() + 1e-12)


def master(x, target, ceil_db=-6.5):
    lead = np.argmax(np.abs(x).max(1) > 10 ** (-60 / 20) * np.abs(x).max())             # trim the silence in front
    x = x[max(0, lead - 48):]
    tail = len(x) - np.argmax(np.abs(x[::-1]).max(1) > 10 ** (-66 / 20) * np.abs(x).max())
    x = x[:min(len(x), tail + int(.02 * SR))].copy()
    fo = min(len(x), int(.03 * SR)); x[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2; x[:24] *= np.linspace(0, 1, 24)[:, None]
    x = x * 10 ** ((target - lufs(x)) / 20)
    ceil = 10 ** (ceil_db / 20)
    pk = np.abs(x).max()
    if pk > ceil:                                                                         # a soft knee, then exactly the ceiling
        x = np.tanh(x / ceil * 1.2) / np.tanh(1.2) * ceil if pk < ceil * 2.2 else x / pk * ceil
        x = x * min(1.0, ceil / np.abs(x).max())
    return x


def deliver(stem, take, x, ff):
    os.makedirs(MASTERS, exist_ok=True)
    name = f'sfx_{stem}_{take}'
    wav = os.path.join(MASTERS, name + '.wav')
    sf.write(wav, x, SR, subtype='PCM_16')
    run = lambda *a: subprocess.run([ff, '-hide_banner', '-loglevel', 'error', '-y', *a], check=True)
    run('-i', wav, '-c:a', 'libopus', '-b:a', '96k', '-ar', '48000', '-vbr', 'on', '-application', 'audio', os.path.join(ASSETS, name + '.ogg'))
    run('-i', wav, '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-f', 'adts', os.path.join(ASSETS, name + '.aac'))
    return os.path.getsize(os.path.join(ASSETS, name + '.ogg')) + os.path.getsize(os.path.join(ASSETS, name + '.aac'))


if __name__ == '__main__':
    ff = ffmpeg()
    total = 0
    only = set(sys.argv[1:])
    for stem, takes, target, make in SETS:
        if only and stem not in only:
            continue
        row = []
        for k in range(1, takes + 1):
            y = master(make(k), target)
            total += deliver(stem, k, y, ff)
            row.append(f'{len(y) / SR:.2f}s {lufs(y):.1f}LUFS pk{20 * np.log10(np.abs(y).max()):.1f}')
        print(f'{stem:12s}', ' | '.join(row), flush=True)
    print(f'{sum(s[1] for s in SETS if not only or s[0] in only)} takes, {total // 1024} KB of .ogg + .aac')
