"""For a hunt/x9 grid: which of its white dots make r9c7 = 9 impossible? Circles r9c7 + X, r9c7 given 9, one white dot
forced (both uninfected, consecutive), everything else free. usage: x9kill.py full_r8c9_w3_s0.json -> RESULT lines"""
import sys, os, json, re
sys.path.insert(0, "/home/caneff/orca/workspaces/sudokumaker-custom-constraints/tang/docs/research")
import zombo_brainanas_cpsat as zb
Z = os.path.dirname(os.path.abspath(__file__)) + "/"
zb.WORKERS = int(os.environ.get("ZB_WORKERS", 2)); zb.BIG_POCKET_CELLS = frozenset(p for p in zb.CELLS if zb.box(*p) == 9)
f = sys.argv[1]; d = json.load(open(Z + "hunt/x9/" + f))
xn = re.match(r"full_(r\dc\d)_", f).group(1); X = (int(xn[1]) - 1, int(xn[3]) - 1)
A = (8, 6)
sol = {(r, c): int(d["grid"][r][c]) for r in range(9) for c in range(9)}
shade = {(r, c): d["infected"][r][c] == "*" for r in range(9) for c in range(9)}
NEAR = {(r, c) for r in range(3, 9) for c in range(3, 9)}  # rows 4-9, cols 4-9: only dominoes here can touch the block
whites = [(p, q) for p in zb.CELLS for q in zb.nb(p) if q > p and not shade[p] and not shade[q] and abs(sol[p] - sol[q]) == 1 and (p in NEAR or q in NEAR)]
_build = zb.build
cur = [None]
def build(*a, **k):
    m, x, inf = _build(*a, **k); p, q = cur[0]
    m.Add(inf[p] == 0); m.Add(inf[q] == 0); e = m.NewBoolVar("")
    m.Add(x[p] - x[q] == 1).OnlyEnforceIf(e); m.Add(x[q] - x[p] == 1).OnlyEnforceIf(e.Not())
    return m, x, inf
zb.build = build
killers = []
for p, q in whites:
    cur[0] = (p, q)
    try:
        r = zb.solve_valid(givens={A: 9}, circles={A: None, X: None}, seed=1, limit=180, min_pockets=1)
        v = "KILLS" if r is None else "no"
    except TimeoutError: v = "UNKNOWN"
    if v == "KILLS": killers.append(f"r{p[0]+1}c{p[1]+1}-r{q[0]+1}c{q[1]+1}")
    print(f"  {f} white r{p[0]+1}c{p[1]+1}-r{q[0]+1}c{q[1]+1}: {v}", flush=True)
print(f"RESULT {f[5:-5]} killers {killers}", flush=True)
