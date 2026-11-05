"""SCRATCH: Chris's 10-mark board with no digits or colours, negative rule off.

Marks r2c1 r2c3 r2c5 r2c7 r4c2 r4c6 r6c2 r6c6 r8c2 r8c6. Feasibility on the repo's full
model with a witness re-read by the reader, each cell's target status, and each border
cell's digits. One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, show, targets
from nr_full_targets_edges import BORDER
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

BOARD = frozenset(
    (r - 1, c - 1) for r, c in [(2, 1), (2, 3), (2, 5), (2, 7), (4, 2), (4, 6), (6, 2), (6, 6), (8, 2), (8, 6)]
)


def can(extra=None):
    m, x, b, t = build(None, {})
    for r, c in BOARD:
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        m.Add(a == e)
        m.Add(f == d)
        m.Add(a + f == 1)
    if extra:
        extra(m, b, t)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and BOARD <= marks(grid)
    return grid


def main():
    grid = can()
    print("feasible:", bool(grid))
    print(show(grid))
    print("targets", len(targets(grid)), "marks in witness", len(marks(grid)), flush=True)
    for r in range(9):
        row = ""
        for c in range(9):
            yes = can(lambda m, b, t, r=r, c=c: m.Add(t[r, c] == 1))
            no = can(lambda m, b, t, r=r, c=c: m.Add(t[r, c] == 0))
            row += "X" if yes and not no else "." if no and not yes else "?"
        print(row, flush=True)
    for cell in BORDER:
        allowed = [
            d for d in range(1, 10)
            if can(lambda m, b, t, d=d: m.Add(b[cell[0], cell[1], d] == 1))
        ]
        if len(allowed) < 9:
            print(f"r{cell[0] + 1}c{cell[1] + 1}", "".join(map(str, allowed)), flush=True)


if __name__ == "__main__":
    main()
