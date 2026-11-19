# High Peaks - game design (v1, 2026-11-18)

A cartoon ski resort on the mountains, with weed (owner: open, cartoony, a bong is fine). Flat adult-animation
cartoon art: thick black outlines, flat colours, no realistic lighting. Built on Falcos: the board, the math and
every mechanic below are Falcos's, renamed (README.md has the name table). Kept unchanged from the base game: the
HUD, the black-and-white Smukiez intro, the three-card loading screen and the Bonus Buy menu (with new banner
foregrounds and backgrounds).

## Jackpots (new, owner 2026-11-18)

A MINI / MINOR / MAJOR / GRAND bar beside the board (left of it on landscape screens, above it on portrait).
Fixed prizes x the bet: **MINI 10x, MINOR 50x, MAJOR 250x, GRAND 2,500x** (owner-approved). Not progressive:
rounds stay independent.

* A **?** can drop onto the board on any spin: base 1 in 400 spins (natural rate), every FRESH POWDER /
  BLACK DIAMOND free spin 1 in 20, every STASH spin 1 in 60. It covers a cell; the symbol under it plays on.
* When the spin's cascade is over the bar spins: the highlight runs MINI -> MINOR -> MAJOR -> GRAND with a note on
  each (D5, F#5, A5, D6), speeding up over four laps, then eases onto the level and plays its fanfare.
* Level weights once a ? has dropped: MINI 860, MINOR 115, MAJOR 22, GRAND 3 (per 1,000). Mean prize 27.4x.
* The prize is added to the spin's win and counts toward the 50,000x max win. Criteria with an exact win (max win,
  no win) never drop a ?.

As played (LUT-weighted, `jackpot_stats.py`): base game a jackpot in 1 round in 383 (MINI 1 in 413, MINOR 1 in
2,247, MAJOR 1 in 10,471, GRAND 1 in 1.4M), 7.2% of the base RTP. Bought bonuses: STASH 1 in 4, FRESH POWDER 1 in
2, BLACK DIAMOND 1 in 2.

Events: `jackpotDrop {reel, row}` right after the reveal (STASH: after the spin's land) and
`jackpotWin {level, mult, amount}` after the cascade, before setWin (EVENTS.md).

Math changes: HIGHER CHANCE gives the bonuses 1.7x as often (Falcos 2.2x), and a natural bonus is asked at its pool
mean capped at its designed average (STASH 118x, FRESH POWDER 500x, BLACK DIAMOND 1,160x). Both keep HIGHER
CHANCE's etl40b inside the 3-star band (0.80, limit 0.9). Every mode is 96.50% and passes the RGS checks.

---

The Falcos design follows. Its rules all still apply under the High Peaks names.

# Falcos - game design (v1, 2026-11-09)

Night-time gas station cluster slot. Front end built on the base game's engine, HUD and
black-and-white intro (re-lettered to FALCOS). All art, names, numbers and wording are Falcos's own.
Art direction: art/falcos/STYLE.md.

RTP 96.50% in every mode. Max win 50,000x the bet.

## Code layout and the round contract (2026-11-10)

Two parts, reviewed together, joined only by the event contract (math-sdk/games/falcos/EVENTS.md):

* **Front end - `frontend/`**: visuals, UI, animation, sound. It holds no math: no RNG that decides anything
  (Math.random only for cosmetics such as particles and which matching wheel slice to stop on), no reel strips,
  weights, lookup tables or RTP logic. The paytable, prices and odds in the rules are display text.
* **Math - `math-sdk/games/falcos/`**: game config, reel strips, simulation, optimisation and the published
  books + lookup tables (`library/publish_files`).
* **Local RGS - `rgs/mock_rgs.py`**: a stand-in for the Stake Engine RGS for testing only (never uploaded): it
  draws a weighted book per bet and serves `frontend/`.

Every bet is stateless: one `/play` returns the whole, already-resolved round (a bought bonus, or a FUEL CHANCE
spin and any bonus it triggers, is one book); `/end-round` only pays it. There are no
progressive jackpots, no links between rounds, no `/bet/event` progress markers and no mid-round save or resume:
a round left open by a dropped connection is settled on the next load and its result shown in a notice.
Six modes (base, FUEL CHANCE, FILL UP, PREMIUM, NITRO SPIN, MIDNIGHT RUN).

## Board and ways to win

7x5: 7 reels (columns) wide and 5 rows tall, 35 cells (owner decision 2026-11-09). A cluster is 5 or more matching symbols joined up, down, left or right (diagonals don't count).
It pays by symbol and size (15+ pays the top rate), times its multiplier. After every win the board
tumbles: winners clear, survivors fall, new symbols drop in, and a spin can chain many tumbles. The
board also refills after every feature that removes symbols (see Feature symbols), so no cell sits
empty while the next feature fires.

### Cell multipliers

Every cell has its own multiplier. It starts at x1 and doubles each time a win or a feature hits
that cell, up to x2048. The multiplier belongs to the cell, not the symbol: whatever tumbles into the
cell takes it on. A cluster's multiplier is the sum of the multipliers of its cells that are at x2
or more; if none are, the cluster pays x1. Base game: cells reset every spin. PREMIUM and
MIDNIGHT RUN: cells keep their multipliers for the whole bonus.

## Paying symbols (9) - pays x bet by cluster size

| size | H1 Cash Drawer | H2 Gold Key | H3 Pump Nozzle | H4 Jerry Can | L1 Energy Drink | L2 Slushie | L3 Hot Dog | L4 Chips | L5 Donut |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 1 | 0.8 | 0.5 | 0.4 | 0.3 | 0.3 | 0.2 | 0.2 | 0.2 |
| 6 | 1.5 | 1 | 0.8 | 0.5 | 0.4 | 0.4 | 0.3 | 0.3 | 0.2 |
| 7 | 2 | 1.2 | 1 | 0.8 | 0.5 | 0.5 | 0.4 | 0.4 | 0.3 |
| 8 | 2.5 | 1.5 | 1.2 | 1 | 0.8 | 0.6 | 0.5 | 0.5 | 0.4 |
| 9 | 3 | 2 | 1.5 | 1.2 | 1 | 0.8 | 0.7 | 0.6 | 0.5 |
| 10 | 5 | 4 | 3 | 2 | 1.5 | 1.2 | 1.1 | 1 | 0.9 |
| 11 | 8 | 6 | 4.5 | 3 | 2.5 | 2 | 1.8 | 1.5 | 1.4 |
| 12 | 15 | 12 | 10 | 5 | 4 | 3 | 2.8 | 2.5 | 2.2 |
| 13 | 30 | 25 | 20 | 10 | 8 | 6 | 5.5 | 5 | 4.5 |
| 14 | 60 | 50 | 40 | 20 | 15 | 12 | 11 | 10 | 9 |
| 15+ | 150 | 100 | 60 | 40 | 30 | 25 | 22 | 20 | 18 |

Owner-approved table (2026-11-09). Every pay is in 0.1x steps (the RGS grid), so every win is exact
with no rounding. The RTP is set by the reel strips and the optimiser's weights, not by this table.

Each paying symbol has its own land, idle and win animation and its own soft win sound.

## Feature symbols

Cluster wins always come first (owner, 2026-11-17: "let line hits come before any special symbols
like the lighter. let the line pay play out then the special symbol"). Whenever the board holds a
cluster it pays and the board refills; only on a board with no cluster does the next feature fire:
all Gas Pumps together, else one Scratch Ticket / Gold Ticket, else one Lighter (reading order).
The board drops new symbols after every pay and every feature (owner, 2026-11-10), so every feature
acts on a full board, and it is checked for clusters again before the next feature. The spin ends
when the board holds neither a cluster nor a feature.

* **Lighter (ZP)** - lights up its 3x3 area: the 8 cells around it and its own cell double their
  multipliers; paying symbols there burn (clear, feeding their doubled multipliers into any cluster
  they were part of). Scatters keep their place but still double. It never lands in FILL UP
  (owner, 2026-11-17).
* **Scratch Ticket (ST)** - scratches off one paying symbol that is on the board; every cell holding
  it doubles and burns, and so does the ticket's cell. FILL UP: an area collector - it collects
  every Fuel Drop in its 8 neighbours (adding their values to its own) plus any collector there that
  activated on an earlier spin; with nothing to collect it is removed, otherwise it stays with its
  total.
* **Gold Scratch Ticket (GT)** - every paying symbol on the board doubles and burns, and so does the
  ticket's cell. FILL UP: a whole-board collector.
* **Gas Pump (GP)** - column feature and the biggest single event; at most one per column. Rolls a
  fuel grade: REGULAR x2 or x4, PLUS x8 or x16, PREMIUM x32 or x64, or **FULL TANK**. REGULAR to
  PREMIUM: every cell in its column gets the pump's multiplier applied and paying symbols in the
  column burn. FULL TANK: every cell in the column becomes a MAX cell, and any cluster touching a MAX
  cell pays the max win. Pumps in different columns fire together. FILL UP: rolls x2-x64 and
  multiplies every Fuel Drop in its column and any collector there that already collected; then it
  leaves.

## Scatters

* **FALCOS Token (BS)** - exactly 3 in the base game (and no DS) -> FILL UP; 4 or more -> PREMIUM.
* **Midnight Token (DS)** - darker, rare. 3 in the base game (or in a FUEL CHANCE spin) -> MIDNIGHT
  RUN. MIDNIGHT RUN can also be bought (500x).
* **Mixed** (owner, 2026-11-17) - 3 or more tokens with at least one DS among them (2 BS + 1 DS, 2 + 2 ...)
  -> MIDNIGHT RUN, unless 4 or more are BS (PREMIUM). Order: 3+ DS, 4+ BS, mixed 3+, exactly 3 BS.

## Bonuses

* **FILL UP** (3 FALCOS Tokens, or buy 100x) - a Fuel Drop collection game with a 3-bar fuel gauge.
  No cell multipliers here. The gauge starts full (3). Every spin uses one bar; any spin that lands
  something new (a drop or a feature) refills it to 3. The bonus ends when the gauge is empty and
  nothing new lands. Fuel Drops are sticky: green x0.2/x0.5/x1/x2/x3, amber x5/x10/x15/x20, red
  x50/x100/x250/x500, and a drop that grows changes colour (green under x5, amber from x5, red from
  x50). No Lighter lands in FILL UP (owner, 2026-11-17); Scratch Tickets collect their 8 neighbours, Gold Tickets collect the
  whole board and then double what they collected (2026-11-13), Gas Pumps multiply them.
  At the end you win the total of every drop left plus every collector's total, times the bet,
  capped at the max win.
* **PREMIUM** (4+ FALCOS Tokens, or buy 300x) - 10 free spins of the base game with sticky cell
  multipliers: a cell that reached x8 keeps x8 into the next spin and keeps growing.
* **MIDNIGHT RUN** (3 Midnight Tokens, or buy 500x) - 10 free spins with sticky cell multipliers,
  every cell starting at x4, and Gas Pumps landing far more often. The biggest bonus in the game.
  The bought one is the same bonus (same strip, same x4 start, same 10 spins).

## Bet modes

| mode | cost | what it is |
|---|---|---|
| base | 1x | normal spin |
| FUEL CHANCE | 3x | one base spin with about 2.2x the chance of triggering any bonus |
| FILL UP | 100x | buys the collection bonus |
| PREMIUM | 300x | buys the sticky-multiplier free spins |
| NITRO SPIN | 500x | one spin with every cell preloaded with a multiplier from x16 to x2048 |
| MIDNIGHT RUN | 500x | buys MIDNIGHT RUN directly (owner 2026-11-10: replaces the LUCKY PUMP wheel) |

Max win 50,000x the bet in every mode (owner decision 2026-11-09). Every mode's RTP is 96.50%.

## Sound

Soft and short: every win and feature sound is musical and gentle, mixed under the music, nothing
harsh or loud.

## Open items

* Math phase 2 (7x5 retune, optimisation to 96.50%, RGS checks): see Math notes below.
* Front-end playback of cell multipliers, burns, Gas Pump grades, Fuel Drops and the fuel gauge.

## Math notes (phase 2, 2026-11-09; re-run 2026-11-10)

Model: `math-sdk/games/falcos/` (`game_config.py`, `reels/gen_reels.py`, `game_optimization.py`,
`cap_books.py`, `trim_chance_tail.py`). Event contract: `math-sdk/games/falcos/EVENTS.md`. Optimised
with the Rust optimiser; `rgs_verification` and `verify_books.py` run on the published files.

2026-11-10 re-run (owner): the board now refills after the cluster pay and after every feature group
(more symbols drop per spin, so features chain more and the natural bonuses grew: PREMIUM ~410x,
MIDNIGHT RUN ~1,080x, NITRO ~825x a spin unweighted), and LUCKY PUMP was replaced by the MIDNIGHT
RUN buy. base, FUEL CHANCE, PREMIUM, NITRO and MIDNIGHT RUN were re-simulated and re-optimised; FILL
UP has no tumbles and its books and table are unchanged.

Books: base 100,000, FUEL CHANCE 50,000, FILL UP / PREMIUM / NITRO / MIDNIGHT RUN 20,000 each.

| mode | RTP | wins | max win (50,000x) | P(win >= 100x) | heaviest book | std (bets) | etl10k | etl40b | prob5k | 3-star band |
|---|---|---|---|---|---|---|---|---|---|---|
| base | 96.50% | 1 in 2.97 | 1 in 8.0M | 1 in 538 | 1 in 52,700 | 26.8 | 0.01 | 0.60 | 0.000 | pass |
| FUEL CHANCE | 96.50% | 1 in 2.46 | 1 in 3.6M | 1 in 261 | 1 in 7,446 | 42.3 | 0.03 | 0.84 | 0.000 | pass |
| FILL UP | 96.50% | always | 1 in 250,000 | 1 in 2.9 | 1 in 2,000 | 179.9 | 0.54 | 0.70 | 0.000 | pass |
| PREMIUM | 96.50% | always | 1 in 200,000 | 1 in 1.4 | 1 in 2,000 | 368.7 | 0.60 | 0.40 | 0.000 | pass |
| NITRO SPIN | 96.50% | 1 in 1.25 | 1 in 200,000 | 1 in 1.5 | 1 in 2,000 | 1,182 | 0.60 | 0.42 | 0.009 | pass |
| MIDNIGHT RUN | 96.50% | always | 1 in 200,000 | 1 in 1.2 | 1 in 2,000 | 1,015 | 0.60 | 0.40 | 0.006 | pass |

Limits (rgs_verification): RTP <= 0.967, etl10k <= 0.8, etl40b <= 0.9, prob5k <= 0.01, prob10k <=
0.005, cvar <= 800. Every mode passes; `verify_books.py` replays every book cleanly.

Bonuses: base FILL UP 1 in 400 (avg 112x), PREMIUM 1 in 2,700 (avg 476x), MIDNIGHT RUN 1 in 14,000
(avg 1,139x); FUEL CHANCE 2.2x as often (1 in 182 / 1,227 / 6,364; 5x failed the 3-star etl40b
limit). FUEL CHANCE's ordinary spins must return ~4.4x per win (the bonuses carry only ~0.35 of
its 0.965): trim_chance_tail.py now sets their shape - each board weighted by payout^0.47 (the
natural pool gently tilted, the optimiser's fence totals and so the hit rate and RTP kept), boards
paying 120x+ at weight 1 - which keeps etl40b at 0.84 and gives a FUEL CHANCE spin 0.1-1x 17.7%,
1-2x 4.9%, 2-3x 4.1%, 3-5x 4.7%, 5-20x 6.9%, 20-120x 2.1% (left to itself the optimiser had put
27% of all chance spins on 3-5x boards). Bought FILL UP averages 96.5x, PREMIUM 289.5x, MIDNIGHT RUN 482.5x.

MIDNIGHT RUN buy (500x): the same bonus as the natural one, unweighted it averages ~1,080x (median
385x), so the lookup table weights it down to 482.5x: median 210x; under 100x 1 in 5.7, 100-500x
71%, 500-1,000x 1.2%, 1,000-5,000x 9.2% (1 in 11), 5,000-10,000x 1.2% (1 in 85), 10,000x+ 1 in
42,900, the max win 1 in 200,000; it pays its price back (500x+) 1 in 8.6 buys. The thin 500-1,000x
band is the optimiser's (value-weighted buys show the same dip just above cost in PREMIUM and
NITRO, old and new).

Base game as played: a winning spin 1 in 3.0; base-game wins 5-20x 1 in 74 spins, 20-100x 1 in
467, 100x+ 1 in 3,860; a Lighter fires 1 in 2.8 spins, a Scratch Ticket 1 in 5.2, a Gold Ticket
1 in 38, a Gas Pump REGULAR 1 in 7.0 / PLUS 1 in 20 / PREMIUM 1 in 124; two FALCOS Tokens (tease)
1 in 47, two Midnight Tokens 1 in 239; 1.3 refills (tumbleBoard) per base spin on average.

7x5 retune (strips and tables):
* Paying-symbol weights skewed harder to the lows (H 3.5/4.5/5.5/6.5, L 12/14.5/17/19.5/23; 7x7
  had H 4.5-7.5, L 12-20); NITRO strip H 1.5-3, L 8-50.
* BR0: FALCOS Tokens 2/1/2/1/2/1/1 per reel (was 1 each), Midnight Tokens 2/1/2 on reels 2/4/6
  (was 1/1/1). Natural rates: FILL UP 1 in ~390, PREMIUM 1 in ~8,000, MIDNIGHT 1 in ~16,000 (the
  published rates are the optimiser's; a PREMIUM rate of 1 in 2,700 by density alone would make
  FILL UP ~1 in 150, so the PREMIUM rate is set by the table, not the strip).
* FR0 (PREMIUM): Lighters 3/3/4/3/4/3/3, Scratch Tickets 3 per reel (were 2 and 2).
* FRM (MIDNIGHT RUN): Lighters 3/2/3/2/3/2/3, Scratch Tickets 2 per reel (were 1 and 1), pumps 3.
* FILL UP: lands FD 45 / ST 3.1 / GT 0.5 / GP 3.7 / ZP 1.2 per 1,000 blanks (was 24 / 2.2 / 0.35
  / 1.6 / 1.4); amber drops a little more often, 250 / 500 drops 0.12 / 0.03 (were 0.25 / 0.08),
  x32 / x64 pumps 1.5 / 0.3 (were 2 / 0.6).
* NITRO cells x16 600, x32 300, x64 80, x128 20, x256 5, x512 1.5, x1024 0.4, x2048 0.1 (were
  680 / 230 / 60 / 20 / 7 / 2.5 / 1 / 0.4).

Tails: the buys' 50,000x and big wins sit in their own optimiser fences with fixed returns
(FILL UP: max win 0.2 bets, 4,000x+ 0.5; PREMIUM / NITRO / MIDNIGHT RUN: max win 0.25, 10,000x+
0.35; NITRO and MIDNIGHT RUN also hold 5,000-10,000x at 1.7% / 1.2% of rounds), which keeps etl10k,
etl40b and prob5k inside the 3-star band. cap_books.py then keeps every buy board under 1 in 2,000.
