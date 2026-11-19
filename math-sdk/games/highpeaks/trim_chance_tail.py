"""Shape FUEL CHANCE's ordinary spins and keep the mode inside the 3-star etl40b limit (run after
optimising chance; run.py does).

FUEL CHANCE (3x) gives the bonuses 2.2x as often as base, but they return only ~0.35 of the
0.965, so the ordinary (`basegame`) spins must return the rest: ~4.4x per winning spin against a
natural ~1.55x. The optimiser fixes that fence's total weight (its share of rounds, i.e. the hit
rate) and its return, but left to itself it reaches that mean by piling weight onto a few payouts
(2026-11-10, after the refill change: 27% of all chance spins on 3-5x boards, one 5.0x board 1 in
17 spins, almost nothing under 1x). This script redraws the fence's shape and keeps its totals:

* every basegame book paying >= the etl40b edge (40 x the cost = 120x) gets weight 1 (it stays in
  the table, ~never drawn): etl40b is the return, in base bets, from 120x+ wins and must stay
  <= 0.9, and the bonuses alone put ~0.87 there;
* every other winning basegame book gets a weight proportional to payout^b - the natural pool
  tilted by one power, so boards paying the same are drawn equally often and the profile falls
  smoothly from the small wins up - with b solved so the fence keeps its return; its total weight
  is unchanged, so the hit rate is unchanged;
* zero-win, bonus and wincap books keep their weights. The books are not touched, so the
  verification sidecars stay valid. A second run changes nothing.

    python trim_chance_tail.py [--dry-run]
"""

import argparse
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "library")
LUT = os.path.join(LIB, "publish_files", "lookUpTable_chance_0.csv")
SEG = os.path.join(LIB, "lookup_tables", "lookUpTableSegmented_chance.csv")
COST = 3.0
EDGE = int(40 * COST * 100)          # payouts are in hundredths of the bet
BANDS = ((0.1, 1), (1, 2), (2, 3), (3, 5), (5, 20), (20, 40), (40, 120), (120, None))


def etl40(rows, total):
    return sum(p / 100 * w for _, w, p in rows if p >= EDGE) / total


def profile(rows, total):
    out = []
    for lo, hi in BANDS:
        p = sum(w for _, w, pp in rows if lo * 100 <= pp < (hi or 1e9) * 100) / total
        out.append(f"{lo}-{hi or ''}x {p:.2%}")
    return "  ".join(out)


def tilted_mean(vals, b):
    ws = [v ** b for v in vals]
    return sum(w * v for w, v in zip(ws, vals)) / sum(ws)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    crit = {int(r[0]): r[1] for r in csv.reader(open(SEG))}
    rows = [[int(x) for x in r] for r in csv.reader(open(LUT)) if r]
    total = sum(w for _, w, _ in rows)
    rtp0 = sum(w * p for _, w, p in rows)
    hits0 = sum(w for _, w, p in rows if p > 0)
    print(f"before: etl40b {etl40(rows, total):.4f}  rtp {rtp0 / total / 100 / COST:.6f}")
    print(f"        {profile(rows, total)}")

    fence = [k for k, (i, w, p) in enumerate(rows) if crit.get(i) == "basegame" and p > 0]
    tail = [k for k in fence if rows[k][2] >= EDGE]
    body = [k for k in fence if rows[k][2] < EDGE]
    weight = sum(rows[k][1] for k in fence) - len(tail)          # what the body shares
    mass = sum(rows[k][1] * rows[k][2] for k in fence) - sum(rows[k][2] for k in tail)
    target = mass / weight / 100                                  # the body's mean, in bets
    vals = [rows[k][2] / 100 for k in body]
    lo, hi = -3.0, 3.0
    assert tilted_mean(vals, lo) < target < tilted_mean(vals, hi), f"no tilt reaches a {target:.3f}x mean"
    for _ in range(200):
        b = (lo + hi) / 2
        if tilted_mean(vals, b) < target:
            lo = b
        else:
            hi = b
    b = (lo + hi) / 2
    raw = [v ** b for v in vals]
    scale = weight / sum(raw)
    exact = [r * scale for r in raw]
    new = [int(x) for x in exact]
    # integer remainder: one each to the books with the largest fractional parts (deterministic)
    for j in sorted(range(len(new)), key=lambda j: (new[j] - exact[j], body[j]))[: weight - sum(new)]:
        new[j] += 1
    for k in tail:
        rows[k][1] = 1
    for k, w in zip(body, new):
        rows[k][1] = w

    assert sum(w for _, w, _ in rows) == total and all(rows[k][1] >= 1 for k in fence)
    assert sum(w for _, w, p in rows if p > 0) == hits0
    rtp1 = sum(w * p for _, w, p in rows)
    print(f"after:  etl40b {etl40(rows, total):.4f}  rtp {rtp1 / total / 100 / COST:.6f}  "
          f"(ordinary spins: weight ~ payout^{b:.4f} over {len(body)} books, {len(tail)} books "
          f">= {EDGE / 100:.0f}x -> weight 1; heaviest ordinary board 1 in {total / max(new):,.0f})")
    print(f"        {profile(rows, total)}")
    if not a.dry_run:
        with open(LUT, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(f"{i},{w},{p}\n" for i, w, p in rows))


if __name__ == "__main__":
    main()
