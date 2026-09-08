"""Digit variants of pair99g4 UI_w3_s0: the whole shading fixed, circles open on r9c7 + r9c9, maximize circles,
each solution excluded from the next. usage: pair99digits.py 0 1 [nseeds] [limit] [stall] -> hunt/pair99digits/full_UI_d<seed>.json"""
import sys, time, os, json
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/pair99digits/"; os.makedirs(OUT, exist_ok=True)
nseeds = int(sys.argv[3]) if len(sys.argv) > 3 else 6
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 600
stall = int(sys.argv[5]) if len(sys.argv) > 5 else 90
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B = (8, 6), (8, 8)
src = json.load(open(Z + "hunt/pair99g4/full_UI_w3_s0.json"))
sh = {p: int(src["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}
exclude = [{p: int(src["grid"][p[0]][p[1]]) for p in zb.CELLS}]
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
for seed in range(nseeds):
    name = f"UI_d{seed}"
    if os.path.exists(OUT + f"full_{name}.json"):
        d = json.load(open(OUT + f"full_{name}.json")); exclude.append({p: int(d["grid"][p[0]][p[1]]) for p in zb.CELLS}); continue
    t = time.time(); log(f"{name}: start")
    found = zb.solve_valid(circles={A: None, B: None}, seed=200 + seed, limit=limit, min_pockets=1, objective=True,
                           exclude=list(exclude), log=log, stall=stall, stop_at=99, fix_shade=sh)
    if found is None:
        log(f"{name}: no grid within {limit}s"); continue
    sol, shade = found; circ = zb.circle_candidates(sol, shade)
    zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
    exclude.append(dict(sol))
    log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate ({time.time()-t:.0f}s)")
log("SHARD 0 DONE")
