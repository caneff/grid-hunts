"""White-dot feasibility sweep: circles r6c8+r9c7+r9c9, kind fixed, one edge forced white (both uninfected, consecutive).
usage: tri68sweep.py kind r1 c1 r2 c2 (0-based)"""
import sys, os
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
kind = sys.argv[1]; P, Q = (int(sys.argv[2]), int(sys.argv[3])), (int(sys.argv[4]), int(sys.argv[5]))
zb.WORKERS = 2; zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B, C = (8, 6), (8, 8), (5, 7)
sh = {A: int(kind[0] == "I"), B: int(kind[1] == "I"), P: 0, Q: 0}
_build = zb.build
def build(*a, **k):
    m, x, inf = _build(*a, **k); d = m.NewBoolVar("wd")
    m.Add(x[P] - x[Q] == 1).OnlyEnforceIf(d); m.Add(x[Q] - x[P] == 1).OnlyEnforceIf(d.Not())
    return m, x, inf
zb.build = build
try:
    r = zb.solve_valid(circles={A: None, B: None, C: None}, seed=1, limit=240, min_pockets=1, fix_shade=sh)
    v = "FOUND" if r else "NONE"
except TimeoutError: v = "UNKNOWN"
print(f"RESULT {kind} r{P[0]+1}c{P[1]+1}-r{Q[0]+1}c{Q[1]+1} {v}")
