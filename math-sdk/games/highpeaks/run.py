"""Generate Falcos books, lookup tables and config files.

    python run.py                                   # phase-1 test books (small)
    python run.py --base 200000 --others 50000 --threads 8
    python run.py --modes base nitro                # only these modes; the others' files stay
    python run.py --modes fillup --others 20000 --threads 8 --batch 1250   # bound memory
    python run.py --optimize --analysis --checks    # phase 2 (needs the Rust toolchain)

Every mode's sim count must divide evenly by --threads (the SDK splits sims per thread), and by
threads x batch when it is larger than batch^2.
Without --optimize the lookup tables are uniform (weight 1 per book): the client then meets every
criteria at its sim quota, which is what front-end testing wants - NOT the real frequencies
(sim_stats.py gives those).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gamestate import GameState  # noqa: E402
from game_config import GameConfig  # noqa: E402
from game_optimization import OptimizationSetup  # noqa: E402
from src.state.run_sims import create_books  # noqa: E402
from src.write_data.write_configs import generate_configs  # noqa: E402

MODES = ("base", "chance", "fillup", "premium", "nitro", "midnight")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Simulate Falcos outcomes.")
    ap.add_argument("--base", type=int, default=2000, help="base mode sims")
    ap.add_argument("--others", type=int, default=500, help="sims for chance / fillup / premium / nitro / midnight")
    ap.add_argument("--modes", nargs="+", default=None, help=f"subset of {MODES}")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--batch", type=int, default=50000,
                    help="sims per thread per batch (memory: bonus books are ~30 KB each)")
    ap.add_argument("--rust-threads", type=int, default=8)
    ap.add_argument("--no-sims", action="store_true")
    ap.add_argument("--optimize", action="store_true")
    ap.add_argument("--analysis", action="store_true")
    ap.add_argument("--checks", action="store_true")
    args = ap.parse_args()

    num_sim_args = {m: (args.base if m == "base" else args.others) for m in MODES}
    if args.modes:
        unknown = set(args.modes) - set(MODES)
        assert not unknown, f"unknown modes {sorted(unknown)}"
        num_sim_args = {m: n for m, n in num_sim_args.items() if m in args.modes}
    for m, n in num_sim_args.items():
        assert n % args.threads == 0, f"{m}: {n} sims do not split evenly over {args.threads} threads"

    batching_size = args.batch
    compression = True
    profiling = False

    config = GameConfig()
    gamestate = GameState(config)

    if not args.no_sims:
        # a fresh uniform table each run: the SDK only writes lookUpTable_<mode>_0.csv when absent
        for m in num_sim_args:
            stale = os.path.join(config.publish_path, f"lookUpTable_{m}_0.csv")
            if os.path.exists(stale) and not args.optimize:
                os.remove(stale)
        create_books(gamestate, config, num_sim_args, batching_size, args.threads, compression, profiling)

    OptimizationSetup(config)
    generate_configs(gamestate)

    if args.optimize:
        from optimization_program.run_script import OptimizationExecution

        OptimizationExecution().run_all_modes(config, list(num_sim_args), args.rust_threads)
        # no single buy board drawn more often than 1 in 2,000 rounds (see cap_books.py)
        import subprocess
        buys = [m for m in num_sim_args if m in ("fillup", "premium", "nitro", "midnight")]
        if buys:
            subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cap_books.py"),
                            "--modes", *buys], check=True)
        # FUEL CHANCE: keep etl40b inside the 3-star band (see trim_chance_tail.py)
        if "chance" in num_sim_args:
            subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "trim_chance_tail.py")],
                           check=True)
        generate_configs(gamestate)

    if args.analysis:
        from utils.game_analytics.run_analysis import create_stat_sheet

        create_stat_sheet(gamestate, custom_keys=[{"symbol": "fillup"}, {"symbol": "premium"},
                                                  {"symbol": "midnight"}, {"symbol": "fulltank"}])

    if args.checks:
        from utils.rgs_verification import execute_all_tests

        execute_all_tests(config)
