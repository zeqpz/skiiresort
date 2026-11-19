# High Peaks

A cartoon ski-resort slot for Stake Engine, built on the Falcos engine and math: a 7x5 board with cluster pays and
tumbles, cell multipliers, RTP 96.50% in every mode and a max win of 50,000x. New in High Peaks: **MINI / MINOR /
MAJOR / GRAND jackpots** (10x / 50x / 250x / 2,500x the bet), won when a **?** drops onto the board.

Kept from the base game: the HUD's layout (restyled see-through black and white), the black-and-white Smukiez
intro, the three-card loading screen, and the Bonus Buy menu layout. Everything else was made new: the scene and
its animation (`frontend/skyfx.js`: chairs riding the lift, skiers and snowboarders on the run, chimney smoke,
drifting clouds, falling snow, flickering windows), the log board frame and plank backing, the framed jackpot
board, the treasure-chest Buy Bonus button, symbols, banners, logos, loading cards, gauges and all five music cues
(Lyria via OpenRouter, `tools/music`: reggae-tinged chill house, in keys that match the sound effects).
**The duck** (the main character, by the board) and the skiing ducks on the slope are modelled, rigged (a real
armature with IK arms) and animated in Blender: `tools/highpeaks/blender/duck_build.py` (model, rig, toon materials,
props), `duck_anim.py` (the clips), `duck_render.py` (headless render; also saves `art/highpeaks/blender/duck.blend`),
then `tools/highpeaks/pack_duck.py` packs the frames into `frontend/assets/duck/`. Clips: idle, look, roll (papers
and a bud out, rolls, licks, puts it away), smoke (joint and lighter out, lights it, hits it, exhales, puts them
away), bong (bong from behind, two dud sparks then a light, a bubbling pull, a cloud and a cough, puts it away);
reactions win, mult, bonus, bonusidle (bonus rounds) and tease; ski and board loops for the slope.

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/highpeaks/blender/duck_render.py
.venv/bin/python tools/highpeaks/pack_duck.py
```

Design: [DESIGN.md](DESIGN.md). Event contract: [math-sdk/games/highpeaks/EVENTS.md](math-sdk/games/highpeaks/EVENTS.md).

## Names (Falcos -> High Peaks)

| Falcos | High Peaks |
| --- | --- |
| FUEL CHANCE (3x) | HIGHER CHANCE: about 1.7x the bonus chance |
| FILL UP (100x) | STASH: collect sticky Buds (green / gold / red) |
| PREMIUM (300x) | FRESH POWDER |
| NITRO SPIN (500x) | AVALANCHE SPIN |
| MIDNIGHT RUN (500x) | BLACK DIAMOND |
| FALCOS / Midnight Token | PEAK Token (FS) / Black Diamond Token (XFS) |
| Gas Pump: REGULAR / PLUS / PREMIUM / FULL TANK | Snow Cannon: DUSTING / POWDER / BLIZZARD / WHITEOUT |
| Scratch Ticket / Gold Ticket | Lift Pass / Gold Lift Pass |
| Lighter | Lighter |
| H1-H4 | Bong, Stash Jar, Snowboard, Ski Goggles |
| L1-L5 | Hot Cocoa, Joint, Brownie, Beanie, Pizza Slice |

Internal ids (mode keys, symbol ids, event names) are unchanged from Falcos.

## Layout

| Part | Where | What |
| --- | --- | --- |
| Front end | `frontend/` | visuals, UI, animation, sound. No outcome math. |
| Math | `math-sdk/games/highpeaks/` | config, reel strips, sims, optimisation, published books (`library/publish_files`). |
| Local RGS | `rgs/mock_rgs.py` | a stand-in for the Stake Engine RGS, for testing only. |
| Art and sound tools | `tools/highpeaks/`, `art/highpeaks/` | OpenRouter image generation (`orgen.py`, prompts in `art/highpeaks/jobs/`), `install_art.py`, `static_symbols.py`, the jackpot sounds (`sfx/jackpot.py`). |

The OpenRouter key is read from `~/.highpeaks/openrouter-key.txt`. It is never stored in the repo.

## Play it locally

```bash
python3 -m venv .venv && .venv/bin/pip install pillow zstandard numpy scipy soundfile pyloudnorm imageio-ffmpeg noisereduce
.venv/bin/python rgs/mock_rgs.py
```

then open http://localhost:8755/index.html?sessionID=test&rgs_url=http://localhost:8755&lang=en&device=desktop

Watch a jackpot round (base-game book 1005 drops a ? and spins to MAJOR):
http://localhost:8755/index.html?replay=true&game=highpeaks&version=1&mode=base&event=1005&amount=1000000&rgs_url=http://localhost:8755&lang=en&device=desktop

## Rebuild the math

```bash
cd math-sdk/games/highpeaks
../../.venv/bin/python run.py --modes fillup premium nitro midnight --others 20000 --threads 8 --batch 1250 --optimize
../../.venv/bin/python run.py --modes base --base 100000 --threads 8 --optimize
../../.venv/bin/python run.py --modes chance --others 50000 --threads 8 --optimize
../../.venv/bin/python run.py --no-sims --checks
../../.venv/bin/python verify_books.py --write-index
../../.venv/bin/python jackpot_stats.py
```
