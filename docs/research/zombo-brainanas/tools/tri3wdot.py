"""As tri3 (circles r9c7 r8c9 r6c8) with a forced white dot on one edge (both cells uninfected, consecutive digits).
usage: tri3wdot.py kind r1c1 r2c2 [nseeds] [limit] [stall] [groups]  (cells 1-based like r6c5) -> hunt/tri3wdot/full_<edge>_<kind>_w<3|6>_s<seed>.json"""
import sys, time, os, json, re
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/tri3wdot/"; os.makedirs(OUT, exist_ok=True)
kind = sys.argv[1]
cell = lambda s: tuple(int(v) - 1 for v in re.findall(r"\d", s))
P, Q = cell(sys.argv[2]), cell(sys.argv[3]); edge = sys.argv[2] + sys.argv[3]
nseeds = int(sys.argv[4]) if len(sys.argv) > 4 else 3
limit = int(sys.argv[5]) if len(sys.argv) > 5 else 600
stall = int(sys.argv[6]) if len(sys.argv) > 6 else 90
groups = int(sys.argv[7]) if len(sys.argv) > 7 else 1
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B, C = (8, 6), (7, 8), (5, 7)  # r9c7, r8c9, r6c8
sh = {A: int(kind[0] == "I"), B: int(kind[1] == "I"), P: 0, Q: 0}
_build = zb.build
def build(*a, **k):
    m, x, inf = _build(*a, **k); d = m.NewBoolVar("wd")
    m.Add(x[P] - x[Q] == 1).OnlyEnforceIf(d); m.Add(x[Q] - x[P] == 1).OnlyEnforceIf(d.Not())
    return m, x, inf
zb.build = build
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
avoid = []
for seed in range(nseeds):
    w = 3 if seed % 2 == 0 else 6
    name = f"{edge}_{kind}_w{w}_s{seed}" + (f"_g{groups}" if groups > 1 else "")
    if os.path.exists(OUT + f"full_{name}.json"):
        d = json.load(open(OUT + f"full_{name}.json")); avoid.append({p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}); continue
    t = time.time(); log(f"{name}: start")
    bonus = {p: zb.CIRCLE_WEIGHT // w for p in zb.CELLS}
    found = zb.solve_valid(circles={A: None, B: None, C: None}, seed=100 + seed, limit=limit, min_pockets=1, objective=True,
                           avoid=avoid, min_distance=12, log=log, stall=stall, stop_at=99, fix_shade=sh, bonus=bonus, min_groups=groups)
    if found is None:
        log(f"{name}: no grid within {limit}s"); break
    sol, shade = found; circ = zb.circle_candidates(sol, shade)
    zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
    avoid.append(dict(shade))
    log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)} ({time.time()-t:.0f}s)")
log(f"{edge} {kind} DONE")
