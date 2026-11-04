"""SCRATCH: hill-climb over grids toward fewer outside givens, then none.

The score of a grid is the smallest greedy set of outside givens found in
ORDERS random orders, 99 when a second grid has its marks and all 36 outside
digits. Score 0 means the marks alone leave one grid. Moves keep the grid a
sudoku: a digit swap, a row or column swap inside a band or stack, a band or
stack swap, and a row or column cycle swap inside a band or stack, the one move
that leaves the grid's class under the others.

A hit is any grid at or below the best score so far. Scores are upper bounds.

Usage: nr_climb.py SURVEY_JSONL PROGRESS_JSONL SECONDS [START_COUNT]
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import clue_name, is_sudoku, marks, outside, solve
from nr_greedy import greedy

ORDERS = 2
LIMIT = 20.0


def score(grid, rng):
    mark_set, ring = marks(grid), outside(grid)
    if solve(mark_set, ring, exclude=[grid], limit=LIMIT) is not None:
        return 99, {}
    if solve(mark_set, exclude=[grid], limit=LIMIT) is None:
        return 0, {}
    best = None
    for _ in range(ORDERS):
        held, _late = greedy(grid, mark_set, ring, rng)
        if best is None or len(held) < len(best):
            best = held
    return len(best), best


def transpose(grid):
    return [list(col) for col in zip(*grid)]


def cycle_swap(grid, rng):
    """Swap two rows of one band over the smallest closed set of columns."""
    grid = [row[:] for row in grid]
    band = rng.randrange(3) * 3
    a, b = rng.sample(range(band, band + 3), 2)
    c = rng.randrange(9)
    start = grid[a][c]
    want = grid[b][c]
    columns = [c]
    while want != start:
        c = grid[a].index(want)
        columns.append(c)
        want = grid[b][c]
    for c in columns:
        grid[a][c], grid[b][c] = grid[b][c], grid[a][c]
    return grid


def move(grid, rng):
    kind = rng.choice(["digits", "lines", "blocks", "cycle", "cycle", "cycle"])
    flip = rng.random() < 0.5
    work = transpose(grid) if flip else [row[:] for row in grid]
    if kind == "digits":
        x, y = rng.sample(range(1, 10), 2)
        swap = {x: y, y: x}
        work = [[swap.get(d, d) for d in row] for row in work]
    elif kind == "lines":
        band = rng.randrange(3) * 3
        a, b = rng.sample(range(band, band + 3), 2)
        work[a], work[b] = work[b], work[a]
    elif kind == "blocks":
        a, b = rng.sample(range(3), 2)
        for i in range(3):
            work[a * 3 + i], work[b * 3 + i] = work[b * 3 + i], work[a * 3 + i]
    else:
        work = cycle_swap(work, rng)
    new = transpose(work) if flip else work
    assert is_sudoku(new)
    return new


def main(survey, progress, seconds, start_count=6):
    rows = [json.loads(line) for line in open(survey)]
    starts = sorted(
        (r for r in rows if r["status"] == "separable"),
        key=lambda r: min(r["sizes"]),
    )[:start_count]
    rng = random.Random(20261104)
    began = time.time()
    current = [(min(r["sizes"]), r["grid"]) for r in starts]
    best = min(size for size, _ in current)
    evals = 0
    print("starts", [size for size, _ in current], flush=True)
    with open(progress, "a") as f:
        while time.time() - began < seconds and best > 0:
            for i, (size, grid) in enumerate(current):
                new = move(grid, rng)
                new_size, givens = score(new, rng)
                evals += 1
                if new_size <= size:
                    current[i] = (new_size, new)
                if new_size <= best:
                    if new_size < best:
                        print(
                            f"{time.time() - began:.0f}s evals {evals} best {new_size}",
                            flush=True,
                        )
                    best = new_size
                    row = {
                        "size": new_size,
                        "grid": new,
                        "marks": sorted(marks(new)),
                        "givens": {clue_name(c): v for c, v in givens.items()},
                        "evals": evals,
                    }
                    f.write(json.dumps(row) + "\n")
                    f.flush()
                if best == 0:
                    break
    print(
        f"done: {evals} evals in {time.time() - began:.0f}s, best {best}, "
        f"climbs at {[size for size, _ in current]}",
        flush=True,
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), *map(int, sys.argv[4:]))
