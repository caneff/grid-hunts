"""Score feasible 4-cell line pairs (from find_pair4) by how much they pin down.

Usage: uv run rank_pair4.py board.json pairs.jsonl out.jsonl [limit]
For each pair: `limit` solves with random digit objectives; record, per cell,
the digits seen and whether the copycat flag varied.  Score = number of cells
whose digit is constant across the sample (an upper bound on forced cells;
verify the leaders with copycat_rsl_solver --candidates).
"""

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build, parse_cell
from ortools.sat.python import cp_model

BASE, PAIRS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 12
base = json.loads(Path(BASE).read_text())


# baseline: which cells are already constant on the board alone
def sample(setup):
    """K solves, each maximising a random weighting of the digits, so the grids
    differ in digits (plain enumeration only shuffles copycat placements)."""
    rng = random.Random(1)
    digits = [[set() for _ in range(9)] for _ in range(9)]
    flags = [[set() for _ in range(9)] for _ in range(9)]
    n = 0
    for _ in range(LIMIT):
        m, digit, cc, _ = build(setup)
        m.Maximize(
            sum(rng.randint(-9, 9) * digit[r][c] for r in range(9) for c in range(9))
        )
        sv = cp_model.CpSolver()
        sv.parameters.num_search_workers = 1
        sv.parameters.max_time_in_seconds = 20
        st = sv.Solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            continue
        n += 1
        for r in range(9):
            for c in range(9):
                digits[r][c].add(sv.Value(digit[r][c]))
                flags[r][c].add(bool(sv.Value(cc[r][c])))
    return n, digits, flags


n0, base_digits, base_flags = sample(base)
base_fixed = {(r, c) for r in range(9) for c in range(9) if len(base_digits[r][c]) == 1}
print(f"baseline: {n0} solutions sampled, {len(base_fixed)} constant cells", flush=True)

for raw in Path(PAIRS).read_text().splitlines():
    if not raw.startswith("{"):
        continue
    row = json.loads(raw)
    setup = {
        "lines": dict(base["lines"], X=row["X"].split("-"), Y=row["Y"].split("-")),
        "pairs": [*base["pairs"], ["X", "Y"]],
    }
    t = time.time()
    n, digits, flags = sample(setup)
    fixed = {(r, c) for r in range(9) for c in range(9) if len(digits[r][c]) == 1}
    new = sorted(fixed - base_fixed)
    cc_fixed = sum(
        1
        for r in range(9)
        for c in range(9)
        if len(flags[r][c]) == 1 and len(base_flags[r][c]) > 1
    )
    xcells = [parse_cell(c) for c in row["X"].split("-")]
    ycells = [parse_cell(c) for c in row["Y"].split("-")]
    line_fixed = sum(1 for rc in xcells + ycells if len(digits[rc[0]][rc[1]]) == 1)
    out = {
        "X": row["X"],
        "Y": row["Y"],
        "n": n,
        "new_fixed": len(new),
        "new_cells": [f"r{r + 1}c{c + 1}={next(iter(digits[r][c]))}" for r, c in new],
        "cc_fixed": cc_fixed,
        "line_fixed": line_fixed,
        "t": round(time.time() - t, 1),
    }
    with Path(OUT).open("a") as f:
        print(json.dumps(out), file=f, flush=True)
with Path(OUT).open("a") as f:
    print("DONE", file=f)
