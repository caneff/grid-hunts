"""Score feasible 4-cell line pairs (from find_pair4) by how much they pin down.

Usage: uv run rank_pair4.py board.json pairs.jsonl out.jsonl
         [--limit 4] [--top 30] [--full 12] [--shape 2,2] [--seed forced.json]
Two stages.  Stage 1: every pair gets `limit` solves with random digit
objectives; record, per cell, the digits seen and whether the copycat flag
varied.  Score = number of cells whose digit is constant across the sample (an
upper bound on forced cells).  Stage 2: the `top` pairs by that score are
re-sampled with `full` solves and rewritten (rows carry "stage": 1 or 2).
Verify the leaders with copycat_rsl_solver --candidates.
--shape keeps only pairs whose two lines both have those segment lengths
(needs the .lines.jsonl beside pairs.jsonl); --seed merges exact forced facts
(from --candidates --forced-out) into every model.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build, parse_cell
from ortools.sat.python import cp_model

ap = argparse.ArgumentParser()
ap.add_argument("board")
ap.add_argument("pairs")
ap.add_argument("out")
ap.add_argument("--limit", type=int, default=4, help="stage-1 solves per pair")
ap.add_argument("--top", type=int, default=30, help="pairs re-sampled in stage 2")
ap.add_argument("--full", type=int, default=12, help="stage-2 solves per pair")
ap.add_argument("--shape", help="a,b: keep pairs whose lines both have this shape")
ap.add_argument("--seed", help="forced.json from copycat_rsl_solver --forced-out")
args = ap.parse_args()
BASE, PAIRS, OUT = args.board, args.pairs, args.out
base = json.loads(Path(BASE).read_text())
SEED = json.loads(Path(args.seed).read_text()) if args.seed else {}
SHAPES = None
if args.shape:
    shape = tuple(int(x) for x in args.shape.split(","))
    lines_file = Path(PAIRS.replace(".pairs.jsonl", ".lines.jsonl"))
    SHAPES = {
        row["cells"]: tuple(row["struct"])
        for row in map(json.loads, lines_file.read_text().splitlines())
    }
    keep = (shape, shape[::-1])


# baseline: which cells are already constant on the board alone
def sample(setup, k):
    """k solves, each maximising a random weighting of the digits, so the grids
    differ in digits (plain enumeration only shuffles copycat placements)."""
    rng = random.Random(1)
    digits = [[set() for _ in range(9)] for _ in range(9)]
    flags = [[set() for _ in range(9)] for _ in range(9)]
    n = 0
    for _ in range(k):
        m, digit, cc, _ = build({**SEED, **setup})
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


n0, base_digits, base_flags = sample(base, args.full)
base_fixed = {(r, c) for r in range(9) for c in range(9) if len(base_digits[r][c]) == 1}
print(f"baseline: {n0} solutions sampled, {len(base_fixed)} constant cells", flush=True)


def score(row, k, stage):
    setup = {
        "lines": dict(base["lines"], X=row["X"].split("-"), Y=row["Y"].split("-")),
        "pairs": [*base["pairs"], ["X", "Y"]],
    }
    t = time.time()
    n, digits, flags = sample(setup, k)
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
        "stage": stage,
        "n": n,
        "new_fixed": len(new),
        "new_cells": [f"r{r + 1}c{c + 1}={next(iter(digits[r][c]))}" for r, c in new],
        "cc_fixed": cc_fixed,
        "line_fixed": line_fixed,
        "t": round(time.time() - t, 1),
    }
    with Path(OUT).open("a") as f:
        print(json.dumps(out), file=f, flush=True)
    return out


rows = [
    json.loads(raw)
    for raw in Path(PAIRS).read_text().splitlines()
    if raw.startswith("{")
]
if SHAPES:
    rows = [r for r in rows if SHAPES[r["X"]] in keep and SHAPES[r["Y"]] in keep]
print(f"{len(rows)} pairs to rank", flush=True)
stage1 = [score(row, args.limit, 1) for row in rows]
stage1.sort(key=lambda o: -o["new_fixed"])
for out in stage1[: args.top]:
    score(out, args.full, 2)
with Path(OUT).open("a") as f:
    print("DONE", file=f)
