"""Rank feasible fourth lines from a find_l4_all log by how much they force.

Usage: uv run rank_l4.py board.json FIXED_A,FIXED_B TARGET search.log out.txt
For each FEASIBLE candidate: enumerate up to LIMIT solutions (TIME s) and
record the pair sums seen, whether every solution has a copycat on the
candidate, the boxes it shares with the fixed lines, and the distinct-value
counts seen.  Lines with fewer sums / a forced copycat sort first.
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from copycat_rsl_solver import Collector, box_of, build, segments, value_of
from ortools.sat.python import cp_model
from segment_openers import line_multisets

BASE, FIXED, TARGET, LOGPATH, OUT = (
    sys.argv[1],
    sys.argv[2].split(","),
    sys.argv[3],
    sys.argv[4],
    sys.argv[5],
)
LIMIT, TIME = 40, 20
base = json.loads(Path(BASE).read_text())


def rc(cell: str) -> tuple[int, int]:
    return int(cell[1]) - 1, int(cell[3]) - 1


def boxes(cells: list[str]) -> set[int]:
    return {box_of(*rc(c)) for c in cells}


fixed_boxes = {name: boxes(cells) for name, cells in base["lines"].items()}
rows = []
for raw in Path(LOGPATH).read_text().splitlines():
    if " FEASIBLE " not in raw:
        continue
    cells = raw.split()[-1].split("-")
    setup = {
        "lines": dict(base["lines"], L4=cells),
        "pairs": [FIXED, [TARGET, "L4"]],
    }
    m, digit, cc, lines = build(setup)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = TIME
    col = Collector(digit, cc, LIMIT)
    t = time.time()
    solver.Solve(m, col)
    sums, cc_on, distinct = Counter(), [], Counter()
    l4 = [rc(c) for c in cells]
    target = [rc(c) for c in base["lines"][TARGET]]
    seg0 = segments(target)[0]  # pair sums are reported as TARGET's segment sum
    for d, k in col.solutions:
        vals = {(r, c): value_of(d, k, r, c) for r, c in l4}
        sums[sum(value_of(d, k, r, c) for r, c in seg0)] += 1
        cc_on.append(sum(k[r][c] for r, c in l4))
        distinct[len(set(vals.values()))] += 1
    n = len(col.solutions)
    # sums the segment model allows but the sample missed: test each one
    struct = tuple(len(s) for s in segments(l4))
    target_struct = tuple(
        len(s) for s in segments([rc(c) for c in base["lines"][TARGET]])
    )
    for s_t in range(3, 46):
        if s_t in sums or (len(target_struct) * s_t) % len(struct):
            continue
        s_4 = len(target_struct) * s_t // len(struct)
        if not set(line_multisets(target_struct, s_t)) & set(
            line_multisets(struct, s_4)
        ):
            continue
        m2, d2, k2, _ = build(dict(setup, sums={TARGET: s_t}))
        sv = cp_model.CpSolver()
        sv.parameters.num_search_workers = 1
        sv.parameters.max_time_in_seconds = TIME
        if sv.Solve(m2) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            sums[s_t] += 0
    shared = {
        name: sorted(b + 1 for b in boxes(cells) & fb)
        for name, fb in fixed_boxes.items()
    }
    shared = {k: v for k, v in shared.items() if v}
    rows.append(
        {
            "cells": "-".join(cells),
            "struct": struct,
            "n": n,
            "sums": sorted(sums),
            "min_cc": min(cc_on) if cc_on else None,
            "distinct": sorted(distinct),
            "shared": shared,
            "t": round(time.time() - t, 1),
        }
    )
    with Path(OUT).open("a") as out:
        print(json.dumps(rows[-1]), file=out)
with Path(OUT).open("a") as out:
    print("DONE", file=out)
