"""SCRATCH, not a finder: one feasibility solve for Aqre shading + 5-whispers.

Rules: 9x9 sudoku; shaded cells one orthogonally connected group; no 4 in a
line of one colour in a row or column; orthogonally adjacent unshaded cells
differ by at least 5. Connectivity is the repo's flow encoding from
finders/counting_shaded/connected.py; the board is sudoku_kit's sudoku_model.
The reader `violations` shares nothing with the model.
"""

import json
import os
import sys
from pathlib import Path

from connected import add_flow_connectivity
from ortools.sat.python import cp_model
from finders.hunt.render import GridCanvas
from shapes import ORTH
from sudoku_kit.cpsat import solver, sudoku_model, boxes

N = 9
TIME_LIMIT = 120.0


def build():
    m, x = sudoku_model(N, boxes(N, 3, 3))
    g = [m.new_bool_var(f"g{i}") for i in range(N * N)]
    add_flow_connectivity(m, g)
    shaded = lambda r, c: g[r * N + c]
    for a in range(N):
        for b in range(N - 3):
            for line in (
                [shaded(a, b + k) for k in range(4)],
                [shaded(b + k, a) for k in range(4)],
            ):
                m.add_bool_or(line)
                m.add_bool_or([v.Not() for v in line])
    for i in range(N * N):
        for j in ORTH[i]:
            if i >= j:
                continue
            ri, ci, rj, cj = i // N, i % N, j // N, j % N
            gap = m.new_int_var(0, N - 1, f"gap{i}_{j}")
            m.add_abs_equality(gap, x[ri, ci] - x[rj, cj])
            m.add(gap >= 5).only_enforce_if(g[i].Not(), g[j].Not())
    return m, x, g


def violations(digits, shade):
    """Every rule broken by a filled grid, read with no solver."""
    found = []
    full = set(range(1, 10))
    for i in range(9):
        if set(digits[i]) != full:
            found.append(f"row {i + 1} digits")
        if {digits[r][i] for r in range(9)} != full:
            found.append(f"column {i + 1} digits")
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            box = {digits[r][c] for r in range(br, br + 3) for c in range(bc, bc + 3)}
            if box != full:
                found.append(f"box at r{br + 1}c{bc + 1} digits")
    for a in range(9):
        for b in range(6):
            row = {shade[a][b + k] for k in range(4)}
            col = {shade[b + k][a] for k in range(4)}
            if len(row) == 1:
                found.append(f"four in a line, row {a + 1} from column {b + 1}")
            if len(col) == 1:
                found.append(f"four in a line, column {a + 1} from row {b + 1}")
    steps = ((0, 1), (1, 0), (0, -1), (-1, 0))
    for r in range(9):
        for c in range(9):
            for dr, dc in steps[:2]:
                rr, cc = r + dr, c + dc
                if rr < 9 and cc < 9 and not shade[r][c] and not shade[rr][cc]:
                    if abs(digits[r][c] - digits[rr][cc]) < 5:
                        found.append(f"whisper r{r + 1}c{c + 1}-r{rr + 1}c{cc + 1}")
    cells = {(r, c) for r in range(9) for c in range(9) if shade[r][c]}
    if cells:
        seen, stack = set(), [next(iter(cells))]
        while stack:
            cell = stack.pop()
            if cell in seen:
                continue
            seen.add(cell)
            stack += [
                (cell[0] + dr, cell[1] + dc)
                for dr, dc in steps
                if (cell[0] + dr, cell[1] + dc) in cells
            ]
        if seen != cells:
            found.append(f"shaded not connected: {len(seen)} of {len(cells)}")
    return found


def controls(digits, shade):
    """Each rule of the reader must fire on a grid broken in that rule."""
    swapped = [row[:] for row in digits]
    swapped[0][0], swapped[0][1] = swapped[0][1], swapped[0][0]
    assert any("digits" in v for v in violations(swapped, shade)), "digit control"
    blank = [[False] * 9 for _ in range(9)]
    assert any("four" in v for v in violations(digits, blank)), "line control"
    assert any("whisper" in v for v in violations(digits, blank)), "whisper control"
    apart = [[False] * 9 for _ in range(9)]
    apart[0][0] = apart[8][8] = True
    assert any("connected" in v for v in violations(digits, apart)), "connect control"


def main(out_dir):
    m, x, g = build()
    s = solver(TIME_LIMIT)
    status = s.solve(m)
    name = s.status_name(status)
    print(f"status {name} in {s.wall_time:.1f}s on {s.parameters.num_workers} worker")
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 1
    digits = [[s.value(x[r, c]) for c in range(9)] for r in range(9)]
    shade = [[bool(s.value(g[r * 9 + c])) for c in range(9)] for r in range(9)]
    broken = violations(digits, shade)
    controls(digits, shade)
    print("reader violations:", broken or "none", "(controls fired)")

    counts = {}
    circles = {}
    canvas = GridCanvas(9, 9, cell=64, margin=24)
    for r in range(9):
        for c in range(9):
            if shade[r][c]:
                canvas.shade_cell(r, c, "#b8b8b8")
    for br in (0, 3, 6):
        for bc in (0, 3, 6):
            box = [(r, c) for r in range(br, br + 3) for c in range(bc, bc + 3)]
            count = sum(shade[r][c] for r, c in box)
            counts[f"r{br + 1}c{bc + 1}"] = count
            spot = next(cell for cell in box if digits[cell[0]][cell[1]] == count)
            circles[f"r{br + 1}c{bc + 1}"] = f"r{spot[0] + 1}c{spot[1] + 1}"
            canvas.circle(*spot, color="#c0392b", width=4)
    for r in range(9):
        for c in range(9):
            canvas.digit(r, c, digits[r][c])
    canvas.box_lines(3, 3, thin=1, thick=5)

    print("\n".join(
        " ".join(("#" if shade[r][c] else ".") + str(digits[r][c]) for c in range(9))
        for r in range(9)
    ))
    print("shaded total", sum(map(sum, shade)))
    print("shaded per box", counts)
    print("circle spot per box", circles)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "grid-1.json").write_text(json.dumps(
        {"digits": digits, "shaded": shade, "box_counts": counts, "circles": circles}
    ))
    temp = out / "grid-1.tmp.png"
    canvas.image.save(temp)
    os.replace(temp, out / "grid-1.png")
    print("picture", out / "grid-1.png")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
