"""SCRATCH: climb over grids toward an edge that has one completion.

Goal (c) needs a grid fixed by its 32 edge cells. The score is the count of
completions of the edge, by a solver-free backtracking count capped at CAP. A
grid at 1 is then tested for marks-alone uniqueness. A capped count is reported
as capped. Moves are nr_climb's.

Usage: nr_edge_climb.py PROGRESS_JSONL SECONDS RESTARTS
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import marks, random_grid, solve
from nr_climb import move

CAP = 20000
ALL = 0b1111111110


def completions(grid, cap=CAP):
    rows, cols, boxes = [ALL] * 9, [ALL] * 9, [ALL] * 9
    empty = []
    for r in range(9):
        for c in range(9):
            if r in (0, 8) or c in (0, 8):
                bit = 1 << grid[r][c]
                rows[r] &= ~bit
                cols[c] &= ~bit
                boxes[r // 3 * 3 + c // 3] &= ~bit
            else:
                empty.append((r, c, r // 3 * 3 + c // 3))
    count = 0

    def search(todo):
        nonlocal count
        if not todo:
            count += 1
            return
        best_i, best_mask, best_n = -1, 0, 10
        for i, (r, c, b) in enumerate(todo):
            mask = rows[r] & cols[c] & boxes[b]
            n = mask.bit_count()
            if n < best_n:
                best_i, best_mask, best_n = i, mask, n
                if n <= 1:
                    break
        if best_n == 0:
            return
        r, c, b = todo[best_i]
        rest = todo[:best_i] + todo[best_i + 1 :]
        mask = best_mask
        while mask and count <= cap:
            bit = mask & -mask
            mask ^= bit
            rows[r] ^= bit
            cols[c] ^= bit
            boxes[b] ^= bit
            search(rest)
            rows[r] ^= bit
            cols[c] ^= bit
            boxes[b] ^= bit

    search(empty)
    return min(count, cap + 1)


def main(progress, seconds, restarts):
    rng = random.Random(20261105)
    began = time.time()
    best = CAP + 2
    evals = 0
    per_climb = seconds / restarts
    with open(progress, "a") as f:
        for climb in range(restarts):
            grid = random_grid(rng)
            size = completions(grid)
            stop = began + per_climb * (climb + 1)
            while time.time() < stop:
                new = move(grid, rng)
                new_size = completions(new)
                evals += 1
                if new_size <= size:
                    grid, size = new, new_size
                if new_size < best:
                    best = new_size
                    row = {"completions": new_size, "grid": new, "evals": evals}
                    if new_size == 1:
                        alone = solve(marks(new), exclude=[new], limit=60.0)
                        row["marks_alone_unique"] = alone is None
                    f.write(json.dumps(row) + "\n")
                    f.flush()
                    print(f"{time.time() - began:.0f}s evals {evals} best {new_size}", flush=True)
            print(f"climb {climb} ended at {size}", flush=True)
    print(f"done: {evals} evals, best {best} completions (cap {CAP})", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]))
