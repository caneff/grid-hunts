"""Can a 6x6 Latin square be cut into 6 connected 6-cell regions, each holding 1-6?
Prints every partition (up to relabelling) with cap."""

import json
import sys
from pathlib import Path

from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gridenum as G

G.geometry(6, 2, 3)
N = 6
NN = 36


def partitions(grid, cap=50):
    m = cp_model.CpModel()
    x = [[m.new_bool_var(f"x{i}_{k}") for k in range(N)] for i in range(NN)]
    for i in range(NN):
        m.add_exactly_one(x[i])
    for k in range(N):
        m.add(sum(x[i][k] for i in range(NN)) == N)
        for d in range(1, N + 1):
            m.add_exactly_one([x[i][k] for i in range(NN) if grid[i] == d])
        G.add_connectivity(m, [x[i][k] for i in range(NN)], N, f"r{k}")
    # relabelling symmetry: region k's first cell precedes region k+1's first cell
    first = [m.new_int_var(0, NN - 1, f"f{k}") for k in range(N)]
    for k in range(N):
        for i in range(NN):
            m.add(first[k] <= i).only_enforce_if(x[i][k])
        m.add_exactly_one(
            [m.new_bool_var(f"isf{k}_{i}") for i in range(NN)]
        )  # placeholder to keep names unique
        # first[k] == min index with x[i][k]: exists i with x[i][k] and first[k]==i
        lits = []
        for i in range(NN):
            b = m.new_bool_var(f"ff{k}_{i}")
            m.add(first[k] == i).only_enforce_if(b)
            m.add_implication(b, x[i][k])
            lits.append(b)
        m.add_bool_or(lits)
    for k in range(N - 1):
        m.add(first[k] < first[k + 1])
    s = cp_model.CpSolver()
    s.parameters.num_workers = 8
    sols = []
    while len(sols) < cap:
        st = s.solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        lab = [next(k for k in range(N) if s.value(x[i][k])) for i in range(NN)]
        sols.append(lab)
        m.add_bool_or([x[i][lab[i]].Not() for i in range(NN)])
    return sols


rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
out = []
for k, row in enumerate(rows):
    sols = partitions(row["grid"])
    print(
        f"grid {k + 1}: {len(sols)} partition(s) into 6 connected regions with 1-6 (cap 50)"
    )
    for lab in sols[:3]:
        for r in range(N):
            print("  " + " ".join("ABCDEF"[lab[r * N + c]] for c in range(N)))
        print()
    out.append({**row, "partitions": sols})
Path(sys.argv[2]).write_text(json.dumps(out))
