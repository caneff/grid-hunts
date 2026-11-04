"""SCRATCH: the CP-SAT model against the solver-free reader, with controls.

For each random grid: the model accepts the grid with its own marks and outside
digits, refuses it when one mark is flipped or one outside digit changed, and
each grid the unpinned model returns reads back with the marks it was given.
Rule cases from the sources are pinned by hand first.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import (
    CLUES,
    WINDOWS,
    is_sudoku,
    line_cells,
    marks,
    outside,
    random_grid,
    solve,
    target_of,
)

N = 40


def main():
    # logic-masters 0008WX's example: r6c9 = 6, clue from the east, target r6c4.
    assert line_cells(("R", 5))[5] == (5, 3)
    # gmpuzzles example: r1c4 = 5 from the top, target r5c4.
    assert line_cells(("T", 3))[4] == (4, 3)

    rng = random.Random(20261104)
    for n in range(N):
        grid = random_grid(rng)
        assert is_sudoku(grid)
        mark_set, ring = marks(grid), outside(grid)
        pin = {(r, c): grid[r][c] for r in range(9) for c in range(9)}

        assert solve(mark_set, ring, pin) == grid, "model refused its own grid"

        window = rng.choice(WINDOWS)
        assert solve(mark_set ^ {window}, ring, pin) is None, "flipped mark passed"

        clue = rng.choice(CLUES)
        wrong = dict(ring)
        wrong[clue] = ring[clue] % 9 + 1
        assert solve(mark_set, wrong, pin) is None, "wrong outside digit passed"

        other = solve(mark_set)
        assert is_sudoku(other) and marks(other) == mark_set, "unpinned model drifted"
        some = dict(rng.sample(sorted(ring.items()), 6))
        other = solve(mark_set, some)
        got = outside(other)
        assert all(got[c] == v for c, v in some.items()), "outside digit not held"
        assert target_of(grid, clue) in line_cells(clue)
    print(f"selfcheck passed on {N} random grids, one worker")


if __name__ == "__main__":
    main()
