"""The game's five music cues: where each plays, what Lyria is asked for, and how build.py cuts it.

Falcos (owner, 2026-11-10: new music, nothing from the game it was forked from; 2026-11-12: "make the music more
hype", then - the faster synth-funk still not liked - "EDM / big drops"; then, 2026-11-13: "make the music more dopamine and less chaotic we want it more
relaxing"): smooth melodic chill house - warm pads, a gentle steady groove, soft plucks and a catchy, uplifting
hook; rewarding, never harsh, no drops. Base and menu at 126
BPM, the bonus intro and the bonus at 128, the TOTAL WIN at 126 - asked in B minor (TOTAL WIN in D major), inside
the D major / B minor notes the sound effects are pitched in (tools/falcos/sfx: D major pentatonic). Lyria takes the
tempo but not always the key: keep takes for their key; varispeed.py moves one a semitone or two (the tempo moves
with it, ~6% a semitone - the bpm below is what each cue's source in art/music-src actually plays at: the EDM takes
came back in A# minor and were all moved +1 to B minor). Earlier cues:
art/music-src/v1/ (late-night synth-funk), v2/ (the faster synth-funk), v3/ (EDM, big drops).

  bars       the loop's length in bars (4/4)
  head       None: the cue is only the loop. A number: the take's opening plays once and the loop
             starts that many seconds in (snapped to the take's beat), cut from wherever after
             loop_from fits best; the opening keeps ringing under it for `tail` seconds (default 2)
  loop_from  seconds into the take before which no loop may start (past its intro)
  game_lufs  how loud the cue should sit in the game (the music bar at 100); sets its MUSIC level
"""

CUES = {
    "base": {
        "where": "the base game",
        "bpm": 120.8, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -25,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 116 BPM. Smooth, relaxing melodic chill house for a "
            "cartoon gas station at night. 116 BPM, B minor, 4/4. A soft, steady four-on-the-floor kick, light claps, "
            "gentle shuffling hi-hats, a warm round bassline, lush warm pads over Bm9 - Gmaj7 - Dmaj7 - A6, soft "
            "plucked synth arpeggios, and a catchy, uplifting, feel-good lead melody that comes back again and again. "
            "Calm, warm and rewarding - it makes you feel good and relaxed for a long time. Never harsh, no drops, no "
            "builds, nothing chaotic. Structure: [Groove] -> [Groove with the melody] -> [Groove with pads and "
            "arpeggios] -> [Groove with the melody]. No intro, no breakdown, no fade-out."),
    },
    "menu": {
        "where": "the bonus buy menu",
        "bpm": 116.6, "bars": 16, "head": None, "loop_from": 0, "game_lufs": -27,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 112 BPM. A relaxed, dreamy deep-house groove for "
            "choosing a bonus in a cozy gas-station slot game. 112 BPM, B minor, 4/4. A soft kick, gentle shaker, a "
            "warm deep bass, dreamy Rhodes electric piano chords over Bm9 - Gmaj7 - Dmaj7 - A6, airy pads, a soft "
            "hopeful melody. Calm, pleasant and a little exciting. The same smooth groove from start to finish: no "
            "build-ups, no drops, no breakdown, no fade-out."),
    },
    "intro": {
        "where": "the bonus intro screen (waits for a click)",
        "bpm": 120.0, "bars": 8, "head": 5.6, "tail": .6, "loop_from": 10, "game_lufs": -24,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 120 BPM. The happy announcement of a bonus round in a "
            "cozy neon slot game: melodic house. 120 BPM, B minor. It opens with a warm, joyful swell - a soft "
            "cymbal, a bright rising pad chord and a sparkling harp-like glissando - then a smooth, hopeful groove: a "
            "steady soft kick, warm bass, shimmering plucked arpeggios and a gentle rising melody, full of "
            "anticipation but relaxed. Structure: [Warm swell] -> [Hopeful groove, steady and repeating]. No drop, "
            "no breakdown, no fade-out."),
    },
    "bonus": {
        "where": "the bonus rounds (FILL UP, PREMIUM, MIDNIGHT RUN)",
        "bpm": 133.8, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -23,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 122 BPM. Uplifting, euphoric but smooth melodic house "
            "for a slot game's bonus round. 122 BPM, B minor, 4/4. A punchy but soft kick, claps, open hi-hats, a "
            "warm driving bassline, bright lush chords over Bm - G - D - A, sparkling plucked arpeggios and a "
            "memorable, joyful lead hook that repeats. Feel-good, rewarding and exciting, yet relaxed and never "
            "chaotic - no harsh sounds, no big drops. Structure: [Main groove with the hook] -> [Groove with "
            "arpeggios] -> [Main groove with the hook] -> [Groove with pads]. No intro, no breakdown, no fade-out."),
    },
    "total": {
        "where": "the bonus's TOTAL WIN screen (waits for a click)",
        "bpm": 113.3, "bars": 8, "head": 8.6, "tail": 1.2, "loop_from": 15, "game_lufs": -22,
        "prompt": (
            "Instrumental only, no vocals. Key: D major. Tempo: 118 BPM. A warm, joyful celebration of a big win at a "
            "cozy neon gas station: feel-good disco house. 118 BPM, D major, 4/4. It opens with a bright happy hit - "
            "a soft crash, a sparkling glissando and a lush major chord - then a feel-good groove: a smooth "
            "four-on-the-floor kick, claps, a bouncing warm bass, bright guitar, lush strings over D - Bm7 - Gmaj7 - "
            "A and a sweet triumphant melody. Joyful, rewarding and relaxed. Structure: [Celebration hit] -> "
            "[Feel-good groove, steady and repeating]. No breakdown, no fade-out."),
    },
}
