import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gridenum as G

n_, br, bc, latin = (
    int(sys.argv[1]),
    int(sys.argv[2]),
    int(sys.argv[3]),
    sys.argv[4] == "latin",
)
G.geometry(n_, br, bc)
G.LATIN = latin
NN = n_ * n_
label = f"{n_}x{n_} {'Latin' if latin else f'boxes {br}x{bc}'}"


def collector(g, n):
    class C(cp_model.CpSolverSolutionCallback):
        def __init__(s2):
            super().__init__()
            s2.sh = []

        def on_solution_callback(s2):
            sh = [i for i in range(NN) if s2.value(g[i])]
            s2.sh.append((sh, {i: s2.value(n[i]) for i in sh}))
            if len(s2.sh) >= 500:
                s2.stop_search()

    return C()


res = []
unknown = []
for size in range(2, NN):
    m, g, n = G.build(size, min_distinct=0)
    for d in range(1, n_ + 1):
        has = []
        for i in range(NN):
            e = G._reify_eq(m, n[i], d, f"cc{i}_{d}")
            b = m.new_bool_var(f"ccb{i}_{d}")
            m.add_min_equality(b, [g[i], e])
            has.append(b)
        p = m.new_bool_var(f"ccp{d}")
        m.add_max_equality(p, has)
        m.add(sum(has) == d).only_enforce_if(p)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.enumerate_all_solutions = True
    s.parameters.max_time_in_seconds = 120

    c = collector(g, n)
    st = s.solve(m, c)
    if st not in (cp_model.OPTIMAL, cp_model.INFEASIBLE) or len(c.sh) >= 500:
        unknown.append(size)
    for sh, gv in c.sh:
        k = G.count(gv, 2)
        res.append((size, sh, gv, k))
    if c.sh:
        print(
            f"{label} size {size}: {len(c.sh)} shapes, {sum(1 for sh, gv in c.sh if G.count(gv, 2) >= 1)} with a grid, {sum(1 for sh, gv in c.sh if G.count(gv, 2) == 1)} unique{' (NOT exhausted)' if size in unknown else ''}",
            flush=True,
        )
print(
    f"RESULT {label}: {len(res)} shapes, {sum(1 for t in res if t[3] >= 1)} with a grid, {sum(1 for t in res if t[3] == 1)} unique; not exhausted sizes {unknown}"
)
for size, sh, gv, k in res:
    if k >= 1:
        print("  ", "UNIQUE" if k == 1 else "grids", size, sh, [gv[i] for i in sh])
