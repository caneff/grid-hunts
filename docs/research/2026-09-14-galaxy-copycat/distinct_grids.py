import json, sys
sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build
from ortools.sat.python import cp_model
from collections import Counter, defaultdict

for i in range(1, 6):
    setup = json.load(open(f".scratch/copycat-rsl/p22/p{i}.json"))
    m, digit, cc, _ = build(setup)
    sols = []
    while len(sols) < 200:
        sv = cp_model.CpSolver(); sv.parameters.num_search_workers = 1; sv.parameters.max_time_in_seconds = 120
        if sv.Solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        g = [[sv.Value(digit[r][c]) for c in range(9)] for r in range(9)]
        k = [[sv.Value(cc[r][c]) for c in range(9)] for r in range(9)]
        sols.append((g, k))
        diff = []
        for r in range(9):
            for c in range(9):
                b = m.NewBoolVar(""); m.Add(digit[r][c] != g[r][c]).OnlyEnforceIf(b); diff.append(b)
                diff.append(cc[r][c].Not() if k[r][c] else cc[r][c])
        m.AddBoolOr(diff)
    n = len(sols)
    grids = {json.dumps(g) for g, _ in sols}
    placements = defaultdict(set)
    for g, k in sols:
        placements[json.dumps(g)].add(tuple(f"r{r+1}c{c+1}" for r in range(9) for c in range(9) if k[r][c]))
    # single given: digit at cell -> number of full solutions
    cnt = Counter((r, c, g[r][c]) for g, _ in sols for r in range(9) for c in range(9))
    open_cells = {(r, c) for g, _ in sols for r in range(9) for c in range(9) if g[r][c] != sols[0][0][r][c]}
    uniq = [f"r{r+1}c{c+1}={d}" for (r, c, d), v in sorted(cnt.items()) if v == 1]
    print(f"p{i}: {n} solutions (digits+placement){' CAP' if n>=200 else ''}, {len(grids)} digit grids; single digit givens giving uniqueness: {len(uniq)}")
    print("   ", " ".join(uniq))
    for g, ps in placements.items():
        if len(ps) > 1:
            common = set.intersection(*map(set, ps))
            print(f"    a grid with {len(ps)} placements; floating copycats:", sorted({c for p in ps for c in p} - common))
