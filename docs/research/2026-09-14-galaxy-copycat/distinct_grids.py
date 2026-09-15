import json, sys
sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build
from ortools.sat.python import cp_model
from collections import Counter

for i in range(1, 6):
    setup = json.load(open(f".scratch/copycat-rsl/p22/p{i}.json"))
    m, digit, cc, _ = build(setup)
    grids = []
    while len(grids) < 60:
        sv = cp_model.CpSolver(); sv.parameters.num_search_workers = 1; sv.parameters.max_time_in_seconds = 120
        st = sv.Solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        g = [[sv.Value(digit[r][c]) for c in range(9)] for r in range(9)]
        grids.append(g)
        # forbid this digit grid
        diff = []
        for r in range(9):
            for c in range(9):
                b = m.NewBoolVar(""); m.Add(digit[r][c] != g[r][c]).OnlyEnforceIf(b); diff.append(b)
        m.AddBoolOr(diff)
    n = len(grids)
    opts = {(r, c): Counter(g[r][c] for g in grids) for r in range(9) for c in range(9)}
    open_cells = [rc for rc, o in opts.items() if len(o) > 1]
    uniq = [(f"r{r+1}c{c+1}={d}") for (r, c) in open_cells for d, k in opts[(r, c)].items() if k == 1]
    print(f"p{i}: {n} distinct digit grids{' (cap)' if n>=60 else ''}, {len(open_cells)} open cells; single givens forcing uniqueness: {len(uniq)}")
    print("   ", " ".join(uniq))
    # describe the grids' differences pairwise from grid 0
    for j, g in enumerate(grids[1:], 1):
        d = [(f"r{r+1}c{c+1}", grids[0][r][c], g[r][c]) for r in range(9) for c in range(9) if g[r][c] != grids[0][r][c]]
        print(f"    grid{j} vs grid0: {len(d)} cells:", " ".join(f"{n}:{a}>{b}" for n, a, b in d))
