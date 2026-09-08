"""As tri3 (circles r9c7 r8c9 r6c8) with a white dot on some edge of r6c6: r6c6 uninfected and at least one
orthogonal neighbour uninfected with a consecutive digit. usage: tri3w66.py kind [nseeds] [limit] [stall] [groups] -> hunt/tri3w66/full_<kind>_w<3|6>_s<seed>.json"""
import sys, time, os, json
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/tri3w66/"; os.makedirs(OUT, exist_ok=True)
kind = sys.argv[1]
nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 600
stall = int(sys.argv[4]) if len(sys.argv) > 4 else 90
groups = int(sys.argv[5]) if len(sys.argv) > 5 else 1
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B, C = (8, 6), (7, 8), (5, 7)  # r9c7, r8c9, r6c8
H = (5, 5)  # r6c6
sh = {A: int(kind[0] == "I"), B: int(kind[1] == "I"), H: 0}
_build = zb.build
def build(*a, **k):
    m, x, inf = _build(*a, **k)
    es = []
    for q in zb.nb(H):
        e = m.NewBoolVar(f"wd{q}"); es.append(e)
        m.AddImplication(e, inf[q].Not())
        d = m.NewBoolVar("")
        m.Add(x[H] - x[q] == 1).OnlyEnforceIf([e, d]); m.Add(x[q] - x[H] == 1).OnlyEnforceIf([e, d.Not()])
    m.AddBoolOr(es)
    return m, x, inf
zb.build = build
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
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
        log(f"{name}: no grid within {limit}s"); break
    sol, shade = found; circ = zb.circle_candidates(sol, shade)
    zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
    avoid.append(dict(shade))
    wd = [q for q in zb.nb(H) if not shade[q] and abs(sol[q] - sol[H]) == 1]
    log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)}, white dots at r6c6: {[f'r{r+1}c{c+1}' for r, c in wd]} ({time.time()-t:.0f}s)")
log(f"{kind} DONE")
