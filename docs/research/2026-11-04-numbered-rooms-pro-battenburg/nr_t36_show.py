"""SCRATCH: print a grid's targets, outside digits and marks with the solver-free reader.

Usage: nr_t36_show.py "ROW ROW ... ROW"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, is_sudoku, marks, outside, targets


def main(rows):
    grid = [[int(d) for d in row] for row in rows.split()]
    assert is_sudoku(grid)
    hit = targets(grid)
    print("targets", len(hit))
    for r in range(9):
        print("".join(map(str, grid[r])), "".join("X" if (r, c) in hit else "." for c in range(9)))
    assert all(sum((r, c) in hit for c in range(9)) == 4 for r in range(9))
    assert all(sum((r, c) in hit for r in range(9)) == 4 for c in range(9))
    ring = outside(grid)
    for side in "TBLR":
        print(side, " ".join(str(ring[k]) for k in CLUES if k[0] == side))
    found = sorted(marks(grid))
    print("marks", len(found), " ".join(f"r{r + 1}c{c + 1}" for r, c in found))


if __name__ == "__main__":
    main(sys.argv[1])
