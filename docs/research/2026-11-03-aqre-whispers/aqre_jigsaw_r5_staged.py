"""SCRATCH: 8 circles in r5 of a jigsaw sudoku, solved in two stages.

Stage one chooses regions and connected shading with no digits: Aqre shading, the
eight r5 regions counting 1-8, no straight region. Stage two fixes those and fills
digits and 5-whispers on shaded cells. A failed fill rules out only that layout, so
this can find a grid and cannot prove there is none. It stops at the first grid.

Stage one holds what digits would force, so fewer layouts fail the fill:
- Shaded cells alternate low (1-4) and high (6-9) by checkerboard colour, so a row,
  column or region holds at most 4 shaded cells of each colour.
- A shaded r5 cell's digit, known from its count, must suit its colour; a 5 is
  never shaded; shaded r5 neighbours differ by at least 5.
- Flipping the grid top to bottom keeps every rule and r5, so the top half holds at
  least as many shaded cells as the bottom half.

`control DIR` runs the known grid-8-r1 through both stages, plus one layout each
stage must refuse. `trial DIR` is 90 s of stage one. `run DIR` runs stage one in turn
over the 9's columns, then falls back on the plain model for a long solve of the 9 in
r5c5.
"""

import json
import sys
import time
from pathlib import Path

import aqre_jigsaw_r5 as plain
from aqre_jigsaw_feasible import connected, controls, draw, neighbours, violations
from connected import add_flow_connectivity
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver as base_solver
from sudoku_kit.cpsat import sudoku_model

WORKERS = 8
LAYOUT_LIMIT = 900.0
FILL_LIMIT = 120.0
STAGED_BUDGET = 4 * 3600.0
PLAIN_LIMIT = 2 * 3600.0
CELLS = [(r, c) for r in range(9) for c in range(9)]


def solver(limit, seed):
    s = base_solver(limit, reproducible=False, seed=seed, randomize=True)
    s.parameters.num_workers = WORKERS
    return s


def build_layout(row, n, straight_ok=False, flip_cut=True):
    m = cp_model.CpModel()
    y = {cell: [m.new_bool_var(f"y{cell}{k}") for k in range(9)] for cell in CELLS}
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    shaded = lambda r, c: g[r * 9 + c]
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

    count = []
    for k in range(9):
        m.add(sum(y[cell][k] for cell in CELLS) == 9)
        terms = {}
        for cell in CELLS:
            w = m.new_bool_var(f"w{cell}{k}")
            m.add_implication(w, y[cell][k])
            m.add_implication(w, shaded(*cell))
            m.add_bool_or(w, y[cell][k].Not(), shaded(*cell).Not())
            terms[cell] = w
        total = m.new_int_var(1, 8, f"count{k}")
        m.add(total == sum(terms.values()))
        count.append(total)
        for colour in (0, 1):
            m.add(sum(w for (r, c), w in terms.items() if (r + c) % 2 == colour) <= 4)
    m.add_all_different(count[k] for k in range(9) if k != n)

    for a in range(9):
        for colour in (0, 1):
            m.add(sum(shaded(a, c) for c in range(9) if (a + c) % 2 == colour) <= 4)
            m.add(sum(shaded(r, a) for r in range(9) if (r + a) % 2 == colour) <= 4)
        for b in range(6):
            for line in (
                [shaded(a, b + k) for k in range(4)],
                [shaded(b + k, a) for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    if not straight_ok:
        for k in range(9):
            for a in range(9):
                m.add(sum(y[a, c][k] for c in range(9)) <= 8)
                m.add(sum(y[r, a][k] for r in range(9)) <= 8)

    even_low = m.new_bool_var("even_low")
    low = [even_low if (row + c) % 2 == 0 else even_low.Not() for c in range(9)]
    value = [9 if c == n else count[c] for c in range(9)]
    for c in range(9):
        s = shaded(row, c)
        m.add(value[c] <= 4).only_enforce_if(s, low[c])
        m.add(value[c] >= 6).only_enforce_if(s, low[c].Not())
    for c in range(8):
        both = [shaded(row, c), shaded(row, c + 1)]
        m.add(value[c + 1] - value[c] >= 5).only_enforce_if(*both, low[c])
        m.add(value[c] - value[c + 1] >= 5).only_enforce_if(*both, low[c].Not())

    if flip_cut:
        m.add(
            sum(shaded(r, c) for r in range(row) for c in range(9))
            >= sum(shaded(r, c) for r in range(row + 1, 9) for c in range(9))
        )
    add_flow_connectivity(m, g)
    return m, y, g


def fill(region, shade, row, n, seed):
    """Digits for fixed regions and shading: (status name, digits or None)."""
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    m, x = sudoku_model(9, None, regions=regions)
    even_low = m.new_bool_var("even_low")
    for c in range(9):
        m.add(x[row, c] == (9 if c == n else sum(shade[a][b] for a, b in regions[c])))
    for r, c in CELLS:
        if not shade[r][c]:
            continue
        low = even_low if (r + c) % 2 == 0 else even_low.Not()
        m.add(x[r, c] <= 4).only_enforce_if(low)
        m.add(x[r, c] >= 6).only_enforce_if(low.Not())
        for other in neighbours((r, c)):
            if shade[other[0]][other[1]]:
                m.add(x[other] - x[r, c] >= 5).only_enforce_if(low)
    s = solver(FILL_LIMIT, seed)
    status = s.solve(m)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return s.status_name(status), [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    return s.status_name(status), None


def read_back(digits, shade, region, row, n):
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    controls(digits, shade, regions)
    broken = violations(digits, shade, regions)
    broken += [
        f"region {k} split" for k, cells in enumerate(regions) if not connected(cells) or len(cells) != 9
    ]
    counts = [sum(shade[r][c] for r, c in cells) for cells in regions]
    if digits[row][n] != 9:
        broken.append("the uncircled cell is not the 9")
    broken += [
        f"column {c + 1}: digit {digits[row][c]}, region count {counts[c]}"
        for c in range(9)
        if c != n and digits[row][c] != counts[c]
    ]
    if len({region[row, c] for c in range(9) if c != n}) != 8:
        broken.append("circles not in 8 regions")
    return broken, regions, counts


def straight(regions):
    return sum(len({c for _, c in x}) == 1 or len({r for r, _ in x}) == 1 for x in regions)


def staged(out, budget, layout_limit):
    start = time.time()
    forbidden = {n: [] for n in (4, 3, 2, 1, 0)}
    seed = 0
    tries = fills = 0
    log = out / "layouts-r5.jsonl"
    while time.time() - start < budget:
        n = (4, 3, 2, 1, 0)[seed % 5]
        seed += 1
        m, y, g = build_layout(4, n)
        for shade_old, region_old in forbidden[n]:
            m.add_bool_or(
                [g[r * 9 + c].Not() if shade_old[r][c] else g[r * 9 + c] for r, c in CELLS]
                + [y[cell][region_old[cell]].Not() for cell in CELLS]
            )
        s = solver(min(layout_limit, budget - (time.time() - start)), seed)
        status = s.solve(m)
        tries += 1
        print(f"try {tries}, 9 in r5c{n + 1}: layout {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            continue
        shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
        region = {cell: next(k for k in range(9) if s.value(y[cell][k])) for cell in CELLS}
        name, digits = fill(region, shade, 4, n, seed)
        fills += 1
        print(f"  fill {name}, shaded {sum(map(sum, shade))}", flush=True)
        with log.open("a") as f:
            f.write(json.dumps({
                "n": n,
                "fill": name,
                "shaded": shade,
                "region": [[region[r, c] for c in range(9)] for r in range(9)],
            }) + "\n")
        if digits:
            return finish(digits, shade, region, n, out)
        forbidden[n].append((shade, region))
    print(f"staged budget spent: {tries} layout solves, {fills} fills, no grid", flush=True)
    return False


def finish(digits, shade, region, n, out):
    broken, regions, counts = read_back(digits, shade, region, 4, n)
    print(f"FOUND. reader violations {broken or 'none'} (controls fired)", flush=True)
    print(f"straight regions {straight(regions)} of 9", flush=True)
    print("\n".join("".join(str(region[r, c]) for c in range(9)) for r in range(9)), flush=True)
    print("\n".join(
        " ".join(("#" if shade[i][j] else ".") + str(digits[i][j]) for j in range(9))
        for i in range(9)
    ), flush=True)
    print(f"region counts by r5 column {counts}, shaded total {sum(counts)}", flush=True)
    spots = [(4, c) for c in range(9) if c != n]
    ninth = next((x for x in regions[n] if digits[x[0]][x[1]] == counts[n] and x[0] != 4), None)
    if ninth:
        spots.append(ninth)
    print(f"ninth region circle {ninth}", flush=True)
    (out / "grid-9-r5.json").write_text(json.dumps({
        "digits": digits, "shaded": shade, "regions": regions, "counts": counts,
    }))
    draw(digits, shade, region, spots, out / "grid-9-r5.png")
    print("picture", out / "grid-9-r5.png", flush=True)
    return not broken


def control(out):
    """The known grid through both stages, with one refusal each."""
    known = json.loads((out / "grid-8-r1.json").read_text())
    shade = known["shaded"]
    region = {tuple(cell): k for k, cells in enumerate(known["regions"]) for cell in cells}
    n = 4
    m, y, g = build_layout(0, n, straight_ok=True, flip_cut=False)
    for r, c in CELLS:
        m.add(g[r * 9 + c] == int(shade[r][c]))
        m.add(y[r, c][region[r, c]] == 1)
    s = solver(120.0, 1)
    first = s.status_name(s.solve(m))
    print(f"layout model holds grid-8-r1: {first}", flush=True)
    m, y, g = build_layout(0, n, straight_ok=True, flip_cut=False)
    for c in range(0, 9, 2):
        m.add(g[c] == 1)
    s = solver(120.0, 1)
    second = s.status_name(s.solve(m))
    print(f"layout model with 5 shaded of one colour in r1: {second}", flush=True)
    name, digits = fill(region, shade, 0, n, 1)
    print(f"fill of grid-8-r1's layout: {name}", flush=True)
    broken = read_back(digits, shade, region, 0, n)[0] if digits else ["no fill"]
    print(f"reader on that fill: {broken or 'none'}", flush=True)
    bad = [row[:] for row in shade]
    bad[3] = [True] * 9
    name2, _ = fill(region, bad, 0, n, 1)
    print(f"fill with a fully shaded r4: {name2}", flush=True)
    ok = first in ("OPTIMAL", "FEASIBLE") and second == "INFEASIBLE" and not broken and name2 == "INFEASIBLE"
    print("controls", "pass" if ok else "FAIL", flush=True)
    return ok


def run(out):
    if staged(out, STAGED_BUDGET, LAYOUT_LIMIT):
        print("stage solve found a grid; the long plain solve is skipped", flush=True)
        return
    print("long plain solve: 9 in r5c5", flush=True)
    plain.TIME_LIMIT = PLAIN_LIMIT
    plain.attempt(4, str(out))


if __name__ == "__main__":
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "control":
        sys.exit(0 if control(out_dir) else 1)
    if sys.argv[1] == "trial":
        staged(out_dir, 90.0, 90.0)
        sys.exit(0)
    run(out_dir)
