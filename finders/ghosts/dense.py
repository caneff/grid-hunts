"""Ghosts, all visible: dense shapes straight from CP-SAT, then a uniqueness check.

    uv run finders/ghosts/dense.py --seconds 300 --seed 1 --out DIR

Uniqueness is monotone in the givens, so many ghosts help. Each round builds
the grid+ghost model (ghost digit = ghost-neighbour count, some ghost holds 8),
maximises the ghost count under a short time limit from random digit hints,
and checks the shape with the bitmask counter (cap 2). A non-unique shape's
second solution Y becomes a cut (some ghost must disagree with Y) and the same
model re-solves; after a hit, or `--rounds` misses, a fresh model with new
hints starts, for diversity. Hits are deduplicated up to the 8 square
symmetries and appended to DIR/examples.jsonl with the grid.
"""

import argparse
import json
import random
import time
from pathlib import Path

from harvest import canonical
from ortools.sat.python import cp_model
from shapes import BOX, NEIGH, count_solutions, givens, has_eight


class Model:
    def __init__(self, rng, min_ghosts):
        self.m = m = cp_model.CpModel()
        self.g = g = [m.new_bool_var(f"g{i}") for i in range(81)]
        self.x = x = [[m.new_bool_var(f"x{i}{d}") for d in range(9)] for i in range(81)]
        for i in range(81):
            m.add_exactly_one(x[i])
        for d in range(9):
            for k in range(9):
                m.add_exactly_one(x[k * 9 + c][d] for c in range(9))
                m.add_exactly_one(x[r * 9 + k][d] for r in range(9))
                m.add_exactly_one(x[i][d] for i in range(81) if BOX[i] == k)
        self.on = []
        for i in range(81):
            digit = sum((d + 1) * x[i][d] for d in range(9))
            m.add(sum(g[j] for j in NEIGH[i]) == digit).only_enforce_if(g[i])
            row = []
            for d in range(9):
                v = m.new_bool_var(f"on{i}{d}")
                m.add_implication(v, g[i])
                m.add_implication(v, x[i][d])
                m.add_bool_or([v, g[i].Not(), x[i][d].Not()])
                row.append(v)
            self.on.append(row)
        m.add_bool_or([self.on[i][7] for i in range(81)])
        m.add(sum(g) >= min_ghosts)
        m.maximize(sum(g))
        for i in range(81):
            m.add_hint(x[i][rng.randrange(9)], True)

    def cut(self, Y):
        self.m.add_bool_or(
            [self.on[i][d] for i in range(81) for d in range(9) if d != Y[i] - 1]
        )

    def solve(self, rng, limit):
        s = cp_model.CpSolver()
        s.parameters.num_workers = 1
        s.parameters.random_seed = rng.randrange(1 << 30)
        s.parameters.max_time_in_seconds = limit
        st = s.solve(self.m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None, None
        shape = {i for i in range(81) if s.value(self.g[i])}
        grid = [
            next(d + 1 for d in range(9) if s.value(self.x[i][d])) for i in range(81)
        ]
        return shape, grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=300)
    ap.add_argument("--solve-seconds", type=float, default=10)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--min-ghosts", type=int, default=26)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    seen = set()
    solves = hits = 0
    while time.monotonic() - t0 < a.seconds:
        model = Model(rng, a.min_ghosts)
        for _ in range(a.rounds):
            limit = min(a.solve_seconds, a.seconds - (time.monotonic() - t0))
            if limit <= 0.5:
                break
            shape, grid = model.solve(rng, limit)
            solves += 1
            if shape is None:
                print(f"solve {solves}: no shape", flush=True)
                break
            g = givens(shape)
            assert has_eight(g), "model shape without an admissible 8"
            sols = []
            n = count_solutions(g, 2, None, sols)
            if n == 1:
                assert sols[0] == grid
                key = canonical(shape)
                new = key not in seen
                if new:
                    seen.add(key)
                    hits += 1
                    with (a.out / "examples.jsonl").open("a") as out:
                        out.write(
                            json.dumps(
                                {
                                    "seed": a.seed,
                                    "ghosts": len(shape),
                                    "shape": sorted(shape),
                                    "solution": grid,
                                }
                            )
                            + "\n"
                        )
                print(
                    f"solve {solves}: UNIQUE {len(shape)} ghosts{'' if new else ' (dup)'}; "
                    f"hits {hits} t={time.monotonic() - t0:.0f}s",
                    flush=True,
                )
                break
            Y = next(s for s in sols if s != grid)
            model.cut(Y)
            print(
                f"solve {solves}: {len(shape)} ghosts, not unique "
                f"(diff {sum(p != q for p, q in zip(Y, grid, strict=True))}) t={time.monotonic() - t0:.0f}s",
                flush=True,
            )
    print(
        f"done solves={solves} hits={hits} t={time.monotonic() - t0:.0f}s", flush=True
    )


if __name__ == "__main__":
    main()
