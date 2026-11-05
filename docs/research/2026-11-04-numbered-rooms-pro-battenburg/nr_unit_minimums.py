"""SCRATCH: the fewest target cells each row, column and box can hold, by CP-SAT.

The D4 symmetries of the board keep the rule, so rows 1 to 5 cover all 18 lines, and
the corner box r1-3 c1-3, the edge box r1-3 c4-6 and the centre box r4-6 c4-6 cover
all nine boxes. Each answer's grid is re-read by the solver-free reader. One worker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, show, targets
from sudoku_kit.cpsat import solver

LIMIT = 120.0
UNITS = {f"r{i + 1}": [(i, c) for c in range(9)] for i in range(5)}
for name, (br, bc) in {"corner box": (0, 0), "edge box": (0, 3), "centre box": (3, 3)}.items():
    UNITS[name] = [(br + r, bc + c) for r in range(3) for c in range(3)]


def main():
    for name, cells in UNITS.items():
        m, x, _, t = build()
        m.Minimize(sum(t[cell] for cell in cells))
        s = solver(LIMIT)
        status = s.StatusName(s.Solve(m))
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        count = len(targets(grid) & set(cells))
        assert is_sudoku(grid) and count == round(s.ObjectiveValue())
        print(name, status, "value", count, "bound", s.BestObjectiveBound())
        print(show(grid), flush=True)


if __name__ == "__main__":
    main()
