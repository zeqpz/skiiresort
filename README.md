# High Peaks

A cartoon ski-resort slot for Stake Engine, built on the Falcos engine and math: a 7x5 board with cluster pays and
tumbles, cell multipliers, RTP 96.50% in every mode and a max win of 50,000x. New in High Peaks: **MINI / MINOR /
MAJOR / GRAND jackpots** (10x / 50x / 250x / 2,500x the bet), won when a **?** drops onto the board.

**From [zeqpz/poweroutage](https://github.com/zeqpz/poweroutage), unchanged (owner, 2026-11-19):** the
black-and-white Smukiez intro (it holds while the game loads, its thin white bar filling), the three intro boxes
(the game's title over three cream feature cards - here the jackpot **?**, the FS scatter and the XFS scatter -
dealt out from a stack, CLICK TO PLAY under them) and the HUD (its navy bar, fixed BALANCE | WIN | BET columns and
`frontend/hudfit.js`, which shrinks a long figure to its slot and keeps the bonus emblem off the bar).
`tools/highpeaks/port_po_ui.py <poweroutage/frontend>` made the port; it is exact-string edits, so it documents
what came over. The Bonus Buy menu layout is still the base game's.

Everything else was made new: the scene and its animation (`frontend/skyfx.js`: chairs riding the lift, flat
cartoon skiers and snowboarders on the run, chimney smoke, drifting clouds, falling snow, flickering windows), the
log board frame and plank backing, the framed jackpot board, the treasure-chest Buy Bonus emblem, symbols, banners,
logos, gauges and all five music cues (Lyria via OpenRouter, `tools/music`: reggae-tinged chill house, in keys that
match the sound effects).

No 3D characters (owner, 2026-11-19): a Blender-rendered duck stood by the board and skied the slope for a day; it
did not fit the flat cartoon and `tools/highpeaks/remove_duck.py` took it out (git history keeps its pipeline).

Lobby covers for engine.io's Media page: `media/cover_16x9.png` (3840x2160) and `media/cover_3x4.png` (3072x4096),
no text on them (owner rule), painted by `tools/highpeaks/gen_covers.py gen` from the game's own art and upscaled
by `gen_covers.py build` (Real-ESRGAN x4 anime when it is installed).

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
