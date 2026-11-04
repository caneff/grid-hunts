"""SCRATCH: the proven fewest outside givens for a fixed grid, and its marks-alone count.

Uniqueness only improves as givens are added, so if no set of size K works then
no smaller set works. For K = size - 1 this walks every K-subset of the 36
outside cells. A subset that misses a known difference set cannot work and costs
no solve; any other is solved, and a second grid adds a new difference set.

Also counts grids with the same marks and no givens, capped at COUNT_CAP.

Usage: nr_exact.py HITS_JSONL PROGRESS_JSONL
"""

import itertools
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import CLUES, _shrunk_difference, clue_name, marks, outside, solve

COUNT_CAP = 200
LIMIT = 60.0


def marks_alone_count(grid):
    mark_set = marks(grid)
    found = []
    while len(found) < COUNT_CAP:
        other = solve(mark_set, exclude=[grid, *found], limit=LIMIT)
        if other is None:
            return len(found) + 1, False
        found.append(other)
    return COUNT_CAP + 1, True


def smallest_set_of_size(grid, k):
    """A k-subset leaving only `grid`, or None, proven over all k-subsets."""
    mark_set, ring = marks(grid), outside(grid)
    index = {clue: 1 << i for i, clue in enumerate(CLUES)}
    pool = []
    solves = 0
    for subset in itertools.combinations(CLUES, k):
        mask = sum(index[c] for c in subset)
        if any(not (mask & s) for s in pool):
            continue
        held = {c: ring[c] for c in subset}
        solves += 1
        alt = solve(mark_set, held, exclude=[grid], limit=LIMIT)
        if alt is None:
            return subset, solves, len(pool)
        diff = _shrunk_difference(grid, alt, mark_set, ring, held, LIMIT)
        pool.append(sum(index[c] for c in diff))
        pool.sort(key=lambda s: s.bit_count())
    return None, solves, len(pool)


def main(hits, progress):
    seen = set()
    with open(progress, "a") as f:
        for line in open(hits):
            hit = json.loads(line)
            key = str(hit["grid"])
            if key in seen:
                continue
            seen.add(key)
            grid = hit["grid"]
            began = time.time()
            row = {"grid": grid, "marks": len(marks(grid)), "greedy": hit["size"]}
            count, capped = marks_alone_count(grid)
            row["marks_alone_count"] = count
            row["marks_alone_capped"] = capped
            size = hit["size"]
            best = None
            try:
                while size > 0:
                    subset, solves, pool = smallest_set_of_size(grid, size - 1)
                    row.setdefault("searches", []).append(
                        {"k": size - 1, "solves": solves, "pool": pool}
                    )
                    if subset is None:
                        break
                    best = subset
                    size -= 1
                row["minimum"] = size
                if best:
                    ring = outside(grid)
                    row["givens"] = {clue_name(c): ring[c] for c in best}
            except TimeoutError as e:
                row["timeout"] = str(e)
            row["seconds"] = round(time.time() - began, 1)
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(
                {k: row.get(k) for k in row if k not in ("grid",)},
                flush=True,
            )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
