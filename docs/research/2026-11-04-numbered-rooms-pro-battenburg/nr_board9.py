"""SCRATCH: Chris's seventh board, read from his picture.

Outside T7=5. Twelve marks at r1, r3, r6, r8 by c1, c3, c5 (top-left naming). r5c1-7
light green (not a target), r5c8-9 pink (target). Two two-way colour pairs: orange and
green on r1-4 c1-6, yellow and blue on r6-9 c1-4. Each pair is tried in both polarities,
negative rule off and on. Also asks whether each part is forced by the givens and marks.
Every grid is re-read by the reader. One worker; a timeout raises.
"""

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import build, is_sudoku, marks, outside, targets
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

RING = {("T", 6): 5}
BOARD = frozenset((r, c) for r in (0, 2, 5, 7) for c in (0, 2, 4))
R5_NOT = [(4, c) for c in range(7)]
R5_YES = [(4, 7), (4, 8)]
# Cells of the first colour of each pair; the rest of the block is the second colour.
ORANGE_ROWS = {0: [1, 2, 5], 1: [0, 3, 4], 2: [0, 3, 4], 3: [1, 2, 5]}
ORANGE = [(r, c) for r, cs in ORANGE_ROWS.items() for c in cs]
GREEN = [(r, c) for r in range(4) for c in range(6) if (r, c) not in ORANGE]
YELLOW_ROWS = {5: [0, 3], 6: [1, 2], 7: [1, 2], 8: [0, 3]}
YELLOW = [(r, c) for r, cs in YELLOW_ROWS.items() for c in cs]
BLUE = [(r, c) for r in range(5, 9) for c in range(4) if (r, c) not in YELLOW]


def name(cell):
    return f"r{cell[0] + 1}c{cell[1] + 1}"


def solve(negative, fixed=(), extra=None):
    m, x, b, t = build(BOARD if negative else None, RING)
    if not negative:
        for r, c in BOARD:
            a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
            m.Add(a == e)
            m.Add(f == d)
            m.Add(a + f == 1)
    for cell, v in fixed:
        m.Add(t[cell] == v)
    if extra:
        extra(m, x, b, t)
    s = solver(120.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid)
    found = marks(grid)
    assert found == BOARD if negative else BOARD <= found
    assert outside(grid)[("T", 6)] == 5
    assert all((cell in targets(grid)) == bool(v) for cell, v in fixed)
    return grid


def pair(first, second, polarity):
    return [(cell, polarity) for cell in first] + [(cell, 1 - polarity) for cell in second]


def word(grid):
    return "feasible" if grid else "INFEASIBLE"


def main():
    r5 = [(cell, 0) for cell in R5_NOT] + [(cell, 1) for cell in R5_YES]
    for negative in (False, True):
        tag = "negative on " if negative else "negative off"
        print(tag, "givens + marks:", word(solve(negative)), flush=True)
        print(tag, "+ r5 colours:", word(solve(negative, r5)), flush=True)
        for cell in R5_NOT + R5_YES:
            yes, no = solve(negative, [(cell, 1)]), solve(negative, [(cell, 0)])
            print(" ", tag, name(cell), "target" if yes else "-", "not" if no else "-", flush=True)
        for po, py in itertools.product((1, 0), repeat=2):
            colours = pair(ORANGE, GREEN, po) + pair(YELLOW, BLUE, py)
            alone = solve(negative, colours)
            full = solve(negative, colours + r5)
            print(
                f"  {tag} orange={'T' if po else 'N'} yellow={'T' if py else 'N'}:",
                "pairs", word(alone), "| pairs + r5", word(full),
                flush=True,
            )
            if full:
                print("   ", " ".join("".join(map(str, row)) for row in full))
        for label, first, second in (("orange/green", ORANGE, GREEN), ("yellow/blue", YELLOW, BLUE)):
            both = [solve(negative, pair(first, second, p)) for p in (1, 0)]
            print(" ", tag, label, "alone:", [word(g) for g in both], flush=True)


if __name__ == "__main__":
    main()
