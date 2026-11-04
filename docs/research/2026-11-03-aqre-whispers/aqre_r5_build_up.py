"""SCRATCH: build an r5 grid region by region, 8 down to 1, then the ninth. One worker.

Chris, 2026-11-04: place a valid 8 region in both shading and digits. Then place a valid
7 that cannot itself be a valid 8 but still works with the 8, and so on. A ninth region
that holds r5's uncircled cell has no circle there and may be able to count 8. Both the 8
and the 7 are strict: a region counting 6 or less cannot be a valid 7 or a valid 8, judged
on the region alone, and the 7 region cannot be a valid 8.

Each placement samples a region's cells, then commits the shading and digits the solver
picks for it. The solver's whole-board model holds placed cells fixed and needs a Latin
square with shading, whispers and connectivity, with the free cells shading the remaining
total. That model has no later regions in it, so it is necessary and not sufficient. Local
checks run too: not straight, and free cells that can still split into 9-cell regions.

The ninth region is whatever is left, solved with the regions all known. Randomised
depth-first search with restarts. It samples, so failing says nothing about r5 as a whole.
It stops at the first grid, which the separate reader checks.
"""

import json
import random
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import connected, neighbours
from aqre_jigsaw_r5_staged import finish, read_back
from aqre_r5_eight_regions import holds_eight
from aqre_r5_region_max import holds, lines_of
from connected import add_flow_connectivity
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import sudoku_model

ROW = 4
CHECK_LIMIT = 10.0
FINAL_LIMIT = 30.0
ATTEMPTS = 400
WIDTH = 3
SUBSETS = 30
BUDGET = 3600.0
CELLS = [(r, c) for r in range(9) for c in range(9)]


class State:
    def __init__(self, low_even, n, row=ROW):
        self.low_even = low_even
        self.n = n
        self.row = row
        self.region = {}
        self.digit = {}
        self.shade = {}

    def is_low(self, cell):
        return (sum(cell) % 2 == 0) == self.low_even

    def free(self):
        return [cell for cell in CELLS if cell not in self.region]

    def apply(self, k, assign, shaded):
        for cell, value in assign.items():
            self.region[cell] = k
            self.digit[cell] = value
            self.shade[cell] = cell in shaded

    def undo(self, assign):
        for cell in assign:
            del self.region[cell], self.digit[cell], self.shade[cell]


def lines_ok(st):
    """No 4 in a line of one colour among placed cells; at most 4 per colour per line."""
    for a in range(9):
        for b in range(6):
            for line in ([(a, b + i) for i in range(4)], [(b + i, a) for i in range(4)]):
                if all(x in st.shade for x in line) and len({st.shade[x] for x in line}) == 1:
                    return False
        for house in ([(a, c) for c in range(9)], [(r, a) for r in range(9)]):
            for colour in (0, 1):
                if sum(st.shade.get(x, False) and sum(x) % 2 == colour for x in house) > 4:
                    return False
    return True


def digits_ok(st):
    """Every placed digit against rows, columns, regions, signs and whispers."""
    seen = set()
    for cell, value in st.digit.items():
        for key in (("r", cell[0], value), ("c", cell[1], value), ("k", st.region[cell], value)):
            if key in seen:
                return False
            seen.add(key)
        if st.shade[cell]:
            if value == 5 or (value < 5) != st.is_low(cell):
                return False
            for other in neighbours(cell):
                if st.shade.get(other) and abs(value - st.digit[other]) < 5:
                    return False
    return True


def free_ok(st, roots):
    """Free cells split into components of whole regions with enough room for the roots."""
    left = set(st.free())
    spare = 0
    while left:
        stack, comp = [left.pop()], []
        while stack:
            cell = stack.pop()
            comp.append(cell)
            for other in neighbours(cell):
                if other in left:
                    left.remove(other)
                    stack.append(other)
        if len(comp) % 9:
            return False
        held = sum((st.row, c) in comp for c in roots)
        if held > len(comp) // 9:
            return False
        spare += len(comp) // 9 - held
    return spare == 1


def shaded_can_join(st):
    """Each placed shaded group touches a free cell, or is every shaded cell there will be."""
    left = {cell for cell, on in st.shade.items() if on}
    while left:
        stack, reach = [left.pop()], False
        while stack:
            cell = stack.pop()
            for other in neighbours(cell):
                if other in left:
                    left.remove(other)
                    stack.append(other)
                elif other not in st.region:
                    reach = True
        if not reach:
            return False
    return True


def grow(root, st, rng, may_take_nine):
    cells = {root}
    while len(cells) < 9:
        options = {
            other
            for cell in cells
            for other in neighbours(cell)
            if other not in cells and other not in st.region
            and (other[0] != st.row or (may_take_nine and other == (st.row, st.n)))
        }
        if not options:
            return None
        cells.add(rng.choice(sorted(options)))
    return cells


def assign_digits(cells, shaded, fixed, st, rng):
    placed_row = {r: {st.digit[x] for x in st.digit if x[0] == r} for r in range(9)}
    placed_col = {c: {st.digit[x] for x in st.digit if x[1] == c} for c in range(9)}
    order = sorted(cells, key=lambda x: (x not in fixed, x not in shaded, rng.random()))
    used = set()
    result = {}

    def allowed(cell, value):
        if value in used or value in placed_row[cell[0]] or value in placed_col[cell[1]]:
            return False
        if cell in shaded:
            if value == 5 or (value < 5) != st.is_low(cell):
                return False
            for other in neighbours(cell):
                known = result.get(other) if other in shaded else st.digit.get(other) if st.shade.get(other) else None
                if known is not None and abs(value - known) < 5:
                    return False
        for other, d in result.items():
            if other[0] == cell[0] and d == value or other[1] == cell[1] and d == value:
                return False
        return True

    def place(i):
        if i == len(order):
            return True
        cell = order[i]
        values = [fixed[cell]] if cell in fixed else rng.sample(range(1, 10), 9)
        for value in values:
            if allowed(cell, value):
                result[cell] = value
                used.add(value)
                if place(i + 1):
                    return True
                del result[cell]
                used.remove(value)
        return False

    return dict(result) if place(0) else None


def fill_region(cells, count, root, st, rng):
    """(assign, shaded) sampled for this region, or None."""
    nine = (st.row, st.n) if (st.row, st.n) in cells else None
    fixed = {root: count}
    if nine:
        fixed[nine] = 9
    pool = sorted(cells)
    for _ in range(SUBSETS):
        shaded = set(rng.sample(pool, count))
        colours = sum(sum(x) % 2 for x in shaded)
        if colours > 4 or count - colours > 4:
            continue
        for cell, digit in fixed.items():
            if cell in shaded and (digit == 5 or (digit < 5) != st.is_low(cell)):
                shaded = None
                break
        if shaded is None:
            continue
        assign = assign_digits(cells, shaded, fixed, st, rng)
        if assign:
            return assign, shaded
    return None


def completes(st, remaining):
    """Latin square, shading, whispers and connectivity with placed cells fixed."""
    m, x = sudoku_model(9, None, latin=True)
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    for cell, value in st.digit.items():
        m.add(x[cell] == value)
        m.add(g[cell[0] * 9 + cell[1]] == int(st.shade[cell]))
    m.add(x[st.row, st.n] == 9)
    free = st.free()
    total = sum(g[r * 9 + c] for r, c in free)
    m.add(total >= sum(remaining) + 1)
    m.add(total <= sum(remaining) + 8)
    shared(m, x, g, st)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = CHECK_LIMIT
    return s.status_name(s.solve(m))


def solver_fill(st, count, cells, root, remaining, seed):
    """Shading and digits for this region, chosen so the whole board can still finish.

    Returns (assign, shaded) or None, with the solver status.
    """
    m, x = sudoku_model(9, None, latin=True)
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    for cell, value in st.digit.items():
        m.add(x[cell] == value)
        m.add(g[cell[0] * 9 + cell[1]] == int(st.shade[cell]))
    m.add(x[st.row, st.n] == 9)
    m.add(x[root] == count)
    m.add_all_different(x[cell] for cell in cells)
    m.add(sum(g[r * 9 + c] for r, c in cells) == count)
    free = [cell for cell in st.free() if cell not in cells]
    total = sum(g[r * 9 + c] for r, c in free)
    m.add(total >= sum(remaining) + 1)
    m.add(total <= sum(remaining) + 8)
    shared(m, x, g, st)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = CHECK_LIMIT
    s.parameters.random_seed = seed
    s.parameters.randomize_search = True
    status = s.solve(m)
    name = s.status_name(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, name
    assign = {cell: s.value(x[cell]) for cell in cells}
    shaded = {cell for cell in cells if s.value(g[cell[0] * 9 + cell[1]])}
    return (assign, shaded), name


def shared(m, x, g, st):
    for a in range(9):
        for b in range(6):
            for line in (
                [g[a * 9 + b + i] for i in range(4)],
                [g[(b + i) * 9 + a] for i in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    for r, c in CELLS:
        s = g[r * 9 + c]
        if st.is_low((r, c)):
            m.add(x[r, c] <= 4).only_enforce_if(s)
        else:
            m.add(x[r, c] >= 6).only_enforce_if(s)
        for other in neighbours((r, c)):
            if (r, c) < other:
                t = g[other[0] * 9 + other[1]]
                if st.is_low((r, c)):
                    m.add(x[other] - x[r, c] >= 5).only_enforce_if(s, t)
                else:
                    m.add(x[r, c] - x[other] >= 5).only_enforce_if(s, t)
    add_flow_connectivity(m, g)


def final_solve(st):
    """All regions known: fill the ninth and every free cell."""
    region = dict(st.region)
    for cell in st.free():
        region[cell] = st.n
    regions = [[cell for cell in CELLS if region[cell] == k] for k in range(9)]
    if not connected(regions[st.n]):
        return None
    m, x = sudoku_model(9, None, regions=regions)
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    for cell, value in st.digit.items():
        m.add(x[cell] == value)
        m.add(g[cell[0] * 9 + cell[1]] == int(st.shade[cell]))
    m.add(x[st.row, st.n] == 9)
    total = sum(g[r * 9 + c] for r, c in regions[st.n])
    m.add(total >= 1)
    m.add(total <= 8)
    shared(m, x, g, st)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = FINAL_LIMIT
    if s.solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    return digits, shade, region


class Search:
    def __init__(self, out, rng):
        self.out, self.rng = out, rng
        self.start = time.time()
        self.deepest = 0
        self.reached = {}
        self.checks = {}
        self.found = False

    def left(self):
        return BUDGET - (time.time() - self.start)

    def note(self, st, depth):
        self.reached[depth] = self.reached.get(depth, 0) + 1
        if depth > self.deepest:
            self.deepest = depth
            print(f"deepest {depth} regions placed, {time.time() - self.start:.0f}s, reached {sorted(self.reached.items())}, checks {self.checks}", flush=True)
            (self.out / "build-up-deepest.json").write_text(json.dumps({
                "depth": depth,
                "n": st.n,
                "cells": [[*cell, st.region[cell], st.digit[cell], st.shade[cell]] for cell in sorted(st.region)],
            }))

    def child_ok(self, st, count, cells, root, remaining_roots, remaining_counts):
        for cell in cells:
            st.region[cell] = root[1]
        split = free_ok(st, remaining_roots)
        for cell in cells:
            del st.region[cell]
        if not split:
            return None
        got, name = solver_fill(st, count, cells, root, remaining_counts, self.rng.randrange(1 << 30))
        self.checks[name] = self.checks.get(name, 0) + 1
        if not got:
            return None
        assign, shaded = got
        st.apply(root[1], assign, shaded)
        if lines_ok(st) and digits_ok(st) and shaded_can_join(st):
            return assign
        st.undo(assign)
        self.checks["local refused"] = self.checks.get("local refused", 0) + 1
        return None

    def place(self, st, counts, roots):
        if self.found or self.left() <= 0:
            return
        if not counts:
            grid = final_solve(st)
            self.reached["ninth tried"] = self.reached.get("ninth tried", 0) + 1
            if grid:
                self.found = True
                print(f"grid after {time.time() - self.start:.0f}s, reached {self.reached}", flush=True)
                finish(grid[0], grid[1], grid[2], st.n, self.out)
            return
        count, rest = counts[0], counts[1:]
        tried = kept = 0
        while tried < ATTEMPTS and kept < WIDTH and self.left() > 0 and not self.found:
            tried += 1
            c = self.rng.choice(roots)
            root = (st.row, c)
            cells = grow(root, st, self.rng, may_take_nine=True)
            if not cells or len({y for _, y in cells}) == 1 or len({x for x, _ in cells}) == 1:
                continue
            if holds_eight(cells, root):
                continue
            lines = lines_of(cells)
            if not holds(cells, root, count, lines):
                continue
            if count <= 6 and holds(cells, root, 7, lines):
                continue
            others = [x for x in roots if x != c]
            assign = self.child_ok(st, count, cells, root, others, rest)
            if not assign:
                continue
            kept += 1
            self.note(st, 8 - len(rest))
            self.place(st, rest, others)
            st.undo(assign)

    def restart(self, catalogue):
        entry = self.rng.choice(catalogue)
        cells = {tuple(x) for x in entry["cells"]}
        root = (ROW, entry["column"])
        second = [x for x in cells if x[0] == ROW and x != root]
        columns = [c for c in range(9) if c != root[1]]
        n = second[0][1] if second else self.rng.choice(columns)
        low_even = sum(root) % 2 != 0
        st = State(low_even, n)
        roots = [c for c in columns if c != n]
        assign = self.child_ok(st, 8, cells, root, roots, list(range(1, 8)))
        if not assign:
            return
        self.note(st, 1)
        self.place(st, list(range(7, 0, -1)), roots)


def control(out):
    known = json.loads((out / "grid-8-r1.json").read_text())
    region = {tuple(cell): k for k, cells in enumerate(known["regions"]) for cell in cells}
    digits, shade = known["digits"], known["shaded"]
    n = digits[0].index(9)
    eight = next(k for k, cells in enumerate(known["regions"]) if len(cells) and k != n and sum(shade[r][c] for r, c in cells) == 8)
    root = (0, eight)
    st = State(sum(root) % 2 != 0, n, row=0)
    results = []
    roots = [c for c in range(9) if c != n]
    for k in sorted(roots, key=lambda k: -known["counts"][k]):
        cells = known["regions"][k]
        assign = {tuple(x): digits[x[0]][x[1]] for x in cells}
        st.apply(k, assign, {tuple(x) for x in cells if shade[x[0]][x[1]]})
        local = lines_ok(st), digits_ok(st), shaded_can_join(st)
        roots.remove(k)
        remaining = [known["counts"][j] for j in roots]
        split = free_ok(st, roots)
        name = completes(st, remaining)
        print(f"  count {known['counts'][k]}: local {local}, free {split}, board {name}", flush=True)
        results.extend([*local, split, name != "INFEASIBLE"])
    last = final_solve(st)
    results.append(last is not None)
    print(f"  ninth solved: {last is not None}", flush=True)
    print(f"checks along grid-8-r1, all should hold: {all(results)} of {len(results)}", flush=True)
    bad = State(sum(root) % 2 != 0, n, row=0)
    cells = known["regions"][eight]
    assign = {tuple(x): digits[x[0]][x[1]] for x in cells}
    wrong = sorted(assign)
    assign[wrong[0]], assign[wrong[1]] = assign[wrong[1]], assign[wrong[0]]
    bad.apply(eight, assign, {tuple(x) for x in cells if shade[x[0]][x[1]]})
    refused = not (lines_ok(bad) and digits_ok(bad)) or completes(bad, list(range(1, 8))) == "INFEASIBLE"
    print(f"a swapped-digit 8 region refused: {refused}", flush=True)
    first = State(sum(root) % 2 != 0, n, row=0)
    filled, name = solver_fill(first, 8, {tuple(x) for x in cells}, root, list(range(1, 8)), 1)
    print(f"solver fill of grid-8-r1's 8 region: {name}", flush=True)
    results.append(filled is not None and all(first_ok(first, eight, filled)))
    print("free_ok refuses a single free cell:", not free_ok_probe(), flush=True)
    broken = read_back(digits, shade, region, 0, n)[0]
    print(f"reader: {broken or 'none'}", flush=True)
    ok = all(results) and refused and not broken
    print("controls", "pass" if ok else "FAIL", flush=True)
    return ok


def first_ok(st, k, filled):
    st.apply(k, filled[0], filled[1])
    return lines_ok(st), digits_ok(st), shaded_can_join(st)


def free_ok_probe():
    st = State(True, 0)
    for cell in CELLS:
        if cell != (0, 0):
            st.region[cell] = 0
    return free_ok(st, [])


def main(out):
    catalogue = json.loads((out / "eight-regions-r5.json").read_text())
    rng = random.Random(53)
    search = Search(out, rng)
    restarts = 0
    while search.left() > 0 and not search.found:
        restarts += 1
        search.restart(catalogue)
        if restarts % 200 == 0:
            print(f"restarts {restarts}, {time.time() - search.start:.0f}s, reached {sorted((str(a), b) for a, b in search.reached.items())}, checks {search.checks}", flush=True)
    if not search.found:
        print(f"budget spent, no grid: restarts {restarts}, deepest {search.deepest}, reached {sorted((str(a), b) for a, b in search.reached.items())}, checks {search.checks}", flush=True)


if __name__ == "__main__":
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "control":
        sys.exit(0 if control(out_dir) else 1)
    main(out_dir)
