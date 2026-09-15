"""For each feasible fourth line, which sums the *other* pair can still take.

Usage: uv run other_pair_sums.py board.json FIXED_A,FIXED_B TARGET feasible.txt out.jsonl
Reads one partner per line (r..c..-r..c.. paths), pairs FIXED_A-FIXED_B and
TARGET-partner, and probes every FIXED_A segment sum 6..30 for feasibility.
Baseline (no partner) is written first.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, "docs/research/2026-09-14-galaxy-copycat")
from copycat_rsl_solver import build
from ortools.sat.python import cp_model

BASE, FIXED, TARGET, LIST, OUT = (
    sys.argv[1],
    sys.argv[2].split(","),
    sys.argv[3],
    sys.argv[4],
    sys.argv[5],
)
base = json.loads(Path(BASE).read_text())


def sums_for(cells: list[str] | None) -> list[int]:
    setup = {"lines": dict(base["lines"]), "pairs": [FIXED]}
    if cells:
        setup["lines"]["L4"] = cells
        setup["pairs"].append([TARGET, "L4"])
    ok = []
    for s in range(6, 31):
        m, *_ = build(dict(setup, sums={FIXED[0]: s}))
        sv = cp_model.CpSolver()
        sv.parameters.num_search_workers = 1
        sv.parameters.max_time_in_seconds = 20
        if sv.Solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            ok.append(s)
    return ok


with Path(OUT).open("a") as out:
    print(json.dumps({"cells": None, "sums": sums_for(None)}), file=out, flush=True)
    for raw in Path(LIST).read_text().split():
        cells = raw.split("-")
        print(json.dumps({"cells": raw, "sums": sums_for(cells)}), file=out, flush=True)
    print("DONE", file=out)
