"""High Peaks (engine and math from Falcos) - game configuration: symbols, cluster paytable, features, bonuses, bet modes.

Source of truth for the rules: FALCOS_DESIGN.md (owner-approved, v1 2026-11-09). This file
implements it exactly where it is specific; where it is not, the decision taken is written
next to the value (and summarised in EVENTS.md, "Rules the books follow").

Symbols
    Paying (9)   H1 Cash Drawer  H2 Gold Key  H3 Pump Nozzle  H4 Jerry Can
                 L1 Energy Drink  L2 Slushie  L3 Hot Dog  L4 Chips  L5 Donut
    Features     ZP Zippo   ST Scratch Ticket   GT Gold Scratch Ticket   GP Gas Pump
    Scatters     BS FALCOS Token (3 -> FILL UP, 4+ -> PREMIUM)
                 DS Midnight Token (3 -> MIDNIGHT RUN in base and FUEL CHANCE; MIDNIGHT RUN can also
                 be bought outright - the `midnight` bet mode)
    FILL UP only FD Fuel Drop (carries `value`), X blank; ST/GT are collectors, GP a booster,
                 BS adds 5 spins; no ZP there (2026-11-17).

Board: 7x5 (7 reels wide, 5 rows tall, 35 cells; owner decision 2026-11-09), clusters of 5+ joined orthogonally, tumbles. Every cell carries a multiplier
(x1 .. x2048) that doubles each time a win or a feature hits it; a cluster pays the SUM of
its cells that are at x2 or more (x1 if none).
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

PAYING = ("H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "L5")
FEATURES = ("ZP", "ST", "GT", "GP")
SCATTERS = ("BS", "DS")

# --------------------------------------------------------------------------------------------
# Paytable, verbatim from FALCOS_DESIGN.md (owner-approved tenths table, 2026-11-09): pays x bet
# by cluster size, 15+ pays the top rate. Every entry is a whole number of tenths and a cluster's
# multiplier is 1 or an even number (a sum of powers of two >= 2), so every win lands on the RGS's
# 0.1x grid (math-sdk utils/rgs_verification.py asserts payout % 10 == 0 in hundredths) with no
# rounding.
DESIGN_PAYTABLE = {
    #       5     6     7     8     9    10    11    12    13    14   15+
    "H1": (1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 8.0, 15.0, 30.0, 60.0, 150.0),
    "H2": (0.8, 1.0, 1.2, 1.5, 2.0, 4.0, 6.0, 12.0, 25.0, 50.0, 100.0),
    "H3": (0.5, 0.8, 1.0, 1.2, 1.5, 3.0, 4.5, 10.0, 20.0, 40.0, 60.0),
    "H4": (0.4, 0.5, 0.8, 1.0, 1.2, 2.0, 3.0, 5.0, 10.0, 20.0, 40.0),
    "L1": (0.3, 0.4, 0.5, 0.8, 1.0, 1.5, 2.5, 4.0, 8.0, 15.0, 30.0),
    "L2": (0.3, 0.4, 0.5, 0.6, 0.8, 1.2, 2.0, 3.0, 6.0, 12.0, 25.0),
    "L3": (0.2, 0.3, 0.4, 0.5, 0.7, 1.1, 1.8, 2.8, 5.5, 11.0, 22.0),
    "L4": (0.2, 0.3, 0.4, 0.5, 0.6, 1.0, 1.5, 2.5, 5.0, 10.0, 20.0),
    "L5": (0.2, 0.2, 0.3, 0.4, 0.5, 0.9, 1.4, 2.2, 4.5, 9.0, 18.0),
}
for _sym, _pays in DESIGN_PAYTABLE.items():
    assert all(abs(p * 10 - round(p * 10)) < 1e-9 for p in _pays), f"{_sym}: pays must be in 0.1x steps"


# --------------------------------------------------------------------------------------------
# Feature tables

# Gas Pump grades: key -> (grade, multiplier). FULL TANK has no multiplier (MAX cells).
GP_GRADES = {
    "R2": ("regular", 2), "R4": ("regular", 4),
    "P8": ("plus", 8), "P16": ("plus", 16),
    "PR32": ("premium", 32), "PR64": ("premium", 64),
    "FT": ("fulltank", None),
}

# FILL UP: what lands in an empty cell on each spin, and what a Fuel Drop / pump is worth.
FD_GREEN = (0.2, 0.5, 1, 2, 3)
FD_AMBER = (5, 10, 15, 20)
FD_RED = (50, 100, 250, 500)

# Jackpots: prize (x bet) and how likely each level is once a "?" has dropped (per 1,000). Mean
# prize 27.4x; at 1 "?" in 400 base spins the jackpots carry ~6.8% of the base game's return.
JACKPOT_VALUES = {"mini": 10, "minor": 50, "major": 250, "grand": 2500}
JACKPOT_LEVELS = {"mini": 860, "minor": 115, "major": 22, "grand": 3}


class GameConfig(Config):
    """Falcos configuration class."""

    def __init__(self):
        super().__init__()
        self.game_id = "highpeaks"
        self.game_name = "highpeaks"
        self.provider_numer = 0
        self.provider_number = 0
        self.provider_name = "highpeaks"
        self.working_name = "High Peaks"
        self.wincap = 50000.0               # owner decision 2026-11-09: max win 50,000x in every mode
        self.win_type = "cluster"
        self.rtp = 0.965
        self.construct_paths()

        self.num_reels = 7
        self.num_rows = [5] * self.num_reels       # 7 reels x 5 rows (35 cells)
        self.include_padding = True

        # Cell multipliers: start x1, double on every win/feature hit, capped at x2048.
        self.cell_cap = 2048
        # Safety net only: a spin keeps tumbling while anything pays or a feature fires; this
        # bound is never meant to bind (sims report how often it does - it should be never).
        self.max_tumbles_per_spin = 150

        # Paytable (cluster size, symbol) -> pay. Sizes 5..14 individually, 15..35 the top rate.
        pay_group = {}
        for sym, pays in DESIGN_PAYTABLE.items():
            for i, pay in enumerate(pays):
                size = 5 + i
                rng = (size, size) if size < 15 else (15, 35)
                pay_group[(rng, sym)] = pay
        self.paytable = self.convert_range_table(pay_group)

        # "scatter" and "feature" become flags on the reveal/tumble symbols ({"name":"BS","scatter":true}).
        self.special_symbols = {
            "wild": [],
            "scatter": list(SCATTERS),
            "feature": list(FEATURES),
        }
        self.free_spins = 10                       # PREMIUM and MIDNIGHT RUN: 10 free spins
        # retriggers (owner, 2026-11-17): 3+ FALCOS Tokens (BS) on the board a PREMIUM / MIDNIGHT RUN spin
        # ends on add 5 spins; in FILL UP a token that lands adds 5 spins to the gauge
        self.retrigger_count = 3
        self.retrigger_spins = 5
        self.max_free_spins = 60                   # PREMIUM / MIDNIGHT RUN never run past this many spins
        self.midnight_start_mult = 4               # MIDNIGHT RUN: every cell starts at x4

        # ---------------------------------------------------------------- JACKPOTS (High Peaks, owner 2026-11-18)
        # A "?" can drop onto the board on any spin (base, FUEL CHANCE, NITRO, every PREMIUM / MIDNIGHT
        # RUN free spin, every FILL UP spin). It sits over a cell (it never replaces a symbol, so the
        # cluster math is untouched); when the spin's cascade is over the MINI / MINOR / MAJOR / GRAND
        # wheel spins and pays one fixed prize (x bet). Fixed prizes, not progressive pools: nothing
        # links rounds. Owner: "very rarely for normal rounds, less than 5%"; mini most likely, grand
        # super rare. Prizes owner-approved 2026-11-18: 10x / 50x / 250x / 2,500x.
        self.jackpot_values = dict(JACKPOT_VALUES)
        self.jackpot_levels = dict(JACKPOT_LEVELS)
        # chance of a "?" per spin, by where the spin is played
        self.jackpot_drop = {"base": 1 / 400, "free": 1 / 20, "fillup": 1 / 60}
        self.freespin_triggers = {self.basegame_type: {3: self.free_spins}, self.freegame_type: {}}
        self.anticipation_triggers = {self.basegame_type: 2, self.freegame_type: 99}

        # ---------------------------------------------------------------- reels
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "FRM": "FRM.csv", "NR0": "NR0.csv"}
        self.reels = {r: self.read_reels_csv(os.path.join(self.reels_path, f)) for r, f in reels.items()}
        self.padding_reels = {self.basegame_type: self.reels["BR0"], self.freegame_type: self.reels["FR0"]}
        # free-spin strips belong to the bonus, not to the criteria: PREMIUM plays FR0, MIDNIGHT
        # RUN the pump-rich FRM, whichever criteria (or natural trigger) led there
        self.bonus_reels = {"premium": {"FR0": 1}, "midnight": {"FRM": 1}}

        # ---------------------------------------------------------------- Gas Pump grades
        # FULL TANK is a rare roll everywhere; how often a player meets it is the optimiser's call
        # (the wincap criteria force it). In a sticky bonus a FULL TANK column stays MAX for the rest
        # of the bonus, so there it is close to a guaranteed max win and must stay very rare.
        gp_base = {"R2": 420, "R4": 260, "P8": 150, "P16": 70, "PR32": 25, "PR64": 8, "FT": 0.05}
        gp_free = {"R2": 420, "R4": 260, "P8": 150, "P16": 70, "PR32": 25, "PR64": 8, "FT": 0.01}
        gp_cap = {"FT": 1}
        self.gp_tables = {"base": gp_base, "free": gp_free, "cap": gp_cap}

        # ---------------------------------------------------------------- big-win records
        # Books whose round win reaches this (and is below the max win) get a {"symbol": "bigwin"}
        # force record, so the optimiser can hold them in their own fence with a fixed RTP share:
        # the 3-star volatility band reads etl10k (return from 10,000x+ wins) <= 0.8 and etl40b
        # (return from wins >= 40x the mode cost) <= 0.9, both in ABSOLUTE bets, so a buy's tail
        # must be weighted on purpose, not left to the optimiser's curves.
        self.bigwin_threshold = {"fillup": 4000.0, "premium": 10000.0, "nitro": 10000.0, "midnight": 10000.0}
        # 500x modes: prob5k (P(win >= 5,000x) x 0.5 <= 1%) needs their 5,000-10,000x books held too
        self.highwin_threshold = {"nitro": 5000.0, "midnight": 5000.0}

        # ---------------------------------------------------------------- NITRO SPIN
        # every cell preloaded x16 .. x2048 (powers of two), heavy at the bottom
        # 7x5 retune: the x16/x32 bulk with a thinner top (x1024 0.4 / x2048 0.1 per ~1,000, was
        # 1 / 0.4): spins under 5,000x average ~350x, 5,000x+ comes ~1 in 25 before weighting
        nitro_cells = {16: 600, 32: 300, 64: 80, 128: 20, 256: 5, 512: 1.5, 1024: 0.4, 2048: 0.1}
        nitro_cells_rich = {1024: 1, 2048: 1}
        self.nitro_tables = {"standard": nitro_cells, "rich": nitro_cells_rich}

        # ---------------------------------------------------------------- FILL UP
        # Each spin, every empty cell independently lands one of these (X = blank). At most one
        # Gas Pump per column per spin (a second one rolled in a column lands as X).
        # seed_drops: FILL UP opens with this many Fuel Drops already on the board (the three
        # FALCOS Tokens that triggered it turn into the first drops; a bought FILL UP gets the same).
        self.fillup_profiles = {
            "standard": {
                # 7x5 retune: 35 cells land far fewer drops than 49, so drops, pumps and tickets
                # land ~1.9x / 2.3x / 1.4x as often (FD 24 -> 45, GP 1.6 -> 3.7, ST 2.2 -> 3.1)
                # no Lighter in FILL UP (owner, 2026-11-17: "remove the lighter symbol from the fill up bonus")
                "land": {"X": 1000, "FD": 45, "ST": 3.1, "GT": 0.5, "GP": 3.7, "BS": 0.6},
                "drop_values": {
                    0.2: 260, 0.5: 240, 1: 200, 2: 130, 3: 90,
                    5: 60, 10: 32, 15: 15, 20: 10,
                    # thinner red top (250: 0.25 -> 0.12, 500: 0.08 -> 0.03) and x32/x64 pumps
                    # (2 -> 1.5, 0.6 -> 0.3): the natural 4,000x+ tail, which etl40b counts in
                    # absolute bets, was ~11% of the bonus's value
                    50: 2.5, 100: 0.8, 250: 0.12, 500: 0.03,
                },
                "gp_mults": {2: 50, 4: 26, 8: 13, 16: 6, 32: 1.5, 64: 0.3},
                "seed_drops": 3,
            },
            # wincap criteria only: dense, heavy drops and pumps so 50,000x is reachable
            "cap": {
                "land": {"X": 300, "FD": 60, "ST": 4, "GT": 2, "GP": 8, "BS": 0.3},
                "drop_values": {50: 2, 100: 2, 250: 2, 500: 2},
                "gp_mults": {16: 1, 32: 1, 64: 1},
                "seed_drops": 3,
            },
        }

        # mixed tokens (owner, 2026-11-17: "Yes, mixed counts", then "if there is already 2 fs symbols and 1 xfs symbol
        # that should be the midnight bonus but if there is just 3 fs symbols that should be the fuel up bonus"): 3+
        # tokens with at least one DS among them start MIDNIGHT RUN - checked after 3+ DS (MIDNIGHT RUN) and 4+ BS
        # (PREMIUM), before exactly 3 BS (FILL UP)
        self.mixed_trigger = 3
        # scatter counts forced on a trigger board (the other scatter class may tease). "pairs" draws the two counts
        # together ("bs,ds": weight) - MIDNIGHT RUN's board is now and then a mixed one; FILL UP's may not show a DS
        # (3 BS + 1 DS is a mixed trigger, MIDNIGHT RUN)
        self.bonus_scatters = {
            "fillup": {"BS": {3: 1}, "DS": {0: 1}},
            "premium": {"pairs": {"4,0": 80, "5,0": 10, "6,0": 2, "4,1": 6, "4,2": 2}},
            "midnight": {"pairs": {"0,3": 45, "1,3": 10, "2,3": 4, "2,1": 18, "1,2": 12, "2,2": 6, "3,1": 5}},
        }

        b, f = self.basegame_type, self.freegame_type

        def base_dists(scale: float = 1.0):
            """base / FUEL CHANCE criteria. `scale` multiplies the bonus criteria's sim quotas
            (FUEL CHANCE: ~2.2x the bonus rate); ordinary spins take up the difference."""
            q = {"wincap": 0.001, "midnight": 0.005, "premium": 0.01, "fillup": 0.03}
            q = {k: round(v * scale, 6) for k, v in q.items()}
            zero = 0.35 if scale == 1.0 else 0.30
            rest = round(1.0 - sum(q.values()) - zero, 6)
            return [
                Distribution(
                    # FULL TANK in the base game: a pump forced onto the reveal rolls FULL TANK; any
                    # cluster on its MAX column pays the max win
                    criteria="wincap", quota=q["wincap"], win_criteria=self.wincap,
                    conditions={
                        "reel_weights": {b: {"BR0": 1}},
                        "gp_grades": {b: gp_base, f: gp_free},
                        "force_fulltank": True,
                        "bonus": None,
                    },
                ),
                Distribution(
                    criteria="midnight", quota=q["midnight"],
                    conditions={
                        "reel_weights": {b: {"BR0": 1}},
                        "gp_grades": {b: gp_base, f: gp_free},
                        "bonus": "midnight",
                    },
                ),
                Distribution(
                    criteria="premium", quota=q["premium"],
                    conditions={
                        "reel_weights": {b: {"BR0": 1}},
                        "gp_grades": {b: gp_base, f: gp_free},
                        "bonus": "premium",
                    },
                ),
                Distribution(
                    criteria="fillup", quota=q["fillup"],
                    conditions={
                        "reel_weights": {b: {"BR0": 1}},
                        "gp_grades": {b: gp_base},
                        "fillup_profile": "standard",
                        "bonus": "fillup",
                    },
                ),
                Distribution(
                    criteria="0", quota=zero, win_criteria=0.0,
                    conditions={"reel_weights": {b: {"BR0": 1}}, "gp_grades": {b: gp_base}, "bonus": None},
                ),
                Distribution(
                    criteria="basegame", quota=rest,
                    conditions={"reel_weights": {b: {"BR0": 1}}, "gp_grades": {b: gp_base}, "bonus": None},
                ),
            ]

        self.bet_modes = [
            BetMode(
                name="base", cost=1.0, rtp=self.rtp, max_win=self.wincap,
                auto_close_disabled=False, is_feature=True, is_buybonus=False,
                distributions=base_dists(1.0),
            ),
            # FUEL CHANCE: one base spin with ~2.2x the chance of any bonus (MIDNIGHT RUN included).
            # Same reels and rules as base; the optimiser's targets set the real 2.2x (phase 2).
            BetMode(
                name="chance", cost=3.0, rtp=self.rtp, max_win=self.wincap,
                auto_close_disabled=False, is_feature=True, is_buybonus=False,
                distributions=base_dists(2.2),
            ),
            # FILL UP buy (100x)
            BetMode(
                name="fillup", cost=100.0, rtp=self.rtp, max_win=self.wincap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap", quota=0.002, win_criteria=self.wincap,
                        conditions={"reel_weights": {b: {"BR0": 1}}, "buy": "fillup",
                                    "fillup_profile": "cap", "bonus": "fillup"},
                    ),
                    Distribution(
                        criteria="fillup", quota=0.998,
                        conditions={"reel_weights": {b: {"BR0": 1}}, "buy": "fillup",
                                    "fillup_profile": "standard", "bonus": "fillup"},
                    ),
                ],
            ),
            # PREMIUM buy (300x)
            BetMode(
                name="premium", cost=300.0, rtp=self.rtp, max_win=self.wincap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(
                        # every pump in the bonus rolls FULL TANK: its column stays MAX for the rest
                        # of the bonus and the next cluster on it pays the max win
                        criteria="wincap", quota=0.004, win_criteria=self.wincap,
                        conditions={"reel_weights": {b: {"BR0": 1}}, "buy": "premium",
                                    "gp_grades": {f: gp_cap}, "bonus": "premium"},
                    ),
                    Distribution(
                        criteria="premium", quota=0.996,
                        conditions={"reel_weights": {b: {"BR0": 1}}, "buy": "premium",
                                    "gp_grades": {f: gp_free}, "bonus": "premium"},
                    ),
                ],
            ),
            # NITRO SPIN (500x): one spin, every cell preloaded x16..x2048. Scatter-free strip:
            # a NITRO spin cannot trigger a bonus.
            BetMode(
                name="nitro", cost=500.0, rtp=self.rtp, max_win=self.wincap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap", quota=0.004, win_criteria=self.wincap,
                        conditions={"reel_weights": {b: {"NR0": 1}}, "gp_grades": {b: gp_base},
                                    "nitro_cells": nitro_cells_rich, "bonus": None},
                    ),
                    Distribution(
                        criteria="0", quota=0.05, win_criteria=0.0,
                        conditions={"reel_weights": {b: {"NR0": 1}}, "gp_grades": {b: gp_base},
                                    "nitro_cells": nitro_cells, "bonus": None},
                    ),
                    Distribution(
                        criteria="nitro", quota=0.946,
                        conditions={"reel_weights": {b: {"NR0": 1}}, "gp_grades": {b: gp_base},
                                    "nitro_cells": nitro_cells, "bonus": None},
                    ),
                ],
            ),
            # MIDNIGHT RUN buy (500x): the natural MIDNIGHT RUN (10 sticky free spins, every cell
            # starting at x4, the pump-rich FRM strip), bought outright: no base spin, no scatters.
            # The book opens like the premium buy's: freeSpinTrigger (DS, no positions) ->
            # enterBonus (midnight, bought) -> cellMults bonusStart x4 -> the 10 spins.
            BetMode(
                name="midnight", cost=500.0, rtp=self.rtp, max_win=self.wincap,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(
                        # every pump in the bonus rolls FULL TANK: its column stays MAX for the rest
                        # of the bonus and the next cluster on it pays the max win
                        criteria="wincap", quota=0.004, win_criteria=self.wincap,
                        conditions={"reel_weights": {b: {"BR0": 1}}, "buy": "midnight",
                                    "gp_grades": {f: gp_cap}, "bonus": "midnight"},
                    ),
                    Distribution(
                        criteria="midnight", quota=0.996,
                        conditions={"reel_weights": {b: {"BR0": 1}}, "buy": "midnight",
                                    "gp_grades": {f: gp_free}, "bonus": "midnight"},
                    ),
                ],
            ),
        ]
