"""Circles r9c7 + r9c9 (kind = their shading), a black dot on some edge inside box 1 or box 2, at least one circle in
box 6 outside row 6 and one in box 8 outside column 6, >= `groups` pockets, circles + chocolate maximized.
usage: pair99b68.py kind [nseeds] [limit] [stall] [groups] -> hunt/pair99b68/full_<kind>_w<3|6>_s<seed>[_g<groups>].json"""
import sys, time, os, json
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/pair99b68/"; os.makedirs(OUT, exist_ok=True)
kind = sys.argv[1]
nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 4
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 600
stall = int(sys.argv[4]) if len(sys.argv) > 4 else 90
groups = int(sys.argv[5]) if len(sys.argv) > 5 else 4
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B = (8, 6), (8, 8)
sh = {A: int(kind[0] == "I"), B: int(kind[1] == "I")}
DOTBOX = [p for p in zb.CELLS if zb.box(*p) in (1, 2)]
EDGES = [(p, q) for p in DOTBOX for q in ((p[0] + 1, p[1]), (p[0], p[1] + 1)) if q in DOTBOX and zb.box(*p) == zb.box(*q)]
B6 = [p for p in zb.CELLS if zb.box(*p) == 6 and p[0] != 5]  # box 6, not row 6
B8 = [p for p in zb.CELLS if zb.box(*p) == 8 and p[1] != 5]  # box 8, not column 6
_build = zb.build
def build(*a, **k):
    m, x, inf = _build(*a, **k)
    es = []  # black dot inside box 1 or 2: infected cell next to an uninfected cell holding its double
    for p, q in EDGES:
        for i, u in ((p, q), (q, p)):
            e = m.NewBoolVar(""); es.append(e)
            m.AddImplication(e, inf[i]); m.AddImplication(e, inf[u].Not())
            m.Add(x[u] == 2 * x[i]).OnlyEnforceIf(e)
    m.AddBoolOr(es)
    for cells in (B6, B8):  # circle_at[p]: bools that each imply p is a circle, so >= 1 is a sound floor
        m.Add(sum(h for p in cells for h in m.circle_at.get(p, [])) >= 1)
    return m, x, inf
zb.build = build
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
avoid = []
for seed in range(nseeds):
    w = 3 if seed % 2 == 0 else 6
    name = f"{kind}_w{w}_s{seed}" + (f"_g{groups}" if groups > 1 else "")
    if os.path.exists(OUT + f"full_{name}.json"):
        d = json.load(open(OUT + f"full_{name}.json")); avoid.append({p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}); continue
    t = time.time(); log(f"{name}: start")
    bonus = {p: zb.CIRCLE_WEIGHT // w for p in zb.CELLS}
    found = zb.solve_valid(circles={A: None, B: None}, seed=100 + seed, limit=limit, min_pockets=1, objective=True,
                           avoid=avoid, min_distance=12, log=log, stall=stall, stop_at=99, fix_shade=sh, bonus=bonus, min_groups=groups)
    if found is None:
        log(f"{name}: no grid within {limit}s"); break
    sol, shade = found; circ = zb.circle_candidates(sol, shade)
    zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
    avoid.append(dict(shade))
    log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)}, "
        f"b6 {[f'r{r+1}c{c+1}' for r, c in circ if zb.box(r, c) == 6]} b8 {[f'r{r+1}c{c+1}' for r, c in circ if zb.box(r, c) == 8]} ({time.time()-t:.0f}s)")
log(f"{kind} DONE g{groups}")
