"""SCRATCH: why does every digits-first grid refuse regions so fast?

For logged digit grids, solve the region search with pieces dropped: the r5 counts, the
no-straight rule, and region connectivity. Also count distinct grids in the log.
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from ortools.sat.python import cp_model

CELLS = [(r, c) for r in range(9) for c in range(9)]
ROW = 4


def search(digits, shade, row, counts=True, no_straight=True, joined=True, limit=30.0):
    n = digits[row].index(9)
    m = cp_model.CpModel()
    y = {cell: [m.new_bool_var("") for k in range(9)] for cell in CELLS}
    level = {cell: m.new_int_var(0, 8, "") for cell in CELLS}
    for cell in CELLS:
        m.add_exactly_one(y[cell])
    for c in range(9):
        if c != n:
            m.add(y[row, c][c] == 1)
            if joined:
                m.add(level[row, c] == 0)
    if joined:
        free_roots = []
        for cell in CELLS:
            if cell[0] == row and cell[1] != n:
                continue
            root = m.new_bool_var("")
            free_roots.append(root)
            m.add_implication(root, y[cell][n])
            m.add(level[cell] == 0).only_enforce_if(root)
            parents = [root]
            for other in neighbours(cell):
                p = m.new_bool_var("")
                parents.append(p)
                m.add(level[cell] >= 1).only_enforce_if(p)
                m.add(level[cell] == level[other] + 1).only_enforce_if(p)
                for k in range(9):
                    m.add_bool_or(p.Not(), y[cell][k].Not(), y[other][k])
            m.add_exactly_one(parents)
        m.add_exactly_one(free_roots)
    for k in range(9):
        for v in range(1, 10):
            m.add_exactly_one(y[r, c][k] for r, c in CELLS if digits[r][c] == v)
        total = sum(y[r, c][k] for r, c in CELLS if shade[r][c])
        if counts:
            m.add(total >= 1)
            if k != n:
                m.add(total == digits[row][k])
        if no_straight:
            for a in range(9):
                m.add(sum(y[a, c][k] for c in range(9)) <= 8)
                m.add(sum(y[r, a][k] for r in range(9)) <= 8)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = limit
    return s.status_name(s.solve(m))


def main(path, k):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    distinct = len({json.dumps(row["digits"]) for row in rows})
    print(f"{len(rows)} logged, {distinct} distinct digit grids", flush=True)
    picks = random.Random(2).sample(rows, k)
    variants = {
        "all": {},
        "no counts": {"counts": False},
        "no straight rule": {"no_straight": False},
        "no region connectivity": {"joined": False},
        "only digits in regions": {"counts": False, "no_straight": False, "joined": False},
        "connected only": {"counts": False, "no_straight": False},
    }
    for name, flags in variants.items():
        tally = Counter(search(row["digits"], row["shaded"], ROW, **flags) for row in picks)
        print(f"{name}: {dict(tally)}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
