"""Clean and measure every raw take: art/highpeaks/sfx_raw/clean/<name>_<take>.wav (48 kHz, cleaned, gated)
and art/highpeaks/sfx_raw/analysis.json. A take is rejected for speech-like content, clipping or a hissy bed.
  python analyze.py [name ...]"""
import os, sys, json, glob, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A
import spec

CLEAN = os.path.join(A.RAW, 'clean')
OUT = os.path.join(A.RAW, 'analysis.json')
# per kind: high-pass, low-pass (warmth: nothing bright gets through), gate depth under the peak
KIND = {'foley': (90, 11500, -52), 'noisy': (150, 11000, -48), 'whoosh': (60, 11000, -50)}   # (2026-11-13: was 9000/6500/6000 - it muffled them)


def main():
    os.makedirs(CLEAN, exist_ok=True)
    rep = json.load(open(OUT)) if os.path.exists(OUT) else {}
    want = sys.argv[1:]
    for p in sorted(glob.glob(os.path.join(A.RAW, '*.pcm'))):
        m = re.match(r'(.+)_(\d+)\.pcm$', os.path.basename(p))
        if not m or m.group(1) not in spec.S or (want and m.group(1) not in want):
            continue
        name, take = m.group(1), int(m.group(2))
        kind = spec.S[name][2]
        x0 = A.load_raw(name, take)
        clip = int((np.abs(x0) > .999).sum())
        sp, br, mod = A.speech_score(x0, A.SR0)
        hf = A.hf_floor(x0, A.SR0)
        x = A.up48(x0)
        hpz, lpz, gr = KIND[kind]
        y, info = A.clean_take(x, A.SR, hpz, lpz, gr)
        ev = A.events(y, A.SR, -36, gap=.08)
        A.write_wav(os.path.join(CLEAN, f'{name}_{take}.wav'), y)
        r = dict(name=name, take=take, raw_s=round(len(x0) / A.SR0, 2), raw_peak=round(A.peak_db(x0), 1), clip=clip,
                 speech=round(sp, 3), speech_band=round(br, 2), speech_mod=round(mod, 2), hf_floor=round(hf, 1),
                 bed=round(info['bed'], 1), resid=round(info['resid'], 1),
                 events=[(round(a / A.SR, 3), round(b / A.SR, 3), round(pk, 1)) for a, b, pk in ev],
                 centroid=A.centroid(y, A.SR) if np.abs(y).max() > 0 else 0)
        # reasons to reject the whole take
        bad = []
        if clip > 4: bad.append('clipping')
        if sp > .08: bad.append('speech-like')   # real speech (macOS say) scores ~0.18-0.20
        if r['bed'] > -50 and r['bed'] > r['raw_peak'] - 30: bad.append('noisy bed')
        if not ev: bad.append('empty')
        r['reject'] = bad
        rep[f'{name}_{take}'] = r
        print(f"{name}_{take:<3d} raw {r['raw_s']:4.2f}s pk {r['raw_peak']:6.1f} bed {r['bed']:6.1f} hf {hf:6.1f} sp {sp:.3f}({br:.2f},{mod:.2f}) "
              f"ev {len(ev)} {[(e[0], round(e[1]-e[0], 2)) for e in r['events'][:4]]} {'REJ ' + ','.join(bad) if bad else ''}", flush=True)
    json.dump(rep, open(OUT, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
