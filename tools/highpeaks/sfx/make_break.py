"""The symbol break (owner, 2026-11-16: "whenever the symbols break. make it have a sound and dont just make them
disappear. make the break away"): sfx_break_1..3, synthesised here (no generation call, no cost).

One take is a cartoon crack and the pieces falling away:
  * the crack: a short bright snap (band-passed noise, 2-6 kHz, ~10 ms), a woody knock under it that drops
    in pitch (190 -> 120 Hz) and a mid crunch (0.5-2.2 kHz, ~70 ms)
  * the break away: 9-14 small grains (band-passed noise ticks, 1-4.5 kHz) scattered over the next 0.4 s,
    denser at the start and quieter as they go, panned left and right, as the chunks clatter off
  * a soft glass plink on D6 (the sets' D major), low, so a run of breaks stays in key with the wins

Mastered like the other sets (audio.master: trim, air shelf, fades, loudness target, limiter at -6.5 dBFS),
louder than the old pop (-21 LUFS) so it reads over the music. Delivered like deliver.py: the WAV master to
art/highpeaks/sfx_masters, Opus .ogg and AAC .aac to frontend/assets, an entry in art/highpeaks/sfx_manifest.json.

    .venv/bin/python tools/highpeaks/sfx/make_break.py
"""
import os, sys, json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A
import synth as S
import deliver as D

SR = 48000
STEM, TAKES, LUFS = 'sfx_break', 3, -21.0


def band(x, lo, hi):
    return sosfilt(butter(4, [lo, hi], btype='band', fs=SR, output='sos'), x)


def env(n, att, tau):
    t = np.arange(n) / SR
    e = np.exp(-np.maximum(0, t - att) / tau)
    a = int(att * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    return e


def take(seed):
    rnd = np.random.default_rng(1000 + seed)
    dur = .62
    n = int(dur * SR)
    L, R = np.zeros(n), np.zeros(n)

    def put(sig, at, gain, pan=0.0):
        i = int(at * SR)
        m = min(len(sig), n - i)
        if m <= 0:
            return
        L[i:i + m] += sig[:m] * gain * np.sqrt(.5 * (1 - pan))
        R[i:i + m] += sig[:m] * gain * np.sqrt(.5 * (1 + pan))

    # the crack
    k = int(.05 * SR)
    snap = band(rnd.standard_normal(k), 2000, 6000) * env(k, .0015, .011 + .003 * seed)
    put(snap, 0, 1.0)
    k = int(.16 * SR)
    t = np.arange(k) / SR
    f = 120 + 70 * np.exp(-t / .03) + rnd.uniform(-8, 8)
    knock = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(k, .002, .045)
    put(knock, .002, .9)
    k = int(.2 * SR)
    crunch = band(rnd.standard_normal(k), 500, 2200) * env(k, .003, .065)
    put(crunch, .004, .7)
    # the pieces clattering away
    grains = rnd.integers(9, 15)
    for g in range(grains):
        at = .05 + .4 * (g / grains) ** 1.4 + rnd.uniform(-.015, .015)
        k = int(rnd.uniform(.008, .022) * SR)
        lo = rnd.uniform(1000, 2600)
        gr = band(rnd.standard_normal(k), lo, lo * rnd.uniform(1.6, 2.2)) * env(k, .0008, rnd.uniform(.004, .009))
        put(gr, at, .55 * (1 - .6 * g / grains) * rnd.uniform(.7, 1.0), rnd.uniform(-.7, .7))
    # in key
    plink = S.glass(1174.66 * (1, 1.1225, 1.3348)[seed % 3], dur=.3, seed=seed)
    put(np.asarray(plink, float), .006, .12)
    return A.master(np.stack([L, R], 1), SR, LUFS, fout=.06)


def main():
    os.makedirs(D.MASTERS, exist_ok=True)
    entry = dict(takes=[], ogg=[], aac=[], seconds=[], lufs=[], peak_db=[], peak_db_ogg=[], peak_db_aac=[])
    for i in range(1, TAKES + 1):
        x = take(i)
        base = f'{STEM}_{i}'
        wav = os.path.join(D.MASTERS, base + '.wav')
        sf.write(wav, x, SR, subtype='PCM_16')
        po = D.encode(wav, os.path.join(D.ASSETS, base + '.ogg'), ['-c:a', 'libopus', '-b:a', '96k', '-ar', '48000', '-vbr', 'on', '-application', 'audio'])
        pa = D.encode(wav, os.path.join(D.ASSETS, base + '.aac'), ['-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-f', 'adts'])
        entry['takes'].append(base + '.wav'); entry['ogg'].append(base + '.ogg'); entry['aac'].append(base + '.aac')
        entry['seconds'].append(round(len(x) / SR, 3)); entry['lufs'].append(round(A.lufs(x, SR), 2))
        entry['peak_db'].append(round(A.peak_db(x), 2)); entry['peak_db_ogg'].append(round(po, 2)); entry['peak_db_aac'].append(round(pa, 2))
    entry.update(target_lufs=LUFS, purpose='A winning symbol breaking away: crack, then its pieces clattering off', sources=['synth'] * TAKES)
    man = json.load(open(D.MAN))
    man[STEM] = entry
    json.dump(man, open(D.MAN, 'w'), indent=1)
    print(json.dumps(entry))


if __name__ == '__main__':
    main()
