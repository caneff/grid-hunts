"""Which non-box-9 circle pins the r9c7/r9c9 shading? For each cell X outside box 9 and each kind (IU / UI):
is a valid grid with open circles on r9c7, r9c9 and X feasible? A kind infeasible for X means a circle on X pins the other kind.
usage: pinx.py shard(0=IU,1=UI) [limit] -> hunt/pinx/<kind>.log"""
import sys, time, os
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/pinx/"; os.makedirs(OUT, exist_ok=True)
shard = int(sys.argv[1]); limit = int(sys.argv[2]) if len(sys.argv) > 2 else 120
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B = (8, 6), (8, 8)
kind, sh = [("IU", {A: 1, B: 0}), ("UI", {A: 0, B: 1})][shard]
LOG = OUT + f"{kind}.log"
done = set(l.split()[0] for l in open(LOG)) if os.path.exists(LOG) else set()
for X in zb.CELLS:
    if zb.box(*X) == 9: continue
    name = f"r{X[0]+1}c{X[1]+1}"
    if name in done: continue
    t = time.time()
    try:
        found = zb.solve_valid(circles={A: None, B: None, X: None}, seed=1, limit=limit, min_pockets=1, fix_shade=sh)
        res = "feasible" if found else "INFEASIBLE"
    except TimeoutError:
        res = "unknown"
    open(LOG, "a").write(f"{name} {kind} {res} {time.time()-t:.0f}s\n")
open(LOG, "a").write(f"DONE {kind}\n")
