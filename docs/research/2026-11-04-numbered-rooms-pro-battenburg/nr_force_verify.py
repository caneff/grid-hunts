"""SCRATCH: verify that the sampled 20-mark set pins the whole border.

The repo's full model with these marks and the negative rule, with this grid's border
forbidden, must be infeasible. Writes the border for count_fills.c. One worker; a
timeout raises.

Usage: nr_force_verify.py OUT_BORDER
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks
from nr_full_targets_edges import BORDER
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

ROWS = "654792831 281635479 793184256 547963182 928541763 316278594 162357948 835429617 479816325"
GRID = [[int(d) for d in row] for row in ROWS.split()]


def main(out):
    assert is_sudoku(GRID)
    board = marks(GRID)
    print("marks", len(board), " ".join(f"r{r + 1}c{c + 1}" for r, c in sorted(board)))
    m, _, b, _ = build(board, {})
    m.AddBoolOr([b[r, c, GRID[r][c]].Not() for r, c in BORDER])
    s = solver(300.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    print("another border exists:", status in SOLVED)
    Path(out).write_text("".join(str(GRID[r][c]) for r, c in BORDER) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
