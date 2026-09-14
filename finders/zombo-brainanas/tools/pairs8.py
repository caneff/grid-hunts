"""Per box-8 cell pair and shading kind: can a grid have >= 5 brainanas with circles on both cells? usage: pairs8.py shard nshards [limit]"""
import sys, time, itertools
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/scratch-zombo/"
B8 = [p for p in zb.CELLS if zb.box(*p) == 8]
zb.BIG_POCKET_CELLS = frozenset(B8)
zb.WORKERS = 4  # box-8 library is 1.5x box 9; 8 workers crossed 9 GB
shard, n = int(sys.argv[1]), int(sys.argv[2]); limit = int(sys.argv[3]) if len(sys.argv) > 3 else 600
name = lambda p: f"r{p[0]+1}c{p[1]+1}"
def log(s): open(Z + "hunt/plant/pairs8.log", "a").write(s + "\n")
cases = [(a, b, k) for a, b in itertools.combinations(B8, 2) for k in ("II", "IU", "UI", "UU")]
import os
done = set(l.split(":")[0] for l in open(Z + "hunt/plant/pairs8.log")) if os.path.exists(Z + "hunt/plant/pairs8.log") else set()
for i, (a, b, k) in enumerate(cases):
    if i % n != shard or f"{name(a)}+{name(b)} {k}" in done: continue
    t = time.time()
    try:
        f = zb.solve_valid(circles={a: None, b: None}, fix_shade={a: int(k[0] == "I"), b: int(k[1] == "I")},
                           min_pockets=1, min_groups=5, limit=limit, seed=i)
        v = "FEASIBLE" if f else "infeasible"
    except TimeoutError:
        f, v = None, "TIMEOUT"
    log(f"{name(a)}+{name(b)} {k}: {v} {time.time()-t:.0f}s")
    if f: zb.dump(Z + f"hunt/groups/full_5_b8_{name(a)}_{name(b)}_{k}.json", *f, dict(f[0]), zb.circle_candidates(*f))
log(f"SHARD {shard} DONE")
