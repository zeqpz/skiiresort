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
    # High Peaks (owner, 2026-11-18: "change the music"): a cartoon ski resort with weed - laid-back, sunny and a
    # little goofy. Reggae-tinged chill house in the base game, a bouncier ska / reggae-house in the bonuses, a big
    # happy brass celebration on the TOTAL WIN. Kept in B minor / D major so the sound effects (D major pentatonic)
    # stay consonant.
    "base": {
        "where": "the base game",
        "bpm": 100.0, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -25,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 100 BPM. Laid-back, sunny reggae-tinged chill house for "
            "a goofy cartoon ski resort in the mountains. 100 BPM, B minor, 4/4. A relaxed steady kick, off-beat "
            "skank guitar chops, a warm round dub bassline, soft organ bubble, gentle sleigh-bell shaker, mellow "
            "Rhodes chords over Bm7 - Gmaj7 - Dmaj7 - A, and a catchy, easy-going melodica lead that comes back again "
            "and again. Chill, happy and cozy, like hanging out in a warm ski lodge. Never harsh, no drops, no builds. "
            "Structure: [Groove] -> [Groove with the melody] -> [Groove with organ and guitar] -> [Groove with the "
            "melody]. No intro, no breakdown, no fade-out."),
    },
    "menu": {
        "where": "the bonus buy menu",
        "bpm": 92.0, "bars": 16, "head": None, "loop_from": 0, "game_lufs": -27,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 92 BPM. A dreamy, mellow lo-fi dub groove for choosing a "
            "bonus in a cozy cartoon ski lodge. 92 BPM, B minor, 4/4. A soft dusty kick and rimshot, deep warm dub "
            "bass, off-beat Rhodes chords over Bm9 - Gmaj7 - Dmaj7 - A6, soft vinyl crackle, a gentle glockenspiel "
            "motif like falling snow. Calm and pleasant. The same smooth groove from start to finish: no build-ups, "
            "no drops, no breakdown, no fade-out."),
    },
    "intro": {
        "where": "the bonus intro screen (waits for a click)",
        "bpm": 101.0, "bars": 8, "head": 6.7, "tail": .6, "loop_from": 10, "game_lufs": -24,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 120 BPM. The happy announcement of a bonus round in a "
            "cartoon ski resort slot game. 120 BPM, B minor. It opens with a joyful swell - a cymbal roll, sleigh "
            "bells, a bright brass stab and a sparkling glissando - then a bouncy, hopeful ska-house groove: a steady "
            "kick, off-beat guitar skank, warm bass, playful horn riffs and a rising melody, full of anticipation. "
            "Structure: [Joyful swell] -> [Bouncy hopeful groove, steady and repeating]. No drop, no breakdown, no "
            "fade-out."),
    },
    "bonus": {
        "where": "the bonus rounds (STASH, FRESH POWDER, BLACK DIAMOND)",
        "bpm": 124.0, "bars": 32, "head": None, "loop_from": 0, "game_lufs": -23,
        "prompt": (
            "Instrumental only, no vocals. Key: B minor. Tempo: 124 BPM. Upbeat, feel-good reggae-house for a cartoon "
            "ski resort slot game's bonus round. 124 BPM, B minor, 4/4. A punchy but soft four-on-the-floor kick, "
            "claps, off-beat skank guitar and organ, a bouncing dub bass, bright horn section riffs over Bm - G - D - A, "
            "sparkling sleigh bells, and a memorable, joyful lead hook that repeats. Exciting and rewarding, yet "
            "smooth, never chaotic, no big drops. Structure: [Main groove with the hook] -> [Groove with horns] -> "
            "[Main groove with the hook] -> [Groove with organ]. No intro, no breakdown, no fade-out."),
    },
    "total": {
        "where": "the bonus's TOTAL WIN screen (waits for a click)",
        "bpm": 116.0, "bars": 8, "head": 8.6, "tail": 1.2, "loop_from": 15, "game_lufs": -22,
        "prompt": (
            "Instrumental only, no vocals. Key: D major. Tempo: 116 BPM. A big happy celebration of a win at a cartoon "
            "ski resort: feel-good reggae-disco. 116 BPM, D major, 4/4. It opens with a bright triumphant hit - a "
            "crash, a brass fanfare, sleigh bells and a sparkling glissando - then a joyful groove: a smooth kick, "
            "claps, a bouncing bass, off-beat guitar, lush strings and horns over D - Bm7 - Gmaj7 - A and a sweet "
            "triumphant melody. Structure: [Celebration hit] -> [Joyful groove, steady and repeating]. No breakdown, "
            "no fade-out."),
    },
}
