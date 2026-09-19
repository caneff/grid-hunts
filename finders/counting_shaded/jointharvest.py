"""counting shaded, all visible and connected: enumerate joint seeds, keep the unique ones.

    uv run finders/counting_shaded/jointharvest.py --seconds 1800 --min-shaded 20 --out DIR

Follows the idiom that produced the 234 disconnected examples and the repo's
other working finders: a CP-SAT model states everything except uniqueness, and
uniqueness is decided outside it by the bounded bitmask counter. Here the model
is the joint one -- digits, shaded cells, the all-visible link, flow connectivity --
so every shape it returns is connected, admissible and solvable by
construction. `joint.py --maximize` proves the ceiling is 26 shaded cells.

Each shape is checked with the counter, then forbidden exactly so the next
solve returns a different one. A non-unique shape is also handed to the C climb
(which enforces connectivity itself) as a local-search start, since the first
optimal shape found came in at 2 solutions -- near misses are common and cheap
to repair.
"""

import argparse
import json
import random
import time
from pathlib import Path

from fastclimb import climb
from harvest import canonical
from joint import build
from ortools.sat.python import cp_model
from shapes import count_solutions, givens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=1800)
    ap.add_argument("--solve-seconds", type=float, default=120)
    ap.add_argument("--climb-seconds", type=float, default=5)
    ap.add_argument("--min-shaded", type=int, default=20)
    ap.add_argument("--max-shaded", type=int, default=26)
    ap.add_argument("--no-climb", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    seen, stats = set(), {"seeds": 0, "unique": 0, "climbed": 0, "sizes": {}}
    while time.monotonic() - t0 < a.seconds:
        left = min(a.solve_seconds, a.seconds - (time.monotonic() - t0))
        if left <= 1:
            break
        weights = [rng.randint(-100, 100) for _ in range(81)]
        m, _v, g = build(a.min_shaded, a.max_shaded, maximize=False, weights=weights)
        s = cp_model.CpSolver()
        s.parameters.num_workers = a.workers
        s.parameters.random_seed = rng.randrange(1 << 30)
        s.parameters.max_time_in_seconds = left
        st = s.solve(m)
        if st == cp_model.INFEASIBLE:
            print("INFEASIBLE: no shape exists in this size range", flush=True)
            break
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # UNKNOWN is a timeout, NOT a proof that no shape is left.
            print(f"{s.status_name(st)}: solve timed out, retrying", flush=True)
            continue
        shape = {i for i in range(81) if s.value(g[i])}
        stats["seeds"] += 1
        stats["sizes"][len(shape)] = stats["sizes"].get(len(shape), 0) + 1
        cands = [(shape, "seed")]
        if not a.no_climb:
            best, score, _ = climb(
                shape, rng.randrange(1, 1 << 62), a.climb_seconds, 2000, 2.0, 0.05, 6
            )
            if score >= 0:
                stats["climbed"] += 1
                cands.append((set(best), "climb"))
        for cand, how in cands:
            gv = givens(cand)
            if gv is None or count_solutions(gv, 2) != 1:
                continue
            key = canonical(cand)
            if key in seen:
                continue
            seen.add(key)
            stats["unique"] += 1
            row = {"shaded": len(cand), "shape": sorted(cand), "from": how}
            with (a.out / "connected.jsonl").open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(
                f"UNIQUE {len(cand)} shaded cells via {how}: {sorted(cand)}", flush=True
            )
        (a.out / "summary.json").write_text(json.dumps(stats, indent=2))
        if stats["seeds"] % 10 == 0:
            print(
                f"seeds {stats['seeds']} unique {stats['unique']} "
                f"({time.monotonic() - t0:.0f}s) sizes {stats['sizes']}",
                flush=True,
            )
    print(f"done: {json.dumps(stats)}")


if __name__ == "__main__":
    main()
