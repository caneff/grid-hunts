"""SCRATCH: is the two-5s board's failure real, and which single removed mark rescues it?

Negative rule off, T7=5 and B7=5. Control: no marks at all must be feasible. Then each
of the 12 marks removed, and the row the shared 5 of c7 lands in for each rescue. Grids
are re-read by the reader. One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nr_board9_fix as F
from nr import is_sudoku, outside
from nr_board9 import BOARD, name
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

RING = {("T", 6): 5, ("B", 6): 5}
F.RING = RING


def free(mark_set):
    F.BOARD = mark_set
    m, x, _, _ = F.model([])
    s = solver(F.LIMIT)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(str(sorted(mark_set)))
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid)
    ring = outside(grid)
    assert all(ring[k] == v for k, v in RING.items())
    assert grid[0][6] + grid[8][6] == 10
    return grid


def main():
    print("no marks:", bool(free(frozenset())), flush=True)
    print("all 12 marks:", bool(free(BOARD)), flush=True)
    for k in sorted(BOARD):
        grid = free(BOARD - {k})
        print("remove", name(k), f"feasible, r1c7={grid[0][6]}" if grid else "INFEASIBLE", flush=True)


if __name__ == "__main__":
    main()
