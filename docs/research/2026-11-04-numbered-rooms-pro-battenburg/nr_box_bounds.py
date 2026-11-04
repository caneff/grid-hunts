"""SCRATCH: the most target cells one box can hold, by CP-SAT.

The D4 symmetries of the board keep the rule, so the corner box r1-3 c1-3, the
edge box r1-3 c4-6 and the centre box r4-6 c4-6 cover all nine. Each grid is
re-read by the solver-free reader. One worker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, show, targets
from sudoku_kit.cpsat import solver

LIMIT = 90.0
BOXES = {"corner": (0, 0), "edge": (0, 3), "centre": (3, 3)}


def main():
    for name, (br, bc) in BOXES.items():
        cells = [(br + r, bc + c) for r in range(3) for c in range(3)]
        m, x, _, t = build()
        m.Maximize(sum(t[cell] for cell in cells))
        s = solver(LIMIT)
        status = s.StatusName(s.Solve(m))
        grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
        count = len(targets(grid) & set(cells))
        assert is_sudoku(grid) and count == round(s.ObjectiveValue())
        print(name, status, "value", count, "bound", s.BestObjectiveBound())
        print(show(grid), flush=True)


if __name__ == "__main__":
    main()
