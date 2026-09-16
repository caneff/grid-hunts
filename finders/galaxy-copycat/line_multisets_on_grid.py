"""Every value multiset a setup's first line can carry, grouped by distinct count. Usage: uv run line_multisets_on_grid.py setup.json"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from copycat_rsl_solver import build
from ortools.sat.python import cp_model

setup = json.loads(Path(sys.argv[1]).read_text())
m, digit, cc, lines = build(setup)
first = next(iter(lines))
cells = lines[first]
counts = []
for v in range(1, 10):
    eqs = []
    for r, c in cells:
        val = m.NewIntVar(1, 9, "")
        m.Add(val == digit[8 - r][8 - c]).OnlyEnforceIf(cc[r][c])
        m.Add(val == digit[r][c]).OnlyEnforceIf(cc[r][c].Not())
        b = m.NewBoolVar("")
        m.Add(val == v).OnlyEnforceIf(b)
        m.Add(val != v).OnlyEnforceIf(b.Not())
        eqs.append(b)
    n = m.NewIntVar(0, 9, "")
    m.Add(n == sum(eqs))
    counts.append(n)
s = cp_model.CpSolver()
s.parameters.num_search_workers = 1
s.parameters.max_time_in_seconds = 120
found = []
while True:
    if s.Solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        break
    cv = [s.Value(n) for n in counts]
    found.append(cv)
    lits = []
    for n, k in zip(counts, cv, strict=True):
        b = m.NewBoolVar("")
        m.Add(n == k).OnlyEnforceIf(b)
        m.Add(n != k).OnlyEnforceIf(b.Not())
        lits.append(b.Not())
    m.AddBoolOr(lits)
msets = sorted(tuple(v for v in range(1, 10) for _ in range(cv[v - 1])) for cv in found)
print(len(msets), "multisets on", first)
by = {}
for ms in msets:
    by.setdefault(len(set(ms)), []).append(ms)
for d in sorted(by):
    print(f"\n{d} distinct ({len(by[d])}):")
    for ms in by[d]:
        print("  ", "".join(map(str, ms)), "sum", sum(ms) // 2)
