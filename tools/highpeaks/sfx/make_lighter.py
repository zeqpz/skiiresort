"""The Zippo sounds like a lighter (owner, 2026-11-16: "make the lighter when it gets used sound like a lighter"):
sfx_zippo_flick_1..3 and sfx_zippo_burn_1..3 remade, synthesised here (no generation call, no cost), under the same
names and take counts, so index.html plays them where it always did.

  zippo_flick  the lighter: the lid flipping open (the Zippo's metal clink - a click, then a bright inharmonic ping
               off the brass case, its hinge's second tick right behind it), the thumb rolling the flint wheel (a
               quick rasp of grit and sparks) and the wick catching (a soft "fff" of flame)
  zippo_burn   the fire it starts: a whoomp as the flame flares (a low thump under a rising roar), then the burning -
               a fluttering low roar with crackles - dying away

    .venv/bin/python tools/highpeaks/sfx/make_lighter.py
"""
import os, sys, json
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A
import deliver as D
from make_break import band, env, SR


def lowpass(x, f):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(4, f, btype='low', fs=SR, output='sos'), x)


class Mix:
    def __init__(self, dur):
        self.n = int(dur * SR)
        self.L, self.R = np.zeros(self.n), np.zeros(self.n)

    def put(self, sig, at, gain, pan=0.0):
        i = int(at * SR)
        m = min(len(sig), self.n - i)
        if m > 0:
            self.L[i:i + m] += sig[:m] * gain * np.sqrt(.5 * (1 - pan))
            self.R[i:i + m] += sig[:m] * gain * np.sqrt(.5 * (1 + pan))

    def out(self):
        return np.stack([self.L, self.R], 1)


def ping(f0, dur, rnd):
    """The case's metal ring: decaying sines at inharmonic ratios, the upper ones dying first."""
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for ratio, g, tau in ((1, 1, .07), (1.52, .6, .05), (2.31, .45, .035), (2.94, .3, .025), (.61, .35, .04)):
        f = f0 * ratio * (1 + rnd.uniform(-.006, .006))
        out += g * np.sin(2 * np.pi * f * t + rnd.uniform(0, 6.3)) * np.exp(-t / tau)
    return out * env(len(t), .0006, 1e9)


def flick(seed):
    rnd = np.random.default_rng(2000 + seed)
    mx = Mix(.62)
    # the lid flips open: a click, the ring off the case, the hinge's tick 15-22 ms behind
    k = int(.006 * SR)
    mx.put(band(rnd.standard_normal(k), 2500, 8000) * env(k, .0003, .0012), 0, .9)
    mx.put(ping(rnd.uniform(2300, 2700), .3, rnd), .001, .55)
    k = int(.03 * SR)
    mx.put(np.sin(2 * np.pi * rnd.uniform(800, 1000) * np.arange(k) / SR) * env(k, .0004, .008), .001, .4)
    hinge = rnd.uniform(.015, .022)
    k = int(.005 * SR)
    mx.put(band(rnd.standard_normal(k), 3000, 7500) * env(k, .0002, .001), hinge, .45)
    mx.put(ping(rnd.uniform(3300, 3800), .15, rnd), hinge + .0005, .18)
    # the thumb rolls the flint wheel: a rasp of grit (8-12 grains over 45-60 ms) with sparks
    at = rnd.uniform(.13, .16)
    grains = rnd.integers(8, 13)
    span = rnd.uniform(.045, .06)
    for g in range(grains):
        k = int(rnd.uniform(.003, .007) * SR)
        lo = rnd.uniform(2200, 3800)
        mx.put(band(rnd.standard_normal(k), lo, lo * 2) * env(k, .0003, .0018), at + span * g / grains + rnd.uniform(0, .003),
               .5 * rnd.uniform(.6, 1), rnd.uniform(-.25, .25))
    k = int(.07 * SR)
    mx.put(band(rnd.standard_normal(k), 1500, 5000) * env(k, .004, .02), at, .25)            # the wheel's own whirr
    # the wick catches: a soft "fff", a little body under it
    ig = at + span * .8
    k = int(.38 * SR)
    t = np.arange(k) / SR
    fff = band(rnd.standard_normal(k), 400, 2400) * (1 - np.exp(-t / .02)) * np.exp(-t / .13)
    mx.put(fff, ig, .55)
    mx.put(lowpass(rnd.standard_normal(k), 500) * (1 - np.exp(-t / .03)) * np.exp(-t / .16), ig, .5)
    return A.master(mx.out(), SR, -22.0, fout=.07)


def burn(seed):
    rnd = np.random.default_rng(3000 + seed)
    mx = Mix(1.05)
    # the flare: a low thump and a roar swelling up through the band
    k = int(.18 * SR)
    t = np.arange(k) / SR
    mx.put(np.sin(2 * np.pi * np.cumsum(55 + 45 * np.exp(-t / .04)) / SR) * env(k, .004, .06), 0, .9)
    k = int(.5 * SR)
    t = np.arange(k) / SR
    x = rnd.standard_normal(k)
    lo, hi = band(x, 150, 600), band(x, 600, 2200)
    sweep = np.clip(t / .12, 0, 1)
    roar = (lo * (1 - .6 * sweep) + hi * sweep) * (1 - np.exp(-t / .035)) * np.exp(-t / .22)
    mx.put(roar, .005, 1.0)
    # the burning: a fluttering low roar dying away, crackles over it
    k = int(1.0 * SR)
    t = np.arange(k) / SR
    flut = 1 + .35 * np.sin(2 * np.pi * np.cumsum(rnd.uniform(7, 13) + 3 * np.sin(2 * np.pi * .9 * t)) / SR)
    body = lowpass(rnd.standard_normal(k), 700) * flut * np.clip((t - .06) / .12, 0, 1) * np.exp(-np.maximum(0, t - .2) / .3)
    mx.put(body, 0, .75)
    for _ in range(rnd.integers(10, 16)):
        k = int(rnd.uniform(.002, .005) * SR)
        lo = rnd.uniform(1400, 3200)
        at = rnd.uniform(.08, .8)
        mx.put(band(rnd.standard_normal(k), lo, lo * 1.8) * env(k, .0002, .0012), at, .45 * np.exp(-at / .5) + .1, rnd.uniform(-.6, .6))
    return A.master(mx.out(), SR, -21.0, fout=.12)


def deliver(stem, make, purpose, lufs):
    entry = dict(takes=[], ogg=[], aac=[], seconds=[], lufs=[], peak_db=[], peak_db_ogg=[], peak_db_aac=[])
    for i in (1, 2, 3):
        x = make(i)
        base = f'{stem}_{i}'
        wav = os.path.join(D.MASTERS, base + '.wav')
        sf.write(wav, x, SR, subtype='PCM_16')
        po = D.encode(wav, os.path.join(D.ASSETS, base + '.ogg'), ['-c:a', 'libopus', '-b:a', '96k', '-ar', '48000', '-vbr', 'on', '-application', 'audio'])
        pa = D.encode(wav, os.path.join(D.ASSETS, base + '.aac'), ['-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-f', 'adts'])
        entry['takes'].append(base + '.wav'); entry['ogg'].append(base + '.ogg'); entry['aac'].append(base + '.aac')
        entry['seconds'].append(round(len(x) / SR, 3)); entry['lufs'].append(round(A.lufs(x, SR), 2))
        entry['peak_db'].append(round(A.peak_db(x), 2)); entry['peak_db_ogg'].append(round(po, 2)); entry['peak_db_aac'].append(round(pa, 2))
    entry.update(target_lufs=lufs, purpose=purpose, sources=['synth'] * 3)
    return entry


def main():
    os.makedirs(D.MASTERS, exist_ok=True)
    man = json.load(open(D.MAN))
    man['sfx_zippo_flick'] = deliver('sfx_zippo_flick', flick, 'The Zippo lit: lid clink, flint wheel, the wick catching', -22.0)
    man['sfx_zippo_burn'] = deliver('sfx_zippo_burn', burn, "The Zippo's fire: a flare, then the flame roaring and crackling away", -21.0)
    json.dump(man, open(D.MAN, 'w'), indent=1)
    for k in ('sfx_zippo_flick', 'sfx_zippo_burn'):
        print(k, man[k]['seconds'], man[k]['lufs'], man[k]['peak_db_ogg'])


if __name__ == '__main__':
    main()
