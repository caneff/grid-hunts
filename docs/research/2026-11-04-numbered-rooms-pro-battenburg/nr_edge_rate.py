"""SCRATCH: how often do a grid's 32 edge cells alone fix the grid?

A necessary condition for goal (c): the marks read only the edge, so a grid with
a second completion of its edge has a second grid with the same marks.
Counts completions per random grid, capped at CAP. One worker.

Usage: nr_edge_rate.py COUNT
"""

import collections
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import random_grid, solve

CAP = 50


def completions(grid):
    pin = {
        (r, c): grid[r][c]
        for r in range(9)
        for c in range(9)
        if r in (0, 8) or c in (0, 8)
    }
    found = [grid]
    while len(found) <= CAP:
        other = solve(pin=pin, exclude=found, limit=30.0)
        if other is None:
            return len(found)
        found.append(other)
    return CAP + 1


def main(count):
    rng = random.Random(3)
    tally = collections.Counter(completions(random_grid(rng)) for _ in range(count))
    print(f"completions of the edge on {count} random grids, {CAP + 1} means capped:")
    print(sorted(tally.items()))


if __name__ == "__main__":
    main(int(sys.argv[1]))
