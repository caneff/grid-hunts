"""SCRATCH: 8 circles in r5, digits and shading first, regions last. One worker.

Stage one solves a Latin square with Aqre shading and 5-whispers on shaded cells, no
regions, r5's digits free, and a shaded total of 37 to 44: the counts 1-8 sum to 36 and
the ninth region holds 1 to 8. The column of r5's 9 is `n`.

Stage two looks for regions on those fixed digits and shading: nine connected 9-cell
regions, each holding every digit, no straight region, region k rooted at r5 column k
with shaded count equal to that cell's digit. The 9 may sit in any region.

Each failure rules out one digit grid. It samples, so it says nothing about r5 as a whole.
It stops at the first grid. `control DIR` tests both stages on the known grid-8-r1.
"""

import json
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from aqre_jigsaw_r5_staged import finish, read_back, straight
from connected import add_flow_connectivity
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import sudoku_model

ROW = 4
GRID_LIMIT = 300.0
REGION_LIMIT = 60.0
BUDGET = 1800.0
CELLS = [(r, c) for r in range(9) for c in range(9)]


def one_worker(limit, seed=0):
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = limit
    s.parameters.random_seed = seed
    s.parameters.randomize_search = True
    return s


def build_grid(total_range=(37, 44)):
    m, x = sudoku_model(9, None, latin=True)
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    shaded = lambda r, c: g[r * 9 + c]
    even_low = m.new_bool_var("even_low")
    m.add(sum(g) >= total_range[0])
    m.add(sum(g) <= total_range[1])
    for a in range(9):
        for colour in (0, 1):
            m.add(sum(shaded(a, c) for c in range(9) if (a + c) % 2 == colour) <= 4)
            m.add(sum(shaded(r, a) for r in range(9) if (r + a) % 2 == colour) <= 4)
        for b in range(6):
            for line in (
                [shaded(a, b + i) for i in range(4)],
                [shaded(b + i, a) for i in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    for r, c in CELLS:
        low = even_low if (r + c) % 2 == 0 else even_low.Not()
        s = shaded(r, c)
        m.add(x[r, c] <= 4).only_enforce_if(s, low)
        m.add(x[r, c] >= 6).only_enforce_if(s, low.Not())
        for other in neighbours((r, c)):
            if (r, c) < other:
                t = shaded(*other)
                m.add(x[other] - x[r, c] >= 5).only_enforce_if(s, t, low)
                m.add(x[r, c] - x[other] >= 5).only_enforce_if(s, t, low.Not())
    add_flow_connectivity(m, g)
    return m, x, g


def find_regions(digits, shade, row, straight_ok=False, seed=0):
    """(status name, region dict or None) for fixed digits and shading."""
    n = digits[row].index(9)
    m = cp_model.CpModel()
    y = {cell: [m.new_bool_var(f"y{cell}{k}") for k in range(9)] for cell in CELLS}
    level = {cell: m.new_int_var(0, 8, f"l{cell}") for cell in CELLS}
    for cell in CELLS:
        m.add_exactly_one(y[cell])
    for c in range(9):
        if c != n:
            m.add(y[row, c][c] == 1)
            m.add(level[row, c] == 0)
    free_roots = []
    for cell in CELLS:
        if cell[0] == row and cell[1] != n:
            continue
        root = m.new_bool_var(f"root{cell}")
        free_roots.append(root)
        m.add_implication(root, y[cell][n])
        m.add(level[cell] == 0).only_enforce_if(root)
        parents = [root]
        for other in neighbours(cell):
            p = m.new_bool_var(f"p{cell}{other}")
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
        m.add(total >= 1)
        if k != n:
            m.add(total == digits[row][k])
        if not straight_ok:
            for a in range(9):
                m.add(sum(y[a, c][k] for c in range(9)) <= 8)
                m.add(sum(y[r, a][k] for r in range(9)) <= 8)
    s = one_worker(REGION_LIMIT, seed)
    status = s.solve(m)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        region = {cell: next(k for k in range(9) if s.value(y[cell][k])) for cell in CELLS}
        return s.status_name(status), region
    return s.status_name(status), None


def control(out):
    known = json.loads((out / "grid-8-r1.json").read_text())
    digits, shade = known["digits"], known["shaded"]
    m, x, g = build_grid()
    for r, c in CELLS:
        m.add(x[r, c] == digits[r][c])
        m.add(g[r * 9 + c] == int(shade[r][c]))
    s = one_worker(60.0)
    first = s.status_name(s.solve(m))
    print(f"grid model holds grid-8-r1: {first}", flush=True)
    name, region = find_regions(digits, shade, 0, straight_ok=True)
    print(f"regions on grid-8-r1: {name}", flush=True)
    broken = read_back(digits, shade, region, 0, digits[0].index(9))[0] if region else ["no regions"]
    print(f"reader: {broken or 'none'}", flush=True)
    name2, _ = find_regions(digits, [[True] * 9 for _ in range(9)], 0, straight_ok=True)
    print(f"regions with every cell shaded: {name2}", flush=True)
    ok = first in ("OPTIMAL", "FEASIBLE") and not broken and name2 == "INFEASIBLE"
    print("controls", "pass" if ok else "FAIL", flush=True)
    return ok


def run(out):
    start = time.time()
    tally = {}
    seed = 0
    while time.time() - start < BUDGET:
        seed += 1
        m, x, g = build_grid()
        s = one_worker(min(GRID_LIMIT, BUDGET - (time.time() - start)), seed)
        status = s.solve(m)
        print(f"try {seed}: grid {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            tally["grid " + s.status_name(status)] = tally.get("grid " + s.status_name(status), 0) + 1
            continue
        digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
        shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
        begun = time.time()
        name, region = find_regions(digits, shade, ROW, seed=seed)
        key = "regions " + name
        tally[key] = tally.get(key, 0) + 1
        print(f"  {key} in {time.time() - begun:.1f}s; tally {tally}", flush=True)
        with (out / "digits-first-r5.jsonl").open("a") as f:
            f.write(json.dumps({"digits": digits, "shaded": shade, "regions": name}) + "\n")
        if region:
            n = digits[ROW].index(9)
            finish(digits, shade, region, n, out)
            print(f"straight check {straight([[c for c in CELLS if region[c] == k] for k in range(9)])}", flush=True)
            return
    print(f"budget spent, no grid: {seed} tries, tally {tally}", flush=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "control":
        sys.exit(0 if control(out_dir) else 1)
    run(out_dir)
