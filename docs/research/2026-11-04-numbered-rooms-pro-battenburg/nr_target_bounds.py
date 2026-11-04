"""SCRATCH: the fewest and most target cells a grid can have, by CP-SAT.

Each answer's grid is re-read by the solver-free reader. One worker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, show, targets
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver

LIMIT = 90.0


def extreme(sense):
    m, x, _, t = build()
    total = sum(t.values())
    m.Minimize(total) if sense == "min" else m.Maximize(total)
    s = solver(LIMIT)
    status = s.StatusName(s.Solve(m))
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and len(targets(grid)) == round(s.ObjectiveValue())
    print(sense, status, "value", round(s.ObjectiveValue()), "bound", s.BestObjectiveBound())
    print(show(grid), flush=True)


if __name__ == "__main__":
    extreme("max")
    extreme("min")
