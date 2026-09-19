"""Possible shaded cell grids: connected all-visible configurations, uniqueness aside.

    uv run finders/counting_shaded/census.py --seconds 600 --out DIR

A configuration here is a (grid, shape) pair where the grid is a valid sudoku,
the shape is an orthogonally connected set of shaded cells, and every shaded cell's
digit equals its shaded-neighbour count. Nothing about uniqueness -- this is the
population the uniqueness hunt draws from, and the baseline corpus for
validating anything that claims to handle connected shaded cells.

One solve per configuration with a fresh random objective, which is what keeps
consecutive answers apart (solve-then-forbid returns near-identical shapes).
Every hit is re-verified from the stored grid and shape before it is written,
by code that does not share the model: the grid is checked as a sudoku, the
shape as connected by flood fill, and each shaded cell digit against its own count.
"""

import argparse
import json
import random
import time
from collections import Counter
from pathlib import Path

from joint import build
from ortools.sat.python import cp_model
from shapes import BOX, NEIGH, connected, count_solutions


def verify(grid, shape):
    """Independent re-check of one configuration. Returns a reason or None."""
    if len(grid) != 81 or any(d not in range(1, 10) for d in grid):
        return "grid is not 81 digits 1-9"
    for r in range(9):
        if len({grid[r * 9 + c] for c in range(9)}) != 9:
            return f"row {r} repeats"
        if len({grid[c * 9 + r] for c in range(9)}) != 9:
            return f"column {r} repeats"
    for b in range(9):
        if len({grid[i] for i in range(81) if BOX[i] == b}) != 9:
            return f"box {b} repeats"
    if not shape:
        return "empty shape"
    if not connected(set(shape)):
        return "shape is not orthogonally connected"
    for i in shape:
        n = sum(j in set(shape) for j in NEIGH[i])
        if grid[i] != n:
            return f"cell {i}: digit {grid[i]} but {n} shaded cell neighbours"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--solve-seconds", type=float, default=60)
    ap.add_argument("--min-shaded", type=int, default=1)
    ap.add_argument("--max-shaded", type=int, default=26)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument(
        "--prove-optimal",
        action="store_true",
        help="let CP-SAT prove the random objective optimal (slow, buys nothing)",
    )
    ap.add_argument(
        "--all-digits",
        action="store_true",
        help="require all of 1-8 on shaded cells; necessary for a unique puzzle",
    )
    ap.add_argument("--cap", type=int, default=2, help="solution counting cap")
    ap.add_argument(
        "--break-symmetry",
        action="store_true",
        help="keep only the lex-smallest of each shape's 8 images; not with pins",
    )
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    sizes, found, bad, seen = Counter(), 0, 0, set()
    while time.monotonic() - t0 < a.seconds:
        left = min(a.solve_seconds, a.seconds - (time.monotonic() - t0))
        if left <= 1:
            break
        weights = [rng.randint(-100, 100) for _ in range(81)]
        m, v, g = build(
            a.min_shaded,
            a.max_shaded,
            maximize=False,
            weights=weights,
            all_digits=a.all_digits,
            break_symmetry=a.break_symmetry,
        )
        s = cp_model.CpSolver()
        s.parameters.num_workers = a.workers
        s.parameters.random_seed = rng.randrange(1 << 30)
        s.parameters.max_time_in_seconds = left
        if not a.prove_optimal:
            # Any feasible configuration is a valid corpus entry, so the
            # optimality proof is pure waste -- and it is nearly all of the
            # cost. Pinned runs at 24, 25 and 26 each returned at exactly their
            # 300s budget, the signature of a solver finishing the search early
            # and then proving. The random-weight objective still steers which
            # region the search lands in; only the proof is dropped.
            s.parameters.stop_after_first_solution = True
        st = s.solve(m)
        if st == cp_model.INFEASIBLE:
            # A proof, and the only status that is one. Stop and say so rather
            # than looping: no configuration of this size exists at all.
            # Name every restriction in play. Without "--all-digits" in this
            # message, an INFEASIBLE at 25 reads as "no 25-cell configuration
            # exists", flatly contradicting the 25-cell configurations already
            # in the corpus. The claim is only ever about the model as posted.
            limits = [f"{a.min_shaded}-{a.max_shaded} shaded cells", "connected"]
            if a.all_digits:
                limits.append("all digits 1-8 present")
            print(
                "INFEASIBLE: no all-visible configuration exists with "
                + ", ".join(limits),
                flush=True,
            )
            break
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # UNKNOWN is a timeout. Not a proof of anything; try another seed.
            print(f"{s.status_name(st)} after {left:.0f}s, retrying", flush=True)
            continue
        shape = sorted(i for i in range(81) if s.value(g[i]))
        grid = [s.value(x) for x in v]
        why = verify(grid, shape)
        if why:
            bad += 1
            print(f"REJECTED by verifier: {why}", flush=True)
            continue
        found += 1
        sizes[len(shape)] += 1
        gv = {i: sum(j in set(shape) for j in NEIGH[i]) for i in shape}
        nsol = count_solutions(gv, a.cap)
        if nsol == 1:
            print(f"*** UNIQUE *** {len(shape)} shaded cells: {shape}", flush=True)
            print(f"    grid: {grid}", flush=True)
        key = (tuple(shape), tuple(grid))
        if key not in seen:
            seen.add(key)
            with (a.out / "configurations.jsonl").open("a") as fh:
                fh.write(
                    json.dumps(
                        {
                            "shaded": len(shape),
                            "shape": shape,
                            "grid": grid,
                            "solutions": nsol,
                            "digits": sorted(set(gv.values())),
                        }
                    )
                    + "\n"
                )
        (a.out / "summary.json").write_text(
            json.dumps(
                {
                    "seed": a.seed,
                    "found": found,
                    "distinct": len(seen),
                    "rejected": bad,
                    "sizes": dict(sorted(sizes.items())),
                },
                indent=2,
            )
        )
        print(
            f"{found} configs ({len(seen)} distinct), sizes "
            f"{dict(sorted(sizes.items()))}, {time.monotonic() - t0:.0f}s",
            flush=True,
        )
    print(f"done: {found} found, {len(seen)} distinct, {bad} rejected by the verifier")


if __name__ == "__main__":
    main()
