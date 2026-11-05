"""SCRATCH: what repairs Chris's 11-mark board.

Negative off: flip each of r1c4, r1c5, r1c8 to a target, everything else as drawn.
Negative on: each single mark removed or added, on marks alone, and on marks with his
digits and with the flipped colour. One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nr_board12 as B
from nr import WINDOWS, build, is_sudoku, marks
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver


def nm(k):
    return f"r{k[0] + 1}c{k[1] + 1}"


def feasible(board, items=()):
    m, x, _, t = build(board, {})
    for kind, key, v in items:
        if kind == "c":
            m.Add(t[key] == v)
        elif kind == "d":
            m.Add(x[key] == v)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(str(sorted(board)))
    if status not in SOLVED:
        return False
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and marks(grid) == board
    return True


def main():
    for name in ("r1c4", "r1c5", "r1c8"):
        k = B.cell(name)
        items = [("c", k, 1) if i[:2] == ("c", k) else i for i in B.ITEMS]
        print("negative off, flip", name, "to target:", B.holds(items, False), flush=True)
    drop = [nm(k) for k in sorted(B.BOARD) if feasible(B.BOARD - {k})]
    print("negative on, marks only, feasible after removing:", drop, flush=True)
    add = [nm(k) for k in WINDOWS if k not in B.BOARD and feasible(B.BOARD | {k})]
    print("negative on, marks only, feasible after adding:", add, flush=True)
    digits = [i for i in B.ITEMS if i[0] == "d"]
    print("with r1c1 = 9, r1c9 = 1, removing:", [n for n in drop if feasible(B.BOARD - {B.cell(n)}, digits)], flush=True)
    print("with r1c1 = 9, r1c9 = 1, adding:", [n for n in add if feasible(B.BOARD | {B.cell(n)}, digits)], flush=True)


if __name__ == "__main__":
    main()
