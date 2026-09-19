"""Largest shaded cell grid containing a given set of pinned cells. Uniqueness aside.

    uv run finders/counting_shaded/maxpinned.py --force r9c1,r9c2 [--no-connect]

Maximises the shaded cell count subject to the pins, so the answer is the biggest
configuration those cells can sit in. Uniqueness is not tested and not wanted
here -- the question is what exists.

Cells are named r<row>c<col>, 1-based, or given as raw 0-80 indices.
`--no-connect` drops the orthogonal-connectivity requirement, which raises the
ceiling from 26 to 35 and is worth running alongside as a comparison.

OPTIMAL means the printed size is the true maximum. FEASIBLE means the solver
ran out of time with that as its best so far, and a larger one may exist --
the distinction is printed, never glossed.
"""

import argparse
import json
import re
import time
from pathlib import Path

from joint import build
from ortools.sat.python import cp_model
from shapes import NEIGH, connected, count_solutions


def parse_cells(text):
    """'r9c1,r9c2' or '72,73' -> [72, 73]."""
    out = []
    for token in (t.strip() for t in text.split(",") if t.strip()):
        m = re.fullmatch(r"[rR](\d)[cC](\d)", token)
        if m:
            out.append((int(m.group(1)) - 1) * 9 + int(m.group(2)) - 1)
        else:
            out.append(int(token))
    return out


def name(i):
    return f"r{i // 9 + 1}c{i % 9 + 1}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", default="", help="cells that must be shaded cells")
    ap.add_argument("--ban", default="", help="cells that must not be shaded cells")
    ap.add_argument("--seconds", type=float, default=900)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-connect", action="store_true")
    ap.add_argument("--all-digits", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    force, ban = parse_cells(a.force), parse_cells(a.ban)
    print(f"force {[name(i) for i in force]}  ban {[name(i) for i in ban]}")
    print(f"connectivity: {'OFF' if a.no_connect else 'ON'}")

    m, v, g = build(
        1,
        81,
        maximize=True,
        connect=not a.no_connect,
        all_digits=a.all_digits,
        force=force,
        ban=ban,
    )
    s = cp_model.CpSolver()
    s.parameters.num_workers = a.workers
    s.parameters.max_time_in_seconds = a.seconds
    t0 = time.monotonic()
    st = s.solve(m)
    el = time.monotonic() - t0
    print(f"{s.status_name(st)} in {el:.1f}s")
    if st == cp_model.INFEASIBLE:
        print("no shaded cell grid at all contains those pins")
        return
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("timed out with no solution; nothing proved either way")
        return

    shape = sorted(i for i in range(81) if s.value(g[i]))
    grid = [s.value(x) for x in v]
    proved = st == cp_model.OPTIMAL
    print(
        f"shaded cells {len(shape)} "
        + ("(proved maximum)" if proved else "(best so far)")
    )
    print(f"shape {shape}")
    print(f"cells {[name(i) for i in shape]}")
    gv = {i: sum(j in set(shape) for j in NEIGH[i]) for i in shape}
    print(f"digits present: {sorted(set(gv.values()))}")
    print(f"connected: {connected(set(shape))}")
    print(f"solutions (cap 1000): {count_solutions(gv, 1000)}")
    assert all(grid[i] == gv[i] for i in shape), "shaded cell digit is not its count"
    for i in force:
        assert i in shape, f"{name(i)} was forced but is not a shaded cell"
    for i in ban:
        assert i not in shape, f"{name(i)} was banned but is a shaded cell"
    print("pins and shaded cell digits re-checked outside the solver")
    for r in range(9):
        print(
            "  "
            + " ".join(
                f"({grid[r * 9 + c]})" if r * 9 + c in shape else f" {grid[r * 9 + c]} "
                for c in range(9)
            )
        )
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("a") as fh:
            fh.write(
                json.dumps(
                    {
                        "shaded": len(shape),
                        "shape": shape,
                        "grid": grid,
                        "forced": force,
                        "banned": ban,
                        "connected": connected(set(shape)),
                        "proved_maximum": proved,
                    }
                )
                + "\n"
            )


if __name__ == "__main__":
    main()
