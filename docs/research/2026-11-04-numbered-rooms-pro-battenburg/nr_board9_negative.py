"""SCRATCH: why the seventh board fails under the negative rule.

Negative rule on throughout. Tries the marks without T7=5, the marks with each one
removed, with each single extra mark, and whether the free-window colour pattern is
what the negative rule forces on the mark block. Every grid is re-read by the reader.
One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS, build, is_sudoku, marks
from nr_board9 import BOARD, RING
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver


def feasible(mark_set, ring):
    m, x, _, _ = build(mark_set, ring)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(str(sorted(mark_set)))
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid) and marks(grid) == mark_set
    return grid


def name(k):
    return f"r{k[0] + 1}c{k[1] + 1}"


def main():
    print("marks, no outside digit:", bool(feasible(BOARD, {})), flush=True)
    print("marks + T7=5:", bool(feasible(BOARD, RING)), flush=True)
    for label, ring in (("with T7=5", RING), ("without T7=5", {})):
        drop = [name(k) for k in sorted(BOARD) if feasible(BOARD - {k}, ring)]
        print(label, "feasible after removing one mark:", drop, flush=True)
        add = [name(k) for k in WINDOWS if k not in BOARD and feasible(BOARD | {k}, ring)]
        print(label, "feasible after adding one mark:", add, flush=True)


if __name__ == "__main__":
    main()
