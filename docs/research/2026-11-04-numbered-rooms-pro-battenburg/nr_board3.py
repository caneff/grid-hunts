"""SCRATCH: Chris's second board with the box 3 mark, r1c8, deleted.

All-marked rule on the remaining 8 marks. Prints which cells are always or never
targets, each cell's digits, how many grids there are (capped), and how his
colours fare. One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, outside, show, solve
from nr_board2 import GREEN, MARKS, PINK, RING, cell
from nr_opening import report
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

BOARD = frozenset(MARKS - {(0, 7)})
CAP = 200


def allowed(name, want):
    m, _, _, t = build(BOARD, RING)
    m.Add(t[cell(name)] == want)
    status = solver(60.0).Solve(m)
    if status == UNKNOWN:
        raise TimeoutError(name)
    return status in SOLVED


def main():
    report("board without r1c8", BOARD, RING)
    found = []
    while len(found) < CAP:
        grid = solve(BOARD, RING, exclude=found, limit=60.0)
        if grid is None:
            break
        assert is_sudoku(grid) and marks(grid) == BOARD
        ring = outside(grid)
        assert all(ring[c] == v for c, v in RING.items())
        found.append(grid)
    capped = " (capped)" if len(found) == CAP else ""
    print(f"grids: {len(found)}{capped}, each re-read by the reader")
    print(show(found[0]))
    colours = [(n, 1) for n in PINK.split()] + [(n, 0) for n in GREEN.split()]
    print("colours refused:", [n for n, w in colours if not allowed(n, w)])


if __name__ == "__main__":
    main()
