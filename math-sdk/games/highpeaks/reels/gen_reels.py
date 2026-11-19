"""Generate the Falcos reel-strip CSVs (deterministic; stdlib only).

Strips (STRIP_LEN positions x 7 reels) for the 7x5 cluster board (7 reels x 5 rows):
    BR0   base game (and FUEL CHANCE): paying symbols, the four features, FALCOS Tokens (BS) on
          every reel and Midnight Tokens (DS) on reels 2, 4 and 6 only (index 1, 3, 5)
    FR0   PREMIUM free spins: FALCOS Tokens for the retrigger (3+ add 5 spins), a little richer in features
    FRM   MIDNIGHT RUN free spins: FALCOS Tokens for the retrigger, Gas Pumps far more often
    NR0   NITRO SPIN: the base strip without scatters (a NITRO spin cannot trigger a bonus)

Symbol counts are per reel (an int applies to all 7 reels, a 7-list sets each reel).

Spacing rules the game logic relies on:
  * scatter-class symbols (BS, DS) keep a circular gap of >= SPACED_GAP from each other, so a
    reel shows at most one of them in its 5-row window (plus padding) - the exact-count board
    forcing depends on it;
  * Gas Pumps keep the same gap from each other, so a column can never hold two pumps: a pump
    fires and leaves on the board it lands on, and a refill is one contiguous run of the strip
    (<= 6 symbols), so "at most one Gas Pump per column" (FALCOS_DESIGN.md) holds by construction.

The paying symbols fill the remaining stops in proportion to PAY_WEIGHTS: cluster pays live or
die on symbol frequency, so the lows are common and the highs scarce.

Run:  python reels/gen_reels.py
"""

import os
import random

STRIP_LEN = 200
NUM_REELS = 7
SPACED_GAP = 10

# relative share of the free stops (after scatters/features) each paying symbol takes.
# 7x5 retune (2026-11-09): 35 cells make 5+ clusters much rarer than on 7x7, so the lows are
# skewed harder (base hit rate ~1 in 3; the 7x7 weights H 4.5-7.5 / L 12-20 gave 1 in 4.2 and a
# base game worth 0.29x on 7x5).
PAY_WEIGHTS = {
    "H1": 3.5, "H2": 4.5, "H3": 5.5, "H4": 6.5,
    "L1": 12.0, "L2": 14.5, "L3": 17.0, "L4": 19.5, "L5": 23.0,
}
# NITRO SPIN: a 500x spin must not be max-or-nothing, so its strip leans hard on the lows - about
# four reveals in five hold a cluster and every cell is boosted.
PAY_WEIGHTS_NITRO = {
    "H1": 1.5, "H2": 2.0, "H3": 2.5, "H4": 3.0,
    "L1": 8.0, "L2": 12.0, "L3": 20.0, "L4": 32.0, "L5": 50.0,
}

# per-strip symbol counts: {symbol: int | [r0 .. r6]}  (7x5 retune, 2026-11-09 - see
# FALCOS_DESIGN.md "Math notes" for what each count was measured to give)
STRIPS = {
    "BR0": {
        "seed": 1101,
        # BS 10 per 1,400 stops (was 7): FILL UP ~1 in 400 base spins on the 5-row window
        # DS on reels 2/4/6 (index 1, 3, 5): 2/1/2 (was 1/1/1): MIDNIGHT RUN ~1 in 14,500
        "scatters": {"BS": [2, 1, 2, 1, 2, 1, 1], "DS": [0, 2, 0, 1, 0, 2, 0]},
        "pumps": 1,
        "features": {"ZP": 2, "ST": 1, "GT": [0, 0, 0, 1, 0, 0, 0]},
    },
    "FR0": {
        "seed": 2202,
        # FALCOS Tokens for the retrigger (owner, 2026-11-17): 16 per 1,400 stops, 3+ on a board ~1 in 100 spins
        "scatters": {"BS": [2, 2, 3, 2, 3, 2, 2]},
        "pumps": 1,
        # PREMIUM: 23 Zippos / 21 Scratch Tickets per strip set (was 14 / 14) - the bought bonus
        # averages ~0.96x its cost before weighting (it was ~0.2x on 7x5 with the 7x7 counts)
        "features": {"ZP": [3, 3, 4, 3, 4, 3, 3], "ST": 3, "GT": [0, 0, 0, 1, 0, 0, 0]},
    },
    "FRM": {
        "seed": 3303,
        "scatters": {"BS": [2, 2, 3, 2, 3, 2, 2]},   # the retrigger, as FR0
        "pumps": 3,       # MIDNIGHT RUN: "Gas Pumps landing far more often" (3x the base strip)
        # 18 Zippos / 14 Scratch Tickets (was 7 / 7): MIDNIGHT RUN averages ~930x
        "features": {"ZP": [3, 2, 3, 2, 3, 2, 3], "ST": 2, "GT": [0, 0, 0, 0, 0, 0, 0]},
    },
    "NR0": {
        "seed": 4404,
        "scatters": {},
        "pumps": 1,
        "features": {"ZP": 2, "ST": 1, "GT": [0, 0, 0, 1, 0, 0, 0]},
        "pay": PAY_WEIGHTS_NITRO,
    },
}


def per_reel(count) -> list:
    return list(count) if isinstance(count, (list, tuple)) else [count] * NUM_REELS


def circular_gap(a: int, b: int, length: int) -> int:
    diff = abs(a - b) % length
    return min(diff, length - diff)


def place_spaced(rng, count, taken, spaced):
    """Pick `count` free positions keeping SPACED_GAP circular distance from `spaced` members."""
    chosen = []
    for _ in range(count):
        candidates = [
            p for p in range(STRIP_LEN)
            if p not in taken and all(circular_gap(p, s, STRIP_LEN) >= SPACED_GAP for s in spaced)
        ]
        assert candidates, "no spaced position available; lower the counts or the gap"
        pick = rng.choice(candidates)
        chosen.append(pick)
        taken.add(pick)
        spaced.append(pick)
    return chosen


def build_reel(rng, reel_idx, spec):
    strip = [None] * STRIP_LEN
    taken = set()

    scatter_positions = []
    for sym, counts in spec["scatters"].items():
        for pos in place_spaced(rng, per_reel(counts)[reel_idx], taken, scatter_positions):
            strip[pos] = sym

    pump_positions = []
    for pos in place_spaced(rng, per_reel(spec["pumps"])[reel_idx], taken, pump_positions):
        strip[pos] = "GP"

    for sym, counts in spec["features"].items():
        placed = 0
        while placed < per_reel(counts)[reel_idx]:
            pos = rng.randrange(STRIP_LEN)
            if pos in taken:
                continue
            strip[pos] = sym
            taken.add(pos)
            placed += 1

    open_slots = [p for p in range(STRIP_LEN) if strip[p] is None]
    weights = spec.get("pay", PAY_WEIGHTS)
    total_w = sum(weights.values())
    counts = {s: int(len(open_slots) * w / total_w) for s, w in weights.items()}
    leftovers = len(open_slots) - sum(counts.values())
    for s in sorted(weights, key=weights.get, reverse=True)[:leftovers]:
        counts[s] += 1
    bag = [s for s, n in counts.items() for _ in range(n)]
    rng.shuffle(bag)
    for pos, sym in zip(open_slots, bag):
        strip[pos] = sym
    return strip


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for name, spec in STRIPS.items():
        rng = random.Random(spec["seed"])
        reels = [build_reel(rng, r, spec) for r in range(NUM_REELS)]
        path = os.path.join(out_dir, f"{name}.csv")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for row in range(STRIP_LEN):
                f.write(",".join(reels[r][row] for r in range(NUM_REELS)) + "\n")
        totals = {}
        for r in range(NUM_REELS):
            for s in reels[r]:
                totals[s] = totals.get(s, 0) + 1
        print(f"{name}: {path}")
        print("   totals:", dict(sorted(totals.items())))


if __name__ == "__main__":
    main()
