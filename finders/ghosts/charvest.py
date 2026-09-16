"""Ghosts, all visible: harvest unique shapes with the C climb.

    uv run finders/ghosts/charvest.py --seconds 1200 --seed 1 --out DIR

Each loop starts from a fresh CP-SAT seed (probability --fresh) or from a
random shape in this process's pool of climb endpoints, then runs gf_climb
hot (t_hi 2 -> t_lo 0.05, walks of up to 6 toggles; the best of three
settings in a 6-seed x 10 s comparison). A unique result is deduplicated up
to the 8 square symmetries and appended to DIR/examples.jsonl with its
solution grid. DIR/summary.json is rewritten after every loop.
"""

import argparse
import json
import random
import time
from pathlib import Path

from fastclimb import climb
from harvest import canonical
from shapes import count_solutions, givens, seed_shape


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=1200)
    ap.add_argument("--climb-seconds", type=float, default=10)
    ap.add_argument("--fresh", type=float, default=0.3)
    ap.add_argument("--min-ghosts", type=int, default=26)
    ap.add_argument("--t-hi", type=float, default=2.0)
    ap.add_argument("--t-lo", type=float, default=0.05)
    ap.add_argument("--toggles", type=int, default=6)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    t0 = time.monotonic()
    seen = set()
    pool = []
    stats = {"seed": a.seed, "loops": 0, "fresh": 0, "hits": 0, "new": 0}
    while time.monotonic() - t0 < a.seconds:
        stats["loops"] += 1
        if not pool or rng.random() < a.fresh:
            start = seed_shape(rng, a.min_ghosts)
            stats["fresh"] += 1
        else:
            start = rng.choice(pool)
        secs = min(a.climb_seconds, a.seconds - (time.monotonic() - t0))
        if secs <= 0.5:
            break
        best, score, _ = climb(
            start, rng.randrange(1, 1 << 62), secs, 2000, a.t_hi, a.t_lo, a.toggles
        )
        if score < 0:
            continue
        pool.append(best)
        if len(pool) > 200:
            pool.pop(rng.randrange(len(pool)))
        if score != 1:
            continue
        stats["hits"] += 1
        key = canonical(best)
        if key in seen:
            continue
        seen.add(key)
        stats["new"] += 1
        sols = []
        assert count_solutions(givens(best), 2, None, sols) == 1
        with (a.out / "examples.jsonl").open("a") as out:
            out.write(
                json.dumps(
                    {
                        "seed": a.seed,
                        "ghosts": len(best),
                        "shape": sorted(best),
                        "canonical": list(key),
                        "solution": sols[0],
                    }
                )
                + "\n"
            )
        stats["elapsed_s"] = round(time.monotonic() - t0)
        (a.out / "summary.json").write_text(json.dumps(stats))
        print(
            f"new #{stats['new']}: {len(best)} ghosts; {json.dumps(stats)}", flush=True
        )
    stats["elapsed_s"] = round(time.monotonic() - t0)
    (a.out / "summary.json").write_text(json.dumps(stats))
    print("done", json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
