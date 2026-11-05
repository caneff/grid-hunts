"""SCRATCH: fewer marks that fix all 36 targets from the marks alone, with no digits.

The climb of nr_t36_fewer.py scored by nr_t36_pure.patterns: a hit needs exactly one
yes/no pattern under the marks, the negative rule and 1 to 4 targets per line, with a
grid behind it. Each hit lowers the mark limit. It finds upper bounds, never a minimum.
One worker.

Usage: nr_t36_pure_fewer.py SECONDS SEED START_LIMIT OUT
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr_full_targets_edges import BORDER
from nr_t36_climb import read_targets
from nr_t36_fewer import sample
from nr_t36_pure import fill, patterns

STUCK = 300


def main(seconds, seed, limit, out):
    rng = random.Random(seed)
    end = time.time() + seconds
    evals = 0
    best = None
    log = open(out, "a")

    def write(kind, **fields):
        log.write(json.dumps({"kind": kind, "evals": evals, "limit": limit, "t": round(seconds - (end - time.time())), **fields}) + "\n")
        log.flush()

    while time.time() < end:
        border = sample(rng.randrange(1 << 30), limit, {})
        if border is None:
            write("no_sample")
            continue
        cur = patterns(read_targets(border)[1])[0]
        stuck = 0
        while time.time() < end and stuck < STUCK:
            keep = rng.uniform(0.4, 0.9)
            pinned = {k: d for k, d in zip(BORDER, border, strict=True) if rng.random() < keep}
            cand = sample(rng.randrange(1 << 30), limit, pinned)
            stuck += 1
            if cand is None or cand == border:
                continue
            evals += 1
            _, board = read_targets(cand)
            n, pattern, opened, complete = patterns(board)
            if n > cur:
                continue
            if n < cur:
                stuck = 0
            border, cur = cand, n
            if best is None or n < best:
                best = n
                write("best", patterns=n, complete=complete, open=opened, marks=len(board))
            if n == 1 and complete and len(pattern) == 36:
                grid = fill(board, cand, pattern)
                if grid is None:
                    write("no_fill", marks=len(board))
                    continue
                write("HIT", count=len(board), marks=sorted(board), grid=" ".join("".join(map(str, row)) for row in grid))
                limit = len(board) - 1
                best = None
                break
    write("done")


if __name__ == "__main__":
    main(float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
