"""Encode the built takes into frontend/assets/<stem>_<n>.ogg (Opus, 48 kHz, 96 kb/s stereo - the bitrate
the game's other effects use) and .aac (AAC-LC in ADTS, 48 kHz, 128 kb/s stereo) with ffmpeg
(the imageio-ffmpeg binary in the venv), and keep the 16-bit WAV master in art/highpeaks/sfx_masters/ (the game ships
only the .ogg/.aac; tools/highpeaks/compress_assets.py moves any frontend/assets/*.wav there too). A single-file sound
(build.py SINGLES) is <stem>.wav/.ogg/.aac.
Never overwrites a file this pass did not make (anything not listed in art/highpeaks/sfx_manifest.json) - except the
original game's sounds that build.py remakes (REMAKE: report.json "replaces_original"), which it replaces under
the same names. Writes the manifest (the stems delivered now; every other entry is kept).
  python deliver.py [stem ...]"""
import os, sys, json, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
BUILD = os.path.join(A.RAW, 'build')
ASSETS = os.path.join(A.ROOT, 'frontend', 'assets')
MAN = os.path.join(A.ROOT, 'art', 'highpeaks', 'sfx_manifest.json')
MASTERS = os.path.join(A.ROOT, 'art', 'highpeaks', 'sfx_masters')


def ff(*args):
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', *args], check=True)


def decode(path):
    import numpy as np
    b = subprocess.run([FF, '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', '48000', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(b, '<f4').reshape(-1, 2).astype(float)


def encode(src, dst, codec_args, ceil=-6.2):
    """Encode; if the codec's overshoot pushes the decoded peak over `ceil` dBFS, re-encode a touch quieter."""
    ff('-i', src, *codec_args, dst)
    pk, vol = A.peak_db(decode(dst)), 0.0
    for _ in range(4):
        if pk <= ceil:
            break
        vol += ceil - pk - .15
        ff('-i', src, '-af', f'volume={vol:.2f}dB', *codec_args, dst)
        pk = A.peak_db(decode(dst))
    return pk


def main():
    rep = json.load(open(os.path.join(BUILD, 'report.json')))
    old = json.load(open(MAN)) if os.path.exists(MAN) else {}
    ours = {f for v in old.values() for f in v.get('takes', []) + v.get('ogg', []) + v.get('aac', [])}
    want = sys.argv[1:]
    man = dict(old)
    os.makedirs(MASTERS, exist_ok=True)
    for stem, r in rep.items():
        if want and stem not in want:
            continue
        wavs, oggs, aacs = [], [], []
        for f in r['files']:
            base = f['file'][:-4]
            for ext in ('.wav', '.ogg', '.aac'):
                dst = os.path.join(ASSETS, base + ext)
                if os.path.exists(dst) and base + ext not in ours and not r.get('replaces_original'):
                    raise SystemExit(f'refusing to overwrite {dst} (not made by this pass)')
            src = os.path.join(BUILD, f['file'])
            shutil.copyfile(src, os.path.join(MASTERS, base + '.wav'))
            stray = os.path.join(ASSETS, base + '.wav')        # the game plays the .ogg/.aac; the master lives in sfx_masters
            if os.path.exists(stray):
                os.remove(stray)
            po = encode(src, os.path.join(ASSETS, base + '.ogg'), ['-c:a', 'libopus', '-b:a', '96k', '-ar', '48000', '-vbr', 'on', '-application', 'audio'])
            pa = encode(src, os.path.join(ASSETS, base + '.aac'), ['-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-f', 'adts'])
            f['peak_db_ogg'], f['peak_db_aac'] = round(po, 2), round(pa, 2)
            wavs.append(base + '.wav'); oggs.append(base + '.ogg'); aacs.append(base + '.aac')
        fs = r['files']
        man[stem] = dict(
            takes=wavs, ogg=oggs, aac=aacs,
            seconds=[f['seconds'] for f in fs], lufs=[f['lufs'] for f in fs], peak_db=[f['peak_db'] for f in fs],
            peak_db_ogg=[f['peak_db_ogg'] for f in fs], peak_db_aac=[f['peak_db_aac'] for f in fs],
            tail_floor_db=[f['tail_floor_db'] for f in fs], centroid_hz=[f['centroid_hz'] for f in fs],
            hf_floor_db=[f['hf_floor_db'] for f in fs], source_speech_score=[f['speech'] for f in fs],
            target_lufs=r['target'], purpose=r['purpose'],
            sources=[f['info'].get('src') for f in fs])
        if r.get('replaces_original'):
            man[stem]['replaces_original'] = True      # same file names as the forked game's sound it replaced
        if r.get('loop'):
            man[stem]['loop'] = True                   # looped by the game: no fades, its end runs on into its start
        print(f'{stem:22s} {len(wavs)} takes')
    json.dump(man, open(MAN, 'w'), indent=1, default=float)
    print(MAN)


if __name__ == '__main__':
    main()
