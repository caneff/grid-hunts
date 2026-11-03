"""SCRATCH: test the INFEASIBLE from aqre_disjoint_feasible.py.

control   first model without the different-counts rule: must find a grid.
shape     no digits or whispers: connected, no 4 in a line, counts a
          permutation of 0-8. Says whether the shading alone is the cause.
second    the whole rule set in a model sharing no encoding with the first:
          one-hot digits, whispers as clauses, no orientation variable, level
          based connectivity, one-hot box counts, no redundant total.
"""

import aqre_disjoint_feasible as first
from ortools.sat.python import cp_model
from sudoku_kit.cpsat import solver

LIMITS = {"control": 300.0, "shape": 300.0, "second": 900.0}
CELLS = [(r, c) for r in range(9) for c in range(9)]
STEPS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def neighbours(cell):
    for dr, dc in STEPS:
        r, c = cell[0] + dr, cell[1] + dc
        if 0 <= r < 9 and 0 <= c < 9:
            yield r, c


def boxes():
    return [
        [(r, c) for r in range(br, br + 3) for c in range(bc, bc + 3)]
        for br, bc in first.BOXES
    ]


def shading(m):
    """Shade booleans, four-in-a-line and level-based connectivity."""
    g = {cell: m.new_bool_var(f"s{cell}") for cell in CELLS}
    for a in range(9):
        for b in range(6):
            for line in (
                [g[a, b + k] for k in range(4)],
                [g[b + k, a] for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    level = {cell: m.new_int_var(0, 80, f"l{cell}") for cell in CELLS}
    root = {cell: m.new_bool_var(f"root{cell}") for cell in CELLS}
    m.add_exactly_one(root.values())
    for cell in CELLS:
        m.add_implication(root[cell], g[cell])
        m.add(level[cell] == 0).only_enforce_if(root[cell])
        parents = []
        for other in neighbours(cell):
            parent = m.new_bool_var(f"p{cell}{other}")
            m.add_implication(parent, g[other])
            m.add(level[cell] == level[other] + 1).only_enforce_if(parent)
            parents.append(parent)
        m.add_bool_or(parents + [g[cell].Not(), root[cell]])
    return g


def permutation_counts(m, g):
    chosen = [[m.new_bool_var(f"c{b}_{k}") for k in range(9)] for b in range(9)]
    for b, box in enumerate(boxes()):
        m.add_exactly_one(chosen[b])
        m.add(sum(g[cell] for cell in box) == sum(k * chosen[b][k] for k in range(9)))
    for k in range(9):
        m.add_exactly_one(chosen[b][k] for b in range(9))


def shape_model():
    m = cp_model.CpModel()
    g = shading(m)
    permutation_counts(m, g)
    return m, g, None


def second_model():
    m = cp_model.CpModel()
    g = shading(m)
    permutation_counts(m, g)
    d = {cell: [m.new_bool_var(f"d{cell}{v}") for v in range(9)] for cell in CELLS}
    for cell in CELLS:
        m.add_exactly_one(d[cell])
    houses = (
        [[(i, j) for j in range(9)] for i in range(9)]
        + [[(j, i) for j in range(9)] for i in range(9)]
        + boxes()
    )
    for house in houses:
        for v in range(9):
            m.add_exactly_one(d[cell][v] for cell in house)
    for cell in CELLS:
        for other in neighbours(cell):
            if cell < other:
                for a in range(9):
                    for b in range(9):
                        if abs(a - b) < 5:
                            m.add_bool_or(
                                g[cell].Not(), g[other].Not(),
                                d[cell][a].Not(), d[other][b].Not(),
                            )
    return m, g, d


def report(name, m):
    s = solver(LIMITS[name])
    status = s.solve(m)
    print(f"{name}: status {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
    return s, status


def main():
    m, x, g = first.build("none", distinct=False)
    s, status = report("control", m)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        digits = [[s.value(x[r, c]) - 1 for c in range(9)] for r in range(9)]
        shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
        rest = [v for v in first.violations(digits, shade, "none") if "box counts" not in v]
        counts = [sum(shade[r][c] for r, c in box) for box in boxes()]
        print(f"control: reader violations {rest or 'none'}; box counts {counts}", flush=True)

    m, g, _ = shape_model()
    s, status = report("shape", m)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("\n".join(
            "".join("#" if s.value(g[r, c]) else "." for c in range(9)) for r in range(9)
        ), flush=True)
        print("shape counts", [sum(s.value(g[cell]) for cell in box) for box in boxes()], flush=True)

    m, g, d = second_model()
    s, status = report("second", m)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        digits = [[next(v for v in range(9) if s.value(d[r, c][v])) for c in range(9)] for r in range(9)]
        shade = [[bool(s.value(g[r, c])) for c in range(9)] for r in range(9)]
        print("second: FOUND A GRID", digits, shade, first.violations(digits, shade, "distinct"), flush=True)


if __name__ == "__main__":
    main()
