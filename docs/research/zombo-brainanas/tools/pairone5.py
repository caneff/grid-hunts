"""One box-9 circle, five brainanas, maximize circles + chocolate.
For each box-9 cell (r8c8 excluded) x shading I/U: fix that cell's shading, open a circle
on it, require >= 5 uninfected groups, maximize circles (10k each) plus chocolate
(CIRCLE_WEIGHT//3 per infected cell anywhere). usage: pairone5.py shard nshards [limit] [stall]
-> hunt/pairone5/full_<cell>_<I|U>.json"""
import sys, time, os, glob, json
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/pairone5/"; os.makedirs(OUT, exist_ok=True)
FOUND = "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research/zombo-brainanas/found/*.json"
shard, n = int(sys.argv[1]), int(sys.argv[2])
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 400
stall = int(sys.argv[4]) if len(sys.argv) > 4 else 90
BONUS = {p: zb.CIRCLE_WEIGHT // 3 for p in zb.CELLS}  # chocolate everywhere
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
cases = [(f"r{r+1}c{c+1}_{k}", (r, c), {(r, c): int(k == "I")})
         for r in range(6, 9) for c in range(6, 9) if (r, c) != (7, 7) for k in "IU"]
def seen():
    g = {}
    for f in glob.glob(FOUND):
        d = json.load(open(f)); g["".join(d["infected"])] = {p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}
    return list(g.values())
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
for i, (name, a, sh) in enumerate(cases):
    if i % n != shard: continue
    if os.path.exists(OUT + f"full_{name}.json"): continue
    t = time.time(); log(f"{name}: start")
    found = zb.solve_valid(circles={a: None}, seed=i, limit=limit, min_pockets=1, min_groups=5, objective=True,
                           avoid=seen(), min_distance=12, log=log, stall=stall, stop_at=99, fix_shade=sh, bonus=BONUS)
    if found is None:
        log(f"{name}: no grid within {limit}s"); continue
    sol, shade = found; circ = zb.circle_candidates(sol, shade)
    zb.dump(OUT + f"full_{name}.json", sol, shade, dict(sol), circ)
    log(f"{name}: {len(circ)} circles, {sum(shade.values())} chocolate, {len(zb.uninfected_groups(shade))} uninfected groups {zb.uninfected_groups(shade)} ({time.time()-t:.0f}s)")
log(f"SHARD {shard} DONE")
