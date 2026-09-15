"""Min and max number of distinct values across a setup's lines. Usage: uv run distinct_values.py setup.json"""

import json
import sys

sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build
from ortools.sat.python import cp_model

setup = json.load(open(sys.argv[1]))
for sense in ("min", "max"):
    m, digit, cc, lines = build(setup)
    cells = [c for n in lines for c in lines[n]]
    present = []
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
        p = m.NewBoolVar("")
        m.AddBoolOr(eqs).OnlyEnforceIf(p)
        m.AddBoolAnd([e.Not() for e in eqs]).OnlyEnforceIf(p.Not())
        present.append(p)
    (m.Minimize if sense == "min" else m.Maximize)(sum(present))
    s = cp_model.CpSolver()
    s.parameters.num_search_workers = 1
    s.parameters.max_time_in_seconds = 120
    st = s.Solve(m)
    vals = {}
    for n in lines:
        vals[n] = [
            s.Value(digit[8 - r][8 - c]) if s.Value(cc[r][c]) else s.Value(digit[r][c])
            for r, c in lines[n]
        ]
    print(
        f"{sense}: {int(s.ObjectiveValue())} distinct values ({s.StatusName(st)})  "
        + "  ".join(f"{n}={v}" for n, v in vals.items())
    )
