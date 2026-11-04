"""SCRATCH: a layout score that keeps the circles hard and minimises shaded groups.

Fixed regions, every rule but connectivity held hard. Each shaded group needs one root,
which supplies flow to the group's other cells, so the fewest roots is the fewest shaded
groups. 1 is a valid grid. `check DIR K` scores K layouts from the fixed-region log;
`control DIR` scores grid-8-r1.
"""

import json
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from aqre_r5_fixed_regions import CELLS, ROW, build, one_worker
from ortools.sat.python import cp_model


def build_groups(region, row, n):
    m, x, g = build(region, row, n, False)
    roots = []
    inflow = {i: [] for i in range(81)}
    outflow = {i: [] for i in range(81)}
    for r, c in CELLS:
        i = r * 9 + c
        for a, b in neighbours((r, c)):
            j = a * 9 + b
            f = m.new_int_var(0, 44, f"f{i}_{j}")
            m.add(f <= 44 * g[i])
            m.add(f <= 44 * g[j])
            outflow[i].append(f)
            inflow[j].append(f)
    for i in range(81):
        root = m.new_bool_var(f"root{i}")
        roots.append(root)
        m.add_implication(root, g[i])
        supply = m.new_int_var(0, 44, f"s{i}")
        m.add(supply <= 44 * root)
        m.add(sum(inflow[i]) + supply - sum(outflow[i]) == g[i])
    m.add(sum(roots) >= 1)
    m.minimize(sum(roots))
    return m, x, g, roots


def groups_of(shade):
    left = {cell for cell in CELLS if shade[cell[0]][cell[1]]}
    sizes = []
    while left:
        stack, size = [left.pop()], 0
        while stack:
            cell = stack.pop()
            size += 1
            for other in neighbours(cell):
                if other in left:
                    left.remove(other)
                    stack.append(other)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def score(region, row, n, limit, hint=None):
    m, x, g, roots = build_groups(region, row, n)
    if hint:
        for r, c in CELLS:
            m.add_hint(x[r, c], hint["digits"][r][c])
            m.add_hint(g[r * 9 + c], int(hint["shaded"][r][c]))
    s = one_worker(limit)
    status = s.solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return s.status_name(status), None, None
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    return s.status_name(status), int(s.objective_value), groups_of(shade)


def main(out, mode, k):
    if mode == "control":
        known = json.loads((out / "grid-8-r1.json").read_text())
        region = {tuple(cell): i for i, cells in enumerate(known["regions"]) for cell in cells}
        print("grid-8-r1:", score(region, 0, 4, 60.0, hint=known), flush=True)
        return
    rows = [json.loads(line) for line in (out / "fixed-r5.jsonl").read_text().splitlines()]
    picks = random.Random(1).sample(rows, k)
    for i, old in enumerate(picks):
        region = {cell: old["region"][cell[0]][cell[1]] for cell in CELLS}
        begun = time.time()
        print(f"layout {i + 1}, earlier {old['outcome']}:", score(region, ROW, old["n"], 30.0),
              f"{time.time() - begun:.1f}s", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[2]), sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
