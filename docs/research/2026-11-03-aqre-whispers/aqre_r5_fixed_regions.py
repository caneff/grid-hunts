"""SCRATCH: 8 circles in r5 on fixed jigsaw regions, one worker.

Layouts come from the border-swap walk in jigsaw_r5_diversity, kept only with no
straight region. Exactly eight regions touch r5, so one region holds two r5 cells: one
is circled, the other is the 9. Each such choice is a case, `n`.

For each case:
1. Region filter: which counts can each region hold alone, with its own digits, signs,
   whispers and runs of 4? The eight r5 regions must take 1-8 between them.
2. Solve without shaded connectivity. Infeasible ends the case.
3. Solve with flow connectivity, warm-started from step 2.

It samples layouts, so a layout failing says nothing about r5 as a whole. It stops at
the first grid. `control DIR` tests the filter and full model on the known grid-8-r1.
"""

import json
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_r5_staged import finish, read_back
from aqre_jigsaw_feasible import neighbours
from connected import add_flow_connectivity
from jigsaw_r5_diversity import measure, touches, walk
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import sudoku_model

ROW = 4
SEEDS = range(6)
WALK_SECONDS = 20.0
RELAX_LIMIT = 30.0
FULL_LIMIT = 180.0
BUDGET = 1800.0
CELLS = [(r, c) for r in range(9) for c in range(9)]


def one_worker(limit):
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = limit
    return s


def region_holds(cells, count, fixed):
    """Can this region alone hold `count` shaded cells? `fixed` maps cell to digit."""
    m = cp_model.CpModel()
    inside = set(cells)
    g = {cell: m.new_bool_var(f"g{cell}") for cell in cells}
    d = {cell: {v: m.new_bool_var(f"d{cell}{v}") for v in range(1, 10)} for cell in cells}
    even_low = m.new_bool_var("even_low")
    m.add(sum(g.values()) == count)
    for v in range(1, 10):
        m.add_exactly_one(d[cell][v] for cell in cells)
    for cell, digit in fixed.items():
        m.add(d[cell][digit] == 1)
    for cell in cells:
        m.add_exactly_one(d[cell].values())
        low = even_low if sum(cell) % 2 == 0 else even_low.Not()
        m.add_bool_or(g[cell].Not(), d[cell][5].Not())
        for v in range(1, 10):
            if v < 5:
                m.add_bool_or(g[cell].Not(), d[cell][v].Not(), low)
            if v > 5:
                m.add_bool_or(g[cell].Not(), d[cell][v].Not(), low.Not())
        for other in neighbours(cell):
            if other in inside and cell < other:
                for a in range(1, 10):
                    for b in range(1, 10):
                        if abs(a - b) < 5:
                            m.add_bool_or(g[cell].Not(), g[other].Not(), d[cell][a].Not(), d[other][b].Not())
        r, c = cell
        for line in ([(r, c + i) for i in range(4)], [(r + i, c) for i in range(4)]):
            if all(x in inside for x in line):
                m.add_bool_or(g[x] for x in line)
                m.add_bool_or(g[x].Not() for x in line)
    return one_worker(10.0).solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def can_match(options):
    """Do these option sets admit distinct picks, one each?"""
    owner = {}

    def place(i, seen):
        for value in options[i]:
            if value not in seen:
                seen.add(value)
                if value not in owner or place(owner[value], seen):
                    owner[value] = i
                    return True
        return False

    return all(place(i, set()) for i in range(len(options)))


def relabel(region, row, n):
    """Region indices with k the region of `row` column k, and n the leftover."""
    mapping = {region[row, c]: c for c in range(9) if c != n}
    leftover = next(k for k in range(9) if k not in mapping)
    mapping[leftover] = n
    return {cell: mapping[k] for cell, k in region.items()}


def region_filter(region, row, n):
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    options = []
    for c in range(9):
        if c == n:
            continue
        fixed = {(row, x): 9 for x in [n] if (row, x) in regions[c]}
        held = []
        for count in range(1, 9):
            if region_holds(regions[c], count, {**fixed, (row, c): count}):
                held.append(count)
        options.append(held)
    return can_match(options), options


def build(region, row, n, connect, circles=True):
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    m, x = sudoku_model(9, regions)
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    shaded = lambda r, c: g[r * 9 + c]
    even_low = m.new_bool_var("even_low")
    m.add(x[row, n] == 9)
    for k, cells in enumerate(regions):
        total = sum(shaded(*cell) for cell in cells)
        m.add(total >= 1)
        m.add(total <= 8)
        if k != n and circles:
            m.add(x[row, k] == total)
        for colour in (0, 1):
            m.add(sum(shaded(r, c) for r, c in cells if (r + c) % 2 == colour) <= 4)
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
    if connect:
        add_flow_connectivity(m, g)
    return m, x, g


def attempt(region, row, n, hint=None):
    """(outcome, digits, shade), with outcome naming the step that ended the case."""
    rm, rx, rg = build(region, row, n, False)
    if hint:
        for r, c in CELLS:
            rm.add_hint(rx[r, c], hint["digits"][r][c])
            rm.add_hint(rg[r * 9 + c], int(hint["shaded"][r][c]))
    rs = one_worker(RELAX_LIMIT)
    rstatus = rs.solve(rm)
    print(f"  no connectivity: {rs.status_name(rstatus)} in {rs.wall_time:.1f}s", flush=True)
    if rstatus == cp_model.INFEASIBLE:
        return "relaxed infeasible", None, None
    m, x, g = build(region, row, n, True)
    if rstatus in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for r, c in CELLS:
            m.add_hint(x[r, c], rs.value(rx[r, c]))
            m.add_hint(g[r * 9 + c], rs.value(rg[r * 9 + c]))
    s = one_worker(FULL_LIMIT)
    status = s.solve(m)
    print(f"  full: {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
        shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
        return "found", digits, shade
    return f"full {s.status_name(status)}", None, None


def control(out):
    known = json.loads((out / "grid-8-r1.json").read_text())
    region = {tuple(cell): k for k, cells in enumerate(known["regions"]) for cell in cells}
    n = 4
    passed, options = region_filter(region, 0, n)
    print(f"filter on grid-8-r1: {passed}, {options}", flush=True)
    column = [(r, 0) for r in range(9)]
    eight = region_holds(column, 8, {})
    seven = region_holds(column, 7, {})
    print(f"a straight column holds 8: {eight}, holds 7: {seven}", flush=True)
    outcome, digits, shade = attempt(region, 0, n, hint=known)
    print(f"full model on grid-8-r1's regions: {outcome}", flush=True)
    broken = read_back(digits, shade, region, 0, n)[0] if digits else ["no grid"]
    print(f"reader: {broken or 'none'}", flush=True)
    refused = kept = 0
    for line in (out / "layouts-r5.jsonl").read_text().splitlines():
        old = json.loads(line)
        layout = relabel({cell: old["region"][cell[0]][cell[1]] for cell in CELLS}, ROW, old["n"])
        if region_filter(layout, ROW, old["n"])[0]:
            kept += 1
        else:
            refused += 1
    print(f"filter on the 15 failed layouts: {refused} refused, {kept} kept", flush=True)
    ok = passed and seven and not eight and outcome == "found" and not broken
    print("controls", "pass" if ok else "FAIL", flush=True)
    return ok


def run(out):
    start = time.time()
    pools = []
    for seed in SEEDS:
        rng = random.Random(seed + 100)
        found = [x for x in walk(seed, WALK_SECONDS) if measure(x)["straight"] == 0]
        rng.shuffle(found)
        pools.append(found)
        print(f"seed {seed}: {len(found)} layouts with no straight region", flush=True)
    tally = {}
    seen = 0
    while time.time() - start < BUDGET and any(pools):
        for pool in pools:
            if not pool or time.time() - start >= BUDGET:
                continue
            region = pool.pop()
            assert touches(region) == 8
            pair = [
                c for c in range(9)
                if sum(region[ROW, x] == region[ROW, c] for x in range(9)) == 2
            ]
            for n in pair:
                seen += 1
                layout = relabel(region, ROW, n)
                passed, options = region_filter(layout, ROW, n)
                if not passed:
                    tally["filter refused"] = tally.get("filter refused", 0) + 1
                    continue
                print(f"case {seen}, 9 in r5c{n + 1}: filter passed, {time.time() - start:.0f}s", flush=True)
                outcome, digits, shade = attempt(layout, ROW, n)
                tally[outcome] = tally.get(outcome, 0) + 1
                print(f"  tally {tally}", flush=True)
                with (out / "fixed-r5.jsonl").open("a") as f:
                    f.write(json.dumps({
                        "n": n,
                        "outcome": outcome,
                        "region": [[layout[r, c] for c in range(9)] for r in range(9)],
                    }) + "\n")
                if digits:
                    finish(digits, shade, layout, n, out)
                    print(f"cases {seen}, tally {tally}", flush=True)
                    return
    print(f"budget spent, no grid: cases {seen}, tally {tally}", flush=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "control":
        sys.exit(0 if control(out_dir) else 1)
    run(out_dir)
