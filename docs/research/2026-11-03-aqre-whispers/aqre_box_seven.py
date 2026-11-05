"""SCRATCH: plain sudoku boxes, 7 different circles, the 7 forced by where the circles sit. One CP-SAT worker.

usage: aqre_box_seven.py DIR [LIMIT_SECONDS]

Chris's question, 2026-11-05. A 3x3 box tops out at 7, so different circles are at most 7, exactly 1 to 7. A box centre
can never hold a circled 7. So six circles on box centres and one off centre force the off-centre circle to be the 7,
which is shaded and high, and that sets the colours. Rules as `aqre_row_diagnose.build`: 1-9 sudoku, connected shading,
no 4 in a line of one colour, shaded whispers, a shaded cell in every box. The solver chooses which boxes hold circles.

A found grid is checked by plain Python with no solver, and written to box-seven.json.
"""

import json
import sys
import time
from pathlib import Path

from aqre_jigsaw_feasible import neighbours
from connected import add_flow_connectivity
from ortools.sat.python import cp_model

CELLS = [(r, c) for r in range(9) for c in range(9)]
BOXES = [[(3 * a + r, 3 * b + c) for r in range(3) for c in range(3)] for a in range(3) for b in range(3)]
CENTRES = [(3 * a + 1, 3 * b + 1) for a in range(3) for b in range(3)]


def build():
    m = cp_model.CpModel()
    x = {cell: m.new_int_var(1, 9, "") for cell in CELLS}
    g = {cell: m.new_bool_var("") for cell in CELLS}
    for i in range(9):
        m.add_all_different([x[i, c] for c in range(9)])
        m.add_all_different([x[r, i] for r in range(9)])
        m.add_all_different([x[cell] for cell in BOXES[i]])
    even_low = m.new_bool_var("")
    for a in range(9):
        for b in range(6):
            for line in ([g[a, b + i] for i in range(4)], [g[b + i, a] for i in range(4)]):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    for r, c in CELLS:
        low = even_low if (r + c) % 2 == 0 else even_low.Not()
        s = g[r, c]
        m.add(x[r, c] <= 4).only_enforce_if(s, low)
        m.add(x[r, c] >= 6).only_enforce_if(s, low.Not())
        for other in neighbours((r, c)):
            if (r, c) < other:
                t = g[other]
                m.add(x[other] - x[r, c] >= 5).only_enforce_if(s, t, low)
                m.add(x[r, c] - x[other] >= 5).only_enforce_if(s, t, low.Not())
    add_flow_connectivity(m, [g[cell] for cell in CELLS])
    value = {}
    for k, cells in enumerate(BOXES):
        total = sum(g[cell] for cell in cells)
        m.add(total >= 1)
        for v in range(1, 8):
            value[k, v] = m.new_bool_var("")
            m.add(total == v).only_enforce_if(value[k, v])
            if v == 7:
                m.add(x[CENTRES[k]] != 7).only_enforce_if(value[k, v])
            else:
                m.add(x[CENTRES[k]] == v).only_enforce_if(value[k, v])
        m.add(sum(value[k, v] for v in range(1, 8)) <= 1)
    for v in range(1, 8):
        m.add(sum(value[k, v] for k in range(9)) == 1)
    return m, x, g, value


def check(digits, shade, circles):
    """Every rule, by plain Python. Returns the first failure, or None."""
    full = set(range(1, 10))
    for i in range(9):
        if {digits[i][c] for c in range(9)} != full or {digits[r][i] for r in range(9)} != full:
            return f"line {i}"
    for k, cells in enumerate(BOXES):
        if {digits[r][c] for r, c in cells} != full:
            return f"box {k}"
        if not sum(shade[r][c] for r, c in cells):
            return f"box {k} has no shaded cell"
    for a in range(9):
        for b in range(6):
            if len({shade[a][b + i] for i in range(4)}) == 1 or len({shade[b + i][a] for i in range(4)}) == 1:
                return f"run of 4 at {a},{b}"
    shaded = [(r, c) for r, c in CELLS if shade[r][c]]
    seen = {shaded[0]}
    stack = [shaded[0]]
    while stack:
        for y in neighbours(stack.pop()):
            if shade[y[0]][y[1]] and y not in seen:
                seen.add(y)
                stack.append(y)
    if len(seen) != len(shaded):
        return "shading not connected"
    for r, c in shaded:
        for y in neighbours((r, c)):
            if shade[y[0]][y[1]] and abs(digits[r][c] - digits[y[0]][y[1]]) < 5:
                return f"whisper at {r},{c}"
    values = []
    for k, cell in circles.items():
        count = sum(shade[r][c] for r, c in BOXES[k])
        if digits[cell[0]][cell[1]] != count:
            return f"circle in box {k}"
        values.append(count)
    if sorted(values) != list(range(1, 8)):
        return f"circle values {sorted(values)}"
    off = [k for k, cell in circles.items() if cell != CENTRES[k]]
    if len(off) != 1 or digits[circles[off[0]][0]][circles[off[0]][1]] != 7:
        return "the off-centre circle is not the only one, or not the 7"
    return None


def main(out, limit):
    begun = time.time()
    m, x, g, value = build()
    s = cp_model.CpSolver()
    s.parameters.num_workers = 1
    s.parameters.max_time_in_seconds = limit
    status = s.status_name(s.solve(m))
    print(f"status {status}, {time.time() - begun:.0f}s, cap {limit:.0f}s", flush=True)
    if status not in ("OPTIMAL", "FEASIBLE"):
        return
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[int(s.value(g[r, c])) for c in range(9)] for r in range(9)]
    circles = {}
    for k in range(9):
        for v in range(1, 8):
            if s.value(value[k, v]):
                circles[k] = CENTRES[k] if v < 7 else next(cell for cell in BOXES[k] if digits[cell[0]][cell[1]] == 7)
    problem = check(digits, shade, circles)
    print(f"plain check: {problem or 'all rules hold'}", flush=True)
    for r in range(9):
        print(" ".join(f"{digits[r][c]}{'#' if shade[r][c] else '.'}{'o' if (r, c) in circles.values() else ' '}" for c in range(9)), flush=True)
    print("circles (box, row, column, digit):", [(k + 1, cell[0] + 1, cell[1] + 1, digits[cell[0]][cell[1]]) for k, cell in sorted(circles.items())], flush=True)
    if not problem:
        (out / "box-seven.json").write_text(json.dumps({"digits": digits, "shade": shade, "circles": {str(k): cell for k, cell in circles.items()}}))


if __name__ == "__main__":
    main(Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 900.0)
