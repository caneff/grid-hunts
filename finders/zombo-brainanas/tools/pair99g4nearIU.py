"""Neighbours of pair99g4 UI_w3_s0: UI kind, chocolate 1/3 circle, >= 4 uninfected groups, each grid >= MIN_DIST (6) shading cells
from that grid and the earlier ones of this run. usage: pair99g4near.py 0 1 [nseeds] [limit] [stall] -> hunt/pair99g4nearIU/full_UI_w3_s<seed>.json"""
import sys, time, os, json
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/pair99g4nearIU/"; os.makedirs(OUT, exist_ok=True)
shard, n = int(sys.argv[1]), int(sys.argv[2])
nseeds = int(sys.argv[3]) if len(sys.argv) > 3 else 6
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 600
stall = int(sys.argv[5]) if len(sys.argv) > 5 else 90
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B = (8, 6), (8, 8)
kinds = [("IU", {A: 1, B: 0})]
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
for i, (kind, sh) in enumerate(kinds):
    if i % n != shard: continue
    avoid = [{p: int(json.load(open(f))["infected"][p[0]][p[1]] == "*") for p in zb.CELLS} for f in (Z + "hunt/pair99g4/full_IU_w3_s0.json", Z + "hunt/pair99g4/full_IU_w6_s1.json")]
    for seed in range(nseeds):
        w = 3
        name = f"{kind}_w{w}_s{seed}"
        if os.path.exists(OUT + f"full_{name}.json"):
            d = json.load(open(OUT + f"full_{name}.json")); avoid.append({p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}); continue
        t = time.time(); log(f"{name}: start")
        bonus = {p: zb.CIRCLE_WEIGHT // w for p in zb.CELLS}
        found = zb.solve_valid(circles={A: None, B: None}, seed=100 + seed, limit=limit, min_pockets=1, objective=True,
                               avoid=avoid, min_distance=int(os.environ.get("MIN_DIST", 6)), log=log, stall=stall, stop_at=99, fix_shade=sh, bonus=bonus, min_groups=4)
        if found is None:
            log(f"{name}: no grid within {limit}s"); continue
        sol, shade = found; circ = zb.circle_candidates(sol, shade)
        zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
        avoid.append(dict(shade))
        log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)} ({time.time()-t:.0f}s)")
log(f"SHARD {shard} DONE")
