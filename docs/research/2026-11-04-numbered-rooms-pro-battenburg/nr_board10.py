"""SCRATCH: the seventh board with B7=5 added to T7=5.

Negative rule off: feasibility, r5's statuses, his colours in all four polarities. Then
the fewest marks to add for the negative rule, and the smallest sets, capped. Reuses
nr_board9_fix's model, in which only his 12 marks are required. Every grid is re-read
by the reader, including both outside digits. One worker; only OPTIMAL is a proven
minimum.
"""

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nr_board9_fix as F
from nr import is_sudoku, outside
from nr_board9 import BLUE, GREEN, ORANGE, R5_NOT, R5_YES, YELLOW, name, pair
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver

RING = {("T", 6): 5, ("B", 6): 5}
F.RING = RING
R5 = [(cell, 0) for cell in R5_NOT] + [(cell, 1) for cell in R5_YES]


def free(fixed=()):
    m, x, _, _ = F.model(list(fixed))
    s = solver(F.LIMIT)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    if status not in SOLVED:
        return None
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid)
    ring = outside(grid)
    assert all(ring[k] == v for k, v in RING.items())
    return grid


def main():
    print("negative off, givens + marks:", bool(free()), flush=True)
    for cell in R5_NOT + R5_YES:
        yes, no = free([(cell, 1)]), free([(cell, 0)])
        print(" ", name(cell), "target" if yes else "-", "not" if no else "-", flush=True)
    print("negative off, r5 colours:", bool(free(R5)), flush=True)
    good = []
    for po, py in itertools.product((1, 0), repeat=2):
        colours = pair(ORANGE, GREEN, po) + pair(YELLOW, BLUE, py) + R5
        grid = free(colours)
        word = f"orange={'T' if po else 'N'} yellow={'T' if py else 'N'}"
        print(" ", word, "feasible" if grid else "INFEASIBLE", flush=True)
        if grid:
            good.append((word, colours))
            print("   ", " ".join("".join(map(str, row)) for row in grid), flush=True)
    status, size, bound, detail = F.minimum([])
    print("negative on, marks + both 5s:", status, "extra", size, "bound", bound, flush=True)
    if detail:
        found, end = F.smallest_sets([], size)
        print("  smallest sets:", len(found), end, flush=True)
    for word, colours in good:
        status, size, bound, detail = F.minimum(colours)
        print("negative on,", word, "colours held:", status, "extra", size, "bound", bound, flush=True)
        if detail:
            print("  set", " ".join(name(k) for k in sorted(detail[0])), flush=True)


if __name__ == "__main__":
    main()
