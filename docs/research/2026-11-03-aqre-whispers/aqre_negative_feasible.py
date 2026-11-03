"""SCRATCH: digits 1-9, Aqre shading, adjacent shaded cells differ by at least 5,
and the negative rule: adjacent unshaded cells differ by at most 4. A mixed pair
is free. Every box has a shaded cell, so all nine boxes hold a valid circle.
"""

import json
import os
import sys
from itertools import combinations
from pathlib import Path

from aqre_shaded_whispers_feasible import violations
from connected import add_flow_connectivity
from finders.hunt.render import GridCanvas
from ortools.sat.python import cp_model
from shapes import ORTH
from sudoku_kit.cpsat import solver, sudoku_model

TIME_LIMIT = 300.0
BOXES = [(r, c) for r in (0, 3, 6) for c in (0, 3, 6)]


def box_of(r, c):
    br, bc = r // 3 * 3, c // 3 * 3
    return [(i, j) for i in range(br, br + 3) for j in range(bc, bc + 3)]


def one_box_table():
    """For each shaded count, how many layouts of one box can take digits 1-9."""
    cells = [(r, c) for r in range(3) for c in range(3)]
    adjacent = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1

    def fits(mask):
        placed = {}

        def go(i, used):
            if i == 9:
                return True
            cell = cells[i]
            for d in range(1, 10):
                if d in used:
                    continue
                good = True
                for other, value in placed.items():
                    if adjacent(cell, other) and (cell in mask) == (other in mask):
                        far = abs(d - value) >= 5
                        if far != (cell in mask):
                            good = False
                            break
                if good:
                    placed[cell] = d
                    if go(i + 1, used | {d}):
                        return True
                    del placed[cell]
            return False

        return go(0, frozenset())

    for k in range(10):
        masks = list(combinations(cells, k))
        print(f"one box, {k} shaded: {sum(fits(set(m)) for m in masks)} of {len(masks)} layouts", flush=True)


def build():
    m, x = sudoku_model(9, (3, 3))
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
                m.add(gap <= 4).only_enforce_if(g[i].Not(), g[j].Not())
    for br, bc in BOXES:
        count = sum(shaded(i, j) for i, j in box_of(br, bc))
        m.add(count >= 1)
    return m, x, g


def negative_errors(digits, shade):
    found = []
    for r in range(9):
        for c in range(9):
            for rr, cc in ((r, c + 1), (r + 1, c)):
                if rr < 9 and cc < 9 and not shade[r][c] and not shade[rr][cc]:
                    if abs(digits[r][c] - digits[rr][cc]) > 4:
                        found.append(f"unshaded far r{r + 1}c{c + 1}-r{rr + 1}c{cc + 1}")
    return found


def main(out_dir):
    one_box_table()
    m, x, g = build()
    s = solver(TIME_LIMIT)
    status = s.solve(m)
    print(f"status {s.status_name(status)} in {s.wall_time:.1f}s", flush=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 0
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    apart = [[1, 9] + [0] * 7] + [[0] * 9 for _ in range(8)]
    assert negative_errors(apart, [[False] * 9 for _ in range(9)]), "negative control"
    broken = violations(digits, shade) + negative_errors(digits, shade)
    print(f"reader violations {broken or 'none'} (negative control fired)", flush=True)
    print("\n".join(
        " ".join(("#" if shade[i][j] else ".") + str(digits[i][j]) for j in range(9))
        for i in range(9)
    ), flush=True)
    print("shaded total", sum(map(sum, shade)), flush=True)
    canvas = GridCanvas(9, 9, cell=64, margin=24)
    for i in range(9):
        for j in range(9):
            if shade[i][j]:
                canvas.shade_cell(i, j, "#b8b8b8")
    for br, bc in BOXES:
        box = box_of(br, bc)
        count = sum(shade[i][j] for i, j in box)
        spot = next(cell for cell in box if digits[cell[0]][cell[1]] == count)
        print(f"box r{br + 1}c{bc + 1}: count {count}, circle r{spot[0] + 1}c{spot[1] + 1}", flush=True)
        canvas.circle(*spot, color="#2471a3", width=4)
    for i in range(9):
        for j in range(9):
            canvas.digit(i, j, digits[i][j])
    canvas.box_lines(3, 3, thin=1, thick=5)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "grid-5.json").write_text(json.dumps({"digits": digits, "shaded": shade}))
    temp = out / "grid-5.tmp.png"
    canvas.image.save(temp)
    os.replace(temp, out / "grid-5.png")
    print("picture", out / "grid-5.png", flush=True)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
