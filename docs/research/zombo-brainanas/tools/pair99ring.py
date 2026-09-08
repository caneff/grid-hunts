"""Circles r9c7 + r9c9 (UI) plus the opener kropki: if r9c7 were 9 the 3x3 r7-9 c6-8 is infected and r6c6-r6c9 +
r7c9-r9c9 are a 7-cell green block, so any kropki domino adjacent to that block (a cell in r5c6-r5c9 or r6c5) kills the 9.
At least one such domino carries a white dot (both uninfected, consecutive) or a black dot (one infected, the uninfected
one holds the double). >= `groups` pockets, circles + chocolate maximized.
usage: pair99ring.py [nseeds] [limit] [stall] [groups] -> hunt/pair99ring/full_UI_w<3|6>_s<seed>[_g<groups>].json"""
import sys, time, os, json
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/pair99ring/"; os.makedirs(OUT, exist_ok=True)
nseeds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 600
stall = int(sys.argv[3]) if len(sys.argv) > 3 else 90
groups = int(sys.argv[4]) if len(sys.argv) > 4 else 3
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B = (8, 6), (8, 8)
sh = {A: 0, B: 1}
RING = {(5, 5), (5, 6), (5, 7), (5, 8), (6, 8), (7, 8), (8, 8)}
TOUCH = {(4, 5), (4, 6), (4, 7), (4, 8), (5, 4)}  # r5c6-r5c9, r6c5
DOMS = sorted({tuple(sorted((p, q))) for p in TOUCH for q in zb.nb(p)})
_build = zb.build
def build(*a, **k):
    m, x, inf = _build(*a, **k)
    es = []
    for p, q in DOMS:
        w = m.NewBoolVar(""); es.append(w)  # white
        m.AddImplication(w, inf[p].Not()); m.AddImplication(w, inf[q].Not()); d = m.NewBoolVar("")
        m.Add(x[p] - x[q] == 1).OnlyEnforceIf([w, d]); m.Add(x[q] - x[p] == 1).OnlyEnforceIf([w, d.Not()])
        for i, u in ((p, q), (q, p)):  # black, i infected
            b = m.NewBoolVar(""); es.append(b)
            m.AddImplication(b, inf[i]); m.AddImplication(b, inf[u].Not()); m.Add(x[u] == 2 * x[i]).OnlyEnforceIf(b)
    m.AddBoolOr(es)
    return m, x, inf
zb.build = build
def dots(sol, shade):
    out = []
    for p, q in DOMS:
        if not shade[p] and not shade[q] and abs(sol[p] - sol[q]) == 1: out.append(("white", p, q))
        if shade[p] != shade[q]:
            i, u = (p, q) if shade[p] else (q, p)
            if sol[u] == 2 * sol[i]: out.append(("black", p, q))
    return [f"{t} r{p[0]+1}c{p[1]+1}-r{q[0]+1}c{q[1]+1}" for t, p, q in out]
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
avoid = []
for seed in range(nseeds):
    w = 3 if seed % 2 == 0 else 6
    name = f"UI_w{w}_s{seed}" + (f"_g{groups}" if groups > 1 else "")
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
    log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)}, opener dots {dots(sol, shade)} ({time.time()-t:.0f}s)")
log(f"DONE g{groups}")
