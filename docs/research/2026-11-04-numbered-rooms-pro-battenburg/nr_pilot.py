"""SCRATCH: step (a) on random grids, step (b) on a few, marks on and off.

Usage: nr_pilot.py SEED_START SEED_END PROGRESS_FILE
Appends one JSON line per grid; a killed run loses at most the grid under way.
"""

import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import clue_name, marks, min_outside_givens, outside, random_grid, targets


def reader_stats():
    rng = random.Random(1)
    grids = [random_grid(rng) for _ in range(2000)]
    t = [len(targets(g)) for g in grids]
    k = [len(marks(g)) for g in grids]
    print(
        f"reader on 2000 random grids: targets min {min(t)} mean "
        f"{statistics.mean(t):.1f} max {max(t)}; marks min {min(k)} mean "
        f"{statistics.mean(k):.1f} max {max(k)}"
    )


def summary(result):
    out = {"status": result["status"], "rounds": result["rounds"]}
    if result["status"] == "minimum":
        out["size"] = len(result["givens"])
        out["givens"] = [clue_name(c) for c in result["givens"]]
    if result["status"] == "capped":
        out["lower_bound"] = result["lower_bound"]
    return out


def main(start, end, progress):
    reader_stats()
    with open(progress, "a") as f:
        for seed in range(start, end):
            grid = random_grid(random.Random(seed))
            row = {
                "seed": seed,
                "grid": grid,
                "marks": sorted(marks(grid)),
                "targets": len(targets(grid)),
                "outside": {clue_name(c): v for c, v in outside(grid).items()},
            }
            for name, flag in (("on", True), ("off", False)):
                began = time.time()
                try:
                    row[name] = summary(min_outside_givens(grid, use_marks=flag))
                except TimeoutError as e:
                    row[name] = {"status": "timeout", "why": str(e)}
                row[name]["seconds"] = round(time.time() - began, 1)
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(
                seed,
                "marks",
                len(row["marks"]),
                "on",
                {k: row["on"].get(k) for k in ("status", "size", "seconds")},
                "off",
                {k: row["off"].get(k) for k in ("status", "size", "seconds")},
                flush=True,
            )


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
