"""SCRATCH: fewer marks that still fix all 36 targets. Negative rule on, no givens.

Same search as nr_t36_climb.py with an upper limit on marks instead of a lower one. Each
proven hit lowers the limit to one below its mark count. Every hit is proven on the full
model by nr_t36_climb.prove. A sample of the space: it finds upper bounds, never a
minimum. One worker. Logs to OUT.

Usage: nr_t36_fewer.py SECONDS SEED START_LIMIT OUT
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr import WINDOWS
from nr_full_targets_edges import BORDER, model
from nr_t36_climb import prove, read_targets, score
from sudoku_kit.cpsat import SOLVED, solver

STUCK = 200


def sample(seed, max_marks, pinned):
    m, b = model(None)
    t = m.target_vars
    m.Add(sum(t.values()) == 36)
    windows = []
    for r, c in WINDOWS:
        one = m.NewBoolVar("one")
        two = m.NewBoolVar("two")
        a, f, d, e = t[r, c], t[r, c + 1], t[r + 1, c], t[r + 1, c + 1]
        m.AddBoolAnd([a, e, f.Not(), d.Not()]).OnlyEnforceIf(one)
        m.AddBoolOr([a.Not(), e.Not(), f, d]).OnlyEnforceIf(one.Not())
        m.AddBoolAnd([f, d, a.Not(), e.Not()]).OnlyEnforceIf(two)
        m.AddBoolOr([f.Not(), d.Not(), a, e]).OnlyEnforceIf(two.Not())
        windows += [one, two]
    m.Add(sum(windows) <= max_marks)
    for cell, d in pinned.items():
        m.Add(b[cell, d] == 1)
    s = solver(20.0)
    s.parameters.random_seed = seed
    s.parameters.randomize_search = True
    s.parameters.num_workers = 1
    if s.Solve(m) not in SOLVED:
        return None
    return [next(d for d in range(1, 10) if s.Value(b[cell, d])) for cell in BORDER]


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
        value = score(read_targets(border)[1])
        cur = (value[0], value[1])
        stuck = 0
        while time.time() < end and stuck < STUCK:
            pinned = {cell: d for cell, d in zip(BORDER, border, strict=True) if rng.random() < rng.uniform(0.3, 0.8)}
            cand = sample(rng.randrange(1 << 30), limit, pinned)
            stuck += 1
            if cand is None or cand == border:
                continue
            evals += 1
            hit, board = read_targets(cand)
            assert len(hit) == 36 and len(board) <= limit
            value = score(board)
            if (value[0], value[1]) > cur:
                continue
            if (value[0], value[1]) < cur:
                stuck = 0
            border, cur = cand, (value[0], value[1])
            if best is None or value[0] < best:
                best = value[0]
                write("open", open=value[0], borders=value[1], marks=len(board))
            if value[0] == 0 and value[2]:
                grid = prove(board, cand)
                if grid is None or isinstance(grid, str):
                    write("hit_failed", why=str(grid), marks=len(board))
                    continue
                write("HIT", count=len(board), borders=value[1], marks=sorted(board),
                      grid=" ".join("".join(map(str, row)) for row in grid))
                limit = len(board) - 1
                best = None
                break
    write("done")


if __name__ == "__main__":
    main(float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
