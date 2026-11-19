"""Assemble every Falcos SFX set from the cleaned takes (art/highpeaks/sfx_raw/clean) and the synth layers,
master them and write art/highpeaks/sfx_raw/build/<stem>_<n>.wav + build/report.json.
  python build.py [stem ...]"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A
import synth as S
from audio import SR, hz

CLEAN = os.path.join(A.RAW, 'clean')
BUILD = os.path.join(A.RAW, 'build')
REP = json.load(open(os.path.join(A.RAW, 'analysis.json')))
_cache = {}


# ------------------------------------------------------------------ foley pieces
def clean(key):
    if key not in _cache:
        _cache[key] = A.read_wav(os.path.join(CLEAN, key + '.wav'))[0]
    return _cache[key]


EXCLUDE = {'keys_8'}     # by eye on the review sheet: two thin, far-apart jingles (choppy once normalised)


def takes(name):
    return sorted([k for k, r in REP.items() if r['name'] == name and not r['reject'] and k not in EXCLUDE],
                  key=lambda k: REP[k]['take'])


def _onset(x, a, b):
    """Precise onset inside event [a, b): first point within 30 dB of the event's peak, minus 4 ms."""
    d = A.envelope_db(x[a:b], SR, .002)
    i = int(np.argmax(d > d.max() - 30))
    return max(0, a + i - int(.004 * SR))


def _end_trim(seg, rel=-45):
    d = A.envelope_db(seg, SR, .005)
    on = np.nonzero(d > d.max() + rel)[0]
    return seg[:on[-1] + 1] if len(on) else seg


def tail_fade(seg, t=.09):
    """Every excerpt ends on a raised-cosine fade (over 90 ms or the last quarter): a sound still going
    where the window cuts it fades away instead of stopping dead."""
    seg = seg.copy()
    n = min(len(seg) // 4, int(t * SR))
    if n > 2:
        seg[-n:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, n)))[:, None]
    return seg


def _score(seg, full_after, ideal):
    """Higher is better: complete (decays inside the window), not speech-like, near the ideal length."""
    d = A.envelope_db(seg, SR, .01)
    end_lvl = d[-int(.01 * SR):].mean() - d.max() if len(seg) > SR // 50 else 0
    e_in = np.square(seg).sum(); e_all = np.square(full_after).sum() + 1e-20
    sp = A.speech_score(seg, SR)[0]
    s = 2.0 * (e_in / e_all) - abs(len(seg) / SR - ideal) / ideal - 8 * sp
    if end_lvl > -20:
        s -= .5
    return float(s)


def excerpts(name, maxdur, ideal=None, mode='main', min_peak_rel=-6, min_event=0.0):
    """Candidate excerpts from every good take of `name`.
    mode 'main': from the first event within min_peak_rel dB of the take's loudest, maxdur long.
    mode 'end':  the last maxdur seconds of the longest event (ends on its natural stop).
    mode 'each': every event on its own (trimmed to maxdur).
    mode 'longest': from the onset of the longest continuous event."""
    ideal = ideal or maxdur * .8
    out = []
    for k in takes(name):
        x = clean(k)
        ev = A.events(x, SR, -36, gap=.05, min_len=.02)
        if not ev:
            continue
        top = max(p for _, _, p in ev)
        if mode == 'each':
            for a, b, p in ev:
                if p < top - 12:
                    continue
                s = _onset(x, a, b)
                seg = _end_trim(x[s:min(b + int(.03 * SR), s + int(maxdur * SR))])
                out.append(dict(key=k, at=s / SR, seg=seg, score=_score(seg, x[s:b + int(.05 * SR)], ideal), peak=p))
            continue
        if mode == 'end':
            a, b, p = max(ev, key=lambda e: e[1] - e[0])
            s = max(a, b - int(maxdur * SR))
            seg = _end_trim(x[s:b + int(.03 * SR)])
            out.append(dict(key=k, at=s / SR, seg=seg, score=(b - a) / SR, peak=p))
            continue
        if mode == 'longest':          # the longest continuous event (a whoosh, not the click before it)
            a, b, p = max(ev, key=lambda e: e[1] - e[0])
            if (b - a) / SR < min_event:
                continue
        else:
            a, b, p = next(e for e in ev if e[2] >= top + min_peak_rel)
        s = _onset(x, a, b)
        seg = _end_trim(x[s:s + int(maxdur * SR)])
        out.append(dict(key=k, at=s / SR, seg=seg, score=_score(seg, x[s:s + int(2.5 * SR)], ideal), peak=p))
    for c in out:
        c['sp'] = A.speech_score(c['seg'], SR)[0]
        c['seg'] = tail_fade(c['seg'])
    return sorted([c for c in out if c['sp'] <= .08], key=lambda c: -c['score'])


def choose(cands, n=3, distinct=True):
    """Best candidate, then the most alike of the next best (duration and brightness), distinct takes."""
    if not cands:
        raise RuntimeError('no candidates')
    best = cands[0]
    cands_all = list(cands)
    feat = lambda c: (np.log(len(c['seg']) / SR + .02), np.log(A.centroid(c['seg'], SR) + 1))
    fb = feat(best)
    dmin = .6 * len(best['seg'])
    cands = [c for c in cands if len(c['seg']) >= dmin] or cands
    pool = [c for c in cands[1:10] if c['score'] > best['score'] - 1.2]
    pool.sort(key=lambda c: abs(feat(c)[0] - fb[0]) + .7 * abs(feat(c)[1] - fb[1]) - .15 * c['score'])
    pick, used = [best], {best['key']}
    for rnd in (0, 1, 2):          # 0: alike + distinct takes; 1: any length, distinct; 2: any
        src = pool + cands if rnd == 0 else (cands_all if rnd == 1 else cands_all)
        for c in src:
            if len(pick) == n:
                break
            if any(c is p for p in pick) or (rnd < 2 and c['key'] in used):
                continue
            pick.append(c); used.add(c['key'])
    return pick


def tune(seg, min_peaky=18, max_shift=1.6):
    """If the excerpt has a clear pitch, nudge it (by resampling) onto D major pentatonic."""
    f, pk = A.dominant_pitch(seg, SR)
    if pk < min_peaky:
        return seg, 0.0
    _, sh = A.penta_snap(f)
    if abs(sh) > max_shift:
        return seg, 0.0
    return A.pitch_shift_resample(seg, sh), float(sh)


# ------------------------------------------------------------------ mixing
def st(m, width=.35):
    return A.to_stereo(m, width) if m.ndim == 1 else m


def lvl(x, rel_db, ref=-24.0):
    """Scale a layer so its loudness is ref + rel_db LUFS (relative balance between layers)."""
    if np.abs(x).max() == 0:
        return x
    return x * 10 ** ((ref + rel_db - A.lufs(st(x), SR)) / 20)


def mix(layers, cap=None):
    """layers: [(signal, at_seconds, rel_db)] -> stereo sum, cut at cap seconds (with a fade)."""
    n = max(int(at * SR) + len(x) for x, at, _ in layers)
    out = np.zeros((n, 2))
    for x, at, rel in layers:
        y = lvl(st(x), rel)
        i = int(at * SR)
        out[i:i + len(y)] += y
    if cap and len(out) > cap * SR:
        out = out[:int(cap * SR)]
        nf = int(.08 * SR)
        out[-nf:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, nf)))[:, None]
    return out


def fade_in(x, t):
    n = int(t * SR); x = x.copy()
    x[:n] *= np.linspace(0, 1, n)[:, None] if x.ndim == 2 else np.linspace(0, 1, n)
    return x


def soft(x, f=6500):
    # (2026-11-13) a gentle roll-off far above where it was: every call's own cutoff is raised to at least 11 kHz
    return A.lp(x, max(f, 11000), SR, 2)


# ------------------------------------------------------------------ the sets
WIN_CHIME = {   # notes, gap, tau, bright, sub (a soft low octave under it), chime level vs foley (dB), cap s
    'h1': (['D5', 'F#5', 'A5', 'D6'], .05, .32, .5, 'D4', 0, .95),
    'h2': (['A5', 'D6', 'F#6'], .045, .26, .42, None, -1, .85),
    'h3': (['F#5', 'B5'], .05, .24, .38, None, -1, .75),
    'h4': (['D5', 'A5'], .05, .22, .35, None, -1.5, .75),
    'l1': (['A5'], 0, .18, .28, None, -2, .62),
    'l2': (['B5'], 0, .18, .28, None, -2, .62),
    'l3': (['E5'], 0, .18, .28, None, -2, .62),
    'l4': (['F#5'], 0, .18, .28, None, -2, .62),
    'l5': (['D6'], 0, .18, .28, None, -2, .62),
}
WIN_FOLEY = {   # raw name(s), excerpt max seconds, foley level (dB), extra low-pass
    'h1': (['reg_bell', 'reg_drawer'], .85, 0, 8000),
    'h2': (['keys'], .65, 0, 8000),
    'h3': (['nozzle'], .5, -1, 7500),
    'h4': (['jerry'], .6, -1, 7500),
    'l1': (['soda'], .45, -2, 6500),
    'l2': (['slushie'], .5, -3, 6000),
    'l3': (['sizzle'], .45, -5, 5000),
    'l4': (['chips'], .45, -4, 5500),
    'l5': (['pop'], .3, -1, 6500),
}
TUNED = {'reg_bell', 'reg_drawer', 'coin', 'drip', 'pop', 'jerry'}


def win_set(sym):
    notes, gap, tau, bright, sub, crel, cap = WIN_CHIME[sym]
    names, mx, frel, lpf = WIN_FOLEY[sym]
    cands = sum((excerpts(n, mx) for n in names), [])
    cands.sort(key=lambda c: -c['score'])
    out = []
    for i, c in enumerate(choose(cands, 3)):
        fol = c['seg']
        sh = 0.0
        if REP[c['key']]['name'] in TUNED:
            fol, sh = tune(fol)
        fol = soft(fol, lpf)
        ch = S.chime(notes, gap=gap * (1 + .12 * (i - 1)), dur=cap, tau=tau, bright=bright, seed=10 * i + 1)
        if sub:
            ch = S.place(ch, S.bell(hz(sub), cap, tau=tau * 1.2, bright=.15, seed=i) * .45, 0)
        # the chime enters on the foley's main hit (a few ms in), never before it
        x = mix([(fol, 0, frel), (ch, .012, crel)], cap)
        out.append((x, dict(src=c['key'], at=round(c['at'], 3), tuned_st=round(sh, 2))))
    return out


def zippo_flick():
    clicks = [c for c in excerpts('zippo', .12, .06, mode='each') if len(c['seg']) < .15 * SR]
    clicks.sort(key=lambda c: -c['peak'])
    wh = excerpts('whoomp', .55, .5, mode='longest', min_event=.5)
    out = []
    for i in range(3):
        c, w = clicks[i * 2 % len(clicks)], wh[i]
        ws = fade_in(soft(w['seg'], 3500), .04)
        t = np.arange(len(ws)) / SR
        ws = ws * np.exp(-np.maximum(0, t - .06) / .16)[:, None]      # a puff that dies away, not a held roar
        x = mix([(soft(c['seg'], 7000), 0, -1), (ws, .07, -2)], .7)
        out.append((x, dict(src=[c['key'], w['key']])))
    return out


def zippo_burn():
    wh = choose(excerpts('whoomp', 1.0, .9, mode='longest', min_event=.6), 3)
    out = []
    for i, w in enumerate(wh):
        swell = S.pad([hz('D3'), hz('A3')], .9, att=.06, rel=.5, cutoff=500, saw=.25, seed=i)
        ws = soft(w['seg'], 4000)
        t = np.arange(len(ws)) / SR
        ws = ws * np.exp(-np.maximum(0, t - .3) / .22)[:, None]      # the spread blooms, then settles away
        x = mix([(ws, 0, 0), (swell, .02, -7)], 1.05)
        out.append((x, dict(src=w['key'])))
    return out


def strokes():
    c = [s for s in excerpts('scratch', .3, .2, mode='each') if .1 * SR < len(s['seg'])]
    return sorted(c, key=lambda s: -s['score'])


def scratch():
    sk = strokes()
    out = []
    for i in range(3):
        a, b, c = sk[i], sk[(i + 3) % len(sk)], sk[(i + 6) % len(sk)]
        L = [(soft(fade_in(s['seg'][:int(.22 * SR)], .01), 6000), t, g) for s, t, g in ((a, 0, 0), (b, .19, -1.5), (c, .38, -1))]
        x = mix(L, .64)
        out.append((x, dict(src=[a['key'], b['key'], c['key']])))
    return out


def scratch_reveal():
    out = []
    starts = [['A5', 'B5', 'D6', 'E6', 'F#6', 'A6'], ['B5', 'D6', 'E6', 'F#6', 'A6', 'B6'], ['A5', 'D6', 'E6', 'F#6', 'A6', 'D7']]
    for i, notes in enumerate(starts):
        sp = np.zeros(int(.9 * SR))
        for j, n in enumerate(notes):
            S.place(sp, S.bell(hz(n), .5, att=.004, tau=.16, bright=.25, warm=False, seed=i * 10 + j), j * .045, .9 ** j)
        pad = S.pad([hz('D5'), hz('A5'), hz('F#6')], .75, att=.12, rel=.4, cutoff=2600, saw=.2, seed=i)
        x = mix([(sp, 0, 0), (pad, 0, -9)], .85)
        out.append((x, dict(src='synth')))
    return out


def gold_scratch():
    sk = strokes()
    out = []
    for i in range(3):
        rng = np.random.default_rng(40 + i)
        sh = np.zeros(int(1.2 * SR))
        pool = ['D6', 'E6', 'F#6', 'A6', 'B6', 'D7']
        for j in range(9):
            t = .12 + j * .085 + rng.uniform(-.015, .015)
            S.place(sh, S.glass(hz(pool[rng.integers(len(pool))]), .35, tau=.1, seed=j), t, .55 + .45 * rng.random())
        pad = S.pad([hz('D5'), hz('A5'), hz('F#6')], 1.05, att=.25, rel=.45, cutoff=3000, saw=.25, seed=i)
        a, b = sk[i], sk[(i + 4) % len(sk)]
        x = mix([(soft(a['seg'][:int(.22 * SR)], 6000), 0, 0), (soft(b['seg'][:int(.22 * SR)], 6000), .17, -1.5),
                 (sh, 0, -2), (pad, .1, -6)], 1.25)
        out.append((x, dict(src=[a['key'], b['key']])))
    return out


def pump_roll():
    cs = excerpts('counter', 1.2, mode='end')
    cs = [c for c in cs if len(c['seg']) > 1.0 * SR][:3]
    out = []
    for i, c in enumerate(cs):
        rise = S.sweep(hz('D4'), hz('A4'), 1.15, att=.3, tau=3)
        x = mix([(fade_in(soft(c['seg'], 7000), .08), 0, 0), (rise, 0, -10)], 1.25)
        out.append((x, dict(src=c['key'], at=round(c['at'], 3))))
    return out


PUMP = {   # notes, gap, tau, pad notes, dur
    'regular': (['A4', 'D5'], .09, .28, None, .75),
    'plus': (['D5', 'F#5', 'A5'], .08, .3, None, .85),
    'premium': (['D5', 'F#5', 'A5', 'D6'], .075, .34, ['D4', 'A4'], 1.05),
    'fulltank': (['A4', 'D5', 'F#5', 'A5', 'D6', 'F#6'], .068, .4, ['D4', 'F#4', 'A4', 'D5'], 1.5),
}


def pump(grade):
    notes, gap, tau, padn, dur = PUMP[grade]
    out = []
    for i in range(3):
        g = gap * (1 + .08 * (i - 1))
        ch = S.chime(notes, gap=g, dur=dur, tau=tau, bright=.45, gains=[1] * len(notes), seed=100 + i * 7)
        L = [(ch, 0, 0)]
        if padn:
            end = g * (len(notes) - 1)
            L.append((S.pad([hz(n) for n in padn], dur - end, att=.1, rel=.45, cutoff=1500 if grade == 'premium' else 2200,
                            saw=.45 if grade == 'premium' else .6, seed=i), end, -6 if grade == 'premium' else -3))
            L.append((S.bell(hz('D3'), dur - end, tau=.6, bright=.1, seed=i), end, -8))
        if grade == 'fulltank':
            sp = np.zeros(int(.6 * SR))
            for j, n in enumerate(['A6', 'B6', 'D7']):
                S.place(sp, S.glass(hz(n), .3, tau=.12, seed=j + i), j * .06)
            L.append((sp, g * len(notes) + .05, -10))
        out.append((mix(L, dur), dict(src='synth')))
    return out


def mult_double():
    out = []
    for i, (a, b) in enumerate([('A5', 'D6'), ('B5', 'E6'), ('D6', 'F#6')]):
        x = S.blip_up(a, b, dur=.15, glide=.03, tau=.045, seed=i)
        out.append((mix([(x, 0, 0)]), dict(src='synth')))
    return out


def burn_clear():
    bs = choose(excerpts('burn', .6, .5), 3)
    out = []
    for i, b in enumerate(bs):
        poof = S.soft_noise(.3, 150, 800, att=.015, tau=.07, seed=i)
        x = mix([(soft(b['seg'], 5500), 0, 0), (poof, 0, -6)], .65)
        out.append((x, dict(src=b['key'])))
    return out


def drop_land():
    ds = [c for c in excerpts('drip', .25, .18, mode='each')]
    ds = choose(ds, 3) if ds else []
    out = []
    for i, (d, n) in enumerate(zip(ds, ['F#6', 'A6', 'B6'])):
        g = S.glass(hz(n), .3, tau=.075, seed=i)
        seg, sh = tune(d['seg'])
        x = mix([(soft(seg, 7500), 0, -3), (g, .004, 0)], .32)
        out.append((x, dict(src=d['key'], tuned_st=round(sh, 2))))
    return out


def drop_collect():
    ss = choose(excerpts('suck', .6, .55, mode='longest', min_event=.4), 3)
    out = []
    for i, s in enumerate(ss):
        seg = s['seg'].copy()
        nf = int(.15 * SR)
        seg[-nf:] *= np.linspace(1, 0, nf)[:, None] ** 1.5      # the suck hands over to the gloop
        gl = S.sweep(700, 250, .1, att=.006, tau=.05)
        t_end = len(seg) / SR
        x = mix([(fade_in(soft(seg, 5000), .02), 0, 0), (gl, max(.1, t_end - .06), -3)], .75)
        out.append((x, dict(src=s['key'])))
    return out


def clicks():
    c = [x for n in ('dial_click', 'ratchet') for x in excerpts(n, .08, .05, mode='each') if len(x['seg']) < .1 * SR]
    return sorted(c, key=lambda c: -c['peak'])


def gauge_refill():
    ck = sorted(clicks()[:12], key=lambda c: A.centroid(c['seg'], SR))   # neighbours in brightness = alike clicks
    out = []
    for i in range(3):
        L = []
        for j, n in enumerate(['D5', 'F#5', 'A5']):
            c = ck[(i * 3 + j) % len(ck)]
            L.append((S.norm(soft(c['seg'], 6500), .5), j * .13, -4))
            L.append((S.bell(hz(n), .4, tau=.13, bright=.3, seed=i * 3 + j), j * .13 + .004, -1))
        out.append((mix(L, .75), dict(src=[ck[(i * 3 + j) % len(ck)]['key'] for j in range(3)])))
    return out


def gauge_tick():
    ck = clicks()
    out = []
    for i in range(3):
        c = ck[(i + 1) % len(ck)]
        x = mix([(soft(c['seg'], 6000), 0, -3), (S.bell(hz('A4'), .35, tau=.1, bright=.2, seed=i), .004, 0)], .36)
        out.append((x, dict(src=c['key'])))
    return out


def token_land():
    cs = choose(excerpts('coin', .6, .5), 3)
    out = []
    for i, c in enumerate(cs):
        seg, sh = tune(c['seg'])
        ch = S.chime(['A5', 'D6'], gap=.03, dur=.7, tau=.26, bright=.4, seed=i)
        h = S.hum(hz('A2'), .6, att=.04, rel=.35)
        x = mix([(soft(seg, 7000), 0, 0), (ch, .01, -1), (S.norm(h, .6), 0, -12)], .72)
        out.append((x, dict(src=c['key'], tuned_st=round(sh, 2))))
    return out


def midnight_land():
    ts = choose(excerpts('thud', .5, .4), 3)
    out = []
    for i, t in enumerate(ts):
        pad = S.pad([hz('B2'), hz('F#3'), hz('D4')], 1.0, att=.05, rel=.6, cutoff=800, saw=.3, seed=i)
        low = S.bell(hz('B3'), 1.0, tau=.45, bright=.15, seed=i)
        top = S.glass(hz('F#5'), .6, att=.02, tau=.25, seed=i)
        x = mix([(soft(t['seg'], 3000), 0, 0), (pad, 0, -3), (low, .01, -6), (top, .12, -16)], 1.05)
        out.append((x, dict(src=t['key'])))
    return out


def bonus_trigger():
    out = []
    for i in range(3):
        g = .08 * (1 + .06 * (i - 1))
        arp = S.chime(['D5', 'F#5', 'A5', 'D6'], gap=g, dur=1.4, tau=.4, bright=.5, gains=[1, 1, 1, 1.1], seed=200 + i)
        t1 = g * 3
        brass = S.pad([hz(n) for n in ('D4', 'F#4', 'A4', 'D5')], 1.5 - t1, att=.09, rel=.5, cutoff=2200, saw=.6, seed=i)
        sub = S.bell(hz('D3'), 1.2, tau=.55, bright=.1, seed=i)
        sp = np.zeros(int(.7 * SR))
        for j, n in enumerate(['F#6', 'A6', 'D7']):
            S.place(sp, S.glass(hz(n), .35, tau=.14, seed=j + 3 * i), j * .07)
        x = mix([(arp, 0, 0), (brass, t1, -2), (sub, t1, -7), (sp, t1 + .12, -9)], 1.5)
        out.append((x, dict(src='synth')))
    return out


# stem -> (builder, target LUFS, fade-out s, purpose)
SETS = {f'sfx_win_{s}': (lambda s=s: win_set(s), -26, .07, p) for s, p in {
    'h1': 'H1 Cash Drawer cluster win: register bell + drawer, rich D-major chime (D5 F#5 A5 D6 + low D4)',
    'h2': 'H2 Gold Key cluster win: car keys jingle + 3-note chime (A5 D6 F#6)',
    'h3': 'H3 Pump Nozzle cluster win: nozzle click/gurgle + 2-note chime (F#5 B5)',
    'h4': 'H4 Jerry Can cluster win: metal can tap/slosh + 2-note chime (D5 A5)',
    'l1': 'L1 Energy Drink cluster win: can crack + fizz + single note A5',
    'l2': 'L2 Slushie cluster win: soft ice rattle + single note B5',
    'l3': 'L3 Hot Dog cluster win: small grill sizzle + single note E5',
    'l4': 'L4 Chips cluster win: chip bag crinkle + single note F#5',
    'l5': 'L5 Donut cluster win: soft bouncy pop + single note D6',
}.items()}
SETS.update({
    'sfx_zippo_flick': (zippo_flick, -24, .06, 'Zippo lands/activates: lid click + soft flame whoosh'),
    'sfx_zippo_burn': (zippo_burn, -24, .08, 'Zippo 3x3 burn: warm low whoomp of fire spreading'),
    'sfx_scratch': (scratch, -24, .05, 'Scratch Ticket scratching (3 short strokes, ~0.6 s)'),
    'sfx_scratch_reveal': (scratch_reveal, -24, .08, 'Scratch Ticket reveal: gentle pentatonic sparkle'),
    'sfx_gold_scratch': (gold_scratch, -24, .08, 'Gold Scratch Ticket: scratch strokes + golden shimmer'),
    'sfx_pump_roll': (pump_roll, -24, .06, 'Gas Pump grade roll: mechanical counter winding and stopping (~1.2 s)'),
    'sfx_pump_regular': (lambda: pump('regular'), -25, .07, 'Gas Pump grade REGULAR (x2/x4): 2-note bell'),
    'sfx_pump_plus': (lambda: pump('plus'), -24.5, .07, 'Gas Pump grade PLUS (x8/x16): 3-note bell'),
    'sfx_pump_premium': (lambda: pump('premium'), -24, .08, 'Gas Pump grade PREMIUM (x32/x64): 4-note arpeggio + soft pad'),
    'sfx_pump_fulltank': (lambda: pump('fulltank'), -23, .08, 'Gas Pump FULL TANK: arpeggio, held brass-like chord, sparkle'),
    'sfx_mult_double': (mult_double, -28, .03, 'Cell multiplier doubles: tiny soft tick-up (many overlap; mixed lower)'),
    'sfx_burn_clear': (burn_clear, -24, .06, 'Symbols burning away: soft crackle-poof'),
    'sfx_drop_land': (drop_land, -24, .04, 'Fuel Drop lands: glassy plink'),
    'sfx_drop_collect': (drop_collect, -24, .05, 'Fuel Drops collected: soft whoosh ending in a gloop'),
    'sfx_gauge_refill': (gauge_refill, -24, .06, 'Fuel gauge refills to 3 bars: three soft ratchet clicks rising D5 F#5 A5'),
    'sfx_gauge_tick': (gauge_tick, -25, .04, 'Fuel gauge loses a bar: soft click + low A4'),
    'sfx_token_land': (token_land, -24, .07, 'FALCOS Token lands: soft coin + chime + faint neon hum (A2)'),
    'sfx_midnight_land': (midnight_land, -25, .08, 'Midnight Token lands: low dark thud + B-minor pad (inside the key)'),
    'sfx_bonus_trigger': (bonus_trigger, -22, .08, 'Bonus triggered: tasteful 1.5 s fanfare in D'),
})



# ================================================================== the original game's sounds, remade (2026-11-10)
# The HUD, the win presentation, the board foley and the FALCOS ident still played the sounds of the game
# Falcos was forked from. Same brief as the sets above; same key. Pure UI ticks, chimes, whooshes and loops are
# synthesised here (no cost); the board foley and a few HUD moments use generated takes (spec.py: reg_key ...
# blinker). The file names and take counts are the ones frontend/index.html already plays (SFX / SFX_SETS).
SINGLES = set()        # stems shipped as one file, <stem>.wav (index.html's SFX), not <stem>_<n>.wav
LOOPS = set()          # stems looped by the game (loopSfx / loopHold): mastered without trim or fades


def ends(x, t=.025):
    """A raised-cosine fade over a synth piece's last t s, so a layer that stops inside a file never clicks."""
    x = np.array(x, dtype=float)
    n = min(len(x) // 3, int(t * SR))
    if n > 2:
        f = .5 + .5 * np.cos(np.linspace(0, np.pi, n))
        x[-n:] *= f[:, None] if x.ndim == 2 else f
    return x


def gl(f, dur=.35, **kw):
    return ends(S.glass(f, dur, **kw))


def bl(f, dur=1.2, **kw):
    return ends(S.bell(f, dur, **kw), .04)


def chime_(notes, gap=.045, dur=1.1, tau=.4, bright=.45, gains=None, warm=True, seed=0):
    """S.chime, with every bell faded out at its own end (S.chime's bells stop dead after `dur`)."""
    out = np.zeros(int((dur + gap * len(notes)) * SR))
    for i, n in enumerate(notes):
        g = gains[i] if gains else 1.0 / (1 + .15 * i)
        S.place(out, bl(hz(n), dur, tau=tau, bright=bright, warm=warm, seed=seed + i), i * gap, g)
    return out


def svf_band(x, fc, q=.8):
    """Band-pass x (mono) through a TPT state-variable filter whose centre follows fc (Hz, one per sample)."""
    g = np.tan(np.pi * np.clip(fc, 20, SR * .45) / SR)
    k = 1.0 / q
    a1 = 1 / (1 + g * (g + k)); a2 = g * a1; a3 = g * a2
    out = np.empty_like(x)
    ic1 = ic2 = 0.0
    for i in range(len(x)):
        v3 = x[i] - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1 = 2 * v1 - ic1; ic2 = 2 * v2 - ic2
        out[i] = v1
    return out


def whoosh(dur, f0, f1, peak=.5, q=.9, lp=3500, seed=0, curve=1.5):
    """Soft air whoosh: noise through a band-pass sweeping f0 -> f1 (exponentially), swelling to its
    loudest at `peak` (fraction of dur) and away again; low-passed so it never hisses."""
    n = int(dur * SR)
    t = np.arange(n) / n
    rng = np.random.default_rng(seed)
    y = svf_band(rng.standard_normal(n), f0 * (f1 / f0) ** t, q)
    pk = max(.02, min(.98, peak))
    e = np.where(t < pk, .5 - .5 * np.cos(np.pi * t / pk), .5 + .5 * np.cos(np.pi * (t - pk) / (1 - pk))) ** curve
    return A.lp(y * e, lp, SR, 4)


def pan(m, p0=0.0, p1=None):
    """Mono -> stereo, equal-power pan moving from p0 to p1 (-1 left .. 1 right)."""
    p1 = p0 if p1 is None else p1
    p = np.linspace(p0, p1, len(m))
    a = (p + 1) * np.pi / 4
    return np.stack([m * np.cos(a), m * np.sin(a)], 1)


def thump(f0, f1, dur, tau=.12, glide=.05, att=.003):
    """Soft low thump: a sine falling from f0 to f1 (time constant glide) under a soft attack."""
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t / glide)
    return ends(np.sin(2 * np.pi * np.cumsum(f) / SR) * S.adsr(len(t), att, tau), min(.03, dur / 4))


def sparkles(dur, notes, n, t0=0.0, t1=None, tau=(.07, .11), gain=(.4, 1.0), width=.6, seed=0):
    """A scatter of soft glass plinks (stereo, each at its own place across the field)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((int(dur * SR), 2))
    t1 = dur - .25 if t1 is None else t1
    times = np.sort(rng.uniform(t0, t1, n))
    for j, tt in enumerate(times):
        g = gl(hz(notes[rng.integers(len(notes))]), .4, tau=rng.uniform(*tau), seed=seed * 31 + j)
        y = pan(g * rng.uniform(*gain), rng.uniform(-width, width))
        i = int(tt * SR); m = min(len(y), len(out) - i)
        out[i:i + m] += y[:m]
    return out


def notes_at(seq, dur, tau=.3, bright=.35, warm=True, seed=0, gains=None):
    """Bells at given times: seq = [(note, seconds, gain)]."""
    out = np.zeros(int(dur * SR))
    for j, (n, at, g) in enumerate(seq):
        S.place(out, bl(hz(n), dur - at, tau=tau, bright=bright, warm=warm, seed=seed + j), at, g)
    return out


def loop_freq(f, n):
    """The frequency nearest f that fits a whole number of cycles into n samples (a seamless loop)."""
    return max(1, round(f * n / SR)) * SR / n


def circ_noise(n, lo, hi, seed=0, tilt=-3.0):
    """Exactly periodic band-limited noise (n samples): shaped in the FFT domain, so its end runs on into its start."""
    rng = np.random.default_rng(seed)
    F = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    w = np.clip((f - lo * .7) / (lo * .3), 0, 1) * np.clip((hi * 1.3 - f) / (hi * .3), 0, 1)
    w = w * (np.maximum(f, lo) / lo) ** (tilt / 6.02)          # tilt dB/oct: darker as it goes up
    y = np.fft.irfft(F * w, n)
    return y / (np.abs(y).max() + 1e-12)


def master_loop(x, sr, target, ceil_db=-6.5):
    """A loop: the warm shelf applied around the loop (three copies, the middle kept), gain to the target
    loudness, and if that peaks over the ceiling a plain gain down - no trim, no fades, no limiter, so the
    last sample still runs on into the first."""
    n = len(x)
    y = A.shelf_soften(np.concatenate([x, x, x]), sr, 6000, -3)[n:2 * n]
    y = y * 10 ** ((target - A.lufs(np.concatenate([y, y, y]), sr)) / 20)
    pk = np.abs(y).max()
    if pk > 10 ** (ceil_db / 20):
        y *= 10 ** (ceil_db / 20) / pk
    return y


def foley(name, maxdur, n, ideal=None, mode='each', lpf=6500, tune_it=False, min_s=0.0, max_s=None):
    """n alike excerpts of a generated take set (cleaned), low-passed, optionally nudged onto the scale."""
    cands = [c for c in excerpts(name, maxdur, ideal, mode=mode) if len(c['seg']) >= min_s * SR
             and (max_s is None or len(c['seg']) <= max_s * SR)] or excerpts(name, maxdur, ideal, mode=mode)
    out = []
    for c in choose(cands, n):
        seg, sh = tune(c['seg']) if tune_it else (c['seg'], 0.0)
        out.append((soft(seg, lpf), dict(src=c['key'], at=round(c['at'], 3), tuned_st=round(sh, 2))))
    return out


def around_peak(name, pre, post, n):
    """The loudest moment of each take's longest event, from `pre` s before it to `post` s after (a pass-by)."""
    out = []
    for k in takes(name):
        x = clean(k)
        ev = A.events(x, SR, -36, gap=.1, min_len=.1)
        if not ev:
            continue
        a, b, _ = max(ev, key=lambda e: e[1] - e[0])
        d = A.envelope_db(x[a:b], SR, .03)
        pk = a + int(np.argmax(d))
        s0, s1 = max(0, pk - int(pre * SR)), min(len(x), pk + int(post * SR))
        seg = x[s0:s1]
        out.append(dict(key=k, at=s0 / SR, seg=seg, pk=(pk - s0) / SR, score=(b - a) / SR - abs(pk - s0 - pre * SR) / SR,
                        sp=A.speech_score(seg, SR)[0]))
    out = sorted([c for c in out if c['sp'] <= .08], key=lambda c: -c['score'])
    return out[:n]


# ---- board foley (landFoley: what each symbol is made of, as it lands; quiet, a patter, never a pile-up)
def land(name, maxdur, n, lpf, tune_it=False, body=None, body_rel=-8, min_s=0.0):
    out = []
    for i, (seg, info) in enumerate(foley(name, maxdur, n, maxdur * .7, 'each', lpf, tune_it, min_s=min_s)):
        L = [(seg, 0, 0)]
        if body:
            L.append((body(i), .002, body_rel))
        out.append((mix(L, maxdur + .03), info))
    return out


def reel_stop():
    return land('rubber', .22, 3, 4500, body=lambda i: thump(150 + 12 * i, 75, .18, tau=.05, glide=.025), body_rel=-6)


def land_brick():
    # the FALCOS letters landing in the ident, one after another a step higher (rates .82 - 1.17)
    return land('rubber', .3, 3, 4500, min_s=.06,
                body=lambda i: bl(hz("D4"), .32, tau=.09, bright=.15, seed=i) + .6 * thump(140, 70, .32, tau=.07, glide=.03),
                body_rel=-4)


# ---- the HUD
def ui_click():
    return [(mix([(s, 0, 0)], .1), info) for s, info in foley('dash_btn', .075, 3, .05, 'each', 6000, max_s=.09)]


def ui_hover():
    out = []
    for i, n in enumerate(['A6', 'F#6']):
        g = gl(hz(n), .04, att=.0015, tau=.009, seed=i)
        tk = S.tick(f=1650 + 120 * i, dur=.035, tau=.004, seed=i)
        out.append((soft(mix([(g, 0, 0), (tk, 0, -8)], .04), 5500), dict(src='synth')))
    return out


def slider_tick():
    out = []
    for i, n in enumerate(['D6', 'E6']):
        tk = S.tick(f=1500 + 180 * i, dur=.05, tau=.0055, seed=10 + i)
        g = gl(hz(n), .05, att=.001, tau=.012, seed=i)
        out.append((soft(mix([(tk, 0, 0), (g, 0, -6)], .05), 5500), dict(src='synth')))
    return out


def swish(rising, durs):
    out = []
    for i, d in enumerate(durs):
        f0, f1, pk = (260, 1500, .72) if rising else (1500, 240, .28)
        w = whoosh(d, f0 * (1 + .08 * i), f1, peak=pk, q=.85, lp=3000, seed=40 + i + 10 * rising)
        out.append((mix([(pan(w, -.25, .2) if rising else pan(w, .2, -.25), 0, 0)], d), dict(src='synth')))
    return out


def fs_tick():
    out = []
    for i, ((seg, info), n) in enumerate(zip(foley('reg_key', .07, 2, .05, 'each', 5500, max_s=.09), ['A5', 'B5'])):
        g = gl(hz(n), .12, att=.002, tau=.03, seed=i)
        out.append((mix([(seg, 0, 0), (g, .004, -5)], .13), info))
    return out


def buy_confirm():
    (cl, info), = foley('nozzle_set', .35, 1, .25, 'each', 4500)
    arp = chime_(['D5', 'F#5', 'A5', 'D6'], gap=.075, dur=1.25, tau=.36, bright=.42, gains=[1, 1, 1, 1.05], seed=500)
    pad = S.pad([hz('D4'), hz('A4'), hz('F#5')], 1.05, att=.12, rel=.55, cutoff=1800, saw=.4, seed=5)
    sp = sparkles(.6, ['A6', 'B6', 'D7'], 3, 0, .2, seed=5)
    return [(mix([(cl, 0, -1), (arp, .03, 0), (pad, .25, -8), (sp, .33, -12)], 1.4), info)]


def bet():
    # the bet buttons, the bonus shop's arm press, the bonus intro's count - and, at half speed, every reel's
    # landing thud (boardThud): a soft register key clack with a little body
    (k, info), = foley('reg_key', .085, 1, .07, 'each', 5500, min_s=.05)       # one clack (some takes clack twice)
    return [(mix([(k, 0, 0), (thump(260, 140, .3, tau=.07, glide=.02), .002, -8)], .3), info)]


def toggle():
    (k, info), = foley('toggle_sw', .14, 1, .1, 'each', 6000)
    return [(mix([(k, 0, 0), (gl(hz('E6'), .28, tau=.055), .006, -9)], .3), info)]


def menu(opening):
    (k, info), = foley('dash_btn', .075, 1, .05, 'each', 6000, max_s=.09)
    seq = [('A5', .02, 1.0), ('D6', .11, .9)] if opening else [('D6', .02, 1.0), ('A5', .13, .9)]
    ch = notes_at(seq, .8 if opening else .9, tau=.17 if opening else .22, bright=.3, seed=60 + opening)
    return [(mix([(k, 0, 0), (ch, 0, -1)], .66 if opening else .8), info)]


def skip():
    w = whoosh(.32, 1800, 420, peak=.18, q=.9, lp=3200, seed=7)
    (k, info), = foley('dash_btn', .075, 1, .05, 'each', 6000, max_s=.09)
    return [(mix([(k, 0, -3), (pan(w, .25, -.25), .01, 0)], .36), info)]


def auto(starting):
    ticks = [c for c in excerpts('blinker', .09, .05, mode='each') if len(c['seg']) < .1 * SR]
    ticks.sort(key=lambda c: -c['peak'])
    seq = [('D5', .0, 1.0), ('A5', .24, .95)] if starting else [('A5', .0, 1.0), ('D5', .2, .95)]
    L = [(notes_at(seq, .78 if starting else .72, tau=.2, bright=.32, seed=70 + starting), .01, 0)]
    use = ticks[:2] if starting else ticks[2:3] or ticks[:1]
    for j, c in enumerate(use):
        L.append((soft(c['seg'], 5000), j * .24, -5))
    return [(mix(L, .79 if starting else .74), dict(src=[c['key'] for c in use]))]


def hover_loop():
    # the Bonus button's hum while a mouse rests on it: a faint neon tube on A2 and its in-key harmonics
    # (A3, E4, A4), breathing slowly, with a soft A4/E5 halo; every partial fits the 4 s loop exactly
    n = 4 * SR
    t = np.arange(n) / SR
    f = lambda v: loop_freq(v, n)
    s = (np.sin(2 * np.pi * f(110) * t) + .5 * np.sin(2 * np.pi * f(110.25) * t + 1) + .32 * np.sin(2 * np.pi * f(220) * t + .4)
         + .12 * np.sin(2 * np.pi * f(330) * t + 2) + .06 * np.sin(2 * np.pi * f(440) * t + 3))
    s *= 1 + .1 * np.sin(2 * np.pi * f(.5) * t)                      # a slow breath (two per loop)
    halo = (np.sin(2 * np.pi * f(440) * t) + .7 * np.sin(2 * np.pi * f(659.25) * t + 1.3)) * (.6 + .4 * np.sin(2 * np.pi * f(.25) * t))
    air = circ_noise(n, 300, 1400, seed=3) * .5 * (.8 + .2 * np.sin(2 * np.pi * f(.75) * t))
    x = np.stack([s + .08 * halo + .05 * air, s + .08 * np.roll(halo, 960) + .05 * np.roll(air, 4800)], 1)
    return [(x, dict(src='synth'))]


def reels():
    # under the whole reveal, its pitch following the reels' speed (rate .55 - 1.5): a soft rolling whir -
    # tyres on the forecourt, a pump motor - with a gentle 'rolling' pulse; exactly periodic (0.68 s)
    n = int(.68 * SR)
    t = np.arange(n) / SR
    f = lambda v: loop_freq(v, n)
    roll = circ_noise(n, 180, 1500, seed=11, tilt=-4)
    pulse = .75 + .25 * np.sin(2 * np.pi * f(11.8) * t) ** 2
    hum = np.sin(2 * np.pi * f(hz('D3')) * t) + .35 * np.sin(2 * np.pi * f(hz('A3')) * t + .7) + .2 * np.sin(2 * np.pi * f(hz('D4')) * t + 2)
    flut = 1 + .15 * np.sin(2 * np.pi * f(5.9) * t)
    m = roll * pulse * .9 + hum * flut * .22
    x = np.stack([m, .8 * m + .2 * np.roll(roll, 2400) * pulse], 1)
    return [(x, dict(src='synth'))]


def money_tick():
    # the counting figure's ticker (the win screen, the balance, the bonus's running win; rate .7 - 1.95):
    # an old pump's number wheels ticking evenly, two wheels a hair apart in pitch, and a tiny bell on every
    # tenth tick (the pump's ding per gallon); 30 ticks in 2.7 s, evenly spaced, so it loops seamlessly
    n = int(2.7 * SR)
    N = 30
    x = np.zeros((n, 2))
    rng = np.random.default_rng(21)
    ck = sorted(clicks()[:10], key=lambda c: A.centroid(c['seg'], SR))[2:6]
    for j in range(N):
        at = j * n // N
        c = ck[j % len(ck)]['seg']
        c = A.lp(c, 4000, SR, 2) / (np.abs(c).max() + 1e-12) * (.55 + .1 * rng.random())
        tk = S.tick(f=1900 if j % 2 else 2150, dur=.03, tau=.004, seed=j) * .25
        y = st(c) + st(np.pad(tk, (0, max(0, len(c) - len(tk))))[:len(c)] if len(tk) < len(c) else tk[:len(c)])
        if j % 10 == 0:
            b = bl(hz('A5'), .25, tau=.07, bright=.25, seed=j) * .22
            y2 = np.zeros((max(len(y), len(b)), 2)); y2[:len(y)] += y; y2[:len(b)] += st(b); y = y2
        idx = (at + np.arange(len(y))) % n          # what runs past the end wraps round to the start
        x[idx] += y
    return [(x, dict(src=[c['key'] for c in ck]))]


# ---- the win presentation (winFxSound, placeWinChip, flyWinToHud): many layers on one cluster, all soft
def line():
    # the shared cluster note under each symbol's own chime: a low, warm D-major pluck
    ch = chime_(['D4', 'A4'], gap=.018, dur=.92, tau=.28, bright=.3, seed=80)
    sub = bl(hz('D3'), .92, tau=.32, bright=.08, seed=81)
    sw = S.pad([hz('D4'), hz('A4'), hz('F#5')], .6, att=.035, rel=.45, cutoff=1100, saw=.4, seed=8)
    return [(mix([(ch, 0, 0), (sub, 0, -6), (sw, 0, -9)], .92), dict(src='synth'))]


def glow_pulse():
    out = []
    for i, (a, b) in enumerate([('D4', 'A4'), ('A3', 'F#4')]):
        pd = S.pad([hz(a), hz(b), 2 * hz(a)], .95, att=.26, rel=.6, cutoff=1300, saw=.35, seed=90 + i)
        hm = S.hum(hz('A2'), .95, att=.25, rel=.55)
        top = gl(hz('A5' if i == 0 else 'F#5'), .6, att=.03, tau=.22, seed=i)
        out.append((mix([(pd, 0, 0), (S.norm(hm, .6), 0, -12), (top, .2, -12)], .95), dict(src='synth')))
    return out


def shine():
    out = []
    for i, (n1, n2) in enumerate([('F#6', 'A6'), ('A6', 'D7')]):
        w = whoosh(.42, 900, 3200, peak=.75, q=1.1, lp=4500, seed=100 + i)
        tg = np.zeros(int(.55 * SR))
        S.place(tg, gl(hz(n1), .25, tau=.07, seed=i), .36)
        S.place(tg, gl(hz(n2), .2, tau=.06, seed=i + 5), .44, .8)
        out.append((mix([(pan(w, -.5, .5), 0, 0), (pan(tg, .3), 0, -2)], .55), dict(src='synth')))
    return out


def sparkle():
    out = []
    for i, d in enumerate([.75, .84, .9]):
        sp = sparkles(d, ['D6', 'E6', 'F#6', 'A6', 'B6', 'D7'], 7 + i, 0, d - .3, seed=110 + i)
        out.append((soft(mix([(sp, 0, 0)], d), 6500), dict(src='synth')))
    return out


GLINT_HZ = hz('D6') / .92   # winFxSound plays it at GLINT_SCALE * .92: the run climbs D6 E6 F#6 G6 A6 B6


def glint():
    out = []
    for i in range(4):
        g = gl(GLINT_HZ, .8, att=.002 + .001 * i, tau=.17 + .015 * i, seed=120 + i)
        b = bl(GLINT_HZ, .8, att=.003, tau=.2, bright=.18 + .05 * i, warm=False, seed=124 + i)
        out.append((soft(mix([(g, 0, 0), (b, 0, -4 - i)], .8), 6500), dict(src='synth')))
    return out


def count_tick():
    out = []
    for i, f in enumerate([1800, 2050, 2300]):
        tk = S.tick(f=f, dur=.05, tau=.0055, seed=130 + i)
        body = thump(700, 520, .05, tau=.008, glide=.01, att=.0008)
        out.append((soft(mix([(tk, 0, 0), (body, 0, -6)], .05), 5500), dict(src='synth')))
    return out


def count_end():
    # the figure lands: the register's ka-chunk and one soft bell
    cs = foley('reg_drawer', .45, 1, .35, 'main', 5000, tune_it=True)
    seg, info = cs[0]
    bell = notes_at([('A5', 0, 1.0), ('D5', .012, .7)], 1.6, tau=.42, bright=.38, seed=140)
    low = bl(hz('D4'), 1.4, tau=.4, bright=.1, seed=141)
    return [(mix([(seg, 0, 0), (bell, .03, -1), (low, .03, -9)], 1.75), info)]


def mult_slam():
    out = []
    for i, (seg, info) in enumerate(foley('stamp', .3, 3, .22, 'each', 4000)):
        th = thump(hz('A2') * 2, hz('D2'), .38, tau=.1, glide=.03)
        tone = bl(hz('D3'), .4, tau=.12, bright=.12, seed=150 + i)
        out.append((mix([(seg, 0, 0), (th, .002, -3), (tone, .004, -8)], .38 + .03 * (i == 0)), info))
    return out


def count_whoosh():
    out = []
    for i in range(2):
        w = whoosh(1.4, 240 + 30 * i, 1600, peak=.82, q=.9, lp=3400, seed=160 + i)
        sw = ends(S.sweep(hz('D4'), hz('D5'), 1.35, att=.5, tau=4) * np.linspace(.4, 1, int(1.35 * SR)), .12)
        out.append((mix([(pan(w, -.2, .2), 0, 0), (sw, 0, -13)], 1.4), dict(src='synth')))
    return out


def float_away():
    out = []
    for i in range(2):
        w = whoosh(1.7, 1300, 420, peak=.42 + .08 * i, q=.8, lp=3200, seed=170 + i)
        tr = np.zeros(int(1.8 * SR))
        for j, (n, at) in enumerate([('A6', .18), ('F#6', .4), ('D6', .64)] if i == 0 else [('B6', .2), ('A6', .44), ('E6', .7)]):
            S.place(tr, gl(hz(n), .5, tau=.16, seed=j + 3 * i), at, .9 ** j)
        out.append((mix([(pan(w, .25, -.1), 0, 0), (pan(tr, -.2, .2), 0, -9)], 1.8), dict(src='synth')))
    return out


def win_text():
    bp = ends(S.blip_up('D5', 'A5', dur=.3, glide=.04, tau=.07), .05)
    g = gl(hz('D6'), .8, tau=.2)
    tail = bl(hz('A5'), .8, tau=.25, bright=.3, seed=180)
    hm = S.norm(S.hum(hz('A2'), .7, att=.06, rel=.45), .6)
    return [(mix([(bp, 0, 0), (g, .05, -3), (tail, .06, -6), (hm, 0, -14)], .87), dict(src='synth'))]


def pop():
    # one icon popping off the board (many in a row, at rates .8 - 1.35): a soft round boop and a puff of air
    (seg, info), = foley('pop', .25, 1, .18, 'each', 6000, tune_it=True)
    poof = S.soft_noise(.7, 180, 1100, att=.02, tau=.16, seed=3)
    air = gl(hz('D6'), .5, att=.02, tau=.12, seed=3)          # a faint in-key glint as it goes
    return [(mix([(seg, 0, 0), (poof, .01, -10), (air, .04, -18)], .66), info)]


# ---- feature and round moments
def spin():
    # every spin's start: the pump handle's clunk (generated, its first 0.15 s), then the pump motor spinning up -
    # a soft low tone rising onto A3 with its gentle harmonics (synthesised: the take's own whir is a 1-2 kHz whine) -
    # a breath of air, and a soft D4-A4 rise
    cs = loudest_hit('pump_start', .16, 6)
    c = next((c for c in cs if c['key'] == 'pump_start_4'), cs[0])      # a clean, low clunk at 1.44 s (picked by eye)
    cl = tail_fade(soft(c['seg'], 4000), .06)
    d = .9
    t = np.arange(int(d * SR)) / SR
    f = hz('A3') * (1 - .45 * np.exp(-t / .16))        # A3 and its harmonics: heard on a phone speaker too
    ph = 2 * np.pi * np.cumsum(f) / SR
    motor = sum(g * np.sin(k * ph) for k, g in ((1, 1), (2, .6), (3, .3), (4, .15)))
    motor = A.lp(motor * S.adsr(len(t), .07, .45) * (1 + .12 * np.sin(2 * np.pi * 9 * t)), 1600, SR, 2)
    air = whoosh(.85, 300, 900, peak=.4, q=.9, lp=2000, seed=31)
    sw = ends(S.sweep(hz('D4'), hz('A4'), .7, att=.08, tau=.5), .1)
    return [(mix([(cl, 0, -1), (ends(motor, .1), .03, -2), (air, .02, -10), (sw, .06, -10)], .92),
             dict(src=c['key'], at=round(c['at'], 3)))]


def bonus_end():
    # FILL UP's summary: a settling, resolving D major - the arpeggio walks down onto the low D
    arp = chime_(['A5', 'F#5', 'D5', 'A4'], gap=.1, dur=1.45, tau=.45, bright=.38, gains=[.9, .95, 1, 1.05], seed=190)
    pd = S.pad([hz('D3'), hz('A3'), hz('D4'), hz('F#4')], 1.25, att=.25, rel=.75, cutoff=1300, saw=.4, seed=19)
    low = bl(hz('D3'), 1.3, tau=.6, bright=.1, seed=191)
    return [(mix([(arp, 0, 0), (pd, .2, -6), (low, .3, -7)], 1.58), dict(src='synth'))]


def medium_win():
    # the win screen's ring at each mark (rates 1, 1.22, 1.5; each cuts the last): the forecourt's driveway bell,
    # ding-ding, and a warm D major shimmer ringing on
    d = 3.0
    dd = notes_at([('A5', 0, 1.0), ('D6', .006, .55), ('A5', .2, .85), ('D6', .206, .5)], d, tau=.75, bright=.42, seed=200)
    pd = S.pad([hz('D4'), hz('F#4'), hz('A4')], 2.7, att=.3, rel=2.0, cutoff=1500, saw=.3, seed=20)
    sp = sparkles(d, ['D6', 'E6', 'F#6', 'A6', 'B6'], 8, .35, 2.2, tau=(.1, .16), gain=(.3, .7), seed=20)
    t = np.arange(int(d * SR)) / SR
    sp = sp * np.exp(-t / 1.0)[:, None]
    return [(mix([(dd, 0, 0), (pd, .1, -9), (sp, 0, -13)], d), dict(src='synth'))]


def trophy():
    # the TOTAL WIN arriving (with the coins): a warm, round D major fanfare-pad bloom
    d = 2.46
    arp = chime_(['D4', 'A4', 'D5', 'F#5', 'A5'], gap=.06, dur=2.2, tau=.6, bright=.38, gains=[1, .95, .95, .9, .9], seed=210)
    br = S.pad([hz(n) for n in ('D3', 'A3', 'D4', 'F#4', 'A4')], 2.2, att=.12, rel=1.4, cutoff=1700, saw=.55, seed=21)
    sub = bl(hz('D2'), 2.0, tau=.8, bright=.05, seed=211)
    return [(mix([(arp, 0, 0), (br, .24, -3), (sub, .24, -9)], d), dict(src='synth'))]


def coins_rain():
    # ... and its coins: soft register coins pouring and settling, with a few in-key glints
    cs = excerpts('coins_pour', 4.6, 4.0, mode='longest', min_event=1.0)
    c = cs[0]
    seg = soft(c['seg'], 5000)
    t = np.arange(len(seg)) / SR
    seg = fade_in(seg, .05) * np.minimum(1, np.exp(-(t - 2.6) / 1.2))[:, None]
    d = max(3.6, min(4.9, len(seg) / SR + .3))
    sp = sparkles(d, ['A5', 'B5', 'D6', 'E6', 'F#6', 'A6'], 9, .05, d - .8, tau=(.08, .13), gain=(.4, .9), seed=22)
    return [(mix([(seg, 0, 0), (sp, 0, -12)], d), dict(src=c['key'], at=round(c['at'], 3)))]


def bust_a():
    # LUCKY PUMP lands on nothing: a gentle, warm shrug - three soft bells walking down onto D
    b = notes_at([('A4', 0, 1.0), ('F#4', .22, .95), ('D4', .46, 1.0)], 1.45, tau=.38, bright=.25, seed=220)
    pd = S.pad([hz('D3'), hz('A3')], 1.2, att=.15, rel=.8, cutoff=700, saw=.3, seed=22)
    w = whoosh(1.0, 800, 220, peak=.15, q=.8, lp=1800, seed=22)
    return [(mix([(b, 0, 0), (pd, .4, -9), (w, 0, -16)], 1.48), dict(src='synth'))]


# ---- the FALCOS ident (runIntro: the letters land, the hit, the swash, the shimmer, out)
def intro_whoosh():
    out = []
    wins = [(.42, .3), (.46, .4), (.34, .24)]     # around the pass-by's loudest moment: 0.6 - 0.86 s
    for i, c in enumerate(around_peak('car_pass', .46, .4, 3)):
        pre, post = wins[i]
        pk = int(c['pk'] * SR)
        seg = c['seg'][max(0, pk - int(pre * SR)):pk + int(post * SR)]
        seg = tail_fade(fade_in(seg, .18), .12)
        seg = soft(seg, 4000)
        m = seg.mean(1)
        out.append((mix([(pan(m, -.6, .6), 0, 0)], len(m) / SR), dict(src=c['key'], at=round(c['at'], 3))))
    return out


def loudest_hit(name, dur, n, rise_db=20):
    """Each take's loudest transient: from where its attack rises within rise_db of the peak (less 4 ms), dur s
    long - so the hit sits 4 ms in, never after a stretch of lead-in."""
    out = []
    for k in takes(name):
        x = clean(k)
        d = A.envelope_db(x, SR, .002)
        pk = int(np.argmax(d))
        i = pk
        while i > 0 and d[i] > d[pk] - rise_db and pk - i < int(.05 * SR):
            i -= 1
        s0 = max(0, i - int(.004 * SR))
        seg = tail_fade(x[s0:s0 + int(dur * SR)], .15)
        crest = d[pk] - np.median(d[s0:s0 + int(dur * SR)])
        out.append(dict(key=k, at=s0 / SR, seg=seg, score=crest, sp=A.speech_score(seg, SR)[0]))
    return sorted([c for c in out if c['sp'] <= .08], key=lambda c: -c['score'])[:n]


def intro_hit():
    # the logo landing (runIntro: the last letter's landing): a neon sign's relay clunk 4 ms in, a soft low D boom,
    # a D major bell chord and the sign's hum (synthesised, in key: A2 and its harmonics) swelling and settling,
    # all decaying cleanly to zero by ~2.6 s
    out = []
    for i, c in enumerate(loudest_hit('neon_on', .22, 2)):
        seg = soft(c['seg'], 3200)
        boom = thump(hz('D2') * 2, hz('D2'), 2.6, tau=.55, glide=.06, att=.004)
        ch = chime_(['D4', 'A4', 'D5', 'F#5'] if i == 0 else ['D4', 'F#4', 'A4', 'D5'], gap=.012, dur=2.6, tau=.7, bright=.35, seed=230 + i)
        pd = S.pad([hz('D3'), hz('A3'), hz('F#4')], 2.5, att=.02, rel=1.8, cutoff=1200, saw=.3, seed=23 + i)
        pd = pd * np.exp(-np.arange(len(pd)) / SR / .9)
        hm = S.hum(hz('A2'), 2.5, att=.12, rel=1.6) * np.exp(-np.arange(int(2.5 * SR)) / SR / .8)
        out.append((mix([(seg, 0, -2), (boom, .004, -3), (ch, .006, -2), (pd, .01, -9), (S.norm(hm, .6), .02, -11)], 2.75),
                    dict(src=c['key'], at=round(c['at'], 3))))
    return out


def intro_shimmer():
    out = []
    seqs = [['A5', 'B5', 'D6', 'E6', 'F#6', 'A6', 'B6', 'D7'], ['B5', 'D6', 'E6', 'F#6', 'A6', 'B6', 'D7', 'E7'],
            ['A5', 'D6', 'E6', 'F#6', 'A6', 'D7', 'E7', 'F#7']]
    for i, notes in enumerate(seqs):
        rng = np.random.default_rng(240 + i)
        sp = np.zeros((int(1.35 * SR), 2))
        for j, n in enumerate(notes):
            g = pan(gl(hz(n), .5, tau=.17, seed=j + 9 * i) * .85 ** (j * .5), -.6 + 1.2 * j / (len(notes) - 1))
            k = int((.02 + j * .085 + rng.uniform(-.01, .01)) * SR); m = min(len(g), len(sp) - k)
            sp[k:k + m] += g[:m]
        pd = S.pad([hz('D5'), hz('A5'), hz('F#6')], 1.3, att=.35, rel=.6, cutoff=3000, saw=.15, seed=24 + i)
        out.append((soft(mix([(sp, 0, 0), (pd, 0, -7)], 1.32), 6500), dict(src='synth')))
    return out


def intro_out():
    out = []
    for i, notes in enumerate([['D5', 'A5', 'D6'], ['A4', 'D5', 'F#5', 'A5']]):
        ch = chime_(notes, gap=0, dur=.9, tau=.35, bright=.3, seed=250 + i)[:int(.86 * SR)][::-1].copy()
        w = whoosh(.86, 300, 1800, peak=.93, q=.8, lp=3500, seed=25 + i)
        out.append((mix([(ch, 0, 0), (pan(w, .3 * (1 - 2 * i), -.3 * (1 - 2 * i)), 0, -4)], .9), dict(src='synth')))
    return out


REMAKE = {   # stem -> (builder, target LUFS, fade-out s, purpose)
    # the FALCOS ident
    'sfx_intro_whoosh': (intro_whoosh, -24, .1, 'Ident: the swash sweeping in - a car passing on the night road, panned left to right'),
    'sfx_intro_hit': (intro_hit, -22, .25, 'Ident: the logo landing - neon sign relay clunk, soft low D boom and a D major bell chord decaying to zero'),
    'sfx_intro_shimmer': (intro_shimmer, -26, .1, 'Ident: soft glassy pentatonic run over the letters, panned across'),
    'sfx_intro_out': (intro_out, -25, .05, 'Ident: reversed D chord swelling with a rising whoosh, out to the game'),
    'sfx_land_brick': (land_brick, -24, .03, 'Ident: each FALCOS letter landing - soft rubbery thunk with a low D body'),
    # the win presentation
    'sfx_line': (line, -27, .08, 'Shared cluster note under each symbol chime: low warm D4/A4 pluck, soft D3'),
    'sfx_glow_pulse': (glow_pulse, -27, .08, 'Winning symbol lighting up: soft neon pad swell on D with a faint A2 hum'),
    'sfx_shine': (shine, -26, .06, 'Shine across a symbol: soft airy sweep left to right, two glass tings'),
    'sfx_sparkle': (sparkle, -27, .06, 'Glitter: soft scattered glass plinks in D pentatonic'),
    'sfx_glint': (glint, -28, .08, 'One soft glass ting per lit symbol (tuned so the game\'s GLINT_SCALE x .92 lands on D6 E6 F#6 G6 A6 B6)'),
    'sfx_win_text': (win_text, -25, .07, 'Win figure popping up: soft rising blip D5-A5, glass D6, faint neon hum'),
    'sfx_count_tick': (count_tick, -27, .01, 'Win figure counting: one tiny soft tick'),
    'sfx_mult_slam': (mult_slam, -23, .04, 'x<N> slamming onto the figure: rubber stamp thump, soft low D boom'),
    'sfx_count_whoosh': (count_whoosh, -26, .06, 'Figure climbing after the slam: soft rising whoosh and D4-D5 glide'),
    'sfx_count_end': (count_end, -25, .08, 'Figure lands: cash register ka-chunk and one soft A5/D5 bell'),
    'sfx_float_away': (float_away, -27, .08, 'Figure floating down into the bar: soft falling whoosh with three fading glass notes'),
    'sfx_medium_win': (medium_win, -24, .2, 'Win screen mark ring: forecourt driveway bell ding-ding and a warm D major shimmer'),
    'sfx_trophy': (trophy, -25, .2, 'TOTAL WIN arrival: warm D major fanfare-pad bloom'),
    'sfx_coins_rain': (coins_rain, -25, .25, 'TOTAL WIN arrival: soft register coins pouring and settling, in-key glints'),
    'sfx_money_tick': (money_tick, -24, 0, 'Counter ticker loop (win screen, balance, bonus win): pump number wheels, a tiny bell every 10th tick'),
    # the board
    'sfx_reels': (reels, -31, 0, 'Reveal loop under the falling reels: soft rolling whir with a low D3/A3 hum (seamless 0.68 s)'),
    'sfx_reel_stop': (reel_stop, -25, .03, 'A column landing: soft rubbery thunk with a low body'),
    'sfx_cascade': (lambda: [(mix([(pan(whoosh(.85, 1400, 360, peak=.3, q=.85, lp=3000, seed=260 + i), .2 - .4 * i, -.2 + .4 * i), 0, 0),
                                  (ends(S.sweep(hz('A4'), hz('D4'), .7, att=.05, tau=.3), .1), .02, -15)], .89), dict(src='synth')) for i in range(2)],
                    -28, .08, 'A tumble refill starting to fall: soft falling whoosh, A4-D4 glide'),
    'sfx_pop': (pop, -25, .06, 'An icon popping off the board: soft round boop and a puff of air'),
    'sfx_land_soft': (lambda: land('cup_set', .14, 3, 5000), -25, .02, 'Slushie / hot dog / donut land: soft paper-cup thump on the counter'),
    'sfx_land_can': (lambda: land('can_set', .32, 3, 6000, tune_it=True), -25, .03, 'Jerry can / energy drink land: soft hollow can tock'),
    'sfx_land_chain': (lambda: land('key_drop', .65, 3, 4500, tune_it=True, min_s=.45), -27, .06, 'Gold key lands: small key ring clink on the counter'),
    'sfx_land_coin': (lambda: land('coin_clink', .45, 2, 4800, tune_it=True, min_s=.15), -26, .05, 'Cash register lands: two coins clinking into the drawer'),
    'sfx_land_baggie': (lambda: land('bag_drop', .24, 3, 5500), -26, .03, 'Chips bag lands: soft crinkly plop'),
    'sfx_land_metal': (lambda: land('nozzle_set', .3, 3, 5500), -26, .03, 'Fuel nozzle / Zippo / Gas Pump land: soft muted metal clunk'),
    'sfx_land_card': (lambda: land('card_drop', .28, 2, 5500, min_s=.12), -26, .03, 'Scratch tickets land: soft papery slap'),
    # the HUD and the round
    'sfx_spin': (spin, -27, .08, 'Spin: gas pump handle lifted, the pump whirring up, soft D4-A4 rise'),
    'sfx_skip': (skip, -28, .05, 'Skip: dashboard click and a quick soft downward whoosh'),
    'sfx_bet': (bet, -26, .03, 'Bet +/- and (at half speed) each reel landing: soft cash register key clack'),
    'sfx_toggle': (toggle, -26, .04, 'Rapid / sound switches: soft dashboard toggle and a tiny E6'),
    'sfx_ui_click': (ui_click, -27, .01, 'Any button: soft dashboard push-button click'),
    'sfx_ui_hover': (ui_hover, -30, .005, 'Pointer arriving on a button: faint glassy tick'),
    'sfx_slider_tick': (slider_tick, -28, .008, 'Volume bar notch: tiny soft tick'),
    'sfx_swish_in': (lambda: swish(True, [.38, .46]), -27, .04, 'Under every menu opening: soft rising whoosh'),
    'sfx_swish_out': (lambda: swish(False, [.5, .44]), -27, .05, 'Under every menu closing: soft falling whoosh'),
    'sfx_menu_open': (lambda: menu(True), -27, .06, 'Menu opens: dashboard click and a rising A5-D6 glass pair'),
    'sfx_menu_close': (lambda: menu(False), -27, .07, 'Menu closes: dashboard click and a falling D6-A5 pair'),
    'sfx_auto_start': (lambda: auto(True), -25, .06, 'Autoplay on: two soft turn-signal ticks, rising D5-A5'),
    'sfx_auto_stop': (lambda: auto(False), -25, .06, 'Autoplay off: one turn-signal tick, falling A5-D5'),
    'sfx_hover_loop': (hover_loop, -26, 0, 'Bonus button hover: faint neon hum on A2 with in-key harmonics, seamless 4 s loop'),
    'sfx_buy_confirm': (buy_confirm, -24, .1, 'Bonus bought: pump nozzle clunk, rising D major arpeggio, soft pad'),
    'sfx_fs_tick': (fs_tick, -26, .02, 'Free spins counter turning over: soft register key and an A5/B5 ting'),
    'sfx_bonus_end': (bonus_end, -24, .1, 'FILL UP summary: D major arpeggio walking down onto a warm low D'),
}
SETS.update(REMAKE)
SINGLES.update({'sfx_spin', 'sfx_bet', 'sfx_reels', 'sfx_skip', 'sfx_line', 'sfx_bonus_end', 'sfx_money_tick', 'sfx_medium_win',
                'sfx_trophy', 'sfx_coins_rain', 'sfx_pop', 'sfx_win_text', 'sfx_hover_loop', 'sfx_auto_start',
                'sfx_auto_stop', 'sfx_menu_open', 'sfx_menu_close', 'sfx_toggle'})
LOOPS.update({'sfx_reels', 'sfx_money_tick', 'sfx_hover_loop'})


def main():
    os.makedirs(BUILD, exist_ok=True)
    rp = os.path.join(BUILD, 'report.json')
    rep = json.load(open(rp)) if os.path.exists(rp) else {}
    want = sys.argv[1:]
    for stem, (fn, tgt, fout, purpose) in SETS.items():
        if want and stem not in want:
            continue
        res = fn()
        files = []
        if stem in SINGLES and len(res) != 1:
            raise SystemExit(f'{stem}: a single file, but {len(res)} takes')
        for i, (x, info) in enumerate(res, 1):
            y = master_loop(x, SR, tgt) if stem in LOOPS else A.master(x, SR, tgt, ceil_db=-6.5, fout=fout)
            p = os.path.join(BUILD, f'{stem}.wav' if stem in SINGLES else f'{stem}_{i}.wav')
            A.write_wav(p, y)
            m = A.measure(A.read_wav(p)[0])
            src = info.get('src')
            src = [src] if isinstance(src, str) else (src or [])
            sp = [REP[k]['speech'] for k in src if k in REP]
            m['speech'] = round(max(sp), 3) if sp else 0.0      # speech score of the generated source takes (synth: 0)
            files.append(dict(file=os.path.basename(p), **m, info=info))
            print(f"{stem}_{i:<2d} {m['seconds']:5.2f}s  {m['lufs']:6.1f} LUFS  pk {m['peak_db']:6.1f}  tail {m['tail_floor_db']:6.1f}  "
                  f"cen {m['centroid_hz']:5d}  hf {m['hf_floor_db']:6.1f}  sp {m['speech']:.3f}  {info}", flush=True)
        rep[stem] = dict(target=tgt, purpose=purpose, files=files, replaces_original=stem in REMAKE, loop=stem in LOOPS)
    json.dump(rep, open(rp, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
