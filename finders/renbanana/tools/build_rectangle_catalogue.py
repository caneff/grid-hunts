"""Build the chocolate rectangle catalogue for one chocolate difference.

Every legal `a x b` chocolate rectangle (a <= b), enumerated exhaustively. A
filling is legal when orthogonally adjacent cells differ by >= `difference`
and digits are distinct within each row and each column of the rectangle.
Layer L is that and nothing else; layer B keeps, per box offset (ro, co) of the
rectangle's top-left cell mod 3, the fillings with no repeated digit inside one
sudoku box. Per shape and offset it records the count, the per-cell digit
support, the cells that can carry a circle (the digit `area`) and the
lexicographically first filling. See docs/research/renbanana/RECTANGLE-CATALOGUE.md.

At difference 5 the output is byte for byte the committed
`docs/research/renbanana/rectangle-catalogue.json` (#377). Other differences
write `rectangle-catalogue-d<difference>.json` beside it (#760).

Counting every filling of a big shape is millions of fillings per layer at
difference 4, so a layer's enumeration stops at `--count-cap` fillings, except
a shape with both sides <= 4 (`UNCAPPED_SIDE`), which is always enumerated in
full: the banabner finder only places such rectangles, so each of their counts
must be exact (#767). A layer
that hit the cap is `truncated` (`L_truncated`, or `"truncated": true` on a box
offset): its count is a floor, and its support, circle cells and
satisfiability come from CP-SAT instead, which is exact. A layer that finished
under the cap is exact throughout. The cap is never hit at difference 5.

    uv run finders/renbanana/tools/build_rectangle_catalogue.py --difference 4
"""

import argparse
import json
from pathlib import Path

from ortools.sat.python import cp_model

CATALOGUE_DIR = Path(__file__).resolve().parents[3] / "docs/research/renbanana"
DIGITS = range(1, 10)
DEFAULT_COUNT_CAP = 100_000
UNCAPPED_SIDE = 4


def cap_for(a, b, count_cap):
    """The cap for an `a x b` shape: none when both sides are <= UNCAPPED_SIDE."""
    return None if max(a, b) <= UNCAPPED_SIDE else count_cap


def default_max_side(difference):
    """The longest side a rectangle can have in a 9x9 grid.

    From difference 5 up, a 5 cannot sit in a group of two or more, so each
    parity class has four digits and a side tops out at 8 (RECTANGLE-CATALOGUE.md
    § Side bound). Below 5 that argument is gone, and the grid's own 9 is the bound.
    """
    return 8 if difference >= 5 else 9


def default_path(difference):
    name = "rectangle-catalogue" + ("" if difference == 5 else f"-d{difference}")
    return CATALOGUE_DIR / f"{name}.json"


def enumerate_fillings(a, b, difference, offset=None):
    """Yield every legal filling of an `a x b` rectangle, lexicographic order.

    `offset` is (ro, co) for layer B, None for layer L."""
    cells = [(i, j) for i in range(a) for j in range(b)]
    grid = [[0] * b for _ in range(a)]
    box_used = {}

    def box(i, j):
        return ((offset[0] + i) // 3, (offset[1] + j) // 3)

    def walk(k):
        if k == len(cells):
            yield [row[:] for row in grid]
            return
        i, j = cells[k]
        for d in DIGITS:
            if j and (abs(d - grid[i][j - 1]) < difference or d in grid[i][:j]):
                continue
            if i and (
                abs(d - grid[i - 1][j]) < difference
                or any(grid[r][j] == d for r in range(i))
            ):
                continue
            if offset is not None:
                key = (box(i, j), d)
                if key in box_used:
                    continue
                box_used[key] = True
            grid[i][j] = d
            yield from walk(k + 1)
            grid[i][j] = 0
            if offset is not None:
                del box_used[key]

    yield from walk(0)


def cpsat_support(a, b, difference, offset=None):
    """Exact per-cell digit support of one layer, or [] when it is unfillable.

    The same rules as `enumerate_fillings`, as a CP-SAT model: all-different per
    row, column and (layer B) box, and a far-apart disjunction per adjacent
    pair. One feasible solve, then one solve per (cell, digit) it did not
    witness; a solution found marks every digit it holds."""
    m = cp_model.CpModel()
    x = [[m.new_int_var(1, 9, f"x{i}_{j}") for j in range(b)] for i in range(a)]
    for i in range(a):
        m.add_all_different(x[i])
    for j in range(b):
        m.add_all_different([x[i][j] for i in range(a)])
    if offset is not None:
        boxes = {}
        for i in range(a):
            for j in range(b):
                boxes.setdefault(
                    ((offset[0] + i) // 3, (offset[1] + j) // 3), []
                ).append(x[i][j])
        for cells in boxes.values():
            m.add_all_different(cells)
    for i in range(a):
        for j in range(b):
            for ni, nj in ((i, j + 1), (i + 1, j)):
                if ni < a and nj < b:
                    up = m.new_bool_var("")
                    m.add(x[i][j] - x[ni][nj] >= difference).only_enforce_if(up)
                    m.add(x[ni][nj] - x[i][j] >= difference).only_enforce_if(
                        up.negated()
                    )
    lit = {}
    for i in range(a):
        for j in range(b):
            for d in DIGITS:
                lit[i, j, d] = m.new_bool_var("")
                m.add(x[i][j] == d).only_enforce_if(lit[i, j, d])
                m.add(x[i][j] != d).only_enforce_if(lit[i, j, d].negated())
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    seen = [[set() for _ in range(b)] for _ in range(a)]

    def solve(*assumptions):
        m.clear_assumptions()
        for lit_ in assumptions:
            m.add_assumption(lit_)
        status = solver.solve(m)
        assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE), (
            status
        )
        if status == cp_model.INFEASIBLE:
            return False
        for i in range(a):
            for j in range(b):
                seen[i][j].add(solver.value(x[i][j]))
        return True

    if not solve():
        return []
    for i in range(a):
        for j in range(b):
            for d in DIGITS:
                if d not in seen[i][j]:
                    solve(lit[i, j, d])
    return [[sorted(s) for s in row] for row in seen]


def summarise(a, b, difference, offset=None, count_cap=DEFAULT_COUNT_CAP):
    """Layer summary: count, truncated, support, circle cells, first filling.

    `count` is exact unless `truncated`, when it is the cap."""
    area = a * b
    count = 0
    support = [[set() for _ in range(b)] for _ in range(a)]
    example = None
    truncated = False
    for filling in enumerate_fillings(a, b, difference, offset):
        if count_cap is not None and count == count_cap:
            truncated = True
            break
        count += 1
        if example is None:
            example = filling
        for i in range(a):
            for j in range(b):
                support[i][j].add(filling[i][j])
    if truncated:
        support_lists = cpsat_support(a, b, difference, offset)
    else:
        support_lists = [[sorted(s) for s in row] for row in support] if count else []
    circle_cells = (
        [[i, j] for i in range(a) for j in range(b) if area in support_lists[i][j]]
        if support_lists
        else []
    )
    return count, truncated, support_lists, circle_cells, example


def build(difference, max_side, count_cap=DEFAULT_COUNT_CAP):
    catalogue = {}
    for a in range(1, max_side + 1):
        for b in range(a, max_side + 1):
            count_cap_ab = cap_for(a, b, count_cap)
            count, truncated, support, circles, _ = summarise(
                a, b, difference, None, count_cap_ab
            )
            by_offset = {}
            for ro in range(3):
                for co in range(3):
                    if ro + a > 9 or co + b > 9:
                        continue
                    n, cut, sup, circ, ex = summarise(
                        a, b, difference, (ro, co), count_cap_ab
                    )
                    by_offset[f"{ro},{co}"] = {
                        "count": n,
                        "support": sup,
                        "circle_cells": circ,
                        "example": ex,
                    }
                    if cut:
                        by_offset[f"{ro},{co}"]["truncated"] = True
            catalogue[f"{a}x{b}"] = {
                "shape": f"{a}x{b}",
                "area": a * b,
                "L_count": count,
                "L_truncated": truncated,
                "L_support": support,
                "B": by_offset,
                "L_circle_cells": circles,
            }
    return catalogue


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--difference", type=int, default=5)
    ap.add_argument("--max-side", type=int, help="default: 8 from difference 5, else 9")
    ap.add_argument("--count-cap", type=int, default=DEFAULT_COUNT_CAP)
    ap.add_argument(
        "--out", type=Path, help="default: beside the difference-5 catalogue"
    )
    args = ap.parse_args(argv)
    max_side = args.max_side or default_max_side(args.difference)
    out = args.out or default_path(args.difference)
    catalogue = build(args.difference, max_side, args.count_cap)
    out.write_text(json.dumps(catalogue))
    print(f"wrote {out} ({len(catalogue)} shapes, difference {args.difference})")


if __name__ == "__main__":
    main()
