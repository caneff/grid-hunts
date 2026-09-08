import sys, json, time
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
d = json.load(open(sys.argv[1])); shade = {p: int(d["infected"][p[0]][p[1]] == "*") for p in zb.CELLS}
t = time.time()
r = zb.solve_valid(circles={(6, 7): None, (8, 6): None}, seed=0, limit=120, shade=shade, log=print)
print("full shading fixed:", "hit" if r else "none", f"{time.time()-t:.0f}s")
lines = [l.strip() for l in open(sys.argv[2]) if l.strip()]
sh2 = {(r, c): 1 if ch == "#" else 0 for r, l in enumerate(lines[:9]) for c, ch in enumerate(l) if ch in "#."}
t = time.time()
r = zb.solve_valid(circles={(6, 7): None, (8, 6): None}, seed=0, limit=600, fix_shade=sh2, log=print)
print("template only, no avoid:", "hit" if r else "none", f"{time.time()-t:.0f}s")
