"""Circle r9c7 (uninfected) + one other box-9 circle X (infected), r9c9 != 9, >= `groups` pockets, circles + chocolate
maximized. usage: x9hunt.py r8c9 [nseeds] [limit] [stall] [groups] -> hunt/x9/full_<X>_w<3|6>_s<seed>.json"""
import sys, time, os, json, re
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/x9/"; os.makedirs(OUT, exist_ok=True)
cell = lambda s: tuple(int(v) - 1 for v in re.findall(r"\d", s))
X = cell(sys.argv[1]); xn = sys.argv[1]
nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 600
stall = int(sys.argv[4]) if len(sys.argv) > 4 else 90
groups = int(sys.argv[5]) if len(sys.argv) > 5 else 4
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, R99 = (8, 6), (8, 8)
sh = {A: 0, X: 1}
_build = zb.build
def build(*a, **k):
    m, x, inf = _build(*a, **k); m.Add(x[R99] != 9); return m, x, inf
zb.build = build
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
avoid = []
for seed in range(nseeds):
    w = 3 if seed % 2 == 0 else 6
    name = f"{xn}_w{w}_s{seed}"
    if os.path.exists(OUT + f"full_{name}.json"):
        d = json.load(open(OUT + f"full_{name}.json")); avoid.append({p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}); continue
    t = time.time(); log(f"{name}: start")
    bonus = {p: zb.CIRCLE_WEIGHT // w for p in zb.CELLS}
    found = zb.solve_valid(circles={A: None, X: None}, seed=100 + seed, limit=limit, min_pockets=1, objective=True,
                           avoid=avoid, min_distance=12, log=log, stall=stall, stop_at=99, fix_shade=sh, bonus=bonus, min_groups=groups)
    if found is None:
        log(f"{name}: no grid within {limit}s"); break
    sol, shade = found; circ = zb.circle_candidates(sol, shade)
    zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
    avoid.append(dict(shade))
    log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)}, r9c9={sol[R99]} ({time.time()-t:.0f}s)")
log(f"{xn} DONE")
