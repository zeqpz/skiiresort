"""Optimisation targets for Falcos (Rust optimiser, math phase 2).

Every mode RTP 0.965 (inside the 96.00-96.70% band; the 3-star volatility check fails above
0.967). rtp values are shares of the MODE'S COST: a criteria returning R base bets in a mode costing
c is asked as R / c. Max win 50,000x in every mode.

How the targets are built
-------------------------
The setup is built AFTER the sims (run.py) and reads each mode's simulated pool
(library/lookup_tables/lookUpTable_<mode>.csv + library/forces/force_record_<mode>.json), walking the
fences in the optimiser's own order (each fence takes its books out of the pool before the next):

* every bonus fence is asked for its trigger rate (hr) at the pool's own mean (av_win), so its
  RTP share is exactly "trigger rate x average bonus" and the optimiser never has to bend a bonus;
* the ordinary base spins take what is left (rtp), at their pool mean (hr = av_win / rtp), and
  are weighted per BOOK toward a target win profile (base_book_scaling, ported from the previous
  game on this engine - DESIGN.md section 6);
* the buys' tails are fenced off with FIXED returns, because the 3-star volatility band reads
  etl10k (return from 10,000x+ wins) <= 0.8 and etl40b (return from wins >= 40x the mode cost)
  <= 0.9 in ABSOLUTE bets, and prob5k (P(win >= 5,000x) x 1 / 0.8 / 0.5 by cost) <= 1%:
  wincap (exactly 50,000x), bigwin (config.bigwin_threshold .. max win) and, for the 500x modes,
  highwin (5,000x .. 10,000x) get a fixed RTP share each; the main fence fits the rest.

Targets (base bets)
-------------------
    base     FILL UP 1 in 400, PREMIUM 1 in 2,700, MIDNIGHT RUN 1 in 14,000; max win 1 in 8M
             (rtp 0.00625); ordinary winning spins ~1 in 3
    chance   (3x) the bonuses and the max win 2.2x as often (5x failed etl40b), same average bonus; ordinary spins
             take the rest at hr 2.5 (their shape is set afterwards by trim_chance_tail.py)
    fillup   wincap 0.20 bb (1 in 250,000) | bigwin (>= 4,000x) 0.50 bb | fillup the rest
    premium  wincap 0.25 bb (1 in 200,000) | bigwin (>= 10,000x) 0.35 bb | premium the rest
    nitro    wincap 0.25 bb | bigwin 0.35 bb | highwin (5,000-10,000x) 1.7% of spins | 80% win
    midnight wincap 0.25 bb | bigwin 0.35 bb | highwin (5,000-10,000x) 1.2% of rounds | midnight
             (the MIDNIGHT RUN buy's main fence) the rest, so the mode returns 0.965 x 500 = 482.5x
"""

import json
import os
from collections import Counter

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)

CHANCE_BONUS = 1.7                       # High Peaks: 1.7x (Falcos 2.2x) - the jackpots in every bonus spin add to etl40b (2.0x: 1.02)

# High Peaks (2026-11-18): a natural bonus is asked at its pool mean, capped here (x bet). The spin modes' bonus pools
# are small (500-3,300 books) and heavy-tailed: a handful of 27,000-50,000x PREMIUM boards put the HIGHER CHANCE
# pool's mean at 895x and its etl40b at 1.52 (limit 0.9). The caps are the designed averages (DESIGN.md) plus the
# jackpots' share; the optimiser weights the pool down to them.
BONUS_AV_CAP = {"midnight": 1160.0, "premium": 500.0, "fillup": 118.0}
CHANCE_COST = 3.0

BASE_HR = {"midnight": 14000, "premium": 2700, "fillup": 400}
BASE_CAP_HR = 8.0e6                      # max win 1 in 8M base spins (rtp 0.00625)
BASE_HIT = 3.0                           # ordinary winning base spins ~1 in 3 (pool: 1 in 3.07)
CHANCE_HIT = 2.5                         # FUEL CHANCE's ordinary spins (see the docstring)

# fixed tail returns per buy mode, in base bets: (wincap, bigwin)
BUY_TAIL = {"fillup": (0.20, 0.50), "premium": (0.25, 0.35), "nitro": (0.25, 0.35), "midnight": (0.25, 0.35)}
HIGHWIN_P = {"nitro": 0.017, "midnight": 0.012}
NITRO_HIT = 0.80

# the pool means used when no pool is on disk yet (first run before any sims)
DEFAULT_MEAN = {"midnight": 930.0, "premium": 290.0, "fillup": 100.0, "basegame": 1.6,
                "bigwin": 15000.0, "highwin": 6800.0}

# base_book_scaling: how often (1 in N spins) the ordinary base spins should land a win in each
# band above 5x once weighted (natural 7x5 pool: 5-20x 1 in 57, 20-100x 1 in 435, 100x+ 1 in
# 6,150). Asked at 80% (BASE_TAIL_ASK) so the optimiser's RTP fix-up adds high wins rather than
# piling onto the smallest payouts; over 100x the optimiser's curves thin the pool's few books,
# so they are asked for BASE_TOP_LIFT times as much (both as tuned on the previous game).
BASE_TAIL = ((5, 20, 70), (20, 100, 400), (100, None, 8000))
BASE_TAIL_ASK = 0.8
BASE_TOP_LIFT = 3.0


# ------------------------------------------------------------------------------------- pools
class Pool:
    """A mode's simulated pool and the books each fence would take, in the optimiser's order."""

    def __init__(self, game_config, mode):
        lut = os.path.join(game_config.library_path, "lookup_tables", f"lookUpTable_{mode}.csv")
        forces = os.path.join(game_config.library_path, "forces", f"force_record_{mode}.json")
        self.ok = os.path.exists(lut) and os.path.exists(forces)
        self.pay, self.keys = {}, {}
        if not self.ok:
            return
        with open(lut, encoding="UTF-8") as f:
            for line in f:
                book, _, payout = (int(x) for x in line.split(","))
                self.pay[book] = payout / 100
        for option in json.load(open(forces, encoding="UTF-8")):
            for k in option["search"]:
                if k["name"] == "symbol":
                    self.keys.setdefault(k["value"], set()).update(option["bookIds"])
        self.left = set(self.pay)

    def take_exact(self, value):
        got = {b for b in self.left if self.pay[b] == value}
        self.left -= got
        return got

    def take_symbol(self, symbol):
        got = self.keys.get(symbol, set()) & self.left
        self.left -= got
        return got

    def mean(self, books, name):
        if not self.ok or not books:
            return DEFAULT_MEAN[name]
        return sum(self.pay[b] for b in books) / len(books)


def cond(**kw):
    return ConstructConditions(**kw).return_dict()


# --------------------------------------------------------------------------- base weighting
def base_book_scaling(pool, books, criteria, hr, rtp, cost):
    """One scaling entry per payout of the ordinary base spins, read off the pool (DESIGN.md
    section 6, previous game). The optimiser fits curves over PAYOUT VALUES and splits each value's
    weight evenly over the books paying it, so a payout few books reach would be drawn as often as
    one thousands reach. Scaling each payout by its book count makes the curves weigh BOOKS; on top
    sits BASE_TAIL (the shape wanted above 5x), and the wins under 5x lean toward the bottom
    (a v^-a tilt, a solved so the criteria keeps its mean)."""
    counts = Counter(pool.pay[b] for b in books if pool.pay[b] > 0)
    if not counts:
        return []
    share = 1 / hr                         # the criteria's share of all rounds
    mean = rtp * hr * cost                 # its average win in base bets
    split = BASE_TAIL[0][0]
    bands = []
    for lo, hi, one_in in BASE_TAIL:
        band = {v: n for v, n in counts.items() if lo < v <= (hi or float("inf"))}
        size = sum(band.values())
        if not size:
            continue
        bands.append((lo, hi or float("inf"), (1 / one_in) / share, size,
                      sum(v * n for v, n in band.items()) / size))
    tail_mass = sum(m for _, _, m, _, _ in bands)
    small_mean = (mean - sum(m * avg for _, _, m, _, avg in bands)) / (1 - tail_mass)
    small = {v: n for v, n in counts.items() if v <= split}
    lo_a, hi_a = -5.0, 10.0
    for _ in range(100):
        a = (lo_a + hi_a) / 2
        tilted = sum(n * v**-a for v, n in small.items())
        if sum(n * v**-a * v for v, n in small.items()) / tilted > small_mean:
            lo_a = a
        else:
            hi_a = a
    got = sum(n * v**-a * v for v, n in small.items()) / tilted
    if abs(got - small_mean) > 1e-6:
        print(f"WARNING {criteria}: BASE_TAIL leaves the small wins a {small_mean:.3f}x mean the pool "
              f"cannot tilt to (pool too small?) - no per-book scaling")
        return []
    total = tilted / (1 - tail_mass)
    levels = [(lo, hi, BASE_TAIL_ASK * m * total / size * (BASE_TOP_LIFT if lo >= 100 else 1.0))
              for lo, hi, m, size, _ in bands]
    most = max(counts.values())
    out = []
    for v, n in sorted(counts.items()):
        if v <= split:
            per_book = v**-a
        else:
            per_book = next((lvl for lo, hi, lvl in levels if lo < v <= hi), v**-a)
        out.append({"criteria": criteria, "scale_factor": n / most * per_book,
                    "win_range": (round(v - 0.005, 3), round(v + 0.005, 3)), "probability": 1.0})
    return out


# ------------------------------------------------------------------------------------- modes
def spin_mode(game_config, mode, k, cost, base_hit):
    """base (k=1, cost 1) and FUEL CHANCE (k=2.2, cost 3)."""
    cap, rtp = game_config.wincap, game_config.rtp
    pool = Pool(game_config, mode)
    out = {}
    cap_rtp = round(k / BASE_CAP_HR * cap / cost, 7)
    pool.take_exact(cap) if pool.ok else None
    out["wincap"] = cond(rtp=cap_rtp, av_win=cap, search_conditions=cap)
    used = cap_rtp
    for name in ("midnight", "premium", "fillup"):
        books = pool.take_symbol(name) if pool.ok else set()
        av = min(pool.mean(books, name), BONUS_AV_CAP[name])
        hr = BASE_HR[name] / k
        r = round(av / hr / cost, 7)
        out[name] = cond(rtp=r, hr=hr, search_conditions={"symbol": name})
        used += r
    zero = pool.take_exact(0.0) if pool.ok else set()
    out["0"] = cond(rtp=0, av_win=0, search_conditions=0)
    rest = round(rtp - used, 7)
    out["basegame"] = cond(rtp=rest, hr=base_hit)
    scaling = base_book_scaling(pool, pool.left, "basegame", base_hit, rest, cost) if pool.ok else []
    return out, scaling


def tail_fences(game_config, mode, pool, out):
    """wincap / bigwin / highwin with fixed returns. Returns (rtp used, probability used)."""
    cap, cost = game_config.wincap, next(bm.get_cost() for bm in game_config.bet_modes if bm.get_name() == mode)
    cap_bb, big_bb = BUY_TAIL[mode]
    if pool.ok:
        pool.take_exact(cap)
    out["wincap"] = cond(rtp=round(cap_bb / cost, 7), av_win=cap, search_conditions=cap)
    used_rtp, used_p = cap_bb / cost, cap_bb / cap
    big = pool.take_symbol("bigwin") if pool.ok else set()
    if big or not pool.ok:
        av = pool.mean(big, "bigwin")
        # rtp + hr, never av_win: the optimiser scales a searched fence's av_win by the mode cost
        out["bigwin"] = cond(rtp=round(big_bb / cost, 7), hr=round(av / big_bb, 4), search_conditions={"symbol": "bigwin"})
        used_rtp += big_bb / cost
        used_p += big_bb / av
    if mode in HIGHWIN_P:
        high = pool.take_symbol("highwin") if pool.ok else set()
        if high or not pool.ok:
            av = pool.mean(high, "highwin")
            p = HIGHWIN_P[mode]
            out["highwin"] = cond(rtp=round(p * av / cost, 7), hr=round(1 / p, 4), search_conditions={"symbol": "highwin"})
            used_rtp += p * av / cost
            used_p += p
    return used_rtp, used_p


def buy_mode(game_config, mode):
    pool = Pool(game_config, mode)
    out = {}
    used, _ = tail_fences(game_config, mode, pool, out)
    out[mode] = cond(rtp=round(game_config.rtp - round(sum(c["rtp"] for c in out.values()), 7), 7), hr="x")
    return out


def nitro_mode(game_config):
    pool = Pool(game_config, "nitro")
    out = {}
    _, used_p = tail_fences(game_config, "nitro", pool, out)
    zero = pool.take_exact(0.0) if pool.ok else None
    out["0"] = cond(rtp=0, av_win=0, search_conditions=0)
    rest = round(game_config.rtp - round(sum(c["rtp"] for c in out.values()), 7), 7)
    out["nitro"] = cond(rtp=rest, hr=round(1 / (NITRO_HIT - used_p), 6))
    return out


def _params(test_spins, test_weights):
    return ConstructParameters(
        num_show=1500, num_per_fence=2000, min_m2m=1, max_m2m=400, pmb_rtp=1.0,
        sim_trials=5000, test_spins=test_spins, test_weights=test_weights, score_type="rtp",
    ).return_dict()


class OptimizationSetup:
    """Handle all game mode optimisation parameters (built after the sims - see run.py)."""

    def __init__(self, game_config):
        self.game_config = game_config
        spin = _params([50, 100, 200], [0.3, 0.4, 0.3])
        buy = _params([10, 20, 50], [0.6, 0.2, 0.2])
        base, base_scaling = spin_mode(game_config, "base", 1.0, 1.0, BASE_HIT)
        chance, chance_scaling = spin_mode(game_config, "chance", CHANCE_BONUS, CHANCE_COST, CHANCE_HIT)
        opt = {
            "base": {"conditions": base, "scaling": ConstructScaling(base_scaling).return_dict(), "parameters": spin},
            "chance": {"conditions": chance, "scaling": ConstructScaling(chance_scaling).return_dict(), "parameters": spin},
            # buys stay value-weighted (per-book scaling made the optimiser search forever on
            # pools of mostly unique payouts); cap_books.py caps the heaviest books afterwards
            "fillup": {"conditions": buy_mode(game_config, "fillup"), "scaling": [], "parameters": buy},
            "premium": {"conditions": buy_mode(game_config, "premium"), "scaling": [], "parameters": buy},
            "nitro": {"conditions": nitro_mode(game_config), "scaling": [], "parameters": buy},
            "midnight": {"conditions": buy_mode(game_config, "midnight"), "scaling": [], "parameters": buy},
        }
        self.game_config.opt_params = opt
        verify_optimization_input(self.game_config, self.game_config.opt_params)
