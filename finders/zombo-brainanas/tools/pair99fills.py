"""Every digit fill of the four UI four-pocket shadings (pair99g4 UI_w3_s0 and its three neighbours):
shading fixed, circles open on r9c7 + r9c9, each fill excluded from the next, until INFEASIBLE or a cap.
usage: pair99fills.py [cap] -> hunt/pair99fills/full_<shading>_f<k>.json"""
import sys, time, os, json, glob
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = Z + "hunt/pair99fills/"; os.makedirs(OUT, exist_ok=True)
cap = int(sys.argv[1]) if len(sys.argv) > 1 else 30
zb.WORKERS = int(os.environ.get("ZB_WORKERS", zb.WORKERS))
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B = (8, 6), (8, 8)
srcs = {"s0": Z + "hunt/pair99g4/full_UI_w3_s0.json"} | {f"n{k}": Z + f"hunt/pair99g4near/full_UI_w3_s{k}.json" for k in range(3)}
def log(line): open(OUT + "PROGRESS.md", "a").write(line + "\n")
for tag, f in srcs.items():
    src = json.load(open(f))
    sh = {p: int(src["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}
    exclude = []
    for g in sorted(glob.glob(OUT + f"full_{tag}_f*.json")):
        d = json.load(open(g)); exclude.append({p: int(d["grid"][p[0]][p[1]]) for p in zb.CELLS})
    k = len(exclude)
    while k < cap:
        t = time.time(); log(f"{tag} fill {k}: start")
        try:
            found = zb.solve_valid(circles={A: None, B: None}, seed=k, limit=300, min_pockets=1, exclude=list(exclude), log=log, fix_shade=sh)
        except TimeoutError:
            log(f"{tag}: TIMEOUT at fill {k}"); break
        if found is None:
            log(f"{tag}: exhausted after {k} fills"); break
        sol, shade = found; circ = zb.circle_candidates(sol, shade)
        zb.dump(OUT + f"full_{tag}_f{k:02d}.json", sol, shade, dict(sol), circ)
        exclude.append(dict(sol)); log(f"{tag} fill {k}: {len(circ)} circles ({time.time()-t:.0f}s)"); k += 1
log("ALL DONE")
