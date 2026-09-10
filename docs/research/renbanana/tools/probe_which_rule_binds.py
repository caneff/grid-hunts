"""Which rule makes a random solved grid unshadeable?

The inverted probe proves random grids carry no legal Renbanana shading, and
steering the grid toward more whisper-legal adjacencies did not change that.
So the whisper is probably not what binds. This drops one rule at a time and
re-asks: the relaxation that flips infeasible to feasible is the real gate.

    uv run --with ortools docs/research/renbanana/tools/probe_which_rule_binds.py --grids 20

One worker, one process (AGENTS.md).
"""

import argparse
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model as cp

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from probe_inverted import Shadings, random_grid

RULES = ("none", "whisper", "renban-consecutive", "renban-distinct", "non-rectangle")


def relaxed(grid, drop):
    """The shading model with one rule removed."""
    m = Shadings.__new__(Shadings)
    Shadings.__init__(m, grid, drop=drop)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grids", type=int, default=20)
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()

    tally = dict.fromkeys(RULES, 0)
    for seed in range(a.grids):
        grid = random_grid(seed, 30.0, a.workers)
        line = []
        for drop in RULES:
            model = Shadings(grid, drop=drop)
            t0 = time.monotonic()
            status, is_choc = model.solve(a.seconds, a.workers, seed)
            got = is_choc is not None
            tally[drop] += got
            line.append(
                f"{drop}={'YES' if got else cp.CpSolver().status_name(status)[:4]}"
                f"/{time.monotonic() - t0:.0f}s"
            )
        print(f"seed {seed}: " + "  ".join(line), flush=True)

    print("\ndropping nothing is the real rate; the rest say what binds:")
    for drop in RULES:
        print(f"  drop {drop:20s} {tally[drop]:3d}/{a.grids} shadeable")


if __name__ == "__main__":
    main()
