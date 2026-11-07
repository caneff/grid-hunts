"""SCRATCH: digits 1-9, Aqre shading, 5-whispers on shaded cells, and four circles
in the 2x2 r3c3 r3c4 r4c3 r4c4, where four boxes meet. Each circled digit equals
the number of shaded cells in that cell's own box. Every box has at least one
shaded cell, so all nine boxes hold a valid circle.

`local` solves only boxes 1, 2, 4 and 5 (r1-6, c1-6) with no connectivity: a
relaxation, so its INFEASIBLE settles the question and its grid warm-starts the
full solve as hints.

The four crossings are one case under reflection of the grid.
"""

import json
import os
import sys
from pathlib import Path

from aqre_shaded_whispers_feasible import violations
from connected import add_flow_connectivity
from finders.hunt.render import GridCanvas
from ortools.sat.python import cp_model
from shapes import ORTH
from sudoku_kit.cpsat import boxes, solver, sudoku_model

TIME_LIMIT = 600.0
LOCAL_LIMIT = 120.0
BOXES = [(r, c) for r in (0, 3, 6) for c in (0, 3, 6)]
CIRCLES = [(2, 2), (2, 3), (3, 2), (3, 3)]


def box_of(r, c):
    br, bc = r // 3 * 3, c // 3 * 3
    return [(i, j) for i in range(br, br + 3) for j in range(bc, bc + 3)]


def build():
    m, x = sudoku_model(9, boxes(9, 3, 3))
    g = [m.new_bool_var(f"g{i}") for i in range(81)]
    add_flow_connectivity(m, g)
    shaded = lambda r, c: g[r * 9 + c]
    for a in range(9):
        for b in range(6):
            for line in (
                [shaded(a, b + k) for k in range(4)],
                [shaded(b + k, a) for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    even_low = m.new_bool_var("even_low")
    for r in range(9):
        for c in range(9):
            low = even_low if (r + c) % 2 == 0 else even_low.Not()
            m.add(x[r, c] <= 4).only_enforce_if(shaded(r, c), low)
            m.add(x[r, c] >= 6).only_enforce_if(shaded(r, c), low.Not())
    for i in range(81):
        for j in ORTH[i]:
            if i < j:
                gap = m.new_int_var(0, 8, f"gap{i}_{j}")
                m.add_abs_equality(gap, x[i // 9, i % 9] - x[j // 9, j % 9])
                m.add(gap >= 5).only_enforce_if(g[i], g[j])
    for r, c in CIRCLES:
        m.add(x[r, c] == sum(shaded(i, j) for i, j in box_of(r, c)))
    for br, bc in BOXES:
        count = sum(shaded(i, j) for i, j in box_of(br, bc))
        m.add(count >= 1)
        m.add(count <= 7)  # redundant: no box holds 8 whisper cells at a gap of 5
    return m, x, g


def local():
    """Boxes around the crossing alone. Nothing here is proved beyond these cells."""
    m = cp_model.CpModel()
    cells = [(r, c) for r in range(6) for c in range(6)]
    x = {cell: m.new_int_var(1, 9, f"x{cell}") for cell in cells}
    g = {cell: m.new_bool_var(f"g{cell}") for cell in cells}
    for i in range(6):
        m.add_all_different(x[i, j] for j in range(6))
        m.add_all_different(x[j, i] for j in range(6))
    for br in (0, 3):
        for bc in (0, 3):
            box = box_of(br, bc)
            m.add_all_different(x[cell] for cell in box)
            count = sum(g[cell] for cell in box)
            m.add(count >= 1)
            m.add(count <= 7)
    for a in range(6):
        for b in range(3):
            for line in (
                [g[a, b + k] for k in range(4)],
                [g[b + k, a] for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    for r, c in cells:
        for rr, cc in ((r, c + 1), (r + 1, c)):
            if rr < 6 and cc < 6:
                gap = m.new_int_var(0, 8, f"gap{r}{c}{rr}{cc}")
                m.add_abs_equality(gap, x[r, c] - x[rr, cc])
                m.add(gap >= 5).only_enforce_if(g[r, c], g[rr, cc])
    for r, c in CIRCLES:
        m.add(x[r, c] == sum(g[cell] for cell in box_of(r, c)))
    return m, x, g


def circle_errors(digits, shade):
    return [
        f"circle r{r + 1}c{c + 1}: digit {digits[r][c]}, box count "
        f"{sum(shade[i][j] for i, j in box_of(r, c))}"
        for r, c in CIRCLES
        if digits[r][c] != sum(shade[i][j] for i, j in box_of(r, c))
    ]


def main(out_dir):
    lm, lx, lg = local()
    ls = solver(LOCAL_LIMIT)
    lstatus = ls.solve(lm)
    print(f"local: status {ls.status_name(lstatus)} in {ls.wall_time:.1f}s", flush=True)
    if lstatus == cp_model.INFEASIBLE:
        return 0
    m, x, g = build()
    if lstatus in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (r, c), var in lx.items():
            m.add_hint(x[r, c], ls.value(var))
            m.add_hint(g[r * 9 + c], ls.value(lg[r, c]))
        print("local:", [
            f"r{r + 1}c{c + 1}={ls.value(lx[r, c])}" for r, c in CIRCLES
        ], flush=True)
    s = solver(TIME_LIMIT)
    status = s.solve(m)
    print(f"status {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 0
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    wrong = [row[:] for row in digits]
    r, c = CIRCLES[0]
    wrong[r][c] = wrong[r][c] % 9 + 1
    assert circle_errors(wrong, shade), "circle control did not fire"
    broken = violations(digits, shade) + circle_errors(digits, shade)
    print(f"reader violations {broken or 'none'} (circle control fired)", flush=True)
    print("\n".join(
        " ".join(("#" if shade[i][j] else ".") + str(digits[i][j]) for j in range(9))
        for i in range(9)
    ), flush=True)
    print("circled", [f"r{r + 1}c{c + 1}={digits[r][c]}" for r, c in CIRCLES], flush=True)
    print("shaded total", sum(map(sum, shade)), flush=True)
    for br, bc in BOXES:
        box = box_of(br, bc)
        count = sum(shade[i][j] for i, j in box)
        spot = [f"r{i + 1}c{j + 1}" for i, j in box if digits[i][j] == count]
        print(f"box r{br + 1}c{bc + 1}: count {count}, circle {spot}", flush=True)

    canvas = GridCanvas(9, 9, cell=64, margin=24)
    for i in range(9):
        for j in range(9):
            if shade[i][j]:
                canvas.shade_cell(i, j, "#b8b8b8")
    for r, c in CIRCLES:
        canvas.circle(r, c, color="#c0392b", width=4)
    for i in range(9):
        for j in range(9):
            canvas.digit(i, j, digits[i][j])
    canvas.box_lines(3, 3, thin=1, thick=5)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "grid-4.json").write_text(json.dumps({"digits": digits, "shaded": shade}))
    temp = out / "grid-4.tmp.png"
    canvas.image.save(temp)
    os.replace(temp, out / "grid-4.png")
    print("picture", out / "grid-4.png", flush=True)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
