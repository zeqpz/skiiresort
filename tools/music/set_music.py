"""Paste build.py's printed MUSIC entries into frontend/index.html: reads them from stdin (or a file), replaces each
cue's line in the MUSIC table, keeps the others.   python tools/music/build.py base | python tools/music/set_music.py"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = os.path.join(ROOT, 'frontend', 'index.html')
text = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
s = open(p).read()
for m in re.finditer(r'^\s*(base|menu|intro|bonus|total):\s*(\{ ogg: "assets/music_\1\.ogg".*\}),\s*$', text, re.M):
    cue, body = m.group(1), m.group(2).replace('level: 0.', 'level: .')
    s, n = re.subn(r'^  %s:\s*\{ ogg: "assets/music_%s\.ogg".*\},\s*$' % (cue, cue), f'  {cue}:{" " * (6 - len(cue))}{body},', s, flags=re.M)
    print(cue, 'set' if n == 1 else f'NOT FOUND ({n})')
open(p, 'w').write(s)
