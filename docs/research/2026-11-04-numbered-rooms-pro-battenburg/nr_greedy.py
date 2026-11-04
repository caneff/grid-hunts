"""SCRATCH: step (b) survey, an upper bound on outside givens per random grid.

For each seed: is the grid the only one with its marks and all 36 outside
digits (separable)? If so, drop outside givens greedily in several random orders
and keep the smallest set. A solve that reaches its limit keeps the given, so a
timeout can only make a set larger. The sizes are upper bounds, not minimums.

Usage: nr_greedy.py SEED_START SEED_END PROGRESS_FILE [ORDERS]
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, clue_name, marks, outside, random_grid, solve

LIMIT = 20.0


def greedy(grid, mark_set, ring, rng):
    held = dict(ring)
    order = list(CLUES)
    rng.shuffle(order)
    timeouts = 0
    for clue in order:
        trial = {c: v for c, v in held.items() if c != clue}
        try:
            if solve(mark_set, trial, exclude=[grid], limit=LIMIT) is None:
                held = trial
        except TimeoutError:
            timeouts += 1
    return held, timeouts


def survey(seed, orders):
    rng = random.Random(seed)
    grid = random_grid(rng)
    mark_set, ring = marks(grid), outside(grid)
    row = {"seed": seed, "grid": grid, "marks": sorted(mark_set)}
    began = time.time()
    if solve(mark_set, ring, exclude=[grid], limit=LIMIT) is not None:
        row["status"] = "not_separable"
    else:
        row["status"] = "separable"
        best, sizes, timeouts = None, [], 0
        for _ in range(orders):
            held, late = greedy(grid, mark_set, ring, rng)
            sizes.append(len(held))
            timeouts += late
            if best is None or len(held) < len(best):
                best = held
        row["sizes"] = sizes
        row["timeouts"] = timeouts
        row["givens"] = {clue_name(c): v for c, v in best.items()}
    row["seconds"] = round(time.time() - began, 1)
    return row


def main(start, end, progress, orders=3):
    with open(progress, "a") as f:
        for seed in range(start, end):
            row = survey(seed, orders)
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(
                seed,
                len(row["marks"]),
                row["status"],
                row.get("sizes"),
                row.get("timeouts"),
                row["seconds"],
                flush=True,
            )


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], *map(int, sys.argv[4:]))
