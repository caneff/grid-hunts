"""SCRATCH: can the circled 7 be unshaded? Same 133,708 r5 regions, each judged alone.

Counts regions that can be a valid 7 with the circled 7 shaded, unshaded, both or neither,
overall and among those that cannot be a valid 8 (the strict 7). A random sample is
checked against the solver with the circled cell's shading forced. Unshaded means the two
unshaded cells hold the 5 and the 7.
"""

import random
from collections import Counter
from itertools import combinations

from aqre_r5_eight_regions import grow, holds_eight, straight
from aqre_r5_region_max import embed, lines_of
from ortools.sat.python import cp_model

ROW = 4


def seven_ways(cells, root, lines):
    nine = next((x for x in cells if x[0] == ROW and x != root), None)
    fixed = {root: 7, **({nine: 9} if nine else {})}
    shaded_way = unshaded_way = False
    for chosen in combinations(sorted(cells), 7):
        on = root in chosen
        if (on and shaded_way) or (not on and unshaded_way):
            continue
        picked = set(chosen)
        if any(len({x in picked for x in line}) == 1 for line in lines):
            continue
        evens = [x for x in chosen if sum(x) % 2 == 0]
        odds = [x for x in chosen if sum(x) % 2 == 1]
        if len(evens) > 4 or len(odds) > 4:
            continue
        for lows, highs in ((evens, odds), (odds, evens)):
            good = True
            for cell, digit in fixed.items():
                if cell in picked and (digit < 5) != (cell in lows):
                    good = False
            if good and embed(lows, highs, fixed, picked):
                if on:
                    shaded_way = True
                else:
                    unshaded_way = True
                break
        if shaded_way and unshaded_way:
            break
    return shaded_way, unshaded_way


def solver_says(cells, root, want_shaded):
    m = cp_model.CpModel()
    cells = sorted(cells)
    inside = set(cells)
    g = {x: m.new_bool_var("") for x in cells}
    d = {x: {v: m.new_bool_var("") for v in range(1, 10)} for x in cells}
    even_low = m.new_bool_var("even_low")
    m.add(sum(g.values()) == 7)
    m.add(g[root] == int(want_shaded))
    m.add(d[root][7] == 1)
    nine = next((x for x in cells if x[0] == ROW and x != root), None)
    if nine:
        m.add(d[nine][9] == 1)
    for v in range(1, 10):
        m.add_exactly_one(d[x][v] for x in cells)
    for x in cells:
        m.add_exactly_one(d[x].values())
        low = even_low if sum(x) % 2 == 0 else even_low.Not()
        for v in range(1, 10):
            if v == 5:
                m.add_bool_or(g[x].Not(), d[x][v].Not())
            elif v < 5:
                m.add_bool_or(g[x].Not(), d[x][v].Not(), low)
            else:
                m.add_bool_or(g[x].Not(), d[x][v].Not(), low.Not())
        for y in ((x[0], x[1] + 1), (x[0] + 1, x[1])):
            if y in inside:
                for a in range(1, 10):
                    for b in range(1, 10):
                        if abs(a - b) < 5:
                            m.add_bool_or(g[x].Not(), g[y].Not(), d[x][a].Not(), d[y][b].Not())
    for line in lines_of(inside):
        m.add_bool_or(g[x] for x in line)
        m.add_bool_or(g[x].Not() for x in line)
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    return s.solve(m) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def main():
    regions = []
    for c in range(5):
        root = (ROW, c)
        regions += [(x, root) for x in grow(root) if not straight(x)]
    overall = Counter()
    strict = Counter()
    example = None
    rows = []
    for cells, root in regions:
        ways = seven_ways(cells, root, lines_of(cells))
        rows.append((cells, root, ways))
        overall[ways] += 1
        if not holds_eight(cells, root):
            strict[ways] += 1
            if ways == (False, True) and example is None:
                example = sorted(cells), root
    names = {(True, True): "either", (True, False): "shaded only", (False, True): "unshaded only", (False, False): "not a valid 7"}
    print("all regions:", {names[k]: v for k, v in overall.items()}, flush=True)
    print("cannot be a valid 8:", {names[k]: v for k, v in strict.items()}, flush=True)
    print("unshaded-only example, not 8-able:", example, flush=True)
    disagree = 0
    picks = random.Random(5).sample(rows, 300)
    for cells, root, ways in picks:
        disagree += solver_says(cells, root, True) != ways[0]
        disagree += solver_says(cells, root, False) != ways[1]
    print(f"solver cross-check: {len(picks) * 2} checks, {disagree} disagree", flush=True)


if __name__ == "__main__":
    main()
