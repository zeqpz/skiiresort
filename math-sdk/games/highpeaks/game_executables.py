"""Falcos executables: board drawing/forcing, the tumble pipeline with cell multipliers and the
four features (the board refills after the cluster pays and after every feature group), bonus
triggers, PREMIUM / MIDNIGHT RUN free spins and the FILL UP collection game."""

import random

from game_calculations import GameCalculations, PAYING_SET
from game_config import GP_GRADES
from game_events import (
    cell_mults_event,
    feature_fire_event,
    max_cells_event,
    freespin_trigger_event,
    freespin_retrigger_event,
    enter_bonus_event,
    gauge_event,
    fillup_land_event,
    fillup_retrigger_event,
    pump_boost_event,
    collect_event,
    zippo_burn_event,
    fillup_end_event,
    jackpot_drop_event,
    jackpot_win_event,
)
from src.calculations.statistics import get_random_outcome
from src.events.events import (
    reveal_event,
    win_info_event,
    update_tumble_win_event,
    update_freespin_event,
    freespin_end_event,
    set_win_event,
    set_total_event,
)

FEATURE_KIND = {"ZP": "zippo", "ST": "scratch", "GT": "gold", "GP": "pump"}


class GameExecutables(GameCalculations):
    """Executable functions for the Falcos mechanics."""

    # ================================================================== stats hooks
    def stat(self, key: str, n: int = 1) -> None:
        """In-memory counters read by tools (sim_stats.py). Never part of a book."""
        self.stats[key] = self.stats.get(key, 0) + n

    # ================================================================== cell multipliers
    def double_cell(self, r: int, c: int):
        before = int(self.grid_mults[r][c])
        after = min(before * 2, self.config.cell_cap)
        self.grid_mults[r][c] = after
        return (r, c, before, after)

    def multiply_cell(self, r: int, c: int, mult: int):
        before = int(self.grid_mults[r][c])
        after = min(before * mult, self.config.cell_cap)
        self.grid_mults[r][c] = after
        return (r, c, before, after)

    def set_grid(self, value: int) -> None:
        self.grid_mults = [[value] * self.config.num_rows[r] for r in range(self.config.num_reels)]

    # ================================================================== boards
    def count_name(self, name: str) -> int:
        return sum(1 for column in self.board for s in column if s.name == name)

    def positions_of(self, name: str) -> list:
        return [(r, c) for r, column in enumerate(self.board) for c, s in enumerate(column) if s.name == name]

    def compute_anticipation(self) -> None:
        """Slow-stop the reels after the one where the tokens reach 2, of either kind (one more makes a trigger:
        3 BS, 3 DS, or a mixed 3)."""
        bs = ds = 0
        first = -1
        for r, column in enumerate(self.board):
            bs += sum(1 for s in column if s.name == "BS")
            ds += sum(1 for s in column if s.name == "DS")
            if first < 0 and bs + ds >= 2:
                first = r + 1
        ant = [0] * self.config.num_reels
        if 0 < first < self.config.num_reels:
            for i, r in enumerate(range(first, self.config.num_reels)):
                ant[r] = i + 1
        self.anticipation = ant

    def draw_falcos_board(self) -> None:
        """Draw the reveal. A base board for a bonus criteria is forced with exact scatter counts;
        otherwise a base board that already shows a trigger is redrawn (the criteria did not ask
        for a bonus). The free-spin strips carry FALCOS Tokens (3+ retrigger +5 spins); NITRO's none."""
        conds = self.get_current_distribution_conditions()
        want = conds.get("bonus")
        if self.gametype == self.config.freegame_type:
            # the SDK draws from conds["reel_weights"][gametype]: point it at this bonus's strip
            conds["reel_weights"][self.gametype] = self.config.bonus_reels[self.bonus_kind]
        if self.gametype == self.config.basegame_type and want in self.config.bonus_scatters:
            spec = self.config.bonus_scatters[want]
            if "pairs" in spec:
                n_bs, n_ds = (int(v) for v in get_random_outcome(spec["pairs"]).split(","))
            else:
                n_bs, n_ds = get_random_outcome(spec.get("BS", {0: 1})), get_random_outcome(spec.get("DS", {0: 1}))
            self.force_scatter_board(get_random_outcome(conds["reel_weights"][self.gametype]), n_bs, n_ds)
        else:
            while True:
                self.create_board_reelstrips()
                if self.gametype != self.config.basegame_type or want == "any":
                    break
                if self.check_bonus_trigger() is None:
                    break
        self.compute_anticipation()

    def force_scatter_board(self, strip_id: str, n_bs: int, n_ds: int) -> None:
        """Force a board holding exactly n_bs FALCOS Tokens and n_ds Midnight Tokens."""
        # one scatter per reel at most: a teaser class never takes a reel the trigger needs
        n_ds = min(n_ds, self.config.num_reels - n_bs)
        bs_stops = self.get_syms_on_reel(strip_id, "BS")
        ds_stops = self.get_syms_on_reel(strip_id, "DS")
        ds_reels = [r for r in range(self.config.num_reels) if ds_stops[r]]
        assert len(ds_reels) >= n_ds, f"{strip_id} holds DS on only {len(ds_reels)} reels"
        for _ in range(500):
            force = {}
            for r in random.sample(ds_reels, n_ds):
                force[r] = random.choice(ds_stops[r])
            bs_reels = [r for r in range(self.config.num_reels) if bs_stops[r] and r not in force]
            if len(bs_reels) < n_bs:
                continue
            for r in random.sample(bs_reels, n_bs):
                force[r] = random.choice(bs_stops[r])
            self.force_board_from_reelstrips(strip_id, dict(sorted(force.items())))
            self.get_special_symbols_on_board()
            if self.count_name("BS") == n_bs and self.count_name("DS") == n_ds:
                return
        raise RuntimeError(f"could not force {n_bs} BS + {n_ds} DS on {strip_id}")

    def plant_fulltank_pump(self) -> None:
        """Wincap criteria: put a Gas Pump on the reveal (never over a scatter, never in a column
        that already has one) and make it roll FULL TANK when it fires."""
        cols = [r for r in range(self.config.num_reels) if not any(s.name == "GP" for s in self.board[r])]
        r = random.choice(cols)
        rows = [c for c in range(self.config.num_rows[r]) if self.board[r][c].name not in ("BS", "DS")]
        c = random.choice(rows)
        self.board[r][c] = self.create_symbol("GP")
        self.get_special_symbols_on_board()
        # keyed by the symbol object, not the cell: the cluster refill can move it down its reel
        # before it fires (the object stays on the board, so its id cannot be reused meanwhile)
        self.forced_grades[id(self.board[r][c])] = "FT"

    # ================================================================== tumble pipeline
    def resolve_tumbles(self) -> None:
        """One spin's cascade. Line pays always come first (owner, 2026-11-17: "let line hits come
        before any special symbols like the lighter. let the line pay play out then the special
        symbol"): each step either
            1. pays the board's clusters (through the current cell multipliers), the cells of every
               paid cluster double -> tumbleBoard (the paid symbols leave, the refill drops in); or,
               only when the board holds no cluster,
            2. fires the next feature standing on it -> tumbleBoard: all Gas Pumps together, else
               the first Scratch / Gold Scratch Ticket, else the first Zippo (reading order: reel
               by reel, top to bottom).
        So a cluster a refill makes is paid before any feature fires, and a feature never burns
        a cluster that is already on the board. Repeat until the board holds neither a cluster
        nor a feature, or the max win is reached (the cascade stops on the paying board)."""
        step = 0
        while True:
            self.evaluate_falcos_wins()
            if self.pay_board():
                if self.wincap_triggered:
                    break
                self.tumble_flagged()
            elif not self.fire_next_feature(step):
                break
            if step >= self.config.max_tumbles_per_spin:
                self.stat("tumble_cap_hit")
                break
            step += 1
        self.stat("tumbles", step)

    def pay_board(self) -> bool:
        """Pay this board's clusters, emit winInfo/updateTumbleWin, flag the cluster symbols and
        double their cells (after paying). Returns True if anything paid."""
        if not self.win_data["wins"]:
            return False
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        win_info_event(self)
        update_tumble_win_event(self)
        self.stat("clusters", len(self.win_data["wins"]))
        if any(w["meta"].get("maxWin") for w in self.win_data["wins"]):
            self.stat("max_cluster")
        self.evaluate_wincap()
        cells = []
        for win in self.win_data["wins"]:
            for p in win["positions"]:
                cells.append((p["reel"], p["row"]))
                self.board[p["reel"]][p["row"]].explode = True
        if not self.wincap_triggered:
            changed = [self.double_cell(r, c) for r, c in sorted(set(cells))]
            cell_mults_event(self, "win", changed)
        return True

    def locate(self, sym) -> tuple:
        """Current cell of a symbol object (tumbles move survivors down their reel)."""
        for r, column in enumerate(self.board):
            for c, s in enumerate(column):
                if s is sym:
                    return r, c
        raise RuntimeError(f"{sym.name} left the board before it fired")

    def fire_next_feature(self, step: int) -> bool:
        """Fire the next feature group standing on the board, then refill: every Gas Pump at once,
        else the first Scratch / Gold Ticket, else the first Zippo. Returns True if one fired."""
        feats = [s for column in self.board for s in column if s.name in FEATURE_KIND and not s.explode]
        if not feats:
            return False
        pumps = [s for s in feats if s.name == "GP"]
        tickets = [s for s in feats if s.name in ("ST", "GT")]
        zippos = [s for s in feats if s.name == "ZP"]
        if pumps:
            for sym in pumps:
                self.fire_pump(*self.locate(sym), step)
        elif tickets:
            sym = tickets[0]
            r, c = self.locate(sym)
            if sym.name == "ST":
                self.fire_scratch(r, c, step)
            else:
                self.fire_gold(r, c, step)
        else:
            self.fire_zippo(*self.locate(zippos[0]), step)
        self.tumble_flagged()
        return True

    def _burn(self, r: int, c: int, burned: list) -> None:
        """Burn a paying symbol (it clears in the next tumble); scatters/features keep their place."""
        sym = self.board[r][c]
        if sym.name in PAYING_SET and not sym.explode:
            sym.explode = True
            burned.append((r, c, sym.name))

    def fire_pump(self, r: int, col_row: int, step: int) -> None:
        """Gas Pump: roll a grade. REGULAR..PREMIUM multiply every cell of the column by the
        pump's multiplier (cap x2048) and burn the column's paying symbols. FULL TANK turns the
        column into MAX cells (and burns its paying symbols too, so fresh symbols drop onto them)."""
        c = col_row
        key = self.forced_grades.pop(id(self.board[r][c]), None)
        if key is None:
            key = get_random_outcome(self.get_current_distribution_conditions()["gp_grades"][self.gametype])
        grade, mult = GP_GRADES[key]
        cells, burned = [], []
        column = list(range(self.config.num_rows[r]))
        if grade == "fulltank":
            cells = [(r, y, int(self.grid_mults[r][y]), int(self.grid_mults[r][y])) for y in column]
        else:
            cells = [self.multiply_cell(r, y, mult) for y in column]
        for y in column:
            self._burn(r, y, burned)
        self.board[r][c].explode = True
        self.stat(f"pump_{key}")
        feature_fire_event(self, {"step": step, "kind": "pump", "cell": (r, c), "grade": grade,
                                  "mult": mult, "cells": cells, "burned": burned})
        if grade == "fulltank":
            added = [(r, y) for y in column if (r, y) not in self.max_cells]
            self.max_cells.update((r, y) for y in column)
            max_cells_event(self, added)
            self.record({"symbol": "fulltank", "kind": 1, "gametype": self.gametype})

    def fire_scratch(self, r: int, c: int, step: int) -> None:
        """Scratch Ticket: scratch off one paying symbol on the board (picked uniformly among the
        symbol types still standing); every cell holding it doubles and burns, and so does the
        ticket's own cell."""
        standing = sorted({s.name for column in self.board for s in column
                           if s.name in PAYING_SET and not s.explode})
        target = random.choice(standing) if standing else None
        cells, burned = [], []
        if target is not None:
            for x, column in enumerate(self.board):
                for y, s in enumerate(column):
                    if s.name == target and not s.explode:
                        cells.append(self.double_cell(x, y))
                        self._burn(x, y, burned)
        cells.append(self.double_cell(r, c))
        self.board[r][c].explode = True
        self.stat("scratch")
        feature_fire_event(self, {"step": step, "kind": "scratch", "cell": (r, c), "target": target,
                                  "cells": cells, "burned": burned})

    def fire_gold(self, r: int, c: int, step: int) -> None:
        """Gold Scratch Ticket: every paying symbol still standing doubles and burns, and so does
        the ticket's own cell."""
        cells, burned = [], []
        for x, column in enumerate(self.board):
            for y, s in enumerate(column):
                if s.name in PAYING_SET and not s.explode:
                    cells.append(self.double_cell(x, y))
                    self._burn(x, y, burned)
        cells.append(self.double_cell(r, c))
        self.board[r][c].explode = True
        self.stat("gold")
        feature_fire_event(self, {"step": step, "kind": "gold", "cell": (r, c), "cells": cells, "burned": burned})

    def fire_zippo(self, r: int, c: int, step: int) -> None:
        """Zippo: its 3x3 area (own cell + up to 8 neighbours) doubles; paying symbols there burn;
        scatters and other features keep their place (they still double)."""
        cells, burned = [], []
        for x in range(r - 1, r + 2):
            for y in range(c - 1, c + 2):
                if 0 <= x < self.config.num_reels and 0 <= y < self.config.num_rows[x]:
                    cells.append(self.double_cell(x, y))
                    self._burn(x, y, burned)
        self.board[r][c].explode = True
        self.stat("zippo")
        feature_fire_event(self, {"step": step, "kind": "zippo", "cell": (r, c), "cells": cells, "burned": burned})

    def flagged_positions(self) -> list:
        return [{"reel": r, "row": c} for r, column in enumerate(self.board)
                for c, s in enumerate(column) if s.explode]

    def tumble_flagged(self) -> None:
        """Every flagged symbol (paid, burned, fired) leaves in one tumble and the refill drops
        in; tumbleBoard lists exactly those cells (see the SDK's tumble_board_event)."""
        self.tumble_explode_positions = self.flagged_positions()
        self.tumble_game_board()

    def set_end_tumble_event(self) -> None:
        if self.win_manager.spin_win > 0:
            set_win_event(self)
        set_total_event(self)

    # ================================================================== spins
    def run_board_spin(self) -> None:
        """One reveal + its whole cascade on the current gametype's strips."""
        conds = self.get_current_distribution_conditions()
        self.draw_falcos_board()
        if self.gametype == self.config.basegame_type and conds.get("force_fulltank"):
            self.plant_fulltank_pump()
        reveal_event(self)
        drop = self.roll_jackpot_drop("free" if self.gametype == self.config.freegame_type else "base")
        self.resolve_tumbles()
        if drop and not self.wincap_triggered:
            self.pay_jackpot()
        self.set_end_tumble_event()
        self.win_manager.update_gametype_wins(self.gametype)

    # ================================================================== jackpots
    def roll_jackpot_drop(self, where: str) -> bool:
        """Maybe drop a "?" onto the board (over a random cell). Criteria with an exact win (the max
        win, or "0" = no win) never drop one: the prize would only make them resimulate."""
        if self.get_current_betmode_distributions().get_win_criteria() is not None:
            return False
        if random.random() >= self.config.jackpot_drop[where]:
            return False
        r = random.randrange(self.config.num_reels)
        c = random.randrange(self.config.num_rows[r])
        jackpot_drop_event(self, r, c)
        self.stat(f"jackpot_drop_{where}")
        return True

    def pay_jackpot(self) -> None:
        """The MINI / MINOR / MAJOR / GRAND wheel: one level by weight, paid at once (trimmed by the max win)."""
        level = get_random_outcome(self.config.jackpot_levels)
        mult = self.config.jackpot_values[level]
        room = max(0.0, round(self.config.wincap - self.win_manager.running_bet_win, 2))
        amount = round(min(float(mult), room), 2)
        jackpot_win_event(self, level, mult, amount)
        self.win_manager.update_spinwin(amount)
        self.record({"symbol": "jackpot", "kind": level, "gametype": self.gametype})
        self.stat(f"jackpot_{level}")
        self.evaluate_wincap()

    def preload_nitro(self) -> None:
        """NITRO SPIN: every cell preloaded with a multiplier from x16 to x2048."""
        table = self.get_current_distribution_conditions()["nitro_cells"]
        for r in range(self.config.num_reels):
            for c in range(self.config.num_rows[r]):
                self.grid_mults[r][c] = int(get_random_outcome(table))
        cell_mults_event(self, "nitro", [])

    # ================================================================== bonus triggers
    def check_bonus_trigger(self):
        """Scatters are counted on the board the base spin ENDS on (they never burn, so tumbles
        can only add to them). 3+ DS -> MIDNIGHT RUN (it outranks everything); else 4+ BS ->
        PREMIUM; else 3+ tokens with at least one DS among them -> MIDNIGHT RUN (2026-11-17); else exactly 3 BS ->
        FILL UP."""
        n_bs, n_ds = self.count_name("BS"), self.count_name("DS")
        if n_ds >= 3:
            return "midnight", self.positions_of("DS"), "DS", n_ds
        if n_bs >= 4:
            return "premium", self.positions_of("BS"), "BS", n_bs
        if n_ds >= 1 and n_bs + n_ds >= self.config.mixed_trigger:
            return "midnight", sorted(self.positions_of("BS") + self.positions_of("DS")), "DS", n_bs + n_ds
        if n_bs == 3:
            return "fillup", self.positions_of("BS"), "BS", n_bs
        return None

    def run_bonus(self, kind: str, positions: list, symbol: str, count: int, bought: bool) -> None:
        self.bonus_kind = kind
        self.record({"symbol": kind, "kind": count, "gametype": self.config.basegame_type})
        if kind == "fillup":
            enter_bonus_event(self, "fillup", positions, bought)
            self.run_fillup()
        else:
            self.tot_fs = self.config.free_spins
            freespin_trigger_event(self, positions, symbol)
            enter_bonus_event(self, kind, positions, bought)
            self.run_freespin()

    # ================================================================== PREMIUM / MIDNIGHT RUN
    def run_freespin(self) -> None:
        """10 free spins of the base game with sticky cell multipliers (and sticky MAX cells).
        MIDNIGHT RUN starts every cell at x4 and plays on the pump-rich strip."""
        self.reset_fs_spin()
        self.tot_fs = self.config.free_spins
        self.max_cells = set()
        self.set_grid(self.config.midnight_start_mult if self.bonus_kind == "midnight" else 1)
        cell_mults_event(self, "bonusStart", [])
        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.fs += 1
            update_freespin_event(self)   # amount = this spin's number (1..10), total = 10
            self.win_manager.reset_spin_win()
            self.win_data = {"totalWin": 0, "wins": []}
            self.run_board_spin()
            # a retrigger (owner, 2026-11-17): 3+ FALCOS Tokens on the board this spin ended on add 5 spins
            tokens = self.positions_of("BS")
            if (len(tokens) >= self.config.retrigger_count and not self.wincap_triggered
                    and self.tot_fs < self.config.max_free_spins):
                added = min(self.config.retrigger_spins, self.config.max_free_spins - self.tot_fs)
                self.tot_fs += added
                self.stat("retrigger")
                freespin_retrigger_event(self, tokens, "BS", added)
        freespin_end_event(self)

    # ================================================================== FILL UP
    def fill_total(self) -> float:
        return round(sum(item.get("value", 0) for item in self.fill_board.values()), 2)

    def run_fillup(self) -> None:
        """FILL UP - hold-and-win collection game on its own 7x5 board (no cell multipliers).

        * Opens with `seed_drops` Fuel Drops on random cells (spin 0) and a full gauge (3).
        * Each spin uses one bar, then every EMPTY cell lands X (blank), a Fuel Drop or a
          feature; drops and collectors that collected are sticky.
        * Resolution: Gas Pumps together (x2..x64 on every drop and every collector that
          collected on an earlier spin in their column, then they leave), Scratch / Gold Tickets
          one at a time (collect, then stay with their total or leave if they found nothing),
          Zippos last (burn every drop in their 3x3, then leave) - none land since 2026-11-17
          (the owner took the Lighter out of FILL UP), the code stays for the event contract.
        * Anything new landing refills the gauge to 3 (if it is lower); a FALCOS Token landing adds
          5 spins on top (fillUpRetrigger) and leaves. The bonus ends when the gauge is empty
          and nothing new landed, when no empty cell is left, or at the max win.
        * Win = every drop + every collector total, x bet, capped at the max win.
        """
        self.reset_fs_spin()
        conds = self.get_current_distribution_conditions()
        prof = self.config.fillup_profiles[conds.get("fillup_profile", "standard")]
        R, C = self.config.num_reels, self.config.num_rows[0]
        self.fill_board = {}
        fuel = 3
        gauge_event(self, fuel, "start")

        seed = random.sample([(r, c) for r in range(R) for c in range(C)], prof["seed_drops"])
        for r, c in seed:
            self.fill_board[(r, c)] = {"name": "FD", "value": get_random_outcome(prof["drop_values"])}
        fillup_land_event(self, 0, [(r, c, self.fill_board[(r, c)]) for r, c in sorted(seed)])

        spin = 0
        reason = "empty"
        while True:
            empty = [(r, c) for r in range(R) for c in range(C) if (r, c) not in self.fill_board]
            if not empty:
                reason = "full"
                break
            spin += 1
            fuel -= 1
            gauge_event(self, fuel, "use")
            landed, cells, pump_cols, fresh = [], [], set(), {}
            for r, c in empty:
                name = get_random_outcome(prof["land"])
                if name == "GP" and r in pump_cols:
                    name = "X"
                item = None
                if name == "FD":
                    item = {"name": "FD", "value": get_random_outcome(prof["drop_values"])}
                elif name in ("ST", "GT"):
                    item = {"name": name, "value": 0, "fresh": True}
                elif name in ("GP", "ZP", "BS"):
                    item = {"name": name}
                    if name == "GP":
                        pump_cols.add(r)
                if item is not None:
                    fresh[(r, c)] = item
                    landed.append((r, c))
                cells.append((r, c, item))
            # drops/collectors join the board now; pumps/zippos are shown in the land event and
            # resolve below (they never stay); a FALCOS Token adds spins and leaves (never on the board)
            for pos, item in fresh.items():
                if item["name"] != "BS":
                    self.fill_board[pos] = item
            fillup_land_event(self, spin, cells)
            for (r, c), item in sorted(fresh.items()):
                if item["name"] == "FD":
                    self.stat("fd_landed")

            for (r, c), item in sorted(fresh.items()):
                if item["name"] == "GP":
                    self.fill_pump(r, c, prof)
            for (r, c), item in sorted(fresh.items()):
                if item["name"] in ("ST", "GT"):
                    self.fill_collect(r, c, item)
            for (r, c), item in sorted(fresh.items()):
                if item["name"] == "ZP":
                    self.fill_zippo(r, c)
            for item in self.fill_board.values():
                item.pop("fresh", None)
            if self.roll_jackpot_drop("fillup"):
                self.pay_jackpot()
                if self.wincap_triggered:
                    reason = "wincap"
                    break

            if landed and fuel < 3:
                fuel = 3
                gauge_event(self, fuel, "refill")
            # a FALCOS Token (owner, 2026-11-17): +5 spins on top of the refill, then it leaves
            for (r, c), item in sorted(fresh.items()):
                if item["name"] == "BS":
                    fuel += self.config.retrigger_spins
                    self.stat("fill_retrigger")
                    fillup_retrigger_event(self, r, c, self.config.retrigger_spins, fuel)
                    gauge_event(self, fuel, "retrigger")
            if self.fill_total() + self.win_manager.running_bet_win >= self.config.wincap:
                reason = "wincap"
                break
            if fuel == 0:
                break

        total = self.fill_total()
        room = round(self.config.wincap - self.win_manager.running_bet_win, 2)
        win = round(min(total, room), 2)
        self.stat("fillup_spins", spin)
        self.stat(f"fillup_end_{reason}")
        fillup_end_event(self, reason, spin, total, win)
        self.win_manager.update_spinwin(win)
        self.evaluate_wincap()
        self.set_end_tumble_event()
        self.win_manager.update_gametype_wins(self.gametype)
        freespin_end_event(self)

    def fill_pump(self, r: int, c: int, prof: dict) -> None:
        mult = int(get_random_outcome(prof["gp_mults"]))
        boosted = []
        for y in range(self.config.num_rows[r]):
            item = self.fill_board.get((r, y))
            if item is None or item.get("fresh") or item["name"] not in ("FD", "ST", "GT"):
                continue
            if item["name"] in ("ST", "GT") and item["value"] <= 0:
                continue
            before = item["value"]
            item["value"] = round(before * mult, 2)
            boosted.append((r, y, item["name"], before, item["value"]))
        del self.fill_board[(r, c)]
        self.stat("fill_pump")
        pump_boost_event(self, (r, c), mult, boosted)

    def fill_collect(self, r: int, c: int, item: dict) -> None:
        """ST: collects every drop in its 8 neighbours plus any collector there that collected on
        an earlier spin. GT: the same over the whole board, and then doubles its total - it collects
        everything AND 2x everything (owner, 2026-11-13). A collector that found nothing leaves."""
        kind = "scratch" if item["name"] == "ST" else "gold"
        if kind == "scratch":
            area = [(x, y) for x in range(r - 1, r + 2) for y in range(c - 1, c + 2) if (x, y) != (r, c)]
        else:
            area = [pos for pos in sorted(self.fill_board) if pos != (r, c)]
        collected = []
        for pos in area:
            other = self.fill_board.get(pos)
            if other is None or other.get("fresh"):
                continue
            if other["name"] == "FD" or (other["name"] in ("ST", "GT") and other["value"] > 0):
                collected.append((pos[0], pos[1], other["name"], other["value"]))
                del self.fill_board[pos]
        total = round(item["value"] + sum(v for _, _, _, v in collected), 2)
        mult = 2 if (kind == "gold" and collected) else 1
        total = round(total * mult, 2)
        removed = not collected
        if removed:
            del self.fill_board[(r, c)]
        else:
            item["value"] = total
        self.stat(f"fill_{kind}")
        collect_event(self, (r, c), kind, collected, total, removed, mult)

    def fill_zippo(self, r: int, c: int) -> None:
        burned = []
        for x in range(r - 1, r + 2):
            for y in range(c - 1, c + 2):
                other = self.fill_board.get((x, y))
                if other is not None and other["name"] == "FD":
                    burned.append((x, y, other["value"]))
                    del self.fill_board[(x, y)]
        del self.fill_board[(r, c)]
        self.stat("fill_zippo")
        zippo_burn_event(self, (r, c), burned)
