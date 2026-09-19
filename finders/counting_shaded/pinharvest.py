"""Largest all-visible-unique connected shading under pinned cells.

    uv run finders/counting_shaded/pinharvest.py --force 72,73 --size 21 --enumerate --seconds 600 --out DIR
    uv run finders/counting_shaded/pinharvest.py --force 72,73 --min-shaded 17 --max-shaded 21 --seconds 600 --out DIR

The question (Chris, 2026-09-16): with r9c1 and r9c2 shaded, what is the largest
connected shading whose digits, taken as the only givens, force the sudoku?
The shading fixes those digits (each is its shaded-neighbour count), so this is
a search over shapes; uniqueness is the bitmask counter at cap 2. All eight
digits 1-8 must appear on the shape (a sudoku whose givens omit two digits is
never unique), which `joint.add_all_digits` posts and which caps the answer at
21 for this pin.

Two modes. `--enumerate` fixes one size and forbids each returned shape
exactly, so INFEASIBLE means the size is exhausted -- a proof that no unique
shape of that size exists under the pin. Without it, random objective weights
give diverse seeds in a size band and each seed goes to the C climb (which
honours the pins) as a local-search start.

Symmetry breaking stays off: a pin fixes the orientation, and `build()` refuses
the combination anyway.
"""

import argparse
import json
import time
from pathlib import Path

from fastclimb import climb, pins
from joint import build
from ortools.sat.python import cp_model
from shapes import count_solutions, givens


def parse_cells(text):
    return tuple(int(x) for x in text.split(",")) if text else ()


def record(a, cand, how, log):
    gv = givens(cand)
    n = count_solutions(gv, 2) if gv is not None else -1
    if n != 1:
        return False
    row = {"shaded": len(cand), "shape": sorted(cand), "from": how}
    with (a.out / "unique.jsonl").open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    log(f"UNIQUE {len(cand)} shaded via {how}: {sorted(cand)}")
    return True


def enumerate_size(a, force, ban, log):
    """Every shape of exactly --size under the pins, each forbidden after use."""
    m, _v, g = build(a.size, a.size, False, all_digits=True, force=force, ban=ban)
    s = cp_model.CpSolver()
    s.parameters.num_workers = a.workers
    t0 = time.monotonic()
    shapes = uniques = 0
    while True:
        left = a.seconds - (time.monotonic() - t0)
        if left <= 1:
            log(
                f"time up: {shapes} shapes at size {a.size}, {uniques} unique; NOT exhausted"
            )
            return "timeout", shapes, uniques
        s.parameters.max_time_in_seconds = left
        st = s.solve(m)
        if st == cp_model.INFEASIBLE:
            log(
                f"EXHAUSTED size {a.size}: {shapes} shapes, {uniques} unique ({time.monotonic() - t0:.0f}s)"
            )
            return "exhausted", shapes, uniques
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            log(f"{s.status_name(st)}: solve timed out, size {a.size} NOT exhausted")
            return "timeout", shapes, uniques
        shape = {i for i in range(81) if s.value(g[i])}
        shapes += 1
        uniques += record(a, shape, "enumerate", log)
        # forbid exactly this shape
        m.add_bool_or(
            [g[i].Not() for i in shape] + [g[i] for i in range(81) if i not in shape]
        )
        if shapes % 50 == 0:
            log(
                f"size {a.size}: {shapes} shapes, {uniques} unique ({time.monotonic() - t0:.0f}s)"
            )


def seed_and_climb(a, force, ban, log):
    import random

    rng = random.Random(a.seed)
    t0 = time.monotonic()
    stats = {"seeds": 0, "unique": 0, "best": None}
    while time.monotonic() - t0 < a.seconds:
        left = min(a.solve_seconds, a.seconds - (time.monotonic() - t0))
        if left <= 1:
            break
        weights = [rng.randint(-100, 100) for _ in range(81)]
        m, _v, g = build(
            a.min_shaded,
            a.max_shaded,
            False,
            weights=weights,
            all_digits=True,
            force=force,
            ban=ban,
        )
        s = cp_model.CpSolver()
        s.parameters.num_workers = a.workers
        s.parameters.random_seed = rng.randrange(1 << 30)
        s.parameters.max_time_in_seconds = left
        st = s.solve(m)
        if st == cp_model.INFEASIBLE:
            log("INFEASIBLE: no shape in this size band under the pins")
            break
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            log(f"{s.status_name(st)}: seed solve timed out, retrying")
            continue
        shape = {i for i in range(81) if s.value(g[i])}
        stats["seeds"] += 1
        cands = [(shape, "seed")]
        best, score, _ = climb(
            shape, rng.randrange(1, 1 << 62), a.climb_seconds, 2000, 2.0, 0.05, 6
        )
        if score >= 0:
            cands.append((set(best), "climb"))
        for cand, how in cands:
            if record(a, cand, how, log):
                stats["unique"] += 1
                if stats["best"] is None or len(cand) > stats["best"]:
                    stats["best"] = len(cand)
        if stats["seeds"] % 10 == 0:
            log(
                f"seeds {stats['seeds']} unique {stats['unique']} best {stats['best']} ({time.monotonic() - t0:.0f}s)"
            )
    log(f"done: {json.dumps(stats)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", default="", help="cell indices 0-80 that must be shaded")
    ap.add_argument(
        "--ban", default="", help="cell indices 0-80 that must not be shaded"
    )
    ap.add_argument("--enumerate", action="store_true")
    ap.add_argument("--size", type=int, default=21)
    ap.add_argument("--min-shaded", type=int, default=17)
    ap.add_argument("--max-shaded", type=int, default=21)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--solve-seconds", type=float, default=120)
    ap.add_argument("--climb-seconds", type=float, default=5)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    force, ban = parse_cells(a.force), parse_cells(a.ban)
    pins(force, ban)
    progress = a.out / "progress.log"

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        with progress.open("a") as fh:
            fh.write(line + "\n")

    log(f"pins force={force} ban={ban} mode={'enumerate' if a.enumerate else 'climb'}")
    if a.enumerate:
        enumerate_size(a, force, ban, log)
    else:
        seed_and_climb(a, force, ban, log)


if __name__ == "__main__":
    main()
