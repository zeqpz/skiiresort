"""Replay every Falcos book the way the client must, and check the event contract (EVENTS.md).

    python verify_books.py                  # all modes in library/publish_files
    python verify_books.py --modes base     # a subset
    python verify_books.py --write-index    # also write library/test_books.json (book ids per feature)

It tracks the board (reveal + tumbleBoard), the cell-multiplier grid (cellMults / featureFire),
MAX cells, the FILL UP board and gauge, and checks that every number the events carry follows
from the ones before it: cluster pays and multipliers, doublings, pump multipliers, collector
totals, board totals, setWin/setTotalWin/finalWin and the book's payoutMultiplier. It also checks
the cascade order (EVENTS.md section 2): cluster wins come first - a feature fires only on a board
that holds no cluster - and then one feature group at a time (every Gas Pump standing together,
else the first ticket, else the first zippo, in reading order); the board refills after each pay
and each group, each tumbleBoard removes exactly the cells that paid / burned / fired since the
last one, and a spin ends on a board with no cluster and no feature left. Any failure is a math bug (or a contract change EVENTS.md has to follow).
"""

import argparse
import io
import json
import os
import sys
from collections import defaultdict

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from game_config import GameConfig, PAYING  # noqa: E402

PUBLISH = os.path.join(HERE, "library", "publish_files")
CAP = 2048
FEATURES = ("ZP", "ST", "GT", "GP")
_CFG = GameConfig()
WINCAP = int(round(_CFG.wincap * 100))
MAX_FS = _CFG.max_free_spins   # hundredths (max win 50,000x = 5,000,000)
NR, NC = _CFG.num_reels, _CFG.num_rows[0]   # 7 reels x 5 rows


class Fail(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


def read_books(mode):
    path = os.path.join(PUBLISH, f"books_{mode}.jsonl.zst")
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    for line in io.BytesIO(data):
        if line.strip():
            yield json.loads(line)


class Replay:
    def __init__(self, paytable, cfg=None):
        self.pay = paytable
        self.cfg = cfg

    def run(self, book, tags):
        ev = book["events"]
        for i, e in enumerate(ev):
            check(e["index"] == i, f"event index {e['index']} != {i}")
        self.grid = [[1] * NC for _ in range(NR)]
        self.maxc = set()
        self.board = None
        self.pad = None
        self.paid = 0               # hundredths paid by winInfo + fillUpEnd
        self.last_total = 0
        self.last_wins = []
        self.fs_seen = 0
        self.fs_total = 10
        self.retrig_at = None       # the free spin a retrigger was given for
        self.fill = None
        self.fuel = None
        self.fuel_at_land = None
        self.refilled = False
        self.bonuses = []
        self.uid = None             # a token per visible symbol: survivors keep theirs in a tumble
        self.next_uid = 0
        self.pending = set()        # cells that paid / burned / fired and wait for their tumbleBoard
        self.pending_kind = None
        self.step = None            # current cascade step's feature part: step, snapshot, fired, rank
        self.capped = False
        self.spin_open = False
        self.jp_drop = False        # a "?" is on the board, waiting for its jackpotWin
        final = None
        for e in ev:
            t = e["type"]
            getattr(self, "on_" + t, self.on_unknown)(e, tags)
            if t == "setTotalWin":
                self.last_total = e["amount"]
            if t == "finalWin":
                final = e["amount"]
        check(final is not None, "no finalWin")
        check(final == book["payoutMultiplier"], f"finalWin {final} != payoutMultiplier {book['payoutMultiplier']}")
        check(final == min(self.paid, WINCAP), f"finalWin {final} != paid {self.paid}")
        check(self.last_total == final, f"last setTotalWin {self.last_total} != finalWin {final}")
        check(final % 10 == 0, f"payout {final} not a 0.1x step")
        check(not self.pending or self.capped, "cells left waiting for a tumbleBoard at the end of the round")
        if final >= WINCAP:
            tags.add("wincap")
        if final == 0:
            tags.add("loss")

    def fresh(self):
        self.next_uid += 1
        return self.next_uid

    def close_step(self):
        """A feature step is over: the group it had to fire (every pump standing, or the one
        ticket / zippo next in line) fired in full."""
        if self.step is not None:
            st, want, fired = self.step
            check(fired == want, f"step {st}: features {sorted(want - fired)} of its group never fired")
            self.step = None

    def has_cluster(self):
        seen = set()
        for r in range(NR):
            for c in range(NC):
                if (r, c) in seen or self.board[r][c] not in PAYING:
                    continue
                stack, size = [(r, c)], 0
                seen.add((r, c))
                while stack:
                    x, y = stack.pop()
                    size += 1
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if 0 <= nx < NR and 0 <= ny < NC and (nx, ny) not in seen and self.board[nx][ny] == self.board[r][c]:
                            seen.add((nx, ny))
                            stack.append((nx, ny))
                if size >= 5:
                    return True
        return False

    def end_of_spin(self):
        """A spin's cascade ends only on a board with no cluster and no feature (or at the cap)."""
        self.close_step()
        check(not self.pending, "spin ended with cells waiting for a tumbleBoard")
        if self.capped:
            return
        check(not any(n in FEATURES for col in self.board for n in col), "spin ended with a feature on the board")
        check(not self.has_cluster(), "spin ended on a board that still holds a cluster")

    def on_unknown(self, e, tags):
        raise Fail(f"unknown event type {e['type']}")

    # -------------------------------------------------------------- board games
    def on_reveal(self, e, tags):
        b = e["board"]
        check(len(b) == NR and all(len(col) == NC + 2 for col in b), f"reveal must be {NR} reels x {NC + 2} (padded) rows")
        check(not self.pending and not self.spin_open, "reveal before the last spin finished")
        self.pad = [col[0]["name"] for col in b]
        self.board = [[s["name"] for s in col[1:NC + 1]] for col in b]
        self.uid = [[self.fresh() for _ in range(NC)] for _ in range(NR)]
        self.step = None
        self.spin_open = True
        names = [n for col in self.board for n in col]
        if names.count("DS") == 2:
            tags.add("ds_tease")
        if names.count("BS") == 2:
            tags.add("bs_tease")
        if e["gameType"] == "freegame":
            check(self.fs_seen > 0, "freegame reveal before updateFreeSpin")
        for r, col in enumerate(self.board):
            for c, n in enumerate(col):
                if n in ("ZP", "ST", "GT", "GP"):
                    check(b[r][c + 1].get("feature") is True, "feature symbol missing feature flag")
                if n in ("BS", "DS"):
                    check(b[r][c + 1].get("scatter") is True, "scatter missing scatter flag")

    def on_winInfo(self, e, tags):
        self.close_step()
        check(not self.pending, "winInfo while earlier cells still wait for their tumbleBoard")
        total = 0
        self.last_wins = []
        for w in e["wins"]:
            pos = [(p["reel"], p["row"] - 1) for p in w["positions"]]
            check(all(0 <= c < NC for _, c in pos), f"win position row out of 1..{NC}")
            check(all(self.board[r][c] == w["symbol"] for r, c in pos), "win positions do not hold the symbol")
            check(w["kind"] == len(pos) == w["meta"]["clusterSize"], "cluster size mismatch")
            cm = [self.grid[r][c] for r, c in pos]
            check(cm == w["meta"]["cellMults"], f"cellMults {w['meta']['cellMults']} != grid {cm}")
            boosted = [m for m in cm if m >= 2]
            mult = sum(boosted) if boosted else 1
            check(mult == w["meta"]["multiplier"], "multiplier is not the sum of the x2+ cells")
            pay = int(round(self.pay[(len(pos), w["symbol"])] * 100))
            check(pay == w["meta"]["winWithoutMult"], "winWithoutMult != paytable")
            touches = any(p in self.maxc for p in pos)
            check(bool(w["meta"].get("maxWin")) == touches, "maxWin flag vs MAX cells mismatch")
            if touches:
                tags.add("max_cluster")
            else:
                check(w["win"] <= pay * mult, "win above pay x multiplier")
                if w["win"] != pay * mult:
                    check(self.paid + total + w["win"] <= WINCAP, "trimmed win below cap")
            if mult >= 2:
                tags.add("multiplied_win")
            total += w["win"]
            self.last_wins.extend(pos)
        check(total == e["totalWin"], "winInfo totalWin != sum of wins")
        self.paid += total
        self.pending = set(self.last_wins)
        self.pending_kind = "win"
        tags.add("cluster_win")

    def on_updateTumbleWin(self, e, tags):
        pass

    def on_setWin(self, e, tags):
        pass

    # -------------------------------------------------------------- jackpots
    def on_jackpotDrop(self, e, tags):
        check(self.spin_open or self.fill is not None, "jackpotDrop outside a spin")
        check(not self.jp_drop, "a second jackpotDrop before the first one paid")
        check(0 <= e["reel"] < NR and 1 <= e["row"] <= NC, "jackpotDrop cell off the board")
        self.jp_drop = True
        tags.add("jackpot_drop")

    def on_jackpotWin(self, e, tags):
        check(self.jp_drop, "jackpotWin without a jackpotDrop")
        check(not self.pending, "jackpotWin before the cascade finished")
        vals = self.cfg.jackpot_values
        check(e["level"] in vals and e["mult"] == vals[e["level"]], f"jackpot level/mult {e['level']} {e['mult']}")
        expect = min(e["mult"] * 100, WINCAP - self.paid)
        check(e["amount"] == expect, f"jackpotWin amount {e['amount']} != {expect}")
        self.paid += e["amount"]
        self.jp_drop = False
        tags.add(f"jackpot_{e['level']}")

    def on_setTotalWin(self, e, tags):
        check(e["amount"] == min(self.paid, WINCAP), f"setTotalWin {e['amount']} != paid {self.paid}")
        check(not self.jp_drop or self.capped, "a jackpot \"?\" left unpaid at the end of a spin")
        if self.spin_open:
            self.end_of_spin()
            self.spin_open = False

    def on_wincap(self, e, tags):
        check(e["amount"] == WINCAP, "wincap amount")
        self.capped = True
        self.pending = set()

    def on_finalWin(self, e, tags):
        pass

    def _apply_grid(self, e, changed):
        g = [row[:] for row in self.grid]
        for r, c, a, b in changed:
            check(g[r][c] == a, f"cell ({r},{c}) from {a} but grid holds {g[r][c]}")
            g[r][c] = b
        check(g == e["gridMults"], "gridMults does not match the changes listed")
        self.grid = g

    def on_cellMults(self, e, tags):
        ch = [(x["reel"], x["row"] - 1, x["from"], x["to"]) for x in e["changed"]]
        if e["reason"] == "win":
            check(sorted((r, c) for r, c, _, _ in ch) == sorted(set(self.last_wins)), "doubled cells != cluster cells")
            check(all(b == min(a * 2, CAP) for _, _, a, b in ch), "win doubling wrong")
            self._apply_grid(e, ch)
        else:
            self.grid = [row[:] for row in e["gridMults"]]
            tags.add(f"cellmults_{e['reason']}")
            if e["reason"] == "bonusStart":
                self.maxc = set()
        check({(p["reel"], p["row"] - 1) for p in e["maxCells"]} == self.maxc, "cellMults maxCells mismatch")

    def on_featureFire(self, e, tags):
        r, c = e["reel"], e["row"] - 1
        kind = e["kind"]
        sym = {"zippo": "ZP", "scratch": "ST", "gold": "GT", "pump": "GP"}[kind]
        check(self.board[r][c] == sym, f"featureFire {kind} at a cell holding {self.board[r][c]}")
        # order: wins first - a feature fires only once the board is refilled and holds no cluster;
        # then one group: every pump standing (together, one tumbleBoard after the last of them),
        # else the first ticket, else the first zippo (reading order: reel by reel, top to bottom)
        if self.step is not None and self.step[0] != e["step"]:
            self.close_step()
        if self.step is None:
            check(not self.pending, f"{kind} fired before the cells that paid/burned were refilled")
            check(not self.has_cluster(), f"{kind} fired while the board held an unpaid cluster")
            standing = [(x, y) for x in range(NR) for y in range(NC) if self.board[x][y] in FEATURES]
            groups = ([p for p in standing if self.board[p[0]][p[1]] == "GP"],
                      [p for p in standing if self.board[p[0]][p[1]] in ("ST", "GT")][:1],
                      [p for p in standing if self.board[p[0]][p[1]] == "ZP"][:1])
            want = next((g for g in groups if g), [])
            self.step = [e["step"], {self.uid[x][y] for x, y in want}, set()]
        else:
            together = kind == "pump" and self.pending_kind == "pump"
            check(together, f"{kind} fired in the same step as another group")
        st = self.step
        check(self.uid[r][c] in st[1], f"step {st[0]}: {kind} at ({r},{c}) is not the feature next in line")
        check(self.uid[r][c] not in st[2], "a feature fired twice")
        st[2].add(self.uid[r][c])
        ch = [(x["reel"], x["row"] - 1, x["from"], x["to"]) for x in e["cells"]]
        burned = [(x["reel"], x["row"] - 1, x["symbol"]) for x in e["burned"]]
        for a, b, s in burned:
            check(self.board[a][b] == s and s in PAYING, "burned cell does not hold that paying symbol")
        if kind == "pump":
            tags.add(f"pump_{e['grade']}")
            check(sorted((a, b) for a, b, _, _ in ch) == [(r, y) for y in range(NC)], "pump cells != its column")
            if e["grade"] == "fulltank":
                check(e["mult"] is None and all(f == t for _, _, f, t in ch), "fulltank changes no multiplier")
            else:
                check(all(t == min(f * e["mult"], CAP) for _, _, f, t in ch), "pump multiplier wrong")
            check(all(a == r for a, _, _ in burned), "pump burned outside its column")
        else:
            check(all(t == min(f * 2, CAP) for _, _, f, t in ch), f"{kind} doubling wrong")
            tags.add(kind)
            if kind == "zippo":
                area = {(x, y) for x in range(r - 1, r + 2) for y in range(c - 1, c + 2) if 0 <= x < NR and 0 <= y < NC}
                check({(a, b) for a, b, _, _ in ch} == area, "zippo cells != its 3x3")
            if kind == "scratch" and e.get("target"):
                check(all(s == e["target"] for _, _, s in burned), "scratch burned another symbol")
        # sequential: a cell may appear more than once in one event only if listed in order
        g = [row[:] for row in self.grid]
        for a, b, f, t in ch:
            check(g[a][b] == f, f"{kind}: cell ({a},{b}) from {f} but grid holds {g[a][b]}")
            g[a][b] = t
        check(g == e["gridMults"], f"{kind}: gridMults mismatch")
        self.grid = g
        self.pending |= {(r, c)} | {(a, b) for a, b, _ in burned}
        self.pending_kind = "pump" if kind == "pump" else kind

    def on_maxCells(self, e, tags):
        added = {(p["reel"], p["row"] - 1) for p in e["added"]}
        self.maxc |= added
        check({(p["reel"], p["row"] - 1) for p in e["cells"]} == self.maxc, "maxCells.cells mismatch")
        tags.add("max_cells")

    def on_tumbleBoard(self, e, tags):
        expl = defaultdict(list)
        for p in e["explodingSymbols"]:
            expl[p["reel"]].append(p["row"] - 1)
        cells = {(p["reel"], p["row"] - 1) for p in e["explodingSymbols"]}
        check(len(cells) == len(e["explodingSymbols"]), "explodingSymbols lists a cell twice")
        check(cells and cells == self.pending,
              f"tumbleBoard removes {sorted(cells)} but {sorted(self.pending)} paid/burned/fired since the last one")
        if self.pending_kind == "win" and self.step is None:
            tags.add("refill_after_win")
        elif self.pending_kind != "win":
            tags.add(f"refill_after_{self.pending_kind}")
        self.pending = set()
        for r in range(NR):
            k = len(expl[r])
            new = [s["name"] for s in e["newSymbols"][r]]
            # SDK convention: newSymbols[reel] = [new top padding, new visible symbols top->bottom];
            # the old top padding drops into view under them, so k exploding -> k entries
            check(len(new) == k, f"reel {r}: {k} exploding but {len(new)} new symbols")
            if k:
                survivors = [n for c, n in enumerate(self.board[r]) if c not in expl[r]]
                keep = [u for c, u in enumerate(self.uid[r]) if c not in expl[r]]
                self.board[r] = new[1:] + [self.pad[r]] + survivors
                self.uid[r] = [self.fresh() for _ in range(k)] + keep
                self.pad[r] = new[0]
                check(len(self.board[r]) == NC, "column length after tumble")

    # -------------------------------------------------------------- bonuses
    def on_freeSpinTrigger(self, e, tags):
        check(e["totalFs"] == 10, "totalFs")
        self.fs_total = 10
        held = [self.board[p["reel"]][p["row"] - 1] for p in e["positions"]]
        if all(h == e["symbol"] for h in held):
            pass
        else:   # a mixed trigger (2026-11-17): 3+ tokens with a DS among them, MIDNIGHT RUN
            check(e["symbol"] == "DS" and all(h in ("BS", "DS") for h in held) and len(held) >= 3
                  and 1 <= held.count("DS") < 3 and held.count("BS") < 4, "trigger position does not hold the scatter")
            tags.add("mixed_trigger")

    def on_enterBonus(self, e, tags):
        tags.add(f"bonus_{e['reason']}" + ("_bought" if e["bought"] else ""))
        self.bonuses.append(e["reason"])
        self.fs_seen = 0

    def owed_retrigger(self):
        """The free spin just played ended on 3+ FALCOS Tokens: a retrigger must have followed it."""
        if self.fs_seen and self.board is not None and not self.capped and self.fs_total < MAX_FS:
            n = sum(n == "BS" for col in self.board for n in col)
            check(n < 3 or self.retrig_at == self.fs_seen, f"free spin {self.fs_seen} ended on {n} FALCOS Tokens but no retrigger")

    def on_updateFreeSpin(self, e, tags):
        self.owed_retrigger()
        self.fs_seen += 1
        check(e["amount"] == self.fs_seen and e["total"] == self.fs_total, "updateFreeSpin numbering")

    def on_freeSpinRetrigger(self, e, tags):
        check(not self.spin_open, "retrigger before the spin's cascade finished")
        check(self.retrig_at != self.fs_seen, "two retriggers for one spin")
        tok = sorted((r, c) for r in range(NR) for c in range(NC) if self.board[r][c] == "BS")
        check(sorted((p["reel"], p["row"] - 1) for p in e["positions"]) == tok and len(tok) >= 3, "retrigger positions != the FALCOS Tokens")
        check(e["symbol"] == "BS" and e["added"] == min(5, MAX_FS - self.fs_total), "retrigger adds 5 spins")
        self.fs_total += e["added"]
        check(e["totalFs"] == self.fs_total and self.fs_total <= MAX_FS, "retrigger totalFs")
        self.retrig_at = self.fs_seen
        tags.add("retrigger")

    def on_freeSpinEnd(self, e, tags):
        if self.fill is None:
            self.owed_retrigger()
            check(self.fs_seen == self.fs_total or self.capped, f"bonus ended after {self.fs_seen} of {self.fs_total} spins")

    # -------------------------------------------------------------- FILL UP
    def ftotal(self):
        return round(sum(v.get("value", 0) for v in self.fill.values()), 2)

    def on_gauge(self, e, tags):
        if e["reason"] == "start":
            check(e["fuel"] == 3, "gauge starts full")
            self.fill = {}
        elif e["reason"] == "use":
            self.owed_refill()
            check(e["fuel"] == self.fuel - 1, "gauge use must drop one bar")
            self._fresh_clear()     # a collector is "fresh" only on the spin it lands
        elif e["reason"] == "retrigger":
            check(e["fuel"] == self.fuel, "retrigger gauge != the fillUpRetrigger's fuel")
        else:
            check(e["fuel"] == 3 and self.fuel < 3, "refill to 3, only from below 3")
            check(self.landed, "refill without anything new")
            self.refilled = True
        self.fuel = e["fuel"]

    def owed_refill(self):
        """Anything new landing on a spin refills the gauge to 3 when it was lower."""
        if self.landed and self.fuel_at_land is not None and self.fuel_at_land < 3:
            check(self.refilled, "something landed but the gauge was not refilled")
        self.landed = False

    def on_fillUpRetrigger(self, e, tags):
        pos = (e["reel"], e["row"] - 1)
        check(self.fill.get(pos, {}).get("name") == "BS", "fillUpRetrigger from a cell without a FALCOS Token")
        check(e["added"] == 5 and e["fuel"] == self.fuel + 5, "FILL UP retrigger adds 5 spins")
        check(self.landed and (self.refilled or self.fuel_at_land >= 3), "retrigger before the refill")
        del self.fill[pos]
        self.fuel = e["fuel"]
        tags.add("fill_retrigger")

    def on_fillUpLand(self, e, tags):
        self.landed = False
        self.refilled = False
        self.fuel_at_land = self.fuel
        for x in e["cells"]:
            pos = (x["reel"], x["row"] - 1)
            check(pos not in self.fill, "landed on an occupied cell")
            if x["name"] != "X":
                item = {"name": x["name"]}
                if "value" in x:
                    item["value"] = x["value"]
                if x["name"] in ("ST", "GT"):
                    item["fresh"] = True
                self.fill[pos] = item
                if e["spin"] > 0:
                    self.landed = True
                tags.add(f"fill_land_{x['name']}")
                if x["name"] == "FD":
                    v = x["value"]
                    tags.add("fd_green" if v < 5 else "fd_amber" if v < 50 else "fd_red")
        if e["spin"] > 0:
            check(self.fuel is not None, "spin before gauge")
            empty = NR * NC - len([1 for p in self.fill if p not in {(c["reel"], c["row"] - 1) for c in e["cells"]}])
            check(len(e["cells"]) == empty, "fillUpLand must list every empty cell")
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "fillUpLand boardTotal")

    def on_pumpBoost(self, e, tags):
        pos = (e["reel"], e["row"] - 1)
        check(self.fill.get(pos, {}).get("name") == "GP", "pumpBoost from a non-pump cell")
        for x in e["boosted"]:
            item = self.fill[(x["reel"], x["row"] - 1)]
            check(x["reel"] == e["reel"], "pump boosted outside its column")
            check(abs(item["value"] - x["from"]) < 1e-6, "pump from value")
            check(abs(round(x["from"] * e["mult"], 2) - x["to"]) < 1e-6, "pump to value")
            item["value"] = x["to"]
        del self.fill[pos]
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "pumpBoost boardTotal")
        tags.add("fill_pump")

    def on_collect(self, e, tags):
        pos = (e["reel"], e["row"] - 1)
        me = self.fill.get(pos)
        check(me and me["name"] == ("ST" if e["kind"] == "scratch" else "GT"), "collector cell")
        got = 0
        for x in e["collected"]:
            p = (x["reel"], x["row"] - 1)
            item = self.fill.get(p)
            check(item and abs(item["value"] - x["value"]) < 1e-6 and not item.get("fresh"), "collected item mismatch")
            if e["kind"] == "scratch":
                check(max(abs(p[0] - pos[0]), abs(p[1] - pos[1])) == 1, "scratch collected beyond its neighbours")
            got += x["value"]
            del self.fill[p]
        mult = 2 if (e["kind"] == "gold" and e["collected"]) else 1      # GT doubles what it collected (2026-11-13)
        check(e.get("mult", 1) == mult, "collect mult")
        check(abs(round(round(me["value"] + got, 2) * mult, 2) - e["total"]) < 1e-6, "collector total")
        check(e["removed"] == (not e["collected"]), "removed flag")
        if e["removed"]:
            del self.fill[pos]
        else:
            me["value"] = e["total"]
            tags.add(f"fill_collect_{e['kind']}")
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "collect boardTotal")

    def on_zippoBurn(self, e, tags):
        pos = (e["reel"], e["row"] - 1)
        check(self.fill.get(pos, {}).get("name") == "ZP", "zippoBurn from a non-zippo cell")
        for x in e["burned"]:
            p = (x["reel"], x["row"] - 1)
            check(max(abs(p[0] - pos[0]), abs(p[1] - pos[1])) <= 1, "zippo burned beyond its 3x3")
            check(self.fill[p]["name"] == "FD", "zippo burned a non-drop")
            del self.fill[p]
        del self.fill[pos]
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "zippoBurn boardTotal")
        if e["burned"]:
            tags.add("fill_zippo_burn")

    def on_fillUpEnd(self, e, tags):
        self.owed_refill()
        for item in self.fill.values():
            item.pop("fresh", None)
        check(all(v["name"] in ("FD", "ST", "GT") for v in self.fill.values()), "leftover pump/zippo on the board")
        drops = sorted((x["reel"], x["row"] - 1, x["value"]) for x in e["drops"])
        mine = sorted((p[0], p[1], v["value"]) for p, v in self.fill.items() if v["name"] == "FD")
        check(drops == mine, "fillUpEnd drops mismatch")
        check(abs(e["boardTotal"] - self.ftotal()) < 1e-6, "fillUpEnd boardTotal")
        expect = min(int(round(e["boardTotal"] * 100)), WINCAP - self.paid)
        check(e["win"] == expect, f"fillUpEnd win {e['win']} != {expect}")
        self.paid += e["win"]
        tags.add(f"fillup_end_{e['reason']}")
        if e["collectors"]:
            tags.add("fillup_end_with_collector")

    def _fresh_clear(self):
        for item in self.fill.values():
            item.pop("fresh", None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=None)
    ap.add_argument("--write-index", action="store_true")
    args = ap.parse_args()
    cfg = GameConfig()
    with open(os.path.join(PUBLISH, "index.json"), encoding="utf-8") as fh:
        modes = [m["name"] for m in json.load(fh)["modes"]]
    if args.modes:
        modes = [m for m in modes if m in args.modes]
    rp = Replay(cfg.paytable, cfg)
    index = {}
    bad = 0
    for mode in modes:
        coverage = defaultdict(list)
        n = 0
        lut = {}
        with open(os.path.join(PUBLISH, f"lookUpTable_{mode}_0.csv"), encoding="utf-8") as fh:
            for line in fh:
                i, w, p = line.strip().split(",")
                lut[int(i)] = int(p)
        for book in read_books(mode):
            n += 1
            tags = set()
            try:
                rp.run(book, tags)
                check(lut.get(book["id"]) == book["payoutMultiplier"], "LUT payout != book payout")
                # collectors that collected stay fresh only for the spin they land on
            except Fail as exc:
                bad += 1
                if bad <= 20:
                    print(f"[{mode}] book {book['id']} ({book.get('criteria')}): {exc}")
                continue
            tags.add(f"criteria_{book.get('criteria')}")
            for t in tags:
                coverage[t].append(book["id"])
        print(f"\n{mode}: {n} books, {len(lut)} LUT rows")
        for t in sorted(coverage):
            ids = coverage[t]
            print(f"   {t:<28} {len(ids):>6}   e.g. {ids[:5]}")
        index[mode] = {t: ids[:10] for t, ids in sorted(coverage.items())}
    print(f"\n{'FAILED: ' + str(bad) + ' books' if bad else 'all books replay cleanly'}")
    if args.write_index:
        out = os.path.join(HERE, "library", "test_books.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=1)
        print(f"wrote {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
