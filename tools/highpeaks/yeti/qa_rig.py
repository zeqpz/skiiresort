"""High Peaks yeti QA on the EXPORTED rig (what the game plays), no Blender: skins the meshes with numpy exactly as
frontend/charrig.js does (4 weights / 255, 2x3 affines) and measures
  * planted boots: the lowest vertices of each boot, per frame, against the rest drawing (clips without a jump)
  * one-shots: first and last frame are the rest pose (identity bone transforms); the size of the last steps
  * loops: the step across the seam (last frame -> first) against the clip's ordinary frame-to-frame steps
  * the puff: the joint's end against his lips through the hold
  * meshes: triangles turned inside out or stretched hard (a tear, a fold, a limb bent the wrong way)
  * how much he moves: the range of each main bone's turn / stretch per clip, air time and height of the jumps
  * the puff's arm: the upper arm's turn through the hit (it must stay put: forearm and hand make the move)
  python tools/highpeaks/yeti/qa_rig.py [build|packed] [--src <rig folder>] [--bones]"""
import json, math, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BUILD = os.path.join(ROOT, "art", "highpeaks", "yeti", "rig_build", "rig")
PACKED = os.path.join(ROOT, "frontend", "assets", "yeti", "rig")
JUMPS = {"big_win", "bonus"}
PUFF = (84, 176)                                       # idle: the whole hit on the joint, look to arm home
ELBOW = (762, 715)                                     # the joint arm's elbow (art px, on forearm_r)


def load(src):
    man = json.load(open(os.path.join(src, "rig.json")))
    geo = open(os.path.join(src, "geo.bin"), "rb").read()
    B = len(man["bones"])
    clips = {}
    if "clips_bin" in man:
        blob = np.frombuffer(open(os.path.join(src, man["clips_bin"]), "rb").read(), np.float32)
        for c, C in man["clips"].items():
            clips[c] = blob[C["o"] // 4: C["o"] // 4 + C["frames"] * B * 6].reshape(C["frames"], B, 6).astype(np.float64)
    else:
        for c, C in man["clips"].items():
            clips[c] = np.frombuffer(open(os.path.join(src, c + ".bin"), "rb").read(), np.float32).reshape(C["frames"], B, 6).astype(np.float64)
    parts = {}
    for p in man["parts"]:
        n = p["verts"]
        parts[p["name"]] = dict(
            pos=np.frombuffer(geo, np.float32, n * 2, p["o_pos"]).reshape(n, 2).astype(np.float64),
            idx=np.frombuffer(geo, np.uint16, p["tris"] * 3, p["o_idx"]).reshape(-1, 3).astype(np.int64),
            bi=np.frombuffer(geo, np.uint8, n * 4, p["o_bi"]).reshape(n, 4).astype(np.int64),
            bw=np.frombuffer(geo, np.uint8, n * 4, p["o_bw"]).reshape(n, 4).astype(np.float64) / 255.0)
    return man, clips, parts


def skin(part, M):
    """Vertices of a part posed by one frame's bone affines M (B, 6) - charrig.js skin()."""
    x, y = part["pos"][:, 0:1], part["pos"][:, 1:2]
    m = M[part["bi"]]                                          # (n, 4, 6)
    px = m[:, :, 0] * x + m[:, :, 2] * y + m[:, :, 4]
    py = m[:, :, 1] * x + m[:, :, 3] * y + m[:, :, 5]
    w = part["bw"]
    return np.stack([(w * px).sum(1), (w * py).sum(1)], 1)


def point(M, j, p):
    return np.array([M[j, 0] * p[0] + M[j, 2] * p[1] + M[j, 4], M[j, 1] * p[0] + M[j, 3] * p[1] + M[j, 5]])


def area(v, idx):
    a, b, c = v[idx[:, 0]], v[idx[:, 1]], v[idx[:, 2]]
    return .5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))


def main():
    src = PACKED if "packed" in sys.argv[1:] else BUILD
    if "--src" in sys.argv:                                    # any rig folder (an older build kept for comparison)
        src = sys.argv[sys.argv.index("--src") + 1]
    man, clips, parts = load(src)
    bones = man["bones"]
    bi = {b: k for k, b in enumerate(bones)}
    ident = np.array([1, 0, 0, 1, 0, 0], np.float64)
    print(f"rig {src}\n  bones {len(bones)}  parts {len(parts)}  verts {sum(len(p['pos']) for p in parts.values())}  "
          f"clips {', '.join(f'{c} {C.shape[0]}f' for c, C in clips.items())}")
    assert len(bones) <= 255 and "idle" in clips
    for k, v in man["points"].items():
        assert v["bone"] in bi, f"point {k} hangs off a missing bone {v['bone']}"
    for name, p in parts.items():
        assert abs(p["bw"].sum(1) - 1).max() < 1e-6 and p["bi"].max() < len(bones), name
    ok = True

    # ---- boots
    print("planted boots (the 12 lowest vertices of each boot, skinned per frame, against the rest drawing):")
    for c, C in clips.items():
        row = []
        for leg, foot in (("leg_l", "foot_l"), ("leg_r", "foot_r")):
            P = parts[leg]
            low = np.argsort(-P["pos"][:, 1])[:12]
            sub = {k: v[low] for k, v in P.items() if k != "idx"}
            d = np.array([np.hypot(*(skin(sub, M) - sub["pos"]).T).max() for M in C])
            row.append(d)
        worst = max(r.max() for r in row)
        air = int((np.maximum(row[0], row[1]) > 2.0).sum())
        if c in JUMPS:
            print(f"  {c:13s} jumps: boots off the snow on {air} frames, highest {worst:.0f} art px")
        else:
            flag = "" if worst <= 2.0 else "   <-- SLIDES"
            ok &= worst <= 2.0
            print(f"  {c:13s} max {worst:.3f} art px{flag}")

    # ---- one-shots / loops
    print("clip ends:")
    shots = [c for c in clips if not man["clips"][c]["loop"]]
    rest = clips[shots[0]][0]
    off = abs(rest - ident)
    off[:, :4] *= 100
    print(f"  rest pose (frame 0 of {shots[0]}) vs the drawing: furthest bone {bones[int(off.max(1).argmax())]} {off.max():.2f} art px / percent")
    for c, C in clips.items():
        loop = man["clips"][c]["loop"]
        P = parts["head"]
        probe = [skin(p_, C[0]) * 0 for p_ in ()]              # (unused)
        allv = lambda M: np.concatenate([skin(p_, M) for n_, p_ in parts.items() if not n_.startswith("face_")])
        V = np.array([allv(M) for M in C])                     # (frames, verts, 2)
        step = np.hypot(*(V[1:] - V[:-1]).transpose(2, 0, 1)).max(1)             # the fastest vertex per frame step
        if loop:
            seam = np.hypot(*(V[0] - V[-1]).T).max()
            flag = "" if seam <= 1.6 * np.percentile(step, 95) + .5 else "   <-- SEAM"
            ok &= not flag
            print(f"  {c:13s} loop: seam step {seam:.2f} art px; ordinary steps median {np.median(step):.2f}, 95% {np.percentile(step, 95):.2f}, max {step.max():.2f}{flag}")
        else:
            d0, d1 = abs(C[0] - rest).max(), abs(C[-1] - rest).max()
            flag = "" if max(d0, d1) < 1e-6 else "   <-- NOT REST"
            ok &= not flag
            print(f"  {c:13s} one-shot: first frame off rest {d0:.2e}, last {d1:.2e}; last 6 steps (fastest vertex, art px) "
                  f"{' '.join(f'{s:.1f}' for s in step[-6:])}; max step {step.max():.1f}{flag}")

    # ---- the puff
    qp = os.path.join(os.path.dirname(BUILD), "qa_points.json")
    if os.path.exists(qp):
        win = json.load(open(qp))["contact"].get("idle", [])
        for (a, b, c_, d) in win:
            je, jl = bi[man["points"]["end"]["bone"]], bi[man["points"]["lips"]["bone"]]
            gap = [np.hypot(*(point(clips["idle"][f], je, man["points"]["end"]["at"]) - point(clips["idle"][f], jl, man["points"]["lips"]["at"])))
                   for f in range(a, d + 1)]
            hold = gap[b - a: c_ - a + 1]
            flag = "" if max(hold) <= 1.0 else "   <-- OFF HIS LIPS"
            ok &= not flag
            print(f"the puff (idle {a}-{d}): joint end to lips through the hold {b}-{c_}: max {max(hold):.3f} art px; "
                  f"coming in {' '.join(f'{g:.0f}' for g in gap[:b - a:2])}; leaving {' '.join(f'{g:.0f}' for g in gap[c_ - a + 1::2])}{flag}")

            # the puff is made by the forearm and the hand, hinging at the elbow: the upper arm (shoulder to elbow)
            # stays put. Its turn through the whole move, on screen and against his chest; where the elbow goes.
            C = clips["idle"]
            lo, hi = PUFF
            turn = lambda b: np.degrees(np.unwrap(np.arctan2(-C[lo:hi + 1, bi[b], 1], C[lo:hi + 1, bi[b], 0])))
            ua, fa, ha, ca, hda = (turn(b) for b in ("upper_arm_r", "forearm_r", "hand_r", "chest", "head"))
            inv = lambda M, j, p: np.linalg.solve(np.array([[M[j, 0], M[j, 2]], [M[j, 1], M[j, 3]]]), np.asarray(p) - M[j, 4:6])
            el = np.array([point(M, bi["forearm_r"], ELBOW) for M in C[lo:hi + 1]])
            el_c = np.array([inv(M, bi["chest"], point(M, bi["forearm_r"], ELBOW)) for M in C[lo:hi + 1]])
            lp_c = np.array([inv(M, bi["chest"], point(M, jl, man["points"]["lips"]["at"])) for M in C[lo:hi + 1]])
            span = lambda v: float(np.ptp(v))
            reach = lambda P: float(np.hypot(*(P - P[0]).T).max())
            rel = ua - ca
            flag = "" if span(rel) <= 8.0 else "   <-- THE UPPER ARM SWINGS"
            ok &= not flag
            print(f"the puff's arm (idle {lo}-{hi}): upper arm turns {span(ua):.1f} deg on screen, {span(rel):.1f} deg against his chest "
                  f"({rel.min() - rel[0]:+.1f} .. {rel.max() - rel[0]:+.1f}); forearm {span(fa):.1f}, hand {span(ha):.1f} deg on screen; "
                  f"forearm against upper arm {span(fa - ua):.1f}, hand against forearm {span(ha - fa):.1f} deg{flag}")
            print(f"                 elbow travels {reach(el):.1f} art px on screen, {reach(el_c):.1f} against his chest; "
                  f"his lips come {reach(lp_c):.1f} art px over (against his chest), the head turns {span(hda - ca):.1f} deg against it")

    # ---- every clip: how near the joint's end comes to his lips (a hit on the joint anywhere else would show here)
    if "end" in man["points"] and "lips" in man["points"]:
        je, jl = bi[man["points"]["end"]["bone"]], bi[man["points"]["lips"]["bone"]]
        near = []
        for c, C in clips.items():
            g = [float(np.hypot(*(point(M, je, man["points"]["end"]["at"]) - point(M, jl, man["points"]["lips"]["at"])))) for M in C]
            near.append(f"{c} {min(g):.0f} (frame {int(np.argmin(g))})")
        print("joint end to lips, nearest per clip (art px): " + ", ".join(near))

    # ---- meshes
    # ---- knees: the IK legs are nearly straight when he stands; their solve must not jitter
    print("knees (frame-to-frame jerk of each knee: the 2nd difference of its place, art px):")
    for c, C in clips.items():
        out = []
        for b, p0 in (("shin_l", (345, 1200)), ("shin_r", (690, 1200))):
            tr = np.array([point(M, bi[b], p0) for M in C])
            if man["clips"][c]["loop"]:
                tr = np.concatenate([tr[-2:], tr, tr[:2]])
            jerk = np.hypot(*(tr[2:] - 2 * tr[1:-1] + tr[:-2]).T)
            out.append(f"{b} median {np.median(jerk):.2f} max {jerk.max():.2f}")
        print(f"  {c:13s} " + "; ".join(out))

    print("meshes (triangles turned inside out / stretched or squeezed past 2.5x in area, worst frame per clip):")
    for c, C in clips.items():
        worst = {}
        for name, P in parts.items():
            if name.startswith("face_") or name in ("board", "snow"):
                continue
            a0 = area(P["pos"], P["idx"])
            flips, hard = 0, 0
            wf = (0, 0)
            for f, M in enumerate(C):
                a1 = area(skin(P, M), P["idx"]) / a0
                nflip, nh = int((a1 <= 0).sum()), int(((a1 > 2.5) | ((a1 > 0) & (a1 < .4))).sum())
                if nflip > flips:
                    flips, wf = nflip, (f, nflip)
                hard = max(hard, nh)
            if flips or hard:
                worst[name] = f"{flips} flipped (frame {wf[0]}), {hard} hard-stretched of {len(P['idx'])}"
        print(f"  {c:13s} " + ("clean" if not worst else "; ".join(f"{k}: {v}" for k, v in worst.items())))

    # ---- how much he moves
    print("motion (range over the clip; turn in degrees, stretch in percent along the bone, travel in art px):")
    main_b = [b for b in ("hips", "spine2", "chest", "head", "pom", "beard", "belly", "hem_l", "upper_arm_l", "forearm_l", "hand_l",
                          "upper_arm_r", "forearm_r", "hand_r", "thigh_l", "shin_l", "foot_l", "board") if b in bi]
    for c, C in clips.items():
        out = []
        for b in main_b:
            m = C[:, bi[b]]
            ang = np.degrees(np.unwrap(np.arctan2(-m[:, 1], m[:, 0])))
            out.append(f"{b} {ang.max() - ang.min():.0f}")
        hips = np.array([point(M, bi["hips"], (520, 1030)) for M in C])
        head = np.array([point(M, bi["head"], (485, 425)) for M in C])
        chest = np.array([point(M, bi["chest"], (517, 660)) for M in C])
        torso = np.hypot(*(chest - hips).T)
        print(f"  {c:13s} hips travel x {np.ptp(hips[:, 0]):.0f} y {np.ptp(hips[:, 1]):.0f} (up {hips[0, 1] - hips[:, 1].min():.0f}, down {hips[:, 1].max() - hips[0, 1]:.0f}); "
              f"torso length {100 * torso.min() / torso[0] - 100:+.0f}% .. {100 * torso.max() / torso[0] - 100:+.0f}%; "
              f"head travel x {np.ptp(head[:, 0]):.0f} y {np.ptp(head[:, 1]):.0f}; head vs chest turn {np.ptp(np.degrees(np.arctan2(-C[:, bi['head'], 1], C[:, bi['head'], 0]) - np.arctan2(-C[:, bi['chest'], 1], C[:, bi['chest'], 0]))):.0f} deg")
        print("                turns: " + ", ".join(out))
    if "--bones" in sys.argv:
        for c, C in clips.items():
            d = abs(C - ident)
            d[:, :, :4] *= 100
            for f in (0, C.shape[0] - 1):
                k = int(d[f].max(1).argmax())
                print(f"  {c} frame {f}: furthest from rest {bones[k]} {d[f, k].max():.3f}")
    print("RESULT", "ok" if ok else "PROBLEMS (see the arrows)")


if __name__ == "__main__":
    main()
