"""Synthesised musical layers (48 kHz mono float, noise-free by construction). Everything pitched sits in
D major pentatonic (D E F# A B) so overlapping wins and features stay consonant."""
import numpy as np
from scipy import signal
from audio import SR, hz


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def adsr(n, att, dec_tau, sus=0.0, rel=None, curve=1.0):
    """Soft attack (raised cosine, att s), exponential decay with time constant dec_tau."""
    t = np.arange(n) / SR
    a = np.where(t < att, (.5 - .5 * np.cos(np.pi * np.clip(t / max(att, 1e-6), 0, 1))) ** curve, 1.0)
    d = sus + (1 - sus) * np.exp(-np.maximum(0, t - att) / dec_tau)
    e = a * d
    if rel:
        r = int(rel * SR)
        e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def bell(f, dur=1.2, att=.006, tau=.45, bright=.5, warm=True, detune=.0015, seed=0):
    """Soft FM bell: carrier f, modulator at 2f (warm) or 3.5f (glassy), modulation index decaying
    faster than the tone, so the attack has a little shimmer and the tail is a pure sine. Two very
    slightly detuned voices give a gentle beat (warmth)."""
    t = _t(dur)
    rng = np.random.default_rng(seed)
    ratio = 2.0 if warm else 3.5
    idx = bright * 2.2 * np.exp(-t / (tau * .35))
    out = np.zeros_like(t)
    for k, dt in enumerate((-detune, detune)):
        fc = f * (1 + dt)
        ph0 = rng.uniform(0, 2 * np.pi)
        out += np.sin(2 * np.pi * fc * t + ph0 + idx * np.sin(2 * np.pi * fc * ratio * t))
    out *= .5
    # a soft octave partial that dies early (body), and a tiny sub for warmth
    out += .18 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / (tau * .4))
    if warm:
        out += .12 * np.sin(2 * np.pi * f / 2 * t) * np.exp(-t / (tau * 1.2))
    # sparkle (2026-11-13: brighter, more rewarding): the 3rd and 5th partials, gone within a few tens of ms
    out += .16 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / (tau * .12)) + .07 * np.sin(2 * np.pi * 5.01 * f * t) * np.exp(-t / (tau * .07))
    return out * adsr(len(t), att, tau)


def glass(f, dur=.35, att=.003, tau=.09, seed=0):
    """Glassy plink: sine with partials at inharmonic ratios, quick decay, slight downward pitch settle."""
    t = _t(dur)
    fi = f * (1 + .03 * np.exp(-t / .01))
    ph = 2 * np.pi * np.cumsum(fi) / SR
    out = np.sin(ph) + .25 * np.sin(2.76 * ph) * np.exp(-t / (tau * .4)) + .1 * np.sin(5.4 * ph) * np.exp(-t / (tau * .2))
    return out * adsr(len(t), att, tau)


def pad(freqs, dur, att=.15, rel=.3, cutoff=1800, saw=.5, detune=.004, seed=0):
    """Soft brass/string pad: detuned saws + sines through a low-pass, slow attack."""
    t = _t(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(t)
    for f in freqs:
        for dt in (-detune, 0, detune):
            ph = rng.uniform(0, 1)
            s = 2 * ((f * (1 + dt) * t + ph) % 1) - 1
            out += saw * s + (1 - saw) * np.sin(2 * np.pi * (f * (1 + dt) * t + ph))
    out /= 3 * len(freqs)
    # (2026-11-13: "they sound muffled / underwater") every pad opened up: about twice its recipe's cutoff, 2.5 kHz at least
    sos = signal.butter(2, min(9000, max(2500, cutoff * 2.2)), 'lowpass', fs=SR, output='sos')
    out = signal.sosfilt(sos, out)
    n = len(t); a, r = int(att * SR), int(rel * SR)
    e = np.ones(n)
    e[:a] = .5 - .5 * np.cos(np.linspace(0, np.pi, a))
    e[-r:] *= .5 + .5 * np.cos(np.linspace(0, np.pi, r))
    return out * e


def place(dst, src, at, gain=1.0):
    i = int(at * SR)
    n = min(len(src), len(dst) - i)
    if n > 0:
        dst[i:i + n] += gain * src[:n]
    return dst


def chime(notes, gap=.045, dur=1.1, tau=.4, bright=.45, gains=None, warm=True, seed=0):
    """Notes rolled upward 'gap' s apart (a strummed chord / arpeggio)."""
    out = np.zeros(int((dur + gap * len(notes)) * SR))
    for i, n in enumerate(notes):
        g = gains[i] if gains else 1.0 / (1 + .15 * i)
        place(out, bell(hz(n), dur, tau=tau, bright=bright, warm=warm, seed=seed + i), i * gap, g)
    return out


def blip_up(n0, n1, dur=.16, glide=.035, tau=.05, seed=0):
    """Soft pitch-rising blip (sine, glide from note n0 to n1) - the multiplier tick-up."""
    t = _t(dur)
    f0, f1 = hz(n0), hz(n1)
    f = f1 + (f0 - f1) * np.exp(-t / (glide / 3))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + .15 * np.sin(2 * ph)
    return s * adsr(len(t), .004, tau)


def tick(f=2200, dur=.03, tau=.004, seed=0):
    """Small soft mechanical tick: a damped resonance (no broadband noise)."""
    t = _t(dur)
    rng = np.random.default_rng(seed)
    s = np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) + .5 * np.sin(2 * np.pi * f * 1.52 * t)
    return s * adsr(len(t), .0008, tau)


def sweep(f0, f1, dur, att=.01, tau=None, shape='exp'):
    t = _t(dur)
    if shape == 'exp':
        f = f0 * (f1 / f0) ** (t / dur)
    else:
        f = f0 + (f1 - f0) * t / dur
    ph = 2 * np.pi * np.cumsum(f) / SR
    e = adsr(len(t), att, tau or dur)
    return np.sin(ph) * e


def soft_noise(dur, lo, hi, att=.01, tau=.05, seed=0):
    """Band-limited noise burst (for a 'poof'); kept low-passed so it never hisses."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    sos = signal.butter(2, [lo, hi], 'bandpass', fs=SR, output='sos')
    return signal.sosfilt(sos, rng.standard_normal(n)) * adsr(n, att, tau) / 3


def hum(f=120, dur=.6, att=.05, rel=.3, level=1.0):
    """Neon hum: soft fundamental + 2 gentle harmonics with a slow swell, low-passed."""
    t = _t(dur)
    s = np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * 2 * f * t) + .12 * np.sin(2 * np.pi * 3 * f * t)
    s *= 1 + .08 * np.sin(2 * np.pi * 7 * t)
    n = len(t); a, r = int(att * SR), int(rel * SR)
    e = np.ones(n); e[:a] = np.linspace(0, 1, a) ** 2; e[-r:] *= np.linspace(1, 0, r) ** 2
    return s * e * level


def norm(x, peak=1.0):
    return x * (peak / (np.abs(x).max() + 1e-12))
