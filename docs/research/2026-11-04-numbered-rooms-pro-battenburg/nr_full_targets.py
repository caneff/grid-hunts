"""SCRATCH: one grid with 36 target cells, its outside digits and every mark.

Asks CP-SAT for 36 targets with no Battenburg rule, then reads everything back with the
solver-free reader. Fixed seed from the kit's solver. One worker; a timeout raises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, build, clue_name, is_sudoku, marks, outside, show, targets
from sudoku_kit.cpsat import SOLVED, UNKNOWN, solver


def main():
    m, x, _, t = build()
    m.Add(sum(t.values()) == 36)
    s = solver(300.0)
    status = s.Solve(m)
    if status == UNKNOWN:
        raise TimeoutError("no verdict")
    assert status in SOLVED
    grid = [[s.Value(x[r, c]) for c in range(9)] for r in range(9)]
    assert is_sudoku(grid)
    hit = targets(grid)
    assert len(hit) == 36
    for r in range(9):
        assert sum((r, c) in hit for c in range(9)) == 4
        assert sum((c, r) in hit for c in range(9)) == 4
    print(show(grid))
    print("targets")
    for r in range(9):
        print("".join("X" if (r, c) in hit else "." for c in range(9)))
    ring = outside(grid)
    for side in "TBLR":
        print(side, " ".join(str(ring[k]) for k in CLUES if k[0] == side))
    found = sorted(marks(grid))
    print("marks", len(found), " ".join(f"r{r + 1}c{c + 1}" for r, c in found))
    print("outside names", [clue_name(k) for k in CLUES][:2])


if __name__ == "__main__":
    main()
