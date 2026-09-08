"""Plant the box-4 and box-5 patient zeros next to box 1 and measure how much
chocolate reaches box 1. usage: plant.py variant seed  -> hunt/plant/
Variants: A-C put the 5 at r4c4 and the 4 at r5c1..r5c3; D-F put the 5 at r5c4
and the 4 at r4c3..r4c1; Z plants nothing. Pair r7c8 infected + r9c7 uninfected
fixed (as ceiling.py) so the objective model fits in memory."""
import sys, time, os, json, re
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
Z = os.path.dirname(os.path.abspath(__file__)) + "/"; OUT = Z + "hunt/plant/"; os.makedirs(OUT, exist_ok=True)
var, seed = sys.argv[1], int(sys.argv[2])
MODE = sys.argv[3] if len(sys.argv) > 3 else "ceil"  # ceil: pair open, no pocket library
PLANTS = {"A": {(3, 3): 5, (4, 0): 4}, "B": {(3, 3): 5, (4, 1): 4}, "C": {(3, 3): 5, (4, 2): 4},
          "D": {(4, 3): 5, (3, 2): 4}, "E": {(4, 3): 5, (3, 1): 4}, "F": {(4, 3): 5, (3, 0): 4}, "Z": {}}
B1 = [p for p in zb.CELLS if zb.box(*p) == 1]
def log(line): open(OUT + "PROGRESS.md", "a").write(f"{var}{seed} {MODE}: {line}\n")
t = time.time(); log("start")
if MODE == "ceil":
    kw = dict(min_pockets=0)
else:  # MODE = r7c8I_r9c7U : fix that pair's shading, both circles open, full pocket library
    a, b = re.findall(r"r(\d)c(\d)([IU])", MODE)
    A, B = (int(a[0]) - 1, int(a[1]) - 1), (int(b[0]) - 1, int(b[1]) - 1)
    kw = dict(circles={A: None, B: None}, fix_shade={A: int(a[2] == "I"), B: int(b[2] == "I")}, min_pockets=1)
found = zb.solve_valid(givens=PLANTS[var], seed=seed, limit=400, objective=True, log=log, stall=120, stop_at=99,
                       bonus={p: 50000 for p in B1}, **kw)
if found is None:
    log("NO GRID"); sys.exit()
sol, sh = found; circ = zb.circle_candidates(sol, sh)
zb.dump(OUT + f"full_{var}{seed}_{MODE}.json", sol, sh, dict(sol), circ)
open(OUT + f"grid_{var}{seed}_{MODE}.txt", "w").write(zb.show(sol, sh, circles=circ) + "\n")
log(f"DONE {len(circ)} circles, {sum(sh.values())} infected, {sum(sh[p] for p in B1)}/9 box-1 infected, "
    f"{sum(sh[p] for p in zb.CELLS if p[0] < 5 and p[1] < 5)}/25 quadrant ({time.time()-t:.0f}s)")
