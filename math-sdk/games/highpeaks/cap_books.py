"""Cap the heaviest books of the optimised buy tables (run after every optimisation; run.py does).

The optimiser weights payout VALUES and splits each value's weight over the books paying it, so a
payout only one book reaches can make that one board come up far more often than the rest (NITRO:
a single 49.6x board 1 in 221 spins). Per-book scaling, which fixes this in the base game, made the
optimiser search forever on the buys' pools of mostly unique payouts, so the cap is applied here
instead:

* no book may weigh more than 1 / --cap of its table (default 1 in 2,000 rounds);
* a capped book's excess goes to the books paying close to it (0.8x .. 1.25x its payout, widened up to 3x when one
  side is empty; never
  0, never the max win, never up across a tail-fence edge, so bigwin / highwin never gain weight), split between the ones paying less and the ones paying more so
  the payout-weighted sum - the RTP - is unchanged (to integer rounding) and every book keeps
  paying exactly what it paid;
* the table's hit rate is unchanged (only winning books move).

The books are not touched, so the verification sidecars stay valid. A second run changes nothing.

    python cap_books.py [--modes fillup premium nitro midnight] [--cap 2000] [--dry-run]
"""

import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISH = os.path.join(HERE, "library", "publish_files")
BUY_MODES = ("fillup", "premium", "nitro", "midnight")


def read(mode):
    with open(os.path.join(PUBLISH, f"lookUpTable_{mode}_0.csv"), encoding="utf-8") as fh:
        return [[int(x) for x in line.split(",")] for line in fh if line.strip()]


def write(mode, rows):
    with open(os.path.join(PUBLISH, f"lookUpTable_{mode}_0.csv"), "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(f"{i},{w},{p}\n" for i, w, p in rows))


def cap_table(rows, one_in, edges):
    total = sum(w for _, w, _ in rows)
    cap = total // one_in
    by_pay = sorted(range(len(rows)), key=lambda k: rows[k][2])
    band = lambda p: sum(1 for e in edges if p >= e)       # noqa: E731  (fence bands)
    moved = 0
    for _ in range(20):
        heavy = [k for k in range(len(rows)) if rows[k][1] > cap and 0 < rows[k][2] < edges[-1]]
        if not heavy:
            break
        for k in heavy:
            v = rows[k][2]
            excess = rows[k][1] - cap
            # upper recipients stay in the book's band; lower ones may sit in the band below
            # (moving weight DOWN out of a tail band only lowers the tail statistics)
            near = [j for j in by_pay if 0 < rows[j][2] and band(rows[j][2]) <= band(v) and rows[j][1] < cap]
            for wide in (1.25, 1.5, 2.0, 3.0):        # widen until both sides have books
                lower = [j for j in near if v / wide <= rows[j][2] < v]
                upper = [j for j in near if v < rows[j][2] <= v * wide and band(rows[j][2]) == band(v)]
                if lower and upper:
                    break
            if not lower or not upper:
                continue
            m_lo = sum(rows[j][2] for j in lower) / len(lower)
            m_hi = sum(rows[j][2] for j in upper) / len(upper)
            # a to the lower group, b to the upper: a + b = excess, a*m_lo + b*m_hi = excess*v
            a = excess * (m_hi - v) / (m_hi - m_lo)
            b = excess - a
            each_lo, each_hi = a / len(lower), b / len(upper)
            given = 0
            for j in lower:
                add = int(each_lo)
                rows[j][1] += add
                given += add
            for j in upper:
                add = int(each_hi)
                rows[j][1] += add
                given += add
            rows[k][1] -= given
            moved += given
    return moved, cap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", nargs="+", default=list(BUY_MODES))
    ap.add_argument("--cap", type=int, default=2000, help="no book heavier than 1 in CAP rounds")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
    sys.path.insert(0, HERE)
    from game_config import GameConfig
    cfg = GameConfig()
    # fence bands (the optimiser fixed each band's total; weight never crosses a band edge)
    edges = {m: sorted({int(round(t * 100)) for t in (cfg.highwin_threshold.get(m), cfg.bigwin_threshold.get(m))
                        if t} | {int(round(cfg.wincap * 100))}) for m in BUY_MODES}
    for mode in args.modes:
        rows = read(mode)
        total = sum(w for _, w, _ in rows)
        rtp0 = sum(w * p for _, w, p in rows) / total
        top0 = max(w for _, w, _ in rows)
        moved, cap = cap_table(rows, args.cap, edges[mode])
        rtp1 = sum(w * p for _, w, p in rows) / total
        top1 = max(w for _, w, _ in rows)
        assert sum(w for _, w, _ in rows) == total and min(w for _, w, _ in rows) >= 0
        print(f"{mode}: heaviest book 1 in {total / top0:,.0f} -> 1 in {total / top1:,.0f}; "
              f"moved {moved / total:.4%} of the weight; payout mean {rtp0 / 100:.6f} -> {rtp1 / 100:.6f}")
        if not args.dry_run:
            write(mode, rows)


if __name__ == "__main__":
    main()
