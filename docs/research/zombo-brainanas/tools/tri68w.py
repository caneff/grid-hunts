"""Circles r6c8 + r9c7 + r9c9, white dot forced on r7c5-r7c6 (both uninfected, consecutive digits),
circles + chocolate maximized (CIRCLE_WEIGHT//w per infected cell, w alternates 3/6), >= `groups` uninfected groups.
usage: tri68w.py shard nshards [nseeds] [limit] [stall] [groups] -> hunt/tri68w/full_<kind>_w<3|6>_s<seed>.json (groups=4 was infeasible for both kinds; use groups=1)"""
import sys, time, os, json
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/tri68w/"; os.makedirs(OUT, exist_ok=True)
shard, n = int(sys.argv[1]), int(sys.argv[2])
nseeds = int(sys.argv[3]) if len(sys.argv) > 3 else 4
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 600
stall = int(sys.argv[5]) if len(sys.argv) > 5 else 90
groups = int(sys.argv[6]) if len(sys.argv) > 6 else 4
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B, C = (8, 6), (8, 8), (5, 7)  # r9c7, r9c9, r6c8
W1, W2 = (6, 4), (6, 5)  # r7c5, r7c6: the white dot
_build = zb.build
def build(*a, **k):  # white dot: consecutive digits (shading fixed uninfected via fix_shade)
    m, x, inf = _build(*a, **k)
    d = m.NewBoolVar("wd")
    m.Add(x[W1] - x[W2] == 1).OnlyEnforceIf(d)
    m.Add(x[W2] - x[W1] == 1).OnlyEnforceIf(d.Not())
    return m, x, inf
zb.build = build
kinds = [("IU", {A: 1, B: 0}), ("UI", {A: 0, B: 1})]
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
for i, (kind, sh) in enumerate(kinds):
    if i % n != shard: continue
    sh = {**sh, W1: 0, W2: 0}
    avoid = []
    for seed in range(nseeds):
        w = 3 if seed % 2 == 0 else 6
        name = f"{kind}_w{w}_s{seed}"
        if os.path.exists(OUT + f"full_{name}.json"):
            d = json.load(open(OUT + f"full_{name}.json")); avoid.append({p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}); continue
        t = time.time(); log(f"{name}: start")
        bonus = {p: zb.CIRCLE_WEIGHT // w for p in zb.CELLS}
        found = zb.solve_valid(circles={A: None, B: None, C: None}, seed=100 + seed, limit=limit, min_pockets=1, objective=True,
                               avoid=avoid, min_distance=12, log=log, stall=stall, stop_at=99, fix_shade=sh, bonus=bonus, min_groups=groups)
        if found is None:
            log(f"{name}: no grid within {limit}s"); continue
        sol, shade = found; circ = zb.circle_candidates(sol, shade)
        zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
        avoid.append(dict(shade))
        log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)} ({time.time()-t:.0f}s)")
log(f"SHARD {shard} DONE")
