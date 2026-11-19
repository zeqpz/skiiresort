# High Peaks additions (2026-11-18): jackpots

Two new events. Everything else is the Falcos contract below.

* `jackpotDrop` `{index, type, reel, row}` - a "?" dropped over cell (reel, row) (row 1-5, padding offset as
  everywhere). Base / chance / nitro / free spins: right after `reveal`. FILL UP: after the spin's `fillUpLand` and
  its resolution. It never replaces the symbol in the cell.
* `jackpotWin` `{index, type, level, mult, amount}` - the bar stopped on `level` (`mini` `minor` `major` `grand`),
  worth `mult` x bet (10 / 50 / 250 / 2500); `amount` (hundredths of the bet) is what is paid: `mult x 100` unless
  the max win trims it. Comes after the spin's cascade, before `setWin` / `setTotalWin`; in FILL UP right after its
  `jackpotDrop`. Every `jackpotDrop` is followed by its `jackpotWin` in the same spin unless the max win was reached
  first (then the ? is simply cleared). `verify_books.py` checks all of this.

# Falcos - front-end event contract (math phase 2: 7x5 board, max win 50,000x)

**Change 2026-11-17 (owner: "let line hits come before any special symbols like the lighter. let the line pay
play out then the special symbol"):** cluster wins always come first. Each cascade step is now EITHER a cluster pay
OR one feature group, and a feature fires only when the board holds no cluster: a cluster that a refill makes is
paid before the next feature, so a feature never burns a cluster already on the board. Events and fields are
unchanged; `featureFire.step` still numbers steps (now one pay or one feature group each), and the pumps of one
step still fire together. A real book now reads: reveal -> pay -> refill -> pay -> refill -> pumps -> refill ->
pay -> refill -> ticket -> refill -> zippo -> refill ...

**Change 2026-11-13 (owner):** in FILL UP the Gold Scratch Ticket collects the whole board and then doubles its
total; `collect` carries a new `mult` (2 for a gold ticket that collected, else 1).

**Changes 2026-11-10 (owner):** (1) the board refills after the cluster pay and after EVERY feature
group - one `tumbleBoard` after the cluster pay, one after all the step's Gas Pumps, one after each
Scratch / Gold Ticket, one after each Zippo (it used to be one `tumbleBoard` per board, after every
feature had fired); (2) the LUCKY PUMP mode and its `luckyWheel` event are gone; MIDNIGHT RUN is
bought directly in the new `midnight` mode (500x). No event changed its fields: `featureFire.step`
now numbers cascade *steps* (one step = a cluster pay plus the feature groups after it, each with its
own refill), and `tumbleBoard` simply arrives more often.

Game id `falcos`. This is everything a book (and the RGS `round.state`) carries, in the order the
client must play it. The client never re-derives math: every number it shows (cluster wins, cell
multipliers, pump multipliers, drop values, collector totals, board totals, the gauge, wins) is in
these events. `verify_books.py` replays every book exactly as described here and fails on any
mismatch - if this file and the books ever disagree, the books are wrong.

Source rules: `FALCOS_DESIGN.md`. Implementation: `game_config.py`, `game_executables.py`,
`game_events.py`. Event ids for testing each feature: `library/test_books.json` (book id = LUT line =
replay `event` id; regenerate with `python verify_books.py --write-index`).

## 1. Conventions

| what | convention |
|---|---|
| positions `{reel, row}` | `reel` 0-6 left to right; `row` **1-5** top to bottom (+1 padding offset, as in the previous game). Row 0 and 6 exist only in `reveal.board` (padding symbols). The board is **7 reels x 5 rows** (35 cells). Applies to FILL UP too. |
| `gridMults` | whole 7x5 grid (7 reels x 5 rows), **reel-major** (`gridMults[reel][row]`), visible rows only, **no** padding offset (row index 0-4). Plain multipliers 1, 2, 4 ... 2048. |
| money | `win`, `amount`, `totalWin`, `winWithoutMult`: integer **hundredths of the bet** (100 = 1x). The live RGS `round.payoutMultiplier` is a plain multiple; event amounts stay hundredths. |
| drop / collector values | plain bet multiples (`0.2` = x0.2, `12.8` = x12.8). Fuel Drop colour is derived from the value: green `< 5`, amber `5 - 49.99`, red `>= 50` (a drop that grows changes colour). |
| symbols | `H1 H2 H3 H4 L1 L2 L3 L4 L5` paying; `ZP ST GT GP` features (flag `"feature": true` in reveal/tumble symbols); `BS DS` scatters (flag `"scatter": true`). FILL UP only: `FD` (with `value`), `X` blank; `ST`/`GT` there carry `value` (their total). |
| max win | 50,000x = `5000000`. |

## 2. Round structure

```
base / chance (FUEL CHANCE)
  reveal
  repeat per cascade step ("step" 0, 1, 2 ...) - a step is ONE of these, the first that applies:
      a) the board holds a cluster:
         winInfo -> updateTumbleWin -> cellMults(reason "win") -> tumbleBoard
                                         every cluster on the board pays; the paid cells leave, the refill drops in
         [wincap]                        cap reached (right after updateTumbleWin): the cascade stops
                                         here - no cellMults, no tumbleBoard, nothing else in this spin
      b) no cluster, Gas Pumps standing:
         featureFire(pump) x every pump [+ maxCells after a FULL TANK] -> tumbleBoard
                                         all the pumps fire together, then ONE refill
      c) no cluster, no pump, a Scratch / Gold Ticket standing:
         featureFire(scratch | gold) -> tumbleBoard              the first ticket only
      d) no cluster, no pump, no ticket, a Zippo standing:
         featureFire(zippo) -> tumbleBoard                       the first zippo only
      (the spin ends when the board holds neither a cluster nor a feature)
  setWin (only if the spin won; omitted when the cap was hit) -> setTotalWin
  -- bonus, if the final board shows 3+ DS (MIDNIGHT RUN) / 4+ BS (PREMIUM) / 3+ tokens with a DS among them
     (MIDNIGHT RUN, a mixed trigger since 2026-11-17: freeSpinTrigger symbol "DS", positions = every token) /
     exactly 3 BS and no DS (FILL UP) --
  [freeSpinTrigger] (PREMIUM / MIDNIGHT RUN only) -> enterBonus -> bonus events (below)
  finalWin

PREMIUM / MIDNIGHT RUN (after enterBonus)
  cellMults(reason "bonusStart")          x1 everywhere (PREMIUM) or x4 everywhere (MIDNIGHT RUN)
  10 x: updateFreeSpin -> reveal(gameType "freegame") -> cascade as above -> [setWin] -> setTotalWin
        (stops early at the max win)
  freeSpinEnd

FILL UP (after enterBonus)
  gauge(3, "start") -> fillUpLand(spin 0: the 3 opening drops)
  per spin: gauge(n-1, "use") -> fillUpLand(spin k) -> pumpBoost* -> collect* -> zippoBurn*
            -> [gauge(3, "refill") if anything new landed]
  fillUpEnd -> [setWin] -> setTotalWin -> freeSpinEnd

fillup buy (100x)   enterBonus(bought) -> FILL UP -> finalWin                 (no base spin)
premium buy (300x)  freeSpinTrigger -> enterBonus(bought) -> PREMIUM -> finalWin (no base spin)
midnight buy (500x) freeSpinTrigger(symbol "DS", positions []) -> enterBonus(reason "midnight", bought true)
                    -> MIDNIGHT RUN -> finalWin                                (no base spin)
nitro (500x)        cellMults(reason "nitro") -> reveal -> cascade -> setWin/setTotalWin -> finalWin
```

Cluster wins always come first (owner, 2026-11-17). After every refill the board is checked for
clusters again; only a board with no cluster lets the next feature fire. Feature priority on such a
board: all Gas Pumps together (consecutive `featureFire` kind `pump` events with the same `step` -
play them at once; pumps sit in different columns, so the last one's `gridMults` is the grid after
all of them), else the first Scratch / Gold Ticket, else the first Zippo. Ties go in reading order:
reel 0-6, then row top to bottom. Every `tumbleBoard` removes exactly what paid, or what the
feature group just before it burned or fired. A spin always ends on a board with no cluster and no
feature (unless the max win stopped it).

Example - event types in order:
```
0 reveal
1 winInfo (L5 x5) -> 2 updateTumbleWin -> 3 cellMults "win" -> 4 tumbleBoard          step 0: pay
5 winInfo (L2 x6) -> 6 updateTumbleWin -> 7 cellMults "win" -> 8 tumbleBoard          step 1: the refill's cluster pays first
9 featureFire pump (step 2) -> 10 featureFire pump (step 2) -> 11 tumbleBoard         step 2: both pumps together
12 featureFire scratch (step 3, target L4) -> 13 tumbleBoard                          step 3: no cluster, the ticket
14 winInfo (H2 x5) -> ... -> 17 tumbleBoard                                           step 4: a cluster the ticket's refill made
18 featureFire zippo (step 5) -> 19 tumbleBoard                                       step 5: the lighter, last
20 setWin -> 21 setTotalWin -> 22 finalWin
```

Cell multipliers: base game and NITRO reset at the start of every round (all x1, or the NITRO
preload). PREMIUM / MIDNIGHT RUN keep the grid (and MAX cells) from spin to spin for the whole bonus.

## 3. Standard SDK events

**reveal** - the board for a new spin. `board[reel]` has 7 symbols: padding, rows 1-5, padding.
`gameType` `basegame` | `freegame`. `anticipation[reel]` > 0 = slow-stop that reel (either scatter
class reached 2 on an earlier reel). `paddingPositions` = strip stops (informational).
```json
{"index":0,"type":"reveal","board":[[{"name":"L3"},{"name":"H2"},{"name":"L4"},{"name":"L2"},{"name":"L5"},{"name":"L2"},{"name":"L5"}],[{"name":"L2"},{"name":"ZP","feature":true},"..."],"..."],"paddingPositions":[97,53,24,124,7,99,110],"gameType":"basegame","anticipation":[0,0,0,0,0,0,0]}
```

**winInfo** - every cluster this board pays. `kind` = cluster size. `win` (hundredths) = `winWithoutMult x multiplier`,
except: a cluster with `meta.maxWin: true` touches a MAX cell and pays exactly what is left to reach
the max win, and any cluster may be trimmed so the round never exceeds the max win. `meta.multiplier`
= sum of the cluster's `cellMults` that are >= 2 (1 if none). `meta.cellMults[i]` belongs to
`positions[i]` (the cells' multipliers BEFORE this win doubles them).
```json
{"index":1,"type":"winInfo","totalWin":120,"wins":[{"symbol":"L4","kind":5,"win":120,"positions":[{"reel":2,"row":4},{"reel":3,"row":2},{"reel":3,"row":3},{"reel":3,"row":4},{"reel":4,"row":3}],"meta":{"clusterSize":5,"winWithoutMult":20,"multiplier":6,"cellMults":[2,1,4,1,1]}}]}
```

**updateTumbleWin** `{amount}` - running win of this spin's cascade (hundredths).
**setWin** `{amount, winLevel}` - this spin's total (emitted only when > 0 and the cap was not hit).
**setTotalWin** `{amount}` - the round's running total so far.
**wincap** `{amount: 5000000}` - the max win was reached; nothing else pays after it.
**finalWin** `{amount}` - the round's payout (= book `payoutMultiplier`).
```json
{"index":6,"type":"setWin","amount":20,"winLevel":2}
{"index":7,"type":"setTotalWin","amount":20}
{"index":9,"type":"wincap","amount":5000000}
{"index":8,"type":"finalWin","amount":20}
```

**tumbleBoard** - what just paid (the step's clusters), or what the feature group just before it
burned or fired, leaves at once and the refill drops in. `explodingSymbols` lists exactly those
cells. A step holds one `tumbleBoard` after its cluster pay, one after its pumps and one after each
ticket and each zippo. `newSymbols[reel]` = `[new top padding, new visible symbols top->bottom]`: with
k cells leaving a reel, k entries arrive; the old top padding symbol drops into view directly under
the new ones. New column (top->bottom) = `newSymbols[reel][1:] + [old padding] + survivors`.
```json
{"index":5,"type":"tumbleBoard","newSymbols":[[{"name":"L5"},{"name":"H1"}],[],[],[],[],[],[]],"explodingSymbols":[{"reel":0,"row":1},{"reel":0,"row":2}]}
```

**freeSpinTrigger** `{totalFs: 10, symbol: "BS"|"DS", positions}` - PREMIUM / MIDNIGHT RUN awarded; the
scatter cells that did it (`[]` when bought).
**updateFreeSpin** `{amount, total}` - `amount` = the spin about to play, **1-based** (1..10).
**freeSpinEnd** `{amount, winLevel}` - total won inside the bonus (also closes FILL UP).
```json
{"index":1,"type":"freeSpinTrigger","totalFs":10,"symbol":"DS","positions":[]}
{"index":7,"type":"updateFreeSpin","amount":1,"total":10}
{"index":65,"type":"freeSpinEnd","amount":31250,"winLevel":7}
```

**enterBonus** `{reason: "fillup"|"premium"|"midnight", bought, positions}` - `positions` = trigger
scatter cells (`[]` when bought). MIDNIGHT RUN comes from 3 DS in base / chance, or is bought in
the `midnight` mode (`bought: true`, preceded by `freeSpinTrigger` symbol `DS`, positions `[]`).
```json
{"index":0,"type":"enterBonus","reason":"fillup","bought":true,"positions":[]}
```

## 4. Custom events - board games

**cellMults** - the grid changed for a reason other than a feature. `reason`:
`win` (the cells of the clusters just paid doubled; right after their `winInfo`), `nitro` (NITRO
preload, first event of the round, before `reveal`), `bonusStart` (PREMIUM x1 / MIDNIGHT RUN x4
grid, after `enterBonus`). `changed` lists `{reel,row,from,to}` (empty for nitro / bonusStart: take
the whole `gridMults`). `maxCells` = every MAX cell live now.
```json
{"index":3,"type":"cellMults","reason":"win","changed":[{"reel":2,"row":4,"from":1,"to":2},{"reel":3,"row":2,"from":1,"to":2},{"reel":3,"row":3,"from":1,"to":2},{"reel":3,"row":4,"from":1,"to":2},{"reel":4,"row":3,"from":1,"to":2}],"gridMults":[[1,1,1,1,1],[1,1,1,1,1],[1,1,1,2,1],[1,2,2,2,1],[1,1,2,1,1],[1,1,1,1,1],[1,1,1,1,1]],"maxCells":[]}
```

**featureFire** - one feature symbol fired (it always leaves in the next `tumbleBoard`, which
follows it directly - or, for pumps, follows the last pump of the step).
Fields: `step` (cascade step, 0 = the reveal's; several boards share a step since the board refills
after every feature group), `kind` `zippo|scratch|gold|pump`, `reel,row` (the feature's cell on the
board as it is now - the refills before it may have moved it down its reel), `cells` = every
multiplier change `{reel,row,from,to}` in the order applied, `burned` = paying symbols it burned
`{reel,row,symbol}`, `gridMults` = the grid after it.
* `zippo`: `cells` = its 3x3 (clipped at the edges), each doubled. Burns paying symbols there;
  scatters / features stay.
* `scratch`: `target` = the paying symbol scratched off (`null` if none were left standing); every
  cell holding it doubles and burns, then the ticket's own cell doubles.
* `gold`: every paying symbol still standing doubles and burns, then the ticket's own cell doubles.
* `pump`: `grade` `regular|plus|premium|fulltank`, `mult` 2/4 | 8/16 | 32/64 | `null`. `cells` = the
  whole column, `to = min(from x mult, 2048)`; FULL TANK leaves the numbers alone (`from == to`)
  and is followed by `maxCells`. Burns the column's paying symbols in every grade.
```json
{"index":4,"type":"featureFire","step":0,"kind":"pump","reel":2,"row":5,"grade":"premium","mult":32,"cells":[{"reel":2,"row":1,"from":1,"to":32},{"reel":2,"row":2,"from":1,"to":32},{"reel":2,"row":3,"from":2,"to":64},{"reel":2,"row":4,"from":2,"to":64},{"reel":2,"row":5,"from":1,"to":32}],"burned":[{"reel":2,"row":1,"symbol":"H1"},{"reel":2,"row":2,"symbol":"H4"}],"gridMults":[[1,1,1,1,1],[1,2,2,1,1],[32,32,64,64,32],[2,2,1,2,1],[2,1,1,1,1],[2,1,1,1,1],[2,1,1,1,1]]}
{"index":2,"type":"featureFire","step":0,"kind":"scratch","reel":5,"row":4,"target":"L2","cells":[{"reel":1,"row":2,"from":1,"to":2},{"reel":5,"row":4,"from":1,"to":2}],"burned":[{"reel":1,"row":2,"symbol":"L2"}],"gridMults":"..."}
{"index":6,"type":"featureFire","step":0,"kind":"zippo","reel":6,"row":1,"cells":[{"reel":5,"row":1,"from":2,"to":4},{"reel":5,"row":2,"from":4,"to":8},{"reel":6,"row":1,"from":2,"to":4},{"reel":6,"row":2,"from":2,"to":4}],"burned":[],"gridMults":"..."}
```

**maxCells** - a FULL TANK turned its column into MAX cells. `added` = this column, `cells` = every
MAX cell live now. Any later cluster covering a MAX cell pays the max win (`winInfo` `meta.maxWin`).
In PREMIUM / MIDNIGHT RUN MAX cells persist for the rest of the bonus.
```json
{"index":14,"type":"maxCells","added":[{"reel":1,"row":1},{"reel":1,"row":2},{"reel":1,"row":3},{"reel":1,"row":4},{"reel":1,"row":5}],"cells":[{"reel":1,"row":1},{"reel":1,"row":2},{"reel":1,"row":3},{"reel":1,"row":4},{"reel":1,"row":5}]}
```

## 5. Custom events - FILL UP

The FILL UP board is its own 7x5 (7 columns x 5 rows, no reels, no cell multipliers). Track it from these events.
Every event carries `boardTotal` = sum of every drop and collector value on the board after it.

**gauge** `{fuel: 0-3, reason: "start"|"use"|"refill"}` - start full; each spin uses one bar; a spin
that landed anything (drop or feature) refills to 3.
```json
{"index":5,"type":"gauge","fuel":2,"reason":"use"}
```

**fillUpLand** `{spin, cells, boardTotal}` - `spin` 0 = the 3 opening drops (the triggering tokens
become drops; a bought FILL UP gets the same), then 1, 2, 3 ... `cells` = **every cell that was
empty** before the spin with what landed: `X`, `FD` (+`value`), `ST`/`GT` (+`value` 0), `GP`, `ZP`.
Drops and collectors stay; `GP`/`ZP` resolve in the events that follow and leave.
```json
{"index":126,"type":"fillUpLand","spin":46,"cells":[{"reel":1,"row":3,"name":"X"}],"boardTotal":80.7}
```

**pumpBoost** - a Gas Pump multiplied every drop in its column (including drops that landed with it)
and every collector there that collected on an earlier spin, then left. `boosted` = `{reel,row,name,from,to}`.
```json
{"index":5,"type":"pumpBoost","reel":5,"row":4,"mult":4,"boosted":[],"boardTotal":7}
```

**collect** - a ticket collected. `kind` `scratch` (its 8 neighbours) | `gold` (whole board). It takes
every drop there plus every collector that collected on an EARLIER spin; `collected` =
`{reel,row,name,value}` (those cells empty), `total` = the collector's new value. `removed: true` =
nothing to collect, the ticket left (its cell is empty). `mult` (2026-11-13): a **gold** ticket that collected
doubles its total - `total = (its value + the collected values) x mult`, `mult` 2; a scratch ticket (and a gold one
that found nothing) has `mult` 1.
```json
{"index":5,"type":"collect","kind":"scratch","reel":1,"row":4,"collected":[{"reel":0,"row":4,"name":"FD","value":3}],"total":3,"mult":1,"removed":false,"boardTotal":16}
{"index":8,"type":"collect","kind":"scratch","reel":3,"row":1,"collected":[],"total":0,"mult":1,"removed":true,"boardTotal":8}
```

**zippoBurn** - a Zippo burned every Fuel Drop in its 3x3 (never collectors) and left.
```json
{"index":6,"type":"zippoBurn","reel":4,"row":2,"burned":[{"reel":3,"row":3,"value":1}],"boardTotal":15}
```

**fillUpEnd** - `reason` `empty` (gauge ran out) | `full` (no empty cell left) | `wincap`. `spins` =
spins played. `drops` / `collectors` = what is left, `boardTotal` their sum, `win` (hundredths) =
what FILL UP pays: `boardTotal` capped at the max win (minus anything the round already won).
```json
{"index":21,"type":"fillUpEnd","reason":"empty","spins":7,"drops":[],"collectors":[{"reel":3,"row":2,"name":"GT","value":11.2}],"boardTotal":11.2,"win":1120}
```

## 6. Rules the books follow (decisions where FALCOS_DESIGN.md is not specific)

* Cluster wins are evaluated through the multipliers the cells hold before the win; the cells of
  every paid cluster then double. Paying symbols burned by a feature simply clear; their cells keep
  the boosted multiplier for whatever tumbles in.
* Cascade: cluster wins first (owner, 2026-11-17). Each step pays every cluster on the board and
  refills, or - only on a board with no cluster - fires one feature group and refills: all Gas
  Pumps together, else the first Scratch / Gold Ticket, else the first Zippo (reading order; a
  tumble keeps it, since symbols only fall within their reel). The board refills after every pay
  and every group (owner, 2026-11-10: no cell sits empty while the next one fires), and is checked
  for clusters again before the next feature. The spin ends on a board with neither a cluster nor
  a feature. Each feature fires once and leaves in the refill right after its group.
  Features never burn scatters or other features.
* Scratch Ticket target: uniform among the paying symbol types standing on the (refilled) board.
  Gold Ticket: every paying symbol on the (refilled) board.
* Gas Pump multiplier is applied to the cell (`to = from x mult`), cap x2048. FULL TANK: the column's
  cells become MAX cells (the column's paying symbols burn so fresh symbols drop onto them); a
  cluster **covering** a MAX cell pays the max win (`meta.maxWin`, win = room left to the cap).
* Scatters are counted on the board a base spin ENDS on (they never burn, so tumbles can add
  more). 3+ DS -> MIDNIGHT RUN (outranks the rest); 4+ BS -> PREMIUM; exactly 3 BS -> FILL UP.
  PREMIUM / MIDNIGHT RUN: 10 spins, no retriggers (their strips carry no scatters).
* MIDNIGHT RUN plays a strip with 3x the Gas Pumps (and fewer doublers than PREMIUM's); grids start
  at x4.
* MIDNIGHT RUN buy (`midnight`, 500x): the same bonus as the natural one (FRM strip, grid starts
  x4, 10 spins, no retriggers); the book starts as a bought PREMIUM does (`freeSpinTrigger` symbol
  `DS` with no positions, then `enterBonus` reason `midnight`, bought `true`). Its lookup table
  weights the books so the mode returns 96.50% (482.5x on average).
* Board 7 reels x 5 rows. A Gas Pump's column is 5 cells; a Zippo's 3x3 is clipped at the edges;
  FILL UP's board is 35 cells; NITRO preloads all 35 cells.
* NITRO SPIN: every cell preloaded x16..x2048 (powers of two, heavy at x16); a scatter-free strip
  that leans on the lows, so it cannot trigger a bonus and wins about 4 times in 5.
* FILL UP: opens with 3 Fuel Drops; each spin every empty cell rolls blank / drop / feature
  independently (at most one pump per column per spin). Resolution order per spin: pumps, tickets,
  zippos. A collector that finds nothing leaves. Board full -> the bonus ends.
* Paytable: the owner-approved tenths table (FALCOS_DESIGN.md, 2026-11-09). Every pay is a whole
  number of tenths and a cluster multiplier is 1 or even, so every win sits on the RGS's 0.1x grid
  with no rounding. The rules screen shows exactly `config_fe_falcos.json`'s symbols paytable.

## 7. Not in the books (client-side only)

* Win celebrations tiers: use `winLevel` or the amounts; none of it changes the math.
* Base-game cell reset: a new base/chance round starts with every cell at x1 (no event).
* `round.state` on the live RGS is this `events` array; `payoutMultiplier` there is plain, not hundredths.
