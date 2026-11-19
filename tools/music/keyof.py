"""Estimate the key of music takes (Krumhansl profiles over a simple chroma).  python tools/music/keyof.py FILES..."""
import sys, os
import av, numpy as np
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
for f in sys.argv[1:]:
    c = av.open(f); r = av.AudioResampler(format='fltp', layout='mono', rate=22050)
    x = np.concatenate([fr.to_ndarray()[0] for p in c.decode(audio=0) for fr in r.resample(p)])
    n = 4096; fq = np.fft.rfftfreq(n, 1 / 22050); m = (fq > 60) & (fq < 2000)
    bins = (np.round(12 * np.log2(fq[m] / 261.63)) % 12).astype(int)
    ch = np.zeros(12)
    for i in range(0, len(x) - n, n * 2):
        S = np.abs(np.fft.rfft(x[i:i + n] * np.hanning(n)))[m]
        np.add.at(ch, bins, S)
    best = max((np.corrcoef(np.roll(t, k), ch)[0, 1], NAMES[k] + (' major' if t is MAJ else ' minor')) for t in (MAJ, MIN) for k in range(12))
    print(f'{os.path.basename(f):16} {len(x) / 22050:6.1f}s  {best[1]:9} {best[0]:.2f}')
