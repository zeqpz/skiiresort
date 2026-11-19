"""Shared DSP for the Falcos SFX pass: reading takes, cleaning, measuring, mastering, writing."""
import os, warnings
import numpy as np
from scipy import signal
import soundfile as sf
import pyloudnorm as pyln

warnings.filterwarnings('ignore')
SR = 48000
SR0 = 24000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RAW = os.path.join(ROOT, 'art', 'highpeaks', 'sfx_raw')

# D major pentatonic: D E F# A B
PENTA = [2, 4, 6, 9, 11]          # semitones above C
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F#': 6, 'G': 7, 'A': 9, 'B': 11}


def hz(name):
    """'D5' -> Hz (A4 = 440)."""
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


def penta_snap(f):
    """Nearest D-major-pentatonic pitch to f (Hz) -> (target Hz, semitone shift)."""
    m = 69 + 12 * np.log2(f / 440)
    cands = [12 * o + p for o in range(0, 11) for p in PENTA]
    t = min(cands, key=lambda c: abs(c - m))
    return 440 * 2 ** ((t - 69) / 12), t - m


# ---------------------------------------------------------------- io
def load_raw(name, take):
    b = open(os.path.join(RAW, f'{name}_{take}.pcm'), 'rb').read()
    x = np.frombuffer(b[:len(b) // 4 * 4], '<i2').reshape(-1, 2).astype(np.float64) / 32768
    return x


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    sf.write(path, x.astype(np.float32), sr, subtype='PCM_16')


def read_wav(path):
    x, sr = sf.read(path, always_2d=True)
    return x, sr


def up48(x):
    return signal.resample_poly(x, 2, 1, axis=0)


# ---------------------------------------------------------------- measures
def db(v):
    return 20 * np.log10(v + 1e-12)


def peak_db(x):
    return float(db(np.abs(x).max()))


def lufs(x, sr=SR):
    """Integrated loudness (BS.1770, pyloudnorm). Sounds under 0.4 s are measured padded with silence
    to 0.5 s (one gating block), i.e. their loudness averaged over that block."""
    m = pyln.Meter(sr)
    n = max(len(x), int(.5 * sr))
    y = np.zeros((n, x.shape[1])); y[:len(x)] = x
    v = m.integrated_loudness(y)
    return float(v) if np.isfinite(v) else -120.0


def win_rms(x, sr, w, hop=None):
    m = np.square(x).mean(1) if x.ndim > 1 else np.square(x)
    n = max(1, int(w * sr)); h = hop or max(1, n // 4)
    c = np.concatenate([[0], np.cumsum(m)])
    idx = np.arange(0, max(1, len(m) - n + 1), h)
    return 10 * np.log10((c[np.minimum(idx + n, len(m))] - c[idx]) / n + 1e-30), idx, n


def centroid(x, sr):
    m = x.mean(1) if x.ndim > 1 else x
    f, P = signal.welch(m, sr, nperseg=min(2048, len(m)))
    return float((f * P).sum() / (P.sum() + 1e-30))


def band_ratio(x, sr, lo, hi):
    m = x.mean(1) if x.ndim > 1 else x
    f, P = signal.welch(m, sr, nperseg=min(2048, len(m)))
    return float(P[(f >= lo) & (f < hi)].sum() / (P.sum() + 1e-30))


def speech_score(x, sr):
    """Speech-likeness: share of energy in 300-3400 Hz x share of the 300-3400 Hz envelope's modulation
    that sits at syllable rate (3-8 Hz), over the active part. Returns (score, band share, mod share)."""
    m = x.mean(1) if x.ndim > 1 else x
    if len(m) < int(.5 * sr):
        return 0.0, 0.0, 0.0
    br = band_ratio(x, sr, 300, 3400)
    bp = signal.sosfiltfilt(signal.butter(4, [300, 3400], 'bandpass', fs=sr, output='sos'), m)
    hop = int(.01 * sr)
    env = np.sqrt(np.convolve(bp ** 2, np.ones(hop * 2) / (hop * 2), 'same')[::hop])
    act = env > env.max() * 10 ** (-30 / 20)
    if act.sum() < 50:          # under 0.5 s of activity: no syllable train possible
        return 0.0, br, 0.0
    e = env[np.nonzero(act)[0][0]:np.nonzero(act)[0][-1] + 1]
    e = e - e.mean()
    f, P = signal.welch(e, 100, nperseg=min(128, len(e)))
    mod = P[(f >= 3) & (f <= 8)].sum() / (P[(f >= .5) & (f <= 20)].sum() + 1e-30)
    # syllabic: enough distinct envelope bumps at 3-8 per second
    pk, _ = signal.find_peaks(np.convolve(env, np.ones(5) / 5, 'same'), prominence=env.max() * .15, distance=8)
    rate = len(pk) / (len(e) / 100)
    syl = 1.0 if 2.5 <= rate <= 9 and len(pk) >= 4 else 0.3
    return float(br * mod * syl * (.3 + .7 * voicing(m, sr))), br, float(mod)


def voicing(m, sr):
    """Share of active 40 ms frames that are voiced like a human voice: a clear periodicity at
    80-400 Hz (normalised autocorrelation > 0.5) whose pitch moves between frames (a held tone,
    a bell or a hum does not glide like speech)."""
    lo = signal.sosfiltfilt(signal.butter(4, [70, 1200], 'bandpass', fs=sr, output='sos'), m)
    n, h = int(.04 * sr), int(.02 * sr)
    e = np.array([np.sqrt(np.mean(lo[i:i + n] ** 2)) for i in range(0, len(lo) - n, h)])
    if not len(e):
        return 0.0
    act = e > e.max() * .1
    f0s, voiced = [], 0
    l0, l1 = int(sr / 400), int(sr / 80)
    for k, i in enumerate(range(0, len(lo) - n, h)):
        if not act[k]:
            continue
        fr = lo[i:i + n] * np.hanning(n)
        ac = np.correlate(fr, fr, 'full')[n - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        j = l0 + int(np.argmax(ac[l0:l1]))
        if ac[j] > .5:
            voiced += 1; f0s.append(sr / j)
    if act.sum() == 0 or voiced < 3:
        return 0.0
    f0s = np.array(f0s)
    glide = np.median(np.abs(np.diff(12 * np.log2(f0s)))) if len(f0s) > 2 else 0
    moving = 1.0 if .15 < glide < 4 else .3      # speech pitch drifts; a steady tone or random jumps do not
    return float(voiced / act.sum() * moving)


def hf_floor(x, sr):
    """Hiss check: the quietest 50 ms of the 6-12 kHz band, dBFS (digital silence excluded)."""
    hb = signal.sosfiltfilt(signal.butter(4, [6000, min(12000, sr / 2 - 100)], 'bandpass', fs=sr, output='sos'), x, axis=0)
    d, _, _ = win_rms(hb, sr, .05)
    d = d[d > -110]
    return float(d.min()) if len(d) else -140.0


def tail_floor(x, sr):
    """Noise floor in the tail: RMS of the last 30 ms that is not digital zero... we report the RMS
    of the final 20% of the file (at most 200 ms) - the decaying end - and the true floor of the
    stretch after the sound has fallen 50 dB under its peak (exact zero = -140)."""
    e, idx, n = win_rms(x, sr, .01, hop=int(.0025 * sr))
    top = e.max()
    after = np.nonzero(e > top - 50)[0]
    end = idx[after[-1]] + n if len(after) else 0
    tail = x[end:]
    return float(max(-140, 10 * np.log10(np.mean(np.square(tail)) + 1e-30))) if len(tail) > 10 else -140.0


def measure(x, sr=SR):
    return dict(seconds=round(len(x) / sr, 3), peak_db=round(peak_db(x), 2), lufs=round(lufs(x, sr), 2),
                tail_floor_db=round(tail_floor(x, sr), 1), centroid_hz=round(centroid(x, sr)),
                hf_floor_db=round(hf_floor(x, sr), 1), speech=round(speech_score(x, sr)[0], 3),
                clip=int((np.abs(x) > .999).sum()))


# ---------------------------------------------------------------- cleaning
def hp(x, f, sr, order=4):
    return signal.sosfiltfilt(signal.butter(order, f, 'highpass', fs=sr, output='sos'), x, axis=0)


def lp(x, f, sr, order=4):
    return signal.sosfiltfilt(signal.butter(order, f, 'lowpass', fs=sr, output='sos'), x, axis=0)


def shelf_soften(x, sr, f0=5000, cut_db=-4):
    """Gentle high-shelf cut (biquad, RBJ) for warmth."""
    A = 10 ** (cut_db / 40); w0 = 2 * np.pi * f0 / sr; S = 1
    al = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    c = np.cos(w0)
    b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
         A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
    a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
    return signal.filtfilt(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def bed_profile(x, sr, a, b):
    """The take's own background bed: its quietest 50 ms windows outside the event [a, b), skipping
    the generator's digital-silence padding."""
    d, idx, n = win_rms(x, sr, .05, hop=int(.005 * sr))
    pad = int(.05 * sr)
    ok = [(v, i) for v, i in zip(d, idx) if (i + n < a - pad or i > b + pad) and v > -92]
    if len(ok) < 3:
        ok = [(v, i) for v, i in zip(d, idx) if v > -92]
    if not ok:
        return None, -140.0
    vals = np.array([v for v, _ in ok]); bed = np.percentile(vals, 20)
    ok = sorted(ok, key=lambda t: abs(t[0] - bed))
    used, chunks = [], []
    for v, i in ok:
        if abs(v - bed) > 4 or len(chunks) >= 10:
            break
        if any(abs(i - j) < n for j in used):
            continue
        used.append(i); chunks.append(x[i:i + n])
    return (np.concatenate(chunks) if chunks else None), float(bed)


def denoise(x, sr, noise, prop=1.0):
    import noisereduce as nr
    out = np.zeros_like(x)
    for c in range(x.shape[1]):
        y = nr.reduce_noise(y=x[:, c], sr=sr, y_noise=noise[:, c], stationary=True, prop_decrease=prop,
                            n_std_thresh_stationary=1.5, n_fft=512, time_mask_smooth_ms=8, freq_mask_smooth_hz=200)
        out[:, c] = y[:len(x)]
    return out


def envelope_db(x, sr, w=.005):
    m = np.square(x).mean(1)
    n = max(1, int(w * sr))
    return 10 * np.log10(np.convolve(m, np.ones(n) / n, 'same') + 1e-30)


def gate(x, sr, thr_db, look=.002, hold=.015, rel=.025, bridge=.15):
    """Hard gate to exact digital zero: open where the 5 ms envelope is over thr_db; look-ahead,
    hold, raised-cosine release. Returns the gated signal (same length)."""
    d = envelope_db(x, sr)
    op = d > thr_db
    # bridge: dips shorter than `bridge` s inside a sound stay open (no choppy holes mid-event)
    if bridge and op.any():
        ed = np.diff(np.concatenate([[0], op.astype(int), [0]]))
        on, off = np.nonzero(ed == 1)[0], np.nonzero(ed == -1)[0]
        for e0, s1 in zip(off[:-1], on[1:]):
            if s1 - e0 < bridge * sr:
                op[e0:s1] = True
    L, H = int(look * sr), int(hold * sr)
    c = np.concatenate([[0], np.cumsum(op.astype(np.int64))])
    i = np.arange(len(op))
    k = (c[np.minimum(len(op), i + L + 1)] - c[np.maximum(0, i - H)]) > 0
    g = k.astype(float)
    edges = np.diff(np.concatenate([[0], k.astype(int), [0]]))
    R = int(rel * sr)
    for s in np.nonzero(edges == -1)[0]:
        e0 = min(len(g), s + R)
        g[s:e0] = np.maximum(g[s:e0], .5 + .5 * np.cos(np.linspace(0, np.pi, e0 - s)))
    A = int(.001 * sr)
    for s in np.nonzero(edges == 1)[0]:
        a0 = max(0, s - A)
        g[a0:s] = np.maximum(g[a0:s], np.linspace(0, 1, s - a0 + 1)[:-1])
    return x * g[:, None]


def events(x, sr, rel_db=-38, gap=.06, min_len=.03):
    """Active stretches: 5 ms envelope over (peak + rel_db), joined across gaps < gap s.
    Returns [(a, b, peak_db)] in samples."""
    d = envelope_db(x, sr)
    top = d.max()
    on = d > top + rel_db
    if not on.any():
        return []
    edges = np.diff(np.concatenate([[0], on.astype(int), [0]]))
    st, en = list(np.nonzero(edges == 1)[0]), list(np.nonzero(edges == -1)[0])
    segs = []
    for a, b in zip(st, en):
        if segs and a - segs[-1][1] < gap * sr:
            segs[-1][1] = b
        else:
            segs.append([a, b])
    return [(a, b, float(d[a:b].max())) for a, b in segs if b - a >= min_len * sr]


def clean_take(x, sr, hp_hz=90, lp_hz=9000, gate_rel=-55):
    """DC + high-pass + low-pass, noise reduction from the take's own bed, gate to zero.
    Returns (cleaned, info)."""
    x = x - x.mean(0)
    x = hp(x, hp_hz, sr)
    x = lp(x, lp_hz, sr)
    ev = events(x, sr, -40)
    a = ev[0][0] if ev else 0
    b = ev[-1][1] if ev else len(x)
    noise, bed = bed_profile(x, sr, a, b)
    pk = peak_db(x)
    if noise is not None and bed > -92 and bed < pk - 30 and len(noise) > 512:
        y = denoise(x, sr, noise)
    else:
        y = x.copy()
    # residual bed after reduction, same windows: gate threshold 12 dB above it (or peak - 55)
    d, _, _ = win_rms(y, sr, .05, hop=int(.005 * sr))
    resid = np.percentile(d[d > -110], 10) if (d > -110).any() else -120
    thr = max(resid + 12, peak_db(y) + gate_rel)
    y = gate(y, sr, thr)
    return y, dict(bed=bed, resid=float(resid), thr=float(thr), peak=pk)


# ---------------------------------------------------------------- mastering
def limiter(x, sr, ceil_db=-6.5, look=.002, rel=.05):
    """Look-ahead peak limiter (gain computed on a block max, smoothed)."""
    c = 10 ** (ceil_db / 20)
    a = np.abs(x).max(1)
    L = int(look * sr)
    # running max over the look-ahead window
    from scipy.ndimage import maximum_filter1d
    pk = maximum_filter1d(a, size=2 * L + 1)
    g = np.minimum(1.0, c / (pk + 1e-12))
    # release smoothing (one-pole on the way up), attack instant (already looked ahead)
    out = np.empty_like(g); cur = 1.0; k = np.exp(-1 / (rel * sr))
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else g[i] + (cur - g[i]) * k
        out[i] = cur
    out = np.convolve(out, np.ones(L) / L, 'same')
    out = np.minimum(out, g)          # never let the smoothing overshoot the ceiling
    return x * out[:, None]


def trim(x, sr, thr_db=-70):
    e = np.abs(x).max(1)
    nz = np.nonzero(e > 10 ** (thr_db / 20))[0]
    if not len(nz):
        return x[:0]
    return x[max(0, nz[0] - int(.001 * sr)):nz[-1] + 1]


def fades(x, sr, fin=.004, fout=.05):
    x = x.copy()
    ni, no = min(len(x) // 4, int(fin * sr)), min(len(x) // 2, int(fout * sr))
    x[:ni] *= (.5 - .5 * np.cos(np.linspace(0, np.pi, ni)))[:, None]
    x[-no:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, no)))[:, None]
    x[0] = 0; x[-1] = 0
    return x


def master(x, sr, target_lufs, ceil_db=-6.5, fout=.05, fin=.004, soften=True):
    """Trim, air shelf, loudness to target, peak limiter under ceil_db, fades. Iterates the gain so
    the limited result lands on target."""
    x = trim(x, sr)
    if soften:
        x = shelf_soften(x, sr, 7500, +2.5)   # air, not a cut (2026-11-13: the -3 dB at 6 kHz made them sound underwater)
    x = fades(x, sr, fin, fout)
    g = target_lufs - lufs(x, sr)
    y = x
    for _ in range(4):
        y = limiter(x * 10 ** (g / 20), sr, ceil_db)
        err = target_lufs - lufs(y, sr)
        if abs(err) < .2:
            break
        g += err
    y = fades(trim(y, sr, -80), sr, fin, min(fout, .03))   # re-assert exact-zero ends after trimming
    return y


def to_stereo(m, width=0.0, seed=0):
    """Mono -> stereo with a tiny decorrelation (a few-ms side delay), centred."""
    if m.ndim == 2:
        return m
    if width <= 0:
        return np.stack([m, m], 1)
    d = int(.0006 * SR)
    s = np.concatenate([np.zeros(d), m[:-d]])
    # L leans on the dry signal, R on the slightly delayed copy: centred, a touch wider
    return np.stack([m * (1 - width) + s * width * .5 + m * width * .5, s * (1 - width) + m * width * .5 + s * width * .5], 1)


def pitch_shift_resample(x, semis):
    """Shift pitch by resampling (duration changes by the same ratio)."""
    if abs(semis) < .05:
        return x
    r = 2 ** (semis / 12)
    n = int(round(len(x) / r))
    return signal.resample(x, n, axis=0)


def dominant_pitch(x, sr, lo=300, hi=5000):
    """Strongest spectral peak in lo..hi Hz and how peaky it is (peak / median power, dB)."""
    m = x.mean(1)
    f, P = signal.welch(m, sr, nperseg=min(8192, 1 << int(np.log2(max(256, len(m))))))
    band = (f >= lo) & (f <= hi)
    i = np.argmax(P[band]); fb = f[band]
    return float(fb[i]), float(10 * np.log10(P[band][i] / (np.median(P[band]) + 1e-30)))
