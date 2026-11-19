"""High Peaks jackpot sounds (2026-11-18), synthesised (no generation cost), in the game's D major pentatonic.

    cd tools/highpeaks/sfx && ../../../.venv/bin/python jackpot.py

Writes frontend/assets/sfx_<name>.wav/.ogg/.aac (WAV masters to art/highpeaks/sfx_masters):

  jp_drop          the "?" coin dropping onto the board: a soft poof, a falling glass plink, a bright chime
  jp_tick_<level>  one highlight on the MINI / MINOR / MAJOR / GRAND bar while the wheel spins - each level its own
                   note (D5, F#5, A5, D6), so the spin reads as a rising, repeating little melody
  jp_land          the wheel stopping on its level: a firm low bell under a glassy sparkle
  jp_win_<level>   the prize fanfare - longer, fuller and higher the bigger the jackpot
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A  # noqa: E402
import synth as S  # noqa: E402
import deliver as D  # noqa: E402

SR = A.SR
ASSETS = os.path.join(A.ROOT, 'frontend', 'assets')
MASTERS = os.path.join(A.ROOT, 'art', 'highpeaks', 'sfx_masters')
LEVELS = {'mini': 'D5', 'minor': 'F#5', 'major': 'A5', 'grand': 'D6'}


def buf(dur):
    return np.zeros(int(dur * SR))


def jp_drop():
    x = buf(1.1)
    S.place(x, S.soft_noise(.25, 300, 2400, att=.01, tau=.07, seed=3), 0, .35)
    for i, n in enumerate(['B6', 'A6', 'F#6', 'D6']):          # a falling plink: the coin tumbling in
        S.place(x, S.glass(A.hz(n), .3, seed=i), .02 + i * .055, .55)
    S.place(x, S.chime(['D5', 'A5', 'D6'], gap=.03, dur=.8, tau=.3, bright=.5), .25, .8)
    return x


def jp_tick(note):
    x = buf(.32)
    S.place(x, S.bell(A.hz(note), .3, tau=.09, bright=.55, warm=False), 0, 1.0)
    S.place(x, S.tick(2400, .03), 0, .25)
    return x


def jp_land():
    x = buf(1.4)
    S.place(x, S.bell(A.hz('D4'), 1.3, tau=.5, bright=.4), 0, .9)
    S.place(x, S.bell(A.hz('A4'), 1.2, tau=.45, bright=.35), .01, .5)
    for i, n in enumerate(['D6', 'F#6', 'A6', 'D7']):
        S.place(x, S.glass(A.hz(n), .35, seed=10 + i), .04 + i * .04, .35)
    return x


WIN = {   # level: (arpeggio, pad chord, length s, repeats)
    'mini': (['D5', 'F#5', 'A5'], ['D4', 'A4'], 1.4, 1),
    'minor': (['D5', 'F#5', 'A5', 'D6'], ['D4', 'F#4', 'A4'], 1.8, 1),
    'major': (['A4', 'D5', 'F#5', 'A5', 'D6'], ['D3', 'A3', 'F#4', 'A4'], 2.4, 2),
    'grand': (['D5', 'E5', 'F#5', 'A5', 'B5', 'D6', 'F#6', 'A6'], ['D3', 'A3', 'D4', 'F#4', 'A4'], 3.4, 3),
}


def jp_win(level):
    arp, chord, dur, reps = WIN[level]
    x = buf(dur + .6)
    for k in range(reps):
        S.place(x, S.chime(arp, gap=.07, dur=1.0, tau=.35, bright=.5, seed=20 + k), k * .55, .8)
    S.place(x, S.pad([A.hz(n) for n in chord], dur, att=.12, rel=.5, cutoff=2200), .05, .35)
    S.place(x, S.bell(A.hz(chord[0]), dur, tau=.8, bright=.3), reps * .55 - .05, .6)
    return x


def write(name, x, lufs):
    y = A.master(A.to_stereo(x / (np.max(np.abs(x)) + 1e-9), .3), SR, lufs)
    os.makedirs(MASTERS, exist_ok=True)
    wav = os.path.join(MASTERS, f'sfx_{name}_1.wav')
    A.write_wav(wav, y)
    D.encode(wav, os.path.join(ASSETS, f'sfx_{name}_1.ogg'), ['-c:a', 'libopus', '-b:a', '96k', '-ar', '48000', '-vbr', 'on', '-application', 'audio'])
    D.encode(wav, os.path.join(ASSETS, f'sfx_{name}_1.aac'), ['-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-f', 'adts'])
    print(name, f'{len(y) / SR:.2f}s')


if __name__ == '__main__':
    write('jp_drop', jp_drop(), -20)
    for lvl, note in LEVELS.items():
        write(f'jp_tick_{lvl}', jp_tick(note), -24)
    write('jp_land', jp_land(), -19)
    for lvl in WIN:
        write(f'jp_win_{lvl}', jp_win(lvl), -18 if lvl != 'grand' else -17)
