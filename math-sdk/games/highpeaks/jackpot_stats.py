"""LUT-weighted (as played) RTP and jackpot frequencies per mode, from the published books.

    python jackpot_stats.py [modes...]
"""
import io, json, os, sys
from collections import defaultdict
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "library", "publish_files")
COST = {"base": 1, "chance": 3, "fillup": 100, "premium": 300, "nitro": 500, "midnight": 500}

for mode in sys.argv[1:] or list(COST):
    w = {}
    for line in open(os.path.join(PUB, f"lookUpTable_{mode}_0.csv")):
        i, wt, p = line.strip().split(",")
        w[int(i)] = int(wt)
    tot = sum(w.values())
    rtp = hit = drops = jpret = 0.0
    lv = defaultdict(float)
    with open(os.path.join(PUB, f"books_{mode}.jsonl.zst"), "rb") as fh:
        for line in io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8"):
            b = json.loads(line)
            p = w[b["id"]] / tot
            rtp += p * b["payoutMultiplier"] / 100
            hit += p * (b["payoutMultiplier"] > 0)
            got = False
            for e in b["events"]:
                if e["type"] == "jackpotWin":
                    lv[e["level"]] += p
                    jpret += p * e["amount"] / 100
                    got = True
            drops += p * got
    c = COST[mode]
    one = lambda x: f"1 in {1/x:,.0f}" if x > 0 else "never"
    print(f"{mode:9} RTP {rtp/c:.4f}  hit {one(hit)}  rounds with a jackpot {one(drops)}  jackpot share of RTP {jpret/c:.4f}  "
          + "  ".join(f"{k} {one(v)}" for k, v in sorted(lv.items(), key=lambda kv: -kv[1])))
