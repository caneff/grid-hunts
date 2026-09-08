"""Circles r9c7 r8c9 r6c8, one forced white dot, shading free: is a 4-pocket grid feasible? usage: pocket4.py r6c5 r7c5"""
import sys, re
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
zb.WORKERS = 2; zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B, C = (8, 6), (7, 8), (5, 7)
cell = lambda s: tuple(int(v) - 1 for v in re.findall(r"\d", s))
P, Q = cell(sys.argv[1]), cell(sys.argv[2]); label = sys.argv[1] + "-" + sys.argv[2]
_build = zb.build
def build(*a, **k):
    m, x, inf = _build(*a, **k); d = m.NewBoolVar("wd")
    m.Add(x[P] - x[Q] == 1).OnlyEnforceIf(d); m.Add(x[Q] - x[P] == 1).OnlyEnforceIf(d.Not())
    return m, x, inf
zb.build = build
try:
    r = zb.solve_valid(circles={A: None, B: None, C: None}, seed=1, limit=300, min_pockets=1, fix_shade={P: 0, Q: 0}, min_groups=4)
    v = "4POCKET" if r else "NO4"
    if r: v += f" kind={'I' if r[1][A] else 'U'}{'I' if r[1][B] else 'U'} groups={zb.uninfected_groups(r[1])}"
except TimeoutError: v = "UNKNOWN"
print("RESULT", label, v)
