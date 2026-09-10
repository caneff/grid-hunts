"""Hunt a grid holding two circled chocolate rectangles, outside the pool.

The pool answer is already recorded and it is narrow: 0 of 70 pool digit-grids
admit two circled rectangles, all proved, 12 seconds (CIRCLED-PAIRS.md). But
the pool is eighteen shading families found by searches that never carried this
constraint, so it says nothing about the space.

This samples the space instead. For a pinned geometry -- one of the 1360
disjoint, non-touching (2x2, 2x3) placements the #377 catalogue allows a circle
on -- it builds a solved sudoku that already carries both rectangles:

- every orthogonal pair inside each rectangle differs by at least 5, because
  every cell of a chocolate rectangle is chocolate and the whisper binds them;
- each rectangle holds its own size on a cell the catalogue permits, so the
  circle is real rather than hoped for;
- and the grid is *steered*: at least `--steer` whisper-legal adjacencies
  overall. That number separates the populations we have measured -- a uniform
  random grid averages 37 and known-legal grids average 49 -- and a uniform
  random grid admits any legal shading about 1 time in 200. Sampling uniformly
  would measure that base rate again instead of the question.

Then it asks the full inverted model for a legal shading with two circled
rectangles in it. A hit is a grid no hunt has ever produced. A miss is not a
proof -- that is stage 2, the joint model -- so the run reports the two apart.

    uv run --with ortools docs/research/renbanana/tools/hunt_circled_pair.py \
        --procs 20 --seeds 3 --steer 46 --out docs/research/renbanana/pair-hunt
"""

import argparse
import json
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_circled_pairs as ccp
import probe_inverted as pi
import renbanana_cpsat as rc
import renbanana_verify as rv

N = 9
CELLS = [(r, c) for r in range(N) for c in range(N)]


def grid_carrying(pair, seed, steer, seconds):
    """A solved sudoku that already holds both circled rectangles."""
    rng = random.Random(seed)
    m = cp.CpModel()
    d = {p: m.new_int_var(1, 9, f"d{p}") for p in CELLS}
    for i in range(N):
        m.add_all_different([d[i, c] for c in range(N)])
        m.add_all_different([d[r, i] for r in range(N)])
    for br in range(3):
        for bc in range(3):
            m.add_all_different(
                [d[br * 3 + r, bc * 3 + c] for r in range(3) for c in range(3)]
            )

    far = {}
    for p, q in pi.ADJACENT:
        v = m.new_bool_var(f"far{p}{q}")
        gap = m.new_int_var(-8, 8, f"g{p}{q}")
        m.add(gap == d[p] - d[q])
        mag = m.new_int_var(0, 8, f"a{p}{q}")
        m.add_abs_equality(mag, gap)
        m.add(mag >= 5).only_enforce_if(v)
        m.add(mag <= 4).only_enforce_if(v.negated())
        far[p, q] = v
    if steer:
        m.add(sum(far.values()) >= steer)

    for a, b, r0, c0 in pair:
        inside = ccp.cells_of(a, b, r0, c0)
        for p in sorted(inside):
            for q in rv.neighbours(*p):
                if q in inside and q > p:
                    m.add(far[p, q] == 1)
        sites = [(r0 + i, c0 + j) for i, j in rc.circle_cells_at(a, b, r0 % 3, c0 % 3)]
        got = []
        for p in sites:
            v = m.new_bool_var(f"circ{p}")
            m.add(d[p] == a * b).only_enforce_if(v)
            got.append(v)
        m.add(sum(got) >= 1)

    for p in CELLS:
        m.add_hint(d[p], rng.randint(1, 9))
    s = cp.CpSolver()
    s.parameters.max_time_in_seconds = seconds
    s.parameters.num_workers = 1
    s.parameters.random_seed = seed
    if s.solve(m) not in (cp.OPTIMAL, cp.FEASIBLE):
        return None
    return {p: s.value(d[p]) for p in CELLS}


def attempt(job):
    pair, seed, steer, build_seconds, shade_seconds = job
    grid = grid_carrying(pair, seed, steer, build_seconds)
    if grid is None:
        return {"pair": pair, "seed": seed, "outcome": "no-grid"}
    model = pi.Shadings(grid, want_circled=2)
    status, is_choc = model.solve(shade_seconds, 1, seed)
    row = {
        "pair": pair,
        "seed": seed,
        "outcome": "hit" if is_choc else pi.cp.CpSolver().status_name(status).lower(),
        "circled_sites": getattr(model, "circled_sites", 0),
    }
    if is_choc:
        row["grid"] = ["".join(str(grid[r, c]) for c in range(N)) for r in range(N)]
        row["shading"] = [
            "".join("C" if is_choc[r, c] else "b" for c in range(N)) for r in range(N)
        ]
        row["violations"] = rv.check(grid, is_choc)[:5]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=20)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--steer", type=int, default=46)
    ap.add_argument("--build-seconds", type=float, default=30.0)
    ap.add_argument("--shade-seconds", type=float, default=30.0)
    ap.add_argument("--geometries", type=int, default=0, help="0 means all 1360")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    geos = ccp.geometries()
    if a.geometries:
        geos = geos[: a.geometries]
    jobs = [
        (g, seed, a.steer, a.build_seconds, a.shade_seconds)
        for g in geos
        for seed in range(a.seeds)
    ]
    print(
        f"{len(geos)} geometries x {a.seeds} seeds = {len(jobs)} attempts", flush=True
    )

    log = a.out / "hunt.jsonl"
    tally = {}
    began = time.monotonic()
    with ProcessPoolExecutor(max_workers=a.procs) as pool:
        for done, row in enumerate(pool.map(attempt, jobs, chunksize=2), 1):
            tally[row["outcome"]] = tally.get(row["outcome"], 0) + 1
            with log.open("a") as f:
                f.write(json.dumps(row) + "\n")
            if row["outcome"] == "hit":
                print(
                    f"HIT on geometry {row['pair']} seed {row['seed']} "
                    f"(violations: {row['violations']})",
                    flush=True,
                )
            if done % 50 == 0:
                print(
                    f"  {done}/{len(jobs)} in {time.monotonic() - began:.0f}s: {tally}",
                    flush=True,
                )

    (a.out / "stats.json").write_text(json.dumps(tally, indent=1) + "\n")
    print(
        f"\n{len(jobs)} attempts, {time.monotonic() - began:.0f}s: {tally}", flush=True
    )
    print(
        "A miss is not a proof: these are sampled grids, not every grid. "
        "The proof is the joint model.",
        flush=True,
    )


if __name__ == "__main__":
    main()
