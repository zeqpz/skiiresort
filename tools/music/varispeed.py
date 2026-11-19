"""Shift a take by whole semitones the way a turntable does (speed and pitch together) and write it as the cue's
source: art/music-src/<cue>.wav (build.py reads a .wav before an .mp3).

    .venv/bin/python tools/music/varispeed.py <take.mp3> <cue> <semitones>

Lyria takes the tempo but not the key; Falcos's cues must sit in the notes the sound effects use (D major
pentatonic: keys such as B minor, D, A or G major). A take a semitone away is moved by resampling - no time
stretching, so nothing smears - and the tempo moves with it (about 6% a semitone); cues.py's bpm says so.
"""
import os, sys, wave
import numpy as np
import av
from fractions import Fraction
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SR = 48000
src, cue, semis = sys.argv[1], sys.argv[2], float(sys.argv[3])
c = av.open(src); rate = c.streams.audio[0].rate
x = np.concatenate([f.to_ndarray() for f in c.decode(audio=0)], axis=1).T.astype(np.float64); c.close()
# play it 2^(semis/12) faster: SR out from rate * factor in
k = Fraction(SR / (rate * 2 ** (semis / 12))).limit_denominator(400)
y = signal.resample_poly(x, k.numerator, k.denominator, axis=0)
os.makedirs(os.path.join(ROOT, 'art', 'music-src'), exist_ok=True)
dst = os.path.join(ROOT, 'art', 'music-src', cue + '.wav')
with wave.open(dst, 'wb') as fh:
    fh.setnchannels(2); fh.setsampwidth(2); fh.setframerate(SR)
    fh.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())
print(f'{cue}: {semis:+g} semitones (x{k.numerator}/{k.denominator} at {rate} Hz -> 48 kHz), {len(y) / SR:.1f}s -> {os.path.relpath(dst, ROOT)}')
