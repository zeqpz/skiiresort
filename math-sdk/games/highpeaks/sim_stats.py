"""Raw (unforced, unoptimised) statistics for every Falcos mode, simulated in memory.

The books in library/ are FORCED per criteria (so the client sees every feature); their uniform
lookup tables say nothing about real frequencies. This tool plays NATURAL rounds instead - no
criteria, nothing forced, nothing rejected - and reports what the reels and tables give before
the optimiser weights anything:

    python sim_stats.py                       # 20k base, 2k per bonus, 8 processes
    python sim_stats.py --base 50000 --bonus 5000 --procs 8 --json out.json

Per mode: RTP (x cost), hit rate, average win, max seen, feature frequency per round, bonus
trigger rates (base), average bonus win. "midnight" plays MIDNIGHT RUN directly, as the 500x
MIDNIGHT RUN buy does (natural, unweighted: the buy's optimiser weights are not applied here).
"""

import argparse
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from game_config import GameConfig  # noqa: E402
from gamestate import GameState  # noqa: E402
from src.config.distributions import Distribution  # noqa: E402
from src.config.betmode import BetMode  # noqa: E402


def natural_config():
    cfg = GameConfig()
    b, f = cfg.basegame_type, cfg.freegame_type
    gp = cfg.gp_tables
    common = {"gp_grades": {b: gp["base"], f: gp["free"]}, "fillup_profile": "standard", "require_win": False}

    def mode(name, cost, conds):
        c = dict(common)
        c.update(conds)
        return BetMode(name=name, cost=cost, rtp=cfg.rtp, max_win=cfg.wincap, auto_close_disabled=False,
                       is_feature=False, is_buybonus=False,
                       distributions=[Distribution(criteria="natural", quota=1.0, conditions=c)])

    cfg.bet_modes = [
        mode("base", 1.0, {"reel_weights": {b: {"BR0": 1}}, "bonus": "any"}),
        mode("fillup", 100.0, {"reel_weights": {b: {"BR0": 1}}, "buy": "fillup", "bonus": "fillup"}),
        mode("premium", 300.0, {"reel_weights": {b: {"BR0": 1}}, "buy": "premium", "bonus": "premium"}),
        mode("midnight", 500.0, {"reel_weights": {b: {"BR0": 1}}, "buy": "midnight", "bonus": "midnight"}),
        mode("nitro", 500.0, {"reel_weights": {b: {"NR0": 1}}, "bonus": None,
                              "nitro_cells": cfg.nitro_tables["standard"]}),
    ]
    return cfg


def worker(args):
    mode, start, n = args
    cfg = natural_config()
    gs = GameState(cfg)
    gs.betmode = mode
    gs.criteria = "natural"
    from src.wins.win_manager import WinManager
    gs.win_manager = WinManager(cfg.basegame_type, cfg.freegame_type, cfg.wincap)
    rows = []
    for sim in range(start, start + n):
        before = dict(gs.stats)
        gs.run_spin(sim, sim + 7_000_000)
        delta = {k: v - before.get(k, 0) for k, v in gs.stats.items() if v - before.get(k, 0)}
        book = gs.library[sim + 1]
        rows.append({
            "win": book["payoutMultiplier"] / 100,
            "base": round(book["baseGameWins"], 2),
            "free": round(book["freeGameWins"], 2),
            "bonus": gs.bonus_kind,
            "events": len(book["events"]),
            "bytes": len(json.dumps(book)),
            "stats": delta,
        })
        gs.library = {}
    return rows


def summarise(mode, cost, rows):
    n = len(rows)
    wins = [r["win"] for r in rows]
    hits = [w for w in wins if w > 0]
    out = {
        "mode": mode, "rounds": n, "cost": cost,
        "rtp": round(sum(wins) / n / cost, 4),
        "hit_rate": round(len(hits) / n, 4),
        "one_in": round(n / max(len(hits), 1), 2),
        "avg_win_x": round(sum(hits) / max(len(hits), 1), 3),
        "avg_round_x": round(sum(wins) / n, 3),
        "max_x": max(wins),
        "wincap_rounds": sum(1 for w in wins if w >= 50000),
        "max_book_kb": round(max(r["bytes"] for r in rows) / 1024, 1),
        "avg_book_kb": round(sum(r["bytes"] for r in rows) / n / 1024, 2),
    }
    # feature frequency: share of rounds where it happened at least once, and per round
    keys = sorted({k for r in rows for k in r["stats"]})
    out["per_round"] = {k: round(sum(r["stats"].get(k, 0) for r in rows) / n, 4) for k in keys}
    out["rounds_with"] = {k: round(sum(1 for r in rows if r["stats"].get(k, 0)) / n, 4) for k in keys}
    if mode == "base":
        base_only = [r for r in rows if r["bonus"] is None]
        out["base_game_rtp"] = round(sum(r["base"] for r in rows) / n, 4)
        out["base_game_hit_rate"] = round(sum(1 for r in base_only if r["win"] > 0) / max(len(base_only), 1), 4)
        trig = {}
        for kind in ("fillup", "premium", "midnight"):
            ks = [r for r in rows if r["bonus"] == kind]
            trig[kind] = {
                "count": len(ks),
                "one_in": round(n / len(ks), 1) if ks else None,
                "avg_bonus_win_x": round(sum(r["free"] for r in ks) / len(ks), 2) if ks else None,
                "rtp_share": round(sum(r["free"] for r in ks) / n, 4),
            }
        out["triggers"] = trig
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=int, default=20000)
    ap.add_argument("--bonus", type=int, default=2000)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--modes", nargs="+", default=["base", "fillup", "premium", "midnight", "nitro"])
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    costs = {"base": 1.0, "fillup": 100.0, "premium": 300.0, "midnight": 500.0, "nitro": 500.0}
    results = []
    with Pool(args.procs) as pool:
        for mode in args.modes:
            n = args.base if mode == "base" else args.bonus
            chunk = (n + args.procs - 1) // args.procs
            jobs = [(mode, i * chunk, min(chunk, n - i * chunk)) for i in range(args.procs) if n - i * chunk > 0]
            rows = [r for part in pool.map(worker, jobs) for r in part]
            s = summarise(mode, costs[mode], rows)
            results.append(s)
            print(json.dumps(s, indent=1), flush=True)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1)


if __name__ == "__main__":
    main()
