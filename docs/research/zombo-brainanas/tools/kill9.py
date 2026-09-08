"""Can r9c7 be 9 with circles r9c7 r8c9 r6c8 and a forced white dot on the given edge? Shading free.
usage: kill9.py none | r6c5 r7c5"""
import sys, re
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
zb.WORKERS = 2; zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
A, B, C = (8, 6), (7, 8), (5, 7)
sh = {}
label = "none"
if sys.argv[1] != "none":
    cell = lambda s: tuple(int(v) - 1 for v in re.findall(r"\d", s))
    P, Q = cell(sys.argv[1]), cell(sys.argv[2]); label = sys.argv[1] + "-" + sys.argv[2]
    sh = {P: 0, Q: 0}
    _build = zb.build
    def build(*a, **k):
        m, x, inf = _build(*a, **k); d = m.NewBoolVar("wd")
        m.Add(x[P] - x[Q] == 1).OnlyEnforceIf(d); m.Add(x[Q] - x[P] == 1).OnlyEnforceIf(d.Not())
        return m, x, inf
    zb.build = build
try:
    r = zb.solve_valid(givens={A: 9}, circles={A: None, B: None, C: None}, seed=1, limit=300, min_pockets=1, fix_shade=sh)
    v = "9 POSSIBLE" if r else "9 KILLED"
except TimeoutError: v = "UNKNOWN"
print("RESULT", label, v)
if r: print(zb.show(*r)); print("groups", zb.uninfected_groups(r[1]))
