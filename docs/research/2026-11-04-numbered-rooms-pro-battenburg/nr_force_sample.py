"""SCRATCH: sample random grids and ask what their exact mark sets force, no givens.

Negative rule on. For each grid, enumerates the borders its marks allow on the
border-only model, to CAP. A capped grid is counted and makes no forcing claim. A digit
every listed border shares is forced, and borders without a completion can only hide
more forcing, so the count is a floor. A sample, not a bound. One worker.

Usage: nr_force_sample.py SECONDS SEED
"""

import collections
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import is_sudoku, marks, random_grid
from nr_full_targets_edges import BORDER, model
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver

CAP = 3000


class Keep(cp_model.CpSolverSolutionCallback):
    def __init__(self, b):
        super().__init__()
        self.b, self.borders = b, []

    def on_solution_callback(self):
        row = [next(d for d in range(1, 10) if self.Value(self.b[cell, d])) for cell in BORDER]
        self.borders.append(row)
        if len(self.borders) >= CAP:
            self.StopSearch()


def main(seconds, seed):
    rng = random.Random(seed)
    end = time.time() + seconds
    total = capped = 0
    tally = collections.Counter()
    best = []
    while time.time() < end:
        grid = random_grid(rng)
        assert is_sudoku(grid)
        board = marks(grid)
        m, b = model(board, True)
        s = solver(20.0)
        s.parameters.enumerate_all_solutions = True
        s.parameters.num_workers = 1
        keep = Keep(b)
        status = s.Solve(m, keep)
        total += 1
        if len(keep.borders) >= CAP or s.StatusName(status) == "UNKNOWN":
            capped += 1
            continue
        known = [grid[r][c] for r, c in BORDER]
        assert known in keep.borders
        forced = {
            f"r{cell[0] + 1}c{cell[1] + 1}": v
            for cell, v in zip(BORDER, known, strict=True)
            if all(row[BORDER.index(cell)] == v for row in keep.borders)
        }
        tally[len(forced)] += 1
        best.append((len(forced), -len(keep.borders), len(board), sorted(board), forced, grid))
    print("grids", total, "capped", capped)
    print("forced digit counts", sorted(tally.items()))
    best.sort(key=lambda item: (item[0], item[1]), reverse=True)
    for n, borders, size, board, forced, grid in best[:8]:
        print(n, "forced | borders", -borders, "| marks", size, " ".join(f"r{r + 1}c{c + 1}" for r, c in board))
        print("  ", forced)
        print("  ", " ".join("".join(map(str, row)) for row in grid))
    sizes = collections.defaultdict(list)
    for n, _, size, *_ in best:
        sizes[size].append(n)
    for size in sorted(sizes):
        v = sizes[size]
        print("marks", size, "grids", len(v), "mean forced", round(sum(v) / len(v), 2), "max", max(v))


if __name__ == "__main__":
    main(float(sys.argv[1]), int(sys.argv[2]))
