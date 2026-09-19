"""counting shaded, connected: search the shape inside a fixed solved grid. BROKEN SAMPLER.

    uv run finders/counting_shaded/gridfirst.py --seconds 300 --min-shaded 20

DO NOT TRUST THIS FILE'S NUMBERS. `random_grid()` below builds grids by
relabelling, moving rows within bands, swapping bands and stacks and
transposing one BASE grid. Those are exactly the sudoku-preserving symmetries,
so every grid it returns is isomorphic to BASE -- it samples one equivalence
class out of 5.47 billion, not the space. The shaded-count constraint is not
invariant under those symmetries, so results vary just enough to look like
sampling.

It is kept as a recorded dead end. Its reported ceiling of 9 shaded cells over 38,064
"random" grids is an artefact; `joint.py --maximize` proves the true ceiling is
26, confirmed by a second encoding in `recheck_ceiling.py`. Full account:
`docs/research/2026-09-16-counting-shaded-connected-decision-log.md`, entries 3 and 4.
Use `joint.py` or `census.py`, which hold the grid as a variable instead.

The shape-only model (connected.py) keeps returning connected shapes whose
givens no sudoku grid completes -- admissible but 0 solutions. This flips it:
fix a solved grid first, then a shaded cell set S only has to satisfy

    grid[i] == |NEIGH[i] & S|   for every i in S

with S orthogonally connected. Admissibility is then free (the grid is a valid
sudoku, so two shaded cells in a house cannot show the same digit), and every hit is
solvable by construction -- the grid is a witness. Uniqueness is the only thing
left to check, with the bounded counter.

Grids come from a base grid under relabelling, within-band row moves, band and
stack swaps and transposition, which is cheap and diverse enough to prototype.
"""

import argparse
import json
import random
import time
from pathlib import Path

from ortools.sat.python import cp_model
from shapes import NEIGH, ORTH, count_solutions, givens

BASE = [(3 * (r % 3) + r // 3 + c) % 9 + 1 for r in range(9) for c in range(9)]


def random_grid(rng):
    """A solved grid: relabel, shuffle rows in bands, swap bands/stacks, transpose."""
    rows = list(range(9))
    bands = [rows[0:3], rows[3:6], rows[6:9]]
    for b in bands:
        rng.shuffle(b)
    rng.shuffle(bands)
    rows = [r for b in bands for r in b]
    cols = list(range(9))
    stacks = [cols[0:3], cols[3:6], cols[6:9]]
    for s in stacks:
        rng.shuffle(s)
    rng.shuffle(stacks)
    cols = [c for s in stacks for c in s]
    label = list(range(1, 10))
    rng.shuffle(label)
    grid = [label[BASE[rows[r] * 9 + cols[c]] - 1] for r in range(9) for c in range(9)]
    if rng.random() < 0.5:
        grid = [grid[c * 9 + r] for r in range(9) for c in range(9)]
    return grid


def add_flow_connectivity(m, g):
    """One root shaded cell supplies a unit of flow to every other shaded cell."""
    root = [m.new_bool_var(f"r{i}") for i in range(81)]
    m.add_exactly_one(root)
    arcs = {}
    for i in range(81):
        m.add_implication(root[i], g[i])
        for j in ORTH[i]:
            f = m.new_int_var(0, 81, f"f{i}_{j}")
            m.add(f <= 81 * g[i])
            m.add(f <= 81 * g[j])
            arcs[i, j] = f
    for i in range(81):
        supply = m.new_int_var(0, 81, f"s{i}")
        m.add(supply <= 81 * root[i])
        m.add(
            sum(arcs[j, i] for j in ORTH[i]) + supply
            == sum(arcs[i, j] for j in ORTH[i]) + g[i]
        )


def shapes_for_grid(grid, min_shaded, max_shaded, seconds, workers, limit):
    """Connected shaded cell sets this grid describes, newest-first, up to `limit`."""
    m = cp_model.CpModel()
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    for i in range(81):
        m.add(sum(g[j] for j in NEIGH[i]) == grid[i]).only_enforce_if(g[i])
    m.add(sum(g) >= min_shaded)
    m.add(sum(g) <= max_shaded)
    add_flow_connectivity(m, g)
    s = cp_model.CpSolver()
    s.parameters.num_workers = workers
    out = []
    start = time.monotonic()
    while len(out) < limit:
        left = seconds - (time.monotonic() - start)
        if left <= 0.5:
            break
        s.parameters.max_time_in_seconds = left
        if s.solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        shape = {i for i in range(81) if s.value(g[i])}
        out.append(shape)
        m.add_bool_or(
            [g[i].Not() for i in shape] + [g[i] for i in range(81) if i not in shape]
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=300)
    ap.add_argument("--grid-seconds", type=float, default=20)
    ap.add_argument("--min-shaded", type=int, default=18)
    ap.add_argument("--max-shaded", type=int, default=40)
    ap.add_argument("--per-grid", type=int, default=5)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    grids = shaped = unique = 0
    hits = []
    while time.monotonic() - t0 < a.seconds:
        grid = random_grid(rng)
        grids += 1
        left = min(a.grid_seconds, a.seconds - (time.monotonic() - t0))
        found = shapes_for_grid(
            grid, a.min_shaded, a.max_shaded, left, a.workers, a.per_grid
        )
        shaped += len(found)
        for shape in found:
            gv = givens(shape)
            if gv is None:
                print(f"BUG: grid-first shape not admissible: {sorted(shape)}")
                continue
            n = count_solutions(gv, 2)
            if n == 1:
                unique += 1
                hits.append(
                    {"shaded": len(shape), "shape": sorted(shape), "grid": grid}
                )
                print(f"UNIQUE {len(shape)} shaded cells: {sorted(shape)}")
                if a.out:
                    with a.out.open("a") as fh:
                        fh.write(json.dumps(hits[-1]) + "\n")
        print(
            f"grids {grids} shapes {shaped} unique {unique} "
            f"({time.monotonic() - t0:.0f}s)",
            flush=True,
        )


if __name__ == "__main__":
    main()
