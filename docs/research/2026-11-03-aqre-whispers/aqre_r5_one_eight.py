"""SCRATCH: fixed-region r5 solves on layouts where exactly one region can be the 8.

Chris, 2026-11-04: place the 8 region, and no other region may be able to count 8.
Sampled layouts qualify when, looking at each region alone, exactly one circled region can
be the circled 8 and the ninth region cannot count 8 with a circle on any of its cells.
Sampling with that filter gives the same layouts as placing the 8 first; it is not an
enumeration. One worker, 30 minutes, stops at the first grid.
"""

import json
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_r5_staged import finish
from aqre_r5_eight_regions import holds_eight
from aqre_r5_fixed_regions import BUDGET, CELLS, ROW, attempt, relabel
from jigsaw_r5_diversity import measure, walk


def eight_regions(layout, n):
    """Columns of the circled regions that can be the 8, and whether the ninth can."""
    able = []
    for c in range(9):
        if c == n:
            continue
        cells = {cell for cell in CELLS if layout[cell] == c}
        if holds_eight(cells, (ROW, c)):
            able.append(c)
    ninth = {cell for cell in CELLS if layout[cell] == n}
    return able, any(holds_eight(ninth, cell) for cell in ninth)


def main(out):
    start = time.time()
    rng = random.Random(31)
    pool = [x for seed in (41, 42, 43, 44, 45, 46) for x in walk(seed, 20.0) if measure(x)["straight"] == 0]
    rng.shuffle(pool)
    print(f"{len(pool)} layouts sampled", flush=True)
    tally = {}
    looked = qualified = 0
    spread = {}
    for raw in pool:
        if time.time() - start >= BUDGET:
            break
        pair = [c for c in range(9) if sum(raw[ROW, x] == raw[ROW, c] for x in range(9)) == 2]
        for n in pair:
            layout = relabel(raw, ROW, n)
            looked += 1
            able, ninth = eight_regions(layout, n)
            spread[len(able)] = spread.get(len(able), 0) + 1
            if len(able) != 1 or ninth:
                continue
            qualified += 1
            print(f"case {qualified}, looked at {looked}, 8 region at r5c{able[0] + 1}, 9 in r5c{n + 1}, {time.time() - start:.0f}s", flush=True)
            outcome, digits, shade = attempt(layout, ROW, n)
            tally[outcome] = tally.get(outcome, 0) + 1
            print(f"  tally {tally}; regions able, by count {sorted(spread.items())}", flush=True)
            with (out / "one-eight-r5.jsonl").open("a") as f:
                f.write(json.dumps({
                    "n": n,
                    "eight": able[0],
                    "outcome": outcome,
                    "region": [[layout[r, c] for c in range(9)] for r in range(9)],
                }) + "\n")
            if digits:
                finish(digits, shade, layout, n, out)
                print(f"cases {qualified}, tally {tally}", flush=True)
                return
    print(f"no grid: looked at {looked}, {qualified} cases, tally {tally}, able by count {sorted(spread.items())}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
