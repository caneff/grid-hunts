"""The 4x4 answer key (spec #66): every 4x4 Doppelganger grid with its 16
ranks, by brute force and with no solver, for the tests.

`grids()` lists every grid of digits 0..4 whose rows, columns and 2x2 boxes
each hold four different digits, a search row by row, and keeps those the
rule reader (`rules.py`) finds no broken rule in, each as a `rules.Reading`
beside its grid. `classify(clues)` is a board's status by the key:
`infeasible`, `unique` or `not_unique`, with the grids that keep every clue.

    uv run finders/doppelganger_rank/brute.py

prints how many grids there are and how many have two equal numbers.
"""

import sys
from functools import cache
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules

N = 4
BOX = (2, 2)


@cache
def grids():
    rows = [row for row in permutations(range(N + 1), N) if 0 in row]
    found = []

    def extend(grid):
        if len(grid) == N:
            reading = rules.read(grid, BOX)
            if not reading.violations:
                found.append((grid, reading))
            return
        r = len(grid)
        band = grid[r - r % BOX[0] :]
        for row in rows:
            if any(row[c] == above[c] for above in grid for c in range(N)):
                continue
            if any(
                row[c] in above[c - c % BOX[1] : c - c % BOX[1] + BOX[1]]
                for above in band
                for c in range(N)
            ):
                continue
            extend((*grid, row))

    extend(())
    return tuple(found)


def classify(clues):
    """The board's status by the key, and the grids that keep every clue."""
    keep = [grid for grid, reading in grids() if not reading.broken_clues(clues)]
    status = {0: "infeasible", 1: "unique"}.get(len(keep), "not_unique")
    return status, keep


if __name__ == "__main__":
    tied = [g for g, r in grids() if len(set(r.numbers.values())) < 4 * N]
    print(f"{len(grids())} grids, {len(tied)} with two equal numbers")
