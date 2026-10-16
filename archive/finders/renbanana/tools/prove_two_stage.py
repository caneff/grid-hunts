"""Is a circle set unique? Proved in two stages, never a joint search (#402).

A circle marks a cell whose digit equals the size of its own maximal group,
chocolate or banana -- the question `probe_circle_pattern.py --unique` asks
jointly. Solved jointly, the 12 circles of
`candidates-fully-circled/cand_00.json` gave no first solution in 8 minutes;
with the shading fixed, the digit enumeration finishes in under a second. The
shading is the whole cost, so it is searched on its own:

1. Enumerate the shadings the circle set allows, with `renbanana_cpsat`'s
   stage-1 model plus `pin_circle_sizes`.
2. On each survivor, enumerate digit fills with every circle's digit fixed to
   its group size, then cut that shading and ask stage 1 for the next.

Two fills across all survivors: NOT UNIQUE. Stage 1 exhausted, every stage-2
search exhausted, exactly one fill, and that fill passing `renbanana_verify`:
UNIQUE. Any timeout: NOT PROVED, never UNIQUE.

SOUNDNESS CONDITION. Stage 1 must stay a *relaxation*: it may admit a shading
that carries no digit fill, but must never exclude one that does. It holds
today because every stage-1 constraint is either exact (the rectangle lemma,
the banana size cap) or implied by every legal grid (the banana-non-rectangle
cuts each forbid one illegal pattern; the catalogue's dead placements and
circle cells are layer B facts; the fives lemma). Add a constraint that cuts a
fillable shading and an INFEASIBLE from stage 1 stops being a proof -- this
tool would then print UNIQUE for a circle set with a second solution.

    uv run finders/renbanana/tools/prove_two_stage.py --cells r1c6,r1c9,... \
        [--seconds N] [--workers 1]
"""

import argparse
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import renbanana_cpsat as R
import renbanana_verify as rv
from probe_circle_pattern import parse_cells, render


def pin_circle_sizes(model, circled):
    """Stage 1's share of the circles: only the group sizes they imply.

    Digits do not exist at the shading layer, so whether a circled cell's digit
    can equal its size is left to stage 2. What the shading layer can say: a
    circled chocolate cell sits in a maximal rectangle that the #377 catalogue
    says can put the rectangle's area on that very cell, at that box offset.
    Every real solution satisfies that, so the model stays a relaxation. A
    circled banana cell needs nothing new -- the model already caps banana
    groups at 9 cells.
    """
    for x in circled:
        spots = [
            model.spot(a, b, r, c)
            for a, b in R.SHAPES
            for r in range(max(0, x[0] - a + 1), min(x[0], R.N - a) + 1)
            for c in range(max(0, x[1] - b + 1), min(x[1], R.N - b) + 1)
            if (x[0] - r, x[1] - c) in R.circle_cells_at(a, b, r % 3, c % 3)
        ]
        model.m.add_bool_or([model.choc[x].negated(), *spots])


def digit_fills(is_choc, circled, limit, seconds, workers):
    """Up to `limit` digit fills on one fixed shading, each circle reading its
    group size. Returns (exhausted, grids): exhausted means the search proved
    `grids` is every fill there is, so a cap or a timeout is never exhausted.
    """
    m, d, _ = R.digit_model(is_choc)
    size = rv.group_sizes(is_choc)
    for x in circled:
        m.add(d[x] == size[x])
    s = cp.CpSolver()
    s.parameters.num_workers = workers
    deadline = time.monotonic() + seconds
    grids = []
    while len(grids) < limit:
        left = deadline - time.monotonic()
        if left <= 0:
            return False, grids
        s.parameters.max_time_in_seconds = left
        status = s.solve(m)
        if status == cp.INFEASIBLE:
            return True, grids
        if status not in (cp.OPTIMAL, cp.FEASIBLE):
            return False, grids
        grid = {p: s.value(d[p]) for p in R.CELLS}
        grids.append(grid)
        # Block exactly this fill: some cell must differ.
        differs = []
        for p in R.CELLS:
            t = m.new_bool_var("")
            m.add(d[p] != grid[p]).only_enforce_if(t)
            differs.append(t)
        m.add_bool_or(differs)
    return False, grids


def two_stage(next_shading, fills, forbid, circled, log=print):
    """The verdict, from the two stages passed in.

    `next_shading()` returns (status, shading or None) -- None once stage 1 has
    nothing left, with INFEASIBLE meaning exhausted. `fills(shading, limit)`
    returns (exhausted, grids). `forbid(shading)` cuts a handled shading.
    Returns (verdict, solutions, survivors).
    """
    sols, survivors, conclusive = [], 0, True
    while True:
        status, is_choc = next_shading()
        if is_choc is None:
            break
        survivors += 1
        exhausted, grids = fills(is_choc, 2 - len(sols))
        for grid in grids:
            bad = rv.check(grid, is_choc, circled)
            if bad:
                log(f"verification failed on survivor {survivors}:")
                log("  " + "\n  ".join(bad))
                return "NOT PROVED", sols, survivors
            sols.append((grid, is_choc))
        log(f"survivor {survivors}: {len(grids)} fill(s), {len(sols)} total")
        if len(sols) >= 2:
            return "NOT UNIQUE", sols, survivors
        # A timed-out digit search rules out UNIQUE, but a later survivor can
        # still show NOT UNIQUE, so the enumeration goes on.
        conclusive = conclusive and exhausted
        forbid(is_choc)
    if status != cp.INFEASIBLE or not conclusive:
        return "NOT PROVED", sols, survivors
    return ("UNIQUE" if sols else "NO SOLUTION"), sols, survivors


def prove(circled, seconds, workers, log=print):
    """Both stages for real, sharing one wall-clock budget."""
    model = R.Shadings()
    pin_circle_sizes(model, circled)
    deadline = time.monotonic() + seconds

    def left():
        return deadline - time.monotonic()

    def next_shading():
        if left() <= 0:
            return cp.UNKNOWN, None
        status, is_choc, _ = R.legal_shading(model, left(), workers, lambda _: None)
        return status, is_choc

    def fills(is_choc, limit):
        return digit_fills(is_choc, circled, limit, max(left(), 0), workers)

    return two_stage(next_shading, fills, model.forbid_shading, circled, log)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True)
    ap.add_argument("--seconds", type=float, default=1200)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    circled = parse_cells(a.cells)
    start = time.monotonic()
    verdict, sols, survivors = prove(
        circled, a.seconds, a.workers, lambda line: print(line, flush=True)
    )
    for i, (grid, is_choc) in enumerate(sols, 1):
        print(f"solution {i}:")
        print("\n".join(render(grid, is_choc)))
    print(f"verdict: {verdict}")
    print(f"survivors: {survivors}  wall {time.monotonic() - start:.1f}s")


if __name__ == "__main__":
    main()
